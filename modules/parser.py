
import json
import traceback
from typing import List, Optional
from pydantic import BaseModel, Field
from PySide6.QtCore import Qt, QThread, Signal

from google import genai
from google.genai import types

from docling.document_converter import DocumentConverter

class DoclingWorker(QThread):
    """
    Runs the slow PDF-to-Text conversion in a background thread.
    Emits 'finished_signal' with the text or an error message.
    """
    finished_signal = Signal(str, bool) # (result_text_or_error, is_success)

    def __init__(self, parser, filepath):
        super().__init__()
        self.parser = parser
        self.filepath = filepath

    def run(self):
        try:
            # This is the blocking call
            text = self.parser.convert_pdf_to_text(self.filepath)
            self.finished_signal.emit(text, True)
        except Exception as e:
            error_msg = f"Docling Error:\n{str(e)}\n{traceback.format_exc()}"
            self.finished_signal.emit(error_msg, False)

class LLMWorker(QThread):
    """
    Runs the LLM extraction in a background thread so the UI stays responsive.
    Emits 'finished_signal' with (data_dict, error_string).
    """
    finished_signal = Signal(dict, str) 

    def __init__(self, parser):
        super().__init__()
        self.parser = parser

    def run(self):
        try:
            # Blocking network call happens here
            data = self.parser.extract_data_with_llm()
            # Emit success (data, no error)
            self.finished_signal.emit(data, "")
        except Exception as e:
            # Emit failure (empty data, error message)
            self.finished_signal.emit({}, str(e))

# --- 1. Define Pydantic Models (The Schema) ---

class PatientInfo(BaseModel):
    sex: Optional[str] = Field(description="Patient sex/gender (e.g., Male, Female)")
    age: Optional[float] = Field(description="Patient age in years")

class Metadata(BaseModel):
    report_date: Optional[str] = Field(description="Date of the report YYYY-MM-DD")
    lab: Optional[str] = Field(description="Name of the laboratory")
    patient: PatientInfo

class TestResult(BaseModel):
    test_name: str = Field(description="Standardized English name of the blood test (e.g., 'Hemoglobin', 'Platelets')")
    value: float = Field(description="The numeric result value")
    unit: Optional[str] = Field(description="The unit of measurement (e.g., 'g/dL', '%')")
    ref_range: Optional[str] = Field(description="Reference range as a string (e.g., '13.5-17.5', '<50')")

class BloodWorkReport(BaseModel):
    metadata: Metadata
    tests: List[TestResult] # LLMs prefer lists over dynamic dictionary keys

class PDFParser:
    """
    Public API class used by main.py
    - parse(filepath) => returns dict of parsed blood test data
    - auto_params persists until clear_auto_params() is called
    """

    def __init__(self, llm_client):
        """
        :param llm_client: Instance of google.genai.Client
        """
        self.auto_params = {}
        self.llm_client = llm_client
        self.fulltext = ""

    def set_client(self, client):
        """Allow updating the client if needed"""
        self.llm_client = client

    def convert_pdf_to_text(self, filepath):
        """
        STEP 1: CPU Intensive.
        Runs Docling to get text. Stores it in self.fulltext.
        """
        try:
            converter = DocumentConverter()
            doc = converter.convert(filepath)
            self.fulltext = doc.document.export_to_text()
            return self.fulltext
        except Exception as e:
            raise RuntimeError(f"Docling conversion failed: {e}")

    def clear_data(self):
        self.auto_params = {}
        self.fulltext = ""

    def extract_data_with_llm(self):
        """
        STEP 2: Network Intensive.
        Uses the stored self.fulltext to hit the API.
        """
        if not self.fulltext:
            raise ValueError("No text loaded. Please open a PDF first.")

        if not self.llm_client:
            raise ValueError("LLM Client not initialized.")

        SYSTEM_PROMPT = """
        You are a medical data assistant. Extract blood test results from the text.
        - Normalize test names to standard English.
        - You may use chinese test name to help with identifying what test it is
        - Ignore notes, comments, and non-test data.
        - If a value is missing, skip that test.
        """

        USER_PROMPT = f"Extract structured blood test data from this text:\n\n{self.fulltext}"

        try:
            response = self.llm_client.models.generate_content(
                model="gemini-2.5-flash-lite", 
                contents=USER_PROMPT,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": BloodWorkReport,
                    "system_instruction": SYSTEM_PROMPT,
                    "temperature": 0,
                },
            )

            # Validate
            report = BloodWorkReport.model_validate_json(response.text)

            # Transform to Dictionary for UI
            transformed_data = {
                "metadata": report.metadata.model_dump(),
                "tests": {}
            }

            for t in report.tests:
                transformed_data["tests"][t.test_name] = {
                    "value": t.value,
                    "unit": t.unit,
                    "ref_range": t.ref_range
                }
            
            self.auto_params = transformed_data
            return self.auto_params

        except Exception as e:
            raise ValueError(f"LLM API Error: {str(e)}")
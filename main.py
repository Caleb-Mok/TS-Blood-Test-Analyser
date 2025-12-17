import sys
import json
import os
import pprint

from dotenv import load_dotenv

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QFrame, QScrollArea, QTextEdit, 
    QFileDialog, QMessageBox, QProgressDialog,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from modules.analyzer import Analyzer
from modules.parser import PDFParser
from modules.parser import DoclingWorker
from modules.parser import LLMWorker
from modules.exporter import PDFExporter
from modules.normalizer import Normalizer

from google import genai
from google.genai import types


 # loads the .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env.")
    sys.exit(1)

llm_client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta")
    )

class BloodAnalyzerApp(QMainWindow):
    
    def __init__(self, json_file):
        super().__init__()
        self.setWindowTitle("Blood Test Analyser")
        self.resize(1000, 800)

        # Core Modules
        self.analyzer = Analyzer()
        self.parser = PDFParser(llm_client=llm_client)
        self.exporter = PDFExporter()
        self.json_file = json_file

        # State Variables
        self.param_inputs = {}
        self.param_autos = {}
        self.status_labels = {}
        self.analysed = {}
        self.current_pdf_path = None

        # UI Elements
        self.summary_box = QTextEdit()
        self.extract_btn = None
        self.setup_ui()
        
    def setup_ui (self):
        # central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Menu Buttons
        open_button = QPushButton("Open File")
        self.extract_btn = QPushButton("Extract Data")
        self.extract_btn.setEnabled(False) # Disabled until PDF is parsed
        clear_button = QPushButton("Clear All")
        submit_button = QPushButton("Submit")
        export_button = QPushButton("Export")

        menu_layout = QHBoxLayout() 
        button_font = QFont()
        button_font.setBold(True)
        button_font.setPointSize(10)

        for btn in [open_button, self.extract_btn ,clear_button, submit_button, export_button]:
            btn.setFixedHeight(40)
            btn.setFont(button_font)
            menu_layout.addWidget(btn)
        
        main_layout.addLayout(menu_layout)
        main_layout.addWidget(self.separator())

        # Scroll Area Setup
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(1000,500)
        main_layout.addWidget(scroll_area)

        # Scrollable Inner Widget
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        # Table Grid
        grid = QGridLayout(scroll_content)
        grid.setHorizontalSpacing(25)
        grid.setVerticalSpacing(8)

        # set how wide each column becomes
        grid.setColumnStretch(0, 3)   # Test
        grid.setColumnStretch(1, 1)   # Unit
        grid.setColumnStretch(2, 2)   # Result
        grid.setColumnStretch(3, 2)   # Range 
        grid.setColumnStretch(4, 1)   # Status

        headers = ["<b>Test</b>", "<b>Units</b>", "<b>Result</b>", "<b>Reference Range</b>", "<b>Status</b>"]
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(11)

        for col, header in enumerate(headers):
            header_label = QLabel(header)
            header_label.setFont(header_font)
            grid.addWidget(header_label, 0, col, Qt.AlignTop | Qt.AlignLeft)

        self.load_data(grid, self.json_file)
        self.normalizer = Normalizer(list(self.param_inputs.keys()))

        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.separator())

        summary_label = QLabel("<b>Summary/Notes</b>")
        summary_label.setFont(header_font)
        main_layout.addWidget(summary_label, Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(self.summary_box)
        main_layout.addStretch() # Move everything to top (top justify)

        # connect all the signals
        open_button.clicked.connect(self.on_open_pdf_clicked)
        self.extract_btn.clicked.connect(self.on_extract_clicked)
        clear_button.clicked.connect(self.clear_all)
        submit_button.clicked.connect(self.submit_data)
        export_button.clicked.connect(self.export_data)

    def separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    
    def load_data(self, grid, json_file):
        """Automatically populate the grid layout with test data"""
        with open(json_file, "r") as f:
            data = json.load(f)
        
        row = 1 # start after the header
        section_font = QFont()
        section_font.setBold(True)
        section_font.setPointSize(11)

        # category title
        for category in data["categories"]:
            category_label = QLabel(category["name"])
            category_label.setFont(section_font)
            category_label.setStyleSheet("color: #004080")

            grid.addWidget(category_label, row, 0, 1, 4)
            row += 1

            # tests

            for test in category["tests"]:
                param_label = QLabel(test["name"])
                # param_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

                unit_label = QLabel(test["units"])

                input_field = QLineEdit()
                input_field.setPlaceholderText("Enter result...")
                input_field.setFixedWidth(120)
                self.param_inputs[test["name"]] = input_field
                
                def format_reference(test):
                    min_val = str(test.get("min", "")).strip()
                    max_val = str(test.get("max", "")).strip()
                    healthy_val = str(test.get("healthy_value", "")).strip()

                    if min_val and max_val:
                        return f"{min_val}-{max_val}"
                    elif min_val:
                        return f">{min_val}"
                    elif max_val:
                        return f"<{max_val}"
                    elif healthy_val:
                        return healthy_val
                    else:
                        return ""
                    
                ref_text = format_reference(test)
                healthy_label = QLabel(ref_text)
                # healthy_label = QLabel(str(test["healthy_value"]))
                # healthy_label = QLabel(str(test["min"])+"-"+str(test["max"]))
                # healthy_label.setStyleSheet("color: gray;")

                status_label = QLabel("-")  # placeholder for later green/yellow/red
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet("background-color: gray; color: black; border-radius: 4px; padding: 2px;")
                self.status_labels[test["name"]] = status_label

                grid.addWidget(param_label, row, 0)
                grid.addWidget(unit_label, row, 1)
                grid.addWidget(input_field, row, 2)
                grid.addWidget(healthy_label, row, 3)
                grid.addWidget(status_label, row, 4)
                row += 1
    
    # --- ACTION HANDLERS ---

    def on_open_pdf_clicked(self):
        """Step 1: Open File & Run Docling (Threaded)"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Blood Test PDF", "", "PDF Files (*.pdf)"
        )
        if not filepath:
            return

        self.current_pdf_path = filepath
        
        # Create Progress Dialog
        self.progress = QProgressDialog("Reading PDF structure (Docling)...", "Cancel", 0, 0, self)
        self.progress.setWindowTitle("Reading PDF")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setCancelButton(None) # Disable cancel for simplicity
        self.progress.show()

        # Start Thread
        self.worker = DoclingWorker(self.parser, filepath)
        self.worker.finished_signal.connect(self.on_docling_finished)
        self.worker.start()

    def on_docling_finished(self, result_text, success):
        """Called when Docling thread finishes"""
        self.progress.close()
        
        if success:
            QMessageBox.information(self, "Success", "PDF Read Successfully.\nNow press 'Extract Data' to process with AI.")
            self.extract_btn.setEnabled(True)
            self.extract_btn.setStyleSheet("background-color: #d1e7dd; color: #0f5132;") # Greenish hint
        else:
            QMessageBox.critical(self, "Error Reading PDF", result_text)
            self.extract_btn.setEnabled(False)

    def on_extract_clicked(self):
        """Step 2: Run LLM Extraction (Can be retried)"""
        if not self.parser.fulltext:
            QMessageBox.warning(self, "Warning", "No PDF text loaded.")
            return

        # Show a simple spinner for LLM call too (or just block briefly since it's faster)
        # We'll use a progress dialog again for good UX
        self.llm_progress = QProgressDialog("Contacting AI for Extraction...", None, 0, 0, self)
        self.llm_progress.setWindowTitle("AI Extraction")
        self.llm_progress.setWindowModality(Qt.WindowModal)
        self.llm_progress.setMinimumDuration(0) # Show immediately
        self.llm_progress.setAutoClose(False)   # We will close it manually
        self.llm_progress.setAutoReset(False)
        
        # Connect the Cancel button to stop the thread
        self.llm_progress.canceled.connect(self.cancel_llm_worker)
        
        # 2. Setup and Start Thread
        self.llm_worker = LLMWorker(self.parser)
        self.llm_worker.finished_signal.connect(self.on_llm_finished)
        self.llm_worker.start()
        
        # Show the dialog
        self.llm_progress.exec()

    def on_llm_finished(self, parsed_data, error_msg):
        """Called when LLM thread finishes"""
        self.llm_progress.close()
        
        if error_msg:
            # If the user cancelled, we might get an error or just empty
            if "thread" not in error_msg.lower(): 
                QMessageBox.critical(self, "Extraction Failed", f"AI Error:\n{error_msg}\n\nPlease try pressing Extract again.")
            return

        # Success
        self.populate_ui_from_data(parsed_data)
        QMessageBox.information(self, "Success", "Data extracted and fields populated!")
        self.extract_btn.setStyleSheet("")
        pprint.pp(parsed_data)

    def cancel_llm_worker(self):
        """Handle user clicking 'Cancel' on the loading popup"""
        if hasattr(self, 'llm_worker') and self.llm_worker.isRunning():
            self.llm_worker.terminate()
            self.llm_worker.wait()

    def populate_ui_from_data(self, parsed_data):
        """
        Uses the Normalizer module to clean data before populating UI by
        filling the inputs with the data returned from parser
        """
        if not parsed_data:
            return
        
        # 1. Delegate the complex matching logic to the Normalizer
        clean_data = self.normalizer.normalize(parsed_data)
            
        count = 0
        # 2. Populate UI (No logic needed here, just simple assignment)
        for test_name, value in clean_data.items():
            if test_name in self.param_inputs:
                self.param_inputs[test_name].setText(value)
                # Update the persistent auto-fill dict too
                self.param_autos[test_name] = value 
                count += 1
        
        QMessageBox.information(self, "Success", f"Populated {count} fields.")

    def clear_all(self):
        """Clears inputs, parser memory, and resets UI"""
        # Clear UI
        for field in self.param_inputs.values():
            field.clear()
        self.summary_box.clear()

        # Clear Status
        for label in self.status_labels.values():
            label.setText("-")
            label.setStyleSheet("background-color: lightgray; color: black; border-radius: 4px; padding: 2px;")

        # Clear Data
        self.param_autos = {}
        self.analysed = {}
        self.parser.clear_data()
        
        # Reset Buttons
        self.extract_btn.setEnabled(False)
        self.extract_btn.setStyleSheet("")
        self.current_pdf_path = None

    def submit_data(self):
        """Submits all the value in the line fields to the analyzer and runs the analyzer"""
        raw_data = {param: field.text().strip() for param, field in self.param_inputs.items()}

        # 2. Prepare AI Extracted Units for validation
        # We need to map the AI's units to the canonical test names using the Normalizer
        ai_units_map = {}
        if self.parser.auto_params:
            raw_ai_tests = self.parser.auto_params.get("tests", {})
            
            # We iterate through the raw AI data
            for llm_name, test_data in raw_ai_tests.items():
                unit = test_data.get("unit")
                if unit:
                    # Find which Canonical Name this corresponds to
                    # (We use the internal helper from normalizer if available, or just re-normalize)
                    # Since we don't expose _find_best_match publicly, we can rely on 
                    # self.param_autos logic if we tracked it, OR we just trust the normalize() output if we stored it.
                    
                    # Better approach: Re-use the Normalizer's logic to find the key
                    canonical = self.normalizer._find_best_match(llm_name)
                    if canonical:
                        ai_units_map[canonical] = unit

        self.analysed, summary = self.analyzer.analyze(raw_data, extracted_units=ai_units_map)
        self.summary_box.setPlainText(summary)

        for test_name, info in self.analysed.items():
            status = info["status"]
            # check for unit mismatch
            is_mismatch = info.get("unit_mismatch", False)
            label = self.status_labels.get(test_name)
            if not label:
                continue

            if is_mismatch:
                label.setText("Unit Mismatch")
                label.setStyleSheet("background-color: orange; color: black; font-weight: bold; border-radius: 4px; padding: 2px;")
                # Optional: Tooltip showing the difference
                label.setToolTip(f"Database: {info['units']} vs Extracted: {info['ai_unit']}")

            # Set text and background color
            if status == "green":
                label.setText("Normal")
                label.setStyleSheet("background-color: lightgreen; color: black; border-radius: 4px; padding: 2px;")
            elif status == "yellow":
                label.setText("Slightly High/Low")
                label.setStyleSheet("background-color: yellow; color: black; border-radius: 4px; padding: 2px;")
            elif status == "red":
                label.setText("Abnormal")
                label.setStyleSheet("background-color: red; color: white; border-radius: 4px; padding: 2px;")
            elif status == "empty":
                label.setText("Not Tested")
                label.setStyleSheet("background-color: lightgray; color: black; border-radius: 4px; padding: 2px;")
            else:
                label.setText("Check Manually")
                label.setStyleSheet("background-color: orange; color: black; border-radius: 4px; padding: 2px;")


    def export_data(self):
        if not self.analysed:
            QMessageBox.warning(self, "Warning", "Please analyze data (Submit) before exporting.")
            return
        
        # 2. Open File Explorer to choose save location
        # This handles the "File Explorer" requirement
        default_name = "BloodWork_Report.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save PDF Report", 
            default_name, 
            "PDF Files (*.pdf)"
        )

        if not save_path:
            return # User cancelled

        # 3. Call Exporter
        try:
            # We pass:
            # 1. The status/results (self.analysed)
            # 2. The raw AI data for metadata like Units/Ref Ranges (self.parser.auto_params)
            # 3. The notes (self.summary_box)
            # 4. The path
            self.exporter.export(
                self.analysed, 
                self.parser.auto_params, 
                self.summary_box.toPlainText(), 
                save_path
            )
            
            QMessageBox.information(self, "Success", f"Report saved successfully to:\n{save_path}")
            
            # Optional: Open the file automatically after saving
            # import os
            # os.startfile(save_path) # Windows only
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Ensure data file exists or handle error
    data_file = "data/healthy_ranges.json"
    if not os.path.exists(data_file):
        QMessageBox.critical(None, "Fatal Error", f"Configuration file not found: {data_file}")
        sys.exit(1)

    window = BloodAnalyzerApp(data_file)
    window.show()

    app.exec()
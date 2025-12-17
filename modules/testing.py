# from docling.datamodel.base_models import InputFormat
# from docling.document_extractor import DocumentExtractor

# extractor = DocumentExtractor(allowed_formats=[InputFormat.IMAGE, InputFormat.PDF])
# file_path = "BloodTestReport.pdf"

# result = extractor.extract(
#     source=file_path
#     # template={
#     #     "bill_no": "string",
#     #     "total": "float",
#     # },
# )
# print(result.pages)

from docling.document_converter import DocumentConverter

def extract_text_with_docling(pdf_path: str) -> str:
    converter = DocumentConverter()
    doc = converter.convert(pdf_path)
    return doc.document.export_to_text()

fulltext = extract_text_with_docling("BloodTestReport.pdf")

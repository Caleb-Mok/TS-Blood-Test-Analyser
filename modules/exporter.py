from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from datetime import datetime

class PDFExporter:
    def export(self, analyzed_data, ai_data, summary_text, filepath):
        """
        Generates a PDF report.
        :param analyzed_data: Dict containing statuses and merged unit info (from Analyzer).
        :param ai_data: (Unused but kept for compatibility) Raw parser data.
        :param summary_text: String from the summary box.
        :param filepath: Where to save the PDF.
        """
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # --- 1. Title & Header ---
        title_style = styles['Title']
        elements.append(Paragraph("Blood Test Analysis Report", title_style))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # --- 2. Summary Section ---
        elements.append(Paragraph("Summary / Physician Notes", styles['Heading2']))
        
        # Handle newlines in summary text for PDF
        formatted_summary = summary_text.replace('\n', '<br/>')
        elements.append(Paragraph(formatted_summary, styles['BodyText']))
        elements.append(Spacer(1, 20))

        # --- 3. Results Table ---
        elements.append(Paragraph("Detailed Test Results", styles['Heading2']))
        elements.append(Spacer(1, 10))

        # Define Table Headers
        # Col 1: Name, Col 2: User Value + AI Unit, Col 3: Standard Unit, Col 4: Range, Col 5: Status
        table_headers = ['Test Name', 'Result', 'Unit (Target)', 'Ref. Range', 'Status']
        table_data = [table_headers]

        # Prepare Data Rows
        for test_name, info in analyzed_data.items():
            
            # Skip empty fields
            if info.get('status') == 'empty': 
                continue

            # 1. Format Result (Value + Detected Unit)
            res_val = str(info.get("value", "-"))
            ai_unit = str(info.get("ai_units", "")) # This comes from the UI "Detected Unit" box
            
            # Only add space if unit exists
            if ai_unit != "None":
                result_display = f"{res_val} {ai_unit}".strip()
            else:
                result_display = f"{res_val}".strip()

            # 2. Format Target Unit (From JSON)
            db_unit = str(info.get("db_units", ""))

            # 3. Format Reference Range
            min_v = str(info.get("min", "")).strip()
            max_v = str(info.get("max", "")).strip()
            
            # Logic to handle <, >, or ranges
            if min_v and max_v:
                ref_display = f"{min_v} - {max_v}"
            elif max_v:
                ref_display = f"< {max_v}"
            elif min_v:
                ref_display = f"> {min_v}"
            else:
                ref_display = "-"

            # 4. Format Status & Color Key
            raw_status = info.get("status", "unknown")
            display_status = raw_status.upper() # Default fallback

            # Map internal codes to nice PDF text
            if raw_status == "green":
                display_status = "NORMAL"
            elif raw_status == "yellow":
                display_status = "BORDERLINE"
            elif raw_status == "red":
                display_status = "ABNORMAL"
            else:
                display_status = "MANUAL CHECK"

            row = [test_name, result_display, db_unit, ref_display, display_status]
            table_data.append(row)

        # --- 4. Table Styling ---
        # A4 width is ~595 points. Margins reduce this to ~450-480 points.
        # [Name, Result, Unit, Range, Status]
        col_widths = [160, 80, 70, 80, 90] 

        t = Table(table_data, colWidths=col_widths)

        # Base Styles
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),    # Header Background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),   # Header Text
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),               # Center align all
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),                  # Left align Test Names
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),     # Header Font
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),              # Header Padding
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),      # Row Background
            ('GRID', (0, 0), (-1, -1), 1, colors.black),         # Grid lines
            ('FONTSIZE', (0, 0), (-1, -1), 9),                   # Font size
        ])
        
        for i, row in enumerate(table_data):
            if i == 0: continue # Skip header

            status_text = row[4] # The Status Column
            
            if status_text == "ABNORMAL":
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.red)
                tbl_style.add('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
            elif status_text == "BORDERLINE":
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.orange) # or colors.darkgoldenrod
                tbl_style.add('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
            elif status_text == "NORMAL":
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.green)
            elif status_text == "MANUAL CHECK":
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.blue)

        t.setStyle(tbl_style)
        elements.append(t)

        # Build
        doc.build(elements)
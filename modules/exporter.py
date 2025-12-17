from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

class PDFExporter:
    def export(self, analyzed_data, ai_data, summary_text, filepath):
        """
        Generates a PDF report.
        :param analyzed_data: Dict containing statuses (from Analyzer).
        :param ai_data: Dict containing extracted units/ref ranges (from Parser).
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
        table_data = [['Test Name', 'Result', 'Unit', 'Ref. Range', 'Status']]

        # Prepare Data Rows
        # Analyzed data keys should match the UI keys
        for test_name, info in analyzed_data.items():
            
            # Get Value & Status from Analysis
            value = info.get("value", "-")
            status = info.get("status", "unknown")
            
            # Get Metadata (Units/Ref) from AI Data (if available)
            # We check the AI data for matching keys to fill in details
            unit = "-"
            ref_range = "-"
            
            # Try to find metadata in ai_data (parser results)
            # Note: ai_data might be loose, so we look for exact match first
            if ai_data and "tests" in ai_data:
                # We need to find the AI key that mapped to this test_name
                # Since we don't have the reverse map here, we check if test_name exists directly
                # or rely on what's available. 
                # Ideally, main.py should pass combined data, but we do a safe lookup here.
                ai_test = ai_data["tests"].get(test_name)
                if ai_test:
                    unit = ai_test.get("unit", "-")
                    ref_range = ai_test.get("ref_range", "-")

            # Create Row
            row = [test_name, str(value), unit, ref_range, status.upper()]
            table_data.append(row)

        # --- 4. Table Styling ---
        # Auto-calculate column widths based on A4 width (approx 500pts usable)
        col_widths = [160, 60, 60, 100, 100] 

        t = Table(table_data, colWidths=col_widths)

        # specific styles
        tbl_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue), # Header bg
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Header text
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Align Test Names Left
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige), # Row bg
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])

        # Color code the Status column (Column index 4)
        for i, row in enumerate(table_data[1:], start=1):
            status_text = row[4] # The status column
            if "ABNORMAL" in status_text or "RED" in status_text:
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.red)
                tbl_style.add('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
            elif "HIGH" in status_text or "LOW" in status_text:
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.orange)
            elif "NORMAL" in status_text or "GREEN" in status_text:
                tbl_style.add('TEXTCOLOR', (4, i), (4, i), colors.green)

        t.setStyle(tbl_style)
        elements.append(t)

        # Build
        doc.build(elements)
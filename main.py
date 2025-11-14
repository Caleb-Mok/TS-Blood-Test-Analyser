import sys
import numpy
import json

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QSizePolicy, QFrame, QScrollArea, QTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from modules.analyzer import Analyzer
from modules.parser import PDFParser
from modules.exporter import PDFExporter


class BloodAnalyzerApp(QMainWindow):
    
    def __init__(self, json_file):
        super().__init__()
        self.setWindowTitle("Blood Test Analyser")
        self.resize(1000, 800)
        self.analyzer = Analyzer()
        self.parser = PDFParser()
        self.exporter = PDFExporter()
        self.json_file = json_file

        self.param_inputs = {}
        self.param_autos = {}
        self.status_labels = {}
        self.analysed = {}
        self.summary_box = QTextEdit()
        self.setup_ui()
        
    def setup_ui (self):
        # central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Menu Buttons
        open_button = QPushButton("Open")
        clear_button = QPushButton("Clear All")
        submit_button = QPushButton("Submit")
        export_button = QPushButton("Export")

        menu_layout = QHBoxLayout() 
        button_font = QFont()
        button_font.setBold(True)
        button_font.setPointSize(11)

        for btn in [open_button, clear_button, submit_button, export_button]:
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

        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.separator())

        summary_label = QLabel("<b>Summary/Notes</b>")
        summary_label.setFont(header_font)
        main_layout.addWidget(summary_label, Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(self.summary_box)
        main_layout.addStretch() # Move everything to top (top justify)

        # connect all the signals
        clear_button.clicked.connect(self.clear_all)
        submit_button.clicked.connect(self.submit_data)
        export_button.clicked.connect(self.export_data)
        open_button.clicked.connect(self.open_n_parse_data)

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

    def clear_all(self):
        """Clears all QLineEdit fields and summary box."""
        for field in self.param_inputs.values():
            field.clear()
        self.summary_box.clear()

        for label in self.status_labels.values():
            label.setText("-")
            label.setStyleSheet("background-color: lightgray; color: black; border-radius: 4px; padding: 2px;")

        self.status_outputs = {}

    def submit_data(self):
        """Submits all the value in the line fields to the analyzer and runs the analyzer"""
        raw_data = {param: field.text().strip() for param, field in self.param_inputs.items()}

        self.analysed, summary = self.analyzer.analyze(raw_data)
        self.summary_box.setPlainText(summary)

        for test_name, info in self.analysed.items():
            status = info["status"]
            label = self.status_labels.get(test_name)
            if not label:
                continue

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
            elif status == "uncheckable":
                label.setText("Check Manually")
                label.setStyleSheet("background-color: orange; color: black; border-radius: 4px; padding: 2px;")
            else:
                # label.setText("Unknown")
                # label.setStyleSheet("background-color: gray; color: white; border-radius: 4px; padding: 2px;")
                label.setText("Check Manually")
                label.setStyleSheet("background-color: orange; color: black; border-radius: 4px; padding: 2px;")


    def export_data(self):
        """Starts the export process"""
        print("Exporting data")
        self.exporter.export(self.analysed, self.summary_box.toPlainText())

    def open_n_parse_data(self):
        """Calls parser.py and start parsing the pdf/img from open file
        might want to pop a window popup to choose which files
        """
        print("Opening file")
        filepath = "get filepath from popup"

        self.param_autos = self.parser.parse(filepath)

        # then do comparisons, if param_autos have the same key as params_inputs then update the params_inputs value with the param_autos value.






if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = BloodAnalyzerApp("data/healthy_ranges.json")
    window.show()

    app.exec()
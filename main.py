import sys
import numpy
import json

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QSizePolicy, QFrame, QScrollArea, QTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from modules.analyzer import Analyzer
from modules.parser import PDFParser


class BloodAnalyzerApp(QMainWindow):
    
    def __init__(self, json_file):
        super().__init__()
        self.setWindowTitle("Blood Test Analyser")
        self.resize(1000, 800)
        self.analyzer = Analyzer()
        self.parser = PDFParser()
        self.json_file = json_file

        self.param_inputs = {}
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

        headers = ["<b>Test</b>", "<b>Units</b>", "<b>Result</b>", "<b>Range</b>", "<b>Status</b>"]
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

        main_layout.addWidget(QLabel("<b>Summary/Notes</b>"), Qt.AlignTop | Qt.AlignLeft)
        main_layout.addWidget(self.summary_box)
        main_layout.addStretch() # Move everything to top (top justify)

        # connect all the signals
        clear_button.clicked.connect(self.clear_all)
        submit_button.clicked.connect(self.submit_data)

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

                healthy_label = QLabel(str(test["healthy_value"]))
                # healthy_label.setStyleSheet("color: gray;")

                status_label = QLabel("-")  # placeholder for later green/yellow/red
                status_label.setAlignment(Qt.AlignCenter)

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

    def submit_data(self):
        """Submits all the value in the line fields to the analyzer and runs the analyzer"""
        raw_data = {param: field.text().strip() for param, field in self.param_inputs.items()}

        result = self.analyzer.analyze(raw_data)

        self.display_summary(result)
    
    def display_summary(self, result):
        """Display the analyser's result in the summary box"""
        self.summary_box.setPlainText("This is your summary: .....")





if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = BloodAnalyzerApp("data/healthy_ranges.json")
    window.show()

    app.exec()
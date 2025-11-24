# modules/parser.py
"""
PDF parser with modal region selector.

Usage (in your main.py):
    from modules.parser import PDFParser
    parser = PDFParser()
    param_autos = parser.parse(filepath)   # opens modal, returns dict
    # parser.auto_params persists until parser.clear_auto_params()

Dependencies:
    pip install PySide6 pymupdf pillow pytesseract  # pytesseract optional (OCR)
"""

import os
import re
from collections import defaultdict

import fitz  # PyMuPDF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QRectF, QRect, QPoint
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except Exception:
    _OCR_AVAILABLE = False


class RegionCanvas(QWidget):
    """
    Widget that displays a QPixmap and supports drawing multiple rectangular selections.
    It stores rectangles in widget coordinates (x, y, w, h).
    """

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.pixmap = pixmap
        self.setMinimumSize(pixmap.size())
        self._selections = []  # list of QRect
        self._current_rect = None
        self._start_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

        # draw existing rectangles (semi-transparent fill + border)
        pen = QPen(QColor(255, 0, 0), 2)
        painter.setPen(pen)
        for rect in self._selections:
            painter.fillRect(rect, QColor(255, 0, 0, 40))
            painter.drawRect(rect)

        # draw current rectangle while dragging
        if self._current_rect:
            painter.fillRect(self._current_rect, QColor(255, 0, 0, 40))
            painter.drawRect(self._current_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.pos()
            self._current_rect = QRect(self._start_pos, self._start_pos)
            self.update()

    def mouseMoveEvent(self, event):
        if self._start_pos is not None:
            current_pos = event.pos()
            self._current_rect = QRect(self._start_pos, current_pos).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start_pos is not None:
            # finalize rect (ignore very small)
            rect = QRect(self._start_pos, event.pos()).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self._selections.append(rect)
            self._start_pos = None
            self._current_rect = None
            self.update()

    def clear_last_selection(self):
        if self._selections:
            self._selections.pop()
            self.update()

    def clear_all(self):
        self._selections = []
        self.update()

    def selections(self):
        # returns list of QRect
        return list(self._selections)


class PDFSelectionDialog(QDialog):
    """
    Modal dialog that shows PDF pages and allows region selection per page.
    On Done, it crops each selected region and extracts text via PyMuPDF (and OCR fallback).
    """

    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select regions from PDF")
        self.resize(900, 700)
        self.pdf_path = pdf_path

        # open document
        self.doc = fitz.open(pdf_path)
        self.page_count = len(self.doc)

        # stores per-page selections as list of QRect (widget coords)
        self.page_selections = defaultdict(list)

        # stores QPixmap renderings per page (to avoid re-render)
        self.page_pixmaps = {}

        # UI state
        self.current_page_index = 0
        self.canvas = None

        # results: list of tuples (page_index, QRect)
        self._extracted_regions = []

        self._setup_ui()
        self._show_page(0)

    def _setup_ui(self):
        vbox = QVBoxLayout(self)

        # Page navigation row
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.page_label = QLabel("")
        nav_row.addWidget(self.prev_btn)
        nav_row.addWidget(self.next_btn)
        nav_row.addWidget(self.page_label)
        nav_row.addStretch()
        self.delete_btn = QPushButton("Delete Last Selection")
        nav_row.addWidget(self.delete_btn)
        vbox.addLayout(nav_row)

        # Canvas area placeholder
        self.canvas_container = QVBoxLayout()
        vbox.addLayout(self.canvas_container)

        # Action buttons
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.done_btn = QPushButton("Done")
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.done_btn)
        vbox.addLayout(action_row)

        # Connect signals
        self.prev_btn.clicked.connect(self._on_prev)
        self.next_btn.clicked.connect(self._on_next)
        self.done_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.delete_btn.clicked.connect(self._on_delete_last)

    def _render_page_to_qpixmap(self, page_index, zoom=2.0):
        """
        Render a fitz.Page into a QPixmap. Cache results.
        Zoom controls resolution; default zoom=2.0 (approx 144-150 dpi).
        """
        if page_index in self.page_pixmaps:
            return self.page_pixmaps[page_index]

        page = self.doc[page_index]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        mode = QImage.Format_RGB888
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, mode)
        qpix = QPixmap.fromImage(qimg.copy())  # copy to detach from pixmap memory
        self.page_pixmaps[page_index] = (qpix, pix, mat)
        return qpix, pix, mat

    def _show_page(self, index):
        # save existing canvas selections
        if self.canvas is not None:
            prev_selections = self.canvas.selections()
            self.page_selections[self.current_page_index] = prev_selections
            # remove old widget
            for i in reversed(range(self.canvas_container.count())):
                widget = self.canvas_container.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

        # prepare page
        self.current_page_index = max(0, min(index, self.page_count - 1))
        qpix, pix, mat = self._render_page_to_qpixmap(self.current_page_index)

        # create new canvas
        self.canvas = RegionCanvas(qpix)
        # restore selections for this page (if any)
        for rect in self.page_selections.get(self.current_page_index, []):
            self.canvas._selections.append(rect)

        self.canvas_container.addWidget(self.canvas)
        self._update_page_label()

    def _update_page_label(self):
        self.page_label.setText(f"Page {self.current_page_index + 1} / {self.page_count}")

    def _on_prev(self):
        if self.current_page_index > 0:
            self._show_page(self.current_page_index - 1)

    def _on_next(self):
        if self.current_page_index < self.page_count - 1:
            self._show_page(self.current_page_index + 1)

    def _on_delete_last(self):
        # delete last selection on current page
        if self.canvas:
            self.canvas.clear_last_selection()
            self.page_selections[self.current_page_index] = self.canvas.selections()

    # ---------------- extraction routines ----------------

    def _widget_rect_to_pdf_rect(self, widget_rect, page_index):
        """
        Convert a QRect (widget coords) to a fitz.Rect (PDF coordinates).
        We used a rendering matrix when creating the pixmap; map accordingly.

        widget_rect: QRect
        returns: fitz.Rect(x0, y0, x1, y1) in PDF page coordinate space
        """
        # get cached pixmap info
        qpix, pix, mat = self.page_pixmaps[page_index]
        # pix.width, pix.height are image pixel size after scaling by mat
        # page.rect gives original PDF points (unscaled)
        page = self.doc[page_index]
        page_rect = page.rect  # in PDF points

        # compute scale factors from image pixels -> PDF points
        sx = page_rect.width / pix.width
        sy = page_rect.height / pix.height

        x0 = widget_rect.left() * sx
        y0 = widget_rect.top() * sy
        x1 = widget_rect.right() * sx
        y1 = widget_rect.bottom() * sy

        # fitz.Rect expects (x0, y0, x1, y1)
        return fitz.Rect(x0, y0, x1, y1)

    def extract_selected_regions_text(self, use_ocr_if_empty=True):
        """
        For each page and each selection rect, extract text using PyMuPDF's page.get_text("text", clip=rect).
        If empty and OCR is available + use_ocr_if_empty True, use pytesseract on cropped image.
        Returns dict of extracted texts by page and region index.
        """
        extracted = []  # list of tuples (page_index, rect, text)
        for page_idx, rects in self.page_selections.items():
            if not rects:
                continue
            # ensure cached page pixmap exists (needed for OCR cropping)
            qpix, pix, mat = self._render_page_to_qpixmap(page_idx)
            for rect in rects:
                pdf_rect = self._widget_rect_to_pdf_rect(rect, page_idx)
                page_obj = self.doc[page_idx]
                try:
                    # PyMuPDF text extraction inside clip
                    txt = page_obj.get_text("text", clip=pdf_rect)
                except Exception:
                    txt = ""

                txt = txt.strip()
                if not txt and use_ocr_if_empty and _OCR_AVAILABLE:
                    # fallback: crop the pix (pix is fitz.Pixmap)
                    # convert pix to PIL Image and crop using widget rect scaled to pix dimensions
                    # pix.samples is bytes in RGB
                    pil_mode = "RGB"
                    img = Image.frombytes(pil_mode, (pix.width, pix.height), pix.samples)
                    # map widget rect to pix coordinates
                    # ratio widget->pix: pix.width / qpix.width()
                    widget_to_pix_x = pix.width / qpix.width()
                    widget_to_pix_y = pix.height / qpix.height()
                    crop_box = (
                        int(rect.left() * widget_to_pix_x),
                        int(rect.top() * widget_to_pix_y),
                        int(rect.right() * widget_to_pix_x),
                        int(rect.bottom() * widget_to_pix_y),
                    )
                    try:
                        cropped = img.crop(crop_box)
                        ocr_text = pytesseract.image_to_string(cropped)
                        txt = ocr_text.strip()
                    except Exception:
                        txt = ""

                extracted.append((page_idx, rect, txt))
        return extracted


class PDFParser:
    """
    Public API class used by main.py
    - parse(filepath) => opens modal dialog, returns dict of parsed key/value pairs
    - auto_params persists in self.auto_params until clear_auto_params() called
    """

    def __init__(self):
        self.auto_params = {}  # persistent across parse() calls until cleared

    def parse(self, filepath):
        """
        Main entry. Opens a modal dialog for the user to select regions.
        After Done, extracts text from regions and attempts to parse test name -> value.
        Returns: dict {param_name: value}
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        # Create and run modal dialog
        app = QApplication.instance()
        dialog_owner = None
        if app is not None:
            # find top-level widget as owner, else None
            if app.topLevelWidgets():
                dialog_owner = app.topLevelWidgets()[0]

        dlg = PDFSelectionDialog(filepath, parent=dialog_owner)
        result = dlg.exec()  # modal; blocks until closed

        if result != QDialog.Accepted:
            # user cancelled
            return dict(self.auto_params)

        # copy selections from dialog
        selections = dlg.page_selections
        # extract texts from selected regions
        extracted = dlg.extract_selected_regions_text(use_ocr_if_empty=True)

        # parse extracted texts into key/value pairs
        parsed = self._parse_extracted_texts(extracted)
        # merge into persistent auto_params (overwrite existing keys)
        self.auto_params.update(parsed)
        return dict(self.auto_params)

    def clear_auto_params(self):
        self.auto_params = {}

    # ----------------- text parsing heuristics -----------------
    def _parse_extracted_texts(self, extracted_regions):
        """
        Convert list of (page_idx, rect, text) into {name: value} best-effort.
        Strategy:
            - split text into lines
            - for each block, find first numeric token (int/float) - that's the value
            - the preceding text (token(s) or previous line) is used as candidate name (English)
            - sanitize name to match keys in your UI (you can expand normalization in normalizer.py)
        """
        results = {}

        for page_idx, rect, text in extracted_regions:
            if not text:
                continue
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if not lines:
                continue

            # combine into single string for search
            joined = " | ".join(lines)

            # find numeric values (integers, floats, possibly with %)
            num_match = re.search(r"(-?\d+(?:\.\d+)?%?)", joined)
            if num_match:
                value_token = num_match.group(1)
                # find name: take substring before this value_token in joined text
                before = joined[:num_match.start()].strip()
                # heuristic: name = last line or last tokens from 'before'
                name_candidate = None
                if before:
                    parts = re.split(r"\||\n", before)
                    # pick last non-empty part and strip Chinese characters
                    candidate = parts[-1].strip()
                    # remove Chinese characters to prefer English name
                    name_candidate = re.sub(r"[\u4e00-\u9fff]+", "", candidate).strip()
                    # if empty after removing Chinese, try earlier parts
                    if not name_candidate:
                        for p in reversed(parts[:-1]):
                            candidate = p.strip()
                            name_candidate = re.sub(r"[\u4e00-\u9fff]+", "", candidate).strip()
                            if name_candidate:
                                break
                # fallback: use first line without numbers
                if not name_candidate:
                    for ln in lines:
                        if not re.search(r"\d", ln):
                            name_candidate = re.sub(r"[\u4e00-\u9fff]+", "", ln).strip()
                            if name_candidate:
                                break
                if not name_candidate:
                    # as last resort use the whole block
                    name_candidate = re.sub(r"[\u4e00-\u9fff]+", "", lines[0]).strip()

                # sanitize name (strip punctuation)
                name_clean = re.sub(r"[^A-Za-z0-9 \-/()+%]", "", name_candidate).strip()
                if not name_clean:
                    continue

                # normalize value string (remove spaces)
                value_clean = value_token.replace(" ", "")
                results[name_clean] = value_clean

            else:
                # no numeric token found; skip or store as flag
                # optionally, could attempt to extract binary results (Positive/Negative)
                txt_lower = joined.lower()
                if "positive" in txt_lower or "negative" in txt_lower:
                    # attempt to take preceding token as name
                    # naive: take first word before 'positive' or 'negative'
                    m = re.search(r"([A-Za-z /()-]+)\s+(positive|negative)", txt_lower)
                    if m:
                        name = m.group(1).strip()
                        val = m.group(2).capitalize()
                        results[name] = val

        return results

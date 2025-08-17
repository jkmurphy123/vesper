# ui_renderer.py
from __future__ import annotations
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QTextBrowser, QVBoxLayout, QApplication
)


class ConversationWindow(QMainWindow):
    def __init__(self, title: str, background_path: str, ui_cfg: dict) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1000, 700)

        self._bg_label = QLabel()
        self._bg_label.setAlignment(Qt.AlignCenter)

        self._text = QTextBrowser()
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)

        # Styling for white rounded rectangle feel via stylesheet
        opacity = float(ui_cfg.get("text_box_opacity", 0.92))
        rgba = int(opacity * 255)
        rounding = int(ui_cfg.get("text_box_rounding", 16))
        self._text.setStyleSheet(
            f"QTextBrowser {{"
            f"background-color: rgba(255,255,255,{rgba});"
            f"border-radius: {rounding}px;"
            f"padding: 16px;"
            f"}}"
        )

        font = QFont(
            ui_cfg.get("font_family", "DejaVu Sans"),
            int(ui_cfg.get("font_point_size", 12))
        )
        self._text.setFont(font)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            int(ui_cfg.get("text_box_margin", 24)),
            int(ui_cfg.get("text_box_margin", 24)),
            int(ui_cfg.get("text_box_margin", 24)),
            int(ui_cfg.get("text_box_margin", 24)),
        )
        layout.addWidget(self._bg_label, stretch=1)

        # place the text browser *over* the image by making it the central widget and using a trick:
        self.setCentralWidget(container)
        self._background_path = background_path
        self._pixmap = QPixmap(self._background_path)
        self._bg_label.installEventFilter(self)

        # We’ll draw the text widget last so it appears on top visually
        layout.addWidget(self._text, stretch=0)

        self._update_background()

    def eventFilter(self, obj, event):
        # When label resizes, fit image
        if obj is self._bg_label and event.type() == event.Resize:
            self._update_background()
        return super().eventFilter(obj, event)

    def _update_background(self):
        if self._pixmap.isNull():
            self._bg_label.setText("(background not found)")
            return
        size = self._bg_label.size()
        if size.width() <= 0 or size.height() <= 0:
            return
        scaled = self._pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._bg_label.setPixmap(scaled)

    def display_text(self, html_or_text: str) -> None:
        # Accept either plain text or HTML
        if "<" in html_or_text and ">" in html_or_text:
            self._text.setHtml(html_or_text)
        else:
            self._text.setPlainText(html_or_text)
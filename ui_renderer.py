# ui_renderer.py
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QTextBrowser, QVBoxLayout
)

class ConversationWindow(QMainWindow):
    def __init__(self, title: str, background_path: str, ui_cfg: dict) -> None:
        super().__init__()
        self.setWindowTitle(title)

        # Size from config (defaults if missing)
        width = int(ui_cfg.get("screen_width", 1000))
        height = int(ui_cfg.get("screen_height", 700))
        self.resize(width, height)

        self._bg_label = QLabel()
        self._bg_label.setAlignment(Qt.AlignCenter)

        self._text = QTextBrowser()
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)

        # Status bar at bottom
        self._status_label = QLabel("Ready")
        font = QFont(
            ui_cfg.get("font_family", "DejaVu Sans"),
            int(ui_cfg.get("font_point_size", 10))
        )
        self._status_label.setFont(font)
        self._status_label.setStyleSheet("background-color: rgba(0,0,0,150); color: white; padding: 4px;")

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
        margin = int(ui_cfg.get("text_box_margin", 24))
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(self._bg_label, stretch=1)
        layout.addWidget(self._text, stretch=0)
        layout.addWidget(self._status_label, stretch=0)

        self.setCentralWidget(container)

        self._background_path = background_path
        self._pixmap = QPixmap(self._background_path)
        self._bg_label.installEventFilter(self)
        self._update_background()

    def eventFilter(self, obj, event):
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

    def set_background(self, path: str) -> None:
        """Switch the background image and refresh."""
        self._background_path = path
        self._pixmap = QPixmap(self._background_path)
        self._update_background()

    def display_text(self, html_or_text: str) -> None:
        if "<" in html_or_text and ">" in html_or_text:
            self._text.setHtml(html_or_text)
        else:
            self._text.setPlainText(html_or_text)

    def show_status(self, message: str) -> None:
        self._status_label.setText(message)
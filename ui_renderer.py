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
        self.resize(1000, 700)

        self._bg_label = QLabel()
        self._bg_label.setAlignment(Qt.AlignCenter)

        self._text = QTextBrowser()
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)

        # White rounded panel for main text
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

        # NEW: status bar at the bottom
        self._status = QLabel()
        s_opacity = float(ui_cfg.get("status_opacity", 0.8))
        s_rgba = int(s_opacity * 255)
        s_height = int(ui_cfg.get("status_height", 28))
        s_font = QFont(
            ui_cfg.get("font_family", "DejaVu Sans"),
            int(ui_cfg.get("status_font_point_size", 10))
        )
        self._status.setFont(s_font)
        self._status.setMinimumHeight(s_height)
        self._status.setMaximumHeight(s_height)
        self._status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._status.setStyleSheet(
            f"QLabel {{ background-color: rgba(0,0,0,{s_rgba}); color: white; padding-left: 10px; }}"
        )
        self._status.setText("")

        container = QWidget()
        layout = QVBoxLayout(container)
        margin = int(ui_cfg.get("text_box_margin", 24))
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addWidget(self._bg_label, stretch=1)

        self.setCentralWidget(container)
        self._background_path = background_path
        self._pixmap = QPixmap(self._background_path)
        self._bg_label.installEventFilter(self)

        # Main text area then status bar at the very bottom
        layout.addWidget(self._text, stretch=0)
        layout.addWidget(self._status, stretch=0)

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

    def display_text(self, html_or_text: str) -> None:
        if "<" in html_or_text and ">" in html_or_text:
            self._text.setHtml(html_or_text)
        else:
            self._text.setPlainText(html_or_text)

    # NEW: print a status message across the bottom
    def set_status(self, msg: str) -> None:
        self._status.setText(msg or "")

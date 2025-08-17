# ui_renderer.py
from __future__ import annotations
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QTextBrowser, QVBoxLayout, QStackedLayout, QSizePolicy
)

class ConversationWindow(QMainWindow):
    def __init__(self, title: str, background_path: str, ui_cfg: dict) -> None:
        print(f"[DEBUG] ConversationWindow.__init__ called with title={title}, background_path={background_path}")
        super().__init__()
        self.setWindowTitle(title)

        # Size from config (defaults if missing)
        width = int(ui_cfg.get("screen_width", 1000))
        height = int(ui_cfg.get("screen_height", 700))
        print(f"[DEBUG] Setting window size to {width}x{height}")
        self.resize(width, height)

        # --- Background layer ---
        self._bg_label = QLabel()
        self._bg_label.setAlignment(Qt.AlignCenter)
        self._bg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Centered white rounded rectangle for text ---
        self._text = QTextBrowser()
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)
        self._text.setAttribute(Qt.WA_StyledBackground, True)  # ensure stylesheet background paints
        self._text.setAutoFillBackground(True)

        opacity = float(ui_cfg.get("text_box_opacity", 0.92))
        alpha = int(opacity * 255)
        rounding = int(ui_cfg.get("text_box_rounding", 16))
        print(f"[DEBUG] Text box style: opacity={opacity}, alpha255={alpha}, rounding={rounding}")
        self._text.setStyleSheet(
            "QTextBrowser {"
            f"  background-color: rgba(255,255,255,{alpha});"
            f"  border-radius: {rounding}px;"
            "  padding: 16px;"
            "  border: 2px solid rgba(0,0,0,60);"
            "}"
        )
        font = QFont(
            ui_cfg.get("font_family", "DejaVu Sans"),
            int(ui_cfg.get("font_point_size", 12))
        )
        self._text.setFont(font)

        # Keep visible even before content arrives
        self._text.setMinimumWidth(int(width * 0.5))
        self._text.setMaximumWidth(int(width * 0.85))
        self._text.setMinimumHeight(int(height * 0.3))
        self._text.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # --- Status bar at bottom ---
        self._status_label = QLabel("Ready")
        s_font = QFont(
            ui_cfg.get("font_family", "DejaVu Sans"),
            int(ui_cfg.get("status_font_point_size", ui_cfg.get("font_point_size", 10)))
        )
        self._status_label.setFont(s_font)
        s_opacity = float(ui_cfg.get("status_opacity", 0.8))
        s_alpha = int(s_opacity * 255)
        self._status_label.setStyleSheet(
            f"QLabel {{ background-color: rgba(0,0,0,{s_alpha}); color: white; padding: 4px; }}"
        )

        # --- Build layered layout: background + centered text overlay ---
        margin = int(ui_cfg.get("text_box_margin", 24))
        print(f"[DEBUG] Layout margins set to {margin}")

        self._stacked_host = QWidget()
        self._stacked = QStackedLayout(self._stacked_host)
        self._stacked.setStackingMode(QStackedLayout.StackAll)
        self._stacked.addWidget(self._bg_label)  # layer 0

        self._overlay = QWidget()  # layer 1
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay_layout = QVBoxLayout(self._overlay)
        overlay_layout.setContentsMargins(margin, margin, margin, margin)
        overlay_layout.addStretch(1)
        overlay_layout.addWidget(self._text, 0, Qt.AlignHCenter | Qt.AlignVCenter)
        overlay_layout.addStretch(1)
        self._stacked.addWidget(self._overlay)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stacked_host, 1)
        outer.addWidget(self._status_label, 0)
        self.setCentralWidget(container)

        # Ensure overlay is atop background
        self._overlay.raise_()
        self._text.raise_()

        # Initialize background
        self._background_path = background_path
        print(f"[DEBUG] Initializing background with path: {self._background_path}")
        self._pixmap = QPixmap(self._background_path)
        if self._pixmap.isNull():
            print("[DEBUG] Initial QPixmap is NULL — background not found")
        else:
            print("[DEBUG] Initial QPixmap loaded successfully")
        self._bg_label.installEventFilter(self)
        self._update_background()

    # Fire once the window is shown to dump sizes
    def showEvent(self, event):
        super().showEvent(event)
        print("[DEBUG] showEvent fired; scheduling geometry dump")
        QTimer.singleShot(0, self._dump_layout_metrics)

    # Also log on every resize to confirm sizes
    def resizeEvent(self, event):
        super().resizeEvent(event)
        size = event.size()
        print(f"[DEBUG] resizeEvent: window now {size.width()}x{size.height()}")

    def _dump_layout_metrics(self):
        print(
            f"[DEBUG] Geometries — window={self.size().width()}x{self.size().height()}, "
            f"bg_label={self._bg_label.size().width()}x{self._bg_label.size().height()}, "
            f"text={self._text.size().width()}x{self._text.size().height()}"
        )

    def eventFilter(self, obj, event):
        if obj is self._bg_label and event.type() == event.Resize:
            print("[DEBUG] Background label resize event, updating background")
            self._update_background()
        return super().eventFilter(obj, event)

    def _update_background(self):
        print(f"[DEBUG] Updating background from path: {self._background_path}")
        if self._pixmap.isNull():
            print("[DEBUG] QPixmap is NULL during update — showing fallback text")
            self._bg_label.setText("(background not found)")
            return
        size = self._bg_label.size()
        print(f"[DEBUG] Background label size: {size.width()}x{size.height()}")
        if size.width() <= 0 or size.height() <= 0:
            print("[DEBUG] Background label size is zero — skipping update")
            return
        scaled = self._pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._bg_label.setPixmap(scaled)
        print("[DEBUG] Background pixmap applied")
        # Re-assert overlay on top after background changes
        self._overlay.raise_()
        self._text.raise_()

    def set_background(self, path: str) -> None:
        print(f"[DEBUG] set_background called with path: {path}")
        self._background_path = path
        self._pixmap = QPixmap(self._background_path)
        if self._pixmap.isNull():
            print("[DEBUG] New QPixmap is NULL — background not found")
        else:
            print("[DEBUG] New QPixmap loaded successfully")
        self._update_background()

    def display_text(self, html_or_text: str) -> None:
        print(f"[DEBUG] display_text called with text length={len(html_or_text)}")
        self._text.setPlainText(html_or_text)

    def show_status(self, message: str) -> None:
        print(f"[DEBUG] show_status: {message}")
        self._status_label.setText(message)
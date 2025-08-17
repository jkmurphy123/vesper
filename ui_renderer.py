# ui_renderer.py
from __future__ import annotations
from typing import Optional, Dict
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QTextBrowser, QVBoxLayout, QStackedLayout, QSizePolicy
)

class ConversationWindow(QMainWindow):
    def __init__(self, title: str, background_path: str, ui_cfg: dict,
                 balloon_cfg: Optional[Dict[str, int]] = None,
                 design_size: Optional[Dict[str, int]] = None) -> None:
        print(f"[DEBUG] ConversationWindow.__init__ title={title}, background_path={background_path}")
        super().__init__()
        self.setWindowTitle(title)

        # Base (design) size used for scaling speech balloon coordinates
        self._design_w = int((design_size or {}).get("screen_width", ui_cfg.get("screen_width", 1000)))
        self._design_h = int((design_size or {}).get("screen_height", ui_cfg.get("screen_height", 700)))

        width = int(ui_cfg.get("screen_width", 1000))
        height = int(ui_cfg.get("screen_height", 700))
        print(f"[DEBUG] Setting window size to {width}x{height} (design {self._design_w}x{self._design_h})")
        self.resize(width, height)

        # --- Background layer ---
        self._bg_label = QLabel()
        self._bg_label.setAlignment(Qt.AlignCenter)
        self._bg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Overlay (absolute) for the balloon ---
        self._overlay = QWidget()
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._overlay.setAttribute(Qt.WA_StyledBackground, False)

        # The text widget (white rounded rectangle)
        self._text = QTextBrowser(self._overlay)  # child of overlay so we can place absolutely
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)
        self._text.setAttribute(Qt.WA_StyledBackground, True)
        self._text.setAutoFillBackground(True)

        opacity = float(ui_cfg.get("text_box_opacity", 0.92))
        alpha = int(opacity * 255)
        rounding = int(ui_cfg.get("text_box_rounding", 16))
        self._text.setStyleSheet(
            "QTextBrowser {"
            f"  background-color: rgba(255,255,255,{alpha});"
            f"  border-radius: {rounding}px;"
            "  padding: 16px;"
            "  border: 2px solid rgba(0,0,0,60);"
            "}"
        )
        font = QFont(ui_cfg.get("font_family", "DejaVu Sans"), int(ui_cfg.get("font_point_size", 12)))
        self._text.setFont(font)

        # Save balloon config (design-space coords)
        self._balloon = balloon_cfg or {"x_pos": 100, "y_pos": 100, "width": int(width * 0.6), "height": int(height * 0.4)}

        # --- Status bar ---
        self._status_label = QLabel("Ready")
        s_font = QFont(ui_cfg.get("font_family", "DejaVu Sans"), int(ui_cfg.get("status_font_point_size", ui_cfg.get("font_point_size", 10))))
        self._status_label.setFont(s_font)
        s_alpha = int(float(ui_cfg.get("status_opacity", 0.8)) * 255)
        self._status_label.setStyleSheet(f"QLabel {{ background-color: rgba(0,0,0,{s_alpha}); color: white; padding: 4px; }}")

        # --- Build layered layout ---
        self._stacked_host = QWidget()
        self._stacked = QStackedLayout(self._stacked_host)
        self._stacked.setStackingMode(QStackedLayout.StackAll)
        self._stacked.addWidget(self._bg_label)   # layer 0
        self._stacked.addWidget(self._overlay)    # layer 1

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stacked_host, 1)
        outer.addWidget(self._status_label, 0)
        self.setCentralWidget(container)

        # Initialize background
        self._background_path = background_path
        self._pixmap = QPixmap(self._background_path)
        print(f"[DEBUG] Background path={self._background_path}, pixmapNull={self._pixmap.isNull()}")
        self._bg_label.installEventFilter(self)
        self._update_background()

    def _apply_balloon_geometry(self):
        # Scale from design-space to current window space
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        sx = w / float(self._design_w)
        sy = h / float(self._design_h)
        bx = int(self._balloon.get("x_pos", 0) * sx)
        by = int(self._balloon.get("y_pos", 0) * sy)
        bw = int(self._balloon.get("width", 300) * sx)
        bh = int(self._balloon.get("height", 200) * sy)
        print(f"[DEBUG] Applying balloon geometry (scaled): x={bx}, y={by}, w={bw}, h={bh}, scale=({sx:.2f},{sy:.2f})")
        self._text.setGeometry(bx, by, bw, bh)
        self._text.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_balloon_geometry)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_balloon_geometry()

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
        # Keep overlay above
        self._overlay.raise_()
        self._text.raise_()

    def set_background(self, path: str) -> None:
        self._background_path = path
        self._pixmap = QPixmap(self._background_path)
        self._update_background()

    def display_text(self, html_or_text: str) -> None:
        self._text.setPlainText(html_or_text)

    def show_status(self, message: str) -> None:
        self._status_label.setText(message)
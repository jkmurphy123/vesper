# ui_renderer.py — chunked display with fades + end-of-sequence signal + ESC to quit
from __future__ import annotations
from typing import Optional, Dict, List
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QTextBrowser, QVBoxLayout, QStackedLayout, QSizePolicy,
    QGraphicsOpacityEffect, QApplication
)

class ConversationWindow(QMainWindow):
    # Emitted when the LAST chunk has finished displaying
    chunks_finished = pyqtSignal()

    def __init__(self, title: str, background_path: str, ui_cfg: dict,
                 balloon_cfg: Optional[Dict[str, int]] = None,
                 design_size: Optional[Dict[str, int]] = None) -> None:
        super().__init__()
        self.setWindowTitle(title)

        # Base (design) size for scaling balloon coords
        self._design_w = int((design_size or {}).get("screen_width", ui_cfg.get("screen_width", 1000)))
        self._design_h = int((design_size or {}).get("screen_height", ui_cfg.get("screen_height", 700)))

        width = int(ui_cfg.get("screen_width", 1000))
        height = int(ui_cfg.get("screen_height", 700))
        print(f"[DEBUG] Setting window size to {width}x{height} (design {self._design_w}x{self._design_h})")
        self.resize(width, height)

        # Background
        self._bg_label = QLabel()
        self._bg_label.setAlignment(Qt.AlignCenter)
        self._bg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Overlay
        self._overlay = QWidget()
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._overlay.setAttribute(Qt.WA_StyledBackground, False)

        # Speech balloon (white rounded rect)
        self._text = QTextBrowser(self._overlay)
        self._text.setReadOnly(True)
        self._text.setOpenExternalLinks(True)
        self._text.setAttribute(Qt.WA_StyledBackground, True)
        self._text.setAutoFillBackground(True)
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Fade effect
        self._opacity = QGraphicsOpacityEffect(self._text)
        self._text.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(1.0)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setEasingCurve(QEasingCurve.InOutQuad)
        self._fade.setDuration(800)

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

        # Balloon geometry
        self._balloon = balloon_cfg or {"x_pos": 100, "y_pos": 100, "width": int(width * 0.6), "height": int(height * 0.4)}

        # Status bar
        self._status_label = QLabel("Ready")
        s_font = QFont(ui_cfg.get("font_family", "DejaVu Sans"), int(ui_cfg.get("status_font_point_size", ui_cfg.get("font_point_size", 10))))
        self._status_label.setFont(s_font)
        s_alpha = int(float(ui_cfg.get("status_opacity", 0.8)) * 255)
        self._status_label.setStyleSheet(f"QLabel {{ background-color: rgba(0,0,0,{s_alpha}); color: white; padding: 4px; }}")

        # Layout
        self._stacked_host = QWidget()
        self._stacked = QStackedLayout(self._stacked_host)
        self._stacked.setStackingMode(QStackedLayout.StackAll)
        self._stacked.addWidget(self._bg_label)
        self._stacked.addWidget(self._overlay)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stacked_host, 1)
        outer.addWidget(self._status_label, 0)
        self.setCentralWidget(container)

        # Background init
        self._background_path = background_path
        self._pixmap = QPixmap(self._background_path)
        self._bg_label.installEventFilter(self)
        self._update_background()

        # Chunk playback state
        self._chunks: List[str] = []
        self._chunk_idx = 0
        self._chunk_delay_ms = 30000
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._on_delay_elapsed)

        self._fading_out = False
        self._fade.finished.connect(self._on_fade_finished)

    # --- Geometry helpers ---
    def _apply_balloon_geometry(self):
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        sx = w / float(self._design_w)
        sy = h / float(self._design_h)
        bx = int(self._balloon.get("x_pos", 0) * sx)
        by = int(self._balloon.get("y_pos", 0) * sy)
        bw = int(self._balloon.get("width", 300) * sx)
        bh = int(self._balloon.get("height", 200) * sy)
        self._text.setGeometry(bx, by, bw, bh)
        self._text.raise_()

    def set_balloon(self, balloon_cfg: Dict[str, int], design_size: Dict[str, int]) -> None:
        self._balloon = balloon_cfg or self._balloon
        self._design_w = int(design_size.get("screen_width", self._design_w))
        self._design_h = int(design_size.get("screen_height", self._design_h))
        QTimer.singleShot(0, self._apply_balloon_geometry)

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
        self._overlay.raise_()
        self._text.raise_()

    def set_background(self, path: str) -> None:
        self._background_path = path
        self._pixmap = QPixmap(self._background_path)
        self._update_background()

    def clear_text(self) -> None:
        self._text.clear()
        if self._text.graphicsEffect():
            self._text.graphicsEffect().setOpacity(1.0)

    def display_text(self, html_or_text: str) -> None:
        self._text.setPlainText(html_or_text)

    # === Chunked playback API ===
    def play_chunks(self, chunks: List[str], delay_seconds: int = 30) -> None:
        """Begin showing chunks sequentially. Shows first chunk immediately,
        waits delay_seconds, fades out, swaps text, fades in, repeats.
        """        
        if not chunks:
            # Nothing to show; still notify completion so controller can loop
            self.chunks_finished.emit()
            return
        self._chunks = chunks
        self._chunk_idx = 0
        self._chunk_delay_ms = max(1, delay_seconds) * 1000
        self._opacity.setOpacity(1.0)
        self._text.setPlainText(self._chunks[self._chunk_idx])
        self._delay_timer.start(self._chunk_delay_ms)
        print(f"[DEBUG] play_chunks: total={len(chunks)} delay={delay_seconds}s")

    def _on_delay_elapsed(self):
        self._fading_out = True
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self):
        if self._fading_out:
            self._chunk_idx += 1
            if self._chunk_idx >= len(self._chunks):
                self.chunks_finished.emit()
                return
            self._text.setPlainText(self._chunks[self._chunk_idx])
            self._fading_out = False
            self._fade.stop()
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.start()
        else:
            if self._chunk_idx < len(self._chunks) - 1:
                self._delay_timer.start(self._chunk_delay_ms)

    # ESC quits
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.quit()
        else:
            super().keyPressEvent(event)

    def show_status(self, message: str) -> None:
        self._status_label.setText(message)

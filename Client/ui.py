"""
ui.py — Gesamte UI-Schicht für den P2P-Client (Discord-Stil)
  - STYLESHEET          globales QSS
  - CircularSystemButton schöne runde Steuertasten (Min, Max/Fullscreen, Close)
  - ResizeGrip          unsichtbare Anfasser für alle Ränder (8-Wege)
  - PulseDot            animierter Status-Punkt
  - AvatarLabel         farbiger Kreis-Avatar (QPainter)
  - DraggableTitleBar   frameless Fenster verschieben + Systemtasten
  - RoundedContainer    abgerundete Ecken via QPainter
  - TextMessageCard     Discord-Stil Chat-Nachricht
  - FileMessageCard     Datei-Karte mit Download-Button
  - ChatArea            scrollbarer Karten-Container
  - P2PClientWindow     Haupt-Fenster des Clients
"""

import json
import time
import datetime
import pyperclip

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QLineEdit, QPushButton, QLabel, QFrame,
    QMessageBox, QScrollArea, QFileDialog, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, QEvent
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont

from General.constants import (
    C_BG_DARKEST, C_BG_DARK, C_BG_MAIN, C_BG_INPUT, C_BG_HOVER, C_BORDER,
    C_BLURPLE, C_BLURPLE_D, C_GREEN, C_YELLOW, C_RED,
    C_TEXT_PRI, C_TEXT_SEC, C_TEXT_MUT, C_TEXT_WHITE,
    C_HOST_COL, C_USER_COL, C_SYS_COL,
)
from backend import AsyncBridge
import General.file_transfer as ft

RADIUS = 12
SHADOW = 18
FONT_STACK = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

# ════════════════════════════════════════════════════════════
# Globales Stylesheet
# ════════════════════════════════════════════════════════════
STYLESHEET = f"""
* {{
    font-family: {FONT_STACK};
    font-size: 13px;
    color: {C_TEXT_PRI};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: #1a1b1e;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: #111214; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical,  QScrollBar::sub-page:vertical {{ background: none; }}
QLineEdit {{
    background-color: {C_BG_INPUT};
    color: {C_TEXT_PRI};
    border: none;
    border-radius: 8px;
    padding: 11px 14px;
    font-size: 14px;
    selection-background-color: {C_BLURPLE_D};
}}
QPushButton {{
    background-color: transparent;
    color: {C_TEXT_SEC};
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {C_BG_HOVER};
    color: {C_TEXT_PRI};
}}
QPushButton#btn_connect {{
    background-color: {C_BLURPLE};
    color: {C_TEXT_WHITE};
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#btn_connect:hover    {{ background-color: {C_BLURPLE_D}; }}
QPushButton#btn_connect:disabled {{
    background-color: {C_BLURPLE_D};
    color: rgba(255,255,255,0.4);
}}
QPushButton#btn_send {{
    background-color: {C_BLURPLE};
    color: {C_TEXT_WHITE};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 700;
}}
QPushButton#btn_send:hover {{ background-color: {C_BLURPLE_D}; }}
QToolTip {{
    background-color: {C_BG_DARKEST};
    color: {C_TEXT_PRI};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""


# ════════════════════════════════════════════════════════════
# CircularSystemButton
# ════════════════════════════════════════════════════════════
class CircularSystemButton(QPushButton):
    """Ein perfekt runder System-Button mit permanentem Hintergrund und Hover-Effekt."""

    def __init__(self, text: str, tooltip: str, default_bg: str, hover_bg: str, press_bg: str, callback,
                 parent=None) -> None:
        super().__init__(text, parent)
        self.setFixedSize(24, 24)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(callback)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {default_bg};
                color: {C_TEXT_WHITE};
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background: {hover_bg};
            }}
            QPushButton:pressed {{
                background: {press_bg};
            }}
        """)


# ════════════════════════════════════════════════════════════
# ResizeGrip
# ════════════════════════════════════════════════════════════
class ResizeGrip(QWidget):
    """Legt sich unsichtbar an die Ränder und reicht das Ziehen an das Betriebssystem weiter."""

    def __init__(self, parent, edges: Qt.Edge) -> None:
        super().__init__(parent)
        self.edges = edges
        self.setCursor(self._get_cursor())
        self.setStyleSheet("background: transparent;")

    def _get_cursor(self) -> Qt.CursorShape:
        if self.edges in (Qt.Edge.TopEdge | Qt.Edge.LeftEdge, Qt.Edge.BottomEdge | Qt.Edge.RightEdge):
            return Qt.CursorShape.SizeFDiagCursor
        elif self.edges in (Qt.Edge.TopEdge | Qt.Edge.RightEdge, Qt.Edge.BottomEdge | Qt.Edge.LeftEdge):
            return Qt.CursorShape.SizeBDiagCursor
        elif self.edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            return Qt.CursorShape.SizeHorCursor
        else:
            return Qt.CursorShape.SizeVerCursor

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            window_handle = self.window().windowHandle()
            if window_handle:
                window_handle.startSystemResize(self.edges)
        event.ignore()


# ════════════════════════════════════════════════════════════
# PulseDot
# ════════════════════════════════════════════════════════════
class PulseDot(QWidget):
    def __init__(self, color: str = C_GREEN, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor(color)
        self._alpha = 1.0
        self._shrinking = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def _tick(self) -> None:
        step = 0.022
        if self._shrinking:
            self._alpha = max(0.3, self._alpha - step)
            if self._alpha <= 0.3:
                self._shrinking = False
        else:
            self._alpha = min(1.0, self._alpha + step)
            if self._alpha >= 1.0:
                self._shrinking = True
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        c.setAlphaF(self._alpha)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 10, 10)


# ════════════════════════════════════════════════════════════
# AvatarLabel
# ════════════════════════════════════════════════════════════
class AvatarLabel(QWidget):
    def __init__(self, initial: str, color: str, size: int = 36, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._initial = initial.upper()
        self._color = QColor(color)
        self._size = size

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, self._size, self._size)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", int(self._size * 0.38), QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)


# ════════════════════════════════════════════════════════════
# DraggableTitleBar
# ════════════════════════════════════════════════════════════
class DraggableTitleBar(QWidget):
    def __init__(self, window: QMainWindow, parent=None) -> None:
        super().__init__(parent)
        self._window = window
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(48)
        self.setStyleSheet(f"background: {C_BG_DARKEST}; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(0)

        icon = QLabel("◈")
        icon.setStyleSheet(f"color:{C_BLURPLE}; font-size:18px; background:transparent;")
        layout.addWidget(icon)
        layout.addSpacing(8)

        self.title_label = QLabel("P2P Client")
        self.title_label.setStyleSheet(f"color:{C_TEXT_PRI}; font-size:14px; font-weight:600; background:transparent;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.status_dot = PulseDot(C_TEXT_MUT)
        layout.addWidget(self.status_dot)
        layout.addSpacing(6)

        self.status_lbl = QLabel("Offline")
        self.status_lbl.setStyleSheet(
            f"color:{C_TEXT_MUT}; font-size:12px; font-weight:600; background:transparent; margin-right:16px;"
        )
        layout.addWidget(self.status_lbl)

        self.count_badge = QLabel("  0 Clients  ")
        self.count_badge.setStyleSheet(f"""
            color: {C_TEXT_MUT};
            background: {C_BG_DARK};
            border-radius: 10px;
            padding: 2px 0;
            font-size: 12px;
            font-weight: 600;
        """)
        layout.addWidget(self.count_badge)

        layout.addSpacing(14)

        self.btn_min = CircularSystemButton("−", "Minimieren", C_YELLOW, "#FEE75C", "#C97D10",
                                            self._window.showMinimized)
        self.btn_max = CircularSystemButton("▢", "Maximieren", C_GREEN, "#57F287", "#1F8B4C", self._toggle_maximize)
        self.btn_close = CircularSystemButton("✕", "Schließen", C_RED, "#FF4F52", "#C0392B", self._window.close)

        layout.addWidget(self.btn_min)
        layout.addSpacing(4)
        layout.addWidget(self.btn_max)
        layout.addSpacing(4)
        layout.addWidget(self.btn_close)

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
            self.btn_max.setText("▢")
            self.btn_max.setToolTip("Maximieren")
        else:
            self._window.showMaximized()
            self.btn_max.setText("⧉")
            self.btn_max.setToolTip("Wiederherstellen")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._window.isMaximized():
            self._drag_pos = (
                    event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos and not self._window.isMaximized():
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _) -> None:
        self._drag_pos = None


# ════════════════════════════════════════════════════════════
# RoundedContainer
# ════════════════════════════════════════════════════════════
class RoundedContainer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.radius = RADIUS
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
        p.fillPath(path, QColor(C_BG_MAIN))


# ════════════════════════════════════════════════════════════
# TextMessageCard
# ════════════════════════════════════════════════════════════
class TextMessageCard(QWidget):
    _SENDER_CFG = {
        "HOST": (C_HOST_COL, "Host", "H"),
        "USER": (C_USER_COL, "User", "U"),
        "SYSTEM": (C_SYS_COL, "System", "S"),
    }

    def __init__(self, sender: str, text: str, timestamp: str, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        color, name, initial = self._SENDER_CFG.get(sender, (C_TEXT_MUT, sender, "?"))
        self._build(sender, text, timestamp, color, name, initial)

    def _build(self, sender, text, timestamp, color, name, initial) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 4, 16, 4)
        outer.setSpacing(0)

        if sender == "SYSTEM":
            lbl = QLabel(f"── {text} ──")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color:{C_SYS_COL}; font-size:11px; font-style:italic; background:transparent;"
            )
            outer.addWidget(lbl)
            return

        outer.addWidget(AvatarLabel(initial, color, 36))
        outer.addSpacing(12)

        right = QWidget()
        right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(0)
        n_lbl = QLabel(name)
        n_lbl.setStyleSheet(
            f"color:{color}; font-weight:700; font-size:14px; background:transparent;"
        )
        ts_lbl = QLabel(f"  heute um {timestamp}")
        ts_lbl.setStyleSheet(
            f"color:{C_TEXT_MUT}; font-size:10px; background:transparent;"
        )
        header.addWidget(n_lbl)
        header.addWidget(ts_lbl)
        header.addStretch()
        rv.addLayout(header)

        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        msg_lbl.setStyleSheet(
            f"color:{C_TEXT_PRI}; font-size:13px; background:transparent; line-height:1.4;"
        )
        rv.addWidget(msg_lbl)

        outer.addWidget(right, stretch=1)


# ════════════════════════════════════════════════════════════
# FileMessageCard
# ════════════════════════════════════════════════════════════
class FileMessageCard(QWidget):
    _SENDER_CFG = {
        "HOST": (C_HOST_COL, "Host", "H"),
        "USER": (C_USER_COL, "User", "U"),
    }

    def __init__(self, sender: str, filename: str, size: int, file_data: bytes, timestamp: str, parent=None) -> None:
        super().__init__(parent)
        self._filename = filename
        self._size = size
        self._file_data = file_data
        self.setStyleSheet("background: transparent;")

        color, name, initial = self._SENDER_CFG.get(sender, (C_TEXT_MUT, sender, "?"))
        self._build(color, name, initial, timestamp)

    def _build(self, color, name, initial, timestamp) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 6, 16, 6)
        outer.setSpacing(0)

        outer.addWidget(AvatarLabel(initial, color, 36))
        outer.addSpacing(12)

        right = QWidget()
        right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(0)
        n_lbl = QLabel(name)
        n_lbl.setStyleSheet(
            f"color:{color}; font-weight:700; font-size:14px; background:transparent;"
        )
        ts_lbl = QLabel(f"  heute um {timestamp}")
        ts_lbl.setStyleSheet(
            f"color:{C_TEXT_MUT}; font-size:10px; background:transparent;"
        )
        header.addWidget(n_lbl)
        header.addWidget(ts_lbl)
        header.addStretch()
        rv.addLayout(header)

        rv.addWidget(self._build_file_card())
        outer.addWidget(right, stretch=1)

    def _build_file_card(self) -> QWidget:
        card = QWidget()
        card.setMaximumWidth(420)
        card.setStyleSheet(f"""
            QWidget#filecard {{
                background: {C_BG_DARK};
                border: 1px solid {C_BG_DARKEST};
                border-radius: 8px;
            }}
        """)
        card.setObjectName("filecard")

        cl = QHBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(12)

        icon = QLabel("📄")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:26px; background:transparent; border:none;")
        cl.addWidget(icon)

        info = QWidget()
        info.setStyleSheet("background:transparent; border:none;")
        iv = QVBoxLayout(info)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(2)

        display_name = self._filename[:34] + "…" if len(self._filename) > 35 else self._filename
        fn_lbl = QLabel(display_name)
        fn_lbl.setStyleSheet(
            f"color:{C_TEXT_PRI}; font-size:13px; font-weight:600; background:transparent; border:none;")
        fn_lbl.setToolTip(self._filename)

        sz_lbl = QLabel(ft.format_size(self._size))
        sz_lbl.setStyleSheet(f"color:{C_TEXT_MUT}; font-size:11px; background:transparent; border:none;")

        iv.addWidget(fn_lbl)
        iv.addWidget(sz_lbl)
        cl.addWidget(info, stretch=1)

        dl_btn = QPushButton("⬇  Herunterladen")
        dl_btn.setFixedHeight(34)
        dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_btn.clicked.connect(self._on_download)
        dl_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_BLURPLE};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover   {{ background: {C_BLURPLE_D}; }}
            QPushButton:pressed {{ background: #3c45a5; }}
        """)
        cl.addWidget(dl_btn)

        return card

    def _on_download(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Datei speichern unter …", self._filename, "Alle Dateien (*.*)")
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(self._file_data)
        except Exception as exc:
            QMessageBox.critical(self, "Speicherfehler", str(exc))


# ════════════════════════════════════════════════════════════
# ChatArea
# ════════════════════════════════════════════════════════════
class ChatArea(QScrollArea):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"background:{C_BG_MAIN}; border:none;")

        self._content = QWidget()
        self._content.setStyleSheet(f"background:{C_BG_MAIN};")

        self._vb = QVBoxLayout(self._content)
        self._vb.setContentsMargins(0, 16, 0, 16)
        self._vb.setSpacing(2)
        self._vb.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._vb.addStretch()

        self.setWidget(self._content)

    def add_text(self, sender: str, text: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M")
        self._insert(TextMessageCard(sender, text, ts))

    def add_file(self, sender: str, filename: str, size: int, data: bytes) -> None:
        ts = datetime.datetime.now().strftime("%H:%M")
        self._insert(FileMessageCard(sender, filename, size, data, ts))

    def _insert(self, widget: QWidget) -> None:
        sb = self.verticalScrollBar()
        was_at_bottom = sb.value() >= sb.maximum() - 20

        stretch = self._vb.takeAt(self._vb.count() - 1)
        self._vb.addWidget(widget)
        self._vb.addItem(stretch)

        if was_at_bottom:
            QTimer.singleShot(30, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


# ════════════════════════════════════════════════════════════
# P2PClientWindow
# ════════════════════════════════════════════════════════════
class P2PClientWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.start_time = time.time()
        self.bridge = AsyncBridge()
        self._connect_signals()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_window()
        self._build_ui()
        self._create_resize_grips()
        self._start_timers()

        self.bridge.sig_log.emit("SYSTEM", "Client gestartet — warte auf Verbindungsaufbau.")

    def _connect_signals(self) -> None:
        self.bridge.sig_log.connect(self._on_log)
        self.bridge.sig_connected.connect(self._on_connected)
        self.bridge.sig_disconnected.connect(self._on_disconnected)
        self.bridge.sig_offer_ready.connect(self._on_offer_ready)
        self.bridge.sig_file_received.connect(self._on_file_received)
        self.bridge.sig_error.connect(lambda msg: QMessageBox.critical(self, "Fehler", msg))

    def _setup_window(self) -> None:
        self.setWindowTitle("P2P Client")
        self.resize(940 + SHADOW * 2, 680 + SHADOW * 2)
        self.setMinimumSize(700, 520)
        self.setStyleSheet(STYLESHEET)

    def _build_ui(self) -> None:
        outer = QWidget()
        outer.setStyleSheet("background:transparent;")
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(SHADOW, SHADOW, SHADOW, SHADOW)
        ol.setSpacing(0)
        self.setCentralWidget(outer)

        self.container = RoundedContainer()
        ol.addWidget(self.container)

        root = QVBoxLayout(self.container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = DraggableTitleBar(self)
        self.titlebar.title_label.setText("P2P Client")
        self.titlebar.count_badge.hide()
        self.titlebar.status_lbl.setText("Offline")
        self.titlebar.status_lbl.setStyleSheet(f"color:{C_TEXT_MUT}; font-size:12px; font-weight:600;")
        self.titlebar.status_dot.set_color(C_TEXT_MUT)
        root.addWidget(self.titlebar)

        body = QWidget()
        body.setStyleSheet(f"background:{C_BG_MAIN};")
        bh = QHBoxLayout(body)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(0)

        bh.addWidget(self._build_sidebar())
        bh.addWidget(self._build_chat_area(), stretch=1)
        root.addWidget(body, stretch=1)

        root.addWidget(self._build_input_area())

    def _build_sidebar(self) -> QWidget:
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(220)
        self.sidebar_widget.setStyleSheet(f"background:{C_BG_DARK};")

        vb = QVBoxLayout(self.sidebar_widget)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(48)
        hdr.setStyleSheet(f"background:{C_BG_DARK}; border-bottom:1px solid {C_BG_DARKEST};")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(16, 0, 16, 0)
        hh.addWidget(self._lbl("#", f"color:{C_TEXT_MUT}; font-size:18px; font-weight:900;"))
        hh.addSpacing(6)
        hh.addWidget(self._lbl("p2p-general", f"color:{C_TEXT_PRI}; font-size:14px; font-weight:700;"))
        hh.addStretch()
        vb.addWidget(hdr)

        self._sidebar_vb = QVBoxLayout()
        self._sidebar_vb.setContentsMargins(8, 12, 8, 12)
        self._sidebar_vb.setSpacing(2)

        self._sidebar_vb.addWidget(
            self._lbl("VERBINDUNG", f"color:{C_TEXT_MUT}; font-size:10px; font-weight:700; padding:4px 8px 6px 8px;"))

        self.host_row = self._client_row("Host-Server", C_HOST_COL)
        self.host_row.hide()
        self._sidebar_vb.addWidget(self.host_row)

        self._sidebar_vb.addSpacing(16)
        self._sidebar_vb.addWidget(
            self._lbl("CLIENT INFO", f"color:{C_TEXT_MUT}; font-size:10px; font-weight:700; padding:4px 8px 6px 8px;"))
        self.uptime_val = self._stat_row("Uptime")

        vb.addLayout(self._sidebar_vb)
        vb.addStretch()

        self_row = QWidget()
        self_row.setFixedHeight(52)
        self_row.setStyleSheet(f"background:{C_BG_DARKEST};")
        sr = QHBoxLayout(self_row)
        sr.setContentsMargins(10, 0, 10, 0)
        sr.setSpacing(10)
        sr.addWidget(AvatarLabel("D", C_USER_COL, 32))
        nbl = QVBoxLayout()
        nbl.setContentsMargins(0, 0, 0, 0)
        nbl.setSpacing(0)
        nbl.addWidget(self._lbl("Du (Client)", f"color:{C_TEXT_PRI}; font-size:13px; font-weight:700;"))
        sr.addLayout(nbl)
        sr.addStretch()
        vb.addWidget(self_row)

        return self.sidebar_widget

    def _stat_row(self, key: str) -> QLabel:
        row = QWidget()
        row.setFixedHeight(26)
        row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 0, 8, 0)
        rl.addWidget(self._lbl(key, f"color:{C_TEXT_MUT}; font-size:12px;"))
        rl.addStretch()
        val = self._lbl("—", f"color:{C_TEXT_SEC}; font-size:12px; font-weight:600;")
        rl.addWidget(val)
        self._sidebar_vb.addWidget(row)
        return val

    def _client_row(self, name: str, color: str) -> QWidget:
        row = QWidget()
        row.setFixedHeight(32)
        row.setStyleSheet(f"QWidget {{ background:transparent; border-radius:4px; }}")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 0, 8, 0)
        rl.setSpacing(10)
        rl.addWidget(AvatarLabel(name[0], color, 22))
        rl.addWidget(self._lbl(name, f"color:{C_TEXT_SEC}; font-size:13px; font-weight:500;"))
        rl.addStretch()
        dot = self._lbl("●", f"color:{C_GREEN}; font-size:8px;")
        rl.addWidget(dot)
        return row

    def _build_chat_area(self) -> QWidget:
        area = QWidget()
        area.setStyleSheet(f"background:{C_BG_MAIN};")
        vb = QVBoxLayout(area)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)

        ch_hdr = QWidget()
        ch_hdr.setFixedHeight(48)
        ch_hdr.setStyleSheet(f"background:{C_BG_MAIN}; border-bottom:1px solid {C_BG_DARKEST};")
        chh = QHBoxLayout(ch_hdr)
        chh.setContentsMargins(16, 0, 16, 0)
        chh.addWidget(self._lbl("#", f"color:{C_TEXT_MUT}; font-size:18px; font-weight:900;"))
        chh.addSpacing(6)
        chh.addWidget(self._lbl("p2p-general", f"color:{C_TEXT_PRI}; font-size:15px; font-weight:700;"))
        chh.addStretch()
        vb.addWidget(ch_hdr)

        self.chat = ChatArea()
        vb.addWidget(self.chat)
        return area

    def _build_input_area(self) -> QWidget:
        self.input_widget = QWidget()
        self.input_widget.setStyleSheet(
            f"background:{C_BG_MAIN}; border-bottom-left-radius: {RADIUS}px; border-bottom-right-radius: {RADIUS}px;")
        vb = QVBoxLayout(self.input_widget)
        vb.setContentsMargins(16, 8, 16, 16)
        vb.setSpacing(10)

        self.chat_input_container = QWidget()
        self.chat_input_container.setStyleSheet(f"background:{C_BG_INPUT}; border-radius:8px;")
        iw = QHBoxLayout(self.chat_input_container)
        iw.setContentsMargins(4, 4, 4, 4)
        iw.setSpacing(4)

        attach_btn = QPushButton("📎")
        attach_btn.setFixedSize(36, 36)
        attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        attach_btn.clicked.connect(self._on_attach_clicked)
        attach_btn.setStyleSheet(
            f"background:transparent; color:{C_TEXT_MUT}; font-size:18px; border-radius:4px; border:none;")
        iw.addWidget(attach_btn)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Nachricht senden …")
        self.msg_input.setStyleSheet(
            f"background:transparent; border:none; color:{C_TEXT_PRI}; font-size:14px; padding:6px 0;")
        self.msg_input.returnPressed.connect(self._on_send_clicked)
        iw.addWidget(self.msg_input)

        self.send_btn = QPushButton("Senden")
        self.send_btn.setObjectName("btn_send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send_clicked)
        iw.addWidget(self.send_btn)

        vb.addWidget(self.chat_input_container)
        self.chat_input_container.hide()

        self.step_btn = QPushButton("⬡  Schritt 1: Verbindungsanfrage generieren (Offer)")
        self.step_btn.setObjectName("btn_connect")
        self.step_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.step_btn.clicked.connect(self._on_step_btn_clicked)
        vb.addWidget(self.step_btn)

        self.connection_step = 1

        return self.input_widget

    # ── Slots & Logik ────────────────────────────────────────

    def _on_step_btn_clicked(self) -> None:
        if self.connection_step == 1:
            self.step_btn.setEnabled(False)
            self.step_btn.setText("⏳  Generiere Offer …")
            self.bridge.submit(self.bridge.generate_offer())
        elif self.connection_step == 2:
            try:
                answer_dict = json.loads(pyperclip.paste())
                if answer_dict.get("type") != "answer":
                    raise ValueError
                self.step_btn.setEnabled(False)
                self.step_btn.setText("⏳  Verbinde …")
                self.bridge.submit(self.bridge.apply_answer(answer_dict))
            except Exception:
                QMessageBox.critical(self, "Fehler", "Keine gültige Answer in der Zwischenablage!")

    def _on_offer_ready(self) -> None:
        self.connection_step = 2
        self.step_btn.setEnabled(True)
        self.step_btn.setText("⬡  Schritt 2: Answer vom Host aus Zwischenablage einfügen")
        self.step_btn.setStyleSheet(f"background-color: {C_YELLOW}; color: #000;")

    def _on_connected(self) -> None:
        self.titlebar.status_lbl.setText("Verbunden")
        self.titlebar.status_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:12px; font-weight:600;")
        self.titlebar.status_dot.set_color(C_GREEN)
        self.host_row.show()

        self.step_btn.hide()
        self.chat_input_container.show()
        self.msg_input.setFocus()

    def _on_disconnected(self) -> None:
        self.titlebar.status_lbl.setText("Offline")
        self.titlebar.status_lbl.setStyleSheet(f"color:{C_RED}; font-size:12px; font-weight:600;")
        self.titlebar.status_dot.set_color(C_RED)
        self.host_row.hide()

        self.chat_input_container.hide()
        self.step_btn.show()
        self.step_btn.setEnabled(False)
        self.step_btn.setText("Verbindung getrennt. Bitte App neu starten.")
        self.step_btn.setStyleSheet(f"background-color: {C_RED};")

    def _on_log(self, sender: str, message: str) -> None:
        ui_sender = "USER" if sender == "ME" else ("HOST" if sender == "PEER" else "SYSTEM")
        self.chat.add_text(ui_sender, message)

    def _on_file_received(self, sender: str, name: str, size: int, data: bytes) -> None:
        ui_sender = "USER" if sender == "ME" else "HOST"
        self.chat.add_file(ui_sender, name, size, data)

    def _on_send_clicked(self) -> None:
        msg = self.msg_input.text().strip()
        if not msg: return
        self._on_log("ME", msg)
        self.bridge.send_client_message(msg)
        self.msg_input.clear()

    def _on_attach_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Datei zum Senden auswählen", "", "Alle Dateien (*.*)")
        if path:
            self.bridge.submit(self.bridge.send_file(path))

    # ── Ränder & Steuerungslogik (Gleich wie Host) ───────────

    def _create_resize_grips(self) -> None:
        self.grips = {}
        edges = {
            "top": Qt.Edge.TopEdge,
            "bottom": Qt.Edge.BottomEdge,
            "left": Qt.Edge.LeftEdge,
            "right": Qt.Edge.RightEdge,
            "topleft": Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            "topright": Qt.Edge.TopEdge | Qt.Edge.RightEdge,
            "bottomleft": Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
            "bottomright": Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        }
        for name, edge in edges.items():
            self.grips[name] = ResizeGrip(self, edge)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        t = 10
        s = SHADOW

        self.grips["top"].setGeometry(s + t, s - t // 2, w - 2 * (s + t), t)
        self.grips["bottom"].setGeometry(s + t, h - s - t // 2, w - 2 * (s + t), t)
        self.grips["left"].setGeometry(s - t // 2, s + t, t, h - 2 * (s + t))
        self.grips["right"].setGeometry(w - s - t // 2, s + t, t, h - 2 * (s + t))

        self.grips["topleft"].setGeometry(s - t // 2, s - t // 2, t * 2, t * 2)
        self.grips["topright"].setGeometry(int(w - s - t * 1.5), s - t // 2, t * 2, t * 2)
        self.grips["bottomleft"].setGeometry(s - t // 2, int(h - s - t * 1.5), t * 2, t * 2)
        self.grips["bottomright"].setGeometry(int(w - s - t * 1.5), int(h - s - t * 1.5), t * 2, t * 2)

        for grip in self.grips.values():
            grip.raise_()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMaximized():
                self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)
                self.container.radius = 0
                self.titlebar.setStyleSheet(f"background: {C_BG_DARKEST}; border-radius: 0px;")
                if hasattr(self, 'sidebar_widget'):
                    self.sidebar_widget.setStyleSheet(f"background:{C_BG_DARK}; border-radius: 0px;")
                if hasattr(self, 'input_widget'):
                    self.input_widget.setStyleSheet(f"background:{C_BG_MAIN}; border-radius: 0px;")
            else:
                self.centralWidget().layout().setContentsMargins(SHADOW, SHADOW, SHADOW, SHADOW)
                self.container.radius = RADIUS
                self.titlebar.setStyleSheet(
                    f"background: {C_BG_DARKEST}; border-top-left-radius: {RADIUS}px; border-top-right-radius: {RADIUS}px;")
                if hasattr(self, 'sidebar_widget'):
                    self.sidebar_widget.setStyleSheet(f"background:{C_BG_DARK};")
                if hasattr(self, 'input_widget'):
                    self.input_widget.setStyleSheet(
                        f"background:{C_BG_MAIN}; border-bottom-left-radius: {RADIUS}px; border-bottom-right-radius: {RADIUS}px;")
            self.container.update()

    def _start_timers(self) -> None:
        t = QTimer(self)
        t.timeout.connect(self._tick_uptime)
        t.start(1000)

    def _tick_uptime(self) -> None:
        s = int(time.time() - self.start_time)
        h, r = divmod(s, 3600)
        m, s = divmod(r, 60)
        self.uptime_val.setText(f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")

    @staticmethod
    def _lbl(text: str, style: str = "") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background:transparent; {style}")
        return lbl
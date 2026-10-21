"""Design: Schwarz / Rot / Gelb – Widgets und Stylesheet."""
import math
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QConicalGradient, QRadialGradient)
from PySide6.QtWidgets import QFrame, QLabel, QWidget

RED, YEL, BG, PANEL, LINE, TXT, DIM = "#e10600", "#ffc400", "#0a0a0a", "#111111", "#2b2b2b", "#f2f2f2", "#a8a8a8"

QSS = f"""
QWidget {{ background:{BG}; color:{TXT}; font-family:'Segoe UI'; font-size:13px; }}
QLabel {{ background:transparent; }}
QPushButton {{ background:#161616; border:1px solid #333; border-radius:10px; padding:7px 12px; }}
QPushButton:hover {{ border-color:{YEL}; }}
QPushButton:checked {{ border-color:{YEL}; color:{YEL}; }}
QPushButton#primary {{ background:{YEL}; color:#000; border:none; font-weight:600; }}
QPushButton#danger {{ border-color:{RED}; }} QPushButton#danger:hover {{ background:{RED}; color:#fff; }}
QPushButton#nav {{ text-align:left; padding:12px 14px; border:1px solid transparent; border-radius:10px; background:transparent; font-size:15px; }}
QPushButton#nav:hover {{ background:#1a1608; }}
QPushButton#nav:checked {{ background:#3a2f0a; border:1px solid #6b5710; color:{YEL}; }}
QPushButton#send {{ background:{YEL}; color:#000; border:none; border-radius:18px; min-width:36px; max-width:36px; min-height:36px; max-height:36px; font-size:16px; font-weight:700; }}
QPushButton#flat {{ border:none; background:transparent; font-size:18px; padding:4px 8px; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget, QTextBrowser, QSpinBox, QTableWidget {{
    background:#121212; border:1px solid #2f2f2f; border-radius:10px; padding:6px; selection-background-color:{RED}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color:{YEL}; }}
QFrame#grad QLineEdit {{ background:transparent; border:none; font-size:15px; padding:8px 4px; }}
QListWidget::item {{ padding:6px; border-radius:8px; }} QListWidget::item:selected {{ background:#3a2f0a; color:{YEL}; }}
QComboBox QAbstractItemView {{ background:#121212; selection-background-color:{RED}; }}
QFrame#card {{ background:#120e0b; border:1px solid #3b2a12; border-radius:14px; }}
QFrame#card:hover {{ border:1px solid {YEL}; }}
QFrame#panel {{ background:{PANEL}; border:1px solid {LINE}; border-radius:14px; }}
QFrame#panel QFrame#row {{ background:transparent; border:none; border-bottom:1px solid #222; border-radius:0; }}
QGroupBox {{ border:1px solid {LINE}; border-radius:12px; margin-top:14px; padding:14px 10px 10px 10px; font-weight:600; }}
QGroupBox::title {{ subcontrol-origin:margin; left:14px; padding:0 6px; color:{YEL}; }}
QCheckBox::indicator {{ width:18px; height:18px; border-radius:5px; border:1px solid #555; background:#161616; }}
QCheckBox::indicator:checked {{ background:{YEL}; border-color:{YEL}; }}
QSlider::groove:horizontal {{ height:6px; background:#2a2a2a; border-radius:3px; }}
QSlider::sub-page:horizontal {{ background:{RED}; border-radius:3px; }}
QSlider::handle:horizontal {{ background:{YEL}; width:16px; margin:-6px 0; border-radius:8px; }}
QScrollArea {{ border:none; }}
QScrollBar:vertical {{ background:transparent; width:10px; }} QScrollBar::handle:vertical {{ background:#3a3a3a; border-radius:5px; min-height:30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
"""


def label(text, size=13, color=None, bold=False, mono=False):
    l = QLabel(text)
    f = QFont("Consolas" if mono else "Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    if color:
        l.setStyleSheet(f"color:{color}; background:transparent;")
    return l


def circle_icon(text, bg, size=44, fg="#fff"):
    l = QLabel(text)
    l.setFixedSize(size, size)
    l.setAlignment(Qt.AlignCenter)
    l.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:{size // 2}px; font-size:{size // 2 - 2}px;")
    return l


class Clickable(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class GradFrame(QFrame):
    """Rahmen mit Rot→Gelb-Verlauf (wie das Eingabefeld im Entwurf)."""
    def __init__(self):
        super().__init__()
        self.setObjectName("grad")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(RED)); g.setColorAt(1, QColor(YEL))
        p.setPen(QPen(QBrush(g), 2.5)); p.setBrush(QColor("#0d0d0d"))
        p.drawRoundedRect(r, 16, 16)


class LogoRing(QWidget):
    """Logo mit leuchtendem Ring – pulsiert, wenn YAVIS spricht oder zuhört. Klick = Orb-Ansicht."""
    clicked = Signal()

    def __init__(self, size=190):
        super().__init__()
        self.setFixedSize(size, size)
        self.level = self.shown = 0.0
        self.setCursor(Qt.PointingHandCursor)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(33)

    def _tick(self):
        self.shown += (self.level - self.shown) * 0.3
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        R = (min(self.width(), self.height()) / 2 - 14) * (1 + 0.06 * self.shown)

        def grad(a):
            g = QConicalGradient(c, 90)
            g.setColorAt(0, QColor(225, 6, 0, a)); g.setColorAt(0.5, QColor(255, 196, 0, a)); g.setColorAt(1, QColor(225, 6, 0, a))
            return g
        p.setBrush(Qt.NoBrush)
        for w, a in ((14, 22), (8, 45), (4, 90)):
            p.setPen(QPen(QBrush(grad(a)), w)); p.drawEllipse(c, R, R)
        p.setPen(QPen(QBrush(grad(255)), 4)); p.drawEllipse(c, R, R)
        f = QFont("Segoe UI", 20); f.setLetterSpacing(QFont.AbsoluteSpacing, 7)
        p.setFont(f); p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(0, c.y() - 36, self.width(), 40), Qt.AlignCenter, "YAVIS")
        f2 = QFont("Segoe UI", 11)
        p.setFont(f2); p.setPen(QColor(YEL))
        p.drawText(QRectF(0, c.y() + 6, self.width(), 24), Qt.AlignCenter, "lokal · kostenlos")


EMO_STYLE = {"neutral": (YEL, 1.0, 1.0), "freundlich": (YEL, 1.0, 1.1), "lieb": ("#ff9a3c", 0.7, 1.1),
             "froehlich": (YEL, 1.5, 1.3), "traurig": ("#8a6a00", 0.5, 0.7), "boese": (RED, 1.8, 1.4)}


class Orb(QWidget):
    """Großer Kreis in der Mitte: wird größer/kleiner beim Sprechen, Farbe/Tempo zeigen das Gefühl."""
    def __init__(self):
        super().__init__()
        self.level = self.shown = self.t = 0.0
        self.emotion = "neutral"
        self.setMinimumSize(380, 380)
        tm = QTimer(self); tm.timeout.connect(self._tick); tm.start(16)

    def _tick(self):
        self.t += 0.016 * EMO_STYLE[self.emotion][1]
        self.shown += (self.level - self.shown) * 0.25
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        base = min(self.width(), self.height()) * 0.22
        col, _, inten = EMO_STYLE[self.emotion]
        col = QColor(col)
        r = base * (1 + 0.04 * math.sin(self.t * 2) + 0.45 * self.shown * inten)
        for i in range(4, 0, -1):
            ring = QColor(RED if i % 2 else col)
            ring.setAlpha(int(70 / i + 60 * self.shown))
            p.setPen(QPen(ring, 2)); p.setBrush(Qt.NoBrush)
            w = r * (1 + 0.18 * i + 0.05 * math.sin(self.t * (2 + i) + i))
            p.drawEllipse(c, w, w)
        g = QRadialGradient(c, r)
        g.setColorAt(0, col.lighter(130)); g.setColorAt(0.55, col); g.setColorAt(0.85, QColor(RED)); g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawEllipse(c, r, r)
        glow = QRadialGradient(c, r * 2.2)
        gc = QColor(RED); gc.setAlpha(int(40 + 90 * self.shown))
        glow.setColorAt(0.4, gc); glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow); p.drawEllipse(c, r * 2.2, r * 2.2)

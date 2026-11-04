import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class RingTimer(QWidget):
    """A round countdown: dark disc, clock ticks, and a ring that shrinks
    clockwise from 12 o'clock as time runs out."""

    def __init__(self, parent=None, size=240, thickness=12, text_dy=0.0):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._thickness = thickness
        self._text_dy = text_dy  # shifts the text vertically (fraction of size)
        self._progress = 1.0
        self._text = ""
        self._label = ""
        self._color = QColor("#38bdf8")

    def set_state(self, progress: float, text: str, label: str, color: str):
        self._progress = min(1.0, max(0.0, progress))
        self._text = text
        self._label = label
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        c = w / 2
        t = self._thickness

        # background disc
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 23, 42, 240))
        p.drawEllipse(QRectF(1, 1, w - 2, w - 2))

        # ring geometry
        margin = t / 2 + w * 0.04
        rect = QRectF(margin, margin, w - 2 * margin, w - 2 * margin)
        radius = rect.width() / 2

        # clock ticks (every 5th is longer)
        p.save()
        p.translate(c, c)
        tick_start = radius - t / 2 - w * 0.03
        for i in range(60):
            major = i % 5 == 0
            length = w * (0.04 if major else 0.02)
            p.setPen(QPen(QColor("#475569" if major else "#334155"),
                          2 if major else 1))
            p.drawLine(QPointF(0, -tick_start),
                       QPointF(0, -(tick_start - length)))
            p.rotate(6)
        p.restore()

        # track
        pen = QPen(QColor("#1e293b"), t)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(rect)

        # progress arc: starts at 12 o'clock, negative span = clockwise
        if self._progress > 0:
            pen.setColor(self._color)
            p.setPen(pen)
            p.drawArc(rect, 90 * 16, -int(self._progress * 360 * 16))

            # dot at the tip, like a clock hand
            angle = math.radians(90 - self._progress * 360)
            tip = QPointF(c + radius * math.cos(angle),
                          c - radius * math.sin(angle))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#f8fafc"))
            p.drawEllipse(tip, t * 0.5, t * 0.5)

        # time text
        dy = self._text_dy * w
        font = QFont(self.font())
        font.setPixelSize(int(w * 0.2))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#f8fafc"))
        p.drawText(QRectF(0, dy, w, w), Qt.AlignCenter, self._text)

        # label above the time
        font.setPixelSize(max(10, int(w * 0.06)))
        font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(font)
        p.setPen(self._color)
        p.drawText(QRectF(0, dy - w * 0.17, w, w), Qt.AlignCenter, self._label)

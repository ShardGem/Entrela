from PySide6.QtWidgets import (
    QApplication,
    QSplashScreen,
    QLabel,
    QWidget,
    QVBoxLayout,
)

from PySide6.QtCore import (
    Qt,
    QTimer,
    QPointF,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)

from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QLinearGradient,
)

import math
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"


# =========================================================
# Rotating Logo Widget
# =========================================================
class RotatingLogo(QWidget):
    def __init__(self, image_path, size=520, parent=None):
        super().__init__(parent)

        self.pixmap = QPixmap(image_path)

        self._angle = 0
        self.size_value = size

        self.setFixedSize(size, size)

        # Rotação suave infinita
        self.anim = QPropertyAnimation(self, b"angle")

        self.anim.setStartValue(0)
        self.anim.setEndValue(360)

        self.anim.setDuration(22000)

        self.anim.setLoopCount(-1)

        self.anim.setEasingCurve(QEasingCurve.Linear)

        self.anim.start()

    def getAngle(self):
        return self._angle

    def setAngle(self, value):
        self._angle = value
        self.update()

    angle = Property(float, getAngle, setAngle)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.translate(self.width() / 2, self.height() / 2)

        painter.rotate(self._angle)

        painter.drawPixmap(
            -self.size_value // 2,
            -self.size_value // 2,
            self.size_value,
            self.size_value,
            self.pixmap,
        )


# =========================================================
# Animated Quantum Background
# =========================================================
class QuantumBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._offset = 0

        self.animation = QPropertyAnimation(self, b"offset")

        self.animation.setDuration(18000)

        self.animation.setStartValue(0)
        self.animation.setEndValue(360)

        self.animation.setLoopCount(-1)

        self.animation.setEasingCurve(QEasingCurve.Linear)

        self.animation.start()

    def getOffset(self):
        return self._offset

    def setOffset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, getOffset, setOffset)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # =========================================================
        # Background Gradient
        # =========================================================
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())

        gradient.setColorAt(0, QColor("#04060a"))
        gradient.setColorAt(1, QColor("#0a1120"))

        painter.fillRect(rect, gradient)

        # =========================================================
        # Grid
        # =========================================================
        pen = QPen(QColor(255, 255, 255, 7))

        pen.setWidth(1)

        painter.setPen(pen)

        spacing = 50

        for x in range(0, rect.width(), spacing):
            painter.drawLine(x, 0, x, rect.height())

        for y in range(0, rect.height(), spacing):
            painter.drawLine(0, y, rect.width(), y)

        # =========================================================
        # Quantum Particles
        # =========================================================
        center_x = rect.width() / 2
        center_y = rect.height() / 2

        painter.setPen(Qt.NoPen)

        particle_count = 90

        for i in range(particle_count):
            angle = math.radians(self._offset * (0.35 + i * 0.002) + i * 17)

            radius = 120 + (i * 7)

            wave = math.sin(math.radians(self._offset * 2 + i * 9)) * 30

            x = center_x + math.cos(angle) * (radius + wave)

            y = center_y + math.sin(angle) * (radius * 0.35)

            alpha = max(10, 120 - i)

            size = max(1.5, 4 - (i * 0.03))

            painter.setBrush(QColor(88, 214, 255, alpha))

            painter.drawEllipse(QPointF(x, y), size, size)

        # =========================================================
        # Central Glow
        # =========================================================
        glow_radius = 160

        painter.setPen(Qt.NoPen)

        for i in range(8):
            alpha = 18 - i * 2

            painter.setBrush(QColor(88, 214, 255, alpha))

            painter.drawEllipse(
                QPointF(center_x, center_y), glow_radius - i * 18, glow_radius - i * 18
            )


# =========================================================
# Splash Screen
# =========================================================
class SplashScreen(QSplashScreen):
    def __init__(self):

        pixmap = QPixmap(1100, 650)

        pixmap.fill(Qt.transparent)

        super().__init__(pixmap)

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        self.setAttribute(Qt.WA_TranslucentBackground)

        # =========================================================
        # Main Container
        # =========================================================
        self.container = QWidget(self)

        self.container.setGeometry(0, 0, 1100, 650)

        self.container.setStyleSheet("""
            QWidget {
                background-color: #090d14;
                border-radius: 28px;
            }
        """)

        # =========================================================
        # Background
        # =========================================================
        self.bg = QuantumBackground(self.container)

        self.bg.setGeometry(0, 0, 1100, 650)

        # =========================================================
        # Overlay
        # =========================================================
        overlay = QWidget(self.container)

        overlay.setGeometry(0, 0, 1100, 650)

        overlay.setStyleSheet("""
            background: transparent;
        """)

        layout = QVBoxLayout(overlay)

        layout.setContentsMargins(60, 40, 60, 40)

        layout.setSpacing(0)

        layout.addStretch()

        # =========================================================
        # Center Stack
        # =========================================================
        center_container = QWidget()

        center_container.setFixedSize(520, 520)

        center_container.setStyleSheet("""
            background: transparent;
        """)

        # =========================================================
        # Rotating Logo
        # =========================================================
        self.logo = RotatingLogo(
            str(_ASSETS / "entrela_logo.png"), size=520, parent=center_container
        )

        self.logo.move(0, 0)

        # =========================================================
        # Text Overlay
        # =========================================================
        self.text = QLabel(center_container)

        text_pixmap = QPixmap(str(_ASSETS / "entrela_texto.png"))

        self.text.setPixmap(
            text_pixmap.scaled(520, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        self.text.setFixedSize(520, 520)

        self.text.setAlignment(Qt.AlignCenter)

        self.text.setStyleSheet("""
            background: transparent;
        """)

        self.text.move(0, 0)

        self.text.raise_()

        # =========================================================
        # Add Center
        # =========================================================
        layout.addWidget(center_container, alignment=Qt.AlignCenter)

        layout.addStretch()

        # =========================================================
        # Loading Text
        # =========================================================
        self.loading = QLabel("Inicializando área de trabalho...")

        self.loading.setAlignment(Qt.AlignCenter)

        self.loading.setStyleSheet("""
            QLabel {
                color: #58d6ff;
                font-size: 12px;
                font-family: Inter;
                letter-spacing: 2px;
                background: transparent;
                margin-bottom: 10px;
            }
        """)

        layout.addWidget(self.loading)

        # =========================================================
        # Fade In PRA FICAR ESCURO AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASLOUFGWE9HF0´3WGVB4EG08HNERW´B´GRIBWEOÚBGFUIYWB´I0BGFPI9UW
        # =========================================================
        supports_opacity = QApplication.platformName() not in ("offscreen", "minimal")
        if supports_opacity:
            self.setWindowOpacity(0)

        self.fade = QPropertyAnimation(self, b"windowOpacity")

        self.fade.setDuration(1800)

        self.fade.setStartValue(0)
        self.fade.setEndValue(1)

        self.fade.setEasingCurve(QEasingCurve.OutCubic)

        if supports_opacity:
            self.fade.start()

    def closeEvent(self, event):
        self.fade.stop()
        self.logo.anim.stop()
        super().closeEvent(event)

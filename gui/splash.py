"""A short startup screen whose budget includes window initialization."""

from PySide6.QtCore import Qt, QTimer, QElapsedTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen, QFrame, QLabel, QVBoxLayout
from gui.branding import application_icon


class SplashScreen(QSplashScreen):
    DURATION_MS = 3000

    def __init__(self):
        pixmap = QPixmap(640, 360)
        pixmap.fill(Qt.transparent)
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(application_icon())
        self._elapsed = QElapsedTimer()
        self._window = None
        self._completion_timer = QTimer(self)
        self._completion_timer.setSingleShot(True)
        self._completion_timer.setTimerType(Qt.PreciseTimer)
        self._completion_timer.timeout.connect(self._complete)
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 640, 360)
        self.container.setStyleSheet('QFrame {background: #0c1420; border: 1px solid #293b50; border-radius: 20px;} QLabel {background: transparent; border: none; color: #e8eef6; font-family: "Segoe UI", sans-serif;}')
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(36, 32, 36, 26)
        layout.setSpacing(12)
        layout.addStretch()
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setPixmap(application_icon().pixmap(112, 112))
        layout.addWidget(self.logo)
        title = QLabel('Entrela')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 32px; font-weight: 600;')
        layout.addWidget(title)
        subtitle = QLabel('Explorar, simular e compreender estados quânticos')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet('font-size: 14px; color: #afc2d8;')
        layout.addWidget(subtitle)
        layout.addStretch()
        self.loading = QLabel('Preparando sua área de trabalho…')
        self.loading.setAlignment(Qt.AlignCenter)
        self.loading.setStyleSheet('font-size: 13px; color: #8ca6c3;')
        layout.addWidget(self.loading)
        self.fade = QPropertyAnimation(self, b'windowOpacity', self)
        self.fade.setDuration(180)
        self.fade.setStartValue(0.)
        self.fade.setEndValue(1.)
        self.fade.setEasingCurve(QEasingCurve.OutCubic)

    def showEvent(self, event):
        if not self._elapsed.isValid():
            self._elapsed.start()
            app = QApplication.instance()
            if app.platformName() not in ('offscreen', 'minimal') and not app.property('entrelaReduceMotion'):
                self.fade.start()
        super().showEvent(event)

    def remaining_ms(self):
        return max(0, self.DURATION_MS - self._elapsed.elapsed()) if self._elapsed.isValid() else self.DURATION_MS

    def finish_after_minimum(self, window):
        """Finish at the three-second mark, or immediately if startup took longer.

        A blocked GUI thread cannot close the splash before initialization ends;
        the elapsed budget prevents adding another fixed delay after that work.
        """
        self._window = window
        self._completion_timer.start(self.remaining_ms())

    def _complete(self):
        if self.remaining_ms():
            self._completion_timer.start(self.remaining_ms())
            return
        self.stop_animations()
        if self._window is not None:
            self._window.show()
            self.finish(self._window)

    def stop_animations(self):
        self.fade.stop()
        self._completion_timer.stop()

    def closeEvent(self, event):
        self.stop_animations()
        super().closeEvent(event)

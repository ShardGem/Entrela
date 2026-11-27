"""A abertura original conserva sua identidade e o ciclo de vida de três segundos."""
from pathlib import Path

import pytest
from PySide6.QtCore import QAbstractAnimation, QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from gui.splash import SplashScreen, RotatingLogo, QuantumBackground


def test_original_splash_assets_and_composition_are_preserved(qt_app):
    splash = SplashScreen()
    try:
        assets = Path(__file__).resolve().parents[1] / "gui" / "assets"
        assert splash.size() == QSize(1100, 650)
        assert splash.container.size() == splash.size()
        assert isinstance(splash.logo, RotatingLogo)
        assert isinstance(splash.bg, QuantumBackground)
        assert splash.logo.size() == QSize(520, 520)
        assert not splash.logo.pixmap.isNull()
        assert splash.logo.pixmap.toImage() == QPixmap(str(assets / "entrela_logo.png")).toImage()
        expected_text = QPixmap(str(assets / "entrela_texto.png")).scaled(
            520, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        assert splash.text.pixmap().toImage() == expected_text.toImage()
        assert splash.loading.text() == "Inicializando área de trabalho..."
        assert splash.DURATION_MS == 3000
    finally:
        splash.close()


@pytest.mark.parametrize("reduce_motion", [False, True])
def test_splash_motion_starts_on_show_respects_preference_and_stops_on_close(qt_app, reduce_motion):
    previous = qt_app.property("entrelaReduceMotion")
    qt_app.setProperty("entrelaReduceMotion", reduce_motion)
    splash = SplashScreen()
    animations = (splash.logo.anim, splash.bg.animation)
    try:
        assert all(animation.state() == QAbstractAnimation.Stopped for animation in animations)
        splash.show()
        qt_app.processEvents()
        expected = QAbstractAnimation.Stopped if reduce_motion else QAbstractAnimation.Running
        assert all(animation.state() == expected for animation in animations)
        assert 0 < splash.remaining_ms() <= 3000
        splash.close()
        assert all(animation.state() == QAbstractAnimation.Stopped for animation in animations)
        assert splash.fade.state() == QAbstractAnimation.Stopped
        assert not splash._completion_timer.isActive()
    finally:
        splash.close()
        qt_app.setProperty("entrelaReduceMotion", previous)


def test_splash_remaining_budget_does_not_add_delay_after_initialization(qt_app):
    class Clock:
        value = 1250
        def isValid(self):
            return True
        def elapsed(self):
            return self.value

    splash = SplashScreen()
    window = QWidget()
    try:
        splash.show()
        splash._elapsed = Clock()
        splash.finish_after_minimum(window)
        assert splash._completion_timer.interval() == 1750
        splash._complete()
        assert not window.isVisible()
        splash._elapsed.value = 3000
        splash._complete()
        assert window.isVisible()
        assert not splash.isVisible()
        assert not splash._completion_timer.isActive()
        assert splash.logo.anim.state() == QAbstractAnimation.Stopped
        assert splash.bg.animation.state() == QAbstractAnimation.Stopped
    finally:
        splash.close()
        window.close()

"""Installed desktop entry point; assets are packaged beside the GUI."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from gui.splash import SplashScreen
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    window = MainWindow()
    QTimer.singleShot(1500, lambda: (splash.finish(window), window.show()))
    return app.exec()

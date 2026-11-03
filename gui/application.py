"""Installed desktop entry point; assets are packaged beside the GUI."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from gui.branding import configure_application_identity
from gui.splash import SplashScreen
from gui.main_window import MainWindow


def main():
    from gui.diagnostics import enable_diagnostics

    enable_diagnostics()
    app = QApplication(sys.argv)
    configure_application_identity(app)
    app.setProperty('entrelaReduceMotion', QSettings('Entrela', 'TCC').value('appearance/reduce_motion', False, type=bool))
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    window = MainWindow()
    splash.finish_after_minimum(window)
    return app.exec()

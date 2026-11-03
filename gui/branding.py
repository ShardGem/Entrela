"""Packaged identity for native windows and desktop taskbars."""

from pathlib import Path
import sys
from PySide6.QtGui import QIcon

ASSETS = Path(__file__).resolve().parent / "assets" / "icons"


def application_icon():
    """Vector icon in Qt with standard multi-resolution native fallbacks."""
    icon = QIcon(str(ASSETS / "entrela.svg"))
    icon.addFile(str(ASSETS / "entrela.ico"))
    return icon


def configure_application_identity(app):
    app.setApplicationName("Entrela")
    app.setOrganizationName("Entrela")
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Entrela.Quantum.Desktop")
        except (AttributeError, OSError):
            pass
    app.setWindowIcon(application_icon())

"""Identidade da página ativa. Os comandos ficam junto à área a que pertencem."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.design_system import LAYOUT


class Topbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PageHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(LAYOUT.page_margin, 16, LAYOUT.page_margin, 12)
        layout.setSpacing(5)

        self.context = QLabel()
        self.context.setObjectName("TopbarBreadcrumb")
        self.context.setTextFormat(Qt.PlainText)
        self.context.setWordWrap(True)
        layout.addWidget(self.context)

        self.title = QLabel()
        self.title.setObjectName("TopbarTitle")
        self.title.setTextFormat(Qt.PlainText)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

    def set_context(self, title, context=""):
        self.title.setText(title)
        self.context.setText(context)
        self.context.setVisible(bool(context))

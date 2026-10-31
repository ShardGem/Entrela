from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame,QHBoxLayout,QVBoxLayout,QLabel,QPushButton
class Topbar(QFrame):
    help_requested=Signal()
    commands_requested=Signal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("Topbar")
        layout=QHBoxLayout(self)
        layout.setContentsMargins(24,8,24,8)
        text=QVBoxLayout()
        self.breadcrumb=QLabel("ENTRELA")
        self.breadcrumb.setObjectName("TopbarBreadcrumb")
        self.title=QLabel("Início")
        self.title.setObjectName("TopbarTitle")
        text.addWidget(self.breadcrumb)
        text.addWidget(self.title)
        layout.addLayout(text,1)
        commands=QPushButton("Buscar · Ctrl+K")
        commands.clicked.connect(self.commands_requested.emit)
        layout.addWidget(commands)
        help_button=QPushButton("? Ajuda")
        help_button.clicked.connect(self.help_requested.emit)
        layout.addWidget(help_button)
    def set_context(self,title,breadcrumb="ENTRELA"):
        self.title.setText(title)
        self.breadcrumb.setText(breadcrumb)

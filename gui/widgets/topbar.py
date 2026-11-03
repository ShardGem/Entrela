from PySide6.QtCore import Signal
from PySide6.QtCore import QSize
from gui.icons import get_icon
from gui.theme import PALETTE
from PySide6.QtWidgets import QFrame,QHBoxLayout,QVBoxLayout,QLabel,QPushButton
class Topbar(QFrame):
    help_requested=Signal()
    commands_requested=Signal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("Topbar")
        layout=QHBoxLayout(self)
        layout.setContentsMargins(24,12,24,12)
        text=QVBoxLayout()
        self.breadcrumb=QLabel("ENTRELA")
        self.breadcrumb.setObjectName("TopbarBreadcrumb")
        self.title=QLabel("Início")
        self.title.setObjectName("TopbarTitle")
        text.addWidget(self.breadcrumb)
        text.addWidget(self.title)
        layout.addLayout(text,1)
        commands=QPushButton("Buscar")
        commands._icon_name='search'
        commands._icon_color=lambda:PALETTE.text_muted
        commands.setIcon(get_icon('search',PALETTE.text_muted))
        commands.setIconSize(QSize(20,20))
        commands.clicked.connect(self.commands_requested.emit)
        layout.addWidget(commands)
        help_button=QPushButton("Ajuda")
        help_button._icon_name='help'
        help_button._icon_color=lambda:PALETTE.text_muted
        help_button.setIcon(get_icon('help',PALETTE.text_muted))
        help_button.setIconSize(QSize(20,20))
        help_button.clicked.connect(self.help_requested.emit)
        layout.addWidget(help_button)
    def set_context(self,title,breadcrumb="ENTRELA"):
        self.title.setText(title)
        self.breadcrumb.setText(breadcrumb)

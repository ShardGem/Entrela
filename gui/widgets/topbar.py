"""Cabeçalho global e contexto da ferramenta, com responsabilidades separadas."""
from PySide6.QtCore import Signal, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from gui.branding import application_icon
from gui.icons import get_icon


class Topbar(QFrame):
    help_requested = Signal()
    commands_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('GlobalHeader')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(12)
        self.logo = QLabel()
        self.logo.setPixmap(application_icon().pixmap(28, 28))
        layout.addWidget(self.logo)
        brand = QLabel('Entrela')
        brand.setObjectName('GlobalBrand')
        layout.addWidget(brand)
        self.product = QLabel('Laboratório de computação quântica')
        self.product.setObjectName('GlobalProduct')
        layout.addWidget(self.product)
        layout.addStretch()
        self.backend = QLabel('Simulador local')
        self.backend.setObjectName('BackendBadge')
        self.backend.setToolTip('As execuções usam Qiskit Aer neste computador. Não são medições de hardware quântico.')
        layout.addWidget(self.backend)
        self.commands = self._action('Buscar', 'search', self.commands_requested)
        self.help_button = self._action('Ajuda', 'help', self.help_requested)
        layout.addWidget(self.commands)
        layout.addWidget(self.help_button)

        self.page_header = QFrame()
        self.page_header.setObjectName('PageHeader')
        context = QVBoxLayout(self.page_header)
        context.setContentsMargins(24, 12, 24, 12)
        context.setSpacing(4)
        self.breadcrumb = QLabel('ENTRELA')
        self.breadcrumb.setObjectName('TopbarBreadcrumb')
        self.title = QLabel('Início')
        self.title.setWordWrap(True)
        self.title.setObjectName('TopbarTitle')
        context.addWidget(self.breadcrumb)
        context.addWidget(self.title)

    def _action(self, text, icon, signal):
        button = QPushButton(text)
        button.setObjectName('GlobalAction')
        button.setAccessibleName(text)
        button.setToolTip(text + (' comandos, ferramentas e conceitos' if icon == 'search' else ' e manual do Entrela'))
        button._icon_name = icon
        button._icon_color = lambda: '#f4f4f4'
        button.setIcon(get_icon(icon, '#f4f4f4'))
        button.setIconSize(QSize(20, 20))
        button.clicked.connect(signal.emit)
        return button

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scale = max(1, self.font().pixelSize() / 15)
        self.product.setVisible(self.width() >= 1220 * scale)
        self.backend.setVisible(self.width() >= 900 * scale)

    def set_context(self, title, breadcrumb='ENTRELA'):
        self.title.setText(title)
        self.breadcrumb.setText(breadcrumb)

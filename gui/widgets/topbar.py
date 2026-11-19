"""Shared global navigation and local context; no scientific state is copied here."""
from PySide6.QtCore import Signal, Qt, QSize, QSignalBlocker
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTabBar, QMenu, QWidget
from gui.branding import application_icon
from gui.icons import get_icon
from gui.theme import PALETTE
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.button import SecondaryButton


class Topbar(QFrame):
    help_requested = Signal()
    commands_requested = Signal()
    destination_requested = Signal(str)
    activity_requested = Signal(int)
    project_area_requested = Signal(int)
    breadcrumb_requested = Signal(str)
    tool_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('GlobalHeader')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)
        self.logo = QLabel()
        self.logo.setPixmap(application_icon().pixmap(28, 28))
        layout.addWidget(self.logo)
        brand = QLabel('Entrela')
        brand.setObjectName('GlobalBrand')
        layout.addWidget(brand)
        self.destinations = {}
        for key, text in [('dashboard', 'Projetos'), ('examples', 'Biblioteca'), ('docs', 'Aprender')]:
            button = QPushButton(text)
            button.setObjectName('GlobalDestination')
            button.setCheckable(True)
            button.setAccessibleName(text)
            button.clicked.connect(lambda _, k=key: self.destination_requested.emit(k))
            self.destinations[key] = button
            layout.addWidget(button)
        layout.addStretch()
        self.product = QLabel(); self.product.hide()  # compatibility with existing appearance/layout hooks
        self.backend = QLabel(); self.backend.hide()
        self.commands = self._action('Buscar', 'search', self.commands_requested)
        self.commands.setToolTip('Buscar ferramentas, projetos, modelos, execuções e conceitos')
        self.preferences = self._action('', 'settings', None)
        self.preferences.setAccessibleName('Preferências')
        self.preferences.setToolTip('Preferências')
        self.preferences.clicked.connect(lambda: self.destination_requested.emit('settings'))
        layout.addWidget(self.commands)
        layout.addWidget(self.preferences)
        self.help_button = self._action('Ajuda', 'help', self.help_requested)

        self.page_header = QFrame()
        self.page_header.setObjectName('PageHeader')
        context = QVBoxLayout(self.page_header)
        context.setContentsMargins(20, 8, 20, 10)
        context.setSpacing(6)
        self.breadcrumb = QLabel()
        self.breadcrumb.hide()
        self.path_row = QWidget()
        self.path_layout = FlowLayout(self.path_row)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(2)
        context.addWidget(self.path_row)
        self.title_row = QWidget()
        row = FlowLayout(self.title_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.title = QLabel('Projetos')
        self.title.setObjectName('TopbarTitle')
        self.title.setWordWrap(True)
        row.addWidget(self.title)
        self.activities = QTabBar()
        self.activities.setObjectName('ActivityTabs')
        self.activities.setAccessibleName('Atividades do experimento')
        self.activities.setDrawBase(False)
        self.activities.setExpanding(False)
        self.activities.setUsesScrollButtons(True)
        for text in ('Preparar', 'Observar', 'Comparar'):
            self.activities.addTab(text)
        self.activities.currentChanged.connect(self.activity_requested)
        row.addWidget(self.activities)
        self.tools = SecondaryButton('Ferramentas', icon='layers')
        menu = QMenu(self.tools)
        for key, label in [('simulation', 'Configurar Hamiltoniano'), ('circuit', 'Editor de circuitos'),
                           ('history', 'Histórico de execuções'), ('analysis', 'Estudos e varreduras'),
                           ('mitigation', 'Mitigação ZNE'), ('comparison', 'Comparar execuções'),
                           ('configurations', 'Configurações salvas'), ('library', 'Anotações da execução'),
                           ('documentation', 'Relatórios e exportações')]:
            menu.addAction(label, lambda k=key: self.tool_requested.emit(k))
        self.tools.setMenu(menu)
        row.addWidget(self.tools)
        row.addWidget(self.help_button)
        context.addWidget(self.title_row)
        self.project_tabs = QTabBar()
        self.project_tabs.setObjectName('ProjectTabs')
        self.project_tabs.setAccessibleName('Áreas do projeto')
        self.project_tabs.setDrawBase(False)
        self.project_tabs.setExpanding(False)
        for label in ('Visão geral', 'Experimentos', 'Caderno', 'Evidências'):
            self.project_tabs.addTab(label)
        self.project_tabs.currentChanged.connect(self.project_area_requested)
        context.addWidget(self.project_tabs)
        self.activities.hide()
        self.project_tabs.hide()

    def _action(self, text, icon, signal):
        button = QPushButton(text)
        button.setObjectName('GlobalAction')
        button.setAccessibleName(text)
        button._icon_name = icon
        button._icon_color = lambda: PALETTE.text
        button.setIcon(get_icon(icon, PALETTE.text))
        button.setIconSize(QSize(20, 20))
        if signal is not None:
            button.clicked.connect(signal.emit)
        return button

    def set_path(self, parts):
        while self.path_layout.count():
            item = self.path_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.breadcrumb.setText(' / '.join(text for text, _ in parts))
        for index, (text, key) in enumerate(parts):
            if index:
                label = QLabel(' / '); label.setObjectName('FieldHint')
                self.path_layout.addWidget(label)
            limit = max(180, min(500, self.width() // 3))
            shown = self.fontMetrics().elidedText(text, Qt.ElideRight, limit)
            if key:
                widget = QPushButton(shown.replace('&', '&&'))
                widget.setObjectName('Breadcrumb')
                widget.clicked.connect(lambda _, k=key: self.breadcrumb_requested.emit(k))
            else:
                widget = QLabel(shown)
                widget.setAccessibleName(text)
                widget.setObjectName('ExecutionIdentity')
            widget.setToolTip(text)
            self.path_layout.addWidget(widget)

    def set_context(self, title, breadcrumb='Entrela'):
        self._context_title = title
        self._arrange_context()
        self.breadcrumb.setText(breadcrumb)

    def set_destination(self, key):
        for value, button in self.destinations.items():
            button.setChecked(value == key)

    def set_activity(self, index, available=False):
        blocker = QSignalBlocker(self.activities)
        self.activities.setCurrentIndex(index)
        del blocker
        for i in (1, 2):
            # Keep a keyboard-reachable explanation instead of an inert disabled tab.
            self.activities.setTabToolTip(i, 'Consultar a execução selecionada' if available else 'Execute o rascunho ou abra uma execução do histórico para continuar.')

    def _arrange_context(self):
        if not hasattr(self, 'title'): return
        compact = self.width() < 1180 * max(1, self.font().pixelSize()/15)
        title = getattr(self, '_context_title', self.title.text())
        self.title.setText({'Preparar simulação':'Preparar', 'Observar execução':'Observar', 'Editor de circuitos':'Circuito'}.get(title, title) if compact else title)
        self.help_button.setText('' if compact else 'Ajuda')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.logo.setVisible(self.width() >= 1100 or self.font().pixelSize() < 20)
        self._arrange_context()

"""Um contexto de trabalho por seção, preservando as páginas existentes."""

from PySide6.QtCore import Signal, QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QComboBox, QLabel
from gui.widgets.flow_layout import FlowLayout


class SectionWorkspace(QWidget):
    page_selected = Signal(str)

    def __init__(self, pages, entries, parent=None):
        super().__init__(parent)
        self._keys = [key for key, _ in entries]
        self.setObjectName('PageSurface')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = QWidget()
        tools = FlowLayout(toolbar)
        tools.setContentsMargins(20, 10, 20, 8)
        self.selector = QComboBox()
        self.selector.setAccessibleName('Atividade desta área')
        self.selector.setMinimumContentsLength(16)
        self.selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for key, title in entries:
            self.selector.addItem(title, key)
        tools.addWidget(self.selector)
        self.selector.hide()  # Os acessos completos ficam no menu lateral.
        self.context = QLabel()
        self.context.setWordWrap(True)
        self.context.setObjectName('FieldHint')
        tools.addWidget(self.context)
        layout.addWidget(toolbar)
        self.stack = QStackedWidget()
        for key in self._keys:
            self.stack.addWidget(pages[key])
        layout.addWidget(self.stack, 1)
        self.selector.currentIndexChanged.connect(self._selected)

    def select_page(self, key):
        blocker = QSignalBlocker(self.selector)
        self.selector.setCurrentIndex(self._keys.index(key))
        del blocker
        self.stack.setCurrentIndex(self._keys.index(key))
        self.context.setText({
            'analysis': 'Escolha uma pergunta, defina a varredura e examine os resultados.',
            'mitigation': 'Extrapole um observável e confira o erro contra a referência ideal.',
            'comparison': 'Escolha duas execuções e compare evidências compatíveis.',
            'history': 'Reabra, inspecione ou selecione duas execuções para comparar.',
            'library': 'Registre hipóteses e interpretações da execução selecionada.',
            'documentation': 'Organize evidências e prepare os relatórios do estudo.',
            'examples': 'Abra uma cópia editável de um exemplo para começar.',
            'docs': 'Consulte conceitos, exemplos e referências científicas.',
        }.get(key, ''))

    def _selected(self):
        key = self.selector.currentData()
        self.stack.setCurrentIndex(self._keys.index(key))
        self.page_selected.emit(key)

    @property
    def current_page_key(self):
        return self.selector.currentData()

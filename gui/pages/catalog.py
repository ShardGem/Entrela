"""Reusable examples and personal models; opening always produces an editable copy."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QSplitter
from gui.pages.base import PageBase
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.button import PrimaryButton, SecondaryButton
from gui.design_system import Surface
from gui.widgets.preparation_preview import PreparationPreview
from core.types import config_from_dict


class CatalogPage(PageBase):
    template_requested = Signal(str)
    circuit_requested = Signal(object)
    configurations_requested = Signal()

    def __init__(self, examples, editor, parent=None):
        super().__init__("Biblioteca", parent=parent)
        self.setObjectName('PageSurface')
        self.editor = editor
        self.raw = {}
        self.layout_root = self.body()
        self.layout_root.setContentsMargins(20, 0, 20, 20)
        self.tabs = ContentTabs()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(examples, 'Exemplos')
        self.models = QWidget()
        layout = QVBoxLayout(self.models)
        self.search = QLineEdit()
        self.search.setAccessibleName('Buscar modelo pessoal ou circuito')
        self.search.setPlaceholderText('Buscar configuração ou circuito salvo')
        layout.addWidget(self.search)
        self.splitter = QSplitter(Qt.Horizontal)
        self.entries = QListWidget()
        self.entries.setAccessibleName('Modelos pessoais e revisões de circuitos')
        self.splitter.addWidget(self.entries)
        detail = Surface('Modelo reutilizável')
        self.preview = PreparationPreview(); detail.add(self.preview)
        self.description = QLabel('Salve uma configuração ou uma revisão de circuito para reutilizá-la aqui.')
        self.description.setWordWrap(True); detail.add(self.description)
        self.copy = PrimaryButton('Criar cópia editável', icon='plus')
        self.copy.clicked.connect(self._copy); detail.add(self.copy)
        manage = SecondaryButton('Gerenciar configurações salvas')
        manage.clicked.connect(self.configurations_requested.emit); detail.add(manage)
        self.splitter.addWidget(detail)
        self.splitter.setStretchFactor(1, 1); self.splitter.setSizes([400, 800])
        layout.addWidget(self.splitter, 1)
        self.tabs.addTab(self.models, 'Modelos pessoais e circuitos')
        self.layout_root.addWidget(self.tabs)
        self.search.textChanged.connect(self._filter)
        self.entries.currentItemChanged.connect(self._select)


    def refresh(self, raw):
        self.raw = raw
        self._filter()

    def _filter(self, *_):
        self.entries.clear()
        query = self.search.text().casefold()
        for name, value in self.raw.get('templates', {}).items():
            if query not in name.casefold(): continue
            item = QListWidgetItem(name + '\nConfiguração por Hamiltoniano')
            item.setData(Qt.UserRole, ('template', name, value)); item.setToolTip(item.text()); self.entries.addItem(item)
        library = self.editor.library
        if library is not None:
            for entry in library.entries():
                for revision in reversed(library.revisions(entry.identifier)):
                    if query not in (revision.name + ' ' + revision.description).casefold(): continue
                    item = QListWidgetItem(f'{revision.name}\nCircuito livre · revisão {revision.version} · {revision.document.num_qubits} qubits')
                    item.setData(Qt.UserRole, ('circuit', revision.name, revision)); item.setToolTip(item.text()); self.entries.addItem(item)
        if self.entries.count(): self.entries.setCurrentRow(0)
        else:
            self.copy.setEnabled(False)
            self.description.setText('Nenhum modelo corresponde à busca. Salve uma configuração ou uma revisão no editor para reutilizá-la aqui.')
            self.preview.hide()

    def _select(self, item, *_):
        if item is None: return
        kind, name, value = item.data(Qt.UserRole)
        self.copy.setEnabled(True)
        if kind == 'template':
            cfg = config_from_dict(value)
            self.preview.set_preparation(cfg.system.num_qubits, cfg.system.initial_state); self.preview.show()
            self.description.setText(f'{name}\n\n{cfg.system.hamiltonian} · {cfg.system.num_qubits} qubits · {cfg.shots} shots\n\nCriar uma cópia preserva o modelo original. Execute a cópia para obter resultados.')
        else:
            self.preview.hide()
            self.description.setText(f'{name} · revisão {value.version}\n\n{value.document.num_qubits} qubits · {len(value.document.gates)} portas\n\n{value.description}\n\nA cópia começa independente; as revisões originais continuam disponíveis.')

    def _copy(self):
        item = self.entries.currentItem()
        if item is None: return
        kind, name, value = item.data(Qt.UserRole)
        if kind == 'template': self.template_requested.emit(name)
        else: self.circuit_requested.emit(value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.splitter.setOrientation(Qt.Vertical if self.width() < 900 * max(1, self.font().pixelSize()/15) else Qt.Horizontal)

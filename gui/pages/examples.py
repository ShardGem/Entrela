from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QLineEdit,QComboBox,QListWidget,QListWidgetItem,QLabel,QHBoxLayout
from gui.pages.base import PageBase
from gui.widgets.card import Card
from gui.widgets.button import PrimaryButton
from core.examples import EXAMPLES,get_example
import unicodedata

def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD",text.casefold()) if not unicodedata.combining(c))

class ExamplesPage(PageBase):
    example_requested=Signal(str)
    tutorial_requested=Signal()
    def __init__(self,parent=None):
        super().__init__("Galeria de experimentos","Escolha um ponto de partida. Cada exemplo abre uma cópia editável.",parent)
        filters=QHBoxLayout()
        self.search=QLineEdit()
        self.search.setPlaceholderText("Buscar Bell, ruído, Ising…")
        self.level_filter=QComboBox()
        self.level_filter.addItems(["Todos os níveis","Iniciante","Intermediário","Avançado"])
        filters.addWidget(self.search,1)
        filters.addWidget(self.level_filter)
        self.body().addLayout(filters)
        self.list=QListWidget()
        self.list.setMinimumHeight(230)
        self.body().addWidget(self.list)
        card=Card("O que você vai investigar")
        self.details=QLabel()
        self.details.setWordWrap(True)
        card.add(self.details)
        self.btn_try=PrimaryButton("Experimentar — criar cópia")
        self.btn_try.clicked.connect(lambda:self.example_requested.emit(self.current_example_id))
        card.add(self.btn_try)
        self.body().addWidget(card)
        self.btn_tutorial=PrimaryButton("Aprender fazendo: tutorial de Bell")
        self.btn_tutorial.clicked.connect(self.tutorial_requested.emit)
        self.add_action(self.btn_tutorial)
        self.search.textChanged.connect(self._filter)
        self.level_filter.currentTextChanged.connect(self._filter)
        self.list.currentItemChanged.connect(self._selected)
        self._filter()

    def _filter(self,*_):
        query=normalized(self.search.text())
        level=self.level_filter.currentText()
        self.list.clear()
        for example in EXAMPLES:
            if (level=="Todos os níveis" or example.level==level) and all(
                word in normalized(example.title+" "+example.description+" "+example.objective) for word in query.split()):
                item=QListWidgetItem(f"{example.title}  ·  {example.level}")
                item.setData(Qt.UserRole,example.id)
                self.list.addItem(item)
        if self.list.count():self.list.setCurrentRow(0)
        else:
            self.current_example_id=None
            self.details.setText("Nenhum exemplo encontrado. Tente outra busca.")
            self.btn_try.setEnabled(False)

    def _selected(self,item,*_):
        if item is None:return
        example=get_example(item.data(Qt.UserRole))
        self.current_example_id=example.id
        self.btn_try.setEnabled(True)
        cfg=example.config
        self.details.setText(f"{example.description}\n\nObjetivo: {example.objective}\n\n"
            f"O que esperamos: {example.expected}\n\n"
            f"{cfg.system.num_qubits} qubits · {cfg.system.hamiltonian} · "
            f"J={cfg.system.J:g} · h={cfg.system.h:g} · {cfg.shots} shots")

    def select_example(self,identifier):
        get_example(identifier)
        self.search.clear()
        self.level_filter.setCurrentIndex(0)
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.UserRole)==identifier:self.list.setCurrentRow(row)

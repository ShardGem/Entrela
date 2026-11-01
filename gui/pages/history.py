from core.types import system_label
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from gui.pages.base import PageBase


class HistoryPage(PageBase):
    experiment_selected = Signal(str)
    experiment_deleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Histórico",
            "Duplo clique para reabrir configuração, estados e resultados.",
            parent,
        )
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar identificador, modelo, ruído ou estado…")
        self.body().addWidget(self.search)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Data / fuso",
                "Identificador",
                "Modelo",
                "Qubits",
                "Ruído",
                "Fidelidade",
                "Estado",
                "Projeto",
                "Tags",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._open)
        self.body().addWidget(self.table, 1)
        pagination = QHBoxLayout()
        self.previous = QPushButton("Anterior")
        self.next = QPushButton("Próxima")
        self.page_label = QLabel()
        pagination.addWidget(self.previous)
        pagination.addWidget(self.page_label)
        pagination.addWidget(self.next)
        self.body().addLayout(pagination)
        self.previous.clicked.connect(lambda: self._paginate(-1))
        self.next.clicked.connect(lambda: self._paginate(1))
        self.offset = 0
        self.page_size = 100
        self.records = []
        self.annotations = {}
        self.search.textChanged.connect(self._search_changed)

    def load(self, experiments):
        self.records = list(experiments)
        self._filter()

    def _filter(self, *_):
        query = self.search.text().casefold()
        self.table.setRowCount(0)
        matches = []
        for exp in self.records:
            status = (
                "Falhou"
                if exp.result.error
                else ("ZNE" if exp.result.mitigation else "Concluído")
            )
            values = [
                exp.created_at.strftime("%d/%m/%Y %H:%M %z"),
                exp.id,
                system_label(exp.config),
                str(exp.config.system.num_qubits),
                exp.config.noise.kind if exp.config.noise.enabled else "Ideal",
                "—" if exp.result.fidelity is None else f"{exp.result.fidelity:.4f}",
                status,
            ]
            annotation = self.annotations.get(exp.id, {})
            values.extend(
                [annotation.get("project", ""), ", ".join(annotation.get("tags", []))]
            )
            if (
                query
                not in (" ".join(values) + " " + annotation.get("notes", "")).casefold()
            ):
                continue
            matches.append((exp, values))
        self.offset = min(
            self.offset, max(0, ((len(matches) - 1) // self.page_size) * self.page_size)
        )
        for exp, values in matches[self.offset : self.offset + self.page_size]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(Qt.UserRole, exp.id)
                self.table.setItem(row, col, item)
        self.page_label.setText(
            f"{len(matches)} registro(s) · página {self.offset // self.page_size + 1}"
        )
        self.previous.setEnabled(self.offset > 0)
        self.next.setEnabled(self.offset + self.page_size < len(matches))

    def _search_changed(self, *_):
        self.offset = 0
        self._filter()

    def _paginate(self, delta):
        self.offset = max(0, self.offset + delta * self.page_size)
        self._filter()

    def _open(self, row, column):
        item = self.table.item(row, 0)
        if item:
            self.experiment_selected.emit(item.data(Qt.UserRole))

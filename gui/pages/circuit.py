from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
)
from PySide6.QtGui import QFont
from gui.pages.base import PageBase


class CircuitPage(PageBase):
    snapshot_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(
            "Circuito",
            "Portas sintetizadas, preparação, camadas Trotter e medições.",
            parent,
        )
        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.viewer.setFont(QFont("monospace", 10))
        self.viewer.setMinimumHeight(200)
        self.body().addWidget(self.viewer)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Porta", "Qubits", "Parâmetros (rad)", "Origem", "Passo"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.cellClicked.connect(self._selected)
        self.body().addWidget(self.table)
        self.details = QLabel("Selecione uma porta para inspecionar sua camada.")
        self.details.setWordWrap(True)
        self.body().addWidget(self.details)
        self.operations = []
        self.snapshots = False
        self.show_circuit("")

    def show_circuit(self, text, operations=None, snapshots=False):
        self.viewer.setPlainText(
            text or "Execute ou abra um experimento para ver o circuito."
        )
        self.operations = operations or []
        self.snapshots = snapshots
        self.table.setRowCount(len(self.operations))
        for i, op in enumerate(self.operations):
            for j, value in enumerate(
                [
                    op["name"],
                    str(op["qubits"]),
                    str(op["parameters"]),
                    op["stage"],
                    str(op["step"]),
                ]
            ):
                self.table.setItem(i, j, QTableWidgetItem(value))

    def _selected(self, row, column):
        op = self.operations[row]
        self.details.setText(
            f"{op['name']} nos qubits {op['qubits']}; {op['stage']}, passo {op['step']}. "
            + "O snapshot corresponde ao fim da camada completa; não ao instante desta porta. A decomposição não identifica um único termo do Hamiltoniano para cada porta."
        )
        if self.snapshots:
            self.snapshot_requested.emit(op["step"])

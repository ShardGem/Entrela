from core.types import system_label
from data.workspace import experiment_title
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from gui.pages.base import PageBase
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE


def incompatibility(a, b):
    if a.id == b.id:
        return "Selecione dois registros diferentes."
    if a.result.error or b.result.error:
        return "Execuções com erro não são comparáveis."
    if a.config.system != b.config.system:
        return "Sistemas diferentes: iguale qubits, Hamiltoniano, J, h, fronteira e estado inicial."
    if a.config.circuit != b.config.circuit:
        return "Circuitos diferentes: compare a mesma sequência de portas."
    pa, pb = a.config.protocol, b.config.protocol
    if (pa.total_time, pa.trotter_steps, pa.trotter_order) != (
        pb.total_time,
        pb.trotter_steps,
        pb.trotter_order,
    ):
        return "Protocolos de evolução diferentes: iguale tempo, passos e ordem."
    return ""


class ComparisonPage(PageBase):
    def __init__(self, parent=None):
        super().__init__(
            "Comparações",
            "Compare execuções com o mesmo sistema e protocolo, variando ruído e amostragem.",
            parent,
        )
        row = QHBoxLayout()
        self.first_run, self.second_run = QComboBox(), QComboBox()
        self.first_run.setAccessibleName("Execução A")
        self.second_run.setAccessibleName("Execução B")
        self.first_run.setMinimumContentsLength(12)
        self.second_run.setMinimumContentsLength(12)
        self.first_run.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.second_run.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        row.addWidget(QLabel("A"))
        row.addWidget(self.first_run)
        row.addWidget(QLabel("B"))
        row.addWidget(self.second_run)
        self.body().addLayout(row)
        self.message = QLabel("São necessárias duas execuções.")
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["Métrica", "A", "B", "B − A"])
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.body().addWidget(self.metrics_table)
        self.canvas = MplCanvas()
        self.body().addWidget(self.canvas, 1)
        self.records = {}
        self.annotations = {}
        self.first_run.currentIndexChanged.connect(self._compare)
        self.second_run.currentIndexChanged.connect(self._compare)

    def load(self, experiments):
        selected = (self.first_run.currentData(), self.second_run.currentData())
        self.records = {e.id: e for e in experiments}
        self.first_run.blockSignals(True)
        self.second_run.blockSignals(True)
        for combo in (self.first_run, self.second_run):
            combo.clear()
            for e in experiments:
                label = f"{experiment_title(e, self.annotations)} · " + (
                    "ZNE (métricas da fonte)"
                    if e.result.mitigation
                    else (e.config.noise.kind if e.config.noise.enabled else "Ideal")
                )
                combo.addItem(label, e.id)
                combo.setItemData(combo.count() - 1, f"{e.id} · {e.created_at.isoformat()} · {system_label(e.config)}", Qt.ToolTipRole)
        self.first_run.setCurrentIndex(max(0, self.first_run.findData(selected[0])))
        fallback = min(1, len(experiments) - 1)
        self.second_run.setCurrentIndex(
            self.second_run.findData(selected[1])
            if selected[1] in self.records
            else fallback
        )
        self.first_run.blockSignals(False)
        self.second_run.blockSignals(False)
        self._compare()

    def set_runs(self, a, b):
        if a not in self.records or b not in self.records:
            raise ValueError("Execução não encontrada")
        self.first_run.setCurrentIndex(self.first_run.findData(a))
        self.second_run.setCurrentIndex(self.second_run.findData(b))
        self._compare()

    def _compare(self, *_):
        self.metrics_table.setRowCount(0)
        ax = self.canvas.reset_axes()
        a, b = (
            self.records.get(self.first_run.currentData()),
            self.records.get(self.second_run.currentData()),
        )
        error = (
            "São necessárias duas execuções."
            if a is None or b is None
            else incompatibility(a, b)
        )
        if error:
            self.message.setText(error)
            self.canvas.draw()
            return
        note = "Comparação compatível. Distribuições normalizadas pelo número observado de medições. "
        note += f"A: {a.config.shots} shots / {a.duration_s:.4g} s · B: {b.config.shots} shots / {b.duration_s:.4g} s. "
        if a.result.mitigation or b.result.mitigation:
            note += " Os registros ZNE mantêm as métricas da simulação de origem; não são estados mitigados."
        self.message.setText(note)
        for row, (label, key) in enumerate(
            [
                ("Fidelidade", "fidelity"),
                ("Pureza global", "purity"),
                ("Energia", "energy"),
            ]
        ):
            x, y = getattr(a.result, key), getattr(b.result, key)
            self.metrics_table.insertRow(row)
            values = [
                label,
                "—" if x is None else f"{x:.6f}",
                "—" if y is None else f"{y:.6f}",
                "—" if x is None or y is None else f"{y - x:+.6f}",
            ]
            for col, text in enumerate(values):
                self.metrics_table.setItem(row, col, QTableWidgetItem(text))
        keys = sorted(set(a.result.counts or {}) | set(b.result.counts or {}))
        for i, e in enumerate((a, b)):
            total = sum((e.result.counts or {}).values())
            xs = [j + (i - 0.5) * 0.36 for j in range(len(keys))]
            ax.bar(
                xs,
                [
                    (e.result.counts or {}).get(k, 0) / total if total else 0
                    for k in keys
                ],
                width=0.35,
                label="A" if i == 0 else "B",
                color=PALETTE.primary if i == 0 else PALETTE.q2,
            )
        ax.set_xticks(range(len(keys)), keys, rotation=90 if len(keys) > 8 else 0)
        ax.set_ylabel("Frequência observada")
        ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
        self.canvas.draw()

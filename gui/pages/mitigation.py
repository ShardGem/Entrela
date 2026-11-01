from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton

from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE
import numpy as np


class MitigationPage(PageBase):
    run_requested = Signal(int, str, int)

    def __init__(self, parent=None):
        super().__init__(
            "Mitigação",
            "Extrapolação de um observável Z com fatores efetivos 1, 3 e 5.",
            parent,
        )
        self.has_experiment = False
        self.context = QLabel("Execute ou abra um experimento.")
        self.body().addWidget(self.context)
        form = QFormLayout()
        self.qubit = QSpinBox()
        self.method = QComboBox()
        self.method.addItem("Linear", "linear")
        self.method.addItem("Quadrático", "quadratic")
        self.shots = QSpinBox()
        self.shots.setRange(1, 1_000_000)
        self.shots.setValue(8192)
        form.addRow("Qubit observado (q0 à direita)", self.qubit)
        form.addRow("Ajuste", self.method)
        form.addRow("Shots por fator", self.shots)
        self.body().addLayout(form)
        self.btn_run = PrimaryButton("Executar ZNE")
        self.btn_run.clicked.connect(
            lambda: self.run_requested.emit(
                self.qubit.value(), self.method.currentData(), self.shots.value()
            )
        )
        self.body().addWidget(self.btn_run)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Fator efetivo", "⟨Z⟩ observado", "Erro padrão estimado"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.body().addWidget(self.table)
        self.canvas = MplCanvas(height=3)
        self.canvas.setMinimumHeight(250)
        self.body().addWidget(self.canvas)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.body().addWidget(self.summary)
        note = QLabel(
            "ZNE estima um observável e não garante melhora. Não produz automaticamente um estado mitigado. "
            "Valores extrapolados não são truncados a [-1,1]. Fidelidade e pureza permanecem as da simulação original."
        )
        note.setWordWrap(True)
        self.body().addWidget(note)
        self.set_running(False)

    def load_experiment(self, experiment):
        self.has_experiment = not bool(experiment.result.error)
        self.context.setText("Experimento " + experiment.id)
        self.qubit.setRange(0, experiment.config.system.num_qubits - 1)
        self.shots.setValue(experiment.config.shots)
        self.table.setRowCount(0)
        self.summary.setText("Nenhuma extrapolação neste registro.")
        ax = self.canvas.reset_axes()
        m = experiment.result.mitigation
        if m:
            for f, y, e in zip(m["scale_factors"], m["measured"], m["stderr"]):
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, text in enumerate([str(f), f"{y:.6f}", f"{e:.6f}"]):
                    self.table.setItem(row, col, QTableWidgetItem(text))
            self.summary.setText(
                f"Z do qubit {m['qubit']}: {m['extrapolated']:.6f} ± "
                f"{m['extrapolated_stderr']:.6f} (erro padrão de amostragem). "
                f"Fonte das métricas: {m['source_experiment_id']}."
            )
            xs = np.array(m["scale_factors"])
            ys = np.array(m["measured"])
            ax.errorbar(
                xs,
                ys,
                yerr=m["stderr"],
                fmt="o",
                color=PALETTE.primary,
                label="Medições ± erro padrão",
            )
            coeff = m.get(
                "coefficients", np.polyfit(xs, ys, 1 if m["method"] == "linear" else 2)
            )
            grid = np.linspace(0, max(xs), 100)
            ax.plot(grid, np.polyval(coeff, grid), color=PALETTE.q2, label="Ajuste")
            ax.errorbar(
                [0],
                [m["extrapolated"]],
                yerr=[m["extrapolated_stderr"]],
                fmt="s",
                color=PALETTE.success,
                label="Extrapolação",
            )
            if "ideal_observable" in m:
                ax.axhline(
                    m["ideal_observable"],
                    color=PALETTE.text,
                    linestyle="--",
                    label="Z ideal",
                )
                self.summary.setText(
                    self.summary.text()
                    + f" Erro absoluto: antes {m['baseline_absolute_error']:.5g}; após {m['extrapolated_absolute_error']:.5g}. "
                    + f"Graus de liberdade residuais: {m['degrees_of_freedom']}. "
                    + "Incerteza mostrada cobre amostragem, não viés do modelo ou do ajuste."
                )
            ax.set_xlabel("Fator de ruído efetivo")
            ax.set_ylabel("⟨Z⟩")
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text, fontsize=8)
        self.canvas.draw_idle()
        self.set_running(False)

    def set_running(self, running):
        for w in (self.qubit, self.method, self.shots, self.btn_run):
            w.setEnabled(self.has_experiment and not running)
        self.btn_run.setText("Executando…" if running else "Executar ZNE")

    def set_error(self, message):
        self.summary.setText(message)

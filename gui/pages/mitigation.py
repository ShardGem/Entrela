from PySide6.QtCore import Signal, Qt
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
from data.workspace import experiment_title
from core.mitigation import z_sampling_metadata


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
        self.shots.setToolTip(
            "Medições independentes por fator. Mais shots reduzem flutuações de amostragem, "
            "mas não eliminam viés do modelo ou da extrapolação."
        )
        form.addRow("Qubit observado (q0 à direita)", self.qubit)
        form.addRow("Ajuste", self.method)
        form.addRow("Shots por fator", self.shots)
        self.body().addLayout(form)
        self.sampling_advice = QLabel()
        self.sampling_advice.setWordWrap(True)
        self.sampling_advice.setAccessibleName("Orientação sobre quantidade de shots")
        self.shots.valueChanged.connect(self._update_sampling_advice)
        self.body().addWidget(self.sampling_advice)
        self._update_sampling_advice(self.shots.value())
        self.btn_run = PrimaryButton("Executar ZNE")
        self.btn_run.clicked.connect(
            lambda: self.run_requested.emit(
                self.qubit.value(), self.method.currentData(), self.shots.value()
            )
        )
        self.body().addWidget(self.btn_run)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Fator\nefetivo", "⟨Z⟩\nobservado", "Erro padrão\nplug-in", "Intervalo Wilson\n95% por fator"]
        )
        self.table.horizontalHeaderItem(2).setToolTip(
            "Estimativa sqrt((1 − média²) / shots). Pode ser zero quando todos os "
            "resultados observados coincidem; isso não comprova certeza."
        )
        self.table.horizontalHeaderItem(3).setToolTip(
            "Intervalo binomial aproximado para o Z deste fator. A cobertura nominal "
            "não é garantida em amostras pequenas. Não é intervalo da extrapolação."
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAccessibleName("Medições e incerteza de amostragem por fator")
        self.body().addWidget(self.table)
        self.canvas = MplCanvas(height=3)
        self.canvas.setMinimumHeight(250)
        self.body().addWidget(self.canvas)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.body().addWidget(self.summary)
        self.sampling_warning = QLabel()
        self.sampling_warning.setWordWrap(True)
        self.sampling_warning.setAccessibleName("Limitações da amostragem")
        self.body().addWidget(self.sampling_warning)
        note = QLabel(
            "ZNE estima um observável e não garante melhora. Não produz automaticamente um estado mitigado. "
            "Valores extrapolados não são truncados a [-1,1]. Fidelidade e pureza permanecem as da simulação original. "
            "Wilson é um intervalo aproximado por fator, sem cobertura simultânea e sem propagação "
            "ao alvo de ruído zero. Nenhuma das incertezas mostradas cobre viés do modelo ou do ajuste."
        )
        note.setWordWrap(True)
        self.body().addWidget(note)
        self.set_running(False)

    def _update_sampling_advice(self, shots):
        self.sampling_advice.setText(
            "Poucos shots: permitido para exploração, mas a dispersão pode ser subestimada. "
            "O aviso abaixo de 30 shots é orientativo e não garante precisão acima desse valor."
            if shots < 30 else ""
        )
        self.sampling_advice.setVisible(shots < 30)

    def load_experiment(self, experiment):
        self.has_experiment = not bool(experiment.result.error)
        self.context.setText(experiment_title(experiment))
        self.qubit.setRange(0, experiment.config.system.num_qubits - 1)
        self.shots.setValue(experiment.config.shots)
        self.table.setRowCount(0)
        self.summary.setText("Nenhuma extrapolação neste registro.")
        self.sampling_warning.clear()
        ax = self.canvas.reset_axes()
        m = experiment.result.mitigation
        if m:
            self.qubit.setValue(m["qubit"])
            self.shots.setValue(m["shots"])
            self.method.setCurrentIndex(max(0, self.method.findData(m["method"])))
            # Recompute diagnostic display from the recorded counts when present;
            # keep historic records and all stored estimates untouched.
            try:
                sampling = z_sampling_metadata(m["samples"], experiment.config.system.num_qubits, m["qubit"]) if m.get("samples") else {}
            except (ValueError, TypeError, KeyError, AttributeError):
                sampling = {}  # Legacy records can lack valid per-factor counts.
            intervals = sampling.get("sampling_intervals", [])
            warnings = sampling.get("sampling_diagnostics", {}).get("warnings", [])
            if not intervals:
                warnings = list(warnings) + [
                    "Registro anterior sem contagens por fator: intervalo Wilson indisponível. "
                    "Erro padrão igual a zero não comprova ausência de incerteza."
                ]
            self.sampling_warning.setText(" ".join(warnings))
            for index, (f, y, e) in enumerate(zip(m["scale_factors"], m["measured"], m["stderr"])):
                row = self.table.rowCount()
                self.table.insertRow(row)
                interval = intervals[index] if index < len(intervals) else None
                interval_text = f"[{interval[0]:.6f}; {interval[1]:.6f}]" if interval else "Não registrado"
                for col, text in enumerate([str(f), f"{y:.6f}", f"{e:.6f}", interval_text]):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)
            self.summary.setText(
                f"Z extrapolado do qubit {m['qubit']}: {m['extrapolated']:.6f}. "
                f"Erro padrão plug-in propagado: {m['extrapolated_stderr']:.6f}. "
                "Métricas de estado pertencem à execução de origem preservada."
            )
            xs = np.array(m["scale_factors"])
            ys = np.array(m["measured"])
            ax.errorbar(
                xs,
                ys,
                yerr=(np.maximum(0., np.array([ys - np.array(intervals)[:, 0], np.array(intervals)[:, 1] - ys]))
                      if len(intervals) == len(ys) else m["stderr"]),
                fmt="o",
                color=PALETTE.primary,
                label="Wilson 95% por fator" if len(intervals) == len(ys) else "Erro padrão plug-in",
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
                label="ZNE ± erro padrão plug-in",
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
                    + "O erro padrão propagado é estimado; não é um intervalo de confiança do alvo de ruído zero."
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

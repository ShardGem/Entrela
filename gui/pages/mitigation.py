from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtWidgets import (
    QLabel,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView, QHBoxLayout, QScrollArea, QTabWidget,
)
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton
from gui.widgets.card import MetricCard
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.data_table import configure_table
from gui.design_system import Surface

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
        self.body().setSpacing(12)
        workbench = QHBoxLayout()
        self.workbench_layout = workbench
        workbench.setSpacing(20)
        self.body().addLayout(workbench, 1)
        self.compact_tabs = QTabWidget()
        self.compact_tabs.setAccessibleName('Configuração e resultados da ZNE')
        self.compact_tabs.setUsesScrollButtons(True)
        self.compact_tabs.hide()
        self._compact = None
        self._compact_selection = None
        self.views = ContentTabs()
        workbench.addWidget(self.views, 1)
        inspector = Surface('Configurar extrapolação', role='WorkbenchInspector')
        scroll = QScrollArea()
        scroll.setObjectName('InspectorScroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inspector)
        self.inspector_scroll = scroll
        workbench.addWidget(scroll)
        self.context = QLabel("Execute ou abra um experimento.")
        self.context.setTextFormat(Qt.PlainText)
        self.context.setWordWrap(True)
        self.context.setObjectName('FieldHint')
        inspector.add(self.context)
        form = QFormLayout()
        self.form = form
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
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
        form.addRow("Qubit observado", self.qubit)
        self.qubit.setToolTip("Índice do qubit. q0 fica à direita no estado binário.")
        form.addRow("Ajuste", self.method)
        form.addRow("Shots por fator", self.shots)
        inspector.body().addLayout(form)
        self.sampling_advice = QLabel()
        self.sampling_advice.setWordWrap(True)
        self.sampling_advice.setAccessibleName("Orientação sobre quantidade de shots")
        self.shots.valueChanged.connect(self._update_sampling_advice)
        inspector.add(self.sampling_advice)
        self._update_sampling_advice(self.shots.value())
        self.btn_run = PrimaryButton("Executar ZNE")
        self.btn_run.clicked.connect(
            lambda: self.run_requested.emit(
                self.qubit.value(), self.method.currentData(), self.shots.value()
            )
        )
        inspector.add(self.btn_run)
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
        configure_table(self.table, numeric_columns=range(4))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setAccessibleName("Medições e incerteza de amostragem por fator")
        self.canvas = MplCanvas(height=3)
        self.canvas.setMinimumHeight(250)
        plot = Surface(role="PlotFrame")
        plot.add(self.canvas, 1)
        self.views.addTab(plot, 'Extrapolação')
        self.views.addTab(self.table, 'Medições por fator')
        self.extrapolated = MetricCard("⟨Z⟩ extrapolado")
        self.extrapolated.setObjectName("RunMetric")
        self.extrapolated.layout().setContentsMargins(0, 6, 0, 9)
        inspector.add(self.extrapolated)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("FieldHint")
        inspector.add(self.summary)
        self.sampling_warning = QLabel()
        self.sampling_warning.setWordWrap(True)
        self.sampling_warning.setAccessibleName("Limitações da amostragem")
        self.sampling_warning.setObjectName("FieldHint")
        inspector.add(self.sampling_warning)
        note = QLabel(
            "ZNE estima um observável e não garante melhora. Não produz automaticamente um estado mitigado. "
            "Valores extrapolados não são truncados a [-1,1]. Fidelidade e pureza permanecem as da simulação original. "
            "Wilson é um intervalo aproximado por fator, sem cobertura simultânea e sem propagação "
            "ao alvo de ruído zero. O erro padrão propagado é uma estimativa, sem cobertura de intervalo de confiança. "
            "As incertezas de amostragem deixam de fora o viés do modelo e do ajuste."
        )
        note.setWordWrap(True)
        method = CollapsibleSection("Como interpretar")
        method.setProperty("inline", True)
        method.content_layout.addWidget(note)
        inspector.add(method)
        inspector.body().addStretch(1)
        self.reset_result()
        self.set_running(False)
        self._arrange_workbench()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_workbench()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._arrange_workbench()

    def _arrange_workbench(self):
        if not hasattr(self, 'btn_run') or getattr(self, '_arranging_workbench', False):
            return
        self._arranging_workbench = True
        try:
            scale = max(1, self.fontMetrics().height() / 19)
            compact = self.width() < 1050 * scale
            self.form.setRowWrapPolicy(QFormLayout.WrapAllRows if compact else QFormLayout.WrapLongRows)
            if compact:
                self.inspector_scroll.setMinimumWidth(0)
                self.inspector_scroll.setMaximumWidth(16777215)
            else:
                self.inspector_scroll.setFixedWidth(round(310 * scale))
            if compact == self._compact:
                return
            self._compact = compact
            if compact:
                self.workbench_layout.removeWidget(self.views)
                self.workbench_layout.removeWidget(self.inspector_scroll)
                self.compact_tabs.addTab(self.inspector_scroll, 'Configurar ZNE')
                self.compact_tabs.addTab(self.views, 'Resultados')
                if self._compact_selection in (self.views, self.inspector_scroll):
                    self.compact_tabs.setCurrentWidget(self._compact_selection)
                self.workbench_layout.addWidget(self.compact_tabs)
                self.compact_tabs.show()
            else:
                if self.compact_tabs.count():
                    self._compact_selection = self.compact_tabs.currentWidget()
                self.workbench_layout.removeWidget(self.compact_tabs)
                for widget in (self.views, self.inspector_scroll):
                    self.compact_tabs.removeTab(self.compact_tabs.indexOf(widget))
                    self.workbench_layout.addWidget(widget, 1 if widget is self.views else 0)
                    widget.show()
                self.compact_tabs.hide()
        finally:
            self._arranging_workbench = False

    def reset_result(self):
        self.table.setRowCount(0)
        self.summary.clear()
        self.sampling_warning.clear()
        self.sampling_warning.hide()
        self.extrapolated.hide()
        self.views.setCurrentIndex(0)
        self.views.setTabEnabled(1, False)
        self._compact_selection = self.inspector_scroll
        if self._compact:
            self.compact_tabs.setCurrentWidget(self.inspector_scroll)
        ax = self.canvas.reset_axes()
        ax.set_axis_off()
        ax.text(.5, .5, 'Execute ZNE para visualizar o observável extrapolado.',
                transform=ax.transAxes, ha='center', va='center', color=PALETTE.text_muted, wrap=True)
        self.canvas.draw_idle()

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
        m = experiment.result.mitigation
        self.reset_result()
        if m:
            self.views.setTabEnabled(1, True)
            ax = self.canvas.reset_axes()
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
            self.sampling_warning.setVisible(bool(warnings))
            for index, (f, y, e) in enumerate(zip(m["scale_factors"], m["measured"], m["stderr"])):
                row = self.table.rowCount()
                self.table.insertRow(row)
                interval = intervals[index] if index < len(intervals) else None
                interval_text = f"[{interval[0]:.6f}; {interval[1]:.6f}]" if interval else "Não registrado"
                for col, text in enumerate([str(f), f"{y:.6f}", f"{e:.6f}", interval_text]):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)
            self.extrapolated.set_value(f"{m['extrapolated']:.6f}", f"q{m['qubit']}")
            self.extrapolated.show()
            summary = [f"Erro padrão propagado (plug-in): {m['extrapolated_stderr']:.6f}"]

            xs = np.array(m["scale_factors"])
            ys = np.array(m["measured"])
            ax.errorbar(
                xs,
                ys,
                yerr=(np.maximum(0., np.array([ys - np.array(intervals)[:, 0], np.array(intervals)[:, 1] - ys]))
                      if len(intervals) == len(ys) else m["stderr"]),
                fmt="o",
                color=PALETTE.q1,
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
                fmt="D",
                color=PALETTE.q2,
                label="ZNE ± erro padrão plug-in",
            )
            if "ideal_observable" in m:
                ax.axhline(
                    m["ideal_observable"],
                    color=PALETTE.text,
                    linestyle="--",
                    label="Referência: mesmo circuito sem ruído",
                )
                summary.extend([
                    f"Erro absoluto antes: {m['baseline_absolute_error']:.5g}",
                    f"Erro absoluto após: {m['extrapolated_absolute_error']:.5g}",
                    f"Graus de liberdade residuais: {m['degrees_of_freedom']}",
                ])
            self.summary.setText("\n".join(summary))
            ax.set_xlabel("Fator de ruído efetivo (0 = ruído zero)")
            ax.set_ylabel("⟨Z⟩")
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text, fontsize=8)
        self.canvas.draw_idle()
        self.set_running(False)
        if m and self._compact:
            self.compact_tabs.setCurrentWidget(self.views)
        if m:
            self._compact_selection = self.views

    def set_running(self, running):
        for w in (self.qubit, self.method, self.shots, self.btn_run):
            w.setEnabled(self.has_experiment and not running)
        self.btn_run.setText("Executando…" if running else "Executar ZNE")

    def set_error(self, message):
        self.summary.setText(message)

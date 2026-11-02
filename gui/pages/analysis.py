"""Scientific tools operate on the selected run, preserving its result."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QComboBox,
    QLineEdit,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QSpinBox,
    QHBoxLayout,
    QProgressBar,
)
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton, SecondaryButton
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE


class AnalysisPage(PageBase):
    requested = Signal(str, dict)
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Análises científicas",
            "Separe ruído, aproximação numérica e amostragem.",
            parent,
        )
        self.experiment = None
        self.data = None
        self.series = []
        self._running = False
        self.context = QLabel("Abra uma execução para começar.")
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form = form
        self.kind = QComboBox()
        for name, key in [
            ("Métricas temporais e correlações", "temporal"),
            ("Convergência Suzuki–Trotter", "convergence"),
            ("Varredura de parâmetros", "sweep"),
            ("Trotter × ruído: estudo pareado", "trotter_noise"),
            ("Benchmark de mitigação", "mitigation_benchmark"),
        ]:
            self.kind.addItem(name, key)
        self.parameter = QComboBox()
        self.parameter.addItems(
            ["p1", "p2", "J", "h", "t1_us", "t2_us", "trotter_steps"]
        )
        self.values = QLineEdit("0, 0.01, 0.03, 0.05, 0.1")
        self.values.setPlaceholderText("Valores separados por vírgula; ponto decimal")
        self.steps = QLineEdit("1, 2, 4, 8, 16")
        self.seeds = QLineEdit("")
        self.seeds.setPlaceholderText(
            "Vazio: seed efetiva da fonte; até 5 seeds separadas por vírgula"
        )
        self.benchmark_qubit = QSpinBox()
        self.benchmark_qubit.setPrefix("q")
        self.benchmark_qubit.setAccessibleName("Qubit do observável Z no benchmark")
        self.benchmark_shots = QSpinBox()
        self.benchmark_shots.setRange(64, 1_000_000)
        self.benchmark_shots.setValue(8192)
        self.benchmark_shots.setToolTip("Shots por fator 1, 3 e 5. Os ajustes reutilizam as mesmas medições; o custo total é informado no resultado.")
        self.help = QLabel()
        self.help.setWordWrap(True)
        for label, w in [
            ("Análise", self.kind),
            ("Parâmetro da varredura", self.parameter),
            ("Valores da varredura", self.values),
            ("Sementes da varredura", self.seeds),
            ("Passos para convergência", self.steps),
            ("Observável do benchmark", self.benchmark_qubit),
            ("Shots por fator", self.benchmark_shots),
        ]:
            form.addRow(label, w)
        self.body().addLayout(form)
        self.body().addWidget(self.help)
        self.saved = QComboBox()
        self.saved.addItem("Análises salvas desta execução", None)
        self.saved.currentIndexChanged.connect(self._open_saved)
        self.body().addWidget(self.saved)
        self.btn_run = PrimaryButton("Calcular análise")
        self.btn_run.clicked.connect(self._request)
        actions = QHBoxLayout()
        actions.addWidget(self.btn_run)
        self.btn_cancel = SecondaryButton("Cancelar análise")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        actions.addWidget(self.btn_cancel)
        self.body().addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setAccessibleName("Progresso da análise científica")
        self.body().addWidget(self.progress)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.series_combo = QComboBox()
        self.series_combo.currentIndexChanged.connect(self._plot)
        self.body().addWidget(self.series_combo)
        self.canvas = MplCanvas(height=3)
        self.canvas.setMinimumHeight(260)
        self.body().addWidget(self.canvas)
        self.canvas.mpl_connect("button_press_event", self._plot_clicked)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(180)
        self.table.cellClicked.connect(self._select)
        self.body().addWidget(self.table)
        self.export_button = SecondaryButton("Exportar CSV / JSON")
        self.export_button.clicked.connect(self._export)
        self.export_button.setEnabled(False)
        self.add_action(self.export_button)
        self.replay_button = SecondaryButton("Reproduzir análise")
        self.replay_button.setEnabled(False)
        self.replay_button.clicked.connect(self._replay)
        self.add_action(self.replay_button)
        self.kind.currentIndexChanged.connect(self._update_controls)
        self._update_controls()
        self.set_running(False)

    def _update_controls(self, *_):
        kind = self.kind.currentData()
        for w in (self.parameter, self.values, self.seeds):
            self.form.setRowVisible(w, kind == "sweep")
        self.form.setRowVisible(self.steps, kind in ("convergence", "trotter_noise"))
        for widget in (self.benchmark_qubit, self.benchmark_shots):
            self.form.setRowVisible(widget, kind == "mitigation_benchmark")
        self.help.setText({
            "temporal": "Inspecione os estados realmente simulados. Clique na curva ou na tabela para selecionar o mesmo snapshot em 3D.",
            "convergence": "Aumentar os passos reduz o erro de aproximação em muitos casos. Esta análise desliga o ruído e compara com exp(−iHt).",
            "sweep": "Altere um parâmetro por vez. p1/p2 são intensidades despolarizadoras; T₁/T₂ são tempos em µs. Sementes afetam contagens, não a incerteza das métricas do ensemble.",
            "trotter_noise": "Compare, nos mesmos passos, a aproximação ideal e a execução com o ruído da fonte contra a evolução exata. O melhor ponto é escolhido apenas entre os valores calculados.",
            "mitigation_benchmark": "Compare sem mitigação, ZNE linear/quadrática (variantes da mesma técnica) e verificação de simetria por paridade, quando aplicável. ZNE estima ⟨Z⟩ e não reconstrói um estado: sua fidelidade fica indisponível. As medições compartilhadas e os custos são registrados.",
        }.get(kind, ""))

    def load_experiment(self, experiment):
        self.experiment = experiment
        self.data = None
        self.table.setRowCount(0)
        self.series_combo.clear()
        self.canvas.reset_axes()
        self.canvas.draw_idle()
        self.context.setText("Fonte: " + experiment.id + " · configuração preservada")
        self.benchmark_qubit.setMaximum(experiment.config.system.num_qubits - 1)
        self.benchmark_shots.setValue(experiment.config.shots)
        self.message.clear()
        self.export_button.setEnabled(False)
        self.replay_button.setEnabled(False)
        self.set_running(self._running)

    def set_saved(self, paths):
        self.saved.blockSignals(True)
        self.saved.clear()
        self.saved.addItem("Análises salvas desta execução", None)
        for label, path in paths:
            self.saved.addItem(label, str(path))
        self.saved.blockSignals(False)

    def _open_saved(self, *_):
        path = self.saved.currentData()
        if not path:
            return
        try:
            from data.analyses import load_analysis
            data = load_analysis(path, self.experiment.id)
            self.show_analysis(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.message.setText("Não foi possível abrir a análise: " + str(exc))

    def _plot_clicked(self, event):
        if (
            self.data
            and self.data["kind"] == "temporal"
            and event.inaxes
            and event.xdata is not None
        ):
            row = min(
                range(len(self.data["rows"])),
                key=lambda i: abs(self.data["rows"][i]["time"] - event.xdata),
            )
            self.table.selectRow(row)
            self.parent_window_frame(row)

    def _request(self):
        try:
            kind = self.kind.currentData()
            options = {}
            if kind in ("convergence", "trotter_noise"):
                options = {
                    "steps": [int(x.strip()) for x in self.steps.text().split(",")]
                }
            elif kind == "mitigation_benchmark":
                options = {"qubit": self.benchmark_qubit.value(), "shots": self.benchmark_shots.value()}
            elif kind == "sweep":
                options = {
                    "parameter": self.parameter.currentText(),
                    "values": [float(x.strip()) for x in self.values.text().split(",")],
                    "seeds": [int(x.strip()) for x in self.seeds.text().split(",")]
                    if self.seeds.text().strip()
                    else None,
                }
            self.requested.emit(kind, options)
        except ValueError:
            self.message.setText(
                "Revise os valores: use vírgula entre pontos e ponto como separador decimal."
            )

    def show_analysis(self, data):
        self.data = data
        rows = data["rows"]
        note = data["note"]
        if data["kind"] == "mitigation_benchmark":
            cost = data["actual_cost"]
            note = f"Custo efetivamente adquirido: {cost['circuits']} circuitos · {cost['shots']} shots · {cost['acquisition_s']:.3f} s.\n" + note
            columns = ["label", "status", "estimate", "stderr", "absolute_error", "fidelity", "purity", "shots", "retained_shots", "duration_s"]
        else:
            columns = list(rows[0])
        self.message.setText(note)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([field_label(key) for key in columns])
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(columns):
                value = row.get(key)
                if key == "status":
                    value = {"available": "Disponível", "unavailable": "Não se aplica / sem amostras"}.get(value, value)
                item = QTableWidgetItem(
                        "—"
                        if value is None
                        else (
                            format(value, ".9g")
                            if isinstance(value, float)
                            else str(value)
                        )
                    )
                item.setToolTip(str(row.get("reason") or row.get("state_metrics_source") or field_label(key)))
                self.table.setItem(i, j, item)
        self.series_combo.blockSignals(True)
        self.series_combo.clear()
        self.series = [k for k in rows[0] if any(type(row.get(k)) in (int, float) for row in rows)
                       and k not in ("snapshot", "time", "steps", "order", "value", "seed")]
        if data["kind"] == "trotter_noise":
            self.series.insert(0, "paired_infidelity")
        for key in self.series:
            self.series_combo.addItem(field_label(key), key)
        if data["kind"] == "mitigation_benchmark":
            self.series_combo.setCurrentIndex(max(0, self.series_combo.findData("absolute_error")))
        self.series_combo.blockSignals(False)
        self._plot()
        self.export_button.setEnabled(True)
        self.replay_button.setEnabled(not self._running)

    def _replay(self):
        if not self.data or not self.experiment or self._running:
            return
        if self.data.get("source_id") != self.experiment.id:
            self.message.setText("Abra a execução de origem antes de reproduzir esta análise.")
            return
        data, options = self.data, {}
        kind = data["kind"]
        if kind in ("convergence", "trotter_noise"):
            options = {"steps": [row["steps"] for row in data["rows"]]}
        elif kind == "sweep":
            options = {"parameter": data["parameter"], "values": list(dict.fromkeys(row["value"] for row in data["rows"])), "seeds": data["seeds"]}
        elif kind == "mitigation_benchmark":
            options = {"shots": data["config"]["shots"], "qubit": data["qubit"], "scale_factors": data["scale_factors"], "seed": data["provenance"]["effective_seed"]}
        self.requested.emit(kind, options)

    def _plot(self, *_):
        if not self.data:
            return
        rows = self.data["rows"]
        key = self.series_combo.currentData()
        if not key:
            return
        ax = self.canvas.reset_axes()
        kind = self.data["kind"]
        if kind == "mitigation_benchmark":
            selected = [r for r in rows if r.get("status") == "available" and type(r.get(key)) in (int, float)]
            xs = list(range(len(selected)))
            ax.bar(xs, [r[key] for r in selected], color=[PALETTE.primary, PALETTE.q2, PALETTE.q4, PALETTE.q3][:len(selected)])
            if key == "estimate":
                ax.errorbar(xs, [r[key] for r in selected], yerr=[r.get("stderr") or 0 for r in selected], fmt="none", color=PALETTE.text, capsize=5)
                ax.axhline(self.data["ideal_observable"], color=PALETTE.q3, ls="--", label="Referência ideal")
                ax.legend()
            ax.set_xticks(xs, [r["label"].replace(" ", "\n", 1) for r in selected], fontsize=9)
            ax.set_xlabel("Método · somente resultados disponíveis")
            ax.set_ylabel(field_label(key))
            self.canvas.draw_idle()
            return
        xkey = {"temporal": "time", "convergence": "steps", "sweep": "value", "trotter_noise": "steps"}[kind]
        if key == "paired_infidelity":
            for field, label, color in [("ideal_infidelity", "Trotter ideal × exata", PALETTE.primary), ("noisy_infidelity", "Ruidosa × exata", PALETTE.q2)]:
                ax.plot([r[xkey] for r in rows], [r[field] for r in rows], "o-", color=color, label=label)
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
        elif kind == "sweep":
            for seed in sorted(set(row["seed"] for row in rows)):
                selected = [r for r in rows if r["seed"] == seed]
                ax.plot(
                    [r[xkey] for r in selected],
                    [r[key] for r in selected],
                    "o-",
                    label=f"seed {seed}",
                    alpha=0.8,
                )
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
        else:
            ax.plot(
                [r[xkey] for r in rows],
                [np_nan(r.get(key)) for r in rows],
                "o-",
                color=PALETTE.primary,
            )
        ax.set_xlabel(field_label(xkey))
        if xkey == "time" and self.experiment is not None and self.experiment.config.circuit is not None:
            ax.set_xlabel("Índice da porta lógica (sem tempo físico)")
        ax.set_ylabel(field_label(key))
        self.canvas.draw_idle()

    def _select(self, row, column):
        if self.data and self.data["kind"] == "temporal":
            self.parent_window_frame(row)

    def parent_window_frame(self, row):
        window = self.window()
        if hasattr(window, "page_bloch"):
            window.page_bloch.slider.setValue(row)

    def select_frame(self, row):
        if (
            self.data
            and self.data["kind"] == "temporal"
            and row < self.table.rowCount()
        ):
            self.table.selectRow(row)

    def _export(self):
        if not self.data:
            return
        path, kind = QFileDialog.getSaveFileName(
            self, "Exportar análise", "analise.csv", "CSV (*.csv);;JSON (*.json)"
        )
        if not path:
            return
        from pathlib import Path
        if not Path(path).suffix:
            path += ".json" if "JSON" in kind else ".csv"
        try:
            from core.export import export_analysis
            export_analysis(self.data, path)
            self.message.setText("Análise exportada. CSV acompanha manifesto .metadata.json com configuração e proveniência." if path.lower().endswith(".csv") else "Análise completa exportada.")
        except (OSError, ValueError, TypeError) as exc:
            self.message.setText(str(exc))

    def set_running(self, running):
        self._running = running
        for w in (
            self.kind,
            self.parameter,
            self.values,
            self.steps,
            self.seeds,
            self.btn_run,
            self.benchmark_qubit,
            self.benchmark_shots,
        ):
            w.setEnabled(self.experiment is not None and not running)
        self.btn_run.setText("Calculando…" if running else "Calcular análise")
        self.btn_cancel.setVisible(running)
        self.btn_cancel.setEnabled(running)
        self.saved.setEnabled(not running)
        self.replay_button.setEnabled(self.data is not None and not running)
        self.progress.setVisible(running)
        if running:
            self.progress.setValue(0)


def np_nan(value):
    return float("nan") if value is None else value


def field_label(key):
    if key.startswith("entropy_q"):
        return "Entropia de q" + key.removeprefix("entropy_q") + " (bits)"
    return {
        "snapshot": "Snapshot",
        "time": "Tempo (ℏ=1)",
        "fidelity": "Fidelidade ao circuito ideal",
        "purity": "Pureza global",
        "energy": "Energia ⟨H⟩",
        "fidelity_exact": "Fidelidade à evolução exata",
        "trotter_infidelity": "Erro de Trotter (1−F ideal/exato)",
        "negativity_q0_rest": "Negatividade q0 | resto",
        "steps": "Passos Trotter",
        "infidelity": "Infidelidade à evolução exata",
        "depth": "Profundidade",
        "order": "Ordem Suzuki",
        "seed": "Semente",
        "sampled_Z0": "⟨Z0⟩ amostrado",
        "value": "Valor do parâmetro",
        "paired_infidelity": "Erro 1−F contra evolução exata (ideal e ruidoso)",
        "fidelity_ideal_exact": "Fidelidade Trotter ideal/exata",
        "fidelity_noisy_exact": "Fidelidade ruidosa/exata",
        "fidelity_noisy_ideal": "Fidelidade ruidosa/circuito ideal",
        "ideal_infidelity": "Erro Trotter ideal/exato (1−F)",
        "noisy_infidelity": "Erro ruidoso/exato (1−F)",
        "gate_count": "Portas unitárias",
        "ideal_runtime_s": "Tempo ideal (s)",
        "noisy_runtime_s": "Tempo ruidoso (s)",
        "method": "Método",
        "label": "Descrição",
        "status": "Disponibilidade",
        "reason": "Condição / limitação",
        "estimate": "Estimativa de ⟨Z⟩",
        "stderr": "Erro padrão de amostragem",
        "absolute_error": "Erro absoluto do observável",
        "circuits": "Circuitos por método",
        "shots": "Shots por método",
        "retained_shots": "Shots aceitos",
        "acceptance": "Fração amostral aceita",
        "acquisition_s": "Aquisição compartilhada (s)",
        "processing_s": "Processamento (s)",
        "duration_s": "Tempo equivalente do método (s)",
        "shared_samples": "Amostras compartilhadas",
        "state_metrics_source": "Origem das métricas de estado",
    }.get(key, key)

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
from gui.widgets.research_protocol import ProtocolPanel


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
        self.replay_context=None
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
            ("Mapa de calor de dois parâmetros", "heatmap"),
            ("Estabilidade da ZNE: viés e variância", "zne_stability"),
            ("Comparação com orçamento equivalente", "equal_budget"),
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
        self.x_parameter=QComboBox()
        self.y_parameter=QComboBox()
        for widget in (self.x_parameter,self.y_parameter):
            widget.addItems(["trotter_steps","p1","p2","t1_us","t2_us","J","h"])
        self.y_parameter.setCurrentText("p2")
        self.x_values=QLineEdit("1, 2, 4, 8")
        self.y_values=QLineEdit("0, 0.02, 0.05, 0.1")
        self.factor_sets=QLineEdit("1,3,5; 1,3,7")
        self.factor_sets.setToolTip("Conjuntos separados por ponto e vírgula; 3 a 5 fatores ímpares entre 1 e 9, incluindo 1.")
        self.shot_counts=QLineEdit("256, 1024")
        self.repetitions=QSpinBox()
        self.repetitions.setRange(2,10)
        self.repetitions.setValue(5)
        self.total_shots=QSpinBox()
        self.total_shots.setRange(5,1_000_000)
        self.total_shots.setValue(3072)
        self.research_widgets=[self.x_parameter,self.y_parameter,self.x_values,self.y_values,self.factor_sets,self.shot_counts,self.repetitions,self.total_shots]
        for label, w in [
            ("Análise", self.kind),
            ("Parâmetro da varredura", self.parameter),
            ("Valores da varredura", self.values),
            ("Sementes da varredura", self.seeds),
            ("Passos para convergência", self.steps),
            ("Observável do benchmark", self.benchmark_qubit),
            ("Shots por fator", self.benchmark_shots),
            ("Eixo X",self.x_parameter),("Valores X",self.x_values),
            ("Eixo Y",self.y_parameter),("Valores Y",self.y_values),
            ("Conjuntos de fatores ZNE",self.factor_sets),
            ("Shots por fator a investigar",self.shot_counts),
            ("Repetições com sementes distintas",self.repetitions),
            ("Orçamento total de shots por método",self.total_shots),
        ]:
            form.addRow(label, w)
        self.body().addLayout(form)
        self.body().addWidget(self.help)
        self.protocol=ProtocolPanel()
        self.body().addWidget(self.protocol)
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
        self.export_button = SecondaryButton("Exportar análise / figura")
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
            self.form.setRowVisible(widget, kind == "mitigation_benchmark" or (widget is self.benchmark_qubit and kind in ("zne_stability","equal_budget")))
        for widget in (self.x_parameter,self.y_parameter,self.x_values,self.y_values):
            self.form.setRowVisible(widget,kind=="heatmap")
        for widget in (self.factor_sets,self.repetitions):
            self.form.setRowVisible(widget,kind in ("zne_stability","equal_budget"))
        self.form.setRowVisible(self.shot_counts,kind=="zne_stability")
        self.form.setRowVisible(self.total_shots,kind=="equal_budget")
        self.help.setText({
            "temporal": "Inspecione os estados realmente simulados. Clique na curva ou na tabela para selecionar o mesmo snapshot em 3D.",
            "convergence": "Aumentar os passos reduz o erro de aproximação em muitos casos. Esta análise desliga o ruído e compara com exp(−iHt).",
            "sweep": "Altere um parâmetro por vez. p1/p2 são intensidades despolarizadoras; T₁/T₂ são tempos em µs. Sementes afetam contagens, não a incerteza das métricas do ensemble.",
            "trotter_noise": "Compare, nos mesmos passos, a aproximação ideal e a execução com o ruído da fonte contra a evolução exata. O melhor ponto é escolhido apenas entre os valores calculados.",
            "mitigation_benchmark": "Compare sem mitigação, ZNE linear/quadrática (variantes da mesma técnica) e verificação de simetria por paridade, quando aplicável. ZNE estima ⟨Z⟩ e não reconstrói um estado: sua fidelidade fica indisponível. As medições compartilhadas e os custos são registrados.",
            "heatmap":"Investigue dois parâmetros em até 64 pontos reais. Todos os pontos são validados antes de executar. As células exibem as coordenadas calculadas, sem interpolação física.",
            "zne_stability":"Varie fatores e shots com repetições amostradas independentes. Viés, variância amostral e RMSE são do estimador de Z contra a referência ideal, não da fidelidade do ensemble.",
            "equal_budget":"Sem mitigação e ZNE dispõem do mesmo total de shots por repetição. O orçamento da ZNE é dividido entre fatores; os ajustes compartilham amostras. Isso não iguala profundidade nem tempo de execução.",
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
            self.replay_context=None
            kind,options=self.analysis_options()
            self.requested.emit(kind, options)
        except ValueError as exc:
            self.message.setText("Revise os valores: use vírgula entre pontos, ponto decimal e ponto e vírgula entre conjuntos de fatores. "+str(exc))

    def analysis_options(self):
        kind=self.kind.currentData()
        options={}
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
        elif kind == "heatmap":
            options={"x_parameter":self.x_parameter.currentText(),"x_values":[float(x.strip()) for x in self.x_values.text().split(",")],
                     "y_parameter":self.y_parameter.currentText(),"y_values":[float(x.strip()) for x in self.y_values.text().split(",")]}
        elif kind in ("zne_stability","equal_budget"):
            options={"factor_sets":[[int(x.strip()) for x in group.split(",")] for group in self.factor_sets.text().split(";")],
                     "repetitions":self.repetitions.value(),"qubit":self.benchmark_qubit.value()}
            if kind=="zne_stability":
                options["shot_counts"]=[int(x.strip()) for x in self.shot_counts.text().split(",")]
            else:
                options["total_shots"]=self.total_shots.value()
        return kind,options

    def apply_options(self,kind,options):
        self.kind.setCurrentIndex(self.kind.findData(kind))
        for field,widget in (("steps",self.steps),("values",self.values),("seeds",self.seeds),("x_values",self.x_values),("y_values",self.y_values),("shot_counts",self.shot_counts)):
            if options.get(field) is not None:
                widget.setText(", ".join(str(v) for v in options[field]))
        for field,widget in (("parameter",self.parameter),("x_parameter",self.x_parameter),("y_parameter",self.y_parameter)):
            if field in options:
                widget.setCurrentText(options[field])
        for field,widget in (("qubit",self.benchmark_qubit),("shots",self.benchmark_shots),("repetitions",self.repetitions),("total_shots",self.total_shots)):
            if field in options:
                widget.setValue(options[field])
        if "factor_sets" in options:
            self.factor_sets.setText("; ".join(",".join(map(str,group)) for group in options["factor_sets"]))

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
                       and k not in ("snapshot", "time", "steps", "order", "value", "seed", "x", "y")]
        if data["kind"] == "trotter_noise":
            self.series.insert(0, "paired_infidelity")
        for key in self.series:
            self.series_combo.addItem(field_label(key), key)
        if data["kind"] == "mitigation_benchmark":
            self.series_combo.setCurrentIndex(max(0, self.series_combo.findData("absolute_error")))
        if data["kind"] in ("zne_stability","equal_budget"):
            self.series_combo.setCurrentIndex(max(0,self.series_combo.findData("rmse")))
        if data["kind"]=="heatmap":
            preferred="fidelity_exact" if "fidelity_exact" in self.series else "fidelity"
            self.series_combo.setCurrentIndex(max(0,self.series_combo.findData(preferred)))
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
        from copy import deepcopy
        self.replay_context=deepcopy(data.get("protocol",{}))
        kind = data["kind"]
        if kind in ("convergence", "trotter_noise"):
            options = {"steps": [row["steps"] for row in data["rows"]]}
            if kind=="trotter_noise":
                options["seed"]=data.get("options",{}).get("seed",data.get("provenance",{}).get("source_effective_seed"))
        elif kind == "sweep":
            options = {"parameter": data["parameter"], "values": list(dict.fromkeys(row["value"] for row in data["rows"])), "seeds": data["seeds"]}
        elif kind == "mitigation_benchmark":
            options = {"shots": data["config"]["shots"], "qubit": data["qubit"], "scale_factors": data["scale_factors"], "seed": data["provenance"]["effective_seed"]}
        elif kind in ("heatmap","zne_stability","equal_budget"):
            options=data["options"]
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
        if kind in ("heatmap","zne_stability","equal_budget"):
            from core.figures import analysis_figure
            analysis_figure(self.data,key,self.canvas.fig)
            self.canvas.fig.set_facecolor(PALETTE.bg)
            for axis in self.canvas.fig.axes:
                axis.set_facecolor(PALETTE.bg)
                axis.tick_params(colors=PALETTE.text_muted)
                axis.xaxis.label.set_color(PALETTE.text)
                axis.yaxis.label.set_color(PALETTE.text)
                axis.title.set_color(PALETTE.text)
            self.canvas.draw_idle()
            return
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
            self, "Exportar análise", "analise", "CSV (*.csv);;JSON (*.json);;LaTeX (*.tex);;Figura PNG (*.png);;Figura SVG (*.svg);;Figura PDF (*.pdf)"
        )
        if not path:
            return
        from pathlib import Path
        if not Path(path).suffix:
            path += next((ext for label,ext in [("JSON",".json"),("LaTeX",".tex"),("PNG",".png"),("SVG",".svg"),("PDF",".pdf")] if label in kind),".csv")
        try:
            from core.export import export_analysis
            if Path(path).suffix.lower()==".tex":
                from core.documentation import export_latex
                export_latex(self.data,path)
            elif Path(path).suffix.lower() in (".png",".svg",".pdf"):
                self.canvas.fig.savefig(path,dpi=180,bbox_inches="tight")
            else:
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
        for widget in self.research_widgets:
            widget.setEnabled(self.experiment is not None and not running)
        self.protocol.setEnabled(not running)
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
        "x":"Valor X", "y":"Valor Y", "factors":"Fatores efetivos",
        "shots_setting":"Shots configurados", "repetitions":"Repetições independentes",
        "mean_estimate":"Média de ⟨Z⟩", "bias":"Viés empírico", "sample_variance":"Variância amostral",
        "mse":"Erro quadrático médio empírico", "rmse":"Raiz do erro quadrático médio",
        "stderr_mean":"Erro padrão da média amostral", "out_of_range":"Estimativas fora de [-1,1]",
        "mean_reported_stderr":"Erro padrão previsto médio", "mean_absolute_error":"Erro absoluto médio",
        "shots_per_method":"Shots por método / repetição", "circuits_per_method":"Circuitos por método / repetição",
        "degrees_of_freedom":"Graus de liberdade residuais", "acquisition_group_s":"Aquisição total do grupo (s)",
        "mean_acquisition_s":"Aquisição média por método (s)","mean_processing_s":"Tempo médio do ajuste (s)",
        "mean_duration_s":"Aquisição + ajuste médios (s)",
    }.get(key, key)

"""Scientific tools operate on the selected run, preserving its result."""

from PySide6.QtCore import Signal, Qt
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
    QWidget, QVBoxLayout, QTabWidget, QFrame, QSizePolicy, QToolButton, QMenu, QScrollArea,
)
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton, SecondaryButton
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE
from gui.widgets.research_protocol import ProtocolPanel
from gui.widgets.analysis_guidance import PARAMETERS, STUDIES, ParameterCombo, artifact_options


class AnalysisPage(PageBase):
    requested = Signal(str, dict)
    cancel_requested = Signal()
    source_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Estudos e varreduras",
            "Use uma execução como referência para investigar precisão, ruído e mitigação.",
            parent,
        )
        self.experiment = None
        self.data = None
        self.series = []
        self._running = False
        self.replay_context=None
        self.context = QLabel("Abra uma execução para começar.")
        self.context.setWordWrap(True)
        self.context.setTextFormat(Qt.PlainText)
        source_row = QHBoxLayout()
        source_row.addWidget(self.context, 1)
        self.source_button = QToolButton()
        self.source_button.setText("Escolher execução")
        self.source_button.setAccessibleName("Escolher execução de referência do estudo")
        self.source_button.setPopupMode(QToolButton.InstantPopup)
        self.source_menu = QMenu(self.source_button)
        self.source_button.setMenu(self.source_menu)
        self._recent_sources = []
        source_row.addWidget(self.source_button)
        self.body().addLayout(source_row)
        self.set_recent_sources([])
        self.saved = QComboBox()
        self.saved.addItem("Resultados salvos desta execução", None)
        self.saved.setAccessibleName("Resultados de estudos salvos da execução selecionada")
        self.saved.currentIndexChanged.connect(self._open_saved)
        self.body().addWidget(self.saved)
        self.tabs = QTabWidget()
        def scroll_tab():
            area = QScrollArea()
            area.setFrameShape(QFrame.NoFrame)
            area.setWidgetResizable(True)
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            content = QWidget()
            layout = QVBoxLayout(content)
            area.setWidget(content)
            return area, layout

        self.configuration_tab, setup = scroll_tab()
        self.results_tab, results = scroll_tab()
        self.planning_tab, planning = scroll_tab()
        self.tabs.addTab(self.configuration_tab, "Configurar estudo")
        self.tabs.addTab(self.results_tab, "Resultados")
        self.tabs.addTab(self.planning_tab, "Planejamento")
        self.body().addWidget(self.tabs, 1)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form = form
        self.kind = QComboBox()
        self.kind.setAccessibleName("Objetivo do estudo")
        for key, (name, _) in STUDIES.items():
            self.kind.addItem(name, key)
            self.kind.setItemData(self.kind.count()-1, STUDIES[key][1], Qt.ToolTipRole)
        self.parameter = ParameterCombo(["p1", "p2", "J", "h", "t1_us", "t2_us", "trotter_steps"])
        self.parameter.setAccessibleName("Parâmetro a variar")
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
        self.help.setObjectName("FieldHint")
        self.x_parameter=ParameterCombo(["trotter_steps","p1","p2","t1_us","t2_us","J","h"])
        self.y_parameter=ParameterCombo(["trotter_steps","p1","p2","t1_us","t2_us","J","h"])
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
        self.parameter_hint = QLabel()
        self.parameter_hint.setWordWrap(True)
        self.parameter_hint.setObjectName("FieldHint")
        self.use_example = SecondaryButton("Usar exemplo de valores")
        self.use_example.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.use_example.setToolTip("Substitui apenas a lista de valores pelo exemplo do parâmetro escolhido. Não executa o estudo.")
        self.use_example.clicked.connect(lambda: self.values.setText(PARAMETERS[self.parameter.currentData()][1]))
        self.use_axis_examples = SecondaryButton("Usar exemplos dos eixos")
        self.use_axis_examples.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.use_axis_examples.setToolTip("Preenche as duas listas com exemplos; confirme a validade de T₁/T₂ para a fonte escolhida.")
        self.use_axis_examples.clicked.connect(self._axis_examples)
        for label, w in [
            ("Objetivo do estudo", self.kind),
            ("Parâmetro da varredura", self.parameter),
            ("Valores da varredura", self.values),
            ("Sementes da varredura", self.seeds),
            ("Passos para convergência", self.steps),
            ("Qubit para observar ⟨Z⟩", self.benchmark_qubit),
            ("Medições por fator (shots)", self.benchmark_shots),
            ("Eixo X",self.x_parameter),("Valores X",self.x_values),
            ("Eixo Y",self.y_parameter),("Valores Y",self.y_values),
            ("Conjuntos de fatores ZNE",self.factor_sets),
            ("Shots por fator a investigar",self.shot_counts),
            ("Repetições com sementes distintas",self.repetitions),
            ("Orçamento total de shots por método",self.total_shots),
        ]:
            form.addRow(label, w)
            if not w.accessibleName():
                w.setAccessibleName(label)
        form.addRow(self.parameter_hint)
        form.addRow(self.use_example)
        form.addRow(self.use_axis_examples)
        setup.addLayout(form)
        setup.addWidget(self.help)
        setup.addStretch()
        self.protocol=ProtocolPanel()
        plan_note = QLabel("Opcional: registre pergunta, hipótese, controles e referência no TCC. Salvar uma revisão guarda o plano; calcular um estudo produz outra evidência, vinculada à execução de origem.")
        plan_note.setWordWrap(True)
        plan_note.setObjectName("FieldHint")
        planning.addWidget(plan_note)
        planning.addWidget(self.protocol)
        planning.addStretch()
        self.btn_run = PrimaryButton("Calcular análise")
        self.btn_run.clicked.connect(self._request)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.btn_run)
        self.btn_cancel = SecondaryButton("Cancelar análise")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        actions.addWidget(self.btn_cancel)
        self.execution_bar = QFrame()
        self.execution_bar.setObjectName("ExecutionBar")
        footer = QVBoxLayout(self.execution_bar)
        footer.setContentsMargins(20, 10, 20, 12)
        self.availability = QLabel()
        self.availability.setWordWrap(True)
        self.availability.setObjectName("FieldHint")
        footer.addWidget(self.availability)
        footer.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setAccessibleName("Progresso da análise científica")
        footer.addWidget(self.progress)
        self._root.addWidget(self.execution_bar)
        self.result_summary = QLabel("Calcule um estudo ou selecione um resultado salvo desta execução.")
        self.result_summary.setWordWrap(True)
        self.result_summary.setObjectName("FieldHint")
        results.addWidget(self.result_summary)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        results.addWidget(self.message)
        self.series_combo = QComboBox()
        self.series_combo.currentIndexChanged.connect(self._plot)
        self.series_combo.setAccessibleName("Métrica exibida no gráfico do estudo")
        results.addWidget(self.series_combo)
        self.canvas = MplCanvas(height=3)
        self.canvas.setMinimumHeight(260)
        results.addWidget(self.canvas)
        self.canvas.mpl_connect("button_press_event", self._plot_clicked)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(180)
        self.table.cellClicked.connect(self._select)
        results.addWidget(self.table)
        self.export_button = SecondaryButton("Exportar análise / figura")
        self.export_button.clicked.connect(self._export)
        self.export_button.setEnabled(False)
        self.add_action(self.export_button)
        self.replay_button = SecondaryButton("Reproduzir análise")
        self.replay_button.setEnabled(False)
        self.replay_button.clicked.connect(self._replay)
        self.add_action(self.replay_button)
        self.kind.currentIndexChanged.connect(self._update_controls)
        for combo in (self.parameter, self.x_parameter, self.y_parameter):
            combo.currentIndexChanged.connect(self._parameter_guidance)
        self._parameter_guidance()
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
        for widget in (self.parameter_hint, self.use_example):
            self.form.setRowVisible(widget, kind == "sweep")
        self.form.setRowVisible(self.use_axis_examples, kind == "heatmap")
        self.help.setText(STUDIES[kind][1])
        if hasattr(self, "btn_run"):
            self._refresh_availability()

    def _axis_examples(self):
        for combo, field in ((self.x_parameter, self.x_values), (self.y_parameter, self.y_values)):
            field.setText(PARAMETERS[combo.currentData()][1])

    def _parameter_guidance(self, *_):
        for combo, field in ((self.parameter, self.values), (self.x_parameter, self.x_values), (self.y_parameter, self.y_values)):
            _, example, description = PARAMETERS[combo.currentData()]
            combo.setToolTip(description)
            field.setPlaceholderText("Exemplo: " + example)
            field.setToolTip(description + " Separe os pontos por vírgula e use ponto decimal. Exemplo: " + example)
        self.parameter_hint.setText(PARAMETERS[self.parameter.currentData()][2])
        if hasattr(self, "btn_run"):
            self._refresh_availability()

    def compatibility_issue(self):
        """Explica requisitos conhecidos antes de iniciar cálculos ou trocar tela."""
        if self.experiment is None:
            return "Selecione ou execute um experimento para usar sua configuração como referência."
        config, result = self.experiment.config, self.experiment.result
        if result.error:
            return "Esta execução falhou. Execute novamente antes de calcular um estudo."
        kind = self.kind.currentData()
        if kind == "temporal" and (not result.states or not result.times):
            return "Este estudo precisa de snapshots. Ative Salvar estados ao longo do tempo e execute novamente."
        if kind in ("convergence", "trotter_noise") and config.circuit is not None:
            return "Este estudo exige evolução por Hamiltoniano. Para um circuito livre, use métricas, ruído ou mitigação."
        parameters = [self.parameter.currentData()] if kind == "sweep" else [self.x_parameter.currentData(), self.y_parameter.currentData()] if kind == "heatmap" else []
        if config.circuit is not None and any(key in ("J", "h", "trotter_steps") for key in parameters):
            return "Circuitos livres não usam J, h ou passos Trotter. Escolha um parâmetro de ruído para esta fonte."
        if "h" in parameters and config.system.hamiltonian not in ("Ising", "Custom"):
            return "O campo h não participa deste Hamiltoniano. Escolha outro parâmetro ou uma fonte Ising/Custom."
        if kind == "heatmap" and parameters[0] == parameters[1]:
            return "Escolha parâmetros diferentes para os dois eixos do mapa."
        if kind == "heatmap" and set(parameters) & {"p1", "p2"} and set(parameters) & {"t1_us", "t2_us"}:
            return "Escolha parâmetros do mesmo modelo de ruído para os dois eixos."
        return ""

    def _refresh_availability(self):
        issue = self.compatibility_issue()
        self.btn_run.setEnabled(not self._running and not issue)
        self.btn_run.setToolTip(issue or "Calcula novos resultados a partir da fonte selecionada; não altera a execução original.")
        self.availability.setText("Calculando em segundo plano · cancele nesta tela para interromper." if self._running else issue or "Configuração disponível · o estudo usará a execução selecionada como referência.")

    def load_experiment(self, experiment):
        self.experiment = experiment
        self.data = None
        self.table.setRowCount(0)
        self.series_combo.clear()
        self.canvas.reset_axes()
        self.canvas.draw_idle()
        from data.workspace import experiment_title
        self.set_experiment_title(experiment_title(experiment))
        self.benchmark_qubit.setMaximum(experiment.config.system.num_qubits - 1)
        self.benchmark_shots.setValue(experiment.config.shots)
        self.message.clear()
        self.export_button.setEnabled(False)
        self.replay_button.setEnabled(False)
        self.result_summary.setText("Calcule um estudo ou selecione um resultado salvo desta execução.")
        self.tabs.setCurrentWidget(self.configuration_tab)
        self.set_running(self._running)

    def set_experiment_title(self, title):
        if self.experiment is None:
            self.context.setText("Selecione ou execute um experimento para começar.")
            return
        snapshots = len(self.experiment.result.states)
        status = f"{snapshots} snapshots disponíveis" if snapshots else "sem snapshots salvos"
        self.context.setText(f"Execução de referência: {title} · {status}")
        self.context.setToolTip("Identificador técnico: " + self.experiment.id)

    def set_recent_sources(self, sources):
        """Atualiza referências reais fornecidas pelo controlador, sem carregá-las."""
        self._recent_sources = list(sources)
        self.source_menu.clear()
        for identifier, title in self._recent_sources:
            action = self.source_menu.addAction(title.replace("&", "&&"))
            action.setData(identifier)
            action.triggered.connect(lambda checked=False, key=identifier: self.source_requested.emit(key) if not self._running else None)
        self.source_button.setEnabled(bool(self._recent_sources) and not self._running)
        self.source_button.setToolTip("Escolha uma execução salva para estudar seus resultados." if self._recent_sources else "Execute ou salve um experimento para escolher sua referência aqui.")

    def set_saved(self, paths):
        self.saved.blockSignals(True)
        self.saved.clear()
        self.saved.addItem("Resultados salvos desta execução", None)
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
            issue = self.compatibility_issue()
            if issue or self._running:
                self.availability.setText(issue or "Aguarde a tarefa atual.")
                return
            self.replay_context=None
            kind,options=self.analysis_options()
            self.tabs.setCurrentWidget(self.results_tab)
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
                "parameter": self.parameter.currentData(),
                "values": [float(x.strip()) for x in self.values.text().split(",")],
                "seeds": [int(x.strip()) for x in self.seeds.text().split(",")]
                if self.seeds.text().strip()
                else None,
            }
        elif kind == "heatmap":
            options={"x_parameter":self.x_parameter.currentData(),"x_values":[float(x.strip()) for x in self.x_values.text().split(",")],
                     "y_parameter":self.y_parameter.currentData(),"y_values":[float(x.strip()) for x in self.y_values.text().split(",")]}
        elif kind in ("zne_stability","equal_budget"):
            options={"factor_sets":[[int(x.strip()) for x in group.split(",")] for group in self.factor_sets.text().split(";")],
                     "repetitions":self.repetitions.value(),"qubit":self.benchmark_qubit.value()}
            if kind=="zne_stability":
                options["shot_counts"]=[int(x.strip()) for x in self.shot_counts.text().split(",")]
            else:
                options["total_shots"]=self.total_shots.value()
        return kind,options

    def apply_options(self,kind,options):
        if kind not in STUDIES:
            raise ValueError("Tipo de estudo não suportado.")
        self.kind.setCurrentIndex(self.kind.findData(kind))
        for field,widget in (("steps",self.steps),("values",self.values),("seeds",self.seeds),("x_values",self.x_values),("y_values",self.y_values),("shot_counts",self.shot_counts)):
            if options.get(field) is not None:
                widget.setText(", ".join(str(v) for v in options[field]))
            elif field == "seeds" and field in options:
                widget.clear()
        for field,widget in (("parameter",self.parameter),("x_parameter",self.x_parameter),("y_parameter",self.y_parameter)):
            if field in options:
                widget.setCurrentText(options[field])
        for field,widget in (("qubit",self.benchmark_qubit),("shots",self.benchmark_shots),("repetitions",self.repetitions),("total_shots",self.total_shots)):
            if field in options:
                value = options[field]
                if type(value) is not int:
                    raise ValueError("A entrada registrada " + field + " deve ser inteira.")
                widget.setRange(min(widget.minimum(), value), max(widget.maximum(), value))
                widget.setValue(value)
        if "factor_sets" in options:
            self.factor_sets.setText("; ".join(",".join(map(str,group)) for group in options["factor_sets"]))

    def show_analysis(self, data):
        from data.analyses import validate_analysis
        expected_source = self.experiment.id if self.experiment is not None and isinstance(data, dict) and data.get("source_id") else None
        validate_analysis(data, expected_source)
        options = artifact_options(data)
        # Valide entradas que serão representadas antes de substituir a evidência.
        for key in ("qubit", "shots", "repetitions", "total_shots"):
            if key in options and type(options[key]) is not int:
                raise ValueError("A entrada registrada " + key + " deve ser inteira.")
        for key in ("parameter", "x_parameter", "y_parameter"):
            if key in options and options[key] not in PARAMETERS:
                raise ValueError("Parâmetro registrado não suportado: " + str(options[key]))
        self.apply_options(data["kind"], options)
        self.data = data
        self.canvas.reset_axes()
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
        self.table.setHorizontalHeaderLabels([self._field_label(key) for key in columns])
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(columns):
                value = row.get(key)
                if key == "status":
                    value = {"available": "Disponível", "unavailable": "Não se aplica / sem amostras"}.get(value, value)
                if key == "method":
                    value = {"none": "Sem mitigação", "zne_linear": "ZNE linear", "zne_quadratic": "ZNE quadrática", "symmetry": "Verificação de paridade"}.get(value, value)
                item = QTableWidgetItem(
                        "—"
                        if value is None
                        else (
                            format(value, ".9g")
                            if isinstance(value, float)
                            else str(value)
                        )
                    )
                item.setToolTip(str(row.get("reason") or row.get("state_metrics_source") or self._field_label(key)))
                self.table.setItem(i, j, item)
        self.series_combo.blockSignals(True)
        self.series_combo.clear()
        self.series = [k for k in rows[0] if any(type(row.get(k)) in (int, float) for row in rows)
                       and k not in ("snapshot", "time", "steps", "order", "value", "seed", "x", "y")]
        if data["kind"] == "trotter_noise":
            self.series.insert(0, "paired_infidelity")
        for key in self.series:
            self.series_combo.addItem(self._field_label(key), key)
        if data["kind"] == "mitigation_benchmark":
            self.series_combo.setCurrentIndex(max(0, self.series_combo.findData("absolute_error")))
        if data["kind"] in ("zne_stability","equal_budget"):
            self.series_combo.setCurrentIndex(max(0,self.series_combo.findData("rmse")))
        if data["kind"]=="heatmap":
            preferred="fidelity_exact" if "fidelity_exact" in self.series else "fidelity"
            self.series_combo.setCurrentIndex(max(0,self.series_combo.findData(preferred)))
        self.series_combo.blockSignals(False)
        self._plot()
        if self.series_combo.currentData() is None:
            self.canvas.draw_idle()
        self.export_button.setEnabled(True)
        self._refresh_replay()
        self.result_summary.setText("Resultado selecionado: " + STUDIES[data["kind"]][0] + ". Reproduzir usa as entradas registradas; calcular um novo estudo usa os campos de Configurar.")
        self.tabs.setCurrentWidget(self.results_tab)

    def _field_label(self, key):
        config = self.data.get("config", {}) if self.data else {}
        circuit = config.get("circuit") if isinstance(config, dict) else None
        if key == "time" and (circuit is not None or (not config and self.experiment is not None and self.experiment.config.circuit is not None)):
            return "Índice da porta lógica (sem tempo físico)"
        return field_label(key)

    def replay_unavailable_reason(self):
        if not self.data:
            return "Selecione um resultado de estudo para reproduzir."
        data, kind = self.data, self.data["kind"]
        if self.experiment is None or data.get("source_id") != self.experiment.id:
            return "Abra a execução de origem para reproduzir este estudo."
        if not isinstance(data.get("config"), dict):
            return "Este resultado histórico não registra a configuração completa; ele continua disponível para consulta e exportação."
        try:
            from core.types import config_from_dict
            config_from_dict(data["config"])
        except (ValueError, TypeError, KeyError):
            return "A configuração registrada não permite reproduzir este resultado."
        if kind == "temporal" and not self.experiment.result.states:
            return "A reprodução temporal requer os snapshots da execução de origem."
        if kind == "sweep" and (data.get("parameter") not in PARAMETERS or not data.get("seeds")):
            return "Este resultado histórico não registra todos os parâmetros e sementes da varredura."
        if kind == "mitigation_benchmark" and not all(key in data for key in ("qubit", "scale_factors")):
            return "Faltam o qubit ou os fatores usados no benchmark histórico."
        if kind == "mitigation_benchmark" and data.get("provenance", {}).get("effective_seed") is None:
            return "A semente efetiva do benchmark histórico não foi registrada."
        required_options = {
            "heatmap": ("x_parameter", "x_values", "y_parameter", "y_values", "seed"),
            "zne_stability": ("factor_sets", "shot_counts", "repetitions", "qubit", "seed"),
            "equal_budget": ("factor_sets", "total_shots", "repetitions", "qubit", "seed"),
        }.get(kind, ())
        if required_options and (not isinstance(data.get("options"), dict) or any(key not in data["options"] for key in required_options)):
            return "Este resultado histórico não registra as opções necessárias para reproduzir o estudo."
        if kind == "trotter_noise" and data.get("options", {}).get("seed", data.get("provenance", {}).get("source_effective_seed")) is None:
            return "A semente do estudo pareado histórico não foi registrada."
        return ""

    def _refresh_replay(self):
        issue = self.replay_unavailable_reason()
        self.replay_button.setEnabled(not self._running and not issue)
        self.replay_button.setToolTip(issue or "Cria outra evidência com os parâmetros e sementes registrados no resultado selecionado.")

    def _replay(self):
        if not self.data or not self.experiment or self._running:
            return
        issue = self.replay_unavailable_reason()
        if issue:
            self.message.setText(issue)
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
            for seed in sorted(set(row.get("seed") for row in rows), key=lambda value: (-1 if value is None else value)):
                selected = [r for r in rows if r.get("seed") == seed]
                ax.plot(
                    [r[xkey] for r in selected],
                    [r[key] for r in selected],
                    "o-",
                    label=f"semente {seed}" if seed is not None else "semente não registrada",
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
        ax.set_xlabel(self._field_label(xkey))
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
        self.source_button.setEnabled(bool(self._recent_sources) and not running)
        self.source_menu.setEnabled(not running)
        if running:
            self.source_menu.close()
        for w in (
            self.kind,
            self.parameter,
            self.values,
            self.steps,
            self.seeds,
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
        for widget in (self.use_example, self.use_axis_examples):
            widget.setEnabled(self.experiment is not None and not running)
        self._refresh_availability()
        self._refresh_replay()
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

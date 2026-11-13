from core.types import system_label
from data.workspace import experiment_title
from PySide6.QtCore import Qt, Signal, QSignalBlocker, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget, QTabBar, QWidget, QVBoxLayout, QSlider, QCheckBox, QPushButton, QPlainTextEdit,
)
from gui.pages.base import PageBase
from gui.widgets.flow_layout import FlowLayout
from gui.formatting import quantity, timestamp
from gui.widgets.plot_canvas import MplCanvas,style_axes
from gui.theme import PALETTE
from gui.widgets.data_table import configure_table
from gui.widgets.content_tabs import ContentTabs


from core.comparison import incompatibility


class ComparisonPage(PageBase):
    prepare_requested = Signal(str,str)
    documentation_requested = Signal()
    def __init__(self, parent=None):
        super().__init__(
            "Comparações",
            "Compare execuções com o mesmo sistema e protocolo, variando ruído e amostragem.",
            parent,
        )
        row = FlowLayout()
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
        self.comparison_mode = QComboBox()
        self.comparison_mode.setMinimumContentsLength(18)
        self.comparison_mode.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.comparison_mode.addItem("Comparação controlada · mesmo circuito e protocolo","controlled")
        self.comparison_mode.addItem("Convergência · variar passos ou ordem de Trotter","trotter")
        self.comparison_mode.setAccessibleName("Critério científico da comparação")
        row.add_group(QLabel("Critério"), self.comparison_mode)
        self.comparison_mode.setToolTip(self.comparison_mode.currentText())
        self.comparison_mode.currentIndexChanged.connect(lambda *_: self.comparison_mode.setToolTip(self.comparison_mode.currentText()))
        self.comparison_mode.currentIndexChanged.connect(self._compare)
        self.message = QLabel("São necessárias duas execuções.")
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName('SectionSubtitle')
        self.body().addWidget(self.summary)
        tools=QHBoxLayout()
        self.btn_prepare=QPushButton("Carregar estados e curvas")
        self.btn_prepare.clicked.connect(self._request_prepare)
        self.btn_document=QPushButton("Documentar comparação")
        self.btn_document.clicked.connect(self.documentation_requested.emit)
        tools.addWidget(self.btn_prepare)
        tools.addWidget(self.btn_document)
        self.body().addLayout(tools)
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["Métrica", "A", "B", "B − A"])
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        configure_table(self.metrics_table)

        self.tabs=ContentTabs()
        self.canvas = MplCanvas()
        hist=QWidget()
        layout=QVBoxLayout(hist)
        self.hist_layout=QComboBox()
        self.hist_layout.addItems(["Distribuições sobrepostas","Distribuições lado a lado"])
        self.hist_layout.currentIndexChanged.connect(self._compare)
        hist_tools=QHBoxLayout()
        hist_tools.addWidget(self.hist_layout,1)
        hist_tools.addWidget(self.canvas.exploration_button(hist))
        layout.addLayout(hist_tools)
        self.canvas.set_value_lookup(self._histogram_value)
        layout.addWidget(self.canvas)
        self.tabs.addTab(hist,"Distribuições")
        self.curve_canvas=MplCanvas()
        self.tabs.addTab(self.curve_canvas,"Curvas temporais")
        bloch=QWidget()
        content=QVBoxLayout(bloch)
        self.frame_label=QLabel("Carregue os estados para visualizar as duas execuções.")
        self.frame_label.setWordWrap(True)
        content.addWidget(self.frame_label)
        controls=QHBoxLayout()
        self.play=QPushButton("Reproduzir snapshots")
        self.play.clicked.connect(self._play)
        self.camera_sync=QCheckBox("Sincronizar câmeras")
        self.camera_sync.setChecked(True)
        self.focus=QComboBox()
        self.focus.addItem("Todos os qubits",-1)
        self.focus.currentIndexChanged.connect(self._focus)
        controls.addWidget(self.play)
        controls.addWidget(self.camera_sync)
        controls.addWidget(self.focus)
        content.addLayout(controls)
        from gui.widgets.bloch_canvas import BlochCanvas
        scenes=QHBoxLayout()
        self.scenes=[BlochCanvas(),BlochCanvas()]
        self.scene_labels=[]
        for i,scene in enumerate(self.scenes):
            scene.focus_changed.connect(self._scene_focus_changed)
            pane=QWidget()
            pane_layout=QVBoxLayout(pane)
            pane_layout.setContentsMargins(0,0,0,0)
            caption=QLabel("AB"[i])
            caption.setWordWrap(True)
            self.scene_labels.append(caption)
            pane_layout.addWidget(caption)
            pane_layout.addWidget(scene,1)
            scenes.addWidget(pane,1)
            scene.camera_changed.connect(lambda i=i:self._sync_camera(i))
        content.addLayout(scenes)
        self.slider=QSlider(Qt.Horizontal)
        self.slider.setAccessibleName("Snapshot sincronizado das execuções A e B")
        self.slider.valueChanged.connect(self._frame)
        content.addWidget(self.slider)
        self.tabs.addTab(bloch,"Bloch lado a lado")
        self.differences=QPlainTextEdit()
        self.differences.setReadOnly(True)
        self.tabs.addTab(self.differences,"Configurações e referências")
        self.observable_canvas=MplCanvas()
        self.tabs.addTab(self.observable_canvas,"Observáveis ZNE")
        self.tabs.addTab(self.metrics_table, "Métricas numéricas")
        self.view_selector = QComboBox()
        self.view_selector.setAccessibleName("Visualização da comparação")
        for i in range(self.tabs.count()):
            self.view_selector.addItem(self.tabs.tabText(i), i)
        self.tabs.tabBar().hide()
        self.view_selector.currentIndexChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.view_selector.setCurrentIndex)
        self.view_selector.hide()
        self.view_tabs = QTabBar()
        self.view_tabs.setObjectName("ViewTabs")
        self.view_tabs.setUsesScrollButtons(True)
        self.view_tabs.setAccessibleName("Visualização da comparação")
        for title in ("Distribuições", "Curvas", "Bloch", "Configuração", "ZNE", "Métricas"):
            self.view_tabs.addTab(title)
        self.view_tabs.currentChanged.connect(self.view_selector.setCurrentIndex)
        self.view_selector.currentIndexChanged.connect(self.view_tabs.setCurrentIndex)
        self.body().addWidget(self.view_tabs)
        self.tabs.setMinimumHeight(340)
        self.body().addWidget(self.tabs,1)
        self.full_data=None
        self._running = False
        self._desired_focus = -1
        self._suppress_load = False
        self._requested_pair = None
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.setInterval(120)
        self._load_timer.timeout.connect(self._request_prepare)
        self.tabs.currentChanged.connect(self._tab_selected)
        self.timer=QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self._tick)
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
                combo.setItemData(combo.count() - 1, f"{timestamp(e.created_at)} · {system_label(e.config)}", Qt.ToolTipRole)
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
        previous=self.full_data
        self.timer.stop()
        self.play.setText("Reproduzir snapshots")
        self.full_data=None
        self._load_timer.stop()
        self._requested_pair = None
        self._clear_state_views()
        self.slider.setEnabled(False)
        self.play.setEnabled(False)
        self.metrics_table.setRowCount(0)
        ax = self.canvas.reset_axes()
        a, b = (
            self.records.get(self.first_run.currentData()),
            self.records.get(self.second_run.currentData()),
        )
        error = (
            "São necessárias duas execuções."
            if a is None or b is None
            else incompatibility(a, b, mode=self.comparison_mode.currentData())
        )
        if error:
            self.summary.clear()
            self._placeholder(self.observable_canvas, "A comparação precisa de duas execuções compatíveis.")
            self.differences.setPlainText(error)
            self.btn_prepare.setEnabled(False)
            self.btn_document.setEnabled(False)
            self.message.setText(error)
            self.canvas.draw()
            return
        note = "Comparação compatível. Distribuições normalizadas pelo total observado de cada execução; escala comum de 0 a 1. "
        note += f"A: {a.config.shots} shots / {a.duration_s:.4g} s · B: {b.config.shots} shots / {b.duration_s:.4g} s. "
        if self.comparison_mode.currentData() == "trotter":
            note += "As curvas comparam com a evolução exata do Hamiltoniano. Grades temporais diferentes não são interpoladas. "
        if a.result.mitigation or b.result.mitigation:
            note += " Os registros ZNE mantêm as métricas da simulação de origem; não são estados mitigados."
        self.message.setText(note)
        if not (a.result.mitigation or b.result.mitigation):
            self._placeholder(self.observable_canvas, "Nenhuma das execuções contém uma análise ZNE.\nSelecione um registro com mitigação para comparar observáveis.")
        if a.result.mitigation or b.result.mitigation:
            from core.figures import zne_comparison_figure
            zne_comparison_figure([a,b],self.observable_canvas.fig)
            for axis in self.observable_canvas.fig.axes:
                style_axes(axis)
                legend=axis.get_legend()
                if legend:
                    legend.get_frame().set_facecolor(PALETTE.surface)
                    for text in legend.get_texts():
                        text.set_color(PALETTE.text)
            self.observable_canvas.draw_idle()
        self.btn_prepare.setEnabled(not self._running)
        self.btn_document.setEnabled(False)
        from dataclasses import asdict
        import json
        def mitigation_summary(exp):
            return {key:value for key,value in (exp.result.mitigation or {}).items() if key in ("method","qubit","shots","seed","scale_factors","extrapolated","extrapolated_stderr","ideal_observable")}
        self.differences.setPlainText(json.dumps({"A":{"nome":experiment_title(a,self.annotations),"config":asdict(a.config),"mitigation":mitigation_summary(a)},"B":{"nome":experiment_title(b,self.annotations),"config":asdict(b.config),"mitigation":mitigation_summary(b)},"reference":"Fidelidade compara o próprio circuito ideal de cada execução. Registros ZNE preservam estados da fonte. Contagens/folding completos ficam nos arquivos JSON."},ensure_ascii=False,indent=2))
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
                "—" if x is None else quantity(x),
                "—" if y is None else quantity(y),
                "—" if x is None or y is None else quantity(y-x),
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                raw = (label, x, y, None if x is None or y is None else y-x)[col]
                item.setToolTip(str(raw) if raw is not None else "Não disponível")
                self.metrics_table.setItem(row, col, item)
        deltas = []
        for name, key in [('Fidelidade', 'fidelity'), ('Pureza', 'purity'), ('Energia', 'energy')]:
            x, y = getattr(a.result, key), getattr(b.result, key)
            deltas.append(f"Δ {name}: {quantity(None if x is None or y is None else y-x)}")
        self.summary.setText("B − A · " + " · ".join(deltas))
        self.metrics_table.resizeRowsToContents()

        from core.figures import histogram_figure
        from gui.widgets.plot_canvas import style_figure
        histogram_figure((a, b), side_by_side=self.hist_layout.currentIndex() == 1,
                         fig=self.canvas.fig, colors=(PALETTE.primary, PALETTE.q2), label_size=10)
        style_figure(self.canvas.fig)
        self.canvas.draw()
        if previous and previous.get("mode","controlled") == self.comparison_mode.currentData() and tuple(e.id for e in previous["experiments"])==(a.id,b.id):
            self.full_data=previous
            self.set_full_data(previous)
        elif self.tabs.currentIndex() in (1, 2) and not self._suppress_load:
            self._load_timer.start()

    def _histogram_value(self,event):
        for ax in self.canvas.fig.axes:
            if ax is not event.inaxes:
                continue
            for bar in ax.patches:
                if hasattr(bar,"_observed") and bar.contains(event)[0]:
                    run,state,count,total=bar._observed
                    frequency=count/total if total else 0
                    return f"Execução {run} · |{state}⟩\nContagens: {count} de {total}\nFrequência observada: {frequency:.16g} ({frequency*100:.12g}%)"
        return None

    def set_full_data(self,data):
        identifiers=tuple(e.id for e in data["experiments"])
        if identifiers!=(self.first_run.currentData(),self.second_run.currentData()) or data.get("mode","controlled") != self.comparison_mode.currentData():
            return
        self.full_data=data
        self._requested_pair = None
        self._load_timer.stop()
        self.focus.setEnabled(True)
        for scene in self.scenes:
            scene.setEnabled(True)
        for i,exp in enumerate(data["experiments"]):
            self.scene_labels[i].setText(f"{'AB'[i]} · {experiment_title(exp,self.annotations)} · "+(exp.config.noise.kind if exp.config.noise.enabled else "Ideal"))
            self.scene_labels[i].setToolTip(exp.id)
        for scene in self.scenes:
            blocker=QSignalBlocker(scene)
            scene.setup(data["experiments"][0].config.system.num_qubits)
            del blocker
        blocker=QSignalBlocker(self.focus)
        self.focus.clear()
        self.focus.addItem("Todos os qubits",-1)
        for q in range(data["experiments"][0].config.system.num_qubits):
            self.focus.addItem(f"q{q}",q)
        self.focus.setCurrentIndex(max(0, self.focus.findData(self._desired_focus)))
        del blocker
        self._focus()
        self.slider.setRange(0,len(data["vectors"][0])-1 if data["synchronous"] else 0)
        blocker=QSignalBlocker(self.slider)
        self.slider.setValue(0)
        del blocker
        self.slider.setEnabled(data["synchronous"])
        self.play.setEnabled(data["synchronous"])
        self.btn_document.setEnabled(not self._running)
        from core.figures import temporal_figure
        from gui.widgets.plot_canvas import style_figure
        temporal_figure(data['experiments'], reference='exact' if data.get('mode') == 'trotter' else 'circuit',
                        fig=self.curve_canvas.fig, curves=data['curves'], colors=(PALETTE.primary, PALETTE.q2), label_size=10)
        style_figure(self.curve_canvas.fig)
        self.curve_canvas.draw_idle()
        self._frame(0)
        if not any(exp.result.states for exp in data["experiments"]):
            self._placeholder(self.curve_canvas, "Estas execuções não salvaram snapshots.\nReexecute com snapshots para obter curvas temporais.")

    def _placeholder(self, canvas, message):
        ax = canvas.reset_axes()
        ax.text(.5, .5, message, transform=ax.transAxes, ha="center", va="center", wrap=True, color=PALETTE.text_muted)
        ax.set_axis_off()
        canvas.draw_idle()

    def _clear_state_views(self):
        self._placeholder(self.curve_canvas, "Selecione esta aba para carregar as curvas das execuções.\nAs curvas dependem dos snapshots salvos.")
        self.frame_label.setText("Selecione esta aba para carregar os estados de A e B.")
        self.focus.setEnabled(False)
        for scene, label in zip(self.scenes, self.scene_labels):
            scene.setEnabled(False)
            scene.ax.clear()
            scene.ax.text2D(.5, .5, "Estados ainda não carregados", transform=scene.ax.transAxes, ha="center", color=PALETTE.text_muted)
            scene.draw_idle()
            label.setText("Execução aguardando carregamento")

    def _tab_selected(self, index):
        if index in (1, 2) and self.full_data is None:
            self._load_timer.start()

    def _request_prepare(self):
        a, b = self.records.get(self.first_run.currentData()), self.records.get(self.second_run.currentData())
        if a is None or b is None or incompatibility(a, b, mode=self.comparison_mode.currentData()):
            return
        pair = (a.id, b.id)
        request_key = (*pair,self.comparison_mode.currentData())
        if request_key == self._requested_pair:
            return
        self._requested_pair = request_key
        self.frame_label.setText("Carregando os estados selecionados…")
        self._placeholder(self.curve_canvas, "Preparando as curvas dos registros selecionados…")
        self.prepare_requested.emit(*pair)

    def _frame(self,index):
        data=self.full_data
        if data is None:
            return
        for run,scene in enumerate(self.scenes):
            k=index if data["synchronous"] else len(data["vectors"][run])-1
            scene.update_frame(data["vectors"][run][k],record_trail=False,ideal_vectors=data["ideal_vectors"][run][k])
        self.frame_label.setText((f"Snapshot {index} · instante {data['curves'][0][index]['time']:g} · A e B nos mesmos instantes reais." if data["synchronous"] else "Estados finais. Snapshots ausentes ou em grades distintas: sincronização temporal desativada.")+" Linha contínua: simulado; tracejada: ideal de cada circuito.")

    def _sync_camera(self,index):
        if self.full_data is None or not self.camera_sync.isChecked():
            return
        other=self.scenes[1-index]
        blocker=QSignalBlocker(other)
        other.restore_camera(**self.scenes[index].camera_state())
        del blocker

    def _focus(self,*_):
        self._desired_focus = self.focus.currentData() if self.focus.currentData() is not None else -1
        for scene in self.scenes:
            scene.set_focus(self.focus.currentData() if self.focus.currentData() is not None else -1)

    def _scene_focus_changed(self, index):
        if getattr(self, "_syncing_focus", False):
            return
        self._syncing_focus = True
        try:
            blocker = QSignalBlocker(self.focus)
            self.focus.setCurrentIndex(max(0, self.focus.findData(index)))
            del blocker
            self._desired_focus = index
            for scene in self.scenes:
                if scene.focus != index:
                    scene.set_focus(index)
        finally:
            self._syncing_focus = False

    def _play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play.setText("Reproduzir snapshots")
        elif self.full_data and self.full_data["synchronous"]:
            if self.slider.value()==self.slider.maximum():
                self.slider.setValue(0)
            self.timer.start()
            self.play.setText("Pausar")

    def _tick(self):
        if self.slider.value()>=self.slider.maximum():
            self.timer.stop()
            self.play.setText("Reproduzir snapshots")
        else:
            self.slider.setValue(self.slider.value()+1)

    def collect_view_preferences(self):
        return {
            "hist_layout": self.hist_layout.currentIndex(),
            "tab": self.tabs.currentIndex(),
            "camera_sync": self.camera_sync.isChecked(),
            "focus": self._desired_focus,
            "comparison_mode": self.comparison_mode.currentData(),
        }

    def apply_view_preferences(self, values):
        if not isinstance(values, dict):
            return
        blockers = [QSignalBlocker(widget) for widget in (self.hist_layout, self.tabs, self.camera_sync, self.focus,self.comparison_mode)]
        self.comparison_mode.setCurrentIndex(max(0,self.comparison_mode.findData(values.get("comparison_mode","controlled"))))
        for key, widget in (("hist_layout", self.hist_layout), ("tab", self.tabs)):
            index = values.get(key, 0)
            if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < widget.count():
                widget.setCurrentIndex(index)
        if isinstance(values.get("camera_sync"), bool):
            self.camera_sync.setChecked(values["camera_sync"])
        focus = values.get("focus", -1)
        self._desired_focus = focus if isinstance(focus, int) and not isinstance(focus, bool) and -1 <= focus <= 5 else -1
        index = self.focus.findData(self._desired_focus)
        if index >= 0:
            self.focus.setCurrentIndex(index)
        del blockers
        selector_block = QSignalBlocker(self.view_selector)
        self.view_selector.setCurrentIndex(self.tabs.currentIndex())
        tabs_block = QSignalBlocker(self.view_tabs)
        self.view_tabs.setCurrentIndex(self.tabs.currentIndex())
        del tabs_block
        del selector_block
        self._suppress_load = True
        try:
            self._compare()
        finally:
            self._suppress_load = False

    def showEvent(self, event):
        super().showEvent(event)
        self._tab_selected(self.tabs.currentIndex())

    def hideEvent(self,event):
        self._load_timer.stop()
        self.timer.stop()
        self.play.setText("Reproduzir snapshots")
        super().hideEvent(event)

    def set_running(self,running):
        self._running = running
        for widget in (self.first_run,self.second_run,self.hist_layout):
            widget.setEnabled(not running)
        a, b = self.records.get(self.first_run.currentData()), self.records.get(self.second_run.currentData())
        self.btn_prepare.setEnabled(not running and a is not None and b is not None and not incompatibility(a,b))
        self.btn_document.setEnabled(not running and self.full_data is not None)
        if not running:
            if self._requested_pair is not None and self.full_data is None:
                self._clear_state_views()
            self._requested_pair = None

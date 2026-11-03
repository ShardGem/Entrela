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
    QTabWidget, QWidget, QVBoxLayout, QSlider, QCheckBox, QPushButton, QPlainTextEdit,
)
from gui.pages.base import PageBase
from gui.widgets.plot_canvas import MplCanvas,style_axes
from gui.theme import PALETTE


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
        tools=QHBoxLayout()
        self.btn_prepare=QPushButton("Carregar estados e curvas")
        self.btn_prepare.clicked.connect(lambda: self.prepare_requested.emit(self.first_run.currentData() or "",self.second_run.currentData() or ""))
        self.btn_document=QPushButton("Documentar comparação")
        self.btn_document.clicked.connect(self.documentation_requested.emit)
        tools.addWidget(self.btn_prepare)
        tools.addWidget(self.btn_document)
        self.body().addLayout(tools)
        self.metrics_table = QTableWidget(0, 4)
        self.metrics_table.setHorizontalHeaderLabels(["Métrica", "A", "B", "B − A"])
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.body().addWidget(self.metrics_table)
        self.tabs=QTabWidget()
        self.canvas = MplCanvas()
        hist=QWidget()
        layout=QVBoxLayout(hist)
        self.hist_layout=QComboBox()
        self.hist_layout.addItems(["Distribuições sobrepostas","Distribuições lado a lado"])
        self.hist_layout.currentIndexChanged.connect(self._compare)
        layout.addWidget(self.hist_layout)
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
        self.tabs.setMinimumHeight(420)
        self.body().addWidget(self.tabs,1)
        self.full_data=None
        self.tabs.setTabEnabled(1,False)
        self.tabs.setTabEnabled(2,False)
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
        previous=self.full_data
        self.timer.stop()
        self.play.setText("Reproduzir snapshots")
        self.full_data=None
        self.tabs.setTabEnabled(1,False)
        self.tabs.setTabEnabled(2,False)
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
            else incompatibility(a, b)
        )
        if error:
            self.tabs.setTabEnabled(4,False)
            self.btn_prepare.setEnabled(False)
            self.btn_document.setEnabled(False)
            self.message.setText(error)
            self.canvas.draw()
            return
        note = "Comparação compatível. Distribuições normalizadas pelo número observado de medições. "
        note += f"A: {a.config.shots} shots / {a.duration_s:.4g} s · B: {b.config.shots} shots / {b.duration_s:.4g} s. "
        if a.result.mitigation or b.result.mitigation:
            note += " Os registros ZNE mantêm as métricas da simulação de origem; não são estados mitigados."
        self.message.setText(note)
        self.tabs.setTabEnabled(4,bool(a.result.mitigation or b.result.mitigation))
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
        self.btn_prepare.setEnabled(True)
        self.btn_document.setEnabled(False)
        from dataclasses import asdict
        import json
        def mitigation_summary(exp):
            return {key:value for key,value in (exp.result.mitigation or {}).items() if key in ("method","qubit","shots","seed","scale_factors","extrapolated","extrapolated_stderr","ideal_observable","source_experiment_id")}
        self.differences.setPlainText(json.dumps({"A":{"id":a.id,"config":asdict(a.config),"mitigation":mitigation_summary(a)},"B":{"id":b.id,"config":asdict(b.config),"mitigation":mitigation_summary(b)},"reference":"Fidelidade compara o próprio circuito ideal de cada execução. Registros ZNE preservam estados da fonte. Contagens/folding completos ficam nos arquivos JSON."},ensure_ascii=False,indent=2))
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
        self.metrics_table.resizeRowsToContents()
        self.metrics_table.setFixedHeight(self.metrics_table.horizontalHeader().height()+sum(self.metrics_table.rowHeight(i) for i in range(3))+6)
        keys = sorted(set(a.result.counts or {}) | set(b.result.counts or {}))
        for i, e in enumerate((a, b)):
            if self.hist_layout.currentIndex()==1:
                if i==0:
                    self.canvas.fig.clear()
                ax=self.canvas.fig.add_subplot(1,2,i+1)
            total = sum((e.result.counts or {}).values())
            xs = [j + ((i - 0.5) * 0.36 if self.hist_layout.currentIndex()==0 else 0) for j in range(len(keys))]
            ax.bar(
                xs,
                [
                    (e.result.counts or {}).get(k, 0) / total if total else 0
                    for k in keys
                ],
                width=0.35 if self.hist_layout.currentIndex()==0 else .7,
                label="A" if i == 0 else "B",
                color=PALETTE.primary if i == 0 else PALETTE.q2,
            )
        for ax in self.canvas.fig.axes:
            style_axes(ax)
            ax.set_xticks(range(len(keys)), keys, rotation=90 if len(keys) > 8 else 0)
            ax.set_ylabel("Frequência observada")
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
        self.canvas.draw()
        if previous and tuple(e.id for e in previous["experiments"])==(a.id,b.id):
            self.full_data=previous
            self.tabs.setTabEnabled(1,True)
            self.tabs.setTabEnabled(2,True)
            self.slider.setEnabled(previous["synchronous"])
            self.play.setEnabled(previous["synchronous"])
            self.btn_document.setEnabled(True)

    def set_full_data(self,data):
        identifiers=tuple(e.id for e in data["experiments"])
        if identifiers!=(self.first_run.currentData(),self.second_run.currentData()):
            return
        self.full_data=data
        self.tabs.setTabEnabled(1,True)
        self.tabs.setTabEnabled(2,True)
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
        del blocker
        self.slider.setRange(0,len(data["vectors"][0])-1 if data["synchronous"] else 0)
        self.slider.setEnabled(data["synchronous"])
        self.play.setEnabled(data["synchronous"])
        self.btn_document.setEnabled(True)
        self.curve_canvas.fig.clear()
        for index,key in enumerate(("fidelity","purity","energy")):
            ax=self.curve_canvas.fig.add_subplot(3,1,index+1)
            style_axes(ax)
            for run,rows in enumerate(data["curves"]):
                exp=data["experiments"][run]
                if not exp.result.states:
                    continue
                points=[r for r in rows if r[key] is not None]
                if points:
                    ax.plot([r["time"] for r in points],[r[key] for r in points],label="AB"[run],color=PALETTE.primary if run==0 else PALETTE.q2)
            ax.set_ylabel({"fidelity":"F ao circuito ideal","purity":"Pureza","energy":"Energia"}[key])
            if ax.lines:
                ax.legend(facecolor=PALETTE.surface,labelcolor=PALETTE.text)
            ax.set_xlabel("Índice da porta" if data["experiments"][0].config.circuit else "Tempo (ℏ=1)")
        self.curve_canvas.draw_idle()
        self._frame(0)

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
        for scene in self.scenes:
            scene.set_focus(self.focus.currentData() if self.focus.currentData() is not None else -1)

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

    def hideEvent(self,event):
        self.timer.stop()
        self.play.setText("Reproduzir snapshots")
        super().hideEvent(event)

    def set_running(self,running):
        for widget in (self.first_run,self.second_run,self.hist_layout,self.btn_prepare):
            widget.setEnabled(not running)
        self.btn_document.setEnabled(not running and self.full_data is not None)

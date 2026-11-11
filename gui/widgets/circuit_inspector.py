"""Read-only inspection shared by the circuit workspace and experiment history."""
from PySide6.QtCore import Signal, QSignalBlocker, Qt, QTimer, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QScrollArea, QFileDialog, QCheckBox
from core.circuit_inspection import inspect_circuit, execution_circuit
from core.circuit_document import GATE_HELP
from data.workspace import experiment_title
from gui.widgets.circuit_canvas import CircuitCanvas, angle_label
from gui.widgets.button import PrimaryButton, GhostButton
from gui.widgets.flow_layout import FlowLayout


class CircuitInspector(QWidget):
    snapshot_requested = Signal(int)

    def __init__(self, parent=None, *, snapshots_action=False):
        super().__init__(parent)
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(0)
        self._layout_timer.timeout.connect(self._fit_controls)
        self.operations = []
        self.snapshots = False
        self.experiment = None
        self.selected = -1
        self.page_size = 100
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.context = QLabel("Execute um experimento para explorar seu circuito.")
        self.context.setWordWrap(True)
        self.context.setTextFormat(Qt.PlainText)
        layout.addWidget(self.context)
        tools = FlowLayout()
        self.controls = QWidget()
        self.controls.setLayout(tools)
        self.phase_label = QLabel("Fase global: —")
        tools.addWidget(self.phase_label)
        self.jump = QSpinBox()
        self.jump.setRange(1, 1)
        self.jump.setPrefix("Porta ")
        self.jump.setAccessibleName("Inspecionar operação por número")
        self.jump.setToolTip("Selecione a posição da operação na sequência registrada.")
        self.jump.setKeyboardTracking(False)
        self.jump.valueChanged.connect(lambda value: self.select_operation(value - 1))
        tools.addWidget(self.jump)
        self.chunk = QSpinBox()
        self.chunk.setRange(1, 1)
        self.chunk.setPrefix("Trecho ")
        self.chunk.setAccessibleName("Trecho do circuito")
        self.chunk.setToolTip("Circuitos longos são divididos em trechos de 100 operações para manter a navegação fluida.")
        self.chunk.valueChanged.connect(self._render)
        tools.addWidget(self.chunk)
        fit = GhostButton("Ajustar")
        fit.clicked.connect(lambda: self.canvas.fit_circuit())
        tools.addWidget(fit)
        self.parameters = QCheckBox("Ângulos")
        self.parameters.setChecked(True)
        self.parameters.toggled.connect(self._parameters)
        tools.addWidget(self.parameters)
        self.zoom = QSpinBox()
        self.zoom.setRange(35, 250)
        self.zoom.setValue(100)
        self.zoom.setSuffix("%")
        self.zoom.setPrefix("Zoom ")
        self.zoom.valueChanged.connect(lambda value: self.canvas.set_zoom(value))
        tools.addWidget(self.zoom)
        layout.addWidget(self.controls)
        row = QHBoxLayout()
        self.canvas = CircuitCanvas()
        self.viewer = self.canvas
        row.addWidget(self.canvas, 1)
        self.canvas.operation_selected.connect(self.select_operation)
        self.canvas.zoom_changed.connect(self._sync_zoom)
        panel = QWidget()
        inspector = QVBoxLayout(panel)
        self.details = QLabel("Clique em uma porta para inspecionar.")
        self.details.setTextFormat(Qt.PlainText)
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        inspector.addWidget(self.details)
        self.snapshot_button = PrimaryButton("Ver estado em 3D")
        self.snapshot_button.clicked.connect(self._snapshot)
        inspector.addWidget(self.snapshot_button)
        self.snapshot_button.setVisible(snapshots_action)
        self.snapshot_button.setEnabled(False)
        export = GhostButton("Exportar trecho SVG")
        export.clicked.connect(self._export_svg)
        inspector.addWidget(export)
        self.actions = FlowLayout()
        inspector.addLayout(self.actions)
        note = QLabel(
            "Consulta sem edição. Linhas q são qubits; c guarda os bits de medição. q0 é o bit à direita nas distribuições. Clique nas portas ou use as setas para inspecionar."
        )
        note.setWordWrap(True)
        inspector.addWidget(note)
        inspector.addStretch()
        scroll = QScrollArea()
        self.inspector_scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(215)
        scroll.setMaximumWidth(280)
        row.addWidget(scroll)
        layout.addLayout(row, 1)
        self.range_label = QLabel()
        self.range_label.setWordWrap(True)
        layout.addWidget(self.range_label)
        self.clear()

    def clear(self, message="Selecione uma execução para consultar seu circuito."):
        self.setMinimumHeight(0)
        self.context.setMinimumHeight(0)
        self.range_label.setMinimumHeight(0)
        self.experiment = None
        self.operations = []
        self.selected = -1
        self.snapshots = False
        self.context.setText(message)
        self.context.setToolTip("")
        self.phase_label.setText("Fase global: —")
        self.details.clear()
        self.range_label.clear()
        self.canvas.set_operations([], 1)
        self.controls.hide()
        self.canvas.hide()
        self.inspector_scroll.hide()
        self.snapshot_button.setEnabled(False)

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_fit()

    def hideEvent(self, event):
        self._layout_timer.stop()
        super().hideEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "_layout_timer"):
            self._schedule_fit()

    def _schedule_fit(self):
        if self.isVisible() and not self._layout_timer.isActive():
            self._layout_timer.start()

    def _fit_controls(self):
        if not self.isVisible():
            return
        changed = False
        width = max(1, self.width())
        for label in (self.context, self.range_label):
            required = label.heightForWidth(width)
            if required >= 0 and label.minimumHeight() != required:
                label.setMinimumHeight(required)
                changed = True
        required = self.controls.layout().heightForWidth(max(1, self.controls.width()))
        if self.controls.minimumHeight() != required:
            self.controls.setMinimumHeight(required)
            changed = True
        self.layout().invalidate()
        required = self.layout().minimumSize().height()
        if self.minimumHeight() != required:
            self.setMinimumHeight(required)
            changed = True
        if changed:
            self.updateGeometry()

    def show_experiment(self, experiment, title=None):
        previous = self.selected if self.experiment is not None and self.experiment.id == experiment.id else -1
        self.experiment = experiment
        self.snapshots = bool(experiment.result.states)
        self.selected = -1
        c, r = experiment.config, experiment.result
        inspected = inspect_circuit(experiment)
        self.operations = list(inspected.operations)
        phase = inspected.global_phase
        reconstructed = inspected.reconstructed
        label = "Circuito livre" if c.circuit is not None else c.system.hamiltonian
        self.context.setText(
            f"{title or experiment_title(experiment)} · {label} · {c.system.num_qubits} qubits · {len(self.operations)} portas · profundidade {r.circuit_depth}"
            + (" · reconstruído da configuração com as bibliotecas atuais; não é evidência da decomposição histórica" if reconstructed else " · operações registradas")
        )
        self.context.setToolTip("Identificador técnico: " + experiment.id)
        self.phase_label.setText(f"Fase global: {phase:.6g} rad" if phase is not None else "Fase global: não registrada")
        self.phase_label.setToolTip(
            (repr(phase) + " rad" if phase is not None else "O registro não informa a fase global.")
            + " · uma fase global não altera probabilidades de medição"
        )
        blockers = [QSignalBlocker(self.chunk), QSignalBlocker(self.jump)]
        self.chunk.setRange(
            1, max(1, (len(self.operations) + self.page_size - 1) // self.page_size)
        )
        self.chunk.setValue(1)
        self.jump.setRange(1, max(1, len(self.operations)))
        self.jump.setValue(1)
        del blockers
        self._render()
        self.snapshot_button.setEnabled(False)
        self.details.setText("Clique em uma porta para ver ângulos, qubits e origem.")
        self.controls.show()
        self.canvas.show()
        self.inspector_scroll.show()
        self._schedule_fit()
        if 0 <= previous < len(self.operations):
            self.select_operation(previous)

    def _quantum_circuit(self):
        return execution_circuit(self.experiment.config)

    def _render(self, *_):
        offset = (self.chunk.value() - 1) * self.page_size
        n = self.experiment.config.system.num_qubits if self.experiment else 2
        self.canvas.description = self.phase_label.text() + " · " + self.context.text()
        self.canvas.set_operations(
            self.operations[offset : offset + self.page_size],
            n,
            offset,
            len(self.operations),
        )
        self.range_label.setText(
            f"Portas {offset + 1 if self.operations else 0}–{min(offset + self.page_size, len(self.operations))} de {len(self.operations)} · roda: zoom · arraste o fundo: navegar"
        )
        self.canvas.select_operation(self.selected)
        if self.selected < 0:
            self.canvas.horizontalScrollBar().setValue(0)

    def _parameters(self, checked):
        self.canvas.show_parameters = checked
        self._render()

    def select_operation(self, index):
        if not 0 <= index < len(self.operations):
            return
        self.selected = index
        op = self.operations[index]
        chunk = index // self.page_size + 1
        if self.chunk.value() != chunk:
            self.chunk.setValue(chunk)
        blocker = QSignalBlocker(self.jump)
        self.jump.setValue(index + 1)
        del blocker
        parameters = (
            "\n".join(
                f"{symbol} = {angle_label(value)} rad ({value:.17g})"
                for symbol, value in zip(("θ", "φ", "λ"), op.get("parameters", []))
            )
            or "Sem parâmetros angulares"
        )
        stage = {
            "preparation": "Preparação",
            "evolution": "Evolução",
            "measurement": "Medição",
        }.get(op.get("stage"), "Circuito")
        custom = (
            self.experiment is not None and self.experiment.config.circuit is not None
        )
        if not self.snapshots:
            note = "Esta execução não salvou snapshots. A seleção explica a operação; não calcula nem inventa um estado intermediário."
        elif op["name"] == "measure":
            note = "Snapshot anterior à medição final. O estado condicionado ao resultado da medição não foi salvo."
        elif op.get("stage") == "preparation":
            note = "Snapshot ao fim da preparação completa, antes da evolução por Hamiltoniano. Não foi salvo um estado após cada porta de preparação."
        elif custom:
            note = f"Snapshot após a porta lógica {op.get('logical_gate', op['name']).upper()} deste passo."
        else:
            note = "Snapshot no fim da camada Trotter completa, não após esta porta."
        self.details.setText(
            f"PORTA {index + 1}\n{op['name'].upper()}\n{GATE_HELP.get(op['name'], 'Porta sintetizada do circuito.')}\n\nQubits: {', '.join('q' + str(q) for q in op['qubits'])}\n{parameters}\n\n{stage} · passo {op.get('step', 0)}\n\n{note}"
        )
        self.snapshot_button.setEnabled(self.snapshots)
        self.canvas.select_operation(index)

    def _snapshot(self):
        if self.snapshots and self.selected >= 0:
            self.snapshot_requested.emit(self.operations[self.selected]["step"])

    def _export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar trecho visível", "circuito.svg", "SVG (*.svg)"
        )
        if path:
            try:
                self.canvas.export_svg(path)
            except OSError as exc:
                self.details.setText(str(exc))

    def _sync_zoom(self, value):
        blocker = QSignalBlocker(self.zoom)
        self.zoom.setValue(value)
        del blocker

"""Executed-circuit inspector and an independent Qiskit-backed editor."""

from PySide6.QtCore import Signal, QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QScrollArea,
    QFileDialog,
    QCheckBox,
)
from core.circuits import build_circuit
from core.circuit_document import CircuitDocument, GATE_HELP
from gui.pages.base import PageBase
from gui.widgets.circuit_canvas import CircuitCanvas, angle_label
from gui.widgets.circuit_editor import CircuitEditor
from gui.widgets.button import SecondaryButton, PrimaryButton, GhostButton


class CircuitPage(PageBase):
    snapshot_requested = Signal(int)
    run_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(
            "Circuitos",
            "Explore a execução ou crie um circuito com portas editáveis.",
            parent,
        )
        self.operations = []
        self.snapshots = False
        self.experiment = None
        self.selected = -1
        self.page_size = 100
        self.tabs = QTabWidget()
        self.body().addWidget(self.tabs, 1)
        source = QWidget()
        layout = QVBoxLayout(source)
        self.context = QLabel("Execute um experimento para explorar seu circuito.")
        self.context.setWordWrap(True)
        layout.addWidget(self.context)
        tools = QHBoxLayout()
        self.phase_label = QLabel("Fase global: —")
        tools.addWidget(self.phase_label)
        self.jump = QSpinBox()
        self.jump.setRange(1, 1)
        self.jump.setPrefix("Porta ")
        self.jump.setKeyboardTracking(False)
        self.jump.valueChanged.connect(lambda value: self.select_operation(value - 1))
        tools.addWidget(self.jump)
        self.chunk = QSpinBox()
        self.chunk.setRange(1, 1)
        self.chunk.setPrefix("Trecho ")
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
        tools.addStretch()
        layout.addLayout(tools)
        row = QHBoxLayout()
        self.canvas = CircuitCanvas()
        self.viewer = self.canvas
        row.addWidget(self.canvas, 1)
        self.canvas.operation_selected.connect(self.select_operation)
        self.canvas.zoom_changed.connect(self._sync_zoom)
        panel = QWidget()
        inspector = QVBoxLayout(panel)
        self.details = QLabel("Clique em uma porta para inspecionar.")
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        inspector.addWidget(self.details)
        self.snapshot_button = PrimaryButton("Ver estado em 3D")
        self.snapshot_button.clicked.connect(self._snapshot)
        inspector.addWidget(self.snapshot_button)
        self.copy_button = SecondaryButton("Criar cópia editável")
        self.copy_button.clicked.connect(self._copy_to_editor)
        inspector.addWidget(self.copy_button)
        export = GhostButton("Exportar trecho SVG")
        export.clicked.connect(self._export_svg)
        inspector.addWidget(export)
        note = QLabel(
            "O registro executado é preservado. Para alterar portas e parâmetros, crie uma cópia no editor."
        )
        note.setWordWrap(True)
        inspector.addWidget(note)
        inspector.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(215)
        scroll.setMaximumWidth(280)
        row.addWidget(scroll)
        layout.addLayout(row, 1)
        self.range_label = QLabel()
        layout.addWidget(self.range_label)
        self.tabs.addTab(source, "Circuito da execução")
        self.editor = CircuitEditor()
        self.editor.run_requested.connect(self.run_requested.emit)
        self.tabs.addTab(self.editor, "Editor de circuitos")
        self.snapshot_button.setEnabled(False)
        self.copy_button.setEnabled(False)

    def show_experiment(self, experiment):
        self.experiment = experiment
        self.snapshots = bool(experiment.result.states)
        self.selected = -1
        c, r = experiment.config, experiment.result
        self.operations = list(r.metadata.get("operations") or [])
        phase = r.metadata.get("circuit_global_phase")
        reconstructed = False
        if not self.operations or phase is None:
            circuit = self._quantum_circuit()
            phase = float(circuit.global_phase)
            if not self.operations:
                self.operations = [
                    dict(
                        name=i.operation.name,
                        qubits=[circuit.find_bit(q).index for q in i.qubits],
                        parameters=[float(v) for v in i.operation.params],
                        stage="measurement"
                        if i.operation.name == "measure"
                        else "evolution",
                        step=c.protocol.trotter_steps,
                    )
                    for i in circuit.data
                ]
                reconstructed = True
        label = "Circuito livre" if c.circuit is not None else c.system.hamiltonian
        self.context.setText(
            f"{experiment.id} · {label} · {c.system.num_qubits} qubits · {len(self.operations)} portas · profundidade {r.circuit_depth}"
            + (" · reconstruído da configuração" if reconstructed else "")
        )
        self.phase_label.setText(f"Fase global: {float(phase):.6g} rad")
        self.phase_label.setToolTip(
            repr(float(phase))
            + " rad · uma fase global não altera probabilidades de medição"
        )
        blockers = [QSignalBlocker(self.chunk), QSignalBlocker(self.jump)]
        self.chunk.setRange(
            1, max(1, (len(self.operations) + self.page_size - 1) // self.page_size)
        )
        self.chunk.setValue(1)
        self.jump.setRange(1, max(1, len(self.operations)))
        self.jump.setValue(1)
        del blockers
        self.copy_button.setEnabled(not bool(r.error))
        self._render()
        self.snapshot_button.setEnabled(False)
        self.details.setText("Clique em uma porta para ver ângulos, qubits e origem.")

    def _quantum_circuit(self):
        c = self.experiment.config
        if c.circuit is not None:
            return c.circuit.to_quantum_circuit(measure=True)
        s, p = c.system, c.protocol
        return build_circuit(
            s.num_qubits,
            s.hamiltonian,
            s.J,
            s.h,
            s.periodic,
            p.total_time,
            p.trotter_steps,
            False,
            initial_state=s.initial_state,
            trotter_order=p.trotter_order,
        )[0]

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
                f"{symbol} = {angle_label(value)} rad ({value:.12g})"
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
        if op["name"] == "measure":
            note = "Snapshot anterior à medição final. O estado condicionado ao resultado da medição não foi salvo."
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

    def _copy_to_editor(self):
        if self.experiment is None:
            return
        try:
            doc = (
                self.experiment.config.circuit
                or CircuitDocument.from_quantum_circuit(self._quantum_circuit())
            )
            self.editor.replace_document(doc, "Copiar execução")
            config = self.experiment.config
            noise = config.noise
            self.editor.shots.setValue(config.shots)
            seed = self.experiment.result.metadata.get("effective_seed", config.seed)
            self.editor.seed.setText("" if seed is None else str(seed))
            self.editor.noise.setChecked(noise.enabled)
            self.editor.noise_kind.setCurrentIndex(
                self.editor.noise_kind.findData(noise.kind)
            )
            for widget, value in (
                (self.editor.p1, noise.p1),
                (self.editor.p2, noise.p2),
                (self.editor.t1, noise.t1_us),
                (self.editor.t2, noise.t2_us),
            ):
                widget.setValue(value)
            self.tabs.setCurrentWidget(self.editor)
        except ValueError as exc:
            self.details.setText(
                str(exc) + "\nO circuito executado continua disponível para inspeção."
            )

    def _export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar trecho visível", "circuito.svg", "SVG (*.svg)"
        )
        if path:
            try:
                self.canvas.export_svg(path)
            except OSError as exc:
                self.details.setText(str(exc))

    def set_running(self, running):
        self.editor.set_running(running)

    def _sync_zoom(self, value):
        blocker = QSignalBlocker(self.zoom)
        self.zoom.setValue(value)
        del blocker

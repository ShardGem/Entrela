"""Executed-circuit inspection and an independent editor of working copies."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget
from core.circuit_document import CircuitDocument
from gui.pages.base import PageBase
from gui.widgets.circuit_inspector import CircuitInspector
from gui.widgets.circuit_editor import CircuitEditor
from gui.widgets.button import SecondaryButton


class CircuitPage(PageBase):
    snapshot_requested = Signal(int)
    run_requested = Signal(object)
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Circuitos", "Explore a execução ou crie um circuito com portas editáveis.", parent)
        self.tabs = QTabWidget()
        self.body().addWidget(self.tabs, 1)
        self.inspector = CircuitInspector(snapshots_action=True)
        self.inspector.snapshot_requested.connect(self.snapshot_requested.emit)
        self.tabs.addTab(self.inspector, "Circuito da execução")
        for name in ("context", "phase_label", "jump", "chunk", "canvas", "viewer", "parameters",
                     "zoom", "details", "snapshot_button", "range_label"):
            setattr(self, name, getattr(self.inspector, name))
        self.copy_button = SecondaryButton("Criar cópia editável")
        self.copy_button.setToolTip("Abre uma cópia no editor; o circuito da execução permanece preservado.")
        self.copy_button.clicked.connect(self._copy_to_editor)
        self.inspector.actions.addWidget(self.copy_button)
        self.copy_button.setEnabled(False)
        self.editor = CircuitEditor()
        self.editor.run_requested.connect(self.run_requested.emit)
        self.editor.cancel_requested.connect(self.cancel_requested.emit)
        self.tabs.addTab(self.editor, "Editor de circuitos")
        self.editor.layout().removeWidget(self.editor.execution_bar)
        self._root.addWidget(self.editor.execution_bar)
        self.tabs.currentChanged.connect(self._sync_execution_bar)
        self._sync_execution_bar()

    @property
    def operations(self):
        return self.inspector.operations

    @property
    def experiment(self):
        return self.inspector.experiment

    @property
    def selected(self):
        return self.inspector.selected

    @property
    def snapshots(self):
        return self.inspector.snapshots

    @property
    def page_size(self):
        return self.inspector.page_size

    def _sync_execution_bar(self, *_):
        self.editor.execution_bar.setVisible(self.tabs.currentWidget() is self.editor)

    def show_experiment(self, experiment, title=None):
        self.inspector.show_experiment(experiment, title)
        self.copy_button.setEnabled(not bool(experiment.result.error))

    def _quantum_circuit(self):
        return self.inspector._quantum_circuit()

    def select_operation(self, index):
        self.inspector.select_operation(index)

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
                (self.editor.gate1, noise.gate_time_1q_ns),
                (self.editor.gate2, noise.gate_time_2q_ns),
            ):
                widget.setValue(value)
            self.tabs.setCurrentWidget(self.editor)
        except ValueError as exc:
            self.details.setText(
                str(exc) + "\nO circuito executado continua disponível para inspeção."
            )

    def set_running(self, running):
        self.editor.set_running(running)

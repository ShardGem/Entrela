"""One view of the active worker, available without leaving the current page."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar
from gui.widgets.button import SecondaryButton


class JobMonitor(QFrame):
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExecutionBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAccessibleName("Tarefa em andamento")
        layout.addWidget(self.label, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setMaximumWidth(130)
        self.progress.setAccessibleName("Progresso da tarefa atual")
        layout.addWidget(self.progress)
        self.cancel = SecondaryButton("Cancelar", icon="close")
        self.cancel.setAccessibleName("Cancelar tarefa atual")
        self.cancel.setToolTip("Solicita o cancelamento e aguarda a etapa atual terminar.")
        self.cancel.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self.cancel)
        self._task = ""
        self.hide()

    def start(self, task, context=""):
        self._task = task
        self._context = context
        self.label.setText(task + (" · " + context if context else ""))
        self.progress.setValue(0)
        self.cancel.setEnabled(True)
        self.show()

    def set_phase(self, phase, *, cancellable=True):
        self.label.setText(phase + (" · " + self._context if self._context else ""))
        self.cancel.setEnabled(cancellable)

    def set_progress(self, value):
        self.progress.setValue(max(0, min(100, int(value))))

    def cancelling(self):
        self.label.setText("Cancelando: aguardando a etapa atual terminar…")
        self.cancel.setEnabled(False)

    def finish(self):
        self._task = ""
        self.hide()

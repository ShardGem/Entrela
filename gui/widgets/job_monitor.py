"""One view of the active worker, available without leaving the current page."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar
from gui.widgets.button import SecondaryButton


class JobMonitor(QFrame):
    cancel_requested = Signal()
    open_requested = Signal(str)

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
        self.open_result = SecondaryButton('Abrir resultados', icon='results')
        self.open_result.clicked.connect(lambda: self.open_requested.emit(self._completed_id) if self._completed_id else None)
        layout.addWidget(self.open_result)
        self.dismiss = SecondaryButton('Fechar aviso')
        self.dismiss.clicked.connect(self._dismiss)
        layout.addWidget(self.dismiss)
        self._completed_id = None
        self.open_result.hide(); self.dismiss.hide()
        self._task = ""
        self.hide()

    def start(self, task, context=""):
        self._completed_id = None
        self.open_result.hide(); self.dismiss.hide()
        self.progress.show(); self.cancel.show()
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

    def completed_result(self, identifier, title):
        self._completed_id = identifier
        self.label.setText('Execução concluída · ' + title)
        self.progress.hide(); self.cancel.hide()
        self.open_result.show(); self.dismiss.show()
        self.show()

    def _dismiss(self):
        self._completed_id = None
        self.hide()

    def finish(self):
        self._task = ""
        if self._completed_id:
            self.progress.hide(); self.cancel.hide()
            self.open_result.show(); self.dismiss.show()
            self.show()
        else:
            self.hide()

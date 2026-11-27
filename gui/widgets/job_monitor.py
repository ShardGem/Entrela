"""One view of the active worker, available without leaving the current page."""
from PySide6.QtCore import Signal, QEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QBoxLayout, QLabel, QProgressBar, QWidget
from gui.widgets.button import SecondaryButton


class JobMonitor(QFrame):
    cancel_requested = Signal()
    open_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExecutionBar")
        layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self._layout = layout
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAccessibleName("Tarefa em andamento")
        self.label.setMinimumWidth(0)
        layout.addWidget(self.label, 1)
        self._controls = QWidget()
        controls = QHBoxLayout(self._controls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(12)
        layout.addWidget(self._controls)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setMaximumWidth(130)
        self.progress.setAccessibleName("Progresso da tarefa atual")
        controls.addWidget(self.progress)
        self.cancel = SecondaryButton("Cancelar", icon="close")
        self.cancel.setAccessibleName("Cancelar tarefa atual")
        self.cancel.setToolTip("Solicita o cancelamento e aguarda a etapa atual terminar.")
        self.cancel.clicked.connect(self.cancel_requested.emit)
        controls.addWidget(self.cancel)
        self.open_result = SecondaryButton('Abrir resultados', icon='results')
        self.open_result.clicked.connect(lambda: self.open_requested.emit(self._completed_id) if self._completed_id else None)
        controls.addWidget(self.open_result)
        self.dismiss = SecondaryButton('Fechar aviso')
        self.dismiss.clicked.connect(self._dismiss)
        controls.addWidget(self.dismiss)
        self._completed_id = None
        self.open_result.hide(); self.dismiss.hide()
        self._task = ""
        self.hide()

    def _arrange(self):
        if not hasattr(self, '_controls'):
            return
        margins = self._layout.contentsMargins()
        available = self.width() - margins.left() - margins.right()
        label_width = self.fontMetrics().horizontalAdvance('Simulação em andamento')
        required = self._controls.sizeHint().width() + label_width + self._layout.spacing()
        self._layout.setDirection(QBoxLayout.TopToBottom if available < required else QBoxLayout.LeftToRight)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._arrange()

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
        self._arrange()

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
        self._arrange()

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

"""Consulta dos resultados gravados de um circuito, separada do rascunho."""
from PySide6.QtCore import Signal, QSize
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from gui.widgets.button import GhostButton
from gui.widgets.plot_canvas import MplCanvas, style_figure
from gui.formatting import quantity
from core.figures import draw_histograms


class CircuitEvidence(QFrame):
    results_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('EvidencePanel')
        self.experiment = None
        self.document = None
        self.plot = None
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel('Resultado da execução')
        title.setObjectName('PanelTitle')
        header.addWidget(title, 1)
        self.open_results = GhostButton('Abrir resultados', icon='results')
        self.open_results.clicked.connect(self.results_requested.emit)
        self.open_results.hide()
        header.addWidget(self.open_results)
        root.addLayout(header)
        self.context = QLabel('Execute o circuito para consultar contagens e métricas neste painel.')
        self.context.setWordWrap(True)
        self.context.setObjectName('FieldHint')
        root.addWidget(self.context)
        self.views = QWidget()
        views_layout = QVBoxLayout(self.views)
        views_layout.setContentsMargins(0, 0, 0, 0)
        self.empty = QLabel('Adicione portas pela biblioteca ou carregue um modelo.\nExecutar circuito calcula uma nova simulação com os parâmetros do inspetor.')
        self.empty.setWordWrap(True)
        self.empty.setObjectName('FieldHint')
        views_layout.addWidget(self.empty)
        self.data_view = QWidget()
        self.data_layout = QHBoxLayout(self.data_view)
        self.data_layout.setContentsMargins(0, 0, 0, 0)
        metrics = QVBoxLayout()
        self.values = []
        for text in ('Fidelidade ao circuito ideal', 'Pureza global', 'Shots registrados'):
            label = QLabel(text)
            label.setWordWrap(True)
            label.setObjectName('FieldHint')
            value = QLabel('—')
            value.setObjectName('MetricCompact')
            metrics.addWidget(label)
            metrics.addWidget(value)
            self.values.append(value)
        metrics.addStretch()
        self.data_layout.addLayout(metrics, 1)
        views_layout.addWidget(self.data_view)
        self.data_view.hide()
        root.addWidget(self.views, 1)
        self.change_notice = QLabel()
        self.change_notice.setWordWrap(True)
        self.change_notice.setObjectName('FieldHint')
        root.addWidget(self.change_notice)

    def set_document(self, document):
        self.document = document
        self._describe_source()

    def set_experiment(self, experiment, title=''):
        valid = experiment is not None and experiment.config.circuit is not None and not experiment.result.error
        self.experiment = experiment if valid else None
        self.data_view.setVisible(valid)
        self.empty.setVisible(not valid)
        self.open_results.setVisible(valid)
        if not valid:
            self.context.setText('Nenhuma execução de circuito selecionada. Execute o desenho para gerar resultados.')
            self._describe_source()
            return
        self.context.setText('Execução selecionada · ' + (title or 'Circuito sem nome'))
        self.context.setToolTip(self.context.text())
        if self.plot is None:
            self.plot = MplCanvas()
            self.plot._layout_minimum = QSize(200, 110)
            self.plot.setMinimumSize(200, 110)
            self.data_layout.insertWidget(0, self.plot, 3)
        draw_histograms(self.plot.fig, [experiment.result.counts], frequency=True)
        ax = self.plot.fig.axes[0]
        ax.set_title('Frequências de medição registradas')
        if ax.get_legend() is not None:
            ax.get_legend().remove()
        style_figure(self.plot.fig)
        self.plot.draw_idle()
        for field, raw in zip(self.values, (experiment.result.fidelity, experiment.result.purity, experiment.config.shots)):
            field.setText(quantity(raw))
            field.setToolTip(str(raw))
        self._describe_source()

    def _describe_source(self):
        if self.experiment is None:
            self.change_notice.clear()
        elif self.document != self.experiment.config.circuit:
            self.change_notice.setText('O desenho foi alterado ou pertence a outro circuito. Estes resultados continuam sendo os da execução selecionada.')
        else:
            self.change_notice.setText('Dados gravados. Alterar portas, shots ou ruído exige uma nova execução; este painel não recalcula resultados.')

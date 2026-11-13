"""Observed distributions and snapshot probabilities, with explicit selection."""

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QFrame, QTabBar, QHBoxLayout, QVBoxLayout, QComboBox, QToolButton, QMenu,
)
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE
from PySide6.QtCore import QEvent, QTimer


class ResultsTab(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._counts = {}
        self._hist_title = "Distribuição observada"
        self._probabilities = None
        self._times = None
        self._time_unit = "Tempo (adimensional, ℏ=1)"
        self._manual_states = set()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        self.setWidget(host)
        outer = QVBoxLayout(host)
        outer.setContentsMargins(0, 0, 0, 0)
        self.chart_views = QTabBar()
        self.chart_views.setObjectName("ViewTabs")
        self.chart_views.setAccessibleName("Gráfico dos resultados")
        for title in ("Distribuição", "Evolução", "Lado a lado"):
            self.chart_views.addTab(title)
        outer.addWidget(self.chart_views)
        layout = QHBoxLayout()
        outer.addLayout(layout, 1)
        self._panes = layout
        self._figure_panes = []
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(0)
        self._layout_timer.timeout.connect(self._arrange_panes)
        self.canvas_hist = MplCanvas(self)
        self.canvas_evol = MplCanvas(self)
        self.hist_measure = QComboBox()
        self.hist_measure.addItems(["Contagens", "Frequência observada"])
        self.hist_measure.setAccessibleName("Unidade da distribuição observada")
        self.hist_measure.setToolTip("Contagens são medições observadas. Frequência divide cada contagem pelo total observado; não é uma probabilidade exata do estado.")
        self.hist_measure.currentIndexChanged.connect(self._render_histogram)
        self.state_criterion = QComboBox()
        self.state_criterion.addItems(["Picos na trajetória", "Probabilidade final", "Seleção manual"])
        self.state_criterion.setAccessibleName("Critério de seleção dos estados na evolução")
        self.state_criterion.setToolTip("Exibe até quatro estados com maior probabilidade em algum snapshot (picos), os quatro maiores no final, ou os estados escolhidos. Outros soma todos os estados omitidos.")
        self.state_criterion.currentIndexChanged.connect(self._render_evolution)
        self.state_picker = QToolButton()
        self.state_picker.setText("Estados…")
        self.state_picker.setAccessibleName("Selecionar estados da evolução")
        self.state_picker.setPopupMode(QToolButton.InstantPopup)
        self.state_menu = QMenu(self.state_picker)
        self.state_picker.setMenu(self.state_menu)
        self.state_picker.hide()
        for canvas, control, extra in (
            (self.canvas_hist, self.hist_measure, None),
            (self.canvas_evol, self.state_criterion, self.state_picker),
        ):
            pane = QWidget(self)
            column = QVBoxLayout(pane)
            column.setContentsMargins(0, 0, 0, 0)
            tools = QHBoxLayout()
            tools.addWidget(control, 1)
            if extra is not None:
                tools.addWidget(extra)
            tools.addWidget(canvas.exploration_button(pane))
            column.addLayout(tools)
            column.addWidget(canvas, 1)
            layout.addWidget(pane, 1)
            self._figure_panes.append(pane)
        self.chart_views.currentChanged.connect(self._show_plot)
        self._show_plot(0)
        self.canvas_hist.set_value_lookup(self._histogram_value)
        self.canvas_evol.set_value_lookup(self._evolution_value)

    def _show_plot(self, index):
        for i, pane in enumerate(self._figure_panes):
            pane.setVisible(index == 2 or i == index)
        self._layout_timer.start()

    def _arrange_panes(self):
        # Uma coluna preserva a leitura dos eixos quando o texto é ampliado.
        wide = self.width() >= 860 * max(1, self.font().pixelSize() / 15)
        direction = QHBoxLayout.LeftToRight if wide else QHBoxLayout.TopToBottom
        if self._panes.direction() != direction:
            self._panes.setDirection(direction)
            self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_timer.start()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, '_layout_timer'):
            self._layout_timer.start()

    def exibir_histograma(self, counts, titulo="Distribuição observada"):
        self._counts = dict(counts or {})
        self._hist_title = titulo
        self._render_histogram()

    def _render_histogram(self, *_):
        from core.figures import draw_histograms
        from gui.widgets.plot_canvas import style_figure
        draw_histograms(self.canvas_hist.fig, [self._counts],
                        frequency=self.hist_measure.currentIndex() == 1,
                        colors=(PALETTE.primary,), label_size=10, title=self._hist_title)
        style_figure(self.canvas_hist.fig)
        self.canvas_hist.draw()

    def exibir_evolucao_temporal(self, states, times=None, time_unit="Tempo (adimensional, ℏ=1)"):
        previous_dim = None if self._probabilities is None else self._probabilities.shape[1]
        self._probabilities = np.asarray([s.probabilities() for s in states]) if states else None
        self._times = np.asarray(times) if times is not None and len(times) == len(states) else np.arange(len(states))
        self._time_unit = time_unit
        if self._probabilities is not None and previous_dim != self._probabilities.shape[1]:
            self._manual_states = set(self._rank_states("peak"))
        self._rebuild_state_menu()
        self._render_evolution()

    def _rank_states(self, criterion):
        from core.figures import probability_indices
        return probability_indices(self._probabilities, criterion)

    def _rebuild_state_menu(self):
        self.state_menu.clear()
        if self._probabilities is None:
            return
        dim = self._probabilities.shape[1]
        self._manual_states.intersection_update(range(dim))
        width = int(np.log2(dim))
        for index in range(dim):
            action = self.state_menu.addAction(f"|{index:0{width}b}⟩")
            action.setCheckable(True)
            action.setChecked(index in self._manual_states)
            action.toggled.connect(lambda checked, index=index: self._select_state(index, checked))

    def _select_state(self, index, checked):
        if checked:
            self._manual_states.add(index)
        else:
            self._manual_states.discard(index)
        self._render_evolution()

    def _render_evolution(self, *_):
        from core.figures import draw_probabilities
        from gui.widgets.plot_canvas import style_figure
        criterion = self.state_criterion.currentIndex()
        self.state_picker.setVisible(criterion == 2)
        self.state_picker.setEnabled(self._probabilities is not None)
        draw_probabilities(self.canvas_evol.fig, self._probabilities, self._times,
                           indices=self._manual_states if criterion == 2 else None,
                           criterion=("peak", "final", "manual")[criterion], time_unit=self._time_unit,
                           colors=(PALETTE.q1, PALETTE.q2, PALETTE.q3, PALETTE.q4, PALETTE.text_muted))
        style_figure(self.canvas_evol.fig)
        self.canvas_evol.draw()

    def _histogram_value(self, event):
        total = sum(self._counts.values())
        for state, bar in zip(sorted(self._counts), self.canvas_hist.fig.axes[0].patches):
            if bar.contains(event)[0]:
                frequency = self._counts[state] / total if total else 0
                return f"Estado |{state}⟩\nContagens: {self._counts[state]} de {total}\nFrequência observada: {frequency:.16g} ({frequency * 100:.12g}%)"
        return None

    def _evolution_value(self, event):
        for line in self.canvas_evol.fig.axes[0].lines:
            hit, info = line.contains(event)
            if hit and len(info.get("ind", [])):
                index = info["ind"][0]
                probability = line.get_ydata()[index]
                return f"{line.get_label()}\n{self._time_unit}: {line.get_xdata()[index]:.16g}\nProbabilidade: {probability:.16g} ({probability * 100:.12g}%)"
        return None

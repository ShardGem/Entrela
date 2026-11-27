"""Comparações visuais preservam escalas, massa e significado dos dados."""
from dataclasses import replace

import numpy as np
import pytest
from matplotlib import rcParams
from matplotlib.backend_bases import MouseEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qiskit.quantum_info import Statevector

from core.examples import create_example_config
from core.figures import histogram_figure
from core.types import Experiment, ExperimentResult
from gui.controllers.appearance import apply_appearance
from gui.pages.comparison import ComparisonPage
from gui.tabs.results_tab import ResultsTab
from gui.widgets.plot_canvas import MplCanvas


def distributions():
    config = create_example_config("first-qubit")
    first = Experiment(replace(config, shots=100), ExperimentResult(counts={"0": 100}))
    second = Experiment(replace(config, shots=200), ExperimentResult(counts={"0": 100, "1": 100}))
    return first, second


@pytest.mark.parametrize("side_by_side", [False, True])
def test_portable_comparison_shares_frequency_scale(side_by_side):
    figure = histogram_figure(distributions(), side_by_side=side_by_side)
    try:
        assert len(figure.axes) == (2 if side_by_side else 1)
        for axes in figure.axes:
            assert axes.get_ylim()[0] == 0
            assert axes.get_ylim()[1] >= 1
            assert "Frequência" in axes.get_ylabel()
        heights = [bar.get_height() for axes in figure.axes for bar in axes.patches]
        assert heights == [1, 0, .5, .5]
        if side_by_side:
            assert figure.axes[0].get_ylim() == figure.axes[1].get_ylim()
        assert "total observado" in figure._suptitle.get_text()
    finally:
        figure.clear()


def test_screen_comparison_does_not_equalize_unequal_frequencies(qt_app):
    page = ComparisonPage()
    try:
        page.load(distributions())
        page.hist_layout.setCurrentIndex(1)
        axes = page.canvas.fig.axes
        assert len(axes) == 2
        assert axes[0].get_ylim() == axes[1].get_ylim()
        assert axes[0].get_ylim()[0] == 0
        assert axes[0].get_ylim()[1] >= 1
        assert axes[0].patches[0].get_height() == 1
        assert axes[1].patches[0].get_height() == .5
        assert "escala comum" in page.message.text()
        page.canvas.draw()
        x, y = axes[1].transData.transform((0, .25))
        event = MouseEvent("motion_notify_event", page.canvas, x, y)
        value = page._histogram_value(event)
        assert "Execução B" in value
        assert "100 de 200" in value
        assert "50%" in value
    finally:
        page.timer.stop()
        page._load_timer.stop()
        page.close()
        page.deleteLater()


def test_evolution_keeps_early_peak_and_accounts_for_omitted_probability(qt_app):
    tab = ResultsTab()
    states = [Statevector.from_label("000"), Statevector.from_label("100"), Statevector(np.ones(8) / np.sqrt(8))]
    try:
        tab.exibir_evolucao_temporal(states, times=[0, .5, 1])
        axes = tab.canvas_evol.fig.axes[0]
        lines = {line.get_label(): line for line in axes.lines}
        assert "|000⟩" in lines
        assert "|100⟩" in lines
        np.testing.assert_allclose(lines["|000⟩"].get_ydata(), [1, 0, .125])
        np.testing.assert_allclose(lines["|100⟩"].get_ydata(), [0, 1, .125])
        others = next(line for name, line in lines.items() if name.startswith("Outros"))
        assert others.get_ydata()[-1] == pytest.approx(.5)
        np.testing.assert_allclose(sum(np.asarray(line.get_ydata()) for line in axes.lines), np.ones(3))
        assert "picos" in axes.get_title()
        assert tab.state_criterion.currentIndex() == 0
    finally:
        tab.close()
        tab.deleteLater()


def test_manual_state_selection_keeps_total_mass_and_source_unchanged(qt_app):
    tab = ResultsTab()
    states = [Statevector.from_label("000"), Statevector(np.ones(8) / np.sqrt(8))]
    originals = [state.data.copy() for state in states]
    try:
        tab.exibir_evolucao_temporal(states)
        tab.state_criterion.setCurrentIndex(2)
        for action in tab.state_menu.actions():
            action.setChecked(action.text() == "|111⟩")
        axes = tab.canvas_evol.fig.axes[0]
        assert [line.get_label() for line in axes.lines] == ["|111⟩", "Outros (7 estados)"]
        np.testing.assert_allclose(axes.lines[0].get_ydata(), [0, .125])
        np.testing.assert_allclose(axes.lines[1].get_ydata(), [1, .875])
        for action in tab.state_menu.actions():
            action.setChecked(False)
        axes = tab.canvas_evol.fig.axes[0]
        assert len(axes.lines) == 1
        assert axes.lines[0].get_label() == "Outros (8 estados)"
        np.testing.assert_allclose(axes.lines[0].get_ydata(), [1, 1])
        for state, original in zip(states, originals):
            np.testing.assert_array_equal(state.data, original)
    finally:
        tab.close()
        tab.deleteLater()


def test_histogram_distinguishes_counts_from_observed_frequency(qt_app):
    tab = ResultsTab()
    try:
        tab.exibir_histograma({"0": 1, "1": 3})
        axes = tab.canvas_hist.fig.axes[0]
        assert axes.get_ylabel() == "Contagens"
        assert [bar.get_height() for bar in axes.patches] == [1, 3]
        tab.hist_measure.setCurrentIndex(1)
        axes = tab.canvas_hist.fig.axes[0]
        assert "Frequência observada" in axes.get_ylabel()
        assert [bar.get_height() for bar in axes.patches] == [.25, .75]
        assert axes.get_ylim()[0] == 0
        assert axes.get_ylim()[1] >= 1
        tab.exibir_histograma({})
        assert not tab.canvas_hist.fig.axes[0].patches
        assert any(text.get_text() == "Sem contagens" for text in tab.canvas_hist.fig.axes[0].texts)
    finally:
        tab.close()
        tab.deleteLater()


def test_chart_fonts_follow_ui_without_accumulating_or_changing_exports(qt_app):
    window = QWidget()
    layout = QVBoxLayout(window)
    canvas = MplCanvas(window)
    layout.addWidget(canvas)
    portable = histogram_figure(distributions(), side_by_side=True)
    portable_title_size = portable._suptitle.get_fontsize()
    portable_tick_size = portable.axes[0].get_xticklabels()[0].get_fontsize()
    default_font = rcParams["font.size"]
    try:
        apply_appearance(window, "dark", 15)
        axes = canvas.reset_axes()
        axes.plot([0, 1], [0, 1])
        axes.set_title("Evolução")
        canvas.draw()
        original_title_size = axes.title.get_fontsize()
        original_tick_size = axes.get_xticklabels()[0].get_fontsize()
        apply_appearance(window, "dark", 24)
        for _ in range(4):
            canvas.draw()
        assert axes.title.get_fontsize() == pytest.approx(original_title_size * 24 / 15)
        assert axes.get_xticklabels()[0].get_fontsize() == pytest.approx(original_tick_size * 24 / 15)
        axes.set_xlim(0, .17)
        canvas.draw()
        assert all(label.get_fontsize() == pytest.approx(original_tick_size * 24 / 15) for label in axes.get_xticklabels())
        apply_appearance(window, "light", 15)
        canvas.draw()
        assert axes.title.get_fontsize() == pytest.approx(original_title_size)
        assert axes.get_xticklabels()[0].get_fontsize() == pytest.approx(original_tick_size)
        assert portable._suptitle.get_fontsize() == portable_title_size
        assert portable.axes[0].get_xticklabels()[0].get_fontsize() == portable_tick_size
        assert rcParams["font.size"] == default_font
    finally:
        apply_appearance(window)
        portable.clear()
        window.close()
        window.deleteLater()

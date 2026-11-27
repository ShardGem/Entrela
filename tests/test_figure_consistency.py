"""Scientific evidence retains its values, units and references across views."""
from dataclasses import replace
import numpy as np
import pytest
from core.examples import create_example_config
from core.simulation import run_experiment
from core.analysis import parameter_sweep, temporal_analysis
from core.benchmark import mitigation_benchmark
from core.research import heatmap_study
from core.comparison import prepare_comparison
from core.figures import histogram_figure, temporal_figure, analysis_figure
from gui.pages.comparison import ComparisonPage
from gui.pages.analysis import AnalysisPage
from gui.pages.history import HistoryPage
from gui.tabs.results_tab import ResultsTab


def signature(fig):
    return [(axes.get_xlabel(), axes.get_ylabel(),
             [(line.get_label(), np.asarray(line.get_xdata(), dtype=float).tolist(), np.asarray(line.get_ydata(), dtype=float).tolist()) for line in axes.lines],
             [float(bar.get_height()) for bar in axes.patches],
             [np.asarray(image.get_array()).tolist() for image in axes.images]) for axes in fig.axes]


@pytest.fixture(scope='module')
def source():
    return run_experiment(replace(create_example_config('depolarizing-bell'), shots=32, seed=42))


def test_history_results_and_portable_histogram_keep_identical_frequencies(qt_app, source):
    history, results = HistoryPage(), ResultsTab()
    portable = histogram_figure([source])
    try:
        history.load([source])
        history.set_detail(source)
        results.exibir_histograma(source.result.counts)
        results.hist_measure.setCurrentIndex(1)
        expected = [source.result.counts[key] / sum(source.result.counts.values()) for key in sorted(source.result.counts)]
        for fig in (portable, history.chart.fig, results.canvas_hist.fig):
            ax = fig.axes[0]
            assert ax.get_ylim() == (0, 1.05)
            assert ax.get_xlabel() == 'Estado (q0 à direita)'
            assert ax.get_ylabel() == 'Frequência observada (0–1)'
            np.testing.assert_allclose([bar.get_height() for bar in ax.patches], expected)
    finally:
        portable.clear()
        history.close()
        results.close()


@pytest.mark.parametrize('kind,key', [('sweep','fidelity'), ('mitigation_benchmark','estimate'), ('heatmap','fidelity_exact'), ('temporal','purity')])
def test_study_values_and_axis_units_match_portable_figure(qt_app, source, kind, key):
    if kind == 'sweep':
        data = parameter_sweep(source.config, 'p2', [0, .1], seeds=[3, 7])
    elif kind == 'mitigation_benchmark':
        data = mitigation_benchmark(source, shots=8)
    elif kind == 'heatmap':
        data = heatmap_study(source, x_values=[1, 2], y_values=[0, .1])
    else:
        data = temporal_analysis(source)
    data.setdefault('source_id', source.id)
    portable = analysis_figure(data, key)
    page = AnalysisPage()
    try:
        page.load_experiment(source)
        page.show_analysis(data)
        page.series_combo.setCurrentIndex(page.series_combo.findData(key))
        assert signature(page.canvas.fig) == signature(portable)
        if kind == 'sweep':
            assert len(portable.axes[0].lines) == 2
            assert 'Probabilidade de erro' in portable.axes[0].get_xlabel()
            for line in portable.axes[0].lines:
                np.testing.assert_array_equal(line.get_xdata(), [0, .1])
        if kind == 'mitigation_benchmark':
            assert any(line.get_label() == 'Referência ideal' for line in portable.axes[0].lines)
    finally:
        portable.clear()
        page.close()


def test_html_study_does_not_join_different_seeds_into_a_single_curve(monkeypatch, source):
    from core import report
    data = parameter_sweep(source.config, 'p2', [0, .1], seeds=[3, 7])
    figures = []
    monkeypatch.setattr(report, '_image', lambda fig, description: figures.append(fig) or '<img>')
    report._analysis_section(data)
    try:
        assert len(figures) == 1
        assert len(figures[0].axes[0].lines) == 4  # fidelity and purity, independently for each seed.
        assert all(list(line.get_xdata()) == [0, .1] for line in figures[0].axes[0].lines)
    finally:
        for fig in figures:
            fig.clear()


def test_trotter_curves_keep_independent_grids_and_exact_reference(qt_app):
    config = create_example_config('ising')
    a = run_experiment(replace(config, protocol=replace(config.protocol, trotter_steps=2), shots=8))
    b = run_experiment(replace(config, protocol=replace(config.protocol, trotter_steps=4), shots=8))
    data = prepare_comparison([a, b], mode='trotter')
    page = ComparisonPage()
    portable = temporal_figure([a, b], reference='exact')
    try:
        page.load([a, b])
        page.comparison_mode.setCurrentIndex(page.comparison_mode.findData('trotter'))
        page.set_runs(a.id, b.id)
        page.set_full_data(data)
        for ui_axes, report_axes in zip(page.curve_canvas.fig.axes, portable.axes):
            assert ui_axes.get_ylabel() == report_axes.get_ylabel()
            for ui_line, report_line in zip(ui_axes.lines, report_axes.lines):
                np.testing.assert_array_equal(ui_line.get_xdata(), report_line.get_xdata())
                np.testing.assert_allclose(ui_line.get_ydata(), report_line.get_ydata(), atol=1e-12)
        assert len(page.curve_canvas.fig.axes[0].lines[0].get_xdata()) == 3
        assert len(page.curve_canvas.fig.axes[0].lines[1].get_xdata()) == 5
        assert page.curve_canvas.fig.axes[0].get_ylabel() == 'Fidelidade à evolução exata'
    finally:
        page.timer.stop()
        page._load_timer.stop()
        portable.clear()
        page.close()


def test_missing_time_metadata_is_not_labeled_as_physical_time():
    data = dict(kind='temporal', rows=[dict(time=0, purity=1)], note='Legacy artifact')
    fig = analysis_figure(data, 'purity')
    try:
        assert 'unidade não informada' in fig.axes[0].get_xlabel()
    finally:
        fig.clear()


def test_missing_metric_leaves_a_gap_instead_of_connecting_unsupported_points():
    data = dict(kind='temporal', rows=[dict(time=0, purity=1), dict(time=1, purity=None), dict(time=2, purity=.7)], note='Incomplete legacy data')
    fig = analysis_figure(data, 'purity')
    try:
        line = fig.axes[0].lines[0]
        assert list(line.get_xdata()) == [0, 1, 2]
        assert np.isnan(line.get_ydata()[1])
    finally:
        fig.clear()


def test_exploration_history_is_reset_when_a_different_distribution_is_drawn(qt_app):
    results = ResultsTab()
    try:
        results.exibir_histograma({'0': 1, '1': 2})
        canvas = results.canvas_hist
        old_axes = canvas.fig.axes[0]
        canvas._navigation.push_current()
        old_axes.set_xlim(.2, .4)
        canvas._navigation.push_current()
        results.exibir_histograma({'000': 1, '010': 2, '111': 1})
        new_axes = canvas.fig.axes[0]
        assert new_axes is not old_axes
        limits = new_axes.get_xlim()
        canvas._navigation.home()
        np.testing.assert_allclose(new_axes.get_xlim(), limits)
    finally:
        results.close()

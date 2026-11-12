"""Navegação por tarefa preserva rascunhos, evidências e acessibilidade."""
from dataclasses import replace
import re
import pytest
import numpy as np
from PySide6.QtCore import Qt, QItemSelectionModel, QSettings
from PySide6.QtWidgets import QAbstractItemView
from core.examples import create_example_config
from core.simulation import run_experiment
from core.figures import probability_figure
from gui.main_window import MainWindow
from gui.navigation import NAV_ITEMS
from gui.controllers.appearance import apply_appearance
from gui.formatting import quantity, timestamp
from gui.manual import WELCOME_HTML
from gui.widgets.data_table import configure_table, table_rows, copy_table


def settle(app):
    for _ in range(8):
        app.processEvents()


def load(window, *, snapshots=True, seed=42):
    config = create_example_config('ising')
    config = replace(config, shots=16, seed=seed, protocol=replace(config.protocol, save_snapshots=snapshots))
    record = run_experiment(config)
    window.repository.save(record)
    window._refresh_history()
    window._current_experiment = record
    window._display_experiment(record)
    return record


def test_visible_functions_and_internal_activities_keep_independent_drafts(window):
    assert list(window.sidebar.buttons) == [key for key, _ in NAV_ITEMS]
    form = window.page_simulation.config_panel.get_config()
    window.page_circuit.editor._bell()
    circuit = window.page_circuit.editor.document
    for key in window.pages:
        window._show_page(key)
        assert window.is_page_active(key)
    window._show_page('comparison')
    window.navigation.open_root('dashboard')
    window.navigation.open_root('analysis')
    assert window.is_page_active('comparison')
    assert window.page_simulation.config_panel.get_config() == form
    assert window.page_circuit.editor.document == circuit


def test_laboratory_separates_preparation_from_selected_result(window, qt_app):
    source = load(window)
    workspace = window.page_workspace
    window._show_page('simulation')
    assert workspace.stages.currentIndex() == 0
    assert workspace.draft_label.toolTip().startswith('Em edição:')
    window.page_simulation.config_panel.spin_J.setValue(.12345)
    draft = window.page_simulation.config_panel.get_config()
    workspace.stages.setCurrentIndex(1)
    assert window.is_page_active('results')
    assert workspace.selected_label.isVisible()
    for i in range(workspace.view_selector.count()):
        workspace.view_selector.setCurrentIndex(i)
        settle(qt_app)
        assert window._current_experiment is source
        assert window.page_simulation.config_panel.get_config() == draft
    workspace.stages.setCurrentIndex(0)
    assert window.is_page_active('simulation')
    assert window.page_simulation.config_panel.get_config() == draft


def test_saved_configurations_use_a_separate_dialog(window):
    window._show_page('simulation')
    window._show_saved_configurations()
    assert window.configuration_dialog.isVisible()
    assert window.configuration_dialog.isAncestorOf(window.page_library.templates_group)
    assert window.page_library.tabs.count() == 1
    assert window.is_page_active('simulation')
    window.configuration_dialog.close()


def test_final_state_view_does_not_invent_a_trajectory(window, qt_app):
    record = load(window, snapshots=False)
    assert not record.result.states
    window._show_page('bloch')
    page = window.page_bloch
    assert page.final_only and len(page.original_svs) == 1
    np.testing.assert_array_equal(page.original_svs[0].data, record.result.final_state.data)
    assert not page.btn_play.isEnabled() and not page.slider.isEnabled()
    page.focus_combo.setCurrentIndex(1)
    page._refresh_ui()
    assert 'Estado final' in page.frame_label.text()
    assert 'nenhuma trajetória' in page.timeline_detail.toPlainText()
    assert page.times is None
    np.testing.assert_array_equal(page.ideal_states[0].data, record.result.ideal_final_state.data)


def test_history_compares_two_rows_and_copy_respects_visible_order(window, qt_app):
    a = load(window)
    b = load(window, seed=43)
    window._show_page('history')
    table = window.page_history.table
    for row in range(2):
        table.selectionModel().select(table.model().index(row, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
    assert window.page_history.compare_selected.isEnabled()
    configure_table(table)
    assert table.selectionMode() == QAbstractItemView.ExtendedSelection
    assert len(table.selectionModel().selectedRows()) == 2
    assert table_rows(table)[0][0] == 'Experimento'
    copy_table(table)
    assert qt_app.clipboard().text().startswith('Experimento\t')
    selected = []
    window.page_history.compare_requested.connect(lambda first, second: selected.extend([first, second]))
    window.page_history.compare_selected.click()
    assert set(selected) == {a.id, b.id}
    assert window.is_page_active('comparison')


def test_export_options_open_in_context_and_keep_the_source(window):
    record = load(window)
    window._show_page('results')
    window._open_export_dialog('pdf')
    dialog = window.page_documentation.export_dialog
    assert dialog.isVisible() and window.is_page_active('results')
    assert window._current_experiment is record
    assert window.page_documentation.format.currentData() == 'pdf'
    dialog.close()


def test_layout_roundtrip_and_reset_preserve_experiment_and_draft(window, qt_app):
    record = load(window)
    form = window.page_simulation.config_panel.get_config()
    window.page_settings.category.setCurrentIndex(2)
    window.page_bloch.stage_splitter.setSizes([500, 350])
    window.layout_controller.save()
    restored = MainWindow(window.repository, window.settings)
    try:
        assert restored.page_settings.category.currentIndex() == 2
        assert window.settings.contains('layout/states')
        window.page_analysis.kind.setCurrentIndex(window.page_analysis.kind.findData('equal_budget'))
        study = window.page_analysis.kind.currentData()
        window.layout_controller.reset()
        assert window.page_analysis.kind.currentData() == study
        assert window.page_settings.category.currentIndex() == 0
        assert not window.settings.contains('layout/states')
        assert window.page_simulation.config_panel.get_config() == form
        assert window._current_experiment is record
    finally:
        restored.close()
        restored.deleteLater()


def test_contextual_help_targets_existing_manual_anchors(window):
    for key in window.pages:
        window._show_page(key)
        topic = window.navigation.help_topic()
        assert f'id="{topic}"' in WELCOME_HTML, (key, topic)


def test_study_families_keep_every_study_available(window):
    page = window.page_analysis
    found = set()
    for i in range(page.family.count()):
        page.family.setCurrentIndex(i)
        for k in range(page.kind.count()):
            if not page.kind.view().isRowHidden(k):
                found.add(page.kind.itemData(k))
    assert found == {page.kind.itemData(k) for k in range(page.kind.count())}


def test_numerical_presentation_keeps_small_values_and_humane_dates():
    assert quantity(1e-12) == '1.000e-12'
    assert quantity(None) == '—'
    assert quantity(0) == '0'
    assert re.match(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}', timestamp('2026-11-12T12:00:00+00:00'))


def test_screen_and_report_probability_plots_use_the_same_selection(window):
    record = load(window)
    portable = probability_figure(record)
    screen = window.page_results.results_tab.canvas_evol.fig
    try:
        assert [line.get_label() for line in screen.axes[0].lines] == [line.get_label() for line in portable.axes[0].lines]
        for left, right in zip(screen.axes[0].lines, portable.axes[0].lines):
            np.testing.assert_array_equal(left.get_ydata(), right.get_ydata())
        assert screen.axes[0].get_ylabel() == portable.axes[0].get_ylabel()
    finally:
        portable.clear()


@pytest.mark.parametrize('theme', ['dark', 'light', 'navy'])
@pytest.mark.parametrize('size,font', [((1440, 960), 15), ((1024, 768), 24)])
def test_task_routes_fit_and_keep_execution_actions_reachable(window, qt_app, theme, size, font):
    load(window)
    apply_appearance(window, theme, font)
    window.resize(*size)
    for key in window.pages:
        window._show_page(key)
        settle(qt_app)
        assert window.is_page_active(key)
        assert (window.width(), window.height()) == size
        assert window.pages[key]._scroll.horizontalScrollBar().maximum() == 0
    window._show_page('simulation')
    settle(qt_app)
    for button in (window.page_simulation.btn_run, window.page_simulation.examples_button):
        assert button.isVisible()
        assert window.rect().contains(button.mapTo(window, button.rect().center()))


def test_final_bloch_export_action_is_visible_and_preserves_provenance(window, qt_app, tmp_path, monkeypatch):
    import json
    from PySide6.QtWidgets import QFileDialog
    record = load(window, snapshots=False)
    window._show_page('bloch')
    settle(qt_app)
    assert window.export_bloch_view.isVisible()
    assert window.rect().contains(window.export_bloch_view.mapTo(window, window.export_bloch_view.rect().center()))
    destination = tmp_path / 'estado-final.svg'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(destination), 'SVG (*.svg)'))
    window.export_bloch_view.click()
    assert destination.is_file()
    metadata = json.loads(destination.with_suffix('.metadata.json').read_text())
    assert metadata['source_id'] == record.id
    assert metadata['snapshot'] is None and metadata['state_kind'] == 'final'
    assert metadata['camera'] == window.page_bloch.canvas.camera_state()
    window._show_page('simulation')
    assert not window.export_bloch_view.isVisible()


def test_restored_comparison_chart_matches_visible_selector(window):
    page = window.page_comparison
    page.apply_view_preferences({'tab': 4})
    assert page.tabs.currentIndex() == page.view_selector.currentIndex() == 4
    page.apply_view_preferences({'tab': 5})
    assert page.tabs.currentWidget() is page.metrics_table
    assert page.view_selector.currentText() == 'Métricas numéricas'

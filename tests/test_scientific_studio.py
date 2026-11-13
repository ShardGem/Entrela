"""Composição do estúdio e continuidade entre rascunhos e evidências reais."""
from dataclasses import replace
import numpy as np
from PySide6.QtCore import Qt
from core.examples import create_example_config
from core.simulation import run_experiment
from gui.widgets.analysis_guidance import STUDIES
from tests.qt_helpers import wait_until


def settle(app):
    for _ in range(8):
        app.processEvents()


def source(window):
    experiment = run_experiment(replace(create_example_config('bell'), shots=32))
    window.repository.save(experiment)
    window._current_experiment = experiment
    window._display_experiment(experiment)
    return experiment


def test_scientific_area_has_priority_and_parameters_are_in_the_inspector(window, qt_app):
    window.resize(1920,1080)
    window._show_page('simulation')
    settle(qt_app)
    page=window.page_simulation
    assert not page._compact
    assert page.splitter.widget(0) is page.summary_scroll
    assert page.splitter.widget(1) is page.config_panel
    assert page.summary_scroll.width() > page.config_panel.width()
    assert not window.page_workspace.stages.isVisible()
    assert not window.page_workspace.view_selector.isVisible()
    assert page.config_panel._inspector_mode
    assert set(window.pages) <= set(window.sidebar.buttons)


def test_editing_preparation_does_not_change_the_evidence_on_the_workbench(window, qt_app):
    experiment=source(window)
    window.resize(1920,1080)
    window._show_page('simulation')
    page=window.page_simulation
    original=experiment.result.final_state.data.copy()
    counts=dict(experiment.result.counts)
    page.config_panel.spin_J.setValue(.1234567890123)
    page.preview_tabs.setCurrentIndex(2)
    settle(qt_app)
    assert page._source_experiment is experiment
    assert page.source_view.isVisible()
    assert page.source_metrics[0].toolTip() == str(experiment.result.fidelity)
    assert sum(bar.get_height() for bar in page.source_plot.fig.axes[0].patches) == 1
    assert experiment.result.counts == counts
    np.testing.assert_array_equal(experiment.result.final_state.data, original)
    assert page.config_panel.get_config() != experiment.config
    assert window._current_worker is None


def test_chart_views_preserve_counts_probabilities_and_scientific_labels(window, qt_app):
    experiment=source(window)
    window._show_page('results')
    graph=window.page_results.results_tab
    assert graph.chart_views.currentIndex() == 0
    assert graph.canvas_hist.isVisible() and not graph.canvas_evol.isVisible()
    counts=dict(graph._counts)
    probabilities=graph._probabilities.copy()
    graph.chart_views.setCurrentIndex(1)
    settle(qt_app)
    assert graph.canvas_evol.isVisible() and not graph.canvas_hist.isVisible()
    graph.chart_views.setCurrentIndex(2)
    settle(qt_app)
    assert graph.canvas_evol.isVisible() and graph.canvas_hist.isVisible()
    assert graph._counts == counts == experiment.result.counts
    np.testing.assert_array_equal(graph._probabilities, probabilities)
    assert 'Probabilidade' in graph.canvas_evol.fig.axes[0].get_ylabel()


def test_editor_execution_inspector_drives_the_existing_simulator(window, qt_app):
    window.resize(1920,1080)
    window.navigation.open_page('circuit')
    editor=window.page_circuit.editor
    editor._bell()
    editor.inspector_tabs.setCurrentIndex(1)
    editor.shots.setValue(32)
    editor.seed.setText('42')
    editor.noise.setChecked(False)
    settle(qt_app)
    assert editor.shots.isVisible()
    assert editor.scene_splitter.widget(1) is editor.operation_views
    document=editor.document
    editor.run.click()
    wait_until(lambda: window._current_worker is None)
    assert window._current_experiment.config.circuit == document
    assert window._current_experiment.config.shots == 32
    assert sum(window._current_experiment.result.counts.values()) == 32
    assert window._current_experiment.result.fidelity > .999999


def test_study_catalog_keeps_the_canonical_studies_and_source(window):
    experiment=source(window)
    page=window.page_analysis
    found=set()
    for family in range(page.family.count()):
        page.family.setCurrentIndex(family)
        for row in range(page.study_catalog.count()):
            key=page.study_catalog.item(row).data(Qt.UserRole)
            page.study_catalog.setCurrentRow(row)
            assert page.kind.currentData() == key
            found.add(key)
    assert found == set(STUDIES)
    assert window._current_experiment is experiment
    assert window._current_worker is None


def test_preferences_list_and_persisted_category_stay_in_sync(window):
    page=window.page_settings
    assert page.category_list.count() == page.category.count() == 5
    for row in range(page.category_list.count()):
        page.category_list.setCurrentRow(row)
        assert page.sections.currentIndex() == page.category.currentIndex() == row
    page.category.setCurrentIndex(1)
    assert page.category_list.currentRow() == 1
    window.layout_controller.save()
    assert window.settings.value('layout/choice/preferences', type=int) == 1
    assert len(page.restore_menu_button.menu().actions()) == 2


def test_transport_stays_below_the_scene_and_keeps_camera_independent(window, qt_app):
    source(window)
    window.resize(1920,1080)
    window._show_page('bloch')
    settle(qt_app)
    page=window.page_bloch
    assert page.transport.y() >= page.stage_splitter.y()+page.stage_splitter.height()
    assert page.btn_play.isVisible() and page.speed_combo.isVisible()
    camera=page.canvas.camera_state()
    page.slider.setValue(2)
    page.btn_play.click()
    assert page.timer.isActive()
    page.btn_prev.click()
    assert page.canvas.camera_state() == camera


def test_workbench_views_fit_small_windows_with_enlarged_text(window, qt_app):
    source(window)
    window.page_settings.apply_values({'font_size': 24})
    window._apply_preferences()
    window.resize(1024, 768)
    window._show_page('simulation')
    page = window.page_simulation
    settle(qt_app)
    page.compact_tabs.setCurrentIndex(1)
    for tab in range(page.preview_tabs.count()):
        page.preview_tabs.setCurrentIndex(tab)
        settle(qt_app)
        assert page._scroll.horizontalScrollBar().maximum() == 0
        assert page.summary_scroll.horizontalScrollBar().maximum() == 0
    assert all(metric.isVisible() for metric in page.source_metrics)


def test_wide_history_keeps_the_view_action_inside_the_master_pane(window, qt_app):
    experiment = source(window)
    page = window.page_history
    page.annotations = {experiment.id: {'title': 'Ising · referência para uma investigação reproduzível'}}
    page.load([experiment])
    window.resize(1920, 1080)
    window._show_page('history')
    settle(qt_app)
    page.set_detail(experiment)
    settle(qt_app)
    table = page.table
    action = table.visualRect(table.model().index(0, 9))
    assert action.right() <= table.viewport().width()
    assert table.horizontalScrollBar().maximum() == 0
    assert table.cellWidget(0, 9).accessibleName() == 'Visualizar'


def test_preferences_remain_readable_with_enlarged_text_in_a_small_window(window, qt_app):
    page = window.page_settings
    page.apply_values({'font_size': 24})
    window._apply_preferences()
    window.resize(1024, 768)
    window._show_page('settings')
    settle(qt_app)
    assert page.category.isVisible()
    assert not page.category_list.isVisible()
    for row in range(page.category.count()):
        page.category.setCurrentIndex(row)
        settle(qt_app)
        assert page.sections.currentWidget().horizontalScrollBar().maximum() == 0
        assert page._scroll.horizontalScrollBar().maximum() == 0
        assert page.sections.currentIndex() == page.category_list.currentRow() == row


def test_editor_adapts_its_three_panes_without_replacing_the_document(window, qt_app):
    window.resize(1920, 1080)
    window.navigation.open_page('circuit')
    editor = window.page_circuit.editor
    editor._bell()
    editor._select(1)
    before = editor.draft_state()
    window.page_settings.apply_values({'font_size': 24})
    window._apply_preferences()
    window.resize(1024, 768)
    settle(qt_app)
    assert editor._compact_scene
    for widget in (editor.palette_panel, editor.operation_views, editor.inspector_tabs):
        editor.scene_compact_tabs.setCurrentWidget(widget)
        settle(qt_app)
        assert widget.isVisible()
        assert window.page_circuit._scroll.horizontalScrollBar().maximum() == 0
    editor.scene_compact_tabs.setCurrentIndex(1)
    editor.inspector_toggle.click()
    assert editor.scene_compact_tabs.currentWidget() is editor.inspector_tabs
    assert editor.draft_state() == before
    assert editor.run.isVisible()
    window.page_settings.apply_values({'font_size': 15})
    window._apply_preferences()
    window.resize(1920, 1080)
    settle(qt_app)
    assert not editor._compact_scene
    assert editor.scene_splitter.widget(1) is editor.operation_views
    assert editor.draft_state() == before

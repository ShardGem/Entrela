"""Estudos e ZNE preservam parâmetros e comandos com texto ampliado."""
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest

from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance


def settle(app):
    for _ in range(12):
        app.processEvents()


def source(window):
    record = run_experiment(replace(create_example_config('bell'), shots=16))
    window._current_experiment = record
    window._display_experiment(record)
    return record


def test_study_context_and_execution_actions_use_full_width_at_large_text(window, qt_app):
    record = source(window)
    counts = dict(record.result.counts)
    window.navigation.open_page('analysis')
    apply_appearance(window, 'navy', 24)
    window.resize(1024, 768)
    settle(qt_app)
    page = window.page_analysis
    assert page._compact_analysis
    assert page.context.width() >= page.source_bar.width() - 4
    assert page.kind.isVisible()
    assert not page.study_catalog.isVisible()
    assert page._scroll.horizontalScrollBar().maximum() == 0
    assert window.rect().contains(page.btn_run.mapTo(window, page.btn_run.rect().bottomRight()))
    page.family.setCurrentIndex(page.family.findData('noise'))
    page.kind.setCurrentIndex(page.kind.findData('heatmap'))
    assert page.kind.currentData() == 'heatmap'
    assert page.x_values.isVisible() and page.y_values.isVisible()
    assert window._current_experiment is record
    assert record.result.counts == counts
    assert window._current_worker is None


def test_study_layout_reacts_to_font_change_without_a_window_resize(window, qt_app):
    source(window)
    window.navigation.open_page('analysis')
    window.resize(1500, 900)
    apply_appearance(window, 'navy', 15)
    settle(qt_app)
    page = window.page_analysis
    assert not page._compact_analysis
    size = window.size()
    apply_appearance(window, 'navy', 24)
    settle(qt_app)
    assert window.size() == size
    assert page._compact_analysis
    assert page.kind.isVisible() and not page.study_catalog.isVisible()


def test_zne_compact_configuration_and_keyboard_execution_are_reachable(window, qt_app):
    source(window)
    window.navigation.open_page('mitigation')
    apply_appearance(window, 'navy', 24)
    window.resize(1024, 768)
    settle(qt_app)
    page = window.page_mitigation
    assert page._compact
    assert page.compact_tabs.currentWidget() is page.inspector_scroll
    assert page.inspector_scroll.width() >= page.compact_tabs.width() - 24
    assert page._scroll.horizontalScrollBar().maximum() == 0
    page.qubit.setFocus(Qt.TabFocusReason)
    for _ in range(12):
        if page.btn_run.hasFocus():
            break
        QTest.keyClick(qt_app.focusWidget(), Qt.Key_Tab)
        settle(qt_app)
    assert page.btn_run.hasFocus()
    assert window.rect().contains(page.btn_run.mapTo(window, page.btn_run.rect().bottomRight()))
    assert window._current_worker is None


def test_zne_result_and_parameters_survive_compact_and_wide_layouts(window, qt_app):
    record = source(window)
    mitigation = {
        'qubit': 1, 'method': 'quadratic', 'shots': 128,
        'scale_factors': [1, 3, 5], 'measured': [.1, .08, .06],
        'stderr': [.02, .02, .02], 'coefficients': [0, -.01, .11],
        'extrapolated': .11, 'extrapolated_stderr': .03,
    }
    saved = replace(record, result=replace(record.result, mitigation=mitigation))
    page = window.page_mitigation
    window.navigation.open_page('mitigation')
    apply_appearance(window, 'navy', 24)
    window.resize(1024, 768)
    settle(qt_app)
    requested = QSignalSpy(page.run_requested)
    page.load_experiment(saved)
    settle(qt_app)
    assert page.compact_tabs.currentWidget() is page.views
    rows = [[page.table.item(r, c).text() for c in range(4)] for r in range(3)]
    window.resize(1920, 1080)
    apply_appearance(window, 'navy', 15)
    settle(qt_app)
    assert not page._compact
    assert page.views.isVisible() and page.inspector_scroll.isVisible()
    window.resize(1024, 768)
    apply_appearance(window, 'navy', 24)
    settle(qt_app)
    assert page._compact
    assert page.qubit.value() == 1
    assert page.method.currentData() == 'quadratic'
    assert page.shots.value() == 128
    assert [[page.table.item(r, c).text() for c in range(4)] for r in range(3)] == rows
    assert page.table.property('dataTable')
    assert requested.count() == 0
    assert record.result.mitigation is None

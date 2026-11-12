"""Fluxos visuais preservam evidências ao alternar abas e recolher painéis."""

from dataclasses import replace
import json

import numpy as np
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout

from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance
from gui.main_window import MainWindow
from gui.widgets.content_tabs import ContentTabs


def settle(app):
    for _ in range(10):
        app.processEvents()


def load(window):
    experiment = run_experiment(replace(create_example_config('ising'), shots=64))
    window.repository.save(experiment)
    window._current_experiment = experiment
    window._display_experiment(experiment)
    window.page_simulation.config_panel.load_config(experiment.config)
    return experiment


def test_hidden_tab_does_not_reserve_height_for_its_text(qt_app):
    host = QWidget()
    layout = QVBoxLayout(host)
    tabs = ContentTabs()
    graph = QLabel('Gráfico')
    graph.setMinimumSize(200, 180)
    text = QLabel('Explicação\n' * 100)
    tabs.addTab(graph, 'Gráfico')
    tabs.addTab(text, 'Texto extenso')
    layout.addWidget(tabs)
    host.resize(700, 400)
    host.show()
    try:
        settle(qt_app)
        before = tabs.minimumSizeHint().height()
        text.setText(text.text() * 3)
        settle(qt_app)
        assert tabs.minimumSizeHint().height() == before
        assert graph.height() <= host.height()
        tabs.setCurrentWidget(text)
        assert tabs.minimumSizeHint().height() > before
        tabs.setCurrentWidget(graph)
        assert tabs.minimumSizeHint().height() == before
    finally:
        host.close()
        host.deleteLater()


def test_results_keep_full_plots_visible_after_other_tabs(window, qt_app):
    experiment = load(window)
    window.resize(1440, 960)
    window._show_page('results')
    page = window.page_results
    for tab in (page.metadata, page.state_inspector, page.interpretation, page.results_tab):
        page.tabs.setCurrentWidget(tab)
        settle(qt_app)
    assert page._scroll.verticalScrollBar().maximum() == 0
    viewport = page._scroll.viewport()
    for canvas in (page.results_tab.canvas_hist, page.results_tab.canvas_evol):
        bottom = canvas.mapTo(viewport, QPoint(0, canvas.height()))
        assert bottom.y() <= viewport.height()
    assert page.results_tab._counts == experiment.result.counts


def test_small_results_stack_plots_with_the_same_data(window, qt_app):
    experiment = load(window)
    window._show_page('results')
    apply_appearance(window, 'light', 24)
    window.resize(1024, 768)
    settle(qt_app)
    graph = window.page_results.results_tab
    first = graph.canvas_hist.mapTo(graph, QPoint(0, 0))
    second = graph.canvas_evol.mapTo(graph, QPoint(0, 0))
    assert second.y() >= first.y() + graph.canvas_hist.height()
    assert window.page_results._scroll.horizontalScrollBar().maximum() == 0
    assert graph._counts == experiment.result.counts


def test_guided_form_reserves_space_for_inputs_and_keeps_errors(window, qt_app):
    load(window)
    page = window.page_simulation
    panel = page.config_panel
    window._show_page('simulation')
    apply_appearance(window, 'navy', 24)
    window.resize(1024, 768)
    panel.set_mode('guided')
    panel.set_section('system')
    settle(qt_app)
    assert panel.sections['system'].header.isHidden()
    viewport = panel.parameter_scroll.viewport()
    center = panel.spin_qubits.mapTo(viewport, panel.spin_qubits.rect().center())
    assert viewport.rect().contains(center)
    panel.combo_initial.setCurrentIndex(panel.combo_initial.findData('bell'))
    panel.spin_qubits.setValue(3)
    settle(qt_app)
    assert page.configuration_feedback.isVisible()
    assert not page.btn_run.isEnabled()
    panel.set_mode('advanced')
    assert not panel.sections['system'].header.isHidden()


def test_bloch_folding_and_saved_layout_keep_snapshot_and_camera(window, qt_app):
    experiment = load(window)
    window.resize(1440, 960)
    window._show_page('bloch')
    settle(qt_app)
    page = window.page_bloch
    page.slider.setValue(2)
    page.canvas.set_zoom(1.4)
    before_camera = page.canvas.camera_state()
    before_state = experiment.result.states[2].data.copy()
    page.camera_toggle.setChecked(True)
    page.camera_toggle.click()
    page.details_section.header.click()
    settle(qt_app)
    assert page.camera_scroll.isHidden()
    assert page.details_section.is_expanded
    stored = json.loads(window.settings.value('bloch/view'))
    assert stored == {'camera': False, 'details': True}
    page.set_maximized(True)
    page.set_maximized(False)
    window.resize(1024, 768)
    apply_appearance(window, 'light', 18)
    settle(qt_app)
    assert page.current_frame == 2
    assert page.canvas.camera_state() == before_camera
    np.testing.assert_array_equal(experiment.result.states[2].data, before_state)
    assert page.camera_scroll.isHidden()
    window.close()
    other = MainWindow(window.repository, window.settings)
    try:
        assert other.page_bloch.collect_view_preferences() == stored
    finally:
        other.close()
        other.deleteLater()

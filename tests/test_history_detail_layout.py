from dataclasses import replace

import pytest
from PySide6.QtCore import Qt

from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance


@pytest.fixture(scope='module')
def record():
    return run_experiment(replace(create_example_config('bell'), shots=16, seed=17))


@pytest.mark.parametrize('size,font_size,orientation', [
    ((1440, 900), 15, Qt.Vertical),
    ((1920, 1080), 15, Qt.Horizontal),
    ((1024, 768), 24, Qt.Vertical),
])
def test_history_inspector_does_not_push_content_past_the_viewport(window, qt_app, record, size, font_size, orientation):
    page = window.page_history
    page.load([record])
    window._show_page('history')
    apply_appearance(window, 'navy', font_size)
    window.resize(*size)
    page.set_detail(record, files=[])
    page.detail_tabs.setCurrentWidget(page.circuit)
    for _ in range(20):
        qt_app.processEvents()
    assert page.splitter.orientation() == orientation
    assert page._scroll.horizontalScrollBar().maximum() == 0
    assert page._body_widget.width() == page._scroll.viewport().width()
    assert page.circuit.experiment.id == record.id
    assert page.selected_identifier == record.id
    page.expand_details.setChecked(True)
    for _ in range(20):
        qt_app.processEvents()
    assert page._scroll.horizontalScrollBar().maximum() == 0
    assert page.open_result.isEnabled() and page.use_config.isEnabled()

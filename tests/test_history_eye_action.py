"""Visualização por ícone mantém foco, acessibilidade e identidade dos registros."""
from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QSignalSpy, QTest

from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance
from gui.pages.history import HistoryPage
from gui.theme import PALETTE


@pytest.fixture(scope="module")
def record():
    return run_experiment(replace(create_example_config("bell"), shots=16, seed=17))


def test_view_action_is_an_accessible_icon_without_visible_text(qt_app, record):
    page = HistoryPage()
    page.annotations = {record.id: {"title": "Bell de referência"}}
    page.load([record])
    try:
        button = page.table.cellWidget(0, 9)
        assert button.text() == ""
        assert not button.icon().isNull()
        assert button.toolTip() == "Visualizar"
        assert button.accessibleName() == "Visualizar"
        assert "Bell de referência" in button.accessibleDescription()
        assert record.id not in button.accessibleDescription()
        assert button.focusPolicy() == Qt.StrongFocus
    finally:
        page.close()


def test_keyboard_view_targets_record_after_sorting_and_pagination(qt_app, record):
    page = HistoryPage()
    page.page_size = 2
    records = [replace(record, id=f"registro-{index}") for index in range(5)]
    page.annotations = {item.id: {"title": f"Experimento {4-index}"} for index, item in enumerate(records)}
    page.load(records)
    page.resize(1000, 800)
    page.show()
    page.table.sortItems(1, Qt.AscendingOrder)
    requested = QSignalSpy(page.detail_requested)
    try:
        qt_app.processEvents()
        button = page.table.cellWidget(0, 9)
        button.setFocus(Qt.TabFocusReason)
        assert button.hasFocus()
        QTest.keyClick(button, Qt.Key_Space)
        assert requested.count() == 1
        assert requested.at(0) == [records[4].id]
        assert page.detail_title.text() == "Experimento 0"
        page.next.click()
        qt_app.processEvents()
        button = page.table.cellWidget(0, 9)
        button.setFocus(Qt.TabFocusReason)
        QTest.keyClick(button, Qt.Key_Space)
        assert requested.count() == 2
        assert requested.at(1) == [records[2].id]
        assert page.detail_title.text() == "Experimento 2"
    finally:
        page.close()


@pytest.mark.parametrize("theme,font_size", [("dark", 15), ("light", 24)])
def test_view_action_fits_cell_and_has_rendered_keyboard_focus(window, qt_app, record, theme, font_size):
    page = window.page_history
    page.load([record])
    window._show_page("history")
    try:
        apply_appearance(window, theme, font_size)
        window.resize(1024, 768)
        for _ in range(4):
            qt_app.processEvents()
        button = page.table.cellWidget(0, 9)
        page.table.scrollTo(page.table.model().index(0, 9))
        button.setFocus(Qt.TabFocusReason)
        qt_app.processEvents()
        assert button.hasFocus()
        assert button.width() >= 40
        assert button.height() >= 32
        assert button.width() >= button.iconSize().width() + 16
        assert button.height() >= button.iconSize().height() + 8
        focused = button.grab().toImage()
        focused_edge = focused.pixelColor(focused.width()//2, 1)
        assert focused_edge == QColor(PALETTE.text)
        page.search.setFocus(Qt.TabFocusReason)
        qt_app.processEvents()
        unfocused = button.grab().toImage()
        assert unfocused.pixelColor(unfocused.width()//2, 1) != focused_edge
    finally:
        apply_appearance(window)

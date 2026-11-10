"""Circuit workbench navigation stays reachable without changing its document."""
from dataclasses import replace

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QGraphicsItem, QApplication

from core.circuit_document import CircuitDocument, CircuitGate, GATES
from gui.controllers.appearance import apply_appearance
from gui.widgets.circuit_canvas import GateItem
from gui.widgets.circuit_editor import CircuitEditor, GATE_CATEGORIES


@pytest.fixture
def editor(qt_app):
    widget = CircuitEditor()
    widget.resize(1080, 800)
    widget.show()
    qt_app.processEvents()
    yield widget
    QApplication.clipboard().clear()
    widget.close()
    widget.deleteLater()


def test_gate_search_and_categories_keep_every_supported_operation(editor):
    assert set(editor.palette_buttons) == set(GATES)
    categorized = [name for names in GATE_CATEGORIES.values() for name in names]
    assert len(categorized) == len(set(categorized)) == len(GATES)
    assert set(categorized) == set(GATES)
    document = editor.document
    editor.gate_search.setText("rotacao em x")
    assert editor._visible_gates == ["rx"]
    editor.gate_search.setText("Toffoli")
    assert editor._visible_gates == ["ccx"]
    editor.gate_search.clear()
    editor.gate_category.setCurrentIndex(editor.gate_category.findData("Controladas"))
    assert set(editor._visible_gates) == {"cx", "cy", "cz", "ch", "ccx"}
    editor.gate_search.setText("não existe")
    assert editor._visible_gates == []
    assert not editor.palette_empty.isHidden()
    editor.gate_search.clear()
    editor.gate_category.setCurrentIndex(0)
    assert set(editor._visible_gates) == set(GATES)
    assert all(not button.isHidden() for button in editor.palette_buttons.values())
    assert editor.document == document
    assert editor.undo_stack.count() == 0


def test_list_and_canvas_selection_share_keyboard_clipboard_and_precision(editor, qt_app):
    angle = .12345678901234567
    document = CircuitDocument(2, (CircuitGate("h", (0,)), CircuitGate("rx", (1,), (angle,)),
                                   CircuitGate("cx", (0, 1))))
    editor.replace_document(document)
    editor._select(1)
    assert editor.operations_list.selectedItems()[0].data(Qt.UserRole) == 1
    assert str(angle) in editor.operations_list.item(1).text()
    editor.operation_views.setCurrentIndex(1)
    editor.operations_list.setFocus()
    QTest.keyClick(editor.operations_list, Qt.Key_Down)
    assert editor.selected_indices == [2]
    assert [item.index for item in editor.canvas.scene().selectedItems()] == [2]
    QTest.keyClick(editor.operations_list, Qt.Key_Up, Qt.ShiftModifier)
    assert editor.selected_indices == [1, 2]
    QTest.keyClick(editor.operations_list, Qt.Key_C, Qt.ControlModifier)
    QTest.keyClick(editor.operations_list, Qt.Key_V, Qt.ControlModifier)
    assert editor.document.gates == document.gates + document.gates[1:]
    assert editor.document.gates[-2].parameters == (angle,)
    editor.undo_stack.undo()
    assert editor.document == document
    editor.operation_views.setCurrentIndex(0)
    editor.canvas.setFocus()
    editor._select(0)
    QTest.keyClick(editor.canvas, Qt.Key_Right)
    assert editor.selected == 1
    assert editor.param_fields[0].text() == repr(angle)
    assert editor.operations_list.selectedItems()[0].data(Qt.UserRole) == 1
    QTest.keyClick(editor.canvas, Qt.Key_Right, Qt.ShiftModifier)
    assert editor.selected_indices == [1, 2]
    assert len(editor.operations_list.selectedItems()) == 2
    assert all(item.flags() & QGraphicsItem.ItemIsFocusable for item in editor.canvas.scene().items()
               if isinstance(item, GateItem))
    assert editor.document == document


@pytest.mark.parametrize("font_size", [15, 24])
def test_execution_stays_visible_while_page_scrolls(window, qt_app, font_size):
    page = window.page_circuit
    editor = page.editor
    window._show_page("circuit")
    page.tabs.setCurrentWidget(editor)
    apply_appearance(window, "dark", font_size)
    window.resize(1024, 768)
    for _ in range(5):
        qt_app.processEvents()
    try:
        first_position = editor.run.mapTo(page, QPoint())
        assert page.rect().contains(first_position)
        assert page.rect().contains(editor.run.mapTo(page, editor.run.rect().bottomRight()))
        assert editor.execution_bar.parentWidget() is page
        assert editor.run.width() >= editor.run.minimumSizeHint().width()
        page._scroll.verticalScrollBar().setValue(page._scroll.verticalScrollBar().maximum())
        qt_app.processEvents()
        assert editor.run.mapTo(page, QPoint()) == first_position
        assert page._scroll.horizontalScrollBar().maximum() == 0
        editor.creation_help.set_expanded(True, animate=False)
        qt_app.processEvents()
        assert editor.run.mapTo(page, QPoint()) == first_position
        page.tabs.setCurrentIndex(0)
        assert editor.execution_bar.isHidden()
        page.tabs.setCurrentWidget(editor)
        assert not editor.execution_bar.isHidden()
    finally:
        apply_appearance(window)


def test_fixed_execution_preserves_configuration_and_cancel_signal(window, qt_app):
    page = window.page_circuit
    editor = page.editor
    editor._bell()
    editor.shots.setValue(73)
    editor.seed.setText("987")
    configurations, cancelled = [], []
    # Keep this test independent from the application's execution scheduler.
    page.run_requested.disconnect()
    page.run_requested.connect(configurations.append)
    page.cancel_requested.connect(lambda: cancelled.append(True))
    editor.run.click()
    assert len(configurations) == 1
    assert configurations[0].circuit == editor.document
    assert configurations[0].shots == 73
    assert configurations[0].seed == 987
    page.set_running(True)
    assert not editor.run.isEnabled()
    assert editor.cancel.isEnabled()
    editor.cancel.click()
    assert cancelled == [True]
    page.set_running(False)
    assert editor.run.isEnabled()
    assert not editor.cancel.isEnabled()
    editor.seed.setText("inválida")
    editor.run.click()
    assert len(configurations) == 1
    assert "Revise a configuração" in editor.execution_status.text()

"""Circuit explanations and templates preserve the editable scientific document."""
import numpy as np
import pytest
from PySide6.QtWidgets import QMessageBox
from qiskit.quantum_info import Statevector

from core.circuit_document import CircuitDocument, CircuitGate
from gui.controllers.appearance import apply_appearance
from gui.widgets.circuit_editor import CircuitEditor
from gui.widgets.circuit_guidance import TEMPLATES


@pytest.mark.parametrize("key,probabilities", [
    ("superposicao", [.5, .5]), ("bell", [.5, 0, 0, .5]),
    ("qubit", [0, 1]), ("interferencia", [0, 1]), ("bloch", [.5, .5]),
])
def test_load_template_is_editable_undoable_and_does_not_run(qt_app, key, probabilities):
    editor = CircuitEditor()
    requested = []
    editor.run_requested.connect(requested.append)
    editor.seed.setText("123")
    editor.shots.setValue(231)
    editor.noise.setChecked(True)
    editor.p1.setValue(.0123456789012345)
    editor.circuit_name.setText("Meu estudo")
    before = editor.document
    try:
        editor.template_selector.setCurrentIndex(editor.template_selector.findData(key))
        editor.use_template.click()
        template = next(item for item in TEMPLATES if item.key == key)
        assert editor.document == template.document
        np.testing.assert_allclose(Statevector.from_instruction(editor.document.to_quantum_circuit()).probabilities(), probabilities, atol=1e-12)
        assert editor.circuit_name.text() == "Meu estudo"
        assert editor.seed.text() == "123"
        assert editor.shots.value() == 231
        assert editor.noise.isChecked()
        assert editor.p1.value() == .0123456789012345
        assert requested == []
        assert "analítica" in editor.template_hint.text()
        editor.undo_stack.undo()
        assert editor.document == before
        editor.undo_stack.redo()
        assert editor.document == template.document
    finally:
        editor.close()


def test_template_cancellation_preserves_unfinished_parameters(qt_app, monkeypatch):
    editor = CircuitEditor()
    editor.replace_document(CircuitDocument(1, (CircuitGate("rx", (0,), (.123456789012345,)),)))
    editor._select(0)
    editor.param_fields[0].setText("pi /")
    before = editor.document
    editor.template_selector.setCurrentIndex(editor.template_selector.findData("bell"))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
    try:
        editor.use_template.click()
        assert editor.document == before
        assert editor.param_fields[0].text() == "pi /"
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
        editor.use_template.click()
        assert [gate.name for gate in editor.document.gates] == ["h", "cx"]
        editor.undo_stack.undo()
        assert editor.document == before
    finally:
        editor.close()


def test_explanations_and_control_roles_are_available_without_running(qt_app):
    editor = CircuitEditor()
    try:
        before = editor.document
        editor.creation_help.set_expanded(True, animate=False)
        assert editor.document == before
        assert "Hadamard" in editor.palette_buttons["h"].text()
        assert "X controlado" in editor.palette_buttons["cx"].text()
        assert "radianos" in editor.param_fields[0].toolTip()
        assert "não altera probabilidades" in editor.phase.toolTip()
        editor._bell()
        editor._select(1)
        assert "controle" in editor.qubit_fields[0].accessibleName()
        assert "alvo" in editor.qubit_fields[1].accessibleName()
        assert editor.gate_type.currentText() == "cx"
        assert editor.draft_state()["gate_type"] == "cx"
    finally:
        editor.close()


@pytest.mark.parametrize("font_size", [15, 24])
def test_explained_editor_does_not_force_horizontal_page_scroll(window, qt_app, font_size):
    editor = window.page_circuit.editor
    window._show_page("circuit")
    window.page_circuit.tabs.setCurrentWidget(editor)
    try:
        apply_appearance(window, "dark", font_size)
        window.resize(1024, 768)
        for _ in range(5):
            qt_app.processEvents()
        assert window.page_circuit._scroll.horizontalScrollBar().maximum() == 0
        assert editor.palette_scroll.horizontalScrollBar().maximum() == 0
        for button in editor.palette_buttons.values():
            assert button.height() >= len(button.text().splitlines()) * button.fontMetrics().lineSpacing()
        expected = editor.document
        editor.creation_help.set_expanded(True, animate=False)
        qt_app.processEvents()
        assert editor.document == expected
        assert window.page_circuit._scroll.horizontalScrollBar().maximum() == 0
    finally:
        apply_appearance(window)

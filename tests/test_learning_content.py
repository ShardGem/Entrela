"""Analytical checks for the circuits actually offered by the learning catalogue."""
import numpy as np
import pytest
from qiskit.quantum_info import Statevector, partial_trace
from PySide6.QtCore import Qt

from core.learning import CONCEPTS, CONCEPT_BY_KEY
from gui.manual import WELCOME_HTML
from gui.pages.docs import DocsPage


def _state(key):
    document = CONCEPT_BY_KEY[key].demonstration
    document.validate()
    return Statevector.from_instruction(document.to_quantum_circuit())


def test_catalogue_has_complete_distinct_concepts_and_valid_examples():
    assert len(CONCEPTS) == 15
    assert len(CONCEPT_BY_KEY) == len(CONCEPTS)
    for concept in CONCEPTS:
        for field in ("definition", "intuition", "mathematics", "visual", "example", "application", "exercise", "answer", "references"):
            assert getattr(concept, field), (concept.key, field)
        if concept.demonstration is not None:
            state = _state(concept.key)
            assert state.is_valid()
        assert "http" not in concept.to_html()


def test_bell_demonstration_matches_analytic_state():
    expected = np.array([1, 0, 0, 1]) / np.sqrt(2)
    assert np.allclose(_state("bell").data, expected)
    assert np.allclose(partial_trace(_state("emaranhamento"), [1]).data, np.eye(2) / 2)


def test_deutsch_jozsa_balanced_input_output_is_one():
    # q0 is the input, q1 the ancilla; bit strings are q1 q0.
    state = _state("deutsch-jozsa")
    assert np.allclose(state.probabilities(qargs=[0]), [0, 1])
    assert np.allclose(state.probabilities(qargs=[1]), [0.5, 0.5])


def test_grover_specific_oracle_marks_11():
    assert np.allclose(_state("grover").probabilities(), [0, 0, 0, 1])


def test_repetition_demonstration_recovers_qubit_for_explicit_x_error():
    reduced = partial_trace(_state("correcao-erros"), [1, 2])
    psi = np.array([np.cos(0.3), np.sin(0.3)])
    assert np.allclose(reduced.data, np.outer(psi, psi))


def test_unsupported_protocols_are_conceptual():
    assert CONCEPT_BY_KEY["shor"].demonstration is None
    assert CONCEPT_BY_KEY["teletransporte"].demonstration is None
    assert "não suporta medições intermediárias" in CONCEPT_BY_KEY["teletransporte"].demonstration_note


def test_learning_search_selection_demo_and_narrow_layout(qt_app):
    page = DocsPage(WELCOME_HTML)
    opened = []
    page.demonstration_requested.connect(opened.append)
    page.resize(1180, 800)
    page.show()
    qt_app.processEvents()
    assert page.concept_list.count() == 16
    page.search.setText("emaranhamento")
    assert page.concept_list.count() >= 1
    row = next(i for i in range(page.concept_list.count()) if page.concept_list.item(i).data(Qt.UserRole) == "emaranhamento")
    page.concept_list.setCurrentRow(row)
    assert "pureza global" in page.browser.toPlainText()
    page.demo_button.click()
    assert opened == [CONCEPT_BY_KEY["emaranhamento"].demonstration]
    page.search.setText("nao-existe-assunto")
    assert page.concept_list.count() == 0
    assert not page.demo_button.isVisible()
    page.scroll_to("Shots")
    assert page.concept_list.currentItem().data(Qt.UserRole) == "manual"
    assert "Shots" in page.browser.toPlainText()
    page.resize(680, 700)
    qt_app.processEvents()
    assert page.splitter.orientation() == Qt.Vertical
    assert page._scroll.horizontalScrollBar().maximum() == 0
    page.close()

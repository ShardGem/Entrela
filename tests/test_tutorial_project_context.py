"""O tutorial e o histórico devem reconhecer o contexto real da execução."""
from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy

from core.examples import create_example_config
from core.circuit_document import CircuitDocument
from core.simulation import run_experiment
from gui.pages.history import HistoryPage
from gui.widgets.tutorial import BellTutorial


@pytest.fixture(scope="module")
def bell_run():
    return run_experiment(replace(create_example_config("bell"), shots=16, seed=42))


def test_results_page_alone_does_not_unlock_interpretation(qt_app, bell_run):
    tutorial = BellTutorial()
    try:
        tutorial.start(5, bell_run)
        tutorial.update_context(bell_run.config, "results")
        assert not tutorial.ready()
        tutorial.update_context(bell_run.config, "results", "another-record")
        assert not tutorial.ready()
        tutorial.update_context(bell_run.config, "results", bell_run.id)
        assert tutorial.ready()
        tutorial.update_context(bell_run.config, "simulation", bell_run.id)
        assert not tutorial.ready()
    finally:
        tutorial.close()


def test_free_circuit_cannot_pass_as_bell_from_inert_system_fields(bell_run):
    free_circuit = replace(bell_run.config, circuit=CircuitDocument(2))
    assert BellTutorial.matches(bell_run.config)
    assert not BellTutorial.matches(free_circuit)


def test_final_tutorial_steps_have_relevant_navigation_and_real_reopen(qt_app, bell_run):
    tutorial = BellTutorial()
    destinations = QSignalSpy(tutorial.destination_requested)
    sections = QSignalSpy(tutorial.section_requested)
    try:
        tutorial.start(5, bell_run)
        assert destinations.at(0) == ["results"]
        assert "resultados" in tutorial.locate.text()
        tutorial.update_context(bell_run.config, "results", bell_run.id)
        tutorial.advance()
        assert tutorial.step == 6
        assert destinations.at(1) == ["history"]
        assert "histórico" in tutorial.locate.text()
        assert not tutorial.ready()
        tutorial.record_open("another-record")
        assert not tutorial.ready()
        tutorial.record_open(bell_run.id)
        assert tutorial.ready()
        tutorial.back()
        assert tutorial.step == 5
        assert destinations.at(2) == ["results"]
        tutorial.back()
        assert tutorial.step == 4
        assert sections.at(0) == ["execution"]
        assert tutorial.locate.text() == "Ir para a configuração"
    finally:
        tutorial.close()


def test_project_filter_uses_exact_field_and_keeps_free_search_independent(qt_app, bell_run):
    page = HistoryPage()
    records = [replace(bell_run, id=f"run-{index}") for index in range(4)]
    page.annotations = {
        records[0].id: {"project": "Alpha", "title": "Referência Bell"},
        records[1].id: {"project": "Alpha", "title": "Bell repetido"},
        records[2].id: {"project": "Beta", "notes": "Comparar com Alpha"},
        records[3].id: {"project": "Alpha extra", "title": "Outro estudo"},
    }
    page.load(records)
    try:
        page.set_project_filter("Alpha")
        assert page.project_filter == "Alpha"
        assert not page.project_filter_bar.isHidden()
        assert page.table.rowCount() == 2
        assert {page.table.item(row, 0).data(Qt.UserRole) for row in range(2)} == {records[0].id, records[1].id}
        page.search.setText("Referência")
        assert page.table.rowCount() == 1
        assert page.table.item(0, 0).data(Qt.UserRole) == records[0].id
        page.clear_project_filter.click()
        assert page.project_filter is None
        assert page.search.text() == "Referência"
        assert page.project_filter_bar.isHidden()
        assert page.table.rowCount() == 1
        page.search.clear()
        assert page.table.rowCount() == 4
    finally:
        page.close()


def test_project_selection_resets_pagination_and_actions_still_target_records(qt_app, bell_run):
    page = HistoryPage()
    records = [replace(bell_run, id=f"project-run-{index}") for index in range(5)]
    page.page_size = 2
    page.annotations = {
        record.id: {"project": "Alpha" if index < 3 else "Beta", "title": f"Bell {4-index}"}
        for index, record in enumerate(records)
    }
    page.load(records)
    page.table.sortItems(1, Qt.AscendingOrder)
    page.next.click()
    requested = QSignalSpy(page.detail_requested)
    try:
        assert page.offset == 2
        page.set_project_filter("Alpha")
        assert page.offset == 0
        assert page.table.rowCount() == 2
        assert page.next.isEnabled()
        page.table.cellWidget(0, 9).click()
        assert requested.at(0) == [records[2].id]
        page.next.click()
        assert page.table.rowCount() == 1
        page.table.cellWidget(0, 9).click()
        assert requested.at(1) == [records[0].id]
        page.set_project_filter("sem execuções")
        assert page.offset == 0
        assert page.table.rowCount() == 0
        assert "Nenhum experimento" in page.page_label.text()
    finally:
        page.close()


def test_resuming_interpretation_restores_the_tutorial_record(window, bell_run):
    window.repository.save(bell_run)
    window.settings.setValue("tutorial/bell/step", 5)
    window.settings.setValue("tutorial/bell/run_id", bell_run.id)
    window._begin_tutorial()
    assert window.tutorial.step == 5
    assert window._current_experiment.id == bell_run.id
    assert window.is_page_active("results")
    assert window.tutorial.ready()


def test_resuming_reopen_step_routes_to_history_without_pretending_it_was_opened(window, bell_run):
    window.repository.save(bell_run)
    window.settings.setValue("tutorial/bell/step", 6)
    window.settings.setValue("tutorial/bell/run_id", bell_run.id)
    window._begin_tutorial()
    assert window.tutorial.step == 6
    assert window.is_page_active("history")
    assert not window.tutorial.ready()
    window._open_experiment(bell_run.id)
    assert window.tutorial.ready()


def test_project_history_routes_with_exact_filter(window):
    window.page_history.search.setText("Bell")
    window._show_project_history("Alpha")
    assert window.is_page_active("history")
    assert window.page_history.project_filter == "Alpha"
    assert window.page_history.search.text() == "Bell"

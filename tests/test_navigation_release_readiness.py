"""Busca e histórico devem anunciar e abrir o contexto realmente consultado."""

from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from core.examples import create_example_config
from core.learning import CONCEPTS
from core.simulation import run_experiment


@pytest.fixture(scope="module")
def source_record():
    return run_experiment(replace(create_example_config("bell"), shots=16, seed=42))


def history_records(window, source_record):
    records = [replace(source_record, id=f"scope-run-{i}") for i in range(3)]
    for record, project, title in zip(records, ["Alpha", "Beta", ""],
                                       ["Bell Alpha", "Bell Beta", "Bell sem projeto"]):
        window.repository.save(record)
        window._workspace_library().annotate(record.id, project, "Comparar com Alpha", [], title=title)
    window._refresh_history()
    window._refresh_library()
    return records


def visible_ids(page):
    return {page.table.item(row, 0).data(Qt.UserRole) for row in range(page.table.rowCount())}


def test_search_button_works_without_the_removed_shortcut(window, qt_app):
    assert "Ctrl+K" not in [shortcut.key().toString() for shortcut in window.shortcuts]
    assert "Ctrl+K" not in window.sidebar.search.toolTip()
    assert not window.sidebar.search.findChildren(type(window.sidebar.logo), "NavShortcut")
    window.activateWindow()
    window.sidebar.search.setFocus()
    qt_app.processEvents()
    QTest.keyClick(window.sidebar.search, Qt.Key_K, Qt.ControlModifier)
    assert not window.command_palette.isVisible()
    QTest.keyClick(window.sidebar.search, Qt.Key_Space)
    assert window.command_palette.isVisible()
    window.command_palette.close()


def test_global_search_indexes_every_existing_learning_concept(window):
    window._open_commands()
    identifiers = {row[0] for row in window.command_palette._index}
    assert {"concept:" + concept.key for concept in CONCEPTS} <= identifiers
    window.command_palette.close()


def test_contextual_help_opens_instructions_for_the_current_tool(window, monkeypatch):
    requested_topics = []
    monkeypatch.setattr(window, '_show_help', requested_topics.append)
    for key, expected in [('analysis', 'Análises'), ('notebook', 'Documentação'),
                          ('catalog', 'Conceitos'), ('docs', 'Primeiros passos')]:
        window.sidebar.buttons[key].click()
        window.sidebar.help_button.click()
        assert requested_topics[-1] == expected
    window.page_docs.select_concept('manual')
    window.sidebar.help_button.click()
    assert requested_topics[-1] == 'Conceitos'


@pytest.mark.parametrize("query", ["correção", "correcao"])
def test_search_opens_the_exact_concept_without_replacing_the_work(window, source_record, query):
    window.projects.open_project("Alpha")
    window.page_simulation.config_panel.spin_J.setValue(.3456789)
    original_config = window.page_simulation.config_panel.get_config()
    window._current_experiment = source_record
    window.page_docs.search.setText("sem-assunto-correspondente")
    window._open_commands()
    palette = window.command_palette
    palette.search.setText(query)
    item = next(palette.list.item(i) for i in range(palette.list.count())
                if palette.list.item(i).data(Qt.UserRole) == "concept:correcao-erros")
    palette.list.setCurrentItem(item)
    palette._activate()
    assert window.is_page_active("docs")
    assert window.page_docs.concept_list.currentItem().data(Qt.UserRole) == "correcao-erros"
    assert "Correção de erros quânticos" in window.page_docs.browser.toPlainText()
    assert window.page_docs.search.text() == ""
    assert window.projects.project == "Alpha"
    assert window.page_simulation.config_panel.get_config() == original_config
    assert window._current_experiment is source_record
    assert window._current_worker is None


def test_history_changes_scope_with_project_and_distinguishes_unassigned(window, source_record):
    records = history_records(window, source_record)
    page = window.page_history
    page.search.setText("Bell")
    page.status_filter.setCurrentIndex(page.status_filter.findData("ok"))
    for project, expected, label in [("Alpha", {records[0].id}, "Alpha"),
                                     ("Beta", {records[1].id}, "Beta"),
                                     ("", {records[2].id}, "Sem projeto"),
                                     (None, {r.id for r in records}, "Todos os projetos")]:
        window.projects.open_project(project)
        window.sidebar.buttons["history"].click()
        assert page.project_filter == project
        assert window.topbar.context.text() == label
        assert visible_ids(page) == expected
        assert page.search.text() == "Bell"
        assert page.status_filter.currentData() == "ok"
    assert len(page.records) == 3


def test_all_projects_choice_and_row_selection_survive_reopening_history(window, source_record):
    records = history_records(window, source_record)
    window.projects.open_project("Alpha")
    # Um caminho explícito para o projeto pode abrir o Histórico antes do menu.
    window._show_project_history("Alpha")
    page = window.page_history
    page.clear_project_filter.click()
    assert page.project_filter is None
    assert window.topbar.context.text() == "Todos os projetos"
    page.search.setText("Bell")
    page.status_filter.setCurrentIndex(page.status_filter.findData("ok"))
    chosen_row = next(row for row in range(page.table.rowCount())
                      if page.table.item(row, 0).data(Qt.UserRole) == records[1].id)
    page.table.selectRow(chosen_row)
    selected = [page.table.item(index.row(), 0).data(Qt.UserRole)
                for index in page.table.selectionModel().selectedRows()]
    window.sidebar.buttons["docs"].click()
    window.sidebar.buttons["history"].click()
    assert page.project_filter is None
    assert window.topbar.context.text() == "Todos os projetos"
    assert page.search.text() == "Bell"
    assert page.status_filter.currentData() == "ok"
    assert [page.table.item(index.row(), 0).data(Qt.UserRole)
            for index in page.table.selectionModel().selectedRows()] == selected
    assert visible_ids(page) == {r.id for r in records}

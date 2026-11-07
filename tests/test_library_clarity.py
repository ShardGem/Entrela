"""O caderno e as configurações pessoais têm fontes e ações distintas."""
from dataclasses import asdict, replace
import json

import pytest
from PySide6.QtWidgets import QMessageBox

from core.circuit_document import CircuitDocument, CircuitGate
from core.examples import create_example_config
from data.workspace import WorkspaceLibrary
from gui.controllers.appearance import apply_appearance
from gui.pages.library import LibraryPage


@pytest.mark.parametrize("section,key,value", [
    ("annotations", "execucao", 42),
    ("annotations", "execucao", {"notes": []}),
    ("annotations", "execucao", {"tags": "Bell"}),
    ("annotations", "execucao", {"categories": [1]}),
    ("projects", "TCC", []),
    ("projects", "TCC", {"description": None}),
    ("templates", "Referencia", {"system": {}}),
])
def test_invalid_library_entries_are_rejected_without_rewriting_file(tmp_path, section, key, value):
    library = WorkspaceLibrary(tmp_path)
    raw = {"version": 1, "templates": {}, "projects": {}, "annotations": {}}
    raw[section][key] = value
    library.path.write_text(json.dumps(raw), encoding="utf-8")
    before = library.path.read_bytes()
    with pytest.raises(ValueError, match="preservado"):
        library.read()
    with pytest.raises(ValueError, match="preservado"):
        library.save_template("Novo", create_example_config("bell"))
    assert library.path.read_bytes() == before


def test_personal_form_configuration_rejects_gate_circuits(tmp_path):
    library = WorkspaceLibrary(tmp_path)
    base = create_example_config("bell")
    config = replace(base, protocol=replace(base.protocol, total_time=1, trotter_steps=1),
                     circuit=CircuitDocument(2, (CircuitGate("h", (0,)),)))
    with pytest.raises(ValueError, match="biblioteca do editor"):
        library.save_template("Circuito", config)
    assert not library.path.exists()
    raw = {"version": 1, "templates": {"Circuito": asdict(config)}, "projects": {}, "annotations": {}}
    library.path.write_text(json.dumps(raw), encoding="utf-8")
    before = library.path.read_bytes()
    with pytest.raises(ValueError, match="circuito de portas"):
        library.template("Circuito")
    assert library.path.read_bytes() == before


def test_form_configuration_and_notebook_remain_separate(tmp_path, qt_app):
    library = WorkspaceLibrary(tmp_path)
    config = create_example_config("thermal-ising")
    library.save_template("Térmico", config)
    library.annotate("execucao", "TCC", "Observação", ["controle"], title="Ruído de referência",
                     objective="Medir perda de pureza", hypothesis="A pureza cai")
    data = library.read()
    page = LibraryPage()
    try:
        page.load(data, "execucao")
        assert page.run_title.text() == "Ruído de referência"
        assert page.objective.toPlainText() == "Medir perda de pureza"
        page.show_configurations()
        assert "formulário de simulação" in page.context.text()
        assert "Ruído de referência" not in page.context.text()
        page.name.setText("Outra configuração")
        assert page.annotation_payload()["hypothesis"] == "A pureza cai"
        page.show_notebook()
        assert "Ruído de referência" in page.context.text()
        assert library.template("Térmico") == config
        assert data["annotations"]["execucao"]["notes"] == "Observação"
    finally:
        page.close()


def test_configuration_overwrite_requires_confirmation_and_load_never_executes(qt_app, monkeypatch):
    page = LibraryPage()
    requested = []
    loaded = []
    page.template_save_requested.connect(requested.append)
    page.template_load_requested.connect(loaded.append)
    page.load({"templates": {"Referencia": {}}, "annotations": {}})
    try:
        assert not page.save_template.isEnabled()
        page.name.setText(" Referencia ")
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
        page.request_template_save(" Referencia ")
        assert requested == []
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
        page.save_template.click()
        assert requested == ["Referencia"]
        page.name.setText("Nova")
        page.save_template.click()
        assert requested == ["Referencia", "Nova"]
        page.load_template.click()
        assert loaded == ["Referencia"]
        # Signals only request the existing handlers. No simulation occurs here.
        assert not page.annotation_group.isEnabled()
        page.load({"templates": {}, "annotations": {}})
        assert not page.load_template.isEnabled()
        assert not page.delete_template.isEnabled()
    finally:
        page.close()


def test_project_history_and_navigation_keep_selected_notebook(qt_app):
    page = LibraryPage()
    navigation, projects = [], []
    page.navigation_requested.connect(navigation.append)
    page.project_history_requested.connect(projects.append)
    page.load({"templates": {}, "annotations": {"run": {"title": "Controle", "project": "TCC"}}}, "run")
    try:
        page.project_history.click()
        assert projects == ["TCC"]
        page.select_execution.click()
        page.open_circuits.click()
        assert navigation == ["history", "circuit"]
        assert page.identifier == "run"
        assert page.run_title.text() == "Controle"
    finally:
        page.close()


def test_unreadable_library_cannot_save_a_stale_notebook(qt_app):
    page = LibraryPage()
    raw = {"templates": {}, "annotations": {"run": {"title": "Controle"}}}
    try:
        page.load(raw, "run")
        page.set_unavailable("Caderno inválido; arquivo preservado.")
        assert page.identifier is None
        assert not page.annotation_group.isEnabled()
        assert not page.templates_group.isEnabled()
        assert "preservado" in page.message.text()
        page.load(raw, "run")
        assert page.annotation_group.isEnabled()
        assert page.templates_group.isEnabled()
    finally:
        page.close()


@pytest.mark.parametrize("font_size", [15,24])
def test_notebook_and_form_configuration_tabs_fit_small_window(qt_app, font_size):
    page = LibraryPage()
    try:
        apply_appearance(page, "dark", font_size)
        page.resize(760, 660)
        page.show()
        for section in (page.annotation_group, page.templates_group):
            page.tabs.setCurrentWidget(section)
            for _ in range(4):
                qt_app.processEvents()
            assert page._scroll.horizontalScrollBar().maximum() == 0
    finally:
        apply_appearance(page)
        page.close()

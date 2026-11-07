"""O laboratório reutiliza páginas e solicita ações sem criar dados científicos."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from gui.controllers.appearance import apply_appearance
from gui.pages.experiment_workspace import ExperimentWorkspace


def create_pages():
    pages, fields = {}, {}
    for key, _, _ in ExperimentWorkspace.TABS:
        page = QWidget()
        field = QLineEdit(key + " · rascunho")
        QVBoxLayout(page).addWidget(field)
        pages[key], fields[key] = page, field
    return pages, fields


def test_tabs_use_the_existing_widgets_and_keep_edits(qt_app):
    pages, fields = create_pages()
    workspace = ExperimentWorkspace(pages)
    selected = QSignalSpy(workspace.page_selected)
    try:
        for index, (key, _, _) in enumerate(workspace.TABS):
            workspace.select_page(key)
            assert workspace.tabs.currentWidget() is pages[key]
            assert fields[key].text() == key + " · rascunho"
            assert workspace.current_page_key == key
            assert workspace.tabs.tabToolTip(index)
        assert selected.count() == 0
        workspace.tabs.setCurrentIndex(1)
        assert selected.count() == 1 and selected.at(0) == ["circuit"]
        with pytest.raises(ValueError, match="fora do laboratório"):
            workspace.select_page("settings")
    finally:
        workspace.close()


def test_menus_request_ids_and_render_names_literally(qt_app):
    pages, _ = create_pages()
    workspace = ExperimentWorkspace(pages)
    template = QSignalSpy(workspace.template_requested)
    recent = QSignalSpy(workspace.recent_requested)
    try:
        assert not workspace.templates_menu.actions()[0].isEnabled()
        assert not workspace.recent_menu.actions()[0].isEnabled()
        name = "Bell & ruído < 0,1"
        workspace.set_templates([{"id": "config-id", "name": name}])
        workspace.set_recent([("run-id", name)])
        action = workspace.templates_menu.actions()[0]
        assert action.text().replace("&&", "&") == name
        assert "config-id" not in action.text()
        action.trigger()
        workspace.recent_menu.actions()[0].trigger()
        assert template.count() == 1 and template.at(0) == ["config-id"]
        assert recent.count() == 1 and recent.at(0) == ["run-id"]
        assert workspace.current_page_key == "simulation"
        workspace.set_templates([{"id": "new-config", "name": "Outra configuração"}])
        workspace.templates_menu.actions()[0].trigger()
        assert template.at(1) == ["new-config"]
    finally:
        workspace.close()


def test_running_preserves_navigation_and_blocks_replacing_context(qt_app):
    pages, fields = create_pages()
    workspace = ExperimentWorkspace(pages)
    try:
        workspace.set_running(True)
        workspace.set_templates([{"id": "config", "name": "Configuração"}])
        workspace.set_recent([("run", "Execução")])
        assert not workspace.templates_button.isEnabled()
        assert not workspace.recent_button.isEnabled()
        assert workspace.tabs.isEnabled()
        workspace.select_page("results")
        assert workspace.tabs.currentWidget() is pages["results"]
        assert fields["simulation"].text() == "simulation · rascunho"
        workspace.set_running(False)
        assert workspace.templates_button.isEnabled() and workspace.recent_button.isEnabled()
    finally:
        workspace.close()


def test_selected_execution_is_a_received_context_and_not_the_draft(qt_app):
    pages, fields = create_pages()
    workspace = ExperimentWorkspace(pages)
    try:
        title = "Bell & ruído < 0,1"
        workspace.set_selected_experiment(title, "circuit")
        assert title in workspace.selected_label.text()
        assert "Circuito de portas" in workspace.selected_label.text()
        assert "rascunhos independentes" in workspace.selected_label.toolTip()
        assert workspace.selected_label.textFormat() == Qt.PlainText
        for key in workspace.KEYS:
            workspace.select_page(key)
            assert fields[key].text() == key + " · rascunho"
            assert title in workspace.selected_label.text()
        workspace.set_selected_experiment(None, None)
        assert workspace.selected_label.text() == "Nenhuma execução selecionada"
    finally:
        workspace.close()


@pytest.mark.parametrize("font_size", [15, 24])
def test_toolbar_stays_inside_a_narrow_workspace(qt_app, font_size):
    pages, _ = create_pages()
    workspace = ExperimentWorkspace(pages)
    try:
        apply_appearance(workspace, "dark", font_size)
        workspace.resize(600, 420)
        workspace.show()
        for _ in range(4):
            qt_app.processEvents()
        for button in (workspace.templates_button, workspace.recent_button):
            assert workspace.toolbar.rect().contains(button.geometry())
        assert not workspace.templates_button.geometry().intersects(workspace.recent_button.geometry())
        assert workspace.tabs.currentWidget() is pages["simulation"]
    finally:
        apply_appearance(workspace)
        workspace.close()

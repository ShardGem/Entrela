"""A flat notebook preserves scientific drafts and independent form templates."""
from dataclasses import replace
import pytest
from core.examples import create_example_config
from core.simulation import run_experiment
from gui.main_window import MainWindow
from gui.controllers.appearance import apply_appearance
from PySide6.QtWidgets import QTabWidget


def test_notebook_sections_do_not_add_nested_tabs_or_change_payload(window):
    page = window.page_library
    assert len(page.annotation_group.findChildren(QTabWidget)) == 0
    record = run_experiment(replace(create_example_config('bell'), shots=16))
    window.repository.save(record)
    before = window.repository._path(record.id).read_bytes()
    window._current_experiment = record
    window._display_experiment(record)
    page.notes.setPlainText('Observação em elaboração')
    page.hypothesis.setPlainText('Hipótese preservada')
    payload = page.draft_payload()
    page.sections['planning'].set_expanded(True, animate=False)
    page.sections['notes'].set_expanded(False, animate=False)
    page.show_configurations()
    page.name.setText('Parâmetros independentes')
    page.show_notebook()
    assert page.draft_payload() == payload
    window._refresh_library()
    assert page.notes.toPlainText() == 'Observação em elaboração'
    assert window.close()
    reopened = MainWindow(window.repository, window.settings)
    try:
        reopened._open_experiment(record.id)
        assert reopened.page_library.hypothesis.toPlainText() == 'Hipótese preservada'
        assert reopened.page_library.notes.toPlainText() == 'Observação em elaboração'
        assert reopened.page_library.sections['planning'].is_expanded
        assert not reopened.page_library.sections['notes'].is_expanded
        assert reopened.page_library.name.text() == 'Parâmetros independentes'
        assert window.repository._path(record.id).read_bytes() == before
    finally:
        reopened.close()


@pytest.mark.parametrize('font_size', [15, 24])
def test_notebook_save_stays_accessible_at_small_resolution(window, qt_app, font_size):
    page = window.page_library
    window._show_page('library')
    apply_appearance(window, 'dark', font_size)
    window.resize(1024, 768)
    for section in page.sections.values():
        section.set_expanded(True, animate=False)
    for _ in range(4):
        qt_app.processEvents()
    assert page.save_annotation.isVisible()
    center = page.save_annotation.mapTo(window, page.save_annotation.rect().center())
    assert 0 <= center.y() < window.height()
    assert not page.save_annotation.isEnabled()
    assert page._scroll.horizontalScrollBar().maximum() == 0
    page.show_configurations()
    assert window.configuration_dialog.isVisible()
    assert page.templates_group.isVisible()
    assert window.configuration_dialog.isAncestorOf(page.templates_group)
    window.configuration_dialog.close()

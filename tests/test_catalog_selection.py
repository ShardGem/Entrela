from dataclasses import asdict, replace

from PySide6.QtCore import Qt

from core.examples import create_example_config


def test_refresh_keeps_selected_template_and_emits_its_name(window):
    page = window.page_catalog
    cfg = create_example_config('bell')
    raw = {'templates': {'Primeiro': asdict(cfg), 'Ruído e precisão': asdict(cfg)}}
    page.refresh(raw)
    page.entries.setCurrentRow(1)
    selected = []
    page.template_requested.connect(selected.append)
    # A background refresh may include an updated configuration for the same model.
    raw['templates']['Ruído e precisão'] = asdict(replace(cfg, shots=512))
    page.refresh(raw)
    assert page.entries.currentItem().data(Qt.UserRole)[1] == 'Ruído e precisão'
    assert '512 shots' in page.description.text()
    page.copy.click()
    assert selected == ['Ruído e precisão']
    page.search.setText('precisao RUIDO')
    assert page.entries.count() == 1
    assert page.entries.currentItem().data(Qt.UserRole)[1] == 'Ruído e precisão'
    page.search.setText('não existe')
    assert page.entries.count() == 0
    assert not page.copy.isEnabled()


def test_refresh_keeps_exact_circuit_revision_after_new_revision(window):
    page = window.page_catalog
    library = page.editor.library
    document = page.editor.document
    first = library.save('Fase e ruído', document, 'Análise de precisão')
    second = library.save('Fase e ruído', document, identifier=first.identifier)
    page.refresh({'templates': {}})
    # Revisions are newest first; deliberately select the earlier revision.
    page.entries.setCurrentRow(1)
    copied = []
    page.circuit_requested.connect(copied.append)
    library.save('Nome atualizado', document, identifier=first.identifier)
    page.refresh({'templates': {}})
    revision = page.entries.currentItem().data(Qt.UserRole)[2]
    assert revision.identifier == first.identifier and revision.version == 1
    page.copy.click()
    assert copied[0].version == 1
    page.search.setText('precisao ruido')
    assert page.entries.count() == 1
    assert page.entries.currentItem().data(Qt.UserRole)[2].version == 1

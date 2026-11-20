"""Regressions for the project-centered desktop and immutable execution context."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from data.workspace import WorkspaceLibrary
from data.projects import ProjectStore
from core.examples import create_example_config
from core.simulation import run_experiment
from tests.qt_helpers import wait_until


def test_additive_projects_keep_legacy_links_and_unknown_metadata(tmp_path):
    library = WorkspaceLibrary(tmp_path)
    library.annotate('legacy-run', 'Ruído', 'Nota preservada', ['TCC'], title='Execução original')
    with library.transaction() as raw:
        raw['annotations']['legacy-run']['custom_metadata'] = {'retained': True}
    store = ProjectStore(library)
    work = store.create_work('Novo estudo', 'Ruído', 'hamiltonian', {'simulation': {'name': 'Rascunho'}})
    store.link_execution(work['id'], 'new-run')
    store.save_draft(work['id'], {'simulation': {'controls': {'t1': 70, 't2': 180}}}, 'Nome editado')
    raw = store.read()
    assert raw['annotations']['legacy-run']['notes'] == 'Nota preservada'
    assert raw['annotations']['legacy-run']['custom_metadata']['retained']
    assert raw['annotations']['new-run']['project'] == 'Ruído'
    assert store.work_for_execution('new-run')['title'] == 'Nome editado'
    assert store.works('Ruído')[0]['draft']['simulation']['controls']['t2'] == 180
    assert store.works('outro') == []
    assert [p['name'] for p in store.projects()] == ['Ruído']


def test_duplicate_project_is_explicit_and_keeps_data(tmp_path):
    store = ProjectStore(WorkspaceLibrary(tmp_path))
    store.create_project('Ising', 'Primeira descrição')
    with pytest.raises(ValueError, match='Já existe'):
        store.create_project('Ising', 'Não substituir')
    assert store.projects()[0]['description'] == 'Primeira descrição'


def test_thermal_validation_clears_every_surface_and_shortcut(window, monkeypatch):
    page = window.page_simulation
    panel = page.config_panel
    panel.check_ruido.setChecked(True)
    panel.combo_modelo.setCurrentIndex(1)
    panel.spin_t1.setValue(70); panel.spin_t2.setValue(180)
    started = []
    monkeypatch.setattr(window, '_start_worker', lambda *args: started.append(args))
    window._show_page('simulation')
    window._run_active_context()
    assert not started
    assert not page.btn_run.isEnabled()
    assert '140' in panel.validation_message.text()
    assert '140' in page.configuration_feedback.text()
    assert '140' in page.status._text.text()
    assert panel.section_buttons['noise'].property('invalid')
    panel.btn_fix_t2.click()
    assert panel.spin_t2.value() == 140
    assert panel.validation_message.isHidden()
    assert page.configuration_feedback.isHidden()
    assert page.status.state == 'idle'
    assert page.btn_run.isEnabled()
    assert not panel.section_buttons['noise'].property('invalid')
    assert page.validate_configuration().noise.t2_us == 140
    window._run_active_context()
    assert len(started) == 1


def test_switch_work_preserves_both_kinds_and_invalid_controls(window):
    window.projects.project = 'Primeiro'
    assert window.projects.create_work('hamiltonian', 'Rascunho térmico')
    first = window.projects.active_id
    panel = window.page_simulation.config_panel
    panel.check_ruido.setChecked(True); panel.combo_modelo.setCurrentIndex(1)
    panel.spin_t1.setValue(70); panel.spin_t2.setValue(180)
    window.page_simulation.experiment_description.setText('Ainda investigando os tempos')
    window.projects.project = 'Segundo'
    assert window.projects.create_work('circuit', 'Circuito independente')
    second = window.projects.active_id
    window.page_circuit.editor.circuit_name.setText('Circuito renomeado')
    window.projects.open_work(first)
    assert window.projects.project == 'Primeiro'
    assert panel.spin_t2.value() == 180
    assert not window.page_simulation.btn_run.isEnabled()
    assert window.page_simulation.experiment_description.text() == 'Ainda investigando os tempos'
    window.projects.open_work(second)
    assert window.page_circuit.editor.circuit_name.text() == 'Circuito renomeado'
    assert window.projects.project == 'Segundo'


def test_history_consult_does_not_replace_draft(window):
    window.projects.create_work('hamiltonian', 'Configuração em edição')
    panel = window.page_simulation.config_panel
    panel.spin_J.setValue(.321)
    record = run_experiment(replace(create_example_config('bell'), shots=32))
    window.repository.save(record)
    window._refresh_history()
    window._open_experiment(record.id)
    assert window._current_experiment.id == record.id
    assert panel.spin_J.value() == .321
    assert window.page_simulation.experiment_name.text() == 'Configuração em edição'
    assert window.is_page_active('results')


def test_completion_in_other_project_keeps_context_and_opens_exact_record(window):
    window.projects.project = 'Origem'
    window._load_example('bell')
    owner = window.projects.active_id
    window.page_simulation.config_panel.spin_shots.setValue(32)
    window._run_simulation()
    assert window._current_worker is not None
    launched = window.projects.launch['config']
    window.projects.open_project('Outra investigação')
    window.projects.create_work('hamiltonian', 'Outro rascunho')
    active = window.projects.active_id
    window.page_simulation.config_panel.spin_J.setValue(.246)
    wait_until(lambda: window._current_worker is None and window._storage_worker is None)
    assert window.projects.active_id == active
    assert window.projects.project == 'Outra investigação'
    assert window._current_experiment is None
    records = window.repository.list_all()
    assert len(records) == 1 and records[0].config == launched
    record = records[0]
    raw = window.projects.store.read()
    assert raw['annotations'][record.id]['project'] == 'Origem'
    assert raw['annotations'][record.id]['workbench_id'] == owner
    assert record.result.metadata['example_id'] == 'bell'
    assert window.job_monitor._completed_id == record.id
    window.job_monitor.open_result.click()
    assert window._current_experiment.id == record.id
    assert window.page_simulation.config_panel.spin_J.value() == .246


def test_failed_draft_write_aborts_switch_and_preserves_recovery(window, monkeypatch):
    window.projects.create_work('hamiltonian', 'Não perder')
    owner = window.projects.active_id
    original = window.drafts.store.path.read_bytes()
    def fail(*args): raise OSError('Disco indisponível')
    original_write = window.projects.store.library._write
    with monkeypatch.context() as context:
        context.setattr(window.projects.store.library, '_write', fail)
        window.projects.open_project('Outro projeto')
    assert window.projects.active_id == owner
    assert window.projects.project != 'Outro projeto'
    assert 'Não foi possível salvar' in window.statusBar().currentMessage()
    assert window.drafts.store.path.exists() and original
    monkeypatch.setattr(window.projects.store.library, '_write', original_write)


def test_sidebar_results_remain_discoverable_before_an_experiment(window):
    window.sidebar.buttons['simulation'].click()
    assert window.page_workspace.toolbar.isHidden()
    window.sidebar.buttons['results'].click()
    assert window.is_page_active('results')
    assert window.page_results.empty.isVisible()
    assert window.page_workspace.recent_button.isVisible()
    assert window.sidebar.buttons['results'].isChecked()


def test_blue_default_and_existing_profile_priority(window):
    assert window.page_settings.theme.currentData() == 'navy'
    window.settings.setValue('appearance/theme', 'dark')
    window._restore_preferences()
    assert window.page_settings.theme.currentData() == 'dark'


def test_observation_switch_keeps_selected_snapshot(window):
    record = run_experiment(replace(create_example_config('bell'), shots=32))
    window.repository.save(record)
    window._refresh_history()
    window.projects.results[record.id] = record
    window.projects.show_execution(record.id)
    window.page_bloch.slider.setValue(2)
    workspace = window.page_workspace
    window.sidebar.buttons['bloch'].click()
    assert window.is_page_active('bloch')
    assert workspace.observation_tabs.isHidden()
    window.sidebar.buttons['results'].click()
    workspace.observation_tabs.setCurrentIndex(1)
    assert window.is_page_active('results')
    assert window.page_results.results_tab.chart_views.currentIndex() == 1
    assert window.page_bloch.slider.value() == 2
    workspace.observation_tabs.setCurrentIndex(2)
    assert window.page_results.tabs.currentWidget() is window.page_results.state_inspector
    assert window.page_bloch.slider.value() == 2


def test_report_composer_reuses_existing_options_and_sources(window):
    record = run_experiment(replace(create_example_config('bell'), shots=32))
    window.repository.save(record)
    window._refresh_history()
    window.projects.results[record.id] = record
    window.projects.show_execution(record.id)
    window._open_export_dialog('pdf')
    assert window.stack.currentWidget() is window.page_notebook
    assert window.page_notebook.tabs.currentWidget() is window.page_notebook.report_workspace
    assert [source.id for source in window._documentation_sources()] == [record.id]
    assert window._experiment_name(record) in window.page_documentation.dialog_context.text()
    assert window.page_documentation.report_options()['include_distribution']


def test_new_work_clears_all_source_views(window):
    record = run_experiment(replace(create_example_config('bell'), shots=32))
    window.repository.save(record); window._refresh_history()
    window.projects.show_execution(record.id)
    assert window.page_bloch.original_svs
    window.projects.create_work('hamiltonian', 'Sem resultados')
    assert window._current_experiment is None
    assert window.page_bloch.original_svs == []
    assert window.page_circuit.editor.evidence.experiment is None
    assert window.page_analysis.experiment is None
    assert not window.page_mitigation.has_experiment
    assert not window.page_results._available


def test_study_finishes_with_its_source_after_consulting_another_record(window):
    first = run_experiment(replace(create_example_config('bell'), shots=32))
    second = run_experiment(replace(create_example_config('bell'), shots=48, seed=43))
    for record in (first, second): window.repository.save(record)
    window._refresh_history(); window.projects.show_execution(first.id)
    window._run_analysis('temporal', {})
    window.projects.show_execution(second.id)
    wait_until(lambda: window._current_worker is None)
    assert window._current_experiment.id == second.id
    assert window.page_analysis.experiment.id == second.id
    assert window.page_analysis.data is None
    assert window.projects.completed_studies[first.id]['source_id'] == first.id
    window.job_monitor.open_result.click()
    assert window._current_experiment.id == first.id
    assert window.page_analysis.data['source_id'] == first.id


def test_unsaved_background_execution_is_protected_before_close(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    record = run_experiment(replace(create_example_config('bell'), shots=32))
    window.projects.results[record.id] = record
    window.projects.unsaved_runs[record.id] = record
    window._current_experiment = None
    window._unsaved_result = False
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.Cancel)
    assert not window._confirm_unsaved()
    assert record.id in window.projects.unsaved_runs
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.Save)
    assert window._confirm_unsaved()
    assert not window.projects.unsaved_runs
    assert window.repository.load(record.id).result.counts == record.result.counts


def test_export_registry_uses_worker_sources_and_file_integrity(window, tmp_path):
    from hashlib import sha256
    a = run_experiment(replace(create_example_config('bell'), shots=16))
    b = run_experiment(replace(create_example_config('bell'), shots=24, seed=43))
    for record in (a, b): window.repository.save(record)
    window._refresh_history(); window.projects.show_execution(a.id)
    output = tmp_path / 'relatorio.pdf'
    window._start_documentation_export([a], str(output), 'pdf')
    window.projects.show_execution(b.id)
    wait_until(lambda: window._current_worker is None)
    entries = window.projects.store.artifacts([a.id])
    assert len(entries) == 1 and entries[0]['source_ids'] == [a.id]
    assert entries[0]['sha256'] == sha256(output.read_bytes()).hexdigest()
    assert not window.projects.store.artifacts([b.id])
    assert window._current_experiment.id == b.id


def test_project_draft_validation_preserves_corrupt_source(tmp_path):
    import json
    library = WorkspaceLibrary(tmp_path)
    store = ProjectStore(library)
    work = store.create_work('Rascunho íntegro', '', 'hamiltonian', {'simulation': {'controls': {'J': 1.}}})
    raw = library.read()
    raw['workbench'][work['id']]['draft']['simulation']['controls']['J'] = 'inválido'
    library.path.write_text(json.dumps(raw), encoding='utf-8')
    before = library.path.read_bytes()
    with pytest.raises(ValueError, match='numérico'):
        store.read()
    assert library.path.read_bytes() == before


def test_unexecuted_protocol_follows_its_work_and_the_execution(window):
    window.projects.create_work('hamiltonian', 'Primeira investigação')
    first = window.projects.active_id
    protocol = window.page_analysis.protocol
    protocol.fields['question'].setText('Como evolui a coerência?')
    window.projects.create_work('hamiltonian', 'Segunda investigação')
    second = window.projects.active_id
    protocol.fields['question'].setText('Como o ruído afeta a pureza?')
    window.projects.open_work(first)
    assert protocol.fields['question'].text() == 'Como evolui a coerência?'
    window.page_simulation.config_panel.spin_shots.setValue(16)
    window._run_simulation()
    wait_until(lambda: window._current_worker is None)
    record = window._current_experiment
    assert window.drafts.source == record.id
    assert protocol.fields['question'].text() == 'Como evolui a coerência?'
    window.projects.open_work(second)
    assert protocol.fields['question'].text() == 'Como o ruído afeta a pureza?'

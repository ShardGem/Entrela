from dataclasses import replace
from threading import Event
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox,QFileDialog
from gui.main_window import MainWindow
from core.examples import EXAMPLES,create_example_config
from core.export import export_experiment_json
from core.simulation import run_experiment,SimulationCancelled
from core.types import *
from data.repository import ExperimentRepository
from tests.qt_helpers import execute,wait_until

@pytest.mark.parametrize("noisy,snapshots",[(False,False),(True,False),(False,True),(True,True)])
def test_complete_ui_pipeline(window,noisy,snapshots):
    p=window.page_simulation.config_panel
    p.spin_shots.setValue(128)
    p.check_ruido.setChecked(noisy)
    p.check_snaps.setChecked(snapshots)
    exp=execute(window)
    assert sum(exp.result.counts.values())==128
    assert window.page_history.table.rowCount()==1
    assert window.page_dashboard.card_sims._value.text()=="1"
    assert window.page_results.card_pur._value.text()!="—"
    bars=window.page_results.results_tab.canvas_hist.fig.axes[0].patches
    assert sum(bar.get_height() for bar in bars)==128
    assert len(window.page_bloch.precomputed_bloch)==(5 if snapshots else 0)
    np.testing.assert_allclose(window.repository.load(exp.id).result.final_state.data,exp.result.final_state.data)
def test_modes_share_widgets_and_values(window):
    p=window.page_simulation.config_panel
    p.load_config(create_example_config("thermal-ising"))
    before=p.get_config()
    field=p.spin_t1
    for mode in ("advanced","guided","advanced","guided"):
        p.set_mode(mode)
        assert p.get_config()==before
        assert p.spin_t1 is field
    for key in p.sections:p.set_section(key)
    assert p.get_config()==before
def test_thermal_validation_and_explicit_fix(window):
    p=window.page_simulation.config_panel
    p.combo_modelo.setCurrentIndex(1)
    p.spin_t1.setValue(70)
    p.spin_t2.setValue(180)
    window._run_simulation()
    assert window._current_worker is None
    assert "140" in p.validation_message.text()
    p.btn_fix_t2.click()
    assert p.spin_t2.value()==140
    p.get_config().validate()
def test_example_copy_and_search(window):
    gallery=window.page_examples
    gallery.search.setText("bell")
    assert gallery.list.count()==2
    gallery.select_example("bell")
    gallery.btn_try.click()
    p=window.page_simulation.config_panel
    assert p.get_config()==create_example_config("bell")
    p.spin_J.setValue(2)
    assert create_example_config("bell").system.J==0
def test_draft_and_mode_survive_restart(window,qt_app):
    p=window.page_simulation.config_panel
    p.load_config(create_example_config("xy"))
    p.set_mode("advanced")
    expected=p.get_config()
    settings=window.settings
    repo=window.repository
    window.close()
    other=MainWindow(repo,settings)
    try:
        assert other.page_simulation.config_panel.get_config()==expected
        assert other.page_simulation.config_panel.current_mode=="advanced"
    finally:other.close()
def test_actual_tutorial_requires_actions_and_real_reopen(window):
    window._begin_tutorial()
    t=window.tutorial
    p=window.page_simulation.config_panel
    assert t.step==0 and not t.btn_next.isEnabled()
    t.advance()
    assert t.step==0
    p.spin_qubits.setValue(2)
    t.advance()
    assert t.step==1
    p.combo_initial.setCurrentIndex(p.combo_initial.findData("bell"))
    t.advance()
    p.check_ruido.setChecked(False)
    t.advance()
    p.check_snaps.setChecked(True)
    t.advance()
    assert t.step==4 and not t.ready()
    exp=execute(window)
    assert t.run_id==exp.id
    t.advance()
    assert t.step==5 and not t.ready()
    window._show_page("results")
    assert t.ready()
    t.advance()
    assert t.step==6 and not t.ready()
    window._open_experiment(exp.id)
    assert t.ready()
    t.advance()
    assert not t.active
    assert window.settings.value("tutorial/bell/completed",False,type=bool)
def test_tutorial_resume_and_completed_restart_are_separate(window):
    window.settings.setValue("tutorial/bell/step",3)
    window._begin_tutorial()
    assert window.tutorial.step==3
    assert window.page_simulation.config_panel.combo_initial.currentData()=="bell"
    window.tutorial.pause()
    window._begin_tutorial()
    assert window.tutorial.step==3
def test_gallery_replacement_requires_confirmation(window,monkeypatch):
    window.page_simulation.config_panel.spin_J.setValue(2.5)
    original=window.page_simulation.config_panel.get_config()
    monkeypatch.setattr(QMessageBox,"question",lambda *args:QMessageBox.No)
    window._load_example("bell")
    assert window.page_simulation.config_panel.get_config()==original
def test_reopen_preserves_original_when_form_edited(window):
    p=window.page_simulation.config_panel
    p.spin_shots.setValue(64)
    exp=execute(window)
    p.spin_J.setValue(2)
    window.page_results.btn_save.click()
    assert window.repository.load(exp.id).config==exp.config
def test_save_failure_keeps_result_and_retry(window,monkeypatch):
    actual=window.repository.save
    def fail(*args):raise OSError("disk full")
    monkeypatch.setattr(window.repository,"save",fail)
    window.page_simulation.config_panel.spin_shots.setValue(64)
    exp=execute(window)
    assert window._unsaved_result and exp.result.counts
    monkeypatch.setattr(window.repository,"save",actual)
    window.page_results.btn_save.click()
    assert not window._unsaved_result
def test_close_unsaved_requires_discard(window,monkeypatch):
    def fail(*args):raise OSError("disk full")
    monkeypatch.setattr(window.repository,"save",fail)
    window.page_simulation.config_panel.spin_shots.setValue(64)
    execute(window)
    monkeypatch.setattr(QMessageBox,"warning",lambda *args:QMessageBox.Cancel)
    assert window.close() is False
    monkeypatch.setattr(QMessageBox,"warning",lambda *args:QMessageBox.Discard)
    assert window.close() is True
def test_no_parallel_submissions_and_close_waits_for_worker(window,monkeypatch):
    entered,release=Event(),Event()
    def paused(config,progress,is_cancelled):
        entered.set()
        release.wait(5)
        assert is_cancelled()
        raise SimulationCancelled()
    monkeypatch.setattr("gui.workers.simulation_worker.run_experiment",paused)
    window.page_simulation.btn_run.click()
    worker=window._current_worker
    try:
        wait_until(entered.is_set)
        window._run_simulation()
        assert window._current_worker is worker
        assert window.close() is False
        assert window.isVisible()
    finally:
        release.set()
        wait_until(lambda:window._current_worker is None and not window.isVisible())
    assert window.repository.list_all()==[]
def test_zne_is_independent_record(window):
    window.page_simulation.config_panel.load_config(replace(create_example_config("depolarizing-bell"),shots=128))
    original=execute(window)
    before=window.repository._path(original.id).read_bytes()
    window.page_mitigation.shots.setValue(256)
    window.page_mitigation.btn_run.click()
    wait_until(lambda:window._current_worker is None)
    derived=window._current_experiment
    assert derived.id!=original.id
    assert derived.result.mitigation["scale_factors"]==[1,3,5]
    assert derived.result.counts==original.result.counts
    assert derived.result.fidelity==original.result.fidelity
    assert window.repository._path(original.id).read_bytes()==before
    window._open_experiment(derived.id)
    assert window.page_mitigation.table.rowCount()==3
def test_comparison_rejects_incompatible_and_normalizes(window):
    a=run_experiment(replace(create_example_config("bell"),shots=64))
    b=run_experiment(replace(create_example_config("depolarizing-bell"),shots=128))
    c=run_experiment(replace(create_example_config("first-qubit"),shots=64))
    page=window.page_comparison
    page.load([a,b,c])
    page.set_runs(a.id,b.id)
    assert page.metrics_table.rowCount()==3
    bars=page.canvas.fig.axes[0].patches
    assert sum(bar.get_height() for bar in bars)==pytest.approx(2)
    page.set_runs(a.id,c.id)
    assert page.metrics_table.rowCount()==0
    assert "Sistemas diferentes" in page.message.text()
def test_import_creates_independent_record(window,monkeypatch,tmp_path):
    source=run_experiment(replace(create_example_config("bell"),shots=64))
    path=export_experiment_json(source,tmp_path/"run.json")
    monkeypatch.setattr(QFileDialog,"getOpenFileName",lambda *args:(str(path),"JSON"))
    window._import_experiment()
    imported=window._current_experiment
    assert imported.id!=source.id
    assert imported.result.metadata["imported_from_id"]==source.id
    assert window.repository.load(imported.id).config==source.config
def test_command_palette_search_and_action(window):
    window._open_commands()
    palette=window.command_palette
    palette.search.setText("fidelidade")
    assert palette.list.count()==1
    palette._activate()
    assert window.help_dock.isVisible()
    assert window._current_page=="dashboard"
def test_history_search_filters_records(window):
    exp=run_experiment(replace(create_example_config("bell"),shots=64))
    window.repository.save(exp)
    window._refresh_history()
    window.page_history.search.setText("not-found")
    assert window.page_history.table.rowCount()==0
    window.page_history.search.setText(exp.id)
    assert window.page_history.table.rowCount()==1

def test_unopened_tutorial_does_not_erase_saved_progress(window):
    window.settings.setValue("tutorial/bell/step",3)
    window.settings.setValue("tutorial/bell/run_id","previous")
    window.close()
    assert int(window.settings.value("tutorial/bell/step"))==3
    assert window.settings.value("tutorial/bell/run_id")=="previous"

def test_completed_tutorial_restarts_without_reusing_old_run(window):
    exp=run_experiment(replace(create_example_config("bell"),shots=64))
    window.repository.save(exp)
    window.settings.setValue("tutorial/bell/completed",True)
    window.settings.setValue("tutorial/bell/step",6)
    window.settings.setValue("tutorial/bell/run_id",exp.id)
    window._begin_tutorial()
    assert window.tutorial.step==0
    assert window.tutorial.experiment is None

from dataclasses import replace
import json
import numpy as np
import pytest
from PySide6.QtCore import QTimer
from core.examples import create_example_config
from core.simulation import run_experiment
from tests.qt_helpers import execute,wait_until


@pytest.mark.parametrize("kind,options",[
    ("heatmap",dict(x_parameter="trotter_steps",x_values=[1,2],y_parameter="p2",y_values=[0,.05])),
    ("zne_stability",dict(factor_sets=[[1,3,5]],shot_counts=[64],repetitions=2,qubit=0)),
    ("equal_budget",dict(factor_sets=[[1,3,5]],total_shots=65,repetitions=2,qubit=0)),
])
def test_protocol_analysis_reopen_replay_and_lineage(window,kind,options):
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"),shots=64))
    source=execute(window)
    page=window.page_analysis
    page.apply_options(kind,options)
    for key,value in {"title":"Experimento do Capítulo 4","question":"Como varia o erro?","hypothesis":"Depende de ruído e custo","controls":"Mesmo sistema","evidence_ref":"Tabela 5"}.items():
        page.protocol.fields[key].setText(value)
    window._save_protocol()
    saved=page.protocol.loaded
    assert saved["options"]==options
    page.kind.setCurrentIndex(0)
    window._load_protocol(saved["protocol_id"])
    assert page.kind.currentData()==kind
    page.btn_run.click()
    wait_until(lambda:window._current_worker is None)
    data=page.data
    assert data["kind"]==kind
    if kind=="heatmap":
        assert page.series_combo.currentData()=="fidelity_exact"
    assert data["protocol"]["protocol_id"]==saved["protocol_id"]
    assert data["protocol"]["fields"]["evidence_ref"]=="Tabela 5"
    page.protocol.fields["hypothesis"].setText("Outro plano ainda não salvo")
    page._replay()
    wait_until(lambda:window._current_worker is None)
    assert page.data["analysis_id"]!=data["analysis_id"]
    assert page.data["protocol"]["fields"]["hypothesis"]=="Depende de ruído e custo"
    window._show_page("documentation")
    texts=[window.page_documentation.table.item(i,3).text() for i in range(window.page_documentation.table.rowCount())]
    assert "Tabela 5" in texts
    assert window._current_experiment is source


def test_comparison_loads_states_asynchronously_and_synchronizes_cameras(window):
    a=run_experiment(replace(create_example_config("bell"),shots=64))
    b=run_experiment(replace(create_example_config("depolarizing-bell"),shots=64))
    window.repository.save(a)
    window.repository.save(b)
    window._refresh_history()
    page=window.page_comparison
    page.set_runs(a.id,b.id)
    assert not page.records[a.id].result.states
    page.btn_prepare.click()
    wait_until(lambda:window._current_worker is None)
    assert page.full_data["synchronous"]
    assert page.full_data["experiments"][0].result.states
    page.slider.setValue(3)
    assert "Snapshot 3" in page.frame_label.text()
    page.scenes[0].set_zoom(1.4)
    assert page.scenes[1].zoom==pytest.approx(1.4)
    np.testing.assert_allclose(page.full_data["experiments"][0].result.final_state.data,a.result.final_state.data)
    page.btn_document.click()
    assert window.page_documentation.use_comparison.isChecked()
    assert {e.id for e in window._documentation_sources()}=={a.id,b.id}


def test_comparison_disables_timeline_when_one_source_has_no_snapshots(window):
    cfg=replace(create_example_config("bell"),shots=32)
    a=run_experiment(cfg)
    b=run_experiment(replace(cfg,protocol=replace(cfg.protocol,save_snapshots=False)))
    for exp in (a,b):
        window.repository.save(exp)
    window._refresh_history()
    page=window.page_comparison
    page.set_runs(a.id,b.id)
    page.btn_prepare.click()
    wait_until(lambda:window._current_worker is None)
    assert page.full_data is not None
    assert not page.slider.isEnabled()
    assert "Estados finais" in page.frame_label.text()


def test_gif_export_worker_keeps_event_loop_responsive(window,tmp_path,monkeypatch):
    from gui.main_window import QFileDialog
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"),shots=32))
    source=execute(window)
    page=window.page_documentation
    page.max_frames.setValue(2)
    page.frame_ms.setValue(200)
    destination=tmp_path/"evolution.gif"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a:(str(destination),"GIF (*.gif)"))
    ticks=[]
    timer=QTimer(window)
    timer.setInterval(20)
    timer.timeout.connect(lambda:ticks.append(1))
    timer.start()
    window._export_documentation("gif")
    wait_until(lambda:window._current_worker is None,timeout=30000)
    timer.stop()
    assert destination.read_bytes().startswith(b"GIF")
    assert len(ticks)>2
    assert window._current_experiment is source
    assert "exportada" in page.message.text()


def test_current_bloch_image_exports_camera_and_snapshot_metadata(window,tmp_path,monkeypatch):
    from gui.main_window import QFileDialog
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"),shots=32))
    source=execute(window)
    page=window.page_bloch
    page.slider.setValue(2)
    page.canvas.set_zoom(1.3)
    destination=tmp_path/"bloch.svg"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a:(str(destination),"SVG (*.svg)"))
    window._export_bloch_view()
    assert destination.exists()
    data=json.loads(destination.with_suffix(".metadata.json").read_text())
    assert data["snapshot"]==2
    assert data["source_id"]==source.id
    assert data["camera"]["zoom"]==pytest.approx(1.3)
    assert data["effective_seed"]==source.result.metadata["effective_seed"]


def test_results_zip_uses_complete_export_and_keeps_current_unsaved_analysis(window,tmp_path,monkeypatch):
    import zipfile
    from gui.main_window import QFileDialog
    from core.research import heatmap_study
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"),shots=32))
    source=execute(window)
    analysis=heatmap_study(source,x_values=[1],y_values=[0])
    analysis["analysis_id"]="unsaved-study"
    window.page_analysis.show_analysis(analysis)
    window.page_documentation.include_gif.setChecked(False)
    destination=tmp_path/"complete.zip"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a:(str(destination),"Pacote ZIP (*.zip)"))
    window._export_experiment()
    wait_until(lambda:window._current_worker is None,timeout=60000)
    with zipfile.ZipFile(destination) as archive:
        assert archive.read("report.pdf").startswith(b"%PDF")
        assert archive.read(f"run_{source.id}/bloch_final.svg")
        assert json.loads(archive.read("analyses/analysis_001.json"))["analysis_id"]=="unsaved-study"

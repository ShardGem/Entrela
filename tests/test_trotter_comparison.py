from dataclasses import replace
import pytest

from core.comparison import incompatibility, prepare_comparison
from core.simulation import run_experiment
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from tests.qt_helpers import wait_until


def runs():
    config = ExperimentConfig(SystemConfig(2,J=1,h=.7),SimulationProtocol(1,1,True,2),NoiseConfig(False),32,42)
    a = run_experiment(config)
    b = run_experiment(replace(config,protocol=replace(config.protocol,trotter_steps=8)))
    return a,b


def test_depth_comparison_uses_exact_reference_and_never_interpolates():
    a,b = runs()
    assert incompatibility(a,b)
    assert not incompatibility(a,b,mode="trotter")
    comparison = prepare_comparison([a,b],mode="trotter")
    assert not comparison["synchronous"]
    a_final,b_final = [curve[-1] for curve in comparison["curves"]]
    assert a_final["fidelity"] == pytest.approx(1)
    assert b_final["fidelity"] == pytest.approx(1)
    assert a_final["fidelity_exact"] < b_final["fidelity_exact"] < 1
    altered = replace(b,config=replace(b.config,system=replace(b.config.system,J=2)))
    assert "Sistemas diferentes" in incompatibility(a,altered,mode="trotter")
    altered = replace(b,config=replace(b.config,protocol=replace(b.config.protocol,total_time=2)))
    assert "tempo total" in incompatibility(a,altered,mode="trotter")
    from core.figures import temporal_figure
    figure = temporal_figure([a,b],reference="exact")
    assert "exata" in figure.axes[0].get_ylabel()
    assert figure.axes[0].lines[0].get_ydata()[-1] == pytest.approx(a_final["fidelity_exact"])
    assert figure.axes[0].lines[1].get_ydata()[-1] == pytest.approx(b_final["fidelity_exact"])
    figure.clear()


def test_comparison_ui_loads_new_mode_and_syncs_unfocus(window):
    a,b = runs()
    for source in (a,b):
        window.repository.save(source)
    window._refresh_history()
    page = window.page_comparison
    page.set_runs(a.id,b.id)
    assert not page.btn_prepare.isEnabled()
    page.comparison_mode.setCurrentIndex(page.comparison_mode.findData("trotter"))
    page.btn_prepare.click()
    wait_until(lambda: window._current_worker is None)
    assert page.full_data["mode"] == "trotter"
    assert page.curve_canvas.fig.axes[0].get_ylabel() == "F à evolução exata"
    assert not page.slider.isEnabled()
    assert "Estados finais" in page.frame_label.text()
    page.focus.setCurrentIndex(page.focus.findData(1))
    page.scenes[0].reset_camera()
    assert page.focus.currentData() == -1
    assert all(scene.focus == -1 for scene in page.scenes)
    page.comparison_mode.setCurrentIndex(0)
    assert page.full_data is None


def test_exported_depth_study_keeps_the_same_scientific_reference(tmp_path):
    import json,zipfile
    from core.documentation import export_documentation
    from core.pdf_layout import REPORT_SECTIONS
    from data.repository import ExperimentRepository
    from data.study_package import prepare_study_import
    a,b = runs()
    path = export_documentation([a,b],tmp_path/"depth.zip",include_gif=False,
        report_options={key:False for key in REPORT_SECTIONS},raster_dpi=72,comparison_mode="trotter")
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["comparison_reference"] == "exact"
    plan = prepare_study_import(path,ExperimentRepository(tmp_path/"imported"))
    try:
        assert plan.comparison_mode == "trotter"
    finally:
        plan.abort()

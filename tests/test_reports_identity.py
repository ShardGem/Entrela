"""Friendly presentation names never replace the scientific record identity."""

from dataclasses import replace

import pytest

from core.examples import create_example_config
from core.report import report_html, export_report, hamiltonian_description
from core.simulation import run_experiment
from data.repository import ExperimentRepository
from data.workspace import WorkspaceLibrary
from gui.pages.history import HistoryPage
from gui.pages.comparison import ComparisonPage


@pytest.fixture
def run():
    return run_experiment(replace(create_example_config("bell"), shots=64, seed=17))


def test_display_name_survives_reload_and_old_annotation_api(tmp_path, run):
    repository = ExperimentRepository(tmp_path / "runs")
    path = repository.save(run)
    original = path.read_bytes()
    library = WorkspaceLibrary(tmp_path / "workspace")
    library.annotate(run.id, "TCC", "Hipótese", ["Bell"], title=" Bell — referência ")
    library.annotate(run.id, "TCC", "Notas atualizadas", ["Bell"])
    reopened = WorkspaceLibrary(tmp_path / "workspace").read()
    assert reopened["annotations"][run.id]["title"] == "Bell — referência"
    assert reopened["annotations"][run.id]["notes"] == "Notas atualizadas"
    assert path.read_bytes() == original
    assert repository.load(run.id).id == run.id


def test_history_name_and_id_both_searchable(qt_app, run):
    page = HistoryPage()
    page.annotations = {run.id: {"title": "Bell de referência", "notes": "Hipótese da pesquisa"}}
    page.load([run])
    assert page.table.item(0, 1).text() == "Bell de referência"
    assert run.id in page.table.item(0, 1).toolTip()
    page.search.setText(run.id)
    assert page.table.rowCount() == 1
    page.search.setText("referência")
    assert page.table.rowCount() == 1
    page.search.setText("Hipótese")
    assert page.table.rowCount() == 1
    selected = []
    page.experiment_selected.connect(selected.append)
    page._open(0, 1)
    assert selected == [run.id]
    page.close()


def test_comparison_named_runs_keep_technical_lookup(qt_app, run):
    other = replace(run, id="other-run")
    page = ComparisonPage()
    page.annotations = {run.id: {"title": "Controle ideal"}, other.id: {"title": "Repetição"}}
    page.load([run, other])
    assert "Controle ideal" in page.first_run.itemText(0)
    assert page.first_run.itemData(0) == run.id
    assert page.metrics_table.rowCount() == 3
    page.close()


@pytest.mark.parametrize("model,expression", [("Heisenberg", "XiXj + YiYj + ZiZj"), ("XY", "XiXj + YiYj"), ("XXZ", "0,5 ZiZj")])
def test_report_model_convention_uses_actual_hamiltonian(run, model, expression):
    config = replace(run.config, system=replace(run.config.system, hamiltonian=model))
    description = hamiltonian_description(config)
    assert expression in description
    assert "Ising" not in description
    assert "h não participa" in description


def test_report_embeds_actual_curves_identity_and_provenance(qt_app, tmp_path, run):
    annotation = {"title": "Bell <controle>", "project": "TCC", "notes": "<script>unsafe</script>"}
    html = report_html(run, annotation=annotation)
    assert "Bell &lt;controle&gt;" in html
    assert "<script>" not in html
    assert run.id in html
    assert run.created_at.isoformat() in html
    assert "effective_seed" in html
    assert "qiskit-aer" in html
    assert html.count("data:image/png;base64,") == 2
    assert "snapshots reais" in html
    pdf = export_report(run, tmp_path / "report.pdf", annotation=annotation)
    assert pdf.read_bytes().startswith(b"%PDF")
    assert pdf.stat().st_size > 10_000


def test_benchmark_report_preserves_null_state_metrics(run):
    analysis = {
        "kind": "mitigation_benchmark", "source_id": run.id,
        "ideal_observable": 0.0, "actual_cost": {"circuits": 3, "shots": 192},
        "rows": [{"method": "zne_linear", "label": "ZNE linear", "status": "ok", "estimate": .1, "absolute_error": .1, "stderr": .02, "duration_s": .5, "fidelity": None}],
    }
    html = report_html(run, analysis=analysis)
    assert "ZNE linear" in html
    assert "aquisição compartilhada" in html
    assert "não reconstrói um estado mitigado" in html
    assert html.count("data:image/png;base64,") == 3
    assert analysis["rows"][0]["fidelity"] is None


def test_report_rejects_analysis_from_another_source(run):
    with pytest.raises(ValueError, match="outra execução"):
        report_html(run, analysis={"kind": "temporal", "source_id": "different-source", "rows": []})


def test_study_report_plots_calculated_errors_and_keeps_run_index(run):
    analysis = {"kind": "trotter_noise", "source_id": run.id, "rows": [
        {"steps": 1, "ideal_infidelity": .1, "noisy_infidelity": .2},
        {"steps": 2, "ideal_infidelity": .01, "noisy_infidelity": .3},
    ], "runs": [{"id": "paired-reference", "condition": "ideal", "steps": 1, "metadata": {"operations": "very-large-record"}}]}
    html = report_html(run, analysis=analysis)
    assert html.count("data:image/png;base64,") == 3
    assert "paired-reference" in html
    assert "very-large-record" not in html
    assert "very-large-record" == analysis["runs"][0]["metadata"]["operations"]


def test_large_mitigation_payload_is_summarized_in_report_and_preserved(run):
    operations = [{"name": "native-operation-only-in-raw-export", "qubits": [0]}] * 10_000
    state = {"kind": "density_matrix", "real": [[0.015625] * 64 for _ in range(64)], "imag": [[0.] * 64 for _ in range(64)]}
    run.result.mitigation = {"method": "quadratic", "degrees_of_freedom": 0, "native_circuit": {"operations": operations}, "samples": [{"state": state}]}
    analysis = {"kind": "mitigation_benchmark", "source_id": run.id, "rows": [], "provenance": {"native_circuit": {"operations": operations}}, "samples": [{"state": state}], "fits": {"quadratic": {"degrees_of_freedom": 0}}}
    html = report_html(run, analysis=analysis)
    assert "native-operation-only-in-raw-export" not in html
    assert "10000 operações" in html
    assert "dimensions" in html
    assert "Estado complexo integral preservado no JSON completo" in html
    assert "zero graus de liberdade residual" in html
    assert len(run.result.mitigation["native_circuit"]["operations"]) == 10_000
    assert analysis["samples"][0]["state"]["real"][63][63] == 0.015625
    assert state["imag"][63][63] == 0.

"""A configuração do estudo é compreensível e segue a evidência selecionada."""
from copy import deepcopy
from dataclasses import replace

import pytest

from core.analysis import convergence_analysis, temporal_analysis
from core.circuit_document import CircuitDocument, CircuitGate
from core.examples import create_example_config
from core.simulation import run_experiment
from data.analyses import save_analysis
from gui.pages.analysis import AnalysisPage


@pytest.fixture
def source():
    return run_experiment(replace(create_example_config("bell"), shots=16))


@pytest.mark.parametrize("kind, options", [
    ("sweep", {"parameter": "t1_us", "values": [20., 50.], "seeds": [0, 42]}),
    ("heatmap", {"x_parameter": "trotter_steps", "x_values": [1., 3.], "y_parameter": "p2", "y_values": [0., .02]}),
    ("mitigation_benchmark", {"qubit": 0, "shots": 32}),
    ("convergence", {"steps": [1, 3, 9]}),
])
def test_human_labels_roundtrip_scientific_identifiers(qt_app, kind, options):
    page = AnalysisPage()
    try:
        page.apply_options(kind, options)
        assert page.analysis_options() == (kind, options)
        assert page.parameter.currentText() != page.parameter.currentData()
        assert "T₁" in page.parameter.itemText(page.parameter.findData("t1_us"))
        assert "µs" in page.parameter.itemText(page.parameter.findData("t1_us"))
        assert "Passos" in page.steps.accessibleName()
    finally:
        page.close()


def test_examples_are_explicit_and_do_not_replace_edited_values_or_execute(qt_app, source):
    page = AnalysisPage()
    page.load_experiment(source)
    page.kind.setCurrentIndex(page.kind.findData("sweep"))
    requested = []
    page.requested.connect(lambda *args: requested.append(args))
    try:
        page.values.setText("12.123456789, 25")
        page.parameter.setCurrentText("t1_us")
        assert page.values.text() == "12.123456789, 25"
        assert "microssegundos" in page.parameter_hint.text()
        page.use_example.click()
        assert page.values.text() == "20, 50, 100"
        assert requested == []
    finally:
        page.close()


def test_incompatible_sources_explain_requirements_before_request(qt_app):
    config = replace(create_example_config("bell"), shots=16)
    no_snapshots = run_experiment(replace(config, protocol=replace(config.protocol, save_snapshots=False)))
    free = run_experiment(replace(config, system=replace(config.system, initial_state="zero"), protocol=replace(config.protocol, total_time=2., trotter_steps=2), circuit=CircuitDocument(2, (CircuitGate("h", (0,)), CircuitGate("cx", (0, 1))))))
    page = AnalysisPage()
    requested = []
    page.requested.connect(lambda *args: requested.append(args))
    try:
        page.load_experiment(no_snapshots)
        assert not page.btn_run.isEnabled()
        assert "snapshots" in page.availability.text()
        page.btn_run.click()
        assert requested == []
        page.kind.setCurrentIndex(page.kind.findData("mitigation_benchmark"))
        assert page.btn_run.isEnabled()
        page.load_experiment(free)
        page.kind.setCurrentIndex(page.kind.findData("convergence"))
        assert not page.btn_run.isEnabled()
        assert "Hamiltoniano" in page.availability.text()
        page.kind.setCurrentIndex(page.kind.findData("sweep"))
        page.parameter.setCurrentText("J")
        assert not page.btn_run.isEnabled()
        page.parameter.setCurrentText("p1")
        assert page.btn_run.isEnabled()
    finally:
        page.close()


def test_unused_h_is_explained_without_suggesting_a_change_to_the_model(qt_app):
    config = create_example_config("bell")
    source = run_experiment(replace(config, system=replace(config.system, hamiltonian="XY"), shots=16))
    page = AnalysisPage()
    try:
        page.load_experiment(source)
        page.kind.setCurrentIndex(page.kind.findData("sweep"))
        page.parameter.setCurrentText("h")
        assert not page.btn_run.isEnabled()
        assert "não participa" in page.availability.text()
        page.parameter.setCurrentText("J")
        assert page.btn_run.isEnabled()
    finally:
        page.close()


def test_open_saved_result_synchronizes_configuration_without_new_calculations(qt_app, source, tmp_path):
    page = AnalysisPage()
    page.load_experiment(source)
    data = convergence_analysis(source.config, steps=[1, 3])
    data["source_id"] = source.id
    path = save_analysis(data, tmp_path / "convergence.json")
    requested = []
    page.requested.connect(lambda *args: requested.append(args))
    try:
        page.apply_options("sweep", {"parameter": "p2", "values": [0., .1]})
        page.set_saved([("Precisão registrada", path)])
        page.saved.setCurrentIndex(1)
        assert page.kind.currentData() == "convergence"
        assert page.analysis_options() == ("convergence", {"steps": [1, 3]})
        assert page.tabs.currentWidget() is page.results_tab
        assert page.data["rows"] == data["rows"]
        assert requested == []
        assert page.replay_button.isEnabled()
    finally:
        page.close()


def test_circuit_temporal_table_uses_operation_indices(qt_app):
    base = create_example_config("bell")
    config = replace(base, shots=16, system=replace(base.system, initial_state="zero"), protocol=replace(base.protocol, total_time=2., trotter_steps=2), circuit=CircuitDocument(2, (CircuitGate("h", (0,)), CircuitGate("cx", (0, 1)))))
    source = run_experiment(config)
    page = AnalysisPage()
    try:
        page.load_experiment(source)
        data = temporal_analysis(source)
        page.show_analysis(data)
        headers = [page.table.horizontalHeaderItem(i).text() for i in range(page.table.columnCount())]
        assert "Índice da porta lógica (sem tempo físico)" in headers
        assert "Tempo (ℏ=1)" not in headers
        assert page.canvas.fig.axes[0].get_xlabel() == "Índice da porta lógica (sem tempo físico)"
    finally:
        page.close()


def test_invalid_artifact_preserves_previous_evidence_and_legacy_remains_viewable(qt_app, source):
    page = AnalysisPage()
    page.load_experiment(source)
    valid = temporal_analysis(source)
    page.show_analysis(valid)
    previous = page.data
    previous_options = page.analysis_options()
    previous_rows = page.table.rowCount()
    try:
        corrupted = deepcopy(valid)
        corrupted["rows"][0]["time"] = "tempo inválido"
        with pytest.raises(ValueError):
            page.show_analysis(corrupted)
        assert page.data is previous
        assert page.analysis_options() == previous_options
        assert page.table.rowCount() == previous_rows
        assert page.export_button.isEnabled()
        legacy = {"kind": "sweep", "rows": [{"value": .1, "fidelity": .9}], "note": "Resultado histórico sem insumos de reprodução."}
        page.show_analysis(legacy)
        assert page.data is legacy
        assert page.export_button.isEnabled()
        assert not page.replay_button.isEnabled()
        assert "origem" in page.replay_button.toolTip()
    finally:
        page.close()


def test_recent_source_menu_emits_only_selected_identifier_and_respects_busy_state(qt_app, source):
    page = AnalysisPage()
    page.load_experiment(source)
    selected, requested = [], []
    page.source_requested.connect(selected.append)
    page.requested.connect(lambda *args: requested.append(args))
    try:
        assert not page.source_button.isEnabled()
        page.set_recent_sources([(source.id, "Bell <controle> & pesquisa"), ("outra-fonte", "Ruído térmico")])
        assert page.source_button.isEnabled()
        actions = page.source_menu.actions()
        assert actions[0].text() == "Bell <controle> && pesquisa"
        assert actions[0].data() == source.id
        actions[1].trigger()
        assert selected == ["outra-fonte"]
        assert page.experiment is source
        assert requested == []
        page.set_running(True)
        assert not page.source_button.isEnabled()
        actions[0].trigger()
        assert selected == ["outra-fonte"]
        page.set_running(False)
        assert page.source_button.isEnabled()
    finally:
        page.close()

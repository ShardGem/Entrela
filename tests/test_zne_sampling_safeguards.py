"""Sampling limits must remain visible even when the plug-in SE vanishes."""

from copy import deepcopy
from math import comb
import json

import numpy as np
import pytest
from qiskit import QuantumCircuit

from core.benchmark import mitigation_benchmark
from core.circuit_document import CircuitDocument, CircuitGate
from core.mitigation import run_zne, wilson_z_interval, z_sampling_metadata
from core.research import equal_budget_study
from core.simulation import run_experiment
from core.types import ExperimentConfig, NoiseConfig, SimulationProtocol, SystemConfig


def h_source(shots=1):
    return run_experiment(ExperimentConfig(
        SystemConfig(1), SimulationProtocol(1., 1, True),
        NoiseConfig(enabled=False), shots=shots, seed=42,
        circuit=CircuitDocument(1, (CircuitGate("h", (0,)),)),
    ))


def test_wilson_interval_matches_score_formula_including_one_shot_boundaries():
    # At k=0,n=1 the score upper bound for p is z²/(1+z²).
    z_squared = 1.959963984540054**2
    expected_upper = 2 * z_squared / (1 + z_squared) - 1
    np.testing.assert_allclose(wilson_z_interval(0, 1), [-1, expected_upper], atol=1e-14)
    np.testing.assert_allclose(wilson_z_interval(1, 1), [-expected_upper, 1], atol=1e-14)
    interval = wilson_z_interval(5000, 10000)
    assert interval[0] == pytest.approx(-interval[1])
    assert interval[1] == pytest.approx(1.959963984540054 / np.sqrt(10000 + z_squared))


@pytest.mark.parametrize("args", [(0, 0), (-1, 1), (2, 1), (True, 1), (0, 1, 0),
                                  (0, 1, 1), (0, 1, float("nan"))])
def test_wilson_rejects_invalid_observations(args):
    with pytest.raises(ValueError):
        wilson_z_interval(*args)


def test_wilson_coverage_is_approximate_not_a_small_sample_guarantee():
    # Enumerate all outcomes independently of Aer and of any extrapolation.
    shots, probability = 5, .5
    target_z = 2 * probability - 1
    coverage = sum(comb(shots, k) * probability**k * (1 - probability)**(shots - k)
                   for k in range(shots + 1)
                   if wilson_z_interval(k, shots)[0] <= target_z <= wilson_z_interval(k, shots)[1])
    assert coverage == pytest.approx(.9375)
    assert coverage < .95


def test_one_shot_hadamard_keeps_raw_zero_se_but_reports_nonzero_intervals():
    circuit = QuantumCircuit(1)
    circuit.h(0)
    result = run_zne(circuit, None, shots=1, seed=42)
    assert result["stderr"] == [0., 0., 0.]
    assert result["extrapolated_stderr"] == 0.
    assert result["extrapolated_absolute_error"] > .1
    assert result["sampling_diagnostics"]["low_shots_factors"] == [1, 3, 5]
    assert result["sampling_diagnostics"]["boundary_factors"] == [1, 3, 5]
    assert len(result["sampling_diagnostics"]["warnings"]) == 2
    assert all(low < 0 < high for low, high in result["sampling_intervals"])
    assert "não propagado" in result["sampling_diagnostics"]["interval_scope"]
    assert "fidelity" not in result
    json.dumps(result, allow_nan=False)


def test_no_variation_does_not_claim_observations_are_wrong_or_certain():
    deterministic = z_sampling_metadata([dict(scale_factor=1, counts={"00": 128})], 2, 1)
    diagnosis = deterministic["sampling_diagnostics"]
    assert diagnosis["low_shots_factors"] == []
    assert diagnosis["boundary_factors"] == [1]
    assert deterministic["sampling_intervals"][0][1] == pytest.approx(1)
    assert deterministic["sampling_intervals"][0][0] < 1
    balanced = z_sampling_metadata([dict(scale_factor=3, counts={"01": 50, "00": 50})], 2, 0)
    assert balanced["sampling_diagnostics"]["warnings"] == []
    assert balanced["sampling_intervals"][0][0] < 0 < balanced["sampling_intervals"][0][1]


def test_benchmark_and_equal_budget_keep_sampling_limits_in_exported_metadata():
    source = h_source()
    benchmark = mitigation_benchmark(source)
    assert benchmark["rows"][1]["stderr"] == 0
    assert benchmark["sampling_diagnostics"]["boundary_factors"] == [1, 3, 5]
    assert "zero não comprova" in benchmark["note"]
    interval = benchmark["sampling_by_method"]["none"]["sampling_intervals"][0]
    assert interval[0] < interval[1]
    assert "extrapolated_interval" not in benchmark["fits"]["linear"]  # No fabricated ZNE target interval.
    assert all(set(row) == set(benchmark['rows'][0]) for row in benchmark['rows'])
    study = equal_budget_study(source, factor_sets=((1, 3, 5),), total_shots=3, repetitions=2)
    for run in study["runs"]:
        assert run["sampling_diagnostics"]["low_shots_factors"] == [1, 3, 5]
        assert run["fits"]["linear"]["extrapolated_stderr"] == 0
        assert all(lo < hi for lo, hi in run["sampling_intervals"])
    assert "zero não comprova certeza" in study["note"]
    json.dumps(study, allow_nan=False)


def test_mitigation_page_shows_warnings_and_keeps_exploratory_one_shot_available(qt_app):
    from gui.pages.mitigation import MitigationPage
    source = h_source()
    circuit = QuantumCircuit(1)
    circuit.h(0)
    source.result.mitigation = run_zne(circuit, None, shots=1, seed=42)
    page = MitigationPage()
    try:
        page.load_experiment(source)
        assert page.shots.minimum() == 1
        assert page.table.columnCount() == 4
        assert page.table.rowCount() == 3
        assert "[" in page.table.item(0, 3).text()
        assert "zero não comprova" in page.sampling_warning.text()
        assert "±" not in page.summary.text()
        assert page.sampling_warning.accessibleName()
        requests = []
        page.run_requested.connect(lambda *args: requests.append(args))
        page.btn_run.click()
        assert requests == [(0, "linear", 1)]
        legacy = deepcopy(source.result.mitigation)
        for key in ("samples", "sampling_intervals", "sampling_diagnostics"):
            legacy.pop(key)
        source.result.mitigation = legacy
        page.load_experiment(source)
        assert page.table.item(0, 3).text() == "Não registrado"
        assert "Registro anterior" in page.sampling_warning.text()
        assert "zero não comprova" in page.sampling_warning.text()
    finally:
        page.close()

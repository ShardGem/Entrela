"""Independent known states distinguish global mixture from local Bloch data."""
from dataclasses import replace
import numpy as np
import pytest
from qiskit.quantum_info import Statevector, DensityMatrix
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from core.experiment_diagnostics import diagnose_experiment
from core.state_inspection import inspect_state
from gui.widgets.state_inspector import StateInspector


def bell():
    return Statevector(np.array([1, 0, 0, 1]) / np.sqrt(2))


def test_bell_and_classical_mixture_have_same_local_purity_but_different_global_state():
    pure = inspect_state(bell(), bell())
    mixture = inspect_state(DensityMatrix(np.diag([.5, 0, 0, .5])), bell())
    assert pure['purity'] == pytest.approx(1)
    assert pure['entropy_bits'] == pytest.approx(0, abs=1e-12)
    assert pure['coherence_l1'] == pytest.approx(1)
    assert pure['partition']['negativity'] == pytest.approx(.5)
    assert pure['partition']['mutual_information_bits'] == pytest.approx(2)
    assert mixture['purity'] == pytest.approx(.5)
    assert mixture['entropy_bits'] == pytest.approx(1)
    assert mixture['coherence_l1'] == pytest.approx(0)
    assert mixture['partition']['negativity'] == pytest.approx(0)
    assert mixture['fidelity'] == pytest.approx(.5)
    assert mixture['partition']['mutual_information_bits'] == pytest.approx(1)
    assert pure['partition']['purity_a'] == pytest.approx(.5)
    assert mixture['partition']['purity_a'] == pytest.approx(.5)


def test_ghz_partitions_and_invalid_states_preserve_source():
    state = Statevector([1 / np.sqrt(2), 0, 0, 0, 0, 0, 0, 1 / np.sqrt(2)])
    original = state.data.copy()
    for partition in ((0,), (1,), (2,), (0, 2)):
        data = inspect_state(state, partition=partition)
        assert data['partition']['negativity'] == pytest.approx(.5)
        assert data['partition']['entropy_a_bits'] == pytest.approx(1)
    np.testing.assert_array_equal(state.data, original)
    for partition in ((), (0, 0), (0, 1, 2), (False,), (3,)):
        with pytest.raises(ValueError):
            inspect_state(state, partition=partition)
    with pytest.raises(ValueError):
        inspect_state(DensityMatrix([[1.1, 0], [0, -.1]]))
    with pytest.raises(ValueError):
        inspect_state(Statevector([1, 1]))
    with pytest.raises(ValueError):
        inspect_state(state, Statevector([1, 0]))


def test_advisories_describe_ideal_limits_without_claiming_noisy_stationarity():
    config = ExperimentConfig(SystemConfig(2, J=0, h=0, initial_state='bell'),
                              SimulationProtocol(), NoiseConfig(True))
    notices = {item.code: item for item in diagnose_experiment(config)}
    assert 'zero_hamiltonian' in notices
    assert 'bell_local_bloch_zero' in notices
    assert 'ruído' in notices['zero_hamiltonian'].message
    diagonal = replace(config, system=SystemConfig(2, J=1, h=0, initial_state='plus'))
    codes = {item.code for item in diagnose_experiment(diagonal)}
    assert 'constant_z_populations' in codes
    assert 'commuting_terms' in codes
    assert 'stationary_initial_state' not in codes
    noncommuting = replace(diagonal, system=replace(diagonal.system, h=1))
    assert 'commuting_terms' not in {item.code for item in diagnose_experiment(noncommuting)}


def test_inspector_is_lazy_tracks_selected_state_and_clears_invalid_view(qt_app):
    inspector = StateInspector()
    inspector.set_state(bell(), context='Snapshot 1')
    assert inspector.quantities is None
    inspector.show()
    qt_app.processEvents()
    try:
        assert inspector.quantities['purity'] == pytest.approx(1)
        assert 'Snapshot 1' in inspector.summary.text()
        inspector.set_state(DensityMatrix(np.eye(4) / 4), context='Snapshot 2')
        assert inspector.quantities['entropy_bits'] == pytest.approx(2)
        inspector.tabs.setCurrentWidget(inspector.matrix_table)
        assert inspector.matrix_table.rowCount() == 4
        assert inspector.partition.currentData() == (0,)
        inspector.set_state(Statevector([2, 0]))
        assert inspector.quantities is None
        assert inspector.tabs.isHidden()
        assert 'inválido' in inspector.summary.text()
    finally:
        inspector.close()
        inspector.deleteLater()


def test_bloch_and_results_inspect_actual_frames_and_final_state(window, qt_app):
    from core.simulation import run_experiment
    config = ExperimentConfig(SystemConfig(1, J=0, h=.7),
                              SimulationProtocol(trotter_steps=2, save_snapshots=True), NoiseConfig(False), shots=16, seed=42)
    experiment = run_experiment(config)
    window._current_experiment = experiment
    window._display_experiment(experiment)
    window._show_page('bloch')
    page = window.page_bloch
    page.visual_tabs.setCurrentWidget(page.state_inspector)
    page.current_frame = len(experiment.result.states) - 1
    page._refresh_ui()
    qt_app.processEvents()
    np.testing.assert_allclose(page.state_inspector.quantities['density_matrix'], DensityMatrix(experiment.result.states[-1]).data)
    window._show_page('results')
    window.page_results.tabs.setCurrentWidget(window.page_results.state_inspector)
    qt_app.processEvents()
    np.testing.assert_allclose(window.page_results.state_inspector.quantities['density_matrix'], DensityMatrix(experiment.result.final_state).data)

from dataclasses import replace
import numpy as np
import pytest
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix,Statevector,Operator,SparsePauliOp
from core.types import *
from core.circuits import _build_hamiltonian
from core.simulation import run_experiment,SimulationCancelled
from core.noise import build_noise_model
from core.metrics import fidelity,purity,energy_expectation
from core.mitigation import _insert_identity_pairs,_expectation_z,run_zne
from core.examples import EXAMPLES,create_example_config

def cfg(**changes):
    return replace(ExperimentConfig(SystemConfig(),SimulationProtocol(),NoiseConfig(enabled=False),shots=256,seed=42),**changes)

@pytest.mark.parametrize("t2",[100.,140.])
def test_thermal_valid(t2):
    assert build_noise_model(NoiseConfig(kind="Termico",t1_us=70,t2_us=t2)) is not None
@pytest.mark.parametrize("t1,t2",[(70,140.001),(0,1),(-1,1),(1,0),(1,float("nan")),(float("inf"),1)])
def test_thermal_invalid(t1,t2):
    with pytest.raises(ValueError):NoiseConfig(kind="Termico",t1_us=t1,t2_us=t2).validate()
@pytest.mark.parametrize("changes",[{"shots":0},{"shots":True},{"shots":1.5},{"seed":-1},{"seed":2**32},{"seed":1.5}])
def test_invalid_execution(changes):
    with pytest.raises(ValueError):cfg(**changes).validate()
@pytest.mark.parametrize("system",[SystemConfig(0),SystemConfig(7),SystemConfig(True),SystemConfig(1.5),
                                  SystemConfig(J=float("nan")),SystemConfig(hamiltonian="invalid"),
                                  SystemConfig(1,initial_state="bell")])
def test_invalid_system(system):
    with pytest.raises(ValueError):system.validate()
@pytest.mark.parametrize("protocol",[SimulationProtocol(total_time=0),SimulationProtocol(total_time=float("nan")),
                                    SimulationProtocol(trotter_steps=1.5),SimulationProtocol(trotter_order=3)])
def test_invalid_protocol(protocol):
    with pytest.raises(ValueError):protocol.validate()
def test_inactive_noise_does_not_block_ideal():
    assert build_noise_model(NoiseConfig(enabled=False,t1_us=-1)) is None
def test_ising_independent_matrix():
    x=np.array([[0,1],[1,0]])
    z=np.diag([1.,-1.])
    expected=np.kron(z,z)+.5*(np.kron(x,np.eye(2))+np.kron(np.eye(2),x))
    np.testing.assert_allclose(_build_hamiltonian(2,"Ising",1,.5,False).to_matrix(),expected)
def test_evolution_against_exact_exponential():
    x=np.array([[0,1],[1,0]])
    z=np.diag([1.,-1.])
    h=np.kron(z,z)+.5*(np.kron(x,np.eye(2))+np.kron(np.eye(2),x))
    exact=expm(-1j*.7*h)[:,0]
    result=run_experiment(cfg(protocol=SimulationProtocol(.7,64,True))).result
    assert abs(np.vdot(exact,result.final_state.data))**2>1-1e-7
def test_order_four_improves_trotter_accuracy():
    h=_build_hamiltonian(2,"Ising",1,.5,False).to_matrix()
    exact=expm(-1j*h)[:,0]
    errors=[]
    for order in (2,4):
        final=run_experiment(cfg(protocol=SimulationProtocol(1.,2,True,order))).result.final_state
        errors.append(1-abs(np.vdot(exact,final.data))**2)
    assert errors[1]<errors[0]/10
@pytest.mark.parametrize("kind",["Despolarizador","Termico"])
def test_noisy_snapshots_and_seed_repeatability(kind):
    config=cfg(noise=NoiseConfig(kind=kind,t1_us=70,t2_us=100))
    a,b=run_experiment(config),run_experiment(config)
    assert a.id!=b.id and a.result.counts==b.result.counts
    assert len(a.result.density_matrices)==5
    assert a.result.times==[0,.25,.5,.75,1]
    assert all(s.is_valid() for s in a.result.states)
    assert 0<a.result.purity<1
    without=run_experiment(replace(config,protocol=replace(config.protocol,save_snapshots=False)))
    np.testing.assert_allclose(a.result.final_state.data,without.result.final_state.data)
    assert without.result.counts==a.result.counts
def test_analytic_depolarizing_channel():
    result=run_experiment(cfg(system=SystemConfig(1,J=0,h=0,initial_state="plus"),
                               noise=NoiseConfig(p1=.2,p2=0))).result
    np.testing.assert_allclose(result.final_state.data,[[.5,.4],[.4,.5]],atol=1e-12)
    assert result.purity==pytest.approx(.82)
    assert result.fidelity==pytest.approx(.9)
def test_automatic_seed_is_recorded():
    a=run_experiment(cfg(seed=None))
    b=run_experiment(replace(a.config,seed=a.result.metadata["effective_seed"]))
    assert a.result.counts==b.result.counts
def test_mixed_state_metrics_and_full_energy():
    mixed=DensityMatrix(np.eye(2)/2)
    assert purity(mixed)==pytest.approx(.5)
    assert fidelity(mixed,Statevector([1,0]))==pytest.approx(.5)
    plus=Statevector(np.array([1,1])/np.sqrt(2))
    assert energy_expectation(plus,SparsePauliOp("X"))==pytest.approx(1)
    with pytest.raises(ValueError):purity(Statevector([2,0]))
@pytest.mark.parametrize("example",EXAMPLES,ids=lambda e:e.id)
def test_every_example_executes(example):
    config=replace(example.create_config(),shots=64)
    run=run_experiment(config)
    assert sum(run.result.counts.values())==64
    assert run.result.final_state.is_valid()
    assert len(run.result.states)==5
def test_example_copy_is_immutable_and_independent():
    a,b=create_example_config("bell"),create_example_config("bell")
    assert a==b and a is not b and a.system is not b.system
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):a.shots=3
def test_bell_and_spin_analytic_predictions():
    bell=run_experiment(create_example_config("bell")).result
    assert set(bell.counts)=={"00","11"}
    np.testing.assert_allclose(bell.final_state.probabilities(),[.5,0,0,.5],atol=1e-12)
    spin=run_experiment(create_example_config("spin-oscillation")).result
    assert spin.final_state.probabilities()[1]==pytest.approx(np.sin(.5)**2)
def test_folding_preserves_unitary_and_true_scale():
    circuit=QuantumCircuit(2)
    circuit.u(.2,.3,.4,0)
    circuit.cx(0,1)
    for factor in (1,3,5):
        folded=_insert_identity_pairs(circuit,(factor-1)//2)
        assert folded.size()==factor*circuit.size()
        assert Operator(circuit).equiv(Operator(folded))
def test_observable_bit_order():
    assert _expectation_z({"01":8},2,0)==-1
    assert _expectation_z({"01":8},2,1)==1
@pytest.mark.parametrize("factors,method",[([1,2,3],"linear"),([1,1],"linear"),([1],"linear"),
                                          ([1,3],"quadratic"),([3,5],"linear")])
def test_invalid_zne_fits(factors,method):
    circuit=QuantumCircuit(1)
    circuit.x(0)
    with pytest.raises(ValueError):run_zne(circuit,None,factors,method=method)
def test_zne_matches_analytic_channel_and_not_optimized_away():
    circuit=QuantumCircuit(1)
    circuit.x(0)
    result=run_zne(circuit,build_noise_model(NoiseConfig(p1=.1)),shots=32768,seed=42)
    np.testing.assert_allclose(result["measured"],[-.9,-.9**3,-.9**5],atol=.02)
    assert [g["u"] for g in result["folded_gate_counts"]]==[1,3,5]
    assert result["extrapolated_stderr"]>0
def test_zne_unused_classical_registers_and_seed():
    circuit=QuantumCircuit(2,4)
    circuit.x(0)
    a=run_zne(circuit,None,shots=64,seed=42)
    assert a["extrapolated"]==pytest.approx(-1)
    assert a==run_zne(circuit,None,shots=64,seed=42)
def test_cancellation():
    with pytest.raises(SimulationCancelled):run_experiment(cfg(),is_cancelled=lambda:True)

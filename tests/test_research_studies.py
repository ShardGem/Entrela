from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from core.examples import create_example_config
from core.research import heatmap_study,zne_stability,equal_budget_study
from core.simulation import run_experiment,SimulationCancelled
from core.types import ExperimentConfig,SystemConfig,SimulationProtocol,NoiseConfig
from core.circuit_document import CircuitDocument,CircuitGate


@pytest.fixture
def x_run():
    doc=CircuitDocument(1,(CircuitGate("x",(0,)),))
    return run_experiment(ExperimentConfig(SystemConfig(1),SimulationProtocol(1.,1,True),NoiseConfig(p1=.2,p2=0),shots=64,seed=42,circuit=doc))


def test_stability_independent_samples_and_empirical_metrics(x_run):
    before=deepcopy(x_run.result.counts)
    data=zne_stability(x_run,factor_sets=[[1,3,5]],shot_counts=[1024],repetitions=3)
    assert len(data["rows"])==2
    assert len(data["runs"])==3
    seeds=[s["effective_seed"] for run in data["runs"] for s in run["samples"]]
    assert len(seeds)==len(set(seeds))
    np.testing.assert_allclose([s["counts"].get("0",0)/1024*2-1 for s in data["runs"][0]["samples"]],[-.8,-.8**3,-.8**5],atol=.08)
    for row in data["rows"]:
        method=row["method"].removeprefix("zne_")
        values=np.array([r["fits"][method]["extrapolated"] for r in data["runs"]])
        assert row["bias"]==pytest.approx(values.mean()+1)
        assert row["sample_variance"]==pytest.approx(values.var(ddof=1))
        assert row["mse"]==pytest.approx(np.mean((values+1)**2))
        assert row["rmse"]==pytest.approx(np.sqrt(row["mse"]))
        assert row["shots_per_method"]==3072
    assert x_run.result.counts==before
    replay=zne_stability(x_run,**data["options"])
    assert [[s["counts"] for s in r["samples"]] for r in replay["runs"]]==[[s["counts"] for s in r["samples"]] for r in data["runs"]]
    json.dumps(data,allow_nan=False)


def test_equal_budget_includes_remainder_and_shared_cost(x_run):
    data=equal_budget_study(x_run,factor_sets=[[1,3,5]],total_shots=13,repetitions=2)
    assert {r["shots_per_method"] for r in data["rows"]}=={13}
    for run in data["runs"]:
        baseline=[s for s in run["samples"] if s["role"]=="baseline"]
        zne=[s for s in run["samples"] if s["role"]=="zne"]
        assert baseline[0]["shots"]==13
        assert [s["shots"] for s in zne]==[5,4,4]
        assert sum(sum(s["counts"].values()) for s in zne)==13
    assert data["provenance"]["actual_shots"]==52


def test_heatmap_reference_configs_and_no_mutation():
    exp=run_experiment(replace(create_example_config("spin-oscillation"),shots=32))
    data=heatmap_study(exp,x_values=[1,3],y_values=[0,.1])
    assert len(data["rows"])==len(data["runs"])==4
    assert {(r["x"],r["y"]) for r in data["rows"]}=={(1.,0.),(3.,0.),(1.,.1),(3.,.1)}
    for row,run in zip(data["rows"],data["runs"]):
        assert run["config"]["protocol"]["trotter_steps"]==row["x"]
        assert run["config"]["noise"]["p2"]==row["y"]
        assert run["metadata"]["versions"]
        assert row["fidelity_exact"] is not None
    assert exp.config.protocol.trotter_steps==create_example_config("spin-oscillation").protocol.trotter_steps


def test_invalid_heatmap_is_validated_before_any_execution(monkeypatch):
    exp=run_experiment(replace(create_example_config("bell"),shots=8))
    monkeypatch.setattr("core.research.run_experiment",lambda *a,**k:pytest.fail("Simulation started before validation"))
    for kwargs in ({"x_values":[1,300],"y_values":[.1]}, {"x_parameter":"p1","y_parameter":"t1_us"}, {"x_values":[1,1]}):
        with pytest.raises(ValueError):
            heatmap_study(exp,**kwargs)


@pytest.mark.parametrize("kwargs",[{"repetitions":1},{"repetitions":11},{"factor_sets":[[1,2,3]]},{"shot_counts":[0]},{"qubit":4},{"seed":2**32}])
def test_sampling_rejects_invalid_inputs(x_run,kwargs):
    with pytest.raises(ValueError):
        zne_stability(x_run,**kwargs)


def test_studies_cancel_before_acquisition(x_run):
    for callback in (zne_stability,equal_budget_study):
        with pytest.raises(SimulationCancelled):
            callback(x_run,is_cancelled=lambda:True)


def test_studies_freeze_new_seed_when_legacy_source_has_no_seed():
    from core.study import trotter_noise_study
    source=run_experiment(replace(create_example_config("bell"),seed=None,shots=32))
    source.result.metadata.pop("effective_seed")
    for callback,options in ((heatmap_study,{"x_values":[1],"y_values":[.01]}),(trotter_noise_study,{"steps":[1]})):
        result=callback(source,**options)
        assert type(result["options"]["seed"]) is int
        replay=callback(source,**result["options"])
        assert [r["counts"] for r in result["runs"]]==[r["counts"] for r in replay["runs"]]

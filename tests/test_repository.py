from dataclasses import replace,asdict
from pathlib import Path
import json,zipfile
import numpy as np
import pytest
from qiskit.quantum_info import Statevector
from core.simulation import run_experiment
from core.types import *
from core.examples import create_example_config
from core.export import export_experiment_json,import_experiment_json,export_run_bundle
from data.repository import ExperimentRepository

@pytest.mark.parametrize("noisy",[False,True])
def test_state_roundtrip(tmp_path,noisy):
    cfg=replace(create_example_config("bell"),shots=64,noise=NoiseConfig(enabled=noisy))
    exp=run_experiment(cfg)
    repo=ExperimentRepository(tmp_path)
    repo.save(exp)
    loaded=ExperimentRepository(tmp_path).load(exp.id)
    assert loaded.config==exp.config
    assert loaded.result.counts==exp.result.counts
    np.testing.assert_allclose(loaded.result.final_state.data,exp.result.final_state.data)
    np.testing.assert_allclose(loaded.result.states[-1].data,exp.result.states[-1].data)
    assert loaded.result.metadata==exp.result.metadata
def test_export_import_json_and_bundle(tmp_path):
    exp=run_experiment(replace(create_example_config("bell"),shots=64))
    path=export_experiment_json(exp,tmp_path/"run.json")
    loaded=import_experiment_json(path)
    assert loaded.config==exp.config
    np.testing.assert_allclose(loaded.result.final_state.data,exp.result.final_state.data)
    bundle=export_run_bundle(exp,tmp_path/"run.zip")
    with zipfile.ZipFile(bundle) as z:
        assert z.testzip() is None
        assert set(z.namelist())=={"experimento.json","contagens.csv","circuito.txt"}
        assert json.loads(z.read("experimento.json"))["id"]==exp.id
def test_legacy_preserved(tmp_path):
    cfg=asdict(create_example_config("bell"))
    del cfg["system"]["initial_state"]
    del cfg["protocol"]["trotter_order"]
    raw=dict(config=cfg,result={"counts":{"00":4096},"statevectors":None},
             id="legacy",created_at="2025-01-01T12:00:00")
    path=tmp_path/"legacy.json"
    original=json.dumps(raw)
    path.write_text(original)
    loaded=ExperimentRepository(tmp_path).load("legacy")
    assert loaded.config.system.initial_state=="zero"
    assert path.read_text()==original
def test_corruption_reported_without_deleting(tmp_path):
    repo=ExperimentRepository(tmp_path)
    path=tmp_path/"broken.json"
    path.write_text("{broken")
    assert repo.list_all()==[]
    assert len(repo.load_errors)==1
    assert path.read_text()=="{broken"
def test_atomic_write_failure_keeps_record(tmp_path,monkeypatch):
    exp=run_experiment(replace(create_example_config("first-qubit"),shots=64))
    repo=ExperimentRepository(tmp_path)
    path=repo.save(exp)
    original=path.read_bytes()
    def fail(*args):raise OSError("disk full")
    monkeypatch.setattr(Path,"replace",fail)
    with pytest.raises(OSError):repo.save(exp)
    assert path.read_bytes()==original
    assert not list(tmp_path.glob("*.tmp"))
@pytest.mark.parametrize("identifier",["../x","/tmp/x","","..","a/b"])
def test_path_traversal_rejected(tmp_path,identifier):
    with pytest.raises(ValueError):ExperimentRepository(tmp_path).load(identifier)
def test_bad_schema_and_dimensions_rejected(tmp_path):
    exp=run_experiment(replace(create_example_config("first-qubit"),shots=64))
    repo=ExperimentRepository(tmp_path)
    raw=repo._serialize(exp)
    raw["schema_version"]=99
    with pytest.raises(ValueError):repo._deserialize(raw)
    exp.result.final_state=Statevector([1,0,0,0])
    with pytest.raises(ValueError):repo.save(exp)
@pytest.mark.parametrize("text",["{}","[]","null",'{"schema_version":99}'])
def test_invalid_import_is_friendly(tmp_path,text):
    path=tmp_path/"bad.json"
    path.write_text(text)
    with pytest.raises(ValueError):import_experiment_json(path)

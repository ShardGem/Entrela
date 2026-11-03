from dataclasses import replace
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json
import zipfile
import numpy as np
from PIL import Image
import pytest
from core.examples import create_example_config
from core.simulation import run_experiment,SimulationCancelled
from core.research import heatmap_study
from core.documentation import export_animation,export_documentation,export_latex,animation_indices
from core.metrics import bloch_vector
from data.protocols import ProtocolRepository


@pytest.fixture
def run():
    return run_experiment(replace(create_example_config("bell"),shots=32))


def test_bloch_known_bell_and_product_states(run):
    np.testing.assert_allclose(bloch_vector(run.result.final_state,0),[0,0,0],atol=1e-12)
    other=run_experiment(replace(create_example_config("first-qubit"),shots=32))
    assert np.linalg.norm(bloch_vector(other.result.final_state,0))==pytest.approx(1)


def test_gif_has_actual_indices_timing_and_embedded_provenance(run,tmp_path):
    before=run.result.final_state.data.copy()
    path=tmp_path/"states.gif"
    export_animation([run],path,max_frames=3,frame_ms=200,frames_directory=tmp_path/"frames")
    with Image.open(path) as gif:
        assert gif.n_frames==3
        assert gif.info["duration"]==200
        assert "loop" not in gif.info
        metadata=json.loads(gif.info["comment"])
        assert metadata["indices"]==[0,2,4]
        assert metadata["source_ids"]==[run.id]
        assert metadata["times"]==[run.result.times[i] for i in [0,2,4]]
        assert sorted(p.name for p in (tmp_path/"frames").glob("*.png"))==metadata["frame_files"]
    np.testing.assert_array_equal(run.result.final_state.data,before)


def test_animation_rejects_missing_or_unsynchronized_states(run,tmp_path):
    other=run_experiment(replace(run.config,protocol=replace(run.config.protocol,save_snapshots=False)))
    with pytest.raises(ValueError,match="snapshots"):
        export_animation([other],tmp_path/"no.gif")
    with pytest.raises(ValueError,match="mesmos instantes"):
        animation_indices([run,other])


def test_complete_bundle_contains_traceable_science_and_rendered_assets(run,tmp_path):
    data=heatmap_study(run,x_values=[1],y_values=[0,.1])
    data.update(analysis_id="a123",protocol={"protocol_id":"p123","fields":{"title":"Estudo & dados","evidence_ref":"Tabela 4"}})
    path=tmp_path/"everything.zip"
    export_documentation([run],path,[data],annotations={run.id:{"title":"Bell"},"unrelated":{"notes":"Outra pesquisa"}},include_gif=False)
    with zipfile.ZipFile(path) as archive:
        manifest=json.loads(archive.read("manifest.json"))
        assert manifest["lineage"][0]["evidence_ref"]=="Tabela 4"
        assert manifest["lineage"][0]["analysis_id"]=="a123"
        assert manifest["source_ids"]==[run.id]
        assert set(manifest["annotations"])=={run.id}
        for entry in manifest["files"]:
            assert "\\" not in entry["path"]
            assert sha256(archive.read(entry["path"])).hexdigest()==entry["sha256"]
        assert archive.read("report.pdf").startswith(b"%PDF")
        assert json.loads(archive.read(f"run_{run.id}/experiment.json"))["id"]==run.id
        assert archive.read("analyses/analysis_001.tex")
        assert archive.read(f"run_{run.id}/bloch_final.svg").lstrip().startswith(b"<?xml")
        with Image.open(BytesIO(archive.read(f"run_{run.id}/bloch_final.png"))) as image:
            assert image.width>400
        assert archive.read(f"run_{run.id}/bloch.csv").count(b"simulated")==10


def test_latex_escapes_external_text_and_preserves_source(run,tmp_path):
    data={"kind":"sweep","source_id":run.id,"analysis_id":"a_1","rows":[{"value":.02,"fidelity":.999999999}],"note":"50% & correct_1","protocol":{"fields":{"title":r"Text \input{bad}"}}}
    path=export_latex(data,tmp_path/"table.tex")
    text=path.read_text()
    assert run.id in text
    assert r"\input{bad}" not in text
    assert r"50\% \& correct\_1" in text
    assert "linha 1 do JSON" in text
    assert r"\label{tab:entrela-a-1}" in text


def test_protocol_revisions_are_immutable_and_reload_configuration(run,tmp_path):
    repository=ProtocolRepository(tmp_path)
    fields={"title":"Bell","question":"Ruído?","hypothesis":"Perde pureza","controls":"Mesmo Hamiltoniano","evidence_ref":"Fig. 4.1"}
    a=repository.save(run,"heatmap",{"x_values":[1,2]},fields)
    first=(tmp_path/(a["protocol_id"]+".json")).read_bytes()
    b=repository.save(run,"heatmap",{"x_values":[1,3]},fields)
    assert a["protocol_id"]!=b["protocol_id"]
    assert repository.load(a["protocol_id"])["config"]["seed"]==run.result.metadata["effective_seed"]
    assert (tmp_path/(a["protocol_id"]+".json")).read_bytes()==first
    assert len(repository.list_all())==2
    with pytest.raises(ValueError):
        repository.load("../../outside")


def test_cancelling_export_preserves_existing_destination(run,tmp_path):
    path=tmp_path/"existing.zip"
    path.write_bytes(b"previous")
    with pytest.raises(SimulationCancelled):
        export_documentation([run],path,is_cancelled=lambda:True)
    assert path.read_bytes()==b"previous"
    assert list(tmp_path.iterdir())==[path]

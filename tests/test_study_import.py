"""A complete portable study is verified before touching the local workspace."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest

from core.analysis import temporal_analysis
from core.examples import create_example_config
from core.export import export_run_bundle
from core.simulation import run_experiment, SimulationCancelled
from data.repository import ExperimentRepository
from data.protocols import ProtocolRepository
from data.workspace import WorkspaceLibrary
from data.analyses import load_analysis
from data.study_package import prepare_study_import
from tests.qt_helpers import wait_until


@pytest.fixture
def portable(tmp_path):
    a = run_experiment(replace(create_example_config("bell"),shots=32))
    b = run_experiment(replace(a.config,seed=43))
    b.result.metadata["reproduced_from_id"] = a.id
    analysis = temporal_analysis(a)
    analysis["analysis_id"] = "a"*32
    protocol = ProtocolRepository(tmp_path/"protocol-source").save(a,"temporal",{},dict(title="Hipótese Bell",question="Como evolui a pureza?"))
    analysis["protocol"] = dict(protocol_id=protocol["protocol_id"],fields=protocol["fields"])
    contents = {f"run_{source.id}/experiment.json":json.dumps(ExperimentRepository._serialize(source)).encode() for source in (a,b)}
    contents["analyses/analysis_001.json"] = json.dumps(analysis).encode()
    contents["protocols.json"] = json.dumps([protocol]).encode()
    contents["report.pdf"] = b"preserved report bytes"
    manifest = dict(schema_version=1,kind="documentation",source_ids=[a.id,b.id],
                    annotations={a.id:dict(title="Bell da pesquisa",project="TCC",hypothesis="Estado global puro")},
                    files=[dict(path=name,bytes=len(value),sha256=sha256(value).hexdigest()) for name,value in contents.items()])
    contents["manifest.json"] = json.dumps(manifest).encode()
    path = tmp_path/"study.zip"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as archive:
        for name,value in contents.items():
            archive.writestr(name,value)
    return path,a,b,contents


def test_complete_import_preserves_results_and_restores_links(portable,tmp_path):
    path,a,b,_ = portable
    repo = ExperimentRepository(tmp_path/"destination")
    repo.save(a)
    before = repo._path(a.id).read_bytes()
    plan = prepare_study_import(path,repo)
    assert len(repo.list_summaries()) == 1
    imported = plan.commit()
    copied_a,copied_b = imported
    assert {copied_a.id,copied_b.id}.isdisjoint({a.id,b.id})
    assert copied_b.result.metadata["reproduced_from_id"] == copied_a.id
    assert copied_a.result.metadata["imported_from_id"] == a.id
    np.testing.assert_array_equal(repo.load(copied_a.id).result.final_state.data,a.result.final_state.data)
    assert copied_a.result.counts == a.result.counts
    assert repo._path(a.id).read_bytes() == before
    annotation = WorkspaceLibrary(repo.base_dir/".workspace").read()["annotations"][copied_a.id]
    assert annotation["title"] == "Bell da pesquisa" and annotation["hypothesis"] == "Estado global puro"
    analysis_path = next((repo.base_dir/".analyses"/copied_a.id).glob("*.json"))
    analysis = load_analysis(analysis_path,copied_a.id)
    protocol = ProtocolRepository(repo.base_dir/".protocols").list_all()[0]
    assert analysis["protocol"]["protocol_id"] == protocol["protocol_id"]
    assert protocol["source_id"] == copied_a.id
    evidence = next((repo.base_dir/".imports").glob("*/original.zip"))
    assert evidence.read_bytes() == path.read_bytes()


def test_tampered_archive_or_unsafe_paths_never_modify_workspace(portable,tmp_path):
    path,_,_,contents = portable
    repo = ExperimentRepository(tmp_path/"untouched")
    original = dict(contents)
    contents["report.pdf"] = b"altered bytes"
    with zipfile.ZipFile(path,"w") as archive:
        for name,value in contents.items():
            archive.writestr(name,value)
    with pytest.raises(ValueError,match="Tamanho|SHA-256"):
        prepare_study_import(path,repo)
    assert not list(repo.base_dir.iterdir())
    with zipfile.ZipFile(path,"w") as archive:
        for name,value in original.items():
            archive.writestr(name,value)
        archive.writestr("../outside.json",b"unsafe")
    with pytest.raises(ValueError,match="inseguro"):
        prepare_study_import(path,repo)
    assert not list(repo.base_dir.iterdir())


def test_import_rolls_back_on_write_failure_and_cancellation(portable,tmp_path,monkeypatch):
    path,a,_,_ = portable
    repo = ExperimentRepository(tmp_path/"rollback")
    repo.save(a)
    before = repo._path(a.id).read_bytes()
    plan = prepare_study_import(path,repo)
    monkeypatch.setattr(WorkspaceLibrary,"_write",lambda *args: (_ for _ in ()).throw(OSError("disco cheio")))
    with pytest.raises(OSError):
        plan.commit()
    assert [record.id for record in repo.list_summaries()] == [a.id]
    assert repo._path(a.id).read_bytes() == before
    assert not list(repo.base_dir.rglob("original.zip"))
    with pytest.raises(SimulationCancelled):
        prepare_study_import(path,repo,is_cancelled=lambda: True)
    assert not list(repo.base_dir.glob(".study-import-*"))


def test_compact_run_bundle_roundtrips_with_verified_manifest(portable,tmp_path):
    _,source,_,_ = portable
    path = export_run_bundle(source,tmp_path/"compact.zip",dict(title="Nome portátil"))
    repo = ExperimentRepository(tmp_path/"compact-destination")
    copied = prepare_study_import(path,repo).commit()[0]
    assert copied.result.counts == source.result.counts
    assert WorkspaceLibrary(repo.base_dir/".workspace").read()["annotations"][copied.id]["title"] == "Nome portátil"


def test_import_worker_connects_to_history_and_reproduction(window,portable):
    path,source,_,_ = portable
    previous = run_experiment(replace(source.config,seed=99))
    window.repository.save(previous)
    window._refresh_history()
    window.page_history.set_detail(previous)
    window._start_study_import(path)
    wait_until(lambda: window._current_worker is None)
    copied = window._current_experiment
    assert copied is not None and copied.id != source.id
    assert len(window.repository.list_summaries()) == 3
    assert window.page_history.selected_identifier == copied.id
    assert window.page_library.run_title.text() == "Bell da pesquisa"
    assert window.page_analysis.saved.count() == 2
    window._rerun_current()
    wait_until(lambda: window._current_worker is None)
    assert window._current_experiment.result.metadata["reproduction_check"]["status"] == "matched"


def test_real_documentation_export_is_portable_without_manual_repacking(portable,tmp_path):
    from core.documentation import export_documentation
    from core.pdf_layout import REPORT_SECTIONS
    _,source,_,_ = portable
    analysis = temporal_analysis(source)
    analysis["analysis_id"] = "b"*32
    path = export_documentation([source],tmp_path/"real-export.zip",analyses=[analysis],
        annotations={source.id:dict(title="Exportação real",notes="Dados de validação do software")},
        include_gif=False,report_options={key:False for key in REPORT_SECTIONS},raster_dpi=150)
    repo = ExperimentRepository(tmp_path/"real-destination")
    copied = prepare_study_import(path,repo).commit()[0]
    assert copied.result.counts == source.result.counts
    assert len(list((repo.base_dir/".analyses"/copied.id).glob("*.json"))) == 1
    assert WorkspaceLibrary(repo.base_dir/".workspace").read()["annotations"][copied.id]["title"] == "Exportação real"


def test_import_failure_is_not_saved_as_failed_scientific_experiment(window,portable,tmp_path):
    corrupt = tmp_path/"corrupt.zip"
    corrupt.write_bytes(b"not a zip")
    window._start_study_import(corrupt)
    wait_until(lambda: window._current_worker is None)
    assert not window.repository.list_summaries()
    assert window._current_experiment is None
    assert "Não foi possível" in window.page_documentation.message.text()


def test_legacy_protocol_defaults_are_normalized_without_rewriting_file(portable,tmp_path):
    _,source,_,_ = portable
    repository = ProtocolRepository(tmp_path/"legacy-protocols")
    protocol = repository.save(source,"temporal",{},dict(title="Legado"))
    path = repository.directory/(protocol["protocol_id"]+".json")
    raw = json.loads(path.read_text())
    raw["config"]["noise"].pop("gate_time_1q_ns")
    raw["config"]["noise"].pop("gate_time_2q_ns")
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    restored = repository.load(protocol["protocol_id"])
    assert restored["config"]["noise"]["gate_time_1q_ns"] == 50
    assert path.read_bytes() == before

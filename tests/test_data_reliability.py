"""Derived history failures must not hide data or lose concurrent notes."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from core.examples import create_example_config
from core.simulation import run_experiment
from data.file_lock import FileLockTimeout, directory_lock
from data.repository import ExperimentRepository
from data.workspace import WorkspaceLibrary


@pytest.fixture(scope="module")
def experiment():
    return run_experiment(replace(create_example_config("bell"), shots=64))


@pytest.mark.parametrize("corruption", [
    "list", "null", "text", "payload_list", "schema", "id", "result",
    "counts", "states", "config", "created_at", "duration",
])
def test_corrupt_matching_summary_is_rebuilt_from_intact_source(tmp_path, experiment, corruption, monkeypatch):
    repository = ExperimentRepository(tmp_path)
    source = repository.save(experiment)
    before = source.read_bytes()
    cache = tmp_path / ".summaries" / source.name
    original = json.loads(cache.read_text(encoding="utf-8"))
    raw = deepcopy(original)
    if corruption == "list":
        raw = []
    elif corruption == "null":
        raw = None
    elif corruption == "text":
        raw = "cache inválido"
    elif corruption == "payload_list":
        raw["experiment"] = []
    else:
        payload = raw["experiment"]
        if corruption == "schema":
            payload["schema_version"] = 100
        elif corruption == "id":
            payload["id"] = "outro"
        elif corruption == "result":
            payload["result"] = []
        elif corruption == "counts":
            payload["result"]["counts"] = {"00": 1}
        elif corruption == "states":
            payload["result"]["statevectors"] = [{"inválido": True}]
        elif corruption == "config":
            payload["config"] = None
        elif corruption == "created_at":
            payload["created_at"] = "data inválida"
        elif corruption == "duration":
            payload["duration_s"] = -1
    cache.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr("data.repository.decode_state", lambda _: pytest.fail("O histórico não deve decodificar estados"))
    records = repository.list_summaries()
    assert [record.id for record in records] == [experiment.id]
    assert records[0].result.fidelity == experiment.result.fidelity
    assert repository.load_errors == []
    assert source.read_bytes() == before
    assert json.loads(cache.read_text(encoding="utf-8")) == original


def test_bad_summary_does_not_hide_real_source_error(tmp_path, experiment):
    repository = ExperimentRepository(tmp_path)
    source = repository.save(experiment)
    (tmp_path / ".summaries" / source.name).write_text("[]", encoding="utf-8")
    original = json.loads(source.read_text(encoding="utf-8"))
    original["result"]["metadata"] = None
    source.write_text(json.dumps(original), encoding="utf-8")
    before = source.read_bytes()
    assert repository.list_summaries() == []
    assert len(repository.load_errors) == 1
    assert "metadados" in repository.load_errors[0]
    assert source.read_bytes() == before


def test_concurrent_library_instances_preserve_independent_updates(tmp_path):
    start = threading.Barrier(8)

    def annotate(index):
        library = WorkspaceLibrary(tmp_path)
        start.wait(timeout=10)
        for count in range(4):
            library.annotate(f"execucao-{index}-{count}", "TCC", f"Nota {index}", ["base"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(annotate, range(8)))
    raw = WorkspaceLibrary(tmp_path).read()
    assert len(raw["annotations"]) == 32
    assert raw["projects"] == {"TCC": {"description": ""}}


def test_nested_transactions_share_document_and_roll_back_on_failure(tmp_path):
    first, second = WorkspaceLibrary(tmp_path), WorkspaceLibrary(tmp_path)
    with first.transaction() as document:
        document["projects"]["Antes"] = {"description": ""}
        second.annotate("execucao", "Depois", "Aninhada", [])
    assert set(first.read()["projects"]) == {"Antes", "Depois"}
    before = first.path.read_bytes()
    with pytest.raises(RuntimeError):
        with first.transaction() as document:
            second.annotate("outra", "Outro", "Não salvar", [])
            document["templates"].clear()
            raise RuntimeError("abortar")
    assert first.path.read_bytes() == before
    second.annotate("apos-falha", "Outro", "Salvar", [])
    assert "apos-falha" in first.read()["annotations"]


def test_directory_lock_is_reentrant_and_other_threads_have_clear_timeout(tmp_path):
    with directory_lock(tmp_path):
        with directory_lock(tmp_path, timeout=0):
            def contender():
                with pytest.raises(FileLockTimeout, match="em uso"):
                    with directory_lock(tmp_path, timeout=0.03):
                        pytest.fail("O bloqueio de outra thread foi ignorado")
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(contender).result(timeout=5)
    with directory_lock(tmp_path, timeout=0):
        pass


def test_subprocess_transactions_serialize_and_timeout_without_losing_updates(tmp_path):
    # Separate interpreters exercise the OS lock, beyond the in-process RLock.
    script = """
import sys, time
from data.workspace import WorkspaceLibrary
library = WorkspaceLibrary(sys.argv[1], lock_timeout=3)
with library.transaction() as raw:
    print('locked', flush=True)
    time.sleep(0.25)
    raw['projects'][sys.argv[2]] = {'description': ''}
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    first = subprocess.Popen([sys.executable, "-c", script, str(tmp_path), "Primeiro"], env=environment,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    second = None
    try:
        assert first.stdout.readline().strip() == "locked"
        with pytest.raises(FileLockTimeout, match="em uso"):
            WorkspaceLibrary(tmp_path, lock_timeout=0.03).annotate("x", "TCC", "Não gravar", [])
        second = subprocess.Popen([sys.executable, "-c", script, str(tmp_path), "Segundo"], env=environment,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert first.communicate(timeout=20)[1] == ""
        assert first.returncode == 0
        assert second.communicate(timeout=20)[1] == ""
        assert second.returncode == 0
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()
    raw = WorkspaceLibrary(tmp_path).read()
    assert set(raw["projects"]) == {"Primeiro", "Segundo"}
    assert raw["annotations"] == {}

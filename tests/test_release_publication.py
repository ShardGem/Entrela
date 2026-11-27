"""Publicação parcial não deve perder arquivos nem divulgar um pacote inválido."""
import hashlib
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts import publish_release


@pytest.fixture
def assets(tmp_path):
    names = ["Entrela-0.27.0-windows-x64-setup.exe", "Entrela-0.27.0-windows-x64-portatil.zip"]
    hashes = []
    for name in names:
        content = name.encode()
        (tmp_path / name).write_bytes(content)
        hashes.append(f"{hashlib.sha256(content).hexdigest()}  {name}")
    (tmp_path / "SHA256SUMS.txt").write_text("\n".join(hashes), encoding="utf-8")
    (tmp_path / "dependencias-build.txt").write_text("PySide6==6.10.2", encoding="utf-8")
    receipt = dict(success=True, frozen=True, version="0.27.0", qt_platform="windows", checks=list(range(7)))
    for name in ["verificacao-portatil.json", "verificacao-instalado.json"]:
        (tmp_path / name).write_text(json.dumps(receipt), encoding="utf-8")
    (tmp_path / "verificacao-instalado.log").touch()
    return tmp_path


def test_empty_diagnostic_is_not_a_release_asset(assets):
    files = publish_release.validated_assets(assets, "v0.27.0")
    assert len(files) == 6
    assert all(path.stat().st_size > 0 for path in files)
    assert "verificacao-instalado.log" not in {path.name for path in files}


@pytest.mark.parametrize("change", ["missing", "empty", "hash", "receipt", "version", "platform"])
def test_invalid_package_is_rejected_before_contacting_github(assets, monkeypatch, change):
    if change == "missing":
        (assets / "dependencias-build.txt").unlink()
    elif change == "empty":
        (assets / "Entrela-0.27.0-windows-x64-setup.exe").write_bytes(b"")
    elif change == "hash":
        (assets / "Entrela-0.27.0-windows-x64-portatil.zip").write_bytes(b"corrompido")
    else:
        path = assets / "verificacao-instalado.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt[{"receipt": "success", "version": "version", "platform": "qt_platform"}[change]] = {
            "receipt": False, "version": "0.26.0", "platform": "offscreen"}[change]
        path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(publish_release.subprocess, "run", lambda *a, **kw: pytest.fail("GitHub não deveria ser chamado"))
    with pytest.raises(ValueError):
        publish_release.publish(assets, "v0.27.0", "ShardGem/Entrela", Path("notes.md"))


@pytest.mark.parametrize("state", ["draft", "missing", "published", "denied"])
def test_resume_uploads_only_to_draft_and_publishes_last(assets, monkeypatch, state):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command[2] == "view":
            if state in {"missing", "denied"}:
                return CompletedProcess(command, 1, "", "release not found" if state == "missing" else "HTTP 403")
            return CompletedProcess(command, 0, json.dumps(dict(isDraft=state == "draft", tagName="v0.27.0")), "")
        return CompletedProcess(command, 0)

    monkeypatch.setattr(publish_release.subprocess, "run", run)
    if state == "denied":
        with pytest.raises(RuntimeError, match="403"):
            publish_release.publish(assets, "v0.27.0", "ShardGem/Entrela", Path("notes.md"))
        assert len(commands) == 1
        return
    publish_release.publish(assets, "v0.27.0", "ShardGem/Entrela", Path("notes.md"))
    assert [command[2] for command in commands] == {
        "draft": ["view", "upload", "edit"],
        "missing": ["view", "create", "upload", "edit"],
        "published": ["view"],
    }[state]
    for command in commands:
        if command[2] == "upload":
            assert "--clobber" in command
            assert not any(value.endswith(".log") for value in command)
    if state != "published":
        assert "--draft=false" in commands[-1]

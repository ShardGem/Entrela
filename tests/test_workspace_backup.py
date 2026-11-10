"""Workspace transport preserves source bytes; it does not certify the science."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import stat
import zipfile

import pytest

from core.examples import create_example_config
from core.simulation import SimulationCancelled, run_experiment
from data.repository import ExperimentRepository
from data.workspace import WorkspaceLibrary
from data.workspace_backup import create_workspace_backup, prepare_workspace_restore


@pytest.fixture(scope="module")
def bell_experiment():
    return run_experiment(replace(create_example_config("bell"), shots=32, seed=42))


@pytest.fixture
def workspace(tmp_path, bell_experiment):
    root = tmp_path / "Laboratório original"
    repository = ExperimentRepository(root)
    repository.save(bell_experiment)
    library = WorkspaceLibrary(root / ".workspace")
    library.save_template("Bell de referência", bell_experiment.config)
    library.annotate(bell_experiment.id, "TCC", "Hipótese e discussão", ["Bell"], title="Controle ideal")
    content = {
        ".circuits/revisao.json": b'{"circuit_id":"persistent-id","revision":2}',
        ".protocols/protocolo.json": b'{"protocol_id":"unchanged-id"}',
        ".analyses/resultado.json": b'{"source_id":"preserved-as-recorded"}',
        ".workspace/drafts.json": 'Rascunho: não descartar'.encode("utf-8"),
        # Broken source evidence must still be recoverable byte for byte.
        "corrompido.json": b'\xff{"incomplete":',
    }
    for relative, data in content.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "figuras vazias").mkdir()
    return root


def source_bytes(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file() and path.name != ".entrela.lock"}


def rewrite_archive(path, *, alter_members=None, alter_manifest=None, additions=()):
    """Create deliberately damaged transport independently of the reader."""
    with zipfile.ZipFile(path) as archive:
        members = {entry.filename: archive.read(entry.filename) for entry in archive.infolist()}
    if alter_manifest:
        manifest = json.loads(members["manifest.json"])
        alter_manifest(manifest)
        members["manifest.json"] = json.dumps(manifest).encode("utf-8")
    if alter_members:
        alter_members(members)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
        for name, data in additions:
            archive.writestr(name, data)


def test_roundtrip_preserves_records_ids_preferences_and_even_corrupt_sources(tmp_path, workspace, bell_experiment):
    before = source_bytes(workspace)
    preferences = {"appearance/theme": "light", "shots": 64, "bloch/loop": False,
                   "workspace/draft": '{"nota":"Superposição"}', "optional": None}
    original_preferences = deepcopy(preferences)
    archive = tmp_path / "backup.zip"
    progress = []
    assert create_workspace_backup(workspace, archive, preferences, progress=progress.append) == archive
    assert progress[0] == 0 and progress[-1] == 100
    assert progress == sorted(progress)
    assert preferences == original_preferences
    target = tmp_path / "Restaurado"
    prepared = prepare_workspace_restore(archive, target)
    assert not target.exists()
    assert prepared.preview.files == len(before)
    assert prepared.preview.experiments == 2  # JSON files, not certified valid experiments.
    assert prepared.preview.categories["circuits"] == 1
    assert prepared.preview.categories["analyses"] == 1
    assert prepared.preview.categories["protocols"] == 1
    assert prepared.preview.has_preferences
    assert prepared.preview.target_dir == target
    assert "arquivos" in prepared.preview.summary
    returned = prepared.commit()
    assert returned == original_preferences
    returned["shots"] = 1
    assert prepared.preferences["shots"] == 64
    assert source_bytes(target) == before
    assert (target / "figuras vazias").is_dir()
    restored = ExperimentRepository(target)
    experiment = restored.load(bell_experiment.id)
    assert experiment.id == bell_experiment.id
    assert experiment.config == bell_experiment.config
    assert experiment.result.counts == bell_experiment.result.counts
    assert experiment.result.fidelity == bell_experiment.result.fidelity
    assert len(restored.list_summaries()) == 1
    assert len(restored.load_errors) == 1  # Transport integrity is not source validity.
    assert source_bytes(workspace) == before
    assert not list(tmp_path.glob(".entrela-restore-*"))
    with pytest.raises(ValueError, match="concluída|descartada"):
        prepared.commit()


def test_backup_excludes_transient_locks_and_staging_but_keeps_empty_folders(tmp_path, workspace):
    for name in (".study-import-pending", ".entrela-restore-pending"):
        folder = workspace / name
        folder.mkdir()
        (folder / "partial").write_bytes(b"not committed")
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    with zipfile.ZipFile(archive) as stored:
        names = stored.namelist()
        assert not any(".entrela.lock" in name or "pending" in name for name in names)
        manifest = json.loads(stored.read("manifest.json"))
        assert "figuras vazias" in manifest["directories"]
    prepared = prepare_workspace_restore(archive, tmp_path / "restored")
    try:
        assert not prepared.preview.has_preferences
    finally:
        prepared.abort()


@pytest.mark.parametrize("relative", ["corrompido.json", ".workspace/workspace.json", "novo.zip"])
def test_internal_backup_destination_is_rejected_without_changing_sources(workspace, relative):
    before = source_bytes(workspace)
    with pytest.raises(ValueError, match="fora da pasta"):
        create_workspace_backup(workspace, workspace / relative, {})
    assert source_bytes(workspace) == before


def test_backup_cancellation_preserves_existing_archive_and_cleans_temporary_files(tmp_path, workspace):
    archive = tmp_path / "backup.zip"
    archive.write_bytes(b"previous backup remains")
    before = source_bytes(workspace)
    cancelled = False

    def progress(value):
        nonlocal cancelled
        if value > 0:
            cancelled = True

    with pytest.raises(SimulationCancelled):
        create_workspace_backup(workspace, archive, {}, progress=progress, is_cancelled=lambda: cancelled)
    assert archive.read_bytes() == b"previous backup remains"
    assert source_bytes(workspace) == before
    assert not list(tmp_path.glob(".entrela-backup-*.tmp"))


def test_restore_cancellation_preserves_target_and_cleans_staging(tmp_path, workspace):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep").write_bytes(b"important previous data")
    cancelled = False

    def progress(value):
        nonlocal cancelled
        if value > 0:
            cancelled = True

    with pytest.raises(SimulationCancelled):
        prepare_workspace_restore(archive, target, progress=progress, is_cancelled=lambda: cancelled)
    assert source_bytes(target) == {"keep": b"important previous data"}
    assert not list(tmp_path.glob(".entrela-restore-*"))


def test_abort_and_replacement_require_explicit_confirmation(tmp_path, workspace):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {"theme": "dark"})
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep").write_bytes(b"old")
    prepared = prepare_workspace_restore(archive, target)
    assert prepared.preview.target_exists
    with pytest.raises(FileExistsError, match="Confirme"):
        prepared.commit()
    assert source_bytes(target) == {"keep": b"old"}
    prepared.abort()
    prepared.abort()  # Closing an already dismissed preview is harmless.
    assert source_bytes(target) == {"keep": b"old"}
    assert not list(tmp_path.glob(".entrela-restore-*"))
    prepared = prepare_workspace_restore(archive, target)
    assert prepared.commit(replace_existing=True) == {"theme": "dark"}
    assert "keep" not in source_bytes(target)
    assert source_bytes(target) == source_bytes(workspace)


def test_restore_rejects_target_replaced_since_preview(tmp_path, workspace):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep").write_bytes(b"original")
    prepared = prepare_workspace_restore(archive, target)
    target.rename(tmp_path / "previous-target")
    target.mkdir()
    (target / "new").write_bytes(b"new identity")
    try:
        with pytest.raises(ValueError, match="destino mudou"):
            prepared.commit(replace_existing=True)
        assert source_bytes(target) == {"new": b"new identity"}
        assert source_bytes(tmp_path / "previous-target") == {"keep": b"original"}
    finally:
        prepared.abort()


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_install_rolls_back_or_preserves_recovery_copy(tmp_path, workspace, monkeypatch, rollback_fails):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep").write_bytes(b"original")
    prepared = prepare_workspace_restore(archive, target)
    replace_path = Path.replace
    operations = []

    def fail_install(path, destination):
        if Path(destination) == target:
            operations.append(path.name)
            if path.name == "workspace" or rollback_fails:
                raise OSError("injected rename failure")
        return replace_path(path, destination)

    monkeypatch.setattr(Path, "replace", fail_install)
    if rollback_fails:
        with pytest.raises(OSError, match="preservada em"):
            prepared.commit(replace_existing=True)
        recovery = prepared._stage_root / "previous"
        assert source_bytes(recovery) == {"keep": b"original"}
        with pytest.raises(OSError, match="preservada para recuperação"):
            prepared.abort()
        assert source_bytes(recovery) == {"keep": b"original"}
    else:
        with pytest.raises(OSError, match="injected"):
            prepared.commit(replace_existing=True)
        assert source_bytes(target) == {"keep": b"original"}
        prepared.abort()
        assert not list(tmp_path.glob(".entrela-restore-*"))
    assert operations == ["workspace", "previous"]


@pytest.mark.parametrize("corruption", ["file_hash", "preferences_hash", "undeclared", "missing",
                                         "manifest_kind", "manifest_version", "size", "case_alias"])
def test_damaged_archive_never_changes_existing_target(tmp_path, workspace, corruption):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {"theme": "dark"})
    if corruption == "file_hash":
        def tamper(members):
            key = next(name for name in members if name.startswith("workspace/"))
            value = members[key]
            members[key] = bytes([value[0] ^ 1]) + value[1:]
        rewrite_archive(archive, alter_members=tamper)
    elif corruption == "preferences_hash":
        rewrite_archive(archive, alter_members=lambda members: members.update({
            "preferences.json": members["preferences.json"].replace(b"dark", b"evil")
        }))
    elif corruption == "undeclared":
        rewrite_archive(archive, additions=[("workspace/extra", b"undeclared")])
    elif corruption == "missing":
        def remove(members):
            members.pop(next(name for name in members if name.startswith("workspace/")))
        rewrite_archive(archive, alter_members=remove)
    elif corruption == "manifest_kind":
        rewrite_archive(archive, alter_manifest=lambda manifest: manifest.update(kind="study_package"))
    elif corruption == "manifest_version":
        rewrite_archive(archive, alter_manifest=lambda manifest: manifest.update(schema_version=99))
    elif corruption == "size":
        def change_size(manifest):
            manifest["files"][next(iter(manifest["files"]))]["bytes"] += 1
        rewrite_archive(archive, alter_manifest=change_size)
    else:
        rewrite_archive(archive, additions=[("PREFERENCES.JSON", b"alias")])
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep").write_bytes(b"do not replace")
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        prepare_workspace_restore(archive, target)
    assert source_bytes(target) == {"keep": b"do not replace"}
    assert not list(tmp_path.glob(".entrela-restore-*"))


@pytest.mark.parametrize("name", ["../escaped", "/absolute", "workspace/../../escaped",
                                   r"workspace\escaped", "workspace/C:/file", "workspace/CON.txt"])
def test_archive_path_traversal_and_unsafe_windows_names_are_rejected(tmp_path, workspace, name):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    rewrite_archive(archive, additions=[(name, b"must not escape")])
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="Caminho inseguro"):
        prepare_workspace_restore(archive, target)
    assert not target.exists()
    assert not (tmp_path / "escaped").exists()
    assert not list(tmp_path.glob(".entrela-restore-*"))


def test_archive_symlink_is_rejected_before_installation(tmp_path, workspace):
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    link = zipfile.ZipInfo("workspace/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    rewrite_archive(archive, additions=[(link, b"../../outside")])
    with pytest.raises(ValueError, match="link|tipo inseguro"):
        prepare_workspace_restore(archive, tmp_path / "target")
    assert not list(tmp_path.glob(".entrela-restore-*"))


def test_source_and_destination_links_are_rejected_and_preserved(tmp_path, workspace):
    outside = tmp_path / "outside"
    outside.write_bytes(b"do not follow")
    link = workspace / "link"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Links simbólicos indisponíveis: {exc}")
    archive = tmp_path / "backup.zip"
    with pytest.raises(ValueError, match="links|regulares"):
        create_workspace_backup(workspace, archive, {})
    assert not archive.exists()
    assert link.is_symlink() and outside.read_bytes() == b"do not follow"
    link.unlink()
    archive.symlink_to(outside)
    with pytest.raises(ValueError, match="link simbólico"):
        create_workspace_backup(workspace, archive, {})
    assert archive.is_symlink() and outside.read_bytes() == b"do not follow"


def test_changes_while_copying_are_detected_without_replacing_previous_backup(tmp_path, workspace):
    archive = tmp_path / "backup.zip"
    archive.write_bytes(b"previous archive")
    changed = False

    def change_after_copy_started(value):
        nonlocal changed
        if value > 0 and not changed:
            changed = True
            (workspace / "new-evidence").write_bytes(b"created concurrently")

    with pytest.raises(ValueError, match="mudou durante"):
        create_workspace_backup(workspace, archive, {}, progress=change_after_copy_started)
    assert changed
    assert archive.read_bytes() == b"previous archive"
    assert (workspace / "new-evidence").read_bytes() == b"created concurrently"
    assert not list(tmp_path.glob(".entrela-backup-*.tmp"))


@pytest.mark.parametrize("limit", ["MAX_FILES", "MAX_TOTAL_BYTES", "MAX_PREFERENCES_BYTES"])
def test_backup_limits_leave_sources_and_previous_archive_intact(tmp_path, workspace, monkeypatch, limit):
    from data import workspace_backup
    archive = tmp_path / "backup.zip"
    archive.write_bytes(b"previous archive")
    before = source_bytes(workspace)
    monkeypatch.setattr(workspace_backup, limit, 1)
    with pytest.raises(ValueError, match="limite|excede"):
        create_workspace_backup(workspace, archive, {"theme": "dark"})
    assert archive.read_bytes() == b"previous archive"
    assert source_bytes(workspace) == before


def test_restore_limits_cleanup_staging_and_do_not_create_target(tmp_path, workspace, monkeypatch):
    from data import workspace_backup
    archive = create_workspace_backup(workspace, tmp_path / "backup.zip", {})
    monkeypatch.setattr(workspace_backup, "MAX_FILES", 1)
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="limites"):
        prepare_workspace_restore(archive, target)
    assert not target.exists()
    assert not list(tmp_path.glob(".entrela-restore-*"))


def test_empty_workspace_is_a_valid_backup(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    archive = create_workspace_backup(root, tmp_path / "backup.zip", {})
    prepared = prepare_workspace_restore(archive, tmp_path / "restored")
    assert prepared.preview.files == 0
    assert prepared.preview.total_bytes == 0
    prepared.commit()
    assert (tmp_path / "restored").is_dir()
    assert list((tmp_path / "restored").iterdir()) == []

"""Complete local workspace archives with verified staging and explicit restore.

Archives preserve source bytes, including records that need diagnosis. Hashes
verify transport integrity; they do not certify a scientific result. Callers
must pause simulations and other writes before backing up or restoring. The
local sidecar lock serializes these backup/restore operations; it is not a
multiuser synchronization service.
"""

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

from core.simulation import SimulationCancelled
from data.file_lock import directory_lock, file_lock


MAX_FILES = 20_000
MAX_TOTAL_BYTES = 2_000_000_000
MAX_ARCHIVE_BYTES = 2_000_000_000
MAX_MANIFEST_BYTES = 8_000_000
MAX_PREFERENCES_BYTES = 1_000_000
_BLOCK = 1_048_576
_TRANSIENT_PREFIXES = (".study-import-", ".entrela-restore-")
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def _checkpoint(progress, is_cancelled, value):
    if is_cancelled and is_cancelled():
        raise SimulationCancelled()
    if progress:
        progress(value)


def _relative_name(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Caminho inseguro no backup.")
    pure = PurePosixPath(value)
    if pure.is_absolute() or str(pure) != value or any(
        part in (".", "..") or part.endswith((".", " "))
        or part.split(".", 1)[0].casefold() in _RESERVED
        or any(ord(char) < 32 for char in part)
        for part in pure.parts
    ):
        raise ValueError("Caminho inseguro ou incompatível com Windows no backup.")
    return pure


def _json_bytes(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("Os metadados do backup devem conter valores JSON válidos.") from exc


def _json_load(data):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Chave JSON duplicada no backup.")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=object_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Número não finito no backup.")))
        _json_bytes(value)
        return value
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Metadados ilegíveis no backup.") from exc


def _workspace_root(path):
    path = Path(path).expanduser().absolute()
    if path.is_symlink() or path == path.parent:
        raise ValueError("Use uma pasta de trabalho regular, sem links simbólicos.")
    return path.resolve()


def _operation_lock(root):
    # Sibling of the root, so a directory swap cannot replace the lock itself.
    return file_lock(root.parent / f".{root.name}.entrela-backup.lock")


def _signature(information):
    return (information.st_dev, information.st_ino, information.st_size,
            information.st_mtime_ns, information.st_ctime_ns)


def _snapshot(root, excluded):
    files, directories, aliases = {}, [], set()
    for directory, subdirectories, names in os.walk(root, followlinks=False):
        current = Path(directory)
        subdirectories.sort()
        names.sort()
        kept = []
        for name in subdirectories:
            path = current / name
            if path.is_symlink():
                raise ValueError("O backup não aceita links simbólicos na pasta de trabalho.")
            if name.startswith(_TRANSIENT_PREFIXES):
                continue
            relative = path.relative_to(root).as_posix()
            _relative_name(relative)
            if relative.casefold() in aliases:
                raise ValueError("Há caminhos duplicados para sistemas sem distinção entre maiúsculas e minúsculas.")
            aliases.add(relative.casefold())
            directories.append(relative)
            kept.append(name)
        subdirectories[:] = kept
        for name in names:
            path = current / name
            if path in excluded or name == ".entrela.lock":
                continue
            information = path.lstat()
            if not stat.S_ISREG(information.st_mode):
                raise ValueError("O backup aceita apenas arquivos regulares, sem links ou dispositivos.")
            relative = path.relative_to(root).as_posix()
            _relative_name(relative)
            if relative.casefold() in aliases:
                raise ValueError("Há caminhos duplicados para sistemas sem distinção entre maiúsculas e minúsculas.")
            aliases.add(relative.casefold())
            files[relative] = _signature(information)
            if len(files) > MAX_FILES:
                raise ValueError(f"O backup excede o limite de {MAX_FILES} arquivos.")
    if sum(value[2] for value in files.values()) > MAX_TOTAL_BYTES:
        raise ValueError("A pasta de trabalho excede o limite de 2 GB do backup.")
    return files, sorted(directories)


def create_workspace_backup(base_dir, destination, preferences, *, progress=None, is_cancelled=None):
    """Write an atomic ZIP of the complete base directory and JSON preferences.

    Derived caches are included, and can be rebuilt normally after restoring.
    Only active import/staging folders and .entrela.lock files are excluded.
    The output archive must be outside the source directory to protect records
    and avoid recursively including previous backups.
    """
    root = _workspace_root(base_dir)
    if not root.is_dir():
        raise ValueError("A pasta de trabalho não existe.")
    if not isinstance(preferences, dict):
        raise ValueError("As preferências devem ser um objeto JSON.")
    preferences_data = _json_bytes(preferences)
    if len(preferences_data) > MAX_PREFERENCES_BYTES:
        raise ValueError("As preferências excedem 1 MB.")
    destination = Path(destination).expanduser().absolute()
    if destination.is_symlink():
        raise ValueError("O destino do backup não pode ser um link simbólico.")
    destination = destination.resolve()
    if destination == root or root in destination.parents:
        raise ValueError("Salve o backup fora da pasta de trabalho para preservar os dados originais.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with ExitStack() as locks:
            locks.enter_context(_operation_lock(root))
            if (root / ".workspace").is_dir():
                locks.enter_context(directory_lock(root / ".workspace"))
            _checkpoint(progress, is_cancelled, 0)
            descriptor, name = tempfile.mkstemp(prefix=".entrela-backup-", suffix=".tmp", dir=destination.parent)
            os.close(descriptor)
            temporary = Path(name)
            excluded = {destination, temporary}
            source_files, directories = _snapshot(root, excluded)
            if not source_files and not directories:
                # An empty workspace is still a valid, restorable backup.
                directories = []
            file_metadata = {}
            total = max(1, sum(item[2] for item in source_files.values()))
            copied = 0
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for relative, expected in sorted(source_files.items()):
                    _checkpoint(progress, is_cancelled, min(95, int(copied * 95 / total)))
                    path = root.joinpath(*PurePosixPath(relative).parts)
                    digest = sha256()
                    size = 0
                    with path.open("rb") as source, archive.open("workspace/" + relative, "w", force_zip64=True) as target:
                        if _signature(os.fstat(source.fileno())) != expected:
                            raise ValueError("A pasta de trabalho mudou durante o backup. Pause as gravações e tente novamente.")
                        while block := source.read(_BLOCK):
                            size += len(block)
                            copied += len(block)
                            if size > expected[2] or copied > MAX_TOTAL_BYTES:
                                raise ValueError("Um arquivo mudou de tamanho durante o backup.")
                            target.write(block)
                            digest.update(block)
                            _checkpoint(progress, is_cancelled, min(95, int(copied * 95 / total)))
                        if size != expected[2] or _signature(os.fstat(source.fileno())) != expected:
                            raise ValueError("Um arquivo mudou durante o backup. Pause as gravações e tente novamente.")
                    file_metadata[relative] = {"bytes": size, "sha256": digest.hexdigest()}
                after_files, after_directories = _snapshot(root, excluded)
                if source_files != after_files or directories != after_directories:
                    raise ValueError("A pasta de trabalho mudou durante o backup. Pause as gravações e tente novamente.")
                manifest = {
                    "kind": "workspace_backup", "schema_version": 1,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source_name": root.name, "files": file_metadata, "directories": directories,
                    "preferences": {"bytes": len(preferences_data), "sha256": sha256(preferences_data).hexdigest()},
                    "excluded": [".entrela.lock", ".study-import-*", ".entrela-restore-*"],
                }
                manifest_data = _json_bytes(manifest)
                if len(manifest_data) > MAX_MANIFEST_BYTES:
                    raise ValueError("O manifesto excede 8 MB.")
                archive.writestr("preferences.json", preferences_data)
                archive.writestr("manifest.json", manifest_data)
            if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
                raise ValueError("O arquivo de backup excede o limite de 2 GB.")
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            _checkpoint(progress, is_cancelled, 99)
            temporary.replace(destination)
        if progress:
            progress(100)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class WorkspaceBackupPreview:
    created_at: str
    source_name: str
    target_dir: Path
    target_exists: bool
    files: int
    total_bytes: int
    experiments: int
    directories: int
    categories: dict[str, int]
    has_preferences: bool

    @property
    def summary(self):
        return (f"{self.files} arquivos · {self.experiments} registros de experimentos · "
                f"{self.total_bytes / 1_000_000:.2f} MB. "
                "Inclui bibliotecas, anotações, análises, protocolos e preferências presentes no backup.")


@dataclass
class PreparedWorkspaceRestore:
    preview: WorkspaceBackupPreview
    preferences: dict
    _stage_root: Path = field(repr=False)
    _target_identity: tuple | None = field(repr=False)
    _finished: bool = field(default=False, repr=False)
    cleanup_warning: str = ""

    def abort(self):
        """Discard validated staging. Never remove a failed rollback copy."""
        previous = self._stage_root / "previous"
        if previous.exists() and not self._finished:
            raise OSError(f"A cópia anterior foi preservada para recuperação em {previous}.")
        shutil.rmtree(self._stage_root, ignore_errors=True)

    def commit(self, *, replace_existing=False):
        """Install staging via directory renames; existing work requires opt-in.

        Keep all app writers idle. If installation fails, the previous directory
        is moved back before the error is raised. This is a local directory swap,
        not an online merge of independently edited workspaces.
        """
        if self._finished or not (self._stage_root / "workspace").is_dir():
            raise ValueError("Esta restauração já foi concluída ou descartada.")
        target = self.preview.target_dir
        with _operation_lock(target):
            if target.is_symlink() or (target.exists() and not target.is_dir()):
                raise ValueError("O destino da restauração deve ser uma pasta regular, sem links.")
            if target.exists() and not replace_existing:
                raise FileExistsError("A pasta de trabalho já existe. Confirme a substituição antes de restaurar.")
            identity = (target.stat().st_dev, target.stat().st_ino) if target.exists() else None
            if identity != self._target_identity:
                raise ValueError("O destino mudou desde a prévia. Inspecione o backup novamente antes de restaurar.")
            previous = self._stage_root / "previous"
            moved_previous = False
            try:
                if target.exists():
                    target.replace(previous)
                    moved_previous = True
                (self._stage_root / "workspace").replace(target)
            except Exception:
                if moved_previous:
                    try:
                        previous.replace(target)
                    except OSError as exc:
                        raise OSError(f"A restauração falhou e a pasta anterior foi preservada em {previous}.") from exc
                raise
            self._finished = True
        try:
            shutil.rmtree(self._stage_root)
        except OSError:
            self.cleanup_warning = f"A restauração foi concluída. A cópia temporária anterior permanece em {self._stage_root}."
        return deepcopy(self.preferences)


def _validate_manifest(manifest):
    if (not isinstance(manifest, dict) or manifest.get("kind") != "workspace_backup"
            or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1):
        raise ValueError("Use um backup completo da área de trabalho do Entrela.")
    if not isinstance(manifest.get("created_at"), str) or not isinstance(manifest.get("source_name"), str):
        raise ValueError("Identificação do backup inválida.")
    datetime.fromisoformat(manifest["created_at"])
    files, directories = manifest.get("files"), manifest.get("directories")
    if not isinstance(files, dict) or len(files) > MAX_FILES or not isinstance(directories, list) or len(directories) > MAX_FILES:
        raise ValueError("Manifesto com arquivos ou pastas inválidos ou em excesso.")
    aliases, file_names, directory_names = set(), set(), set()
    for name in [*directories, *files]:
        _relative_name(name)
        if name.casefold() in aliases:
            raise ValueError("Caminho duplicado no manifesto do backup.")
        aliases.add(name.casefold())
    for name in directories:
        directory_names.add(name)
    for name, metadata in files.items():
        file_names.add(name)
        _validate_file_metadata(metadata)
    for name in [*directories, *files]:
        parents = PurePosixPath(name).parents
        for parent in parents:
            if str(parent) == ".":
                continue
            if str(parent) not in directory_names:
                raise ValueError("Hierarquia de diretórios incompleta no manifesto.")
    if sum(item["bytes"] for item in files.values()) > MAX_TOTAL_BYTES:
        raise ValueError("O conteúdo do backup excede 2 GB.")
    _validate_file_metadata(manifest.get("preferences"))
    if manifest["preferences"]["bytes"] > MAX_PREFERENCES_BYTES:
        raise ValueError("As preferências excedem 1 MB.")
    return files, directories


def _validate_file_metadata(metadata):
    if (not isinstance(metadata, dict) or type(metadata.get("bytes")) is not int
            or not 0 <= metadata["bytes"] <= MAX_TOTAL_BYTES
            or not isinstance(metadata.get("sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", metadata["sha256"])):
        raise ValueError("Tamanho ou SHA-256 inválido no manifesto.")


def prepare_workspace_restore(archive, target_dir, *, progress=None, is_cancelled=None):
    """Inspect, bound, hash and stage a backup without replacing local data."""
    archive = Path(archive)
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("O arquivo de backup excede o limite de 2 GB.")
    target = _workspace_root(target_dir)
    if target.exists() and not target.is_dir():
        raise ValueError("O destino da restauração deve ser uma pasta.")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix=".entrela-restore-", dir=target.parent))
    try:
        _checkpoint(progress, is_cancelled, 0)
        copied_archive = stage_root / "incoming.zip"
        copied = 0
        with archive.open("rb") as source, copied_archive.open("wb") as destination:
            while block := source.read(_BLOCK):
                copied += len(block)
                if copied > MAX_ARCHIVE_BYTES:
                    raise ValueError("O arquivo de backup excede o limite de 2 GB.")
                destination.write(block)
                _checkpoint(progress, is_cancelled, 0)
        with zipfile.ZipFile(copied_archive) as source:
            entries = source.infolist()
            if (len(entries) > MAX_FILES + 2 or
                    sum(entry.file_size for entry in entries) > MAX_TOTAL_BYTES + MAX_PREFERENCES_BYTES + MAX_MANIFEST_BYTES):
                raise ValueError("O backup excede os limites de tamanho ou quantidade de arquivos.")
            names, aliases = set(), set()
            for entry in entries:
                name = entry.filename
                _relative_name(name)
                mode = stat.S_IFMT(entry.external_attr >> 16)
                if (name.casefold() in aliases or entry.is_dir() or
                        mode not in (0, stat.S_IFREG) or entry.flag_bits & 1):
                    raise ValueError("Arquivo duplicado, link ou tipo inseguro no backup.")
                names.add(name)
                aliases.add(name.casefold())
            if "manifest.json" not in names or source.getinfo("manifest.json").file_size > MAX_MANIFEST_BYTES:
                raise ValueError("Manifesto de backup ausente ou maior que 8 MB.")
            manifest = _json_load(source.read("manifest.json"))
            files, directories = _validate_manifest(manifest)
            expected = {"manifest.json", "preferences.json", *("workspace/" + name for name in files)}
            if names != expected:
                raise ValueError("Os arquivos do backup não correspondem ao manifesto.")
            if source.getinfo("preferences.json").file_size != manifest["preferences"]["bytes"]:
                raise ValueError("Tamanho das preferências incompatível com o manifesto.")
            preferences_data = source.read("preferences.json")
            if sha256(preferences_data).hexdigest() != manifest["preferences"]["sha256"]:
                raise ValueError("SHA-256 das preferências incompatível com o manifesto.")
            preferences = _json_load(preferences_data)
            if not isinstance(preferences, dict):
                raise ValueError("As preferências do backup devem conter um objeto JSON.")
            stage = stage_root / "workspace"
            stage.mkdir()
            for relative in directories:
                stage.joinpath(*PurePosixPath(relative).parts).mkdir(parents=True, exist_ok=True)
            copied, total = 0, max(1, sum(item["bytes"] for item in files.values()))
            for relative, metadata in sorted(files.items()):
                name = "workspace/" + relative
                if source.getinfo(name).file_size != metadata["bytes"]:
                    raise ValueError(f"Tamanho incompatível com o manifesto: {relative}")
                path = stage.joinpath(*PurePosixPath(relative).parts)
                digest, size = sha256(), 0
                with source.open(name) as content, path.open("wb") as destination:
                    while block := content.read(_BLOCK):
                        size += len(block)
                        copied += len(block)
                        if size > metadata["bytes"]:
                            raise ValueError("Arquivo excede o tamanho declarado no manifesto.")
                        destination.write(block)
                        digest.update(block)
                        _checkpoint(progress, is_cancelled, min(99, int(copied * 99 / total)))
                    destination.flush()
                    os.fsync(destination.fileno())
                if size != metadata["bytes"] or digest.hexdigest() != metadata["sha256"]:
                    raise ValueError(f"SHA-256 ou tamanho incompatível: {relative}")
            _checkpoint(progress, is_cancelled, 100)
        categories = {"experiments": 0, "circuits": 0, "analyses": 0, "protocols": 0, "library": 0, "other": 0}
        groups = {".circuits": "circuits", ".analyses": "analyses", ".protocols": "protocols", ".workspace": "library"}
        for name in files:
            pure = PurePosixPath(name)
            group = "experiments" if len(pure.parts) == 1 and pure.suffix == ".json" else groups.get(pure.parts[0], "other")
            categories[group] += 1
        preview = WorkspaceBackupPreview(
            manifest["created_at"], manifest["source_name"], target, target.exists(),
            len(files), sum(item["bytes"] for item in files.values()), categories["experiments"],
            len(directories), categories, bool(preferences),
        )
        identity = (target.stat().st_dev, target.stat().st_ino) if target.exists() else None
        return PreparedWorkspaceRestore(preview, preferences, stage_root, identity)
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise

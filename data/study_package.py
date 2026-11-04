"""Verify and stage portable studies before installing independent local copies."""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from uuid import uuid4
import zipfile

from core.simulation import SimulationCancelled
from data.analyses import validate_analysis, save_analysis
from data.protocols import ProtocolRepository
from data.repository import ExperimentRepository
from data.workspace import WorkspaceLibrary
from core.types import Experiment, config_from_dict


def _json(archive, name, limit=64_000_000):
    if archive.getinfo(name).file_size > limit:
        raise ValueError("Conteúdo JSON excede o limite do importador")
    value = json.loads(archive.read(name).decode("utf-8"))
    json.dumps(value, allow_nan=False)
    return value


def _remap(value, identifiers, key=""):
    if isinstance(value, dict):
        return {name: _remap(item, identifiers, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_remap(item, identifiers, key) for item in value]
    if isinstance(value, str) and (key == "id" or key.endswith(("_id","_ids"))) and not key.startswith("imported_from"):
        return identifiers.get(value, value)
    return value


@dataclass
class PreparedStudy:
    temporary: tempfile.TemporaryDirectory
    repository: ExperimentRepository
    experiments: list[Experiment]
    annotations: dict[str,dict]
    mapping: dict[str,str]
    fingerprint: str
    paths: list[Path]
    archive: Path
    comparison_mode: str = "controlled"

    def abort(self):
        self.temporary.cleanup()

    def commit(self):
        """Only new keys are installed. Roll back this import on write failure."""
        created = []
        try:
            library = WorkspaceLibrary(self.repository.base_dir / ".workspace")
            current = library.read()
            for identifier, annotation in self.annotations.items():
                current["annotations"][identifier] = annotation
                project = annotation.get("project", "")
                if project:
                    current["projects"].setdefault(project, {"description":""})
            for relative in self.paths:
                target = self.repository.base_dir / relative
                if target.exists():
                    raise ValueError("Conflito de importação; nenhum registro anterior será substituído")
                target.parent.mkdir(parents=True, exist_ok=True)
                (Path(self.temporary.name) / relative).replace(target)
                created.append(target)
            library._write(current)
            return self.experiments
        except Exception:
            for target in reversed(created):
                target.unlink(missing_ok=True)
            raise
        finally:
            self.abort()


def prepare_study_import(filepath, repository, *, progress=None, is_cancelled=None):
    path = Path(filepath)
    if path.stat().st_size > 512_000_000:
        raise ValueError("Pacote excede 512 MB")
    temporary = tempfile.TemporaryDirectory(prefix=".study-import-", dir=repository.base_dir)
    stage = Path(temporary.name)

    def checkpoint(value):
        if is_cancelled and is_cancelled():
            raise SimulationCancelled()
        if progress:
            progress(value)

    try:
        checkpoint(0)
        archive_copy = stage/"incoming.zip"
        with path.open("rb") as source, archive_copy.open("wb") as destination:
            while block := source.read(1_048_576):
                checkpoint(0)
                destination.write(block)
        with zipfile.ZipFile(archive_copy) as archive:
            entries = archive.infolist()
            if len(entries) > 2500 or sum(entry.file_size for entry in entries) > 512_000_000:
                raise ValueError("Pacote excede os limites de arquivos ou tamanho descompactado")
            names = set()
            for entry in entries:
                name = entry.filename
                pure = PurePosixPath(name)
                if (name in names or "\\" in name or pure.is_absolute() or ".." in pure.parts or
                    str(pure) != name or ":" in name or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise ValueError("Nome de arquivo inseguro ou duplicado no pacote")
                names.add(name)
            manifest = _json(archive, "manifest.json", 2_000_000)
            if manifest.get("schema_version") != 1 or manifest.get("kind") not in ("documentation","run_bundle"):
                raise ValueError("Use um Pacote completo ZIP exportado pela página Documentação")
            files = manifest.get("files")
            sources = manifest.get("source_ids")
            comparison_mode = manifest.get("comparison_mode","controlled")
            if comparison_mode not in ("controlled","trotter") or manifest.get("comparison_reference","exact" if comparison_mode == "trotter" else "circuit") != ("exact" if comparison_mode == "trotter" else "circuit"):
                raise ValueError("Referência científica da comparação inconsistente")
            if not isinstance(files,list) or not isinstance(sources,list) or not 1 <= len(sources) <= 2:
                raise ValueError("Manifesto de estudo inválido")
            expected = {}
            for record in files:
                if not isinstance(record,dict) or not isinstance(record.get("path"),str) or record["path"] in expected:
                    raise ValueError("Índice de arquivos inválido")
                expected[record["path"]] = record
            if set(expected) != names - {"manifest.json"}:
                raise ValueError("O índice do manifesto não corresponde ao conteúdo do pacote")
            for index,(name,record) in enumerate(expected.items()):
                checkpoint(int(5+45*index/max(1,len(expected))))
                if record.get("bytes") != archive.getinfo(name).file_size:
                    raise ValueError("Tamanho divergente no arquivo: " + name)
                digest = sha256()
                with archive.open(name) as stream:
                    while block := stream.read(1_048_576):
                        checkpoint(int(5+45*index/max(1,len(expected))))
                        digest.update(block)
                if digest.hexdigest() != record.get("sha256"):
                    raise ValueError("Falha de integridade SHA-256: " + name)
            raw_experiments = []
            for identifier in sources:
                repository._path(identifier)  # Validate before building any relative path.
                source_path = "experimento.json" if manifest["kind"] == "run_bundle" else "run_"+identifier+"/experiment.json"
                source = ExperimentRepository._deserialize(_json(archive, source_path))
                if source.id != identifier:
                    raise ValueError("A fonte do experimento não corresponde ao manifesto")
                raw_experiments.append(source)
            if len(set(sources)) != len(sources):
                raise ValueError("Fontes repetidas no pacote")
            if comparison_mode == "trotter":
                from core.comparison import incompatibility
                if len(raw_experiments) != 2 or incompatibility(*raw_experiments,mode="trotter"):
                    raise ValueError("As fontes não são compatíveis com a comparação Trotter declarada")
            analyses = [_json(archive,name) for name in sorted(names)
                        if re.fullmatch(r"analyses/analysis_[0-9]+\.json",name)]
            if "analyses.json" in names:
                analyses.append(_json(archive,"analyses.json"))
            protocols = _json(archive,"protocols.json") if "protocols.json" in names else []
            if not isinstance(protocols,list):
                raise ValueError("Lista de protocolos inválida")
            mapping = {identifier:uuid4().hex[:12] for identifier in sources}
            for data in analyses:
                validate_analysis(data)
                if data.get("source_id") not in sources:
                    raise ValueError("Análise sem fonte no pacote")
                identity = data.get("analysis_id") or data.get("id")
                if identity:
                    if identity in mapping:
                        raise ValueError("Identificador repetido entre os objetos do estudo")
                    mapping[identity] = uuid4().hex
            for protocol in protocols:
                identity = protocol.get("protocol_id")
                if not isinstance(identity,str) or protocol.get("source_id") not in sources:
                    raise ValueError("Protocolo sem fonte no pacote")
                if identity in mapping:
                    raise ValueError("Identificador repetido entre os objetos do estudo")
                mapping[identity] = uuid4().hex
            annotation_raw = manifest.get("annotations",{})
            if not isinstance(annotation_raw,dict):
                raise ValueError("Anotações inválidas")
            annotation_library = WorkspaceLibrary(stage/"annotation-validation")
            for original in sources:
                annotation = annotation_raw.get(original,{})
                if not isinstance(annotation,dict):
                    raise ValueError("Anotação de experimento inválida")
                annotation_library.annotate(mapping[original],annotation.get("project",""),annotation.get("notes",""),
                    annotation.get("tags",[]),**{key:annotation[key] for key in
                    ("title","description","objective","hypothesis","methodology","categories") if key in annotation})
            annotations = annotation_library.read()["annotations"]
            checkpoint(55)
            for data in analyses:
                original = data.get("analysis_id") or data.get("id")
                copied = _remap(data,mapping)
                copied["analysis_id"] = mapping.get(original,uuid4().hex)
                copied["imported_from_analysis_id"] = original
                save_analysis(copied,stage/".analyses"/copied["source_id"]/(copied["analysis_id"]+".json"))
            protocol_repo = ProtocolRepository(stage/".protocols")
            if protocols:
                protocol_repo.directory.mkdir()
            for data in protocols:
                copied = _remap(data,mapping)
                copied["config"] = asdict(config_from_dict(copied["config"]))
                copied["imported_from_protocol_id"] = data["protocol_id"]
                target = protocol_repo.directory/(copied["protocol_id"]+".json")
                target.write_text(json.dumps(copied,ensure_ascii=False,allow_nan=False),encoding="utf-8")
                protocol_repo.load(copied["protocol_id"])
        digest = sha256()
        with archive_copy.open("rb") as stream:
            while block := stream.read(1_048_576):
                checkpoint(70)
                digest.update(block)
        fingerprint = digest.hexdigest()
        experiments = []
        for source in raw_experiments:
            metadata = _remap(deepcopy(source.result.metadata),mapping)
            metadata.update(imported_from_id=source.id,imported_package_sha256=fingerprint,
                            imported_at=datetime.now(timezone.utc).isoformat())
            result = replace(source.result,metadata=metadata,
                             mitigation=_remap(deepcopy(source.result.mitigation),mapping))
            copied = replace(source,id=mapping[source.id],result=result)
            (stage/(copied.id+".json")).write_text(json.dumps(ExperimentRepository._serialize(copied),ensure_ascii=False,allow_nan=False),encoding="utf-8")
            experiments.append(copied)
        evidence = stage/".imports"/uuid4().hex
        evidence.mkdir(parents=True)
        archive_copy.replace(evidence/"original.zip")
        (evidence/"mapping.json").write_text(json.dumps(dict(sha256=fingerprint,identifiers=mapping),indent=2),encoding="utf-8")
        paths = sorted(file.relative_to(stage) for file in stage.rglob("*")
                       if file.is_file() and "annotation-validation" not in file.relative_to(stage).parts)
        checkpoint(100)
        return PreparedStudy(temporary,repository,experiments,annotations,mapping,fingerprint,paths,path,comparison_mode)
    except Exception:
        temporary.cleanup()
        raise

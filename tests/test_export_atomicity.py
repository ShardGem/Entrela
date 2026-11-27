"""Artefatos anteriores sobrevivem a falhas reais de gravação/publicação."""

import csv
import json
from pathlib import Path

import pytest

import core.export as exports
from core.examples import create_example_config
from core.types import Experiment, ExperimentResult


@pytest.fixture
def experiment():
    config = create_example_config('bell')
    return Experiment(config, ExperimentResult(counts={'00': config.shots // 2,
                                                       '11': config.shots - config.shots // 2}))


@pytest.fixture
def analysis():
    return {'source_id': 'execução-nova', 'kind': 'temporal',
            'rows': [{'time': 0.0, 'purity': 1.0}, {'time': 1.0, 'purity': 0.8}],
            'provenance': {'effective_seed': 42}}


@pytest.mark.parametrize('export_kind', ['json', 'counts_csv'])
def test_failed_write_does_not_truncate_previous_export(tmp_path, monkeypatch, experiment, export_kind):
    path = tmp_path / ('execução anterior.json' if export_kind == 'json' else 'contagens anteriores.csv')
    original = b'arquivo anterior integral'
    path.write_bytes(original)
    factory = exports.tempfile.NamedTemporaryFile

    class PartialFailure:
        def __init__(self, stream):
            self.stream = stream
            self.name = stream.name

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, text):
            self.stream.write(text[:20])
            self.stream.flush()
            raise OSError('Disco cheio após gravação parcial')

    monkeypatch.setattr(exports.tempfile, 'NamedTemporaryFile',
                        lambda *args, **kwargs: PartialFailure(factory(*args, **kwargs)))
    with pytest.raises(OSError, match='Disco cheio'):
        if export_kind == 'json':
            exports.export_experiment_json(experiment, path)
        else:
            exports.export_counts_csv(experiment.result.counts, path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_failed_json_publication_preserves_previous_file(tmp_path, monkeypatch, experiment):
    path = tmp_path / 'execucao.json'
    path.write_bytes(b'arquivo anterior')
    replace = Path.replace

    def fail(source, target):
        if target == path:
            raise PermissionError('Arquivo bloqueado')
        return replace(source, target)

    monkeypatch.setattr(Path, 'replace', fail)
    with pytest.raises(PermissionError, match='bloqueado'):
        exports.export_experiment_json(experiment, path)
    assert path.read_bytes() == b'arquivo anterior'
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('previous_csv,previous_metadata', [(True, True), (False, False),
                                                         (True, False), (False, True)])
def test_pair_rolls_back_if_second_publication_fails(tmp_path, monkeypatch, analysis,
                                                    previous_csv, previous_metadata):
    path = tmp_path / 'analise.csv'
    metadata = path.with_suffix('.metadata.json')
    previous = {}
    for exists, file, value in [(previous_csv, path, b'CSV ANTERIOR'),
                                (previous_metadata, metadata, b'METADADOS ANTERIORES')]:
        if exists:
            file.write_bytes(value)
            previous[file] = value
    replace = Path.replace

    def fail(source, target):
        if target == path and source.suffix == '.tmp':
            raise OSError('Publicação do CSV indisponível')
        return replace(source, target)

    monkeypatch.setattr(Path, 'replace', fail)
    with pytest.raises(OSError, match='Publicação do CSV'):
        exports.export_analysis(analysis, path)
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == previous


def test_backup_failure_leaves_both_outputs_unchanged(tmp_path, monkeypatch, analysis):
    path = tmp_path / 'analise.csv'
    metadata = path.with_suffix('.metadata.json')
    path.write_bytes(b'CSV ANTERIOR')
    metadata.write_bytes(b'METADADOS ANTERIORES')
    original = {p: p.read_bytes() for p in tmp_path.iterdir()}
    copy = exports.shutil.copy2

    def fail(source, destination, **kwargs):
        if source == path:
            raise OSError('Não foi possível preparar a recuperação')
        return copy(source, destination, **kwargs)

    monkeypatch.setattr(exports.shutil, 'copy2', fail)
    with pytest.raises(OSError, match='recuperação'):
        exports.export_analysis(analysis, path)
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == original


def test_failed_rollback_reports_and_keeps_original_backup(tmp_path, monkeypatch, analysis):
    path = tmp_path / 'analise.csv'
    metadata = path.with_suffix('.metadata.json')
    path.write_bytes(b'CSV ANTERIOR')
    metadata.write_bytes(b'METADADOS ANTERIORES')
    replace = Path.replace

    def fail(source, target):
        if target == path and source.suffix == '.tmp':
            raise OSError('Falha na publicação')
        if target == metadata and source.suffix == '.backup':
            raise PermissionError('Recuperação bloqueada')
        return replace(source, target)

    monkeypatch.setattr(Path, 'replace', fail)
    with pytest.raises(OSError, match='restauração não pôde ser concluída') as error:
        exports.export_analysis(analysis, path)
    backups = list(tmp_path.glob('*.backup'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b'METADADOS ANTERIORES'
    assert str(backups[0]) in str(error.value)
    assert path.read_bytes() == b'CSV ANTERIOR'


def test_successful_exports_preserve_schema_and_clean_staging(tmp_path, experiment, analysis):
    path = tmp_path / 'analise.csv'
    metadata = path.with_suffix('.metadata.json')
    path.write_text('CSV ANTERIOR', encoding='utf-8')
    metadata.write_text('METADADOS ANTERIORES', encoding='utf-8')
    assert exports.export_analysis(analysis, path) == path
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    assert len(rows) == 2
    assert float(rows[1]['purity']) == 0.8
    manifest = json.loads(metadata.read_text(encoding='utf-8'))
    assert manifest['source_id'] == analysis['source_id']
    assert manifest['provenance'] == analysis['provenance']
    run = tmp_path / 'execucao.json'
    assert exports.export_experiment_json(experiment, run) == run
    loaded = exports.import_experiment_json(run)
    assert loaded.id == experiment.id and loaded.config == experiment.config
    assert loaded.result.counts == experiment.result.counts
    counts = tmp_path / 'contagens.csv'
    exports.export_counts_csv(experiment.result.counts, counts)
    with counts.open(encoding='utf-8', newline='') as stream:
        table = list(csv.reader(stream))
    assert table[0] == ['Bitstring', 'Counts']
    assert {row[0]: int(row[1]) for row in table[1:]} == experiment.result.counts
    assert set(tmp_path.iterdir()) == {path, metadata, run, counts}

"""Uma remoção concorrente não esconde execuções íntegras do histórico."""

from dataclasses import replace
import os
from pathlib import Path

import pytest

from core.examples import create_example_config
from core.types import Experiment, ExperimentResult
from data.repository import ExperimentRepository


@pytest.fixture
def repository(tmp_path):
    repo = ExperimentRepository(tmp_path / 'runs')
    run = Experiment(create_example_config('bell'), ExperimentResult())
    for identifier in ['preservado', 'removido']:
        repo.save(replace(run, id=identifier))
    return repo


@pytest.mark.parametrize('method', ['list_summaries', 'list_all'])
def test_removal_between_glob_and_stat_keeps_other_records(repository, monkeypatch, method):
    victim = repository._path('removido')
    original = Path.stat

    def remove_before_stat(path, *args, **kwargs):
        if path == victim:
            path.unlink(missing_ok=True)
        return original(path, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Path, 'stat', remove_before_stat)
        records = getattr(repository, method)()
    assert [record.id for record in records] == ['preservado']
    assert repository.load_errors == []
    assert repository.load('preservado').id == 'preservado'


@pytest.mark.parametrize('method', ['list_summaries', 'list_all'])
def test_removal_after_sorting_before_read_keeps_other_records(repository, monkeypatch, method):
    victim = repository._path('removido')
    # Force the summary reader to open the source, just like the full reader.
    (repository.base_dir / '.summaries' / victim.name).unlink()
    original = Path.open

    def remove_before_open(path, *args, **kwargs):
        if path == victim:
            path.unlink(missing_ok=True)
        return original(path, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Path, 'open', remove_before_open)
        records = getattr(repository, method)()
    assert [record.id for record in records] == ['preservado']
    assert repository.load_errors == []


@pytest.mark.parametrize('method', ['list_summaries', 'list_all'])
def test_stat_permission_failure_is_a_partial_warning(repository, monkeypatch, method):
    inaccessible = repository._path('removido')
    original = Path.stat

    def inaccessible_stat(path, *args, **kwargs):
        if path == inaccessible:
            raise PermissionError('Acesso ao registro bloqueado')
        return original(path, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Path, 'stat', inaccessible_stat)
        records = getattr(repository, method)()
    assert [record.id for record in records] == ['preservado']
    assert len(repository.load_errors) == 1
    assert 'removido.json' in repository.load_errors[0]
    assert 'bloqueado' in repository.load_errors[0]
    assert inaccessible.exists()


@pytest.mark.parametrize('method', ['list_summaries', 'list_all'])
def test_successful_listing_remains_ordered_by_mtime(repository, method):
    older, newer = repository._path('preservado'), repository._path('removido')
    os.utime(older, (1_600_000_000, 1_600_000_000))
    os.utime(newer, (1_600_000_010, 1_600_000_010))
    assert [record.id for record in getattr(repository, method)()] == ['removido', 'preservado']
    assert repository.load_errors == []

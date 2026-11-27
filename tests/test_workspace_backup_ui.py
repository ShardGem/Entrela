"""Actual archive workers freeze writers and reopen restored sources cleanly."""
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication, QMessageBox
from core.examples import create_example_config
from core.simulation import run_experiment
from dataclasses import replace
from data.workspace import WorkspaceLibrary
from tests.qt_helpers import wait_until


def test_backup_and_restore_reopen_real_data_without_flushing_old_drafts(window, tmp_path, monkeypatch):
    record = run_experiment(replace(create_example_config('bell'), shots=16, seed=42))
    window.repository.save(record)
    library = WorkspaceLibrary(window.repository.base_dir / '.workspace')
    library.annotate(record.id, 'TCC', '', [], title='Bell de referência')
    window.settings.setValue('appearance/font_size', 17)
    window.page_simulation.experiment_name.setText('Rascunho protegido no backup')
    archive = tmp_path / 'backup.zip'
    controller = window.workspace_backup
    controller._start('export', archive)
    assert window._current_worker is not None
    assert not window.job_monitor.isHidden()
    assert not window.stack.isEnabled()
    assert window.drafts.restoring
    window._show_page('history')
    assert not window.job_monitor.isHidden()
    wait_until(lambda: window._current_worker is None and not controller.busy)
    assert archive.is_file()
    assert window.stack.isEnabled()
    assert not window.drafts.restoring
    assert window.job_monitor.isHidden()
    library.annotate(record.id, 'Outro', '', [], title='Mudança posterior')
    window.page_simulation.experiment_name.setText('Não gravar isto após restaurar')
    window.settings.setValue('appearance/font_size', 24)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: QMessageBox.RestoreDefaults)
    controller._start('restore', archive)
    app = QApplication.instance()
    restored = None
    try:
        wait_until(lambda: getattr(app, '_entrela_restored_window', None) is not None)
        restored = app._entrela_restored_window
        assert window._workspace_replaced
        assert not window.isVisible()
        assert restored.repository.load(record.id).result.counts == record.result.counts
        assert WorkspaceLibrary(restored.repository.base_dir / '.workspace').read()['annotations'][record.id]['title'] == 'Bell de referência'
        assert restored.page_simulation.experiment_name.text() == 'Rascunho protegido no backup'
        assert restored.settings.value('appearance/font_size', type=int) == 17
        assert restored.stack.isEnabled()
        assert restored._current_worker is None
    finally:
        if restored:
            restored._unsaved_result = False
            restored.close()
            app.processEvents()
        if hasattr(app, '_entrela_restored_window'):
            del app._entrela_restored_window


def test_restore_cancel_keeps_sources_and_reenables_interface(window, tmp_path, monkeypatch):
    archive = tmp_path / 'backup.zip'
    controller = window.workspace_backup
    controller._start('export', archive)
    wait_until(lambda: not controller.busy)
    source = window.repository.base_dir / 'diagnostic.txt'
    source.write_text('evidência atual', encoding='utf-8')
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: QMessageBox.Cancel)
    controller._start('restore', archive)
    wait_until(lambda: not controller.busy)
    assert source.read_text(encoding='utf-8') == 'evidência atual'
    assert window.stack.isEnabled()
    assert not window.drafts.restoring
    assert not getattr(window, '_workspace_replaced', False)
    assert 'cancelada' in window.page_settings.backup_message.text()


def test_invalid_archive_does_not_create_a_fake_experiment(window, tmp_path):
    source = tmp_path / 'invalid.zip'
    source.write_text('not an archive', encoding='utf-8')
    before = [item.id for item in window.repository.list_summaries()]
    window.workspace_backup._start('restore', source)
    wait_until(lambda: not window.workspace_backup.busy)
    assert [item.id for item in window.repository.list_summaries()] == before
    assert window.stack.isEnabled()
    assert not window.drafts.restoring
    assert 'Não foi possível' in window.page_settings.backup_message.text()


def test_failed_rollback_keeps_stale_writers_suspended(window, monkeypatch):
    from types import SimpleNamespace
    recovery_path = 'recovery/previous'

    class FailedRestore:
        preview = SimpleNamespace(summary='Prévia', source_name='Backup', created_at='2026-11-10')

        def commit(self, **kwargs):
            raise OSError('Falha ao instalar e recuperar')

        def abort(self):
            raise OSError('Cópia anterior preservada em ' + recovery_path)

    notices = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: QMessageBox.RestoreDefaults)
    monkeypatch.setattr(QMessageBox, 'critical', lambda parent, title, text: notices.append(text))
    window.stack.setEnabled(False)
    window.drafts.restoring = True
    window.workspace_backup.prepared = FailedRestore()
    window.workspace_backup._finished()
    assert window._workspace_replaced
    assert not window.stack.isEnabled()
    assert window.drafts.restoring
    assert recovery_path in notices[0]


def test_global_cancel_keeps_previous_results_and_releases_monitor(window):
    from threading import Event

    class CooperativeWorker(QThread):
        completed, cancelled, error, progress = Signal(object), Signal(), Signal(str), Signal(int)
        config = None

        def run(self):
            tick = Event()
            while not self.isInterruptionRequested():
                tick.wait(.01)
            self.cancelled.emit()

    worker = CooperativeWorker(window)
    window._start_worker(worker, window._on_experiment)
    window._show_page('docs')
    window.job_monitor.cancel.click()
    assert not window.job_monitor.cancel.isEnabled()
    wait_until(lambda: window._current_worker is None)
    assert window._current_experiment is None
    assert window.job_monitor.isHidden()

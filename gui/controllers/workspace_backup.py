"""Coordinate an idle workspace, archive preview and clean window replacement."""
from pathlib import Path
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from data.repository import ExperimentRepository
from gui.workers.workspace_backup_worker import WorkspaceBackupWorker


class WorkspaceBackupController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.prepared = None
        self.busy = False

    def export(self):
        if not self._available():
            return
        path, _ = QFileDialog.getSaveFileName(self.window, "Backup completo", "entrela-backup.zip", "Backup Entrela (*.zip)")
        if path:
            self._start("export", path)

    def restore(self):
        if not self._available():
            return
        path, _ = QFileDialog.getOpenFileName(self.window, "Inspecionar backup completo", "", "Backup Entrela (*.zip)")
        if path:
            self._start("restore", path)

    def _available(self):
        window = self.window
        if self.busy or window._current_worker is not None or window._storage_worker is not None:
            window.statusBar().showMessage("Aguarde ou cancele a tarefa atual antes de trabalhar com backups.")
            return False
        if window.repository is None:
            window.statusBar().showMessage("A pasta de trabalho não está disponível para backup.")
            return False
        return True

    def _start(self, mode, path):
        if not self._available():
            return
        window = self.window
        if not window._confirm_unsaved() or not window.drafts.flush():
            return
        window.settings.sync()
        preferences = {key: window.settings.value(key) for key in window.settings.allKeys()}
        self.busy = True
        self.prepared = None
        # Prevent edits and delayed draft writes from changing the snapshot or
        # overwriting a just-restored workspace. Cancel remains outside stack.
        window.drafts.timer.stop()
        window.drafts.restoring = True
        window.page_bloch.timer.stop()
        window.page_bloch.playing = False
        window.stack.setEnabled(False)
        window.page_settings.backup_message.setText("Criando backup…" if mode == "export" else "Validando o backup antes de restaurar…")
        worker = WorkspaceBackupWorker(mode, window.repository.base_dir, Path(path), preferences, window)
        worker.error.connect(window.page_settings.backup_message.setText)
        window._start_worker(worker, self._completed)
        worker.finished.connect(self._finished)

    def _completed(self, result):
        if hasattr(result, "commit"):
            self.prepared = result
        else:
            message = "Backup completo salvo em " + str(result)
            self.window.page_settings.backup_message.setText(message)
            self.window.statusBar().showMessage(message)

    def _finished(self):
        try:
            if self.prepared is not None:
                self._confirm_restore(self.prepared)
        finally:
            self.prepared = None
            self.busy = False
            if not getattr(self.window, "_workspace_replaced", False):
                self.window.drafts.restoring = False
                self.window.stack.setEnabled(True)

    def _confirm_restore(self, prepared):
        window = self.window
        preview = prepared.preview
        message = (preview.summary + "\n\nOrigem: " + preview.source_name +
                   "\nCriado em: " + preview.created_at +
                   "\n\nA restauração substituirá os dados desta pasta e as preferências pelo conteúdo do backup. "
                   "A janela será reaberta com os dados restaurados. Faça um backup do trabalho atual antes de continuar. "
                   "Feche outras instâncias do Entrela que utilizem esta pasta antes de restaurar.")
        answer = QMessageBox.warning(window, "Restaurar espaço de trabalho", message,
                                     QMessageBox.RestoreDefaults | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer != QMessageBox.RestoreDefaults or window._close_pending:
            prepared.abort()
            window.page_settings.backup_message.setText("Restauração cancelada; espaço de trabalho preservado.")
            return
        try:
            preferences = prepared.commit(replace_existing=True)
        except (OSError, ValueError) as exc:
            try:
                prepared.abort()
            except OSError as recovery_error:
                window._workspace_replaced = True
                window.page_settings.backup_message.setText(str(recovery_error))
                QMessageBox.critical(window, "Recuperação necessária", str(recovery_error) +
                                     "\nA edição foi suspensa para preservar a cópia de recuperação. Feche o Entrela e recupere a pasta indicada antes de continuar.")
                return
            window.page_settings.backup_message.setText("Falha ao restaurar: " + str(exc))
            return
        # Old widgets must never flush their drafts/preferences into the new
        # directory. Reuse startup restoration rather than maintaining stale
        # source references, caches or a second copy of scientific state.
        window._workspace_replaced = True
        window.drafts.timer.stop()
        window.settings.clear()
        for key, value in preferences.items():
            window.settings.setValue(key, value)
        window.settings.sync()
        try:
            restored = type(window)(ExperimentRepository(preview.target_dir), window.settings)
        except Exception as exc:
            # The files have already been restored. Keep the old window frozen
            # instead of letting stale widgets save into the restored folder.
            QMessageBox.critical(window, "Backup restaurado", "Os arquivos foram restaurados, mas a janela não pôde ser reaberta. Feche e inicie o Entrela novamente.\n" + str(exc))
            window.close()
            return
        restored.resize(window.size())
        restored.show()
        QApplication.instance()._entrela_restored_window = restored
        restored.statusBar().showMessage(prepared.cleanup_warning or "Backup restaurado. Execuções, bibliotecas e preferências recuperadas.")
        window.close()

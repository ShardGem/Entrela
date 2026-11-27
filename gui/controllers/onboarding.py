"""Coordena a introdução e os atalhos de aprendizagem, sem editar simulações."""

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from gui.widgets.getting_started import WelcomeDialog


class OnboardingController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.dialog = None
        self._previous_focus = None
        self._waiting_for_show = False
        self._startup_timer = QTimer(self)
        self._startup_timer.setSingleShot(True)
        self._startup_timer.timeout.connect(self._offer_when_ready)
        self.guide = window.page_docs.guide
        try:
            step = int(window.settings.value('onboarding/guide_step', 0))
        except (TypeError, ValueError):
            step = 0
        self.guide.restore(step, window.settings.value('onboarding/guide_completed', False, type=bool))
        self.guide.progress_changed.connect(self._save_progress)
        self.guide.destination_requested.connect(window._open_destination)
        self.guide.tutorial_requested.connect(window._begin_tutorial)
        self.guide.welcome_requested.connect(self.show_welcome)
        self.guide.opened.connect(self.refresh_context)
        window.page_dashboard.guide_requested.connect(self.open_guide)
        self.refresh_context()

    def open_guide(self):
        self.window._show_page('docs')
        self.window.page_docs.show_guide()
        self.refresh_context()
        self.guide.step_buttons.button(self.guide.step).setFocus(Qt.OtherFocusReason)

    def _save_progress(self, step, completed):
        self.window.settings.setValue('onboarding/guide_step', step)
        self.window.settings.setValue('onboarding/guide_completed', completed)

    def refresh_context(self):
        experiment = self.window._current_experiment
        self.guide.set_result(self.window._experiment_name(experiment) if experiment and not experiment.result.error else '')

    def offer_on_startup(self):
        """Chamado pela entrada desktop; só apresenta depois que a janela abrir."""
        settings = self.window.settings
        if settings.value('onboarding/welcome_seen', False, type=bool) and not settings.value('onboarding/show_on_startup', False, type=bool):
            return
        if self.window.page_settings.presentation.isChecked():
            return
        if self.window.isVisible():
            self._startup_timer.start(0)
        else:
            self._waiting_for_show = True
            self.window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QEvent.Show and self._waiting_for_show:
            self._waiting_for_show = False
            self.window.removeEventFilter(self)
            self._startup_timer.start(0)
        return False

    def _offer_when_ready(self):
        if not self.window.isVisible():
            return
        if QApplication.activeModalWidget() is not None or self.window._current_worker is not None:
            self._startup_timer.start(500)
            return
        self.show_welcome()

    def show_welcome(self):
        if self.dialog is not None and self.dialog.isVisible():
            self.dialog.raise_()
            self.dialog.activateWindow()
            return
        self._startup_timer.stop()
        self._waiting_for_show = False
        self.window.removeEventFilter(self)
        self._previous_focus = QApplication.focusWidget()
        repeat = self.window.settings.value('onboarding/show_on_startup', False, type=bool)
        self.dialog = WelcomeDialog(repeat, self.window)
        available = self.window.screen().availableGeometry()
        self.dialog.resize(min(760, available.width() - 48), min(740, available.height() - 64))
        self.dialog.finished.connect(self._welcome_closed)
        self.dialog.open()
        self.dialog.actions['guide'].setFocus(Qt.OtherFocusReason)

    def _welcome_closed(self, _result):
        dialog = self.dialog
        self.dialog = None
        self.window.settings.setValue('onboarding/welcome_seen', True)
        self.window.settings.setValue('onboarding/show_on_startup', dialog.repeat.isChecked())
        choice = dialog.choice
        dialog.deleteLater()
        self.window.activateWindow()
        if choice == 'guide':
            self.open_guide()
        elif choice == 'tutorial':
            self.window._begin_tutorial()
        elif choice == 'examples':
            self.window._show_page('examples')
        elif (self._previous_focus is not None and isValid(self._previous_focus)
              and self._previous_focus.isVisible() and self._previous_focus.isEnabled()):
            self._previous_focus.setFocus(Qt.OtherFocusReason)
        self._previous_focus = None

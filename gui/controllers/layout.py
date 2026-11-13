"""Persistência da disposição visual, independente dos rascunhos científicos."""
import json
from PySide6.QtCore import QObject, QTimer, QByteArray
from gui.design_system import LAYOUT


class LayoutController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self.save)
        self.splitters = {
            'preparation': window.page_simulation.splitter,
            'history': window.page_history.splitter,
            'concepts': window.page_docs.splitter,
            'states': window.page_bloch.stage_splitter,
        }
        workspace = window.page_workspace
        for field, choices in (('_last_preparation', workspace.PREPARATION), ('_last_result', workspace.RESULTS)):
            value = window.settings.value('layout/laboratory/' + field)
            if value in {key for key, _ in choices}:
                setattr(workspace, field, value)
        try:
            stage = int(window.settings.value('layout/laboratory/stage', 0))
        except (TypeError, ValueError):
            stage = 0
        workspace._apply_route(workspace._last_result if stage == 1 else workspace._last_preparation)
        self.defaults = {'preparation': [850, LAYOUT.inspector_width], 'history': [450, 650], 'concepts': [270, 740], 'states': [900, 320]}
        if window.settings.value('layout/studio_schema', 0, type=int) < 1:
            window.settings.remove('layout/preparation')
            window.settings.setValue('layout/studio_schema', 1)
        for key, splitter in self.splitters.items():
            self.restore_splitter(key)
            splitter.splitterMoved.connect(lambda *_: self.timer.start())
        window.page_simulation.workbench_changed.connect(lambda: self.restore_splitter('preparation'))
        for key, combo in self.choices.items():
            value = window.settings.value('layout/choice/' + key, 0)
            try:
                index = int(value)
            except (ValueError, TypeError):
                index = 0
            if 0 <= index < combo.count():
                combo.setCurrentIndex(index)
            combo.currentIndexChanged.connect(lambda *_: self.timer.start())
        try:
            routes = json.loads(window.settings.value('layout/routes', '{}'))
        except (TypeError, ValueError):
            routes = {}
        if isinstance(routes, dict):
            from gui.navigation import ROOT_FOR_PAGE
            for root, key in routes.items():
                if key in window.pages and ROOT_FOR_PAGE[key] == root:
                    window.navigation.last_for_root[root] = key

    def restore_splitter(self, key):
        splitter = self.splitters[key]
        encoded = self.window.settings.value('layout/' + key)
        if splitter.count() and isinstance(encoded, str):
            try:
                splitter.restoreState(QByteArray.fromBase64(encoded.encode('ascii')))
            except (ValueError, UnicodeError):
                pass

    @property
    def choices(self):
        w = self.window
        return {'preferences': w.page_settings.category, 'study': w.page_analysis.family}

    def save(self):
        self.timer.stop()
        for key, splitter in self.splitters.items():
            if splitter.count():
                self.window.settings.setValue('layout/' + key, bytes(splitter.saveState().toBase64()).decode('ascii'))
        for key, combo in self.choices.items():
            self.window.settings.setValue('layout/choice/' + key, combo.currentIndex())
        workspace = self.window.page_workspace
        self.window.settings.setValue('layout/laboratory/stage', workspace.stages.currentIndex())
        for field in ('_last_preparation', '_last_result'):
            self.window.settings.setValue('layout/laboratory/' + field, getattr(workspace, field))
        self.window.settings.setValue('layout/routes', json.dumps(self.window.navigation.last_for_root))

    def reset(self):
        self.timer.stop()
        for key, splitter in self.splitters.items():
            splitter.setSizes(self.defaults[key])
            self.window.settings.remove('layout/' + key)
        for key, combo in self.choices.items():
            # A família do estudo determina a pergunta científica em edição.
            # Apagar a preferência futura não deve substituir esse rascunho.
            if key != 'study':
                combo.setCurrentIndex(0)
            self.window.settings.remove('layout/choice/' + key)
        self.window.settings.remove('layout/routes')
        self.window.settings.remove('layout/laboratory')
        self.window.page_workspace._last_preparation = 'simulation'
        self.window.page_workspace._last_result = 'results:graphs'
        self.window.navigation.last_for_root.update(dashboard='dashboard', simulation='simulation', analysis='analysis', history='history', docs='examples', settings='settings')
        self.window.page_history.expand_details.setChecked(False)
        self.timer.stop()
        self.window.statusBar().showMessage('Disposição restaurada. Os parâmetros e os registros foram preservados.', 6000)

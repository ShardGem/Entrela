"""Coordena a navegação visual; não executa nem substitui experimentos."""

from gui.navigation import ROOT_FOR_PAGE, PAGE_LABELS, NAV_LABELS


class NavigationController:
    def __init__(self, window):
        self.window = window
        self.last_for_root = dict(dashboard='dashboard', simulation='simulation', analysis='analysis', history='history', docs='examples', settings='settings')

    def open_page(self, key):
        """Um item visível abre sua função exata, independente da última área."""
        w = self.window
        if key == 'configurations':
            w._show_saved_configurations()
            return
        if key not in w.pages:
            return
        if key == 'circuit':
            w.page_workspace._apply_route('circuit:edit')
        elif key == 'results':
            w.page_workspace._apply_route('results:graphs')
        self.show(key)

    def open_root(self, root):
        key = self.last_for_root.get(root, root)
        if self.window._current_experiment is None and key in ('results', 'bloch', 'library', 'documentation'):
            key = 'simulation' if root == 'simulation' else 'history'
        if root == 'simulation':
            workspace = self.window.page_workspace
            stage = workspace.stages.currentIndex()
            last = workspace._last_preparation if stage == 0 else workspace._last_result
            if self.window._current_experiment is None:
                last = workspace._last_preparation
            workspace._apply_route(last)
            key = workspace.current_page_key
        self.show(key)

    def show(self, key):
        w = self.window
        if key not in w.pages:
            return
        if key == 'documentation':
            w._refresh_documentation()
        w._current_page = key
        root = ROOT_FOR_PAGE[key]
        self.last_for_root[root] = key
        if key in ('catalog', 'examples'):
            w.stack.setCurrentWidget(w.page_catalog)
            if key == 'examples': w.page_catalog.tabs.setCurrentIndex(0)
        elif key in ('notebook', 'library', 'documentation'):
            w.stack.setCurrentWidget(w.page_notebook)
            if key == 'library':
                w.page_notebook.tabs.setCurrentIndex(0); w.page_notebook.scope.setCurrentIndex(1)
            elif key == 'documentation': w.page_notebook.tabs.setCurrentIndex(1)
        elif root == 'simulation':
            w.stack.setCurrentWidget(w.page_workspace)
            w.page_workspace.select_page(key)
        elif root in w.section_workspaces:
            section = w.section_workspaces[root]
            section.select_page(key)
            w.stack.setCurrentWidget(section)
        else:
            w.stack.setCurrentWidget(w.pages[key])
        w.sidebar.set_active(key)
        title = NAV_LABELS.get(key, PAGE_LABELS.get(key, key))
        controller = getattr(w, 'projects', None)
        project = controller.project if controller else None
        preparation = key == 'simulation' or (key == 'circuit' and w.page_workspace._route == 'circuit:edit')
        activity = root == 'simulation' or (key == 'comparison' and w._current_experiment is not None)
        active = controller.active if controller else None
        if not preparation and key in ('results', 'bloch', 'comparison') and w._current_experiment is not None:
            try:
                project = w._workspace_library().read()['annotations'].get(w._current_experiment.id, {}).get('project', '')
            except (OSError, ValueError, TypeError):
                pass
        destination = 'examples' if key in ('catalog', 'examples') else 'docs' if key == 'docs' else 'dashboard'
        w.topbar.set_destination(destination if key != 'settings' else '')
        path = [('Projetos', 'projects')]
        if destination == 'examples': path = [('Biblioteca', 'examples')]
        elif key == 'docs': path = [('Aprender', 'docs')]
        elif key == 'settings': path = [('Preferências', '')]
        else:
            if project is not None: path.append((project or 'Sem projeto', 'project:' + project))
            if activity:
                name = ((w.page_circuit.editor.circuit_name.text() if key == 'circuit' else w.page_simulation.experiment_name.text()) or (active or {}).get('title', 'Rascunho')) if preparation else (w._experiment_name(w._current_experiment) if w._current_experiment else 'Ainda sem execução')
                path.append((name, ''))
        if key == 'dashboard': title = (project or ('Sem projeto' if project == '' else 'Projetos')) + (' · Experimentos' if w.page_dashboard.mode == 'experiments' else '')
        if key in ('results', 'bloch'): title = 'Observar execução'
        if key == 'simulation': title = 'Preparar simulação'
        if key == 'circuit': title = 'Editor de circuitos' if preparation else 'Circuito da execução'
        if hasattr(w, 'export_bloch_view'):
            w.export_bloch_view.setVisible(key == 'bloch')
            w.export_bloch_view.setText('' if w.width() < 1180*max(1, w.font().pixelSize()/15) else 'Exportar Bloch…')
            w.export_bloch_view.setAccessibleName('Exportar a visualização de Bloch')
        w.topbar.set_context(title)
        w.topbar.set_path(path)
        w.topbar.activities.setVisible(activity)
        w.topbar.set_activity(0 if preparation else 2 if key == 'comparison' else 1, w._current_experiment is not None)
        w.topbar.project_tabs.setVisible(project is not None and key in ('dashboard', 'history', 'notebook', 'library', 'documentation'))
        from PySide6.QtCore import QSignalBlocker
        blocker = QSignalBlocker(w.topbar.project_tabs)
        w.topbar.project_tabs.setCurrentIndex((1 if w.page_dashboard.mode == 'experiments' else 0) if key == 'dashboard' else 1 if key == 'history' else 3 if key == 'documentation' else 2)
        del blocker
        w.topbar.tools.setVisible(destination == 'dashboard')
        if hasattr(w, 'layout_controller'):
            w.layout_controller.timer.start()
        w._update_tutorial()

    def is_active(self, key):
        w = self.window
        if key not in w.pages:
            return False
        if key in ('catalog', 'examples'):
            return w.stack.currentWidget() is w.page_catalog and (key != 'examples' or w.page_catalog.tabs.currentIndex() == 0)
        if key in ('notebook', 'library', 'documentation'):
            return w.stack.currentWidget() is w.page_notebook and (key == 'notebook' or (w.page_notebook.tabs.currentIndex() == 0 if key == 'library' else w.page_notebook.tabs.currentIndex() in (1, 2)))
        root = ROOT_FOR_PAGE[key]
        if root == 'simulation':
            return w.stack.currentWidget() is w.page_workspace and w.page_workspace.current_page_key == key
        if root in w.section_workspaces:
            section = w.section_workspaces[root]
            return w.stack.currentWidget() is section and section.current_page_key == key
        return w.stack.currentWidget() is w.pages[key]

    def help_topic(self):
        w = self.window
        if w._current_page == 'simulation':
            return {'system': 'Qubits', 'hamiltonian': 'Hamiltoniano', 'evolution': 'Evolução',
                    'noise': 'Ruído', 'execution': 'Reprodutibilidade'}.get(w.page_simulation.config_panel.current_section, 'Início')
        return {'circuit': 'Circuitos', 'results': 'Fidelidade', 'bloch': 'Esfera de Bloch',
                'mitigation': 'Mitigação', 'analysis': 'Evolução', 'comparison': 'Comparações',
                'history': 'Reprodutibilidade', 'library': 'Protocolos', 'documentation': 'Documentação',
                'settings': 'Configurações'}.get(w._current_page, 'Início')

"""Coordena a navegação visual; não executa nem substitui experimentos."""

from gui.navigation import ROOT_FOR_PAGE, PAGE_LABELS, NAV_LABELS
from data.workspace import experiment_title


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
            w.page_results.reveal_visualization()
            w.page_results.results_tab.chart_views.setCurrentIndex(0)
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
        else:
            w.stack.setCurrentWidget(w.pages[key])
        inspecting_circuit = key == 'circuit' and w.page_workspace._route == 'circuit:inspect'
        active_item = {'examples': 'catalog', 'library': 'notebook', 'documentation': 'notebook'}.get(key, key)
        w.sidebar.set_active('results' if inspecting_circuit else active_item)
        self.update_heading()
        if hasattr(w, 'layout_controller'):
            w.layout_controller.timer.start()
        w._update_tutorial()

    def update_heading(self):
        w = self.window
        key = w._current_page
        inspecting_circuit = key == 'circuit' and w.page_workspace._route == 'circuit:inspect'
        title = PAGE_LABELS.get(key, NAV_LABELS.get(key, key))
        context = ''
        controller = getattr(w, 'projects', None)
        project = controller.project if controller else None
        if key == 'dashboard':
            title = project or ('Sem projeto' if project == '' else 'Projetos')
        elif key == 'simulation':
            title = 'Simulação por Hamiltoniano'
            context = project or ''
        elif key == 'circuit' and not inspecting_circuit:
            title = 'Editor de circuitos'
            context = project or ''
        elif key in ('results', 'bloch') or inspecting_circuit:
            title = 'Estados quânticos 3D' if key == 'bloch' else 'Circuito da execução' if inspecting_circuit else 'Resultados'
        if (key in ('results', 'bloch') or inspecting_circuit) and w._current_experiment is not None:
            annotations = w.page_history.annotations
            source_project = annotations.get(w._current_experiment.id, {}).get('project', '')
            context = ' · '.join(filter(None, (source_project, title)))
            title = experiment_title(w._current_experiment, annotations)
        elif key in ('library', 'notebook', 'documentation', 'analysis', 'history', 'mitigation'):
            context = project or ''
        w.topbar.set_context(title, context)

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

"""Coordena a navegação visual; não executa nem substitui experimentos."""

from gui.navigation import ROOT_FOR_PAGE, PAGE_LABELS


class NavigationController:
    def __init__(self, window):
        self.window = window
        self.last_for_root = dict(dashboard='dashboard', simulation='simulation', analysis='analysis', history='history', docs='examples', settings='settings')

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
        if root == 'simulation':
            w.stack.setCurrentWidget(w.page_workspace)
            w.page_workspace.select_page(key)
        elif root in w.section_workspaces:
            section = w.section_workspaces[root]
            section.select_page(key)
            w.stack.setCurrentWidget(section)
        else:
            w.stack.setCurrentWidget(w.pages[key])
        w.sidebar.set_active(root)
        detail = PAGE_LABELS[key]
        if root == 'simulation':
            detail = w.page_workspace.view_selector.currentText()
        elif root in w.section_workspaces:
            detail = w.section_workspaces[root].selector.currentText()
        w.topbar.set_context(PAGE_LABELS[root], detail if detail != PAGE_LABELS[root] else 'Entrela · simulação científica')
        if hasattr(w, 'layout_controller'):
            w.layout_controller.timer.start()
        w._update_tutorial()

    def is_active(self, key):
        w = self.window
        if key not in w.pages:
            return False
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

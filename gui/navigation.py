"""Destinos principais e rotas internas, sem alterar os registros científicos."""

ROOT_ITEMS = [('dashboard', 'Início'), ('simulation', 'Laboratório'),
              ('analysis', 'Investigação'), ('history', 'Registros'),
              ('docs', 'Aprendizado'), ('settings', 'Preferências')]
PAGE_LABELS = dict(ROOT_ITEMS)
PAGE_LABELS.update(circuit='Circuito de portas', results='Resultados', bloch='Estados quânticos',
                   mitigation='Mitigação ZNE', comparison='Comparar execuções',
                   library='Anotações da execução', documentation='Evidências e relatórios', examples='Exemplos prontos')
ROOT_FOR_PAGE = {key: key for key, _ in ROOT_ITEMS}
ROOT_FOR_PAGE.update(circuit='simulation', results='simulation', bloch='simulation',
                     mitigation='analysis', comparison='analysis', library='history',
                     documentation='history', examples='docs')
SECTION_PAGES = {
    'analysis': [('analysis', 'Estudos e varreduras'), ('mitigation', 'Mitigação ZNE'), ('comparison', 'Comparações')],
    'history': [('history', 'Execuções salvas'), ('library', 'Anotações'), ('documentation', 'Evidências e relatórios')],
    'docs': [('examples', 'Exemplos prontos'), ('docs', 'Conceitos e manual')],
}

# Destinos visíveis: as áreas de trabalho são contêineres, não substitutos
# dos acessos às funcionalidades. A ordem também define o percurso por teclado.
NAV_ITEMS = [
    ('dashboard', 'Início'),
    ('simulation', 'Configurar simulação'),
    ('circuit', 'Editor de circuitos'),
    ('results', 'Resultados'),
    ('bloch', 'Estados quânticos 3D'),
    ('analysis', 'Estudos e varreduras'),
    ('mitigation', 'Mitigação ZNE'),
    ('comparison', 'Comparar execuções'),
    ('history', 'Histórico de execuções'),
    ('library', 'Anotações da execução'),
    ('configurations', 'Configurações salvas'),
    ('documentation', 'Relatórios e exportações'),
    ('examples', 'Exemplos prontos'),
    ('docs', 'Conceitos e manual'),
    ('settings', 'Preferências'),
]
NAV_LABELS = dict(NAV_ITEMS)
NAV_GROUPS = [
    ('lab', 'Laboratório', 'group-lab', ('simulation', 'circuit', 'results', 'bloch')),
    ('research', 'Investigação', 'group-research', ('analysis', 'mitigation', 'comparison')),
    ('records', 'Registros', 'group-organize', ('history', 'library', 'configurations', 'documentation')),
    ('learning', 'Aprendizado', 'group-start', ('examples', 'docs')),
]
NAV_ACTIONS = {'configurations'}

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
# Destinos visíveis: as áreas de trabalho são contêineres, não substitutos
# dos acessos às funcionalidades. A ordem também define o percurso por teclado.
NAV_ITEMS = [
    ('simulation', 'Simulação'),
    ('circuit', 'Circuitos'),
    ('results', 'Resultados'),
    ('bloch', 'Estados 3D'),
    ('comparison', 'Comparar execuções'),
    ('analysis', 'Estudos e varreduras'),
    ('mitigation', 'Mitigação ZNE'),
    ('dashboard', 'Projetos'),
    ('history', 'Histórico'),
    ('notebook', 'Caderno'),
    ('catalog', 'Biblioteca'),
    ('docs', 'Aprender'),
    ('settings', 'Preferências'),
]
NAV_LABELS = dict(NAV_ITEMS)
NAV_GROUPS = [
    ('lab', 'Laboratório', 'group-lab', ('simulation', 'circuit', 'results', 'bloch')),
    ('research', 'Investigação', 'group-research', ('comparison', 'analysis', 'mitigation')),
    ('records', 'Acervo', 'group-organize', ('dashboard', 'history', 'notebook', 'catalog')),
]

ROOT_FOR_PAGE.update(catalog="catalog", notebook="notebook")
PAGE_LABELS.update(catalog="Biblioteca", notebook="Caderno", dashboard="Projetos", history="Histórico de execuções", analysis="Estudos e varreduras", docs="Aprender")

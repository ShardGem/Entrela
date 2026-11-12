"""Destinos principais e rotas internas, sem alterar os registros científicos."""

ROOT_ITEMS = [('dashboard', 'Início'), ('simulation', 'Laboratório'),
              ('analysis', 'Investigar'), ('history', 'Execuções'),
              ('docs', 'Aprender'), ('settings', 'Preferências')]
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

# Entrela 0.24 — interface organizada por tarefa

A navegação agora apresenta seis destinos: **Início, Laboratório, Investigar, Execuções, Aprender e Preferências**. As funcionalidades existentes continuam disponíveis dentro do seu contexto. A splash restaurada, a identidade Entrela, os três temas e os nomes no menu estreito foram preservados.

## O que mudou

| Contexto | Organização |
|---|---|
| Laboratório | Duas etapas, Preparar e Resultados. Um seletor escolhe a atividade de cada etapa. |
| Preparar | Evolução por Hamiltoniano e circuito de portas possuem rascunhos independentes. Configurações salvas abrem em janela própria. |
| Resultados | Gráficos, estados quânticos, circuito executado, dados, interpretação e reprodutibilidade acompanham a execução selecionada. |
| Investigar | Estudos e varreduras, mitigação ZNE e comparações. Os estudos são agrupados por evolução/precisão, ruído/parâmetros e avaliação da mitigação. |
| Execuções | Histórico, anotações da execução e evidências/relatórios. Selecionar duas linhas permite iniciar uma comparação. |
| Aprender | Exemplos prontos e conceitos/manual, com ajuda contextual ligada à tarefa atual. |
| Preferências | Aparência, acessibilidade, exportação e dados/backup em categorias separadas. |

O editor reúne arquivo e desenho em um menu, mantém desfazer/refazer e zoom próximos ao circuito e recolhe a fase global em Avançado. A biblioteca de revisões, os modelos, as explicações das portas e a execução permanecem disponíveis.

A visualização 3D possui um inspetor lateral para câmera, etapa, estados locais e métricas. Em espaços menores, o inspetor pode ser recolhido. Os controles de reprodução trabalham com snapshots armazenados. Quando uma execução contém somente o estado final, esse estado pode ser inspecionado, com reprodução desabilitada e indicação explícita de que não há trajetória intermediária.

Os resultados destacam três métricas: fidelidade, pureza e energia. A infidelidade continua disponível na interpretação/ajuda da fidelidade. Valores pequenos usam notação científica; os valores originais ficam nos dados e em tooltips, sem arredondar o registro científico. Comparações apresentam as diferenças B − A e uma visualização específica das métricas numéricas.

Exportar reúne ações da execução selecionada. PDF, pacote ZIP e GIF possuem preparação contextual, sem exigir mudar para a página de evidências. Essa página continua permitindo gerenciar as fontes e os estudos relacionados. Tabelas compartilham cópia por teclado e exportação da tabela exibida; os arquivos científicos CSV/JSON completos continuam disponíveis nas ações próprias.

## Correspondência com os 30 pontos da revisão

| Pontos | Entrega |
|---|---|
| 1–2 · Navegação e camadas | Seis destinos; etapas de laboratório e seletores de atividade substituem a exposição simultânea de todas as páginas. |
| 3–4 · Rascunho, execução e modalidades | Contexto distingue edição e resultado; Hamiltoniano e circuito são rotas explícitas. |
| 5 · Resultados e 3D | Mesmo laboratório; consulta do estado final separada da evolução registrada. |
| 6 · Caderno e configurações | Anotações em Execuções; parâmetros reutilizáveis em janela própria. |
| 7 · Editor | Comandos agrupados, fase global avançada e execução acessível. |
| 8 · Exportações | Menus e preparação no contexto; gerenciamento das evidências preservado. |
| 9 · Rolagem | Gráficos têm área própria; preferências usam uma categoria por vez; formulário mantém espaço utilizável com texto ampliado. |
| 10 · Estudos | Três famílias pesquisáveis pelo seletor, preservando os oito estudos. |
| 11 · Histórico | Detalhes ao lado em telas largas e foco nos detalhes em espaços menores, com retorno à lista. |
| 12 · Comparação | Seleção A/B, critério, diferenças resumidas e seletor de visualização; métricas deixam de disputar altura com todos os gráficos. |
| 13 · Início | Execuções recentes no topo e uma ação principal para criar experimento. |
| 14–15 · Formulários e ações | Largura limitada onde adequado; comandos secundários agrupados; nomes de salvamento indicam seu escopo. |
| 16 · Controles 3D | Reprodução próxima da cena; inspeção organizada lateralmente; ampliação restaura a disposição. |
| 17 · Figuras | Histogramas, estudos e curvas de probabilidades utilizam renderizadores compartilhados; os relatórios incluem probabilidades com o mesmo critério de seleção. Estilos de tela e documento permanecem próprios de cada meio. Nos relatórios, a seleção padrão é pelos maiores picos da trajetória; seleções manuais da tela podem ser exportadas pelas ações de figuras, mas não substituem automaticamente esse perfil do relatório. |
| 18–21 · Números e tabelas | Notação científica, precisão nos tooltips/dados, unidades explícitas, nome em destaque no histórico e datas legíveis. Cópia respeita a ordem visual das colunas. |
| 22–23 · Textos e ajuda | Orientações curtas por atividade, ajuda progressiva e âncoras específicas para circuitos, estados e preferências. |
| 24 · Salvamento | Salvar execução, salvar revisão, salvar parâmetros e salvar anotações continuam ações distintas. Execução já salva recebe indicação própria. |
| 25–26 · Aprendizado e preferências | Entradas por finalidade e categorias, sem remover exemplos, tutorial ou conceitos. |
| 27 · Disposição | Divisores, categorias e últimas atividades são persistidos. Restaurar disposição preserva parâmetros e registros. |
| 28–29 · Componentes e coordenação | Áreas de trabalho, navegação, disposição, formatação e ações de tabela têm componentes/contratos próprios. O motor científico é preservado. |
| 30 · Verificação | Testes de fluxo, matemática, persistência, exportação, teclado, temas, geometria e empacotamento; validação manual nativa no Windows permanece pendente. |

## Capturas e reprodução

As **66 capturas** desta entrega estão em [screenshots/0.24.0](screenshots/0.24.0/README.md), organizadas por módulo. O manifesto registra dimensões, escala, hashes, cenários e estudos calculados. As 61 capturas da janela principal são renderizadas em 3840 × 2160, sem ampliação posterior. Splash e diálogos mantêm dimensões próprias registradas no índice.

```bash
python scripts/capture_gallery.py --output docs/screenshots/0.24.0 --scale 2 --overwrite
python scripts/verify_gallery.py docs/screenshots/0.24.0
```

Os cenários são simulações executadas em armazenamento temporário, com configurações e sementes registradas. Servem para documentar a aplicação; não são resultados do TCC nem medições de hardware. ZNE estima observáveis e não fornece um estado mitigado com fidelidade/pureza físicas.

## Verificação e limites

A suíte completa passou com **658 testes em 423,51 s**. Após os últimos ajustes de exportação, disposição e reprodutibilidade visual, uma rodada complementar passou com **78 testes em 106,55 s**. O wheel foi aberto fora do checkout e seus **120 módulos Python** foram conferidos contra os fontes. O fluxo real percorreu as 14 páginas, simulações ideais/ruidosas com e sem snapshots, ZNE, tutorial, importação/exportação e reabertura. A verificação de dependências e os hashes/dimensões das 66 capturas também passaram. O [registro da validação](validacao-interface-0.24.json) detalha as verificações locais. As verificações locais utilizam Qt offscreen no Linux. A CI contempla Linux e Windows com escala de tela ampliada; a abertura do wheel usa a versão corrente do projeto, sem depender de um nome de versão antigo. Execução da CI e validação manual nativa não devem ser confundidas com os testes locais.

A disposição se adapta ao espaço disponível; telas muito pequenas ou texto ampliado podem exigir rolagem e recolhimento do inspetor. A restauração da disposição é independente de restaurar preferências e de restaurar backup. Recursos científicos novos do plano P2 continuam fora desta revisão da interface.

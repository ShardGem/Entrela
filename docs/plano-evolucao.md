# Plano de evolução do Entrela

Este plano ordena as propostas pela contribuição ao TCC: resultados confiáveis e reproduzíveis primeiro; depois, experimentação mais fluida, investigação científica e distribuição. A aplicação continua sendo um instrumento de simulação computacional. Dados simulados não representam medições de hardware físico.

Não é necessário refazer o que já existe. O Entrela já possui simulação ideal e ruidosa, snapshots, referências exatas, métricas de estado, ZNE, benchmarks, varreduras, comparações, editor versionado, caderno, recuperação de rascunhos e exportações CSV/JSON/ZIP/PNG/SVG/PDF/GIF/LaTeX. A primeira entrega deste plano corrige limites desses recursos e acrescenta ferramentas que ajudam a interpretá-los.

Na versão 0.21, o histórico ganhou consulta gráfica de circuitos sem edição, compartilhando o componente do laboratório. O item 16 foi concluído, e o item 17 passou a utilizar renderizadores científicos comuns para distribuições, estudos e métricas. As escolhas de séries dos relatórios continuam seguindo o perfil de exportação; ampliar essa personalização permanece no plano.

Na versão 0.22, a revisão visual contínua ganha três estilos compartilhados: Grafite (padrão), Claro científico e Azul escuro. Títulos repetidos e contornos foram reduzidos, e as métricas de Resultados se adaptam ao espaço e à escala de texto. A [galeria comparativa](galeria-interface.html) e o [guia da interface](interface-0.22.md) registram o que foi implementado e a sequência de organização da simulação, área 3D, gráficos e preferências. Essa etapa não conclui a reorganização de todos os fluxos.

Na versão 0.23, o dimensionamento das abas passa a considerar o conteúdo aberto, os gráficos se empilham em janelas menores e o modo guiado recupera espaço para os campos. A área 3D agrupa detalhes e permite recolher a câmera, preservando a etapa e a disposição escolhida. A [galeria em alta resolução](screenshots/0.23.0/README.md) documenta as 14 áreas e as principais abas com simulações executadas. A revisão visual continua; preferências de disposição dos demais painéis e melhorias de tabelas extensas permanecem no plano.

Na versão 0.24, a navegação passa a seis destinos, com duas etapas no laboratório e atividades reunidas por contexto. Configurações reutilizáveis se separam das anotações, exportações recebem preparação contextual, o histórico permite comparar duas linhas e a área 3D passa a usar um inspetor lateral. A disposição de painéis e as atividades recentes são persistidas. As curvas de probabilidades têm renderizador comum para tela, HTML, PDF e pacote científico, com seleção pelos maiores picos e massa omitida identificada. A [entrega e os limites](interface-0.24.md) e a [galeria atual](screenshots/0.24.0/README.md) documentam os 30 pontos da revisão. Validação manual nativa no Windows e ampliação das escolhas de séries nos relatórios permanecem pendentes.

## P0 — Confiabilidade dos resultados e preservação dos dados

| Ordem | Trabalho | Critério de conclusão | Situação nesta etapa |
|---|---|---|---|
| 1 | Unificar a escala dos histogramas comparados | Uma frequência de 50% deve ter metade da altura de 100%, tanto na tela quanto na exportação | Implementado na 0.20 |
| 2 | Mostrar estados relevantes durante toda a evolução | Um estado inicialmente dominante continua representado; estados omitidos têm massa identificada como “Outros”; critério fica explícito | Implementado na 0.20 |
| 3 | Identificar incerteza pouco informativa na ZNE | Poucos shots e contagens extremas geram diagnóstico e intervalos por fator; erro padrão nulo não é apresentado como garantia de exatidão | Implementado na 0.20 |
| 4 | Reconstruir caches inválidos sem esconder experimentos válidos | Corromper o cache não altera a fonte nem remove uma execução íntegra do histórico | Implementado na 0.20 |
| 5 | Evitar perda de alterações concorrentes na biblioteca | Dois processos salvando configurações preservam ambas ou recebem erro explícito de bloqueio | Implementado na 0.20 |
| 6 | Retomar tutorial com evidência realmente exibida | A etapa de interpretação exige a execução correta em Resultados; as ações levam à etapa correspondente | Implementado na 0.20 |
| 7 | Filtrar projetos pelo campo exato | Um nome citado em observações de outro projeto não entra no agrupamento selecionado | Implementado na 0.20 |
| 8 | Comparar circuitos livres pelos parâmetros efetivos | Campos de Hamiltoniano não utilizados não impedem comparação; diferenças físicas relevantes continuam informadas | Implementado na 0.20 |
| 9 | Backup completo do espaço de trabalho | Backup inclui dados, bibliotecas, análises, protocolos, rascunhos e preferências; integridade verificada e restauração com confirmação e recuperação de falha | Implementado na 0.20 |

Os intervalos de amostragem não cobrem automaticamente o viés do modelo de extrapolação. ZNE estima observáveis; não produz, por si só, um estado mitigado com fidelidade/pureza físicas. Resultados determinísticos de matriz densidade não devem receber barras de erro inventadas a partir de várias seeds.

## P1 — Interface e fluxo de experimentação

| Ordem | Trabalho | Critério de conclusão | Situação nesta etapa |
|---|---|---|---|
| 10 | Monitor comum de tarefas | Nome, progresso real e cancelamento continuam acessíveis ao mudar de tela; não há segunda execução simultânea oculta | Implementado na 0.20 |
| 11 | Barra fixa de execução no editor | Executar/cancelar ficam visíveis em 1024 × 768 sem rolar toda a página | Implementado na 0.20 |
| 12 | Paleta pesquisável e lista de operações acessível | Busca/categorias preservam todas as portas; teclado e desenho selecionam a mesma operação | Implementado na 0.20 |
| 13 | Fontes e exploração dos gráficos | Fontes acompanham a preferência da interface; contagens e frequência são identificadas; exportação científica mantém estilo próprio | Implementado na 0.20 |
| 14 | Diagnóstico antes de executar | Casos como H nulo, autoestado e termos comutantes recebem explicação informativa, sem bloquear experimentos válidos | Implementado na 0.20 |
| 15 | Inspetor do estado global | Matriz densidade, espectro, coerência, pureza e entropia distinguem Bell puro de mistura com os mesmos vetores locais; usa estados já calculados | Implementado na 0.20 |
| 16 | Revisar densidade e navegação do caderno | Reduzir níveis redundantes e preservar rascunhos, seleção e identidade das configurações | Implementado na 0.21 |
| 17 | Unificar geração de figuras da tela e dos relatórios | Mesmos nomes, unidades, referências e critérios de seleção; estilos adequados a cada meio | Renderizadores compartilhados na 0.21; ampliar seleção de séries nos relatórios |
| 18 | Revisão visual transversal | Validar telas vazias, carregamento/erro, tabelas extensas, teclado, contraste, resoluções menores e escala de texto | Contínuo; ampliar a cada entrega |

Preservar a splash restaurada, os grupos inicialmente abertos, os nomes no menu estreito e a identidade Entrela. Alterar apenas componentes relacionados ao problema tratado. Preferências de redução de movimento e acessibilidade continuam obrigatórias.

Pedido adicional concluído na 0.21: circuito do histórico em diagrama interativo de consulta, com explicações, zoom e navegação, sem edição dos resultados nem substituição da execução aberta no laboratório. Reconstruções de registros antigos são identificadas explicitamente.

## P2 — Mais valor científico para o TCC

1. **Preparação por circuito seguida de evolução por Hamiltoniano.** Hoje são modalidades distintas. Projetar uma configuração versionada que registre separadamente preparação, evolução, medição e referências. Validar com soluções analíticas antes de integrar à interface.
2. **Campanhas executáveis e recuperáveis.** Expandir as varreduras existentes para conjuntos de configurações/estudos, com planejamento de custo, persistência por execução, cancelamento, checkpoints e retomada sem duplicar evidência.
3. **Observáveis gerais e ZNE de energia.** Permitir strings de Pauli e definir explicitamente aquisição por bases X/Y/Z, orçamento de shots, covariâncias e referências. O cálculo exato atual de energia continua disponível e identificado.
4. **Projetos como coleções de evidências.** Evoluir o agrupamento textual para relacionar execuções, protocolos, hipóteses, figuras e conclusões, com migração dos registros atuais.
5. **Hamiltonianos parametrizáveis.** Esclarecer o comportamento atual de “Custom” e permitir termos/coefs explícitos; parametrizar modelos hoje fixos. Verificar hermiticidade, ordem de qubits e unidades.
6. **Mais bipartições e medidas de emaranhamento.** Ampliar análises respeitando as condições de cada medida; não interpretar pureza local como testemunho universal de emaranhamento em estados mistos.
7. **Rotas didáticas verificáveis.** Acrescentar experiências guiadas T1/T2, erro de Trotter e ZNE com previsões do usuário e checagem sobre dados reais da simulação. Os conceitos e exercícios de texto existentes permanecem.
8. **Relatórios científicos personalizáveis.** Ampliar os modelos A4 existentes com discussão, referências e seleção de evidências; preservar texto vetorial, unidades e rastreabilidade de cada número.

Todos os itens desta seção estão pendentes. Cada um exige desenho de dados, teste científico independente e uma entrega própria, sem acrescentar resultados de demonstração como se fossem evidência experimental.

## P3 — Manutenção, desempenho e distribuição

1. Extrair gradualmente coordenação de tarefas, exportações e persistência de `MainWindow`, com contratos pequenos e testes de fluxo; evitar refatoração indiscriminada.
2. Medir inicialização, renderização 3D e histórico volumoso; otimizar a partir de perfis. Avaliar SQLite apenas se os limites do armazenamento atual forem demonstrados.
3. Mover logs para diretório gravável do usuário, com rotação e exportação de diagnóstico sem dados sensíveis desnecessários.
4. Produzir instalador Windows nativo e validar em máquina limpa. O wheel e a CI Windows existentes não equivalem a validar um instalador ou a interação nativa.
5. Preparar sequência de defesa com resultados salvos, navegação previsível e modo de consulta; aproveitar o modo de apresentação existente.
6. Expandir testes visuais e de desempenho na CI, usando tolerâncias e referências controladas para evitar testes frágeis.

## P4 — Pesquisa e extensões posteriores

Avaliar ruído por qubit, calibração/mitigação de leitura, tomografia de estado/processo, correção de erros, PEC/CDR, comparação entre simuladores, notebooks e hardware IBM. Definir antes o problema científico, a referência, os limites e o custo. Aumentar o limite de qubits depende de memória e desempenho medidos; não é apenas liberar um campo da interface.

## Regra de conclusão de cada entrega

Registrar o problema, a implementação e os testes realmente executados. Verificar migração/persistência, cancelamento, exportações e regressões dos fluxos envolvidos. Testes matemáticos devem usar estados/canais conhecidos ou referências independentes, e não apenas repetir o algoritmo testado. Limitações e itens pendentes permanecem visíveis neste documento.

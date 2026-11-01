# Análise técnica e acadêmica do Entrela para TCC 2

Base inspecionada: commit `0eb5c1ee1b5f337eb3576db3d7454958d2ec0f19`, branch `codex/entrela-workspace`. Análise realizada em 31/10/2026. O aplicativo não foi modificado nesta etapa.

O pedido anexado termina literalmente em “7.”. Foram preservadas as seis seções especificadas e acrescentadas configurações, prioridades e plano de implementação para completar os requisitos do texto.

## 1. Diagnóstico geral

O Entrela já é uma aplicação científica funcional, com separação inicial entre domínio, motor de simulação, persistência e interface. Não é apenas uma maquete. A base tem condições de sustentar uma demonstração acadêmica, mas ainda precisa de ajustes de apresentação científica, navegação visual e robustez para uma banca ao vivo.

Os três pilares devem orientar o trabalho:

- **Rigor científico:** o resultado precisa ter referência, convenções, unidades e limitações explícitas. Fidelidade ideal/ruidosa não equivale a erro de Trotter; distribuição de Bell em uma base não comprova sozinha emaranhamento.
- **Demonstração visual:** a visualização deve explicar estados efetivamente calculados. Câmera, animação e interpolação visual não podem sugerir evolução não simulada.
- **Experiência de uso:** as interações precisam produzir efeitos previsíveis, preservar parâmetros e dar retorno sem bloquear a janela.

### Método e limites desta revisão

Foram lidos o ponto de entrada, módulos científicos, repositório JSON, controlador principal, páginas, widgets, workers, dependências e testes. A revisão inclui inspeção de caminhos efetivamente conectados, execução da suíte e sondagens adicionais em dados temporários.

**Resultado:** 99 testes passaram, sem falhas ou skips, no ambiente Linux/Python 3.12 e nas dependências fixadas do projeto. Isso confirma os cenários testados; não certifica toda a interface, todos os modelos, todo arquivo externo nem todas as resoluções.

Foram executadas sondagens específicas de câmera, reprodução, precisão de parâmetros, entrada JSON e desempenho. A validação gráfica é offscreen; uso com mouse físico, leitores de tela, projetor e sistemas Windows/macOS ainda precisa de ensaio próprio.

### Inventário real

| Componente | Situação constatada |
|---|---|
| `app.py`, splash e shell | Inicialização PySide6, navegação por 11 páginas e splash com assets. Sem serviço web. |
| `core/types.py` | Configurações congeladas, validações e registros de resultado. Suporte a 1–6 qubits. |
| `core/circuits.py` | Ising, Heisenberg, XY e XXZ; Suzuki–Trotter de ordem 2/4; fronteira aberta/periódica e preparação zero/plus/Bell. `Custom` é compatibilidade legada com Ising, não editor. |
| `core/noise.py` | Despolarização e relaxamento térmico por operação. T₂ ≤ 2T₁; duração educativa fixa de 50 ns por porta no canal térmico. |
| `core/simulation.py` | Vetores ideais, matrizes densidade ruidosas, referência ideal, contagens, snapshots, métricas e metadados. |
| `core/metrics.py` | Fidelidade de Uhlmann ao quadrado, pureza e energia a partir do estado. |
| `core/mitigation.py` | ZNE de Z de um qubit; folding em u/cx, fatores ímpares, ajuste linear/quadrático e erro padrão de amostragem. Não reconstrói estado mitigado. |
| ConfigPanel e SimulationPage | Guiado/Avançado com os mesmos controles; etapas livres, validação térmica e execução. |
| Galeria | Doze presets imutáveis, busca, nível, objetivo e criação de cópia editável. |
| Tutorial | Sete etapas de Bell verificadas por ações, execução e reabertura real; pausa e progresso persistentes. |
| Resultados | Gráficos, interpretação determinística, tabela de contagens/probabilidades e metadados. Curva mostra até quatro estados mais prováveis no instante final. |
| Bloch | Traço parcial correto, vetor local e pureza local; snapshots reais, reprodução, slider e velocidade. Zoom dedicado não implementado. |
| Circuito | Diagrama textual. Não há seleção de portas ou execução visual porta a porta. |
| Histórico/comparação | JSON com estados complexos, reabertura, busca e comparação conservadora de sistemas/protocolos iguais. Distribuições são normalizadas. |
| Exportações | CSV, JSON completo, ZIP com JSON/CSV/circuito e figuras PNG. A importação pela interface é JSON; ZIP não é importado diretamente. |
| Configurações | Shots padrão; modo, rascunho e tutorial persistem por QSettings. Não há escolha funcional claro/escuro nem preferências gráficas completas. |
| Arquivos vazios/legados | `gui/widgets/metric_card.py` e `status.py` estão vazios. O MetricCard usado está em `card.py`; o status usado está em `simulation.py`. `gui/styles.py` é legado, não o tema aplicado pelo shell. |

## 2. Pontos fortes

1. O domínio científico não depende de widgets para executar uma simulação.
2. A matriz densidade representa ensembles ruidosos, permitindo pureza e fidelidade com significado físico.
3. A referência de fidelidade é identificada como o mesmo circuito Trotter ideal; a interpretação não inventa um estado mitigado.
4. Os testes incluem exponencial de matriz independente, despolarização analítica, Bell, oscilação de spin, reprodutibilidade e folding unitário.
5. O ruído térmico valida o limite físico correto; a sugestão de correção exige clique.
6. Os snapshots exibidos são estados calculados, sem interpolação de vetores puros tratada como física.
7. Os modos compartilham controles e mantêm parâmetros. Exemplos são copiados, sem alteração do catálogo.
8. Configurações de execução são imutáveis; registros distintos preservam a simulação e a análise ZNE.
9. Há escrita atômica, leitura legada, proteção de resultados não salvos e cancelamento cooperativo, sem destruição forçada de threads.
10. Código, testes e scripts estão versionados no remoto; a implantação deixou de depender apenas da máquina temporária.

## 3. Problemas identificados

### Evidências reproduzidas

| ID | Evidência e origem | Consequência | Prioridade |
|---|---|---|---|
| P01 | `validate_result()` não verifica que `metadata` seja um dicionário. Um JSON versão 2 com `metadata:null` foi aceito por `_deserialize()`, mas `ResultsPage.show_experiment()` lançou `AttributeError`. `_open_experiment()` não captura esse tipo. | Um registro malformado pode interromper o slot de abertura e deixar uma tela parcialmente atualizada. Não é uma falha de toda execução normal. | Crítica para robustez de arquivos externos/histórico. |
| P02 | `ConfigPanel` usa `setDecimals(6)`. Na sondagem, J=0,123456789 tornou-se 0,123457 após `load_config()` e `get_config()`. | O resultado salvo permanece intacto, mas reexecutar o formulário não preserva necessariamente os parâmetros importados. | Alta; crítica se a demonstração depender de reprodução nessa precisão. |
| P03 | Um evento `scroll_event` para cima não alterou a matriz de projeção de Bloch. Não há handlers próprios de roda nem controles de câmera. | A funcionalidade de zoom solicitada ainda não existe. | Alta. |
| P04 | `_on_tick()` usa módulo pelo número de snapshots. Após o último índice, voltou para zero. Os rastros continuam acumulando pontos. | A linha entre o estado final e inicial pode sugerir uma trajetória que não foi simulada. | Alta, especialmente no pilar visual/científico. |
| P05 | `_on_slider()` retorna durante reprodução. Na sondagem, o slider foi para 3 e o estado continuou no índice 0. | Controle e visualização podem discordar até a próxima atualização do timer. | Alta. |
| P06 | Captura em 1024×768 com ajuda aberta: texto do dock quebrado em fragmentos, resumo cortado e ações da coluna direita parcialmente fora da área visível. | A resolução mínima aceita não garante uma demonstração utilizável com painéis abertos. | Alta para apresentação em projetor. |

### Limitações confirmadas por inspeção

- **Animação:** o timer é de 33 ms e avança snapshots por um acumulador. Com cinco snapshots, 1x percorre um ciclo em aproximadamente 165 ms de agenda do timer, sem considerar renderização. Isso não é tempo físico e pode ser rápido demais para explicar. Falta parada no fim, opção explícita de loop, limpeza do rastro em saltos e indicação da duração de reprodução.
- **Desempenho na thread gráfica:** simular está no worker; salvar/validar JSON, reler todos os registros, preparar Bloch, atualizar tabelas e redesenhar gráficos estão na interface. `_refresh_history()` desserializa estados completos de todos os experimentos a cada atualização.
- **Medição representativa:** em 6 qubits, 20 passos, ruído padrão, 128 shots e seed 42: aproximadamente 0,214 s para simular, 0,236 s para salvar, 0,093 s para reler um registro e 6,40 MiB de JSON. É uma medição única nesta máquina, não garantia de desempenho. Uma biblioteca extensa precisa de benchmark próprio.
- **Recursos:** a interface limita passos/shots, mas o domínio não impõe orçamento de memória, quantidade de snapshots ou duração. Arquivos externos podem solicitar tarefas muito maiores. Density matrices crescem como 4ⁿ; listas JSON ampliam bastante o custo.
- **Câmera/legibilidade:** todos os qubits ficam em uma fila horizontal, com o mesmo espaço para seis qubits e para um. As cores dos qubits 1 a 5 são iguais em partes do painel; há seis tokens de cor, mas o código frequentemente só distingue qubit 0 dos demais.
- **Rigor da legenda local:** pureza local baixa aparece em vermelho. Em Bell ideal isso é consequência esperada do emaranhamento, não um erro. Texto e cor precisam distinguir mistura local por correlação de degradação global.
- **Resultados científicos:** a referência exata existe nos testes, não como curva configurável no produto. Não há curva de convergência Trotter, métricas por instante ou medida explícita de emaranhamento.
- **ZNE:** o erro padrão informado cobre amostragem sob o ajuste adotado; não cobre viés de extrapolação. A interface não mostra ajuste, resíduos, referência ideal de Z ou sensibilidade à escolha dos fatores. Três pontos com ajuste quadrático não fornecem graus de liberdade para diagnosticar resíduos de ajuste.
- **Ruído:** T₁/T₂ são aplicados por porta com duração fixa, não por tempo ocioso nem por calibração real. Isso é uma escolha explícita do modelo, não um erro automaticamente corrigível por trocar um rótulo.
- **Circuito:** texto estático; nenhuma ligação selecionável entre termo do Hamiltoniano, porta, camada e snapshot.
- **Navegação visual:** a janela exige no mínimo 1020×720 e a barra lateral tem largura fixa de 200 px. Uma sondagem em 1024×768 abriu a janela; com ajuda lateral, a área central caiu para 899 px. A captura confirmou texto da ajuda excessivamente estreito e corte de resumo/ações na direita. Ajuda e tutorial competem pelo espaço do workspace; o layout precisa de comportamento adaptativo.
- **Ajuda:** `_show_help()` tenta usar o texto do campo como âncora e busca. Nomes como “J — acoplamento” não correspondem a todos os IDs do manual. A navegação contextual precisa de IDs estáveis, não rótulos visuais.
- **Persistência:** validações faltantes de metadados, duração, tags e coerência de alguns campos podem produzir registros aceitos que a GUI não suporta. Timestamps legados podem não ter fuso. Não há fluxo de inspeção/recuperação de arquivo corrompido na tela.
- **Organização:** `MainWindow` acumula navegação, arquivos, tutorial, rascunhos, worker, persistência e exportações; há dependência de membros privados entre módulos e exportação chama métodos privados do repositório. Vários arquivos têm código muito condensado, dificultando revisão acadêmica e manutenção.
- **Empacotamento:** o modo editável foi validado. Os assets estão fora dos pacotes Python e não há definição de distribuição deles em um wheel. Não se deve anunciar instalador desktop autossuficiente sem testar empacotamento e inicialização fora do checkout.

Não foi encontrada nesta revisão uma falha reproduzida que invalide o cálculo básico de Bell, Ising ideal testado, despolarização analítica ou matriz densidade ruidosa dos cenários cobertos. Isso é diferente de provar a correção de todas as combinações possíveis.

## 4. Lista de melhorias possíveis

Complexidade: B=baixa, M=média, A=alta. A viabilidade considera a base atual; não pressupõe reescrita.

| ID / funcionalidade | O que faz | Benefício ao usuário e ao TCC 2 | Complexidade / viabilidade | Dependências e alterações |
|---|---|---|---|---|
| M01 · Contrato de arquivos | Valida metadados, duração, tipos, IDs e relações entre arrays antes de aceitar um registro. | Evita interrupção ao reabrir dados; demonstra engenharia robusta. | M / alta | `repository.py`, adaptador de importação, testes de arquivos inválidos. |
| M02 · Reprodução exata | Mantém precisão dos valores e oferece reexecutar com a seed efetiva registrada. | Permite repetir uma evidência perante a banca. | M / alta | ConfigPanel, serialização de configuração e comando dedicado. |
| M03 · Playback científico | Para no fim; loop opcional; sincroniza slider, tempo e seleção; limpa rastro em saltos. | Evita interpretação visual incorreta e melhora explicação oral. | M / alta | BlochPage, testes de índice/tempo/rastro. |
| M04 · Zoom, pan e reset | Controla só a câmera de Bloch, com roda, limites e restauração. | Aproxima um qubit durante a demonstração sem alterar dados. | M / alta para zoom central; M–A para cursor 3D | Plano da seção 5. |
| M05 · Foco em um qubit | Seleciona qubit, maximiza esfera e mostra coordenadas, ρ reduzida e pureza local. | Torna seis qubits legíveis e explica redução de estado. | M / alta | Estado reduzido já calculável; seletor e layout adaptativo. |
| M06 · Ideal × ruidoso sincronizado | Sobrepõe Bloch e probabilidades no mesmo instante, com legenda inequívoca. | Mostra visualmente o efeito do ruído, sem depender só de números. | M / alta | `ideal_statevectors` já persistido; sincronização temporal. |
| M07 · Métricas temporais | Mostra F(t), Tr(ρ²)(t), energia e inspeção por ponto. | Relaciona a evolução visual às medidas científicas. | M / alta | Métricas existentes, séries derivadas e seleção compartilhada. |
| M08 · Referência exata/convergência | Compara Trotter com exp(−iHt), varrendo passos/ordem. | Separa erro numérico de ruído e fortalece a metodologia do TCC. | M / alta para até seis qubits, com limites | SciPy já instalado; worker, caches e teste de convergência. |
| M09 · Observáveis de correlação | Mostra ⟨Zi⟩, ⟨ZiZj⟩ e um indicador apropriado de emaranhamento. | Evita inferir emaranhamento apenas pelo histograma. | M–A / alta se o domínio for bem delimitado | Definições/limitações: entropia reduzida para estado global puro; negatividade para mistos, por exemplo. |
| M10 · Diagnóstico ZNE | Gráfico por escala, ajuste, erro, Z ideal e comparação de erro absoluto. | Permite defender metodologia e resultados sem prometer melhoria. | M / alta | Dados já retornados; referência ideal, bootstrap opcional e documentação estatística. |
| M11 · Circuito explorável | Seleção de porta/camada revela ângulo, qubits, origem e estado correspondente. | Liga a física ao circuito e evidencia domínio técnico. | A / média | Preservar mapa termo→sintetização→portas; não inferir origem pela imagem. |
| M12 · Histórico leve | Lê resumos para listar e carrega matrizes só ao abrir; filtra e pagina. | Mantém interface fluida após muitas demonstrações. | M / alta | Índice/resumo versionado, migração e leitura assíncrona. |
| M13 · Orçamento de recursos | Estima memória/snapshots, limita tarefas e permite interromper entre pontos. | Evita travamento em uma sessão acadêmica. | M / alta | Validação de custo, política de execução e workers de tarefas grandes. |
| M14 · Modo apresentação | Aumenta texto útil, oculta distrações e encadeia cenas reproduzíveis. | Facilita leitura no projetor e reduz cliques durante a exposição. | M / alta | Presets existentes, preferências e navegação preservando o estado. |
| M15 · Relatório acadêmico | Exporta configuração, convenções, versões, gráficos, métricas e limitações em HTML/PDF. | Gera material rastreável para banca e texto do TCC. | M / alta | JSON e PNG existentes; template HTML; PDF via Qt PrintSupport ou dependência explicitada. |
| M16 · Varreduras paramétricas | Varia p, T₁/T₂, J ou passos e compara curvas. | Transforma exemplos isolados em experimentos científicos. | A / média-alta | Fila/cancelamento, orçamento, várias seeds, agregação e armazenamento. |
| M17 · Preferências úteis | Persiste câmera, velocidade, densidade visual, modo e padrões de execução; restaura por categoria. | Reduz preparação manual e erros em apresentações. | M / alta | QSettings já existe; esquema e defaults testados. |
| M18 · Tema claro e acessibilidade | Atualiza também gráficos, ícones, componentes e estados de foco. | Melhora contraste conforme projetor e necessidade de leitura. | M–A / média-alta | Remover cores hardcoded e dependências estáticas de PALETTE; testar ambos os temas. |
| M19 · Projetos/modelos pessoais | Agrupa execuções e salva configurações reutilizáveis com nome e notas. | Organiza hipóteses, séries e evidências do TCC. | M / alta | Entidades/índices adicionais sem reescrever o motor. |
| M20 · Empacotamento e ensaio | Gera distribuição com assets, testa máquina limpa e prepara plano offline. | Reduz dependência do computador de desenvolvimento na banca. | M–A / média | Assets como recursos, build por plataforma e teste real em hardware de apresentação. |

Não priorizar agora conexão a hardware remoto, IA para explicar resultados, personalização irrestrita de cores ou editor universal de circuitos. Têm custo alto e desviam das lacunas demonstradas. Explicações determinísticas e referências numéricas são mais úteis nesta fase.

## 5. Melhorias específicas na simulação de qubits

### Plano técnico exclusivo: zoom por roda do mouse

**Decisão recomendada:** manter `FigureCanvasQTAgg` e `Axes3D` em `BlochCanvas`. O programa não usa QGraphicsScene/QGraphicsView para essas esferas; chamar `QGraphicsView.scale()` não ampliaria o gráfico atual. Não há justificativa para migrar imediatamente para Qt3D/OpenGL.

1. Separar `CameraState` do estado quântico: escala, centro, azimute, elevação e limites iniciais. Zoom nunca muda ρ, probabilidades, métricas, número de qubits ou geometria matemática da esfera.
2. Conectar `mpl_connect('scroll_event', ...)` na área dos eixos. Roda para cima aproxima; para baixo afasta. Usar fator multiplicativo, por exemplo exp(0,10×passos), aceitando deltas fracionários de touchpad.
3. Adotar limites iniciais propostos de 0,5× a 3×, ajustáveis após ensaio com 1, 2 e 6 qubits. Preservar proporção dos eixos e limitar deslocamento para não perder toda a cena.
4. Guardar escala alvo e interpolar somente a câmera com QTimer de 16–33 ms. Coalescer eventos e usar `draw_idle()`; não reconstruir superfícies, traços parciais ou estados em cada evento da roda.
5. Criar ações `+`, `−` e `Restaurar visão`. O reset restaura centro, escala e orientação documentada. Exibir a ampliação atual e fornecer atalhos acessíveis.
6. Para zoom centralizado no cursor em 3D, o cursor define um raio, não um ponto único. Usar plano de foco do qubit selecionado e inversão da projeção; preservar aproximadamente sua projeção durante o zoom. Na primeira entrega, zoom no centro é aceitável se a limitação for explícita. Não prometer focalização 3D exata antes do protótipo.
7. Oferecer rotação por arraste e pan por botão/modificador consistente. Avaliar a navegação nativa do Matplotlib 3.10.9 antes de duplicar seus handlers; evitar conflito entre arraste, seleção e toolbar.
8. Consumir a roda apenas quando o cursor estiver sobre o canvas/eixos. Fora dele, rolar o formulário/página. Não alterar o tamanho da janela, fontes ou todas as telas.
9. Aplicar antialiasing/HiDPI já disponíveis e medir custo antes de aumentar a malha. Mais polígonos não corrigem uma câmera inadequada.

**Aceite:** zoom in/out com roda e touchpad; limites sem overshoot; reset repetível; pan recuperável; resize; 1/2/6 qubits; cursor fora do canvas sem interferência; nenhum callback duplicado após reabrir experimentos; probabilidades e métricas idênticas antes/depois; playback e zoom simultâneos sem dessincronizar o snapshot.

### Outras melhorias da simulação

Priorizar M03 e M05–M10. Mostrar sempre qubit selecionado, t real do snapshot, índice e se o estado é ideal ou ruidoso. A pureza local deve vir com “estado reduzido”, sem tratar o Bell ideal como falha. Saltos no tempo devem atualizar gráficos, dados e esfera de forma atômica.

Animações podem apresentar transições de câmera e de destaque. Se houver interpolação futura de trajetórias para suavidade, distingui-la dos pontos simulados e não alimentar métricas ou inferências físicas com os frames visuais.

## 6. Modernização da interface e experiência de uso

A direção atual — fundo #080C12, superfícies #111923 e ciano como destaque — é adequada. Evoluir a consistência em vez de aplicar outra identidade sem necessidade.

- **Hierarquia:** experimento e estado da execução primeiro; ações primárias claras; detalhes avançados expansíveis. Evitar duas ações Executar com o mesmo peso visual sem necessidade.
- **Layout:** painel científico redimensionável; área de ajuda recolhível; seletor de qubit e uma esfera ampliada em telas menores. Testar 1280×720 e 1366×768 com escala de 125%/150%, não apenas o tamanho lógico da janela.
- **Tipografia:** fonte de interface com fallback e números tabulares; aumentar corpo em modo apresentação. Não impor fonte inexistente como requisito de funcionamento.
- **Ícones:** exemplos e comparações precisam de mapeamentos próprios; no catálogo atual nem todos os IDs têm desenho. Sempre manter rótulo ou nome acessível.
- **Componentes:** cards, tabela, toolbar, estados vazios, foco e tooltip padronizados. Remover gradualmente `styles.py` e stubs vazios após confirmar ausência de uso.
- **Feedback:** estágios percentuais atuais são marcos do motor, não uma previsão de tempo restante. Mostrar “preparando”, “simulando”, “calculando referência” e “salvando”; não apresentar ETA fictícia.
- **Erros:** resumir o problema, oferecer ação concreta e detalhes técnicos expansíveis; informar o caminho do arquivo inválido sem ocultar que ele foi preservado.
- **Navegação:** manter etapas livres e modos compartilhados; usar IDs estáveis para ajuda e um botão visível para retomar rascunho/tutorial. A paleta complementa os caminhos visíveis, não deve ser a única forma de descobrir importação.
- **Acessibilidade:** contraste medido, foco visível, alvos adequados, texto junto de cores, tabulação, nomes acessíveis e gráficos acompanhados por tabelas. Testes offscreen não substituem leitor de tela.

## 7. Configurações, arquitetura e qualidade técnica

### Preferências que agregam valor

Persistir modo, shots, seed padrão opcional, velocidade de reprodução, loop explícito, rastros, câmera inicial, qubit selecionado, tamanho de fonte e modo apresentação. Permitir restaurar separadamente visualização e execução, com confirmação apenas para perda real de configuração.

Tema claro/escuro é útil, mas depende da centralização de estilos e cores também nos gráficos. Personalização arbitrária da paleta tem retorno menor. Não expor opções internas do Aer sem explicar o efeito e validar combinações.

Preferências não devem reescrever snapshots de execução. Alterar duração de porta, ruído ou método pertence à configuração científica de um novo experimento, não a uma preferência visual silenciosa.

### Evolução arquitetural sem reescrita

1. Extrair de MainWindow serviços de execução, arquivos e navegação; manter a janela como coordenação.
2. Criar API pública de serialização e validação compartilhada, em vez de exportadores chamarem `_serialize()`/`_deserialize()`.
3. Separar índice leve de histórico e payloads científicos; carregar estados sob demanda.
4. Unificar seleção de instante/qubit em um modelo compartilhado para Bloch, curvas e dados.
5. Mover IO e preparação pesada de gráficos para tarefas apropriadas; somente atualização de widgets na thread principal.
6. Manter referência do worker até `QThread.finished`; continuar cancelamento cooperativo, com prazo/estado claros, sem `terminate()`.
7. Formatador, lint e type checking graduais nos contratos de fronteira; remover imports sem uso e código morto com testes.
8. Versionar esquema de preferências, dados e migrações; testar diretório read-only, disco cheio e arquivos parcialmente escritos.

### Lacunas de teste a fechar

Adicionar os seis casos reproduzidos P01–P06; traços parciais e pureza local de Bell; modelos não Ising contra referência independente; periodicidade; limites de recursos; propriedades de canais CPTP; restore com precisão; zoom/rotação/pan/reset; cancelamento durante ZNE; curvas temporais; várias seeds e incertezas; instalação por pacote com assets; ensaio real no sistema e projetor da apresentação.

## 8. Matriz de prioridade

Estimativas são dias úteis aproximados para uma pessoa familiarizada com o projeto, incluindo testes locais. Não são compromissos de prazo, não incluem redação do TCC, variam com a profundidade e não devem ser somadas mecanicamente.

| Prioridade / IDs | Impacto e benefício acadêmico | Esforço estimado | Risco / dependências | Esforço × retorno |
|---|---|---|---|---|
| Crítica · M01 | Evita abrir registros aceitos que quebram a GUI. | 1–2 dias | Baixo–médio; contrato JSON e legado. | Muito favorável. |
| Alta · M02 | Reprodutibilidade defensável. | 1–2 dias | Médio; arredondamento, seed e rascunhos. | Muito favorável. |
| Alta · M03 | Temporalidade e apresentação sem trajetórias falsas. | 1–2 dias | Baixo–médio; controles/rastros. | Muito favorável. |
| Alta · M04 | Inspeção visual dos qubits. | 2–4 dias; cursor 3D pode acrescentar 2–3 | Médio; projeção, eventos e playback corrigido. | Favorável. |
| Alta · M05/M06 | Legibilidade e comparação ideal/ruído. | 3–5 dias | Médio; seleção compartilhada e câmera. | Muito favorável. |
| Alta · M07/M08 | Evidência quantitativa e separação dos erros. | 3–6 dias | Médio; workers e referências numéricas. | Muito favorável. |
| Alta · M10 | Avaliação honesta de mitigação. | 2–4 dias | Médio; estatística, referência e gráfico de ajuste. | Favorável. |
| Alta · M12/M13 | Estabilidade com histórico e tarefas maiores. | 3–6 dias | Médio–alto; índice/migração e orçamento. | Muito favorável. |
| Alta · M14/M15 | Comunicação e documentação para banca. | 3–5 dias | Médio; exportação e dados validados. | Muito favorável. |
| Alta · M20 | Reduz risco de infraestrutura no dia. | 2–5 dias por plataforma | Médio–alto; build e máquina limpa. | Muito favorável perto da apresentação. |
| Média · M09 | Explica correlações/emaranhamento corretamente. | 3–6 dias | Médio–alto; definições para puros/mistos. | Favorável se ligado à pergunta do TCC. |
| Média · M11 | Aproxima operações, circuito e física. | 5–10 dias | Alto; provenance de síntese e editor visual. | Bom, após os fundamentos. |
| Média · M16 | Experimentos paramétricos e resultados mais ricos. | 5–10 dias | Alto; depende de M12/M13 e múltiplas seeds. | Alto retorno científico, maior custo. |
| Média · M17/M19 | Preferências e organização científica. | 3–6 dias | Médio; persistência e navegação. | Favorável. |
| Média · M18 | Leitura e acessibilidade em ambientes diversos. | 3–5 dias | Médio; remover cores hardcoded. | Favorável se o projetor exigir. |
| Baixa · cosmética | Sombras adicionais, animação do splash, mais decoração. | 0,5–2 dias | Baixo, mas pode prejudicar clareza. | Menor retorno. |

## 9. Plano de implementação e demonstração

### Etapa 1 — Correções e estabilidade

Resolver P01/P02, tipar fronteiras, garantir abertura atômica de um registro e preservar rascunhos. Medir histórico e estabelecer limites operacionais. Aceite: JSON inválido não interrompe a GUI; configuração de alta precisão reaparece sem mudança silenciosa; base de testes permanece verde.

### Etapa 2 — Visualização científica

Corrigir P04/P05 antes do zoom. Implementar câmera com roda e reset, depois foco em qubit, sobreposição ideal/ruidosa e curvas sincronizadas. Aceite: um único instante selecionado em todas as vistas, sem wrap implícito ou rastro falso; zoom não altera dados.

### Etapa 3 — Modernização consistente

Ajustar layout em resolução de projetor, toolbar, ajuda por ID, ícones, legendas locais e contraste. Evitar reescrever o shell. Aceite: configuração, execução e inspeção acessíveis sem controles cortados nas resoluções-alvo, com mouse e teclado.

### Etapa 4 — Configurações relevantes

Persistir câmera, velocidade, loop e densidade; restaurar por categoria. Tema claro somente após centralização de estilos. Aceite: reinício mantém preferências; modificar apresentação não muda resultados científicos.

### Etapa 5 — Recursos para banca

Adicionar referência exata/convergência, diagnóstico ZNE, relatório e modo apresentação. Introduzir varredura apenas se ajudar a hipótese principal e o orçamento de recursos estiver pronto. Aceite: cenários reproduzíveis, exportação com parâmetros/versões e interpretação que admite ausência de melhoria.

### Etapa 6 — Validação e ensaio

Executar regressões científicas e de interface, validar build em máquina limpa, medir memória/latência no equipamento real e ensaiar com projetor. Guardar dados e relatório exportados como apoio, identificados como resultados previamente calculados. Manter uma demonstração ao vivo curta e reproduzível.

### Roteiro acadêmico recomendado

1. Bell ideal: preparação H/CX, contagens 00/11, pureza global 1 e pureza local 1/2. Explicar por que um histograma isolado não é testemunha suficiente de emaranhamento.
2. Bell ou Ising com ruído: observar redução de correlação/fidelidade e contração dos vetores, diferenciando mistura local de ruído global.
3. Ising com referência exata: após M08, distinguir aproximação Trotter e ruído. Hoje essa referência está nos testes, não na tela.
4. ZNE: mostrar as escalas, o observável, a extrapolação e suas incertezas. Não anunciar ganho de fidelidade mitigada inexistente.
5. Reprodutibilidade: reabrir histórico, mostrar configuração/seed/versões e exportar o registro.

A melhor próxima entrega é um pacote pequeno: robustez de arquivo e precisão, playback correto, zoom/reset e foco de qubit. Essas mudanças atendem diretamente aos três pilares, antes de ampliar a quantidade de funcionalidades.

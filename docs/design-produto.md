# Entrela — especificação de experiência e design

Status: visão de produto. A base foi recuperada e integrada; os recursos entregues e limites estão em [Entrega do workspace](entrega-workspace.md). Projetos, varreduras e relatórios formatados ainda são evoluções futuras.

## Princípio de produto

Software científico que ensina durante o trabalho: bonito sem ser decorativo, didático sem ser infantil e poderoso sem ser intimidador. Uma pessoa sem Qiskit deve conseguir executar um exemplo; uma pessoa experiente deve encontrar parâmetros científicos, dados e detalhes técnicos.

Modo Guiado e Modo Avançado são apresentações da mesma configuração. Alternar o modo preserva valores, validações, resultados e identificadores. O modo não limita capacidades.

## Design system

### Tokens visuais

| Token | Valor inicial | Aplicação |
|---|---|---|
| background | #080C12 | Fundo principal |
| surface | #111923 | Painéis e menus |
| surface-raised | #192431 | Diálogos e elementos elevados |
| border | #344455 | Separadores discretos |
| text-primary | #EDF4FC | Conteúdo principal |
| text-secondary | #ACBACB | Descrições e unidades |
| accent | #67D8F5 | Foco, seleção e ações |
| on-accent | #080C12 | Texto de botão com fundo accent |
| success | #8EDDB4 | Conclusão, sempre com texto e ícone |
| warning | #F2CC81 | Atenção, sempre com texto e ícone |
| error | #FF9C9C | Erros, sempre com texto e ícone |

Usar Inter se disponível, com fallback na fonte sans-serif do sistema. Escala tipográfica: 12, 14, 16, 20, 28 e 36 px; corpo padrão 14–16 px. Dados numéricos usam algarismos tabulares e detalhes técnicos usam fonte monoespaçada. Espaçamento: 4, 8, 12, 16, 24, 32 e 48 px; raios: 6, 10 e 16 px. Evitar agrupar todo conteúdo em caixas; organizar por títulos, alinhamento e espaço.

Animações de 120–180 ms, respeitando redução de movimento. Contraste deve ser medido na implementação: mínimo de 4,5:1 para texto comum e 3:1 para texto grande e controles. Não depender só de cor. Foco visível, navegação por teclado e nomes acessíveis são requisitos. Ajuda disponível por clique e teclado, não apenas por hover.

### Componentes reutilizáveis

| Componente | Contrato e estados |
|---|---|
| AppShell | Navegação lateral, projeto atual, conteúdo e ajuda contextual; seleção ativa legível |
| ExperimentMap | Etapas clicáveis; pendente, válida, inválida, executando e concluída; acesso livre, execução exige validação |
| ParameterField | Rótulo, valor, unidade, faixa, microajuda, erro; mesmas regras em ambos os modos |
| ScientificHelp | Definição curta, consequência prática, fórmula expansível e exemplo |
| QuantityInput | ns, µs e ms; conversão para unidade canônica e rejeição de valores não finitos |
| PresetPicker | Explica parâmetros substituídos; pede resolução se houver alterações não salvas |
| RunControl | Validando, na fila, executando, cancelando, cancelado, concluído e falhou; impede envio duplicado |
| MetricCard | Valor, precisão, unidade, referência e origem; indisponível aparece como tal |
| ScientificPlot | Legenda, intervalo, tooltip, seleção temporal, tabela acessível e exportação |
| BlochView | Qubit, instante, ideal/ruidoso/sobreposição; coordenadas e estado reduzido associados |
| CircuitInspector | Porta selecionável, qubits, camada, parâmetros e origem quando conhecida |
| EmptyState | Explicação da área e ação útil; não inventa registros |
| ErrorPanel | Causa conhecida, correção concreta e detalhes técnicos expansíveis sem credenciais |
| CommandPalette | Ctrl+K; comandos e glossário pesquisáveis; Esc fecha e devolve foco |

## Mapa de telas

| Área | Conteúdo e principais saídas |
|---|---|
| Boas-vindas | Criar experimento, explorar exemplo ou tutorial; preferência de ajuda opcional |
| Início | Retomar experimento real, projetos recentes, execuções e aprendizado |
| Projetos | Criar, abrir, renomear e organizar experimentos científicos |
| Experimentos | Lista com filtros por projeto, estado e data; criar, duplicar e abrir |
| Workspace | Sistema → Hamiltoniano → Evolução → Ruído → Mitigação → Execução; resultados vinculados à configuração executada |
| Comparações | Seleção de execuções compatíveis, tabela de métricas e curvas alinhadas |
| Hamiltonianos | Biblioteca, convenções, equações e editor com validação |
| Modelos de Ruído | Presets educativos, parâmetros físicos e editor |
| Mitigação | Técnicas suportadas, requisitos, custo e limitações |
| Análise | Métricas, evolução e varreduras a partir de resultados reais |
| Histórico | Execuções imutáveis, erros, tempos, sementes e configuração original |
| Biblioteca | Exemplos somente leitura, favoritos e modelos pessoais |
| Aprender | Tutoriais, glossário, teoria, receitas e exemplos executáveis |
| Exportações | Artefatos gerados, formato, origem e destino |
| Configurações | Modo, ajuda, unidades, aparência e preferências de execução |

Organizar navegação em Trabalho, Ferramentas e Recursos. Em janelas estreitas, recolher a barra lateral e transformar a ajuda em painel sobreposto acessível. Evitar rolagem horizontal do formulário; tabelas e circuitos podem ter rolagem própria.

## Fluxos principais

### Primeiro uso e exemplo de Bell

1. Boas-vindas → Explorar um exemplo → Estado de Bell.
2. Exibir objetivo, circuito H(q0), CX(q0,q1), distribuição esperada e convenção de bits.
3. Experimentar cria cópia editável com novo identificador; exemplo original permanece intacto.
4. Executar valida configuração, registra snapshot, backend, versões e semente e inicia execução.
5. Resultados mostram contagens observadas e probabilidades esperadas separadamente. Idealmente apenas 00 e 11 aparecem; flutuações de contagem dependem dos shots.
6. Adicionar ruído cria nova configuração e nova execução. Comparar mantém ambas as referências.

### Experimento próprio

1. Criar nome e projeto, selecionando modo de apresentação.
2. Sistema: quantidade de qubits e estado inicial, respeitando capacidade real do backend.
3. Hamiltoniano: modelo, parâmetros, fronteira, equação e convenção de sinal explícita.
4. Evolução: método, ordem suportada, passos e tempo com unidades ou convenção adimensional documentada.
5. Ruído: nenhum, modelo suportado ou preset educativo; validar parâmetros imediatamente.
6. Mitigação: opcional, apenas técnicas compatíveis com backend e observáveis selecionados.
7. Execução: shots, semente, resumo e custo estimado apenas se houver base de cálculo.
8. Executar; navegar entre etapas é sempre permitido. Erros impedem execução e oferecem salto ao campo.
9. Resultados: Visão geral, Estados, Bloch, Distribuição, Evolução, Circuito, Métricas e Dados. Abas sem dados explicam o requisito e não exibem dados fictícios.

Alterar um parâmetro após executar marca a configuração como modificada. O resultado continua associado ao snapshot anterior; nova execução nunca reescreve a anterior.

### Validação e recuperação

Para relaxamento térmico, exigir T₁ > 0, T₂ > 0 e T₂ ≤ 2T₁, nas mesmas unidades. Com T₁=70 µs e T₂=180 µs, explicar o máximo de 140 µs. “Usar 140 µs” só altera o campo após ação explícita; permitir desfazer. Validar também shots e qubits inteiros positivos, probabilidades em [0,1], passos positivos e valores finitos. Regras específicas de ordem e método dependem do backend.

Falha de execução preserva configuração e diagnóstico, informa se há resultado parcial e permite tentar novamente. Cancelamento deve ser cooperativo; não anunciar término até confirmação do worker. Fechar com alterações não salvas oferece salvar, descartar ou continuar editando.

### Tutorial orientado a ações

Sete etapas: criar um qubit; selecionar |+⟩; observar +X na esfera; escolher evolução; adicionar ruído válido; executar; interpretar resultado. Cada etapa verifica a ação ou resultado esperado antes de avançar. Permitir sair e retomar, reiniciar com confirmação e consultar explicação sem perder o contexto. Mudanças manuais incompatíveis explicam como retomar a etapa.

### Comparação e análise

Selecionar execuções, verificar sistema, observável, unidades e convenção temporal. Incompatibilidades devem ser explicadas; não alinhar silenciosamente dados distintos. Comparar ideal, ruidoso e mitigado somente quando calculados. Exportar também metadados, sementes, versões, unidades e configurações.

Recuperação relativa de fidelidade: (F_mitigado − F_ruidoso)/(F_ideal − F_ruidoso), se denominador positivo. Caso contrário, marcar a razão como indefinida. Não prometer melhoria: resultados negativos devem aparecer. Estimativas mitigadas de observáveis não definem automaticamente uma matriz densidade física; fidelidade e pureza mitigadas só aparecem quando houver estado reconstruído válido e método documentado.

## Rigor científico e reprodutibilidade

- No Ising H = −J Σ ZᵢZᵢ₊₁ − h Σ Xᵢ, J positivo favorece alinhamento e J negativo antialinhamento; outras convenções precisam ser declaradas.
- Separar estado exato, matriz densidade, amostras e estimativas. Para estados puros, F=|⟨ψ|φ⟩|²; para estados mistos, documentar a convenção de fidelidade usada pela biblioteca.
- Pureza global Tr(ρ²) difere da pureza do estado reduzido de um qubit. Um estado de Bell globalmente puro possui vetor de Bloch local nulo.
- Mais shots reduzem incerteza de amostragem; não corrigem ruído físico nem erro de aproximação temporal.
- ZNE estima limites de observáveis por extrapolação e pode aumentar variância. Não oferecer como correção universal de estados.
- Registrar ordenação de bits, unidades, normalização, backend, versões, semente, tolerâncias e configuração completa. Semente não garante reprodução entre versões e plataformas distintas.
- Interpretações automáticas devem citar valores calculados e distinguir observação de hipótese causal. Sugestões de varredura são propostas de investigação.
- Presets “IBM-like” são exemplos educativos documentados, sem alegação de calibração atual de hardware.

## Organização proposta para PySide6

Separar domínio científico, adaptadores de simulação, persistência e apresentação. Um modelo de configuração compartilhado alimenta formulários guiado e avançado; validações pertencem ao domínio. Workers executam simulações fora da thread gráfica e emitem progresso por sinais. Widgets atualizam somente na thread da interface. Seleção de tempo sincroniza gráficos, estado e Bloch usando a mesma execução e índice temporal.

Entidades mínimas: Project, Experiment, ExperimentConfig, RunSnapshot, RunResult, ExampleTemplate, TutorialProgress e ExportArtifact. Snapshots de execução são imutáveis e possuem versão de esquema. Exemplos geram cópias; modelos pessoais armazenam configuração sem resultados por padrão. Formato de persistência e integração Qiskit ficam pendentes da inspeção dos simuladores.

## Entregas e critérios de aceite

| Etapa | Entrega | Evidência necessária |
|---|---|---|
| 1 | Tokens, shell, campos, ajuda e navegação | Teclado, contraste, estados vazios e layout estreito verificados |
| 2 | Bell e um qubit, execução e histórico | Testes do backend, distribuição de Bell e persistência após reinício |
| 3 | Ising, evolução e ruído | Convenções documentadas, validação T₂ e comparação com referência numérica |
| 4 | Resultados e comparação | Gráficos e tabelas concordam com dados exportados; seleção temporal sincronizada |
| 5 | Tutorial e biblioteca | Ações desbloqueiam etapas; cópias não alteram exemplos; retomada funciona |
| 6 | Mitigação e varreduras | Métodos efetivamente suportados, incertezas e casos sem melhoria demonstrados |

Critérios transversais: alternar modos não altera configuração; reiniciar recupera experimentos; falhas não congelam interface; números sem origem nunca são apresentados como resultado; exportação reproduz o snapshot selecionado. Testes científicos usam tolerâncias e referências independentes, não apenas capturas de tela.

## Próximo passo de implementação

O workspace compartilhado, a galeria e o tutorial de Bell foram implementados nesta entrega. Validar a branch preservada no GitHub e seguir o escopo documentado em [Entrega do workspace](entrega-workspace.md).

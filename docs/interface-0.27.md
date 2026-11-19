# Entrela 0.27 — projetos e bancada de experimentos

A entrega parte de `evolucao_entrela`, commit `866b99f` (0.26.0). A consulta ao GitHub e o `fetch` confirmaram o mesmo commit. As referências aprovadas orientaram composição e identidade; os números das imagens não foram usados como dados. Os cenários da galeria foram executados pelo motor do Entrela em armazenamento temporário.

## Estrutura e dados preservados

O aplicativo continua em PySide6, com Qiskit/Aer, NumPy/SciPy e Matplotlib. `MainWindow` coordena os trabalhadores existentes; não foi criado outro simulador ou outra cópia dos formulários científicos. `core/simulation.py`, portas, Hamiltonianos, ruído, métricas e cálculos de estudos permanecem preservados.

| Conceito na interface | Representação e persistência |
|---|---|
| Projeto | Chave textual existente em `WorkspaceLibrary.projects` e `annotations.project`; nomes e etiquetas anteriores continuam válidos |
| Experimento da bancada | Registro aditivo em `workspace.json/workbench`, com modalidade, rascunho e vínculos às execuções |
| Rascunho | Os mesmos controles serializados por `DraftController`/`DraftStore`, inclusive campos ainda inválidos do ponto de vista físico |
| Execução | `core.types.Experiment`: configuração, identidade, semente, estados, contagens e metadados próprios; a consulta não carrega seus parâmetros no rascunho |
| Modelo | Exemplo, configuração pessoal ou revisão de circuito; criar cópia preserva o trabalho anterior |
| Evidência | Execuções e estudos já existentes, comparações e índice aditivo de arquivos produzidos, com fontes e destino |
| Referência ideal | Mesmo circuito sem ruído, explicitamente distinto da evolução exata do Hamiltoniano |

`data/projects.py` usa as transações e a gravação atômica da biblioteca existente. A mudança é aditiva: registros legados não são renomeados nem convertidos em resultados novos. A validação de rascunhos é compartilhada com a recuperação anterior. A fonte inválida é preservada em caso de erro de leitura.

`gui/controllers/projects.py` coordena contexto e propriedade das tarefas. O trabalhador captura a configuração usada no início. Uma conclusão em outro trabalho permanece no monitor, com acesso ao resultado original. Estudos continuam ligados à fonte do trabalhador. Resultados que falharam ao salvar permanecem em memória e exigem salvar ou descartar explicitamente antes de encerrar.

## Telas e caminhos principais

- **Projetos:** escolher investigação, criar projeto, criar experimento por Hamiltoniano ou circuito, retomar rascunho e consultar execuções recentes. A comparação ideal aparece quando existem duas execuções salvas compatíveis; as duas fontes constam da descrição da ação.
- **Preparar:** etapas Sistema, Hamiltoniano, Evolução, Ruído e Execução; parâmetros ao centro, revisão à direita e execução fixa na base. A preparação ideal fica na etapa Sistema. Em janela compacta, revisão e parâmetros usam abas.
- **Circuito:** paleta, desenho, lista acessível de operações, inspetor, revisões, menus Arquivo/Editar, parâmetros e barra fixa. A última execução é evidência registrada; alterações do rascunho não alteram suas contagens.
- **Observar:** Medições, Evolução, Bloch, Estado global e Dados. Contagens, frequência observada e probabilidade calculada são identificadas separadamente. Curvas e Bloch compartilham a seleção de snapshot registrado.
- **Bloch:** foco e estados locais, referência sem ruído, trajetórias, câmera recolhível e reprodução na base. O seletor de visualização do inspetor conserva probabilidades e estado global no instante.
- **Comparar:** os seletores e a compatibilidade existentes continuam em uso, com distribuições, curvas, Bloch, configuração, métricas e observáveis ZNE. Não há interpolação de grades incompatíveis.
- **Estudos e ZNE:** cálculos, requisitos, planejamento, resultados, tabelas e reprodução existentes foram integrados ao cabeçalho. O zero da ZNE é fator de ruído efetivo zero. Métricas do estado de origem são identificadas como tal.
- **Histórico:** Visualizar consulta detalhes; Abrir resultados consulta a execução; Usar configuração cria uma base editável com as proteções existentes. Ordenação, filtros e comparação de duas linhas permanecem disponíveis.
- **Caderno:** Anotações, Evidências e Relatório. Anotações têm escopo explícito de projeto ou execução. O roteiro lista conteúdo e fontes; a geração usa o compositor A4 existente. As notas do projeto entram como interpretação do pesquisador, separadas dos resultados calculados.
- **Biblioteca:** exemplos, configurações e revisões de circuitos; a ação principal cria uma cópia editável. **Aprender** preserva conceitos, manual, exemplos demonstrativos e tutorial verificável de Bell.
- **Preferências:** Aparência, Acessibilidade, Execução, Exportação e Dados/backup. Azul Entrela é o padrão novo; perfis gravados têm prioridade. A prévia usa componentes da interface e dados reais quando há execução selecionada.

Ferramentas continuam acessíveis no menu **Ferramentas** e em **Buscar**, incluindo Histórico, Circuito, Estudos, ZNE, Configurações salvas e Relatórios. A navegação Preparar/Observar/Comparar aparece na bancada, sem ser repetida nas páginas de consulta, aprendizado ou preferências.

## Correções verificáveis

A validação térmica utiliza o mesmo caminho para formulário, resumo, botão e atalho. Com T₁ = 70 µs e T₂ = 180 µs, o aviso indica o máximo de 140 µs. Aplicar a correção altera o campo, elimina os avisos e habilita a execução imediatamente.

Abrir um resultado pelo histórico preserva o rascunho. Trocar de experimento protege os dois formulários, inclusive uma configuração fisicamente inválida ainda em elaboração. Ao trocar para um trabalho sem execução, os resultados anteriores são limpos em conjunto. Uma tarefa concluída em outro projeto não substitui os campos ou resultados do trabalho ativo.

A tipografia e as tabelas usam os componentes compartilhados; a fonte inclui algarismos tabulares quando o Qt oferece esse recurso. Câmera, parâmetros e painéis longos têm rolagem própria, enquanto ações essenciais ficam fora do formulário rolável.

## Validação e capturas

Os comandos e resultados efetivamente executados estão em [validacao-0.27.json](validacao-0.27.json). A suíte é separada em processos para liberar recursos Qt entre grupos. Os testes científicos anteriores continuam incluídos; novas regressões cobrem validação térmica, rascunhos, consulta, conclusão em outro contexto, falha de gravação e origem de artefatos.

A [galeria](screenshots/0.27.0/README.md) contém PNGs sem perdas, manifesto, hashes, configurações, contagens e estudos usados. Janelas de 1440 × 900 foram renderizadas a 2× (2880 × 1800); a janela compacta de 1024 × 768 com texto de 24 px foi renderizada em 2048 × 1536. Splash e diálogo de configurações mantêm tamanho próprio. Os arquivos de identidade e o comportamento da splash não foram alterados.

## Limites e verificação nativa

- Verificação realizada em Linux com **Qt offscreen**. Não houve sessão desktop nativa disponível nesta entrega. Aparência, teclado, diálogos e escala no Windows nativo ainda exigem revisão nessa plataforma.
- O wheel foi exercitado fora da árvore do repositório; isso não equivale a testar um instalador Windows.
- A interface oferece um roteiro de conteúdo do relatório. Ele não é uma prévia paginada exata do PDF A4 produzido pelo compositor.
- O índice de evidências conserva a localização dos arquivos exportados. Mover ou apagar um arquivo externo não altera a execução; o aplicativo informa a indisponibilidade e permite gerar novamente. Para transportar figuras e dados, use o pacote ZIP científico. O backup do espaço de trabalho conserva o índice; arquivos exportados fora da pasta de dados continuam em seus destinos originais.
- A comparação ideal no projeto utiliza execuções efetivamente calculadas e salvas. Não são criadas contagens artificiais a partir de probabilidades de referência.
- Permanecem os limites científicos do motor: 1–6 qubits, limites de passos e portas existentes, modelos educativos de ruído, e ZNE como estimativa de observável. A entrega não simula hardware físico como se fosse uma medição real.

# Auditoria técnica e de fluxo — etapa 0.19

## Base e método

A análise partiu do commit `5ec110e`, versão 0.18.1. Antes das alterações, foram lidos o controlador principal, as páginas, os workers, a configuração científica, os repositórios e os testes pertinentes. As áreas de análises, biblioteca pessoal e histórico receberam revisão específica; o núcleo científico recebeu leitura e execução de 78 testes de métricas, evolução, reprodução e comparação de Trotter. Esses testes passaram; não foi identificado erro matemático confirmado nas implementações examinadas.

Esta é uma auditoria de código, contratos, fluxos e casos testáveis, não uma demonstração formal de correção para toda combinação possível de entradas. A inspeção visual disponível neste ambiente usa Qt offscreen em Linux; não houve ferramenta de desktop nativo disponibilizada nesta sessão.

## Organização existente

| Camada | Componentes e responsabilidade |
| --- | --- |
| Interface desktop | PySide6: páginas, formulários, widgets compartilhados, navegação e preferências. Matplotlib desenha gráficos e Bloch. |
| Coordenação | `gui/main_window.py` liga sinais, mantém a execução selecionada, protege rascunhos, inicia/cancela workers e coordena persistência/exportações. |
| Cálculo assíncrono | `gui/workers/`: QThreads para simulação, análise, mitigação, comparação, leitura e exportação. |
| Domínio | `core/types.py`: configurações imutáveis e validação; `core/circuit_document.py`: circuito editável e linguagem limitada de ângulos. |
| Simulação | Qiskit/Aer em `core/simulation.py`, construção de circuitos, ruído e métricas. O mesmo motor serve ao formulário e ao editor. |
| Pesquisa | Análises temporais, referência exata, varreduras, benchmark, estudos e comparações em módulos próprios de `core/`. |
| Dados | `data/repository.py`: registros científicos JSON validados, com escrita atômica. Biblioteca pessoal, circuitos com revisões, rascunhos, protocolos e análises derivadas têm repositórios próprios. |
| Documentação | CSV/JSON/ZIP, figuras, animações e compositor PDF A4 são compartilhados entre fluxos de exportação. |

Não há aplicação web. Não faz sentido implementar atributos HTML como `aria-label`; o equivalente no botão Qt é `accessibleName`, com `accessibleDescription`, foco e ativação por teclado.

## Dependências e contratos que precisam ser preservados

- `MainWindow._current_experiment` é a referência da execução selecionada. Resultados, anotações e análises derivadas precisam apontar para ela ou para a fonte capturada pelo worker.
- `DraftController` liga sinais às instâncias existentes de formulário, editor e caderno. Criar cópias dessas páginas pode perder edições e recuperação.
- Configurações salvas do formulário Hamiltoniano não são circuitos salvos. Circuitos têm sua própria biblioteca e revisões. Projeto é um agrupador textual de execuções, não um objeto executável.
- Abertura de modelos e de execuções usa a proteção de substituição do rascunho. Abrir um resultado não deve sobrescrever silenciosamente um circuito em edição.
- Os identificadores internos de análises/parâmetros, o esquema dos resultados e a referência científica devem ser conservados mesmo quando os rótulos visíveis mudam.
- Cancelamento do Aer é cooperativo entre operações. A interface não deve prometer interrupção imediata de uma chamada já em andamento.

## Problemas comprovados e encaminhamento

| Prioridade | Problema | Encaminhamento da etapa |
| --- | --- | --- |
| Alta | A simulação troca automaticamente de página ao terminar; configurar, editar portas e ler resultados exige navegação entre destinos. | Um laboratório com abas reutiliza as mesmas páginas, sem outro motor ou estado científico. |
| Alta | Abrir resultado de circuito livre conserva os parâmetros Hamiltonianos, mas podia copiar para esse rascunho o nome/descrição do circuito. | Abertura de circuito preserva as duas configurações, a identidade e o vínculo do rascunho Hamiltoniano. O resultado e seu caderno são selecionados separadamente. |
| Alta | Botão Visualizar fica menor que seu texto em 1024 × 768. | Ação de olho sem texto, tooltip e nome acessível Visualizar, foco e ativação por teclado; destino permanece vinculado ao ID após ordenar/paginar. |
| Alta | Artefato de análise incompleto passa pela validação e pode trocar `self.data` antes de falhar no desenho, deixando ações associadas a dados inválidos. | Validação dos campos necessários por tipo e atualização da interface somente após aceitar o artefato. Arquivos inválidos são preservados. |
| Alta | Tabela temporal usa “Tempo (ℏ=1)” para circuito livre, apesar de os valores serem índices de portas. | Unidade contextual coerente com o gráfico e os metadados, sem mudar valores. |
| Média | Abrir análise salva não sincroniza o formulário; executar novamente pode calcular outro tipo. | Restaurar modo/opções suportados e distinguir visualização histórica de nova execução/reprodução. |
| Média | “Projetos e Modelos” promete um gerenciador inexistente e não esclarece a origem do modelo salvo. | Caderno e configurações, com explicação do agrupamento Projeto e dos parâmetros do formulário. |
| Média | Biblioteca pessoal valida apenas contêineres: anotações internas inválidas causam erro de atributo na interface. | Validar registros internos e configurações antes de usar ou gravar; preservar o arquivo e informar o diagnóstico. |
| Média | Opções de análise incompatíveis só falham no worker; parâmetros aparecem como códigos internos. | Exibir requisitos, rótulos/unidades e exemplos por parâmetro; manter os códigos em `currentData()`. |
| Técnica | Controlador principal e editor são grandes e concentram responsabilidades. | Acrescentar um componente de composição do laboratório, preservando os contratos. Divisões adicionais exigem refatorações específicas com cobertura, sem reescrita geral nesta etapa. |

## Consistência científica examinada

Fidelidade usa a definição quadrática de Uhlmann; pureza é calculada do estado, e energia exige observável hermitiano. A referência de Trotter exata é separada do mesmo circuito sem ruído. O ruído térmico converte µs para ns e registra durações de portas. ZNE usa folding por identidades e fatores efetivos ímpares; extrapola observáveis e não reconstrói uma matriz densidade mitigada. Shots amostram medições e não definem, por si, incerteza das métricas exatas do ensemble.

As limitações de 6 qubits, 200 passos e tamanho das varreduras são intencionais. Sementes não garantem resultados idênticos entre versões e plataformas. Não foram introduzidos resultados físicos, números projetados ou novos métodos científicos para preencher a interface.

## Verificação da implementação

Os resultados finais de integração e as capturas desta etapa são registrados no guia da entrega após os testes. Os testes existentes do núcleo, dos repositórios, da recuperação, dos protocolos e das exportações devem continuar passando, junto dos novos casos de navegação, contexto, acessibilidade e artefatos inválidos.

Na revisão de integração, foi verificado também o dimensionamento das abas. O conteúdo de resultados não deve forçar espaço vazio na aba de configuração; os estudos usam rolagem por aba, com ações e progresso fora dela. Em fonte ampliada, formulários extensos e gráficos ainda podem exigir rolagem vertical. As capturas finais e os testes registram os cenários efetivamente conferidos.

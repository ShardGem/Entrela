# Revisão para a primeira distribuição desktop

A revisão parte de `redesenho-bancada-cientifica`, commit `2111200748f670cf89c37ecfcb473793a20c61a0`, a branch com o commit mais recente no remoto quando a análise começou. O checkout anterior de `evolucao_entrela` foi preservado. O trabalho está na branch `refinamento-primeira-distribuicao`.

O Entrela já dispõe de modelos científicos, execução em trabalhadores Qt, histórico, projetos, rascunhos, editor versionado, comparações, estudos, backup e exportações. A preparação para distribuição deve consolidar esses fluxos e verificar a instalação real antes de ampliar o catálogo de funcionalidades.

## Arquitetura e contratos preservados

| Camada | Componentes | Responsabilidade e observação |
|---|---|---|
| Inicialização | `gui/application.py`, `branding.py`, `splash.py` | Identidade, fontes e entrada desktop. A splash foi preservada. Importações e construção antecipada de páginas ainda precisam de perfil de desempenho. |
| Coordenação | `gui/main_window.py`, `gui/controllers/` | Navegação, projetos, rascunhos, aparência, disposição, tarefas e recuperação. `MainWindow` ainda concentra coordenação; extrações futuras devem ter contratos e testes de fluxo. |
| Interface | `gui/pages/`, `gui/widgets/`, `gui/theme.py`, `gui/design_system.py` | Formulários, gráficos, tabelas e inspetores usam componentes compartilhados e as instâncias existentes ao alternar a disposição. |
| Execução | `gui/workers/`, `core/simulation.py`, `core/analysis.py`, `core/mitigation.py` | Cálculos separados da apresentação, parâmetros registrados, referências e semente efetiva. Cancelamento é cooperativo; uma chamada nativa em andamento pode precisar terminar. |
| Ciência | `core/types.py`, `circuits.py`, `noise.py`, `metrics.py`, renderizadores | Configurações em dataclasses imutáveis, estados ideais/ruidosos e referências distintas. Nenhuma fórmula ou parametrização científica foi alterada nesta revisão. |
| Dados | `data/repository.py`, `workspace.py`, `projects.py`, `drafts.py` | Esquemas validados, gravação atômica de registros, bloqueio da biblioteca e caches derivados reconstruíveis. Dados ficam fora da instalação; preservar migrações e campos legados. |
| Documentação | `core/export.py`, `report.py`, `documentation.py`, `pdf_layout.py` | Dados, figuras e relatórios identificam a execução de origem. Arquivos de exportação não são a fonte primária dos registros. |

## Correções priorizadas

| Problema observado | Correção e comportamento esperado |
|---|---|
| O atalho Ctrl+K e sua indicação voltaram ao menu, contrariando a preferência já definida. | Removidos o atalho e o indicador. O botão Buscar continua acessível por clique e teclado. Os demais atalhos foram preservados. |
| Histórico podia mostrar o filtro do projeto anterior sob outro contexto. | O escopo acompanha a troca de projeto, distingue **Sem projeto** de **Todos os projetos** e mostra o filtro real no cabeçalho. A escolha explícita Todos é preservada ao reabrir no mesmo contexto. |
| Mestre e detalhe do Histórico ultrapassavam a largura disponível, inclusive em 1440 × 900. | A disposição considera o viewport, as margens e os mínimos reais dos painéis. Onde não cabem lado a lado, ficam empilhados; Ampliar detalhes continua disponível. O olho ganhou um contorno de foco visível sem deslocar o ícone. |
| Busca global não indexava os conceitos completos de Aprender. | Os conceitos existentes são indexados e abrem seu detalhe, inclusive com busca sem acentos. O projeto, o rascunho e a execução atual permanecem preservados. |
| Manual e ajuda contextual ainda citavam a organização antiga do menu. | Orientações usam Preparar, Explorar, Investigar e Acervo, os caminhos da Biblioteca e do Caderno e os comandos reais do Histórico. A ajuda de Estudos abre as instruções do estudo; Biblioteca e Caderno abrem seus tópicos pertinentes. |
| Atualizar a Biblioteca selecionava sempre o primeiro item. | Preservada a identidade do modelo ou da revisão selecionada. Uma revisão nova não troca silenciosamente a revisão cuja cópia a pessoa pretendia criar. Busca pessoal aceita palavras em qualquer ordem e diferenças de acentuação. |
| Barra de origem dos Estudos quebrava em muitas linhas em janelas compactas. | Origem, ações e formulário passam a usar a largura disponível; os tipos de estudo permanecem no seletor. Executar e Cancelar mantêm acesso fora da rolagem principal. |
| ZNE reservava espaço lateral insuficiente com texto ampliado. | Em modo compacto, Configurar ZNE e Resultados reutilizam os mesmos controles em abas. Ao concluir, o resultado fica acessível; parâmetros e dados sobrevivem à alternância larga/compacta. |
| Monitor de tarefas disputava largura com seu contexto e botões. | O monitor reorganiza texto e controles quando necessário, preservando progresso, cancelamento e acesso à execução concluída. |
| Rolar sobre campos sem foco podia modificar parâmetros científicos. | Campos numéricos e seletores sem foco devem encaminhar a roda à área de rolagem. Alteração intencional com foco e navegação por teclado continuam disponíveis. |
| Logs tentavam escrever no diretório de execução, que pode ser somente leitura. | Diagnóstico em diretório gravável do usuário, inicialização idempotente e logs com rotação. Falha de diagnóstico não impede abrir o aplicativo. |
| Falha de disco podia truncar JSON anterior ou deixar CSV e metadados de gerações diferentes. | Preparação em arquivos temporários, substituição do arquivo completo e recuperação do par CSV/metadados quando a publicação falha. Se a recuperação também falhar, o erro informa a cópia preservada. |
| Um registro apagado por outro processo durante a listagem podia interromper a atualização inteira do Histórico. | A leitura ignora o arquivo que desapareceu e mantém os demais registros; falhas de acesso individuais são registradas como avisos parciais. A ordenação por data permanece preservada. |

O par CSV/metadados não constitui uma transação resistente a queda de energia entre duas renomeações, nem sincroniza escritores simultâneos. A exportação JSON/ZIP reúne a evidência em um único arquivo quando esse requisito for necessário.

## Antes de disponibilizar um executável Windows

| Prioridade | Entrega | Critério de aceite |
|---|---|---|
| P0 | Definir runtime de build | Fixar Python e dependências para Windows x64. O `requirements.txt` atual é um lock de desenvolvimento que requer Python 3.12+; o `pyproject.toml` permite outras resoluções compatíveis. |
| P0 | Empacotar e validar o motor | Incluir DLLs do Aer, plugins Qt de plataforma/SVG, fontes, ícones e metadados `dist-info`. Rodar uma simulação, ZNE, relatório e backup fora do checkout e sem Python instalado. |
| P0 | Instalar e atualizar em máquina limpa | Atalhos, primeira abertura, caminho com acentos, usuário sem privilégios e pasta de instalação sem permissão de gravação. Atualização/desinstalação não devem apagar experimentos ou preferências. |
| P1 | Escolher e automatizar a entrega | Avaliar pacote portátil e instalador, gerar artefato em runner Windows, publicar hashes e notas de versão. A CI atual de wheel/Qt offscreen não comprova esse fluxo nativo. |
| P1 | Revisão visual nativa | Windows em escalas de 100%, 150% e 200%, teclado, fonte ampliada, temas e leitor de tela. Concluir o roteiro Bell → executar → histórico → reabrir → comparar → exportar. |
| P1 | Recuperação de falhas | Falta de espaço durante exportação, execução cancelada, fechamento com gravação pendente, restauração de backup e retomada após erro. |
| P1 | Entrada e retomada de contexto | Avaliar Projetos como primeira tela de uma instalação nova. Hoje a inicialização abre a preparação ou retoma o circuito ativo. Separar a preferência de escopo para distinguir Sem projeto de Todos os projetos após reiniciar. |
| P2 | Perfil de inicialização e arquivos volumosos | Medir imports, construção das páginas, renderização 3D e histórico com coleções representativas. Extrair carregamento progressivo somente onde o perfil justificar. |
| P2 | Evolução gradual da coordenação | Extrair exportações e tarefas de `MainWindow` com testes de integração, preservando o vínculo entre projeto, rascunho e execução. |
| P2 | Animação dos grupos de navegação | A expansão atual preserva nomes e estado, mas ainda é imediata. Uma transição futura deve respeitar redução de movimento e manter foco e rolagem estáveis. |

Não há evidência suficiente para migrar imediatamente o armazenamento para SQLite ou aumentar o limite de qubits. Essas decisões exigem medições de memória, latência e consistência nos cenários esperados da distribuição.

## Verificação da revisão inicial (`95f60df`)

As verificações e capturas são feitas em Linux com Qt offscreen, com repositórios e preferências temporários. Não utilizam os experimentos pessoais do usuário. Dados das capturas são cenários de verificação da interface, não evidências da campanha da monografia.

Veja a [seleção de capturas em 1440 × 900 e 1024 × 768 com texto ampliado](screenshots/revisao-distribuicao/README.md).

| Verificação executada | Resultado |
|---|---|
| Suíte automatizada geral (`pytest -q -p no:cacheprovider`) | **753 testes passaram**, em 20 min 24 s. |
| Regressões finais de navegação, ajuda contextual, consulta gráfica, foco do olho e disposição do Histórico | **23 testes passaram**, em 42 s, depois dos últimos ajustes. |
| `scripts/cloud_smoke.py` | Passou: navegação, simulação ideal/ruidosa com e sem snapshots, persistência, ZNE como registro independente, tutorial, exportação/importação JSON e reabertura. |
| Construção do wheel e `scripts/package_smoke.py` | Passaram: pacote extraído fora do checkout, fontes/licenças/ícones, três temas, motor científico, histórico gráfico, inspetor global, backup e recuperação de circuito/preferências. O pacote foi reconstruído após os ajustes finais. |
| `scripts/preview_interface.py` | **96 capturas**: 16 destinos em três temas, a 1440 × 900/15 px e 1024 × 768/24 px. Dimensões conferidas; manual recapturado após a correção dos textos. |
| Dependências, sintaxe e espaços no diff | `pip check`, `compileall` de `core`, `data` e `gui`, e `git diff --check` passaram. |
| Instalador e desktop Windows | **Não executados** neste ambiente. Permanecem os critérios da seção anterior. |

A suíte geral terminou antes dos dois últimos ajustes localizados de disposição do Histórico e ajuda contextual. Os 23 testes de fluxo foram executados novamente sobre o código final e incluem quatro casos acrescentados depois daquela coleta. Há sobreposição entre essas rodadas; os números não devem ser somados como testes distintos.

A primeira rodada expôs quatro falhas: dois estados de foco do botão de olho, uma mensagem vazia do Histórico e uma expectativa antiga sobre o texto do acesso a exemplos. Os estados e a mensagem foram corrigidos; a última verificação passou a acionar os controles pelos nomes acessíveis, preservando o texto conciso dos botões. Nenhuma falha foi ignorada ou marcada como esperada.

Para reproduzir os fluxos na raiz do projeto, com as dependências instaladas:

```sh
QT_QPA_PLATFORM=offscreen OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python -m pytest -q -p no:cacheprovider
QT_QPA_PLATFORM=offscreen OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python scripts/cloud_smoke.py
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
QT_QPA_PLATFORM=offscreen OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python scripts/package_smoke.py
```

Os testes novos exercitam falhas de exportação com recuperação, listagem concorrente do histórico, diagnóstico em diretório do usuário, busca e contexto de projeto, preservação da revisão da Biblioteca, rolagem sem alterar campos, monitor de tarefas e telas científicas compactas. Não demonstram, por si só, compatibilidade de um executável nativo com todas as máquinas Windows.

## Introdução opcional e primeiros passos

A preparação para distribuição passou a incluir uma apresentação inicial com três caminhos: guia de uso, tutorial de Bell e exemplos da Biblioteca. O fechamento por botão, Esc ou controle da janela dispensa a apresentação e devolve o foco ao controle anterior. A preferência de reapresentação é explícita; por padrão, ela aparece uma vez por perfil.

O guia fica em **Aprender → Primeiros passos**, com os tópicos Começar, Preparar, Observar e Guardar. Os acessos correspondem às ferramentas existentes. A prévia de Bell é estrutural e sua previsão é identificada como ideal; os atalhos de resultados dependem de uma execução selecionada. Ler ou concluir o guia não cria experimentos, altera parâmetros ou registra aprendizado como evidência científica.

O tutorial de Bell continua exigindo ações e uma execução compatível. Seus textos agora explicam o motivo de cada etapa e identificam os comandos atuais do Histórico. As proteções contra substituição de rascunho continuam sendo usadas ao iniciá-lo.

`OnboardingController` coordena a apresentação e os acessos; a entrada desktop agenda a oferta somente depois da abertura da janela. A splash mantém seu comportamento. O progresso e as preferências ficam em `onboarding/` no `QSettings`, separados de `tutorial/bell/`; são incluídos pelo mecanismo existente de backup das preferências.

Veja as [capturas da apresentação e do guia](screenshots/primeiros-passos/README.md).

| Verificação do guia | Resultado |
|---|---|
| Fluxos de aprendizagem, navegação, tutorial, projetos, interface e splash | **90 testes passaram**, em 2 min 43 s. |
| Casos próprios da introdução, repetidos sobre o código final | **17 testes passaram**, em 41 s. Incluem dispensa, foco, retomada em outra janela, preservação do rascunho, fontes reais e disposição em três temas/duas escalas. São parte dos 90 casos, não adicionais. |
| `scripts/cloud_smoke.py` atualizado | Passou: apresentação opcional → guia → exemplos → simulação → tutorial de Bell → histórico → reabertura, além dos quatro cenários de ruído/snapshots, ZNE e JSON já cobertos. |
| Wheel reconstruído e `scripts/package_smoke.py` atualizado | Passaram fora do checkout, incluindo apresentação, guia retomável, habilitação dos resultados reais e persistência após reabrir. |
| Capturas | Dez imagens do guia/apresentação em tema Azul Entrela; quatro selecionadas para a documentação. Texto de 24 px e janela de 1024 × 768 incluídos. |

Nesta etapa foi executado o conjunto de regressões relacionado à introdução; a suíte geral de 753 testes acima pertence à revisão inicial. Todas estas verificações continuam sendo em Linux com Qt offscreen. Não houve teste de usabilidade com participantes nem validação de desktop Windows nativo.

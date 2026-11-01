# Entrela 0.11 — evolução para demonstração acadêmica

Implementação em 01/11/2026 na branch `evolucao-entrela`, a partir da análise `c06a234`.
A auditoria anterior é histórica; este documento descreve as mudanças seguintes.

## Entregas e uso

**Arquivos e reprodução.** Metadados, duração, tags, listas, métricas, sementes e operações do circuito passam por validação antes de abrir resultados. Erros de importação preservam o arquivo. Parâmetros numéricos usam apresentação decimal com round-trip de floats, inclusive notação científica e valores pequenos. Valores importados podem ampliar o intervalo do controle. O comando **Reexecutar** copia a configuração salva e utiliza a semente efetiva, criando outra execução. A preferência de shots aplica-se a novos experimentos, sem reescrever o formulário atual.

**Visualização.** A reprodução para no fim por padrão; repetir é uma opção explícita. O slider permanece sincronizado durante reprodução. Os rastros são reconstruídos com até 80 snapshots contíguos, inclusive ao voltar, saltar ou repetir. A reprodução é didática (350 ms por snapshot em 1x), não uma escala de tempo físico.

A roda aproxima/afasta entre 0,5× e 3×. Há botões de zoom, deslocamento, restauração e seleção de qubit; o Matplotlib mantém rotação por arraste e pan com botão central. O foco muda o centro e os limites da câmera. Até seis esferas são organizadas em grade, com cores distintas, coordenadas, pureza e matriz reduzida. Pureza local baixa não recebe indicação de erro. A câmera não modifica estados científicos.

A linha tracejada de Bloch representa o mesmo circuito sem ruído. A aba **Probabilidades no instante** compara as probabilidades dos dois estados no mesmo snapshot; não confunde probabilidades calculadas com frequências de shots.

**Análises.** A nova página usa a execução selecionada e workers canceláveis. Oferece F(t), pureza, energia, fidelidade à evolução exata, erro de Trotter ideal/exato, Z por qubit, ZZ entre vizinhos, entropia reduzida e negatividade na bipartição q0|resto. Entropia reduzida mede emaranhamento somente se o estado global for puro; negatividade zero não exclui todo emaranhamento em dimensões maiores.

A referência exata diagonaliza o Hamiltoniano e aplica exp(−iHt) ao estado inicial ideal. A fidelidade ruidosa/exata inclui ruído e aproximação; a infidelidade circuito ideal/exato separa a aproximação Trotter. A convergência varia os passos, preserva a ordem da fonte e desliga o ruído somente nas novas execuções de análise. Usa até dez valores de 1 a 200 passos.

As varreduras suportam J, h, p1, p2, T₁, T₂ e passos. Validam todos os pontos antes de executar; aceitam até 20 pontos, cinco sementes e 50 execuções. Para variar T₁/T₂, todos os pontos precisam satisfazer a relação física. As métricas do ensemble não ganham incerteza estatística por repetir sementes; Z0 amostrado registra a flutuação de shots. Cada linha mantém a semente usada. As análises são guardadas separadamente, reabertas no seletor da fonte e exportadas como CSV/JSON.

**ZNE.** A interface mostra pontos com erro padrão, ajuste, extrapolação e referência ideal calculada no circuito unitário compilado. Expõe os erros absolutos antes/depois, resíduos e graus de liberdade. Três pontos com ajuste quadrático têm zero grau de liberdade residual. A incerteza cobre amostragem sob o ajuste escolhido, não viés de extrapolação. A análise continua sendo outro registro; não cria um estado mitigado nem promete melhoria.

**Circuito.** A tabela mostra porta, qubits, parâmetros, estágio e passo Trotter. A proveniência de estágio/camada é registrada na construção do circuito. Selecionar uma operação aponta para o snapshot de fim da camada, quando disponível. Não há um estado simulado após cada porta nem mapeamento completo entre cada porta sintetizada e um único termo do Hamiltoniano.

**Desempenho e organização.** O salvamento automático roda fora da thread gráfica, preservando proteção contra perda de resultado e fechamento durante tarefas. O histórico usa caches de resumos invalidados por tamanho/data do JSON original, sem decodificar matrizes para listar execuções. A primeira leitura de um registro antigo ainda precisa ler seu JSON para gerar o resumo. Os estados completos são validados ao abrir. O histórico pagina a cada 100 registros e busca projeto, tags e notas. Comparações usam contagens e métricas dos resumos.

Modelos pessoais guardam configurações nomeadas. Projetos, notas e tags ficam em arquivo separado, sem alterar resultados científicos. Na página **Projetos**, o salvamento de modelo usa o formulário atual; as anotações usam a execução selecionada.

**Interface e relatórios.** Temas claro/escuro alcançam gráficos, estilos locais e botões; a fonte pode variar entre 11 e 20 px. F11 alterna apresentação em tela cheia com fonte maior e navegação compacta. Em telas menores, a navegação compacta libera espaço e a ajuda abre flutuante. A ajuda de campos aponta para as seções correspondentes do manual. Velocidade, loop, rastros, foco e câmera persistem. Restaurar preferências visuais não modifica resultados.

O relatório HTML inclui gráfico de frequências embutido, configuração, métricas, interpretação, versões, convenções, limitações, ZNE, análise selecionada e notas. O PDF usa Qt PrintSupport. O JSON completo continua sendo o arquivo indicado para reprodução dos estados.

## Cobertura das propostas da auditoria

| Propostas | Resultado |
|---|---|
| M01–M03 | Validação de arquivos, precisão, reexecução e playback corrigidos. |
| M04–M06 | Zoom central/foco, pan, reset, matrizes reduzidas e comparação sincronizada. Zoom ancorado no cursor 3D e suavização de câmera não foram implementados. |
| M07–M10 | Métricas temporais, referência exata/convergência, observáveis e diagnóstico ZNE disponíveis. |
| M11 | Explorador por porta e camada disponível. Mapeamento termo→porta e execução porta a porta permanecem fora desta entrega. |
| M12–M13 | Resumos, paginação, salvamento automático assíncrono, estimativa de estados brutos e limites de execução. O histórico antigo tem migração sob demanda; leitura individual e exportação manual ainda podem ocupar a thread gráfica. |
| M14–M19 | Apresentação, relatórios, varreduras, preferências, temas e organização pessoal disponíveis. Sequenciamento automático de apresentações e testes com leitores de tela não estão incluídos. |
| M20 | Wheel com assets e ponto de entrada; ensaio fora do checkout em Linux. Instaladores autossuficientes e validação Windows/macOS/hardware da banca continuam pendentes. |

## Validação

Ambiente: Linux, Python 3.12, PySide6 6.11.1, Qiskit 2.4.1, Aer 0.17.2. Dependências verificadas por `pip check`.

- 133 testes automatizados passaram, incluindo os 99 anteriores e 34 verificações novas.
- Fluxo offscreen completo: navegação em 13 páginas, execuções com/sem ruído e snapshots, persistência, ZNE independente, tutorial, exportação/importação e reabertura.
- Casos científicos novos: Bell com entropia 1 e negatividade ½; convergência ideal à evolução exata; varreduras com sementes e cancelamento; referência ideal e resíduos de ZNE.
- Casos de interface/dados: parâmetros com precisão total, parada e loop, slider durante reprodução, câmera sem mutação do estado, probabilidades sincronizadas, resumos sem decodificação, paginação, projetos, relatórios HTML/PDF e persistência de preferências.
- Inspeção offscreen em 1440×900 e 1024×768, incluindo tema claro, navegação compacta e ajuda flutuante. Em 1024×768, as 13 páginas não exigiram rolagem horizontal do corpo principal; tabelas amplas mantêm sua própria rolagem.
- Wheel construído e exercitado por `scripts/package_smoke.py`, com imports isolados, assets, janela Qt, simulação e persistência fora do checkout.

A validação offscreen não substitui ensaio com mouse/touchpad físicos, leitor de tela, projetor nem execução em outros sistemas operacionais. O pacote é uma distribuição Python, não um instalador com todas as bibliotecas do sistema.

## Reproduzir a validação

```bash
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
QT_QPA_PLATFORM=offscreen python -m pytest -q -p no:cacheprovider
QT_QPA_PLATFORM=offscreen python scripts/cloud_smoke.py
python -m pip wheel --no-deps . -w dist
python scripts/package_smoke.py dist/entrela-0.11.0-py3-none-any.whl
```

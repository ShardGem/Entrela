# Entrela

Laboratório desktop de simulação quântica com PySide6, Qiskit e Aer.

- Modos Guiado e Avançado compartilham os mesmos parâmetros.
- Galeria com 12 exemplos editáveis e tutorial de Bell com sete etapas verificadas por ações reais.
- Evolução ideal por vetores de estado e ruidosa por matrizes densidade.
- Fidelidade, pureza global, energia, circuito, esfera de Bloch, dados e interpretação.
- Histórico com reabertura, comparação de execuções compatíveis e rascunho persistente.
- ZNE de um observável Z com fatores efetivos 1, 3 e 5.
- Exportação CSV, JSON completo, pacote ZIP e figuras PNG; importação como cópia independente.
- Ctrl+K para comandos, exemplos e conceitos; Ctrl+N para criar; Ctrl+O para importar; Ctrl+Enter para executar.


## Interface e navegação — 0.15

Navegação em quatro grupos recolhíveis: **Começar**, **Laboratório**, **Pesquisa** e **Organização**. O grupo da página ativa abre automaticamente, inclusive ao navegar por comandos ou tutoriais. Preferências ficam no rodapé. A barra pode ser expandida ou recolhida pelo botão do menu.

Fonte padrão maior, áreas de clique ampliadas e ícones SVG vetoriais adaptados à escala da tela. O antigo padrão de 13 px migra uma vez para 15 px; preferências manuais diferentes são mantidas. O tamanho continua ajustável em Preferências.

Veja [detalhes e capturas da interface 0.15](docs/interface-0.15.md).

## Estudos e documentação — 0.14

- **Análises**: protocolos com pergunta, hipótese, controles e referência no TCC; revisões preservadas e reprodução com as opções registradas.
- Mapas de calor de dois parâmetros, estabilidade ZNE com viés/variância e comparação sob orçamento equivalente de shots.
- **Comparações**: carregar estados e curvas em segundo plano; gráficos, Bloch A/B, câmeras e snapshots sincronizados, configurações e observáveis ZNE.
- **Documentação**: pacote ZIP com dados integrais, gráficos PNG/SVG/PDF, tabelas LaTeX, PDF, GIF e sequência PNG de snapshots reais, protocolos, manifesto de origem e hashes.
- **Evolução 3D**: exportação da vista atual PNG/SVG/PDF com câmera e snapshot registrados.

Para usar: abra uma execução, planeje o estudo em **Análises**, carregue A/B em **Comparações** e exporte em **Documentação**. O GIF usa tempo didático e nunca interpola estados.

Consulte [manual, referências científicas e limites da versão 0.14](docs/evolucao-0.14.md).

## Pesquisa e experiência de uso — 0.13

- Guiado mostra uma etapa por vez; Avançado reúne as categorias e oculta a navegação de etapas. Ambos preservam os mesmos parâmetros.
- Início explica o fluxo científico; campos têm ajuda e uma prévia descritiva do estado inicial.
- Em **Projetos**, dê um nome à execução selecionada e registre hipótese, projeto, tags e observações. O ID técnico e o resultado permanecem preservados.
- Em **Análises**, escolha **Trotter × ruído** para comparar ideal e ruidoso contra a evolução exata, ou **Benchmark de mitigação** para comparar erro de ⟨Z⟩, custos e tempos.
- O benchmark compara sem mitigação, ZNE linear/quadrática (variantes da mesma técnica) e verificação de paridade Z quando o estado ideal tem paridade determinística. Fidelidade de ZNE fica indisponível, pois o método não reconstrói um estado.
- Análises podem ser canceladas, reabertas pelo histórico da fonte e reproduzidas com as opções registradas. Exportação CSV acompanha `.metadata.json`; preserve os dois arquivos.
- CSV de resultados inclui configuração e proveniência. O pacote ZIP inclui a análise selecionada e as anotações; o relatório HTML/PDF inclui curvas reais, referências e limitações.
- Cálculos dos relatórios rodam fora da thread gráfica; caches limitados evitam repetir derivações de Bloch e desenhos de probabilidades.

Veja [uso, metodologia e limites da versão 0.13](docs/evolucao-0.13.md). Os dados produzidos para validar a aplicação não substituem o protocolo experimental do TCC.

## Circuitos interativos — 0.12

A tela agora oferece diagrama vetorial com inspeção de portas e um editor com paleta, parâmetros, fase global, controles/alvos, arraste, undo/redo e execução Qiskit/Aer. Importa/exporta circuito JSON e OpenQASM 2; exporta SVG. Circuitos editados geram novos registros, sem alterar as execuções de origem.

A área 3D também ganhou ampliação, seleção por clique, pan com Shift e métricas sincronizadas. Veja [manual e imagens da versão 0.12](docs/circuitos-interativos-0.12.md).

## Visualização 3D e estabilidade

A correção do fechamento, o painel de zoom vertical e os controles de câmera estão descritos em [docs/correcao-bloch.md](docs/correcao-bloch.md), com imagem e instruções de atualização no Windows.

As propostas de novas funcionalidades estão em [Próximos ajustes](docs/proximos-ajustes.md).

## Evolução 0.11

A entrega e os limites de validação estão em [docs/evolucao-0.11.md](docs/evolucao-0.11.md).

- Reprodução para no último snapshot; loop explícito, slider sincronizado e rastros derivados da trajetória real.
- Câmera com zoom por roda, pan, reset e foco por qubit; Bloch e probabilidades ideal × ruidoso no mesmo instante.
- Parâmetros importados mantêm precisão; **Reexecutar** usa a semente efetiva da execução selecionada.
- **Análises**: métricas temporais, evolução exata, convergência Trotter, correlações, entropia e negatividade.
- Varreduras com até 20 pontos, cinco sementes e 50 execuções; cancelamento entre pontos, CSV/JSON e análises reabertas pelo histórico da fonte.
- ZNE com gráfico, referência ideal de Z, erros absolutos, resíduos e graus de liberdade.
- Tema claro/escuro, fonte ajustável, navegação compacta e apresentação em tela cheia por **F11**.
- Histórico paginado, resumos leves, salvamento automático em segundo plano, projetos, notas e modelos pessoais.
- Relatórios acadêmicos **HTML/PDF** e distribuição Python com assets e comando `entrela`.

Na página **Análises**, escolha o tipo e clique em **Calcular análise**. A análise temporal requer snapshots.
As análises usam a execução selecionada; as configurações de varredura não modificam seus resultados.
Clique em uma linha ou ponto da curva temporal para selecionar o mesmo snapshot em **Evolução 3D**.
Em varreduras, use ponto decimal e vírgulas entre valores: `0, 0.01, 0.05`.

Para instalar o pacote a partir do checkout:

```bash
python -m pip install .
entrela
```

Para construir e validar o wheel fora do checkout:

```bash
python -m pip wheel --no-deps . -w dist
python scripts/package_smoke.py dist/entrela-0.15.0-py3-none-any.whl
```

O wheel requer Python e as dependências Qt/Qiskit; não é um executável autossuficiente.

## Na nuvem

```bash
cd /workspace/Entrela
bash scripts/cloud-install.sh
bash scripts/cloud-start.sh
```

Sem display, o Qt funciona em modo offscreen para testes. Não há servidor web ou prévia localhost.

```bash
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/entrela/bin/python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/entrela/bin/python scripts/cloud_smoke.py
```

## Desenvolvimento local

Com Python 3.11 ou superior, criar um ambiente virtual e ativá-lo conforme seu sistema:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python app.py
```

A instalação e os testes desta entrega foram executados em Linux, Python 3.12, Qiskit 2.4.1, Aer 0.17.2 e PySide6 6.11.1.

## Usar o aplicativo

Comece pela galeria ou pelo tutorial. Para preparar Bell manualmente, use dois qubits,
estado inicial Bell, J=0, h=0 e ruído desligado. Ative os snapshots para visualizar a evolução.

O modo Guiado permite navegar livremente por Sistema, Hamiltoniano, Evolução, Ruído e Execução.
Trocar para Avançado mantém os campos e valores. O tutorial só avança após reconhecer suas ações,
inclusive executar de verdade e reabrir o resultado pelo histórico.

Cada execução tem configuração imutável e identificador próprio. Alterar o formulário não modifica
resultados anteriores. Rascunhos válidos e a preferência de modo são restaurados ao reabrir.
JSON versão 2 preserva estados complexos, contagens, tempos, sementes e versões. Arquivos legados
de contagens continuam legíveis; arquivos corrompidos são preservados e reportados.
Na nuvem, os dados ficam por padrão em /workspace/.local/share/entrela/experiments.
ENTRELA_DATA_DIR permite escolher outro diretório; no desktop, o padrão é ~/.entrela/experiments.

## Convenções científicas

Ising: **H = +J ΣZZ + h ΣX**; J positivo favorece antialinhamento no termo ZZ.
O tempo de evolução é adimensional, com ℏ=1. T₁ e T₂ são informados em µs e devem
satisfazer **T₂ ≤ 2T₁**, com ambos positivos. O modelo térmico educativo usa 50 ns por porta;
o ruído incide nas operações, inclusive de preparação, e não representa calibração de hardware.

A fidelidade compara o mesmo circuito Suzuki–Trotter ideal e ruidoso, e não o erro de Trotter
contra a evolução exata. Pureza global e local são distintas. Os gráficos de evolução e Bloch
usam snapshots realmente simulados, sem interpolação tratada como física.

ZNE extrapola Z de um qubit e não reconstrói um estado mitigado. Não há garantia de melhoria.
As estimativas não são truncadas ao intervalo físico; o erro padrão mostrado descreve amostragem.
A análise gera outro registro e preserva as contagens e métricas da execução de origem.

## Preservação do trabalho

O código deve estar registrado em commits e confirmado no remoto antes de trocar de ambiente.
Publicar um ambiente é diferente de enviar commits ao GitHub. Scripts e instruções de configuração
ficam versionados junto ao aplicativo.

Ver [escopo e validação](docs/entrega-workspace.md) e [visão de produto](docs/design-produto.md).

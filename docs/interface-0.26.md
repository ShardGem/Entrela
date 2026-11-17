# Entrela 0.26 — interface de plataforma

A composição usa o IBM Quantum Platform e o Composer como referências: cabeçalho global, navegação estável, comandos locais, biblioteca de portas, desenho central e inspeção dos resultados no mesmo ambiente. A identidade continua sendo a do Entrela. Os botões receberam cantos mais arredondados, conforme solicitado, e campos e painéis têm contornos suaves.

## Análise da implementação existente

O Entrela é um aplicativo desktop PySide6. `MainWindow` e os controladores coordenam 14 páginas; configuração, documento do circuito, resultados e histórico têm estados distintos. Qiskit/Aer e os renderizadores científicos ficam em `core`; repositórios, bibliotecas, rascunhos e protocolos ficam em `data`.

A revisão identificou três pontos principais: identidade e contexto misturados em uma barra local, comandos do editor dispersos em botões de mesmo peso e ausência de resultados próximos ao desenho. A altura preferida dos gráficos também podia empurrar conteúdo para fora da janela. Foram mantidos os modelos, sinais, widgets de configuração, fontes de resultados e contratos de persistência existentes.

## Mudanças

| Área | Comportamento atual |
|---|---|
| Cabeçalho global | Identidade Entrela, busca, ajuda e indicação de simulador local. O título e o caminho da ferramenta ficam em uma faixa própria |
| Navegação | Todas as ferramentas continuam acessíveis por nome nos quatro grupos existentes. Os grupos começam abertos e o menu estreito preserva os nomes |
| Sistema visual | Grafite neutro com destaque azul, ações principais evidentes, foco visível, campos identificados e botões arredondados. Os três temas e as preferências continuam disponíveis |
| Tipografia | IBM Plex Sans regular, medium e semibold incluídas no aplicativo. Tamanho de texto e densidade continuam persistentes |
| Configuração | Título explícito do inspetor, modo Passo a passo, orientações breves e ajuda por campo. Cabeçalhos redundantes são reduzidos em janelas pequenas |
| Editor | Arquivo e Editar agrupam comandos; biblioteca de portas identificada por nomes e famílias; inspetor concentra porta e execução. Aplicar alterações exige uma porta selecionada |
| Resultado no editor | Contagens e métricas da execução de circuito selecionada abaixo do desenho, com acesso aos resultados completos e aviso ao alterar o circuito |
| Janelas menores | Portas, Circuito e Inspetor continuam em abas. O painel de resultados pode ser aberto pelo botão Resultados, sem iniciar cálculos |
| Tabelas | Cabeçalhos, foco, seleção e linhas alternadas consistentes nos temas claro e escuros |
| Demais ferramentas | A mesma hierarquia visual se aplica a resultados, estados 3D, estudos, ZNE, comparações, histórico, exemplos, caderno, relatórios e preferências |

O desenho e os resultados compartilham o espaço disponível. A altura mínima preserva os dados e os comandos; a altura preferida de um gráfico não força rolagem desnecessária. Fontes ampliadas ainda podem exigir rolagem vertical para conteúdos extensos.

## Proveniência do painel do editor

O painel **não simula silenciosamente cada edição**. Ele utiliza as contagens, a fidelidade, a pureza e o número de shots da execução selecionada. Alterar o rascunho não modifica esses dados. Um circuito diferente recebe um aviso; uma execução Hamiltoniana não é apresentada como resultado de um circuito livre. Sem execução de circuito selecionada, aparece orientação para executar.

ZNE continua estimando observáveis; esta interface não inventa um estado mitigado nem métricas de estado mitigadas. Os exemplos da galeria são simulações para documentação, não medições de hardware ou evidências dos experimentos do TCC.

## Antes e depois

| Contexto | 0.25 | 0.26 |
|---|---|---|
| Configuração | [Anterior](screenshots/0.25.0/03-laboratorio/04-configurar-ruido.png) | [Atual](screenshots/0.26.0/03-laboratorio/04-configurar-ruido.png) |
| Editor | [Anterior](screenshots/0.25.0/03-laboratorio/08-editor.png) | [Desenho e resultados](screenshots/0.26.0/03-laboratorio/08-editor.png) |
| Parâmetros do circuito | [Anterior](screenshots/0.25.0/03-laboratorio/12-editor-execucao.png) | [Atual](screenshots/0.26.0/03-laboratorio/12-editor-execucao.png) |
| Histórico | [Anterior](screenshots/0.25.0/06-acervo/historico-resumo.png) | [Atual](screenshots/0.26.0/06-acervo/historico-resumo.png) |
| Texto ampliado | [Anterior](screenshots/0.25.0/07-preferencias/texto-ampliado-editor.png) | [Atual](screenshots/0.26.0/07-preferencias/texto-ampliado-editor.png) |

A [galeria atual](screenshots/0.26.0/README.md) mantém índice, dimensões, hashes e dados dos cenários. As pastas anteriores permanecem arquivadas. Os arquivos de ícone e imagens enviados pelo autor, o código e o tempo da splash foram preservados.

## Verificação

A validação desta versão usa testes científicos e de fluxo, inspeção de capturas Qt nos três temas e conferência do pacote fora do repositório. Os totais finais e o ambiente ficam no [registro de validação](validacao-0.26.json).

- **683 testes aprovados**, sem falhas, erros ou casos ignorados, em quatro lotes de 171 + 171 + 171 + 170 casos.
- **15 verificações adicionais de ajuda e tutorial aprovadas** após alinhar os textos aos comandos atuais.
- **77 capturas verificadas**, incluindo 68 em 3840 × 2160; fontes e tamanhos dos diálogos permanecem registrados no manifesto.
- **42 prévias das 14 ferramentas nos três temas**, em 1024 × 768 com texto de 24 px.
- Fluxos reais de execução ideal/ruidosa, snapshots, ZNE, tutorial, persistência e exportação/importação passaram.
- O wheel abriu fora do repositório; seus **122 módulos** foram conferidos byte a byte, incluindo as três fontes e a licença. `pip check` não encontrou dependências incompatíveis.

```bash
python -m pytest -q
python scripts/cloud_smoke.py
python scripts/preview_interface.py --all-pages --width 1024 --height 768 --font-size 24
python scripts/capture_gallery.py --output docs/screenshots/0.26.0 --scale 2 --overwrite
python scripts/verify_gallery.py docs/screenshots/0.26.0
python scripts/package_smoke.py
```

Os testes novos verificam a separação do cabeçalho, contraste das ações, seleção de comandos, preservação dos dados ao editar, distinção entre modalidades e visibilidade das métricas no painel. A suíte também cobre as funções científicas, persistência, cancelamento, exportações e regressões existentes.

A verificação usa Linux e Qt offscreen. A revisão manual nativa no Windows permanece pendente; capturas e testes automatizados não equivalem a essa conferência. Esta entrega não altera os modelos científicos nem implementa os estudos P2 pendentes no plano.

## Referências e fonte

- [IBM Quantum Composer](https://quantum.cloud.ibm.com/composer): organização dos comandos, circuito, biblioteca e painéis de resultados.
- [Carbon Design System — 2x Grid](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview): alinhamento, espaçamento e separação de regiões.
- [IBM Plex](https://github.com/IBM/plex): arquivos da fonte sem alterações, distribuídos sob [SIL Open Font License 1.1](../gui/assets/fonts/OFL.txt). Os arquivos estão em `gui/assets/fonts` e são incluídos no wheel.

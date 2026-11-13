# Entrela 0.25 — estúdio científico

Esta entrega reorganiza a composição das ferramentas existentes: a área científica recebe mais espaço, os parâmetros passam a um inspetor e as ações de execução ficam junto ao trabalho. As 14 páginas e os acessos diretos por nome permanecem disponíveis. Não houve substituição do simulador, dos formatos de dados ou da identidade enviada pelo autor.

As [três propostas de composição](design/0.25.0/README.md) documentam o diagnóstico e a escolha. A [galeria atual](screenshots/0.25.0/README.md) contém capturas das telas reais, com configurações, resultados e metadados das simulações usadas para documentação.

## O que mudou

| Área | Nova organização | Comportamentos preservados |
|---|---|---|
| Configurar simulação | Área central com preparação, revisão do protocolo e execução selecionada; inspetor de parâmetros à direita; título editável e execução na base | Validação, ajuda contextual, modelos, modo guiado/avançado, rascunhos, cancelamento e histórico |
| Editor | Modelos e portas à esquerda, desenho/lista no centro, inspetor Porta/Execução à direita | Biblioteca versionada, importação/exportação, seleção sincronizada, desfazer/refazer, parâmetros e execução real |
| Resultados | Distribuição ou evolução em área ampla; opção explícita Lado a lado | Os mesmos dados, critérios de seleção, referências, contagens/frequências, exploração e exportações |
| Estados 3D | Cena e inspetor mantidos; reprodução, velocidade e navegação abaixo da linha do tempo | Foco/desfoco, quatro qubits por linha, câmera, snapshots, referência ideal e consulta do estado global |
| Estudos | Catálogo por pergunta científica à esquerda; formulário e orientação à direita | Estudos existentes, planejamento, fonte selecionada, persistência, reprodução e exportação |
| Comparações | Seis modos identificados em abas, sem um segundo seletor visível para a mesma escolha | Compatibilidade, curvas, Bloch, configuração, ZNE, métricas e preferências de visualização |
| Histórico | Detalhes em superfície própria, títulos alinhados, valores resumidos com precisão completa em tooltip, estado vazio orientado | Botões de olho acessíveis, filtros, ordenação, paginação, anotações e circuito gráfico somente de leitura |
| Exemplos | Lista e detalhe visual com preparação ideal e ação de carregar | Configurações originais, busca, identificação estável e tutorial |
| Início | Execuções recentes em destaque, início rápido ao lado, orientações opcionais | Histórico, exemplos, tutorial, conceitos e estado do repositório |
| Preferências | Categorias visíveis em lista lateral; ações de restauração em um menu | Temas, destaque, tipografia, densidade, movimento, avisos, exportações e backup |
| Demais ferramentas | Superfícies, tipografia, abas, tabelas e foco do sistema visual compartilhado | ZNE, caderno, documentação, ajuda e gerenciamento existentes |

O sistema visual está centralizado em `gui/design_system.py`, integrado à paleta e à escala tipográfica existentes. Superfícies distinguem documento, inspetor e transporte; métricas usam divisões discretas em vez de mais caixas. Os três estilos continuam disponíveis: Grafite, Claro científico e Azul escuro.

Em janelas menores ou com texto ampliado, o editor usa abas Portas/Circuito/Inspetor para preservar a largura do desenho e dos campos. As preferências trocam a lista lateral por um seletor de categoria e empilham rótulos e campos. O histórico reserva espaço para as colunas principais e para o olho de consulta. A rolagem vertical continua necessária para conteúdos extensos e para a escala de 24 px em 1024 × 768.

## Antes e depois

| Contexto | 0.24.1 | 0.25.0 |
|---|---|---|
| Configuração | [Antes](screenshots/0.24.1/03-laboratorio/04-configurar-ruido.png) | [Estúdio com inspetor](screenshots/0.25.0/03-laboratorio/04-configurar-ruido.png) |
| Circuito | [Antes](screenshots/0.24.1/03-laboratorio/08-editor.png) | [Paleta, desenho e inspetor](screenshots/0.25.0/03-laboratorio/08-editor.png) |
| Resultados | [Antes](screenshots/0.24.1/04-resultados/resultados-graficos.png) | [Área de gráficos](screenshots/0.25.0/04-resultados/resultados-graficos.png) |
| Preferências | [Antes](screenshots/0.24.1/07-preferencias/aparencia.png) | [Categorias visíveis](screenshots/0.25.0/07-preferencias/aparencia.png) |

As capturas antigas continuam arquivadas por versão. O README principal aponta para a nova galeria. As imagens da abertura e os ícones incorporam o commit do autor `5dfe5c3`; seus arquivos e o código da splash foram preservados nesta entrega.

## Integridade dos dados

- A preparação é uma prévia ideal do rascunho. A aba Execução selecionada mostra dados de uma execução já calculada, identificada separadamente. Editar parâmetros não modifica essa evidência.
- Os mesmos widgets de configuração e o mesmo documento do editor foram reposicionados; não há um formulário paralelo com valores divergentes.
- As métricas e os gráficos não receberam dados demonstrativos fixos. As capturas são geradas com simulações e estudos executados em armazenamento temporário.
- Mudar a visualização não recalcula a física nem cria uma nova execução. ZNE continua estimando observáveis, sem alegar reconstrução de um estado mitigado.
- A migração da disposição descarta somente a geometria antiga do painel de preparação, cujos lados mudaram de função. Experimentos, bibliotecas, preferências e rascunhos não são removidos.

## Verificação e reprodução

- **677 testes da suíte completa passaram, sem falhas, erros ou casos ignorados.** A coleção foi executada uma vez por caso em quatro processos Python sequenciais, com relatórios JUnit: 170 + 170 + 170 + 167. Isso evita acumular recursos Qt durante uma única sessão longa. Os tempos de teste foram 73,31 s, 99,58 s, 79,96 s e 157,89 s.
- **122 testes direcionados passaram em 101,26 s**, cobrindo composição, circuito, templates, paleta, teclado, histórico, navegação, preferências, layouts e continuidade dos dados.
- O fluxo real passou por 14 páginas, execuções ideais/ruidosas com e sem snapshots, persistência, ZNE independente, tutorial, exportação/importação JSON e reabertura após reiniciar.
- O wheel abriu fora do repositório em Python isolado, incluindo identidade, simulação, histórico gráfico, estado global, backup e persistência. Seus **121 módulos Python** foram comparados byte a byte com o código; os cinco arquivos de identidade correspondem aos hashes do manifesto.
- **77 PNGs verificados**: 68 em 3840 × 2160, quatro em 2048 × 1536 para janela lógica 1024 × 768 com texto de 24 px, a splash em 2200 × 1300 e quatro diálogos em seus tamanhos próprios. Hashes, resolução, cenários e cobertura das 14 páginas foram conferidos pelo verificador da galeria.
- Foram geradas **42 prévias adicionais** das 14 ferramentas nos três temas em 1024 × 768 com texto de 24 px, para revisão de responsividade. A galeria inclui exemplos dessa adaptação.
- `pip check` não encontrou dependências incompatíveis. O código da splash e os arquivos de identidade não têm diferenças em relação ao commit do autor `5dfe5c3`.

Os comandos abaixo reproduzem as verificações principais. Esta etapa utilizou Linux e Qt offscreen, sem modificar dados ou preferências pessoais.

O [registro de validação](validacao-0.25.json) contém os totais, ambiente, hashes do pacote e das capturas e hashes dos módulos conferidos. A galeria mantém seu próprio manifesto para verificar as imagens e a origem dos dados.

```bash
python -m pytest -q
python scripts/cloud_smoke.py
python scripts/capture_gallery.py --output docs/screenshots/0.25.0 --scale 2 --overwrite
python scripts/verify_gallery.py docs/screenshots/0.25.0
python scripts/package_smoke.py
python scripts/preview_interface.py --all-pages --width 1024 --height 768 --font-size 24
```

## Limites

Capturas Qt fora da tela e testes automatizados não equivalem à validação manual no Windows. Renderização nativa, escala de monitores diferentes, leitores de tela e interação prolongada nessa plataforma ainda precisam de conferência. A entrega não implementa os novos estudos científicos P2 do plano, nem instala outro mecanismo de persistência. A revisão preserva a aplicação desktop e suas dependências atuais.

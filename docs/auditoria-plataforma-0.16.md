# Auditoria anterior à evolução 0.16

Base: `7cfb678` (0.15), branch `evolucao_entrela`. Inspeção por camadas concluída antes das alterações de implementação.

## Arquitetura e inventário

Aplicação desktop Python 3.11+, PySide6/Qt, Qiskit 2.4/Aer 0.17, NumPy/SciPy, Matplotlib e Pillow. Não há servidor web. `core` contém configurações congeladas, circuitos, modelos de ruído, métricas, análises e exportações; `data` guarda experimentos JSON validados/escritos atomicamente, resumos, anotações e protocolos; `gui` contém páginas, widgets e workers. O controlador principal tem 1529 linhas e concentra navegação, execução, persistência e preferências: é um ponto de acoplamento a reduzir por novos componentes, sem reescrever toda a aplicação.

Já existem: 24 portas unitárias, documentos de circuito até 200 portas/6 qubits, undo/redo, reorder, zoom, JSON/OpenQASM2/SVG, snapshots reais, ZNE por folding, paridade quando aplicável, análises temporais, exata/convergência, mapas e orçamento amostrado. Não reimplementar nem substituir esses caminhos sem regressões. Matrizes densidade validadas, métricas Qiskit e referências analíticas têm cobertura existente. O ruído térmico educativo de 50 ns/porta não é calibração de hardware. ZNE estima observáveis, não um estado mitigado.

## Defeitos e causas verificadas

| Área | Evidência | Direção da correção |
|---|---|---|
| PDF | Bell produz 6 páginas com 5 MediaBox diferentes: figuras são entregues com seus próprios tamanhos a PdfPages. Outra rota usa QPrinter. | Compor páginas A4 exatas, margens e paginação comuns; DPI300 raster e artistas vetoriais preservados; unificar rotas PDF. |
| Comparação | Abas temporais/3D desativadas até ação manual; placeholders não explicam requisito; conteúdo antigo permanece ao trocar fonte. | Abas selecionáveis, carregamento explícito/ao selecionar, estados vazio/carregando/erro, rejeição de conclusão obsoleta e compatibilidade científica preservada. |
| Editor | RX 0.12345678912345678 é preenchido como 0.1235 no inspetor e Aplicar muda o circuito sem edição. | Entradas com precisão integral; rótulos compactos apenas no desenho. |
| Foco Bloch | Foco muda de q0 para q1, mas seleção/rótulo permanecem q0. | Sincronizar seleção, menu e câmera sem alterar estados. |
| Probabilidades | Não existe handler de hover com dados exatos. | Tooltip dos dados calculados no snapshot. |
| Histórico | Só duplo clique; sem ação Visualizar nem mestre-detalhe. Resumos não têm estados por projeto de desempenho. | Detalhes preguiçosos e ações claras; nunca desserializar matrizes para listar. |
| Identificação | Nome personalizado existe só em Projetos; criação e visualizações continuam expondo IDs. | Nome/objetivo/hipótese visíveis no fluxo de execução; IDs em metadados avançados. |
| Navegação | Ctrl+K permanece registrado; compacto apaga todos os textos; grupos repetem ícones de folhas; não há animação. | Busca por clique; identificação curta dos grupos; SVGs distintos; animações canceláveis com redução de movimento. |
| Divisórias | SimulationPage usa handle20px com pintura cinza global. | Área discreta de arraste e linha fina. |
| Splash | Espera1500ms depois de construir janela; tempo total soma inicialização; timers de fundo não param todos. | Orçamento total3000ms a partir da exibição, sem espera extra; parar animações. Event loop bloqueado pode atrasar exibição. |
| Preferências | Só claro/escuro, fonte, compacto e apresentação. | Auto, destaque, densidade, movimento, contraste, notificações e exportação consumidos de verdade/persistidos. |
| Ensino | Manual HTML único; tutorial real mas texto obsoleto; sem mestre-detalhe conceitual. | Biblioteca de conceitos com teoria/exemplos/exercícios/referências; sem alegar algoritmos completos não implementados. |
| Identidade | Nenhum grafla.ico/local grafla encontrado no workspace; ícone de janela/app nunca definido. | Após esclarecimento do usuário, melhorar o ícone Entrela existente; não utilizar recursos do outro projeto. |

## Riscos e validação planejada

Preservar IDs técnicos, schemas2/3 e arquivos científicos. Anotações pessoais permanecem separadas e compatíveis. Não ordenar tabelas cuja posição de linha corresponde a snapshot sem mapear índices. Não comparar circuitos físicos diferentes silenciosamente nem interpolar snapshots ausentes. Estados após portas em Trotter só existem no fim da camada; linhas do tempo devem declarar essa granularidade.

Novos testes: tamanho físico de todas as páginas PDF e texto vetorial, precisão de ângulos, comparação/tab loading, metadados sem mutação, revisões/clipboard do editor, preferências/movimento, valores exatos/foco Bloch, identidade/splash e integridade matemática. Regressão completa, pacote isolado, fluxo real offscreen e inspeções em múltiplas resoluções. Não reivindicar teste físico Windows ou leitor de tela a partir de offscreen.

Tomografia, hardware e novos algoritmos avançados exigem protocolos científicos próprios; serão avaliados no registro de escopo, sem resultados simulados fictícios. Uma biblioteca de conceitos pode explicar Shor sem alegar que o aplicativo o executa integralmente.

# Próximos ajustes do Entrela

A primeira entrega desta rodada corrige o viewport 3D: a projeção agora usa todo o retângulo, sem distorcer as esferas, e o botão **Enquadrar cena** ajusta os qubits visíveis ao espaço disponível, mantendo orientação e projeção. O zoom manual continua permitindo inspecionar detalhes; ao ultrapassar as bordas reais da tela, use enquadramento ou foco em um qubit.

## Próximas entregas propostas

Os itens **1–4 foram entregues na versão 0.12**, junto com o editor de circuitos. Veja [manual e validação](circuitos-interativos-0.12.md). O estudo conjunto de Trotter/ruído (item 6) e caches limitados de Bloch/probabilidades (parte do item 8) foram entregues na [0.13](evolucao-0.13.md). Comparação 3D sincronizada e exportação de GIF/quadros PNG foram entregues na [0.14](evolucao-0.14.md). Estados da comparação são carregados em segundo plano; carregamento progressivo de registros individuais continua como proposta.

| Ordem | Ajuste / funcionalidade | Resultado esperado e critério de aceite |
|---|---|---|
| 1 | Área 3D maximizada | Ocultar temporariamente controles e matrizes para ampliar a cena; sair restaura câmera, snapshot e painéis. |
| 2 | Seleção do qubit por clique | Clicar na esfera destaca o qubit e abre seus dados; clicar no fundo não muda o estado nem a seleção. Funciona com rotação e escala de tela. |
| 3 | Navegação por arraste com Shift | Pan com Shift + botão esquerdo, para quem usa touchpad sem botão central; não dispara rotação ao mesmo tempo. |
| 4 | Inspeção científica no próprio visualizador | Mostrar métricas do snapshot selecionado e cursor temporal sobre F(t), pureza e energia, sincronizados com o 3D e com a tabela. Reutiliza as análises existentes e suas referências. |
| 5 | Comparação de duas execuções em 3D | Duas cenas com tempo e câmera sincronizados, cores e legendas distintas, verificando compatibilidade de sistema/protocolo antes de comparar. |
| 6 | Estudo conjunto de Trotter e ruído | Varrer passos nas duas condições e mostrar erro ideal/exato versus erro ruidoso/exato; identificar o melhor ponto apenas dentro da faixa realmente calculada. |
| 7 | Exportação da sequência visual | Exportar snapshots numerados com instante, configuração e metadados; montar animação somente com estados efetivamente simulados e duração didática explícita. |
| 8 | Cache e carregamento progressivo | Reutilizar vetores de Bloch e séries derivadas; carregar registros maiores fora da thread gráfica, com cancelamento e limite de memória. |

## Validação exigida para as próximas mudanças

- Câmera e aparência não alteram os estados, as probabilidades nem as métricas.
- Redimensionar e navegar entre páginas não causam movimento espontâneo nem crescimento do canvas.
- Verificar telas largas/estreitas e escalas de 100%, 125%, 150% e 200%.
- Manter a distinção entre fidelidade ao circuito ideal, fidelidade à evolução exata e incerteza de amostragem.
- Ensaiar interação real no Windows com mouse, touchpad e projetor.

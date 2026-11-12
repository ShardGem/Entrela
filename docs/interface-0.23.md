# Entrela 0.23 — organização da interface e galeria do sistema

Esta etapa melhora o uso do espaço na configuração, nos gráficos e na visualização 3D. A [galeria organizada por módulo](screenshots/0.23.0/README.md) apresenta as 14 áreas do aplicativo e suas principais abas, com arquivos originais para utilização no GitHub.

## Ajustes da interface

### Abas e gráficos

O tamanho solicitado pelas abas de Resultados, Comparações, Caderno e do laboratório agora considera o conteúdo aberto. Um texto longo ou outro painel oculto deixa de reservar uma altura desnecessária para o gráfico selecionado.

Histogramas e evolução permanecem lado a lado quando há espaço; em janelas estreitas ou com texto ampliado, passam para uma coluna. Os controles de unidade, seleção de estados, exploração e dados permanecem ligados aos mesmos resultados. A mudança não altera valores, escalas científicas ou critérios de seleção.

As abas também deixam de desenhar a linha de base nativa que destoava do tema em componentes como o editor de circuitos.

### Configuração guiada

O seletor de etapas já identifica Sistema, Hamiltoniano, Evolução, Ruído e Execução. O título repetido dentro da etapa foi removido no modo guiado; no avançado, os cabeçalhos continuam disponíveis para expandir/recolher as seções.

Em janelas menores, a mensagem de configuração válida cede espaço aos campos, mantendo a indicação de estado e o botão de execução. Erros e mensagens de tarefa em andamento continuam visíveis. Parâmetros, descrições e ajuda dos campos foram preservados.

### Estados em 3D

- **Reproduzir**, **Reiniciar**, **Anterior** e **Próximo** têm rótulos explícitos. Reiniciar retorna ao primeiro snapshot e preserva a câmera.
- **Câmera e visualização** mostra/recolhe zoom, foco, projeção e opções. A disposição automática acompanha o espaço disponível até uma escolha explícita do usuário.
- **Etapa, qubits e métricas** reúne as informações de interpretação em uma seção expansível, liberando a cena quando fechada.
- A escolha de câmera aberta/recolhida e da seção de detalhes é persistida. Restaurar as preferências recupera a disposição automática.
- Recolher painéis, mudar de tema ou ampliar a cena preserva o snapshot, os estados calculados e os parâmetros da câmera. Até quatro esferas continuam na mesma linha; o desfoco e a referência ideal permanecem disponíveis.

A splash restaurada e sua duração, a navegação com nomes, os grupos inicialmente abertos e os três temas existentes foram preservados. O motor científico e os formatos dos experimentos não foram alterados.

## Capturas para o GitHub

As **59 capturas** estão em `docs/screenshots/0.23.0/`: 58 imagens em 4K e a splash em seu tamanho nativo na escala 2×. As pastas são:

| Pasta | Conteúdo |
|---|---|
| `01-inicio` | Visão geral e splash original |
| `02-aprendizado` | Exemplos, conceitos, manual, tutorial e ajuda contextual |
| `03-laboratorio` | Cinco etapas de configuração, modo avançado, consulta, editor, biblioteca e operações |
| `04-resultados` | Gráficos, interpretação, dados, metadados, matriz densidade, Bloch, probabilidades e métricas |
| `05-pesquisa` | Oito tipos de estudo, resultados calculados, planejamento, ZNE e cinco modos de comparação |
| `06-acervo` | Histórico, circuito gráfico, caderno, configurações salvas e documentação/exportação |
| `07-preferencias` | Aparência, acessibilidade, exportação, backup e exemplos dos outros temas |

A janela de **1920 × 1080 pixels lógicos** é renderizada pelo Qt em escala **2×**, produzindo **3840 × 2160 pixels**. Não há ampliação posterior de PNGs. Os gráficos Matplotlib também precisam acompanhar a escala nativa; o gerador interrompe a captura se isso não ocorrer. A splash conserva seu tamanho próprio, registrado no índice.

Os cenários incluem evolução Ising ideal/ruidosa com quatro qubits, circuito GHZ com rotação RZ e ZNE de um observável. Foram executados com shots e sementes explícitos em armazenamento temporário. As quatro análises mostradas também foram calculadas: evolução temporal, varredura de ruído, mapa de calor e benchmark de mitigação.

Esses cenários demonstram o aplicativo. Não substituem o protocolo e os resultados do TCC. ZNE continua estimando observáveis; as capturas não apresentam fidelidade ou pureza de um estado mitigado inexistente.

### Índice e rastreabilidade

- `README.md`: índice por módulo, títulos e resoluções de cada captura.
- `manifesto.json`: versões, dimensões, escala, hashes dos PNGs, execução selecionada e vínculo com os estudos exibidos. Para Bloch, registra câmera e snapshot.
- `cenarios.json`: configurações, contagens, métricas, metadados e análise ZNE dos cenários.
- `estudos.json`: análises efetivamente calculadas para as figuras da galeria.

Os formulários são rascunhos independentes. O campo `selected_result_id` identifica a execução selecionada no laboratório; não afirma que editar um formulário recalculou essa execução.

Para regenerar e conferir:

```bash
python scripts/capture_gallery.py --output docs/screenshots/0.23.0 --scale 2 --overwrite
python scripts/verify_gallery.py docs/screenshots/0.23.0
```

O gerador não lê experimentos nem preferências pessoais. `--overwrite` atualiza somente os arquivos gerados com os nomes previstos. O verificador confere hashes, dimensões físicas/lógicas, referências aos cenários/estudos, arquivos sem índice e cobertura das páginas.

## Verificação e limites

Foram acrescentados testes de dimensionamento por aba ativa, visibilidade dos gráficos completos, empilhamento em janela menor, acesso aos campos com texto de 24 px, erros de configuração e persistência da disposição 3D. Os testes também verificam que recolher painéis preserva o snapshot, a câmera e os estados calculados.

A suíte completa passou com **641 testes**, em 371,24 segundos. O teste do laboratório percorreu as 14 páginas, execuções ideais/ruidosas com e sem snapshots, ZNE, tutorial e recuperação dos dados. O wheel 0.23 abriu em Python isolado; seus 114 módulos Python correspondem aos arquivos da entrega. A verificação de dependências e a conferência das 59 capturas também passaram.

A revisão identificou um teste de exportação GIF dependente de quanto tempo uma exportação pequena demorava. Ele agora mantém o trabalho pendente até a interface processar três eventos, depois executa a exportação real e verifica o arquivo. Isso verifica a execução em segundo plano sem impor duração artificial ao aplicativo.

As verificações e as capturas utilizam **Qt offscreen no Linux**. A revisão manual nativa no Windows continua pendente. As imagens documentam os estados selecionados do aplicativo; não equivalem a validar todas as combinações de resolução, dados e interação.

Permanecem como próximos refinamentos: disposição persistente dos demais painéis, tabelas muito extensas, revisão de textos de ajuda por tarefa e validação visual nativa no Windows. Os itens científicos P2 permanecem separados desta entrega.

# Entrela 0.24.1 — navegação e consistência visual

Todas as funcionalidades têm acesso direto e identificado pelo nome no menu lateral. Os agrupadores organizam o trabalho por finalidade; não substituem as entradas das ferramentas. Início fica no topo e Preferências no rodapé.

| Grupo | Acessos diretos |
|---|---|
| Laboratório | Configurar simulação, Editor de circuitos, Resultados, Estados quânticos 3D |
| Investigação | Estudos e varreduras, Mitigação ZNE, Comparar execuções |
| Registros | Histórico de execuções, Anotações da execução, Configurações salvas, Relatórios e exportações |
| Aprendizado | Exemplos prontos, Conceitos e manual |

Os grupos começam expandidos, podem ser recolhidos independentemente e respeitam a preferência de redução de movimento. O menu estreito mantém os nomes. A rolagem permite alcançar todas as ferramentas em janelas menores e com texto ampliado; Início e Preferências continuam fixos.

## Consistência e comportamento

- Cabeçalhos de grupo usam chevrons e destaque discreto. A seleção principal fica na funcionalidade aberta, com alinhamento estável dos ícones.
- Ícones vetoriais, recuos e espaçamentos são consistentes entre os grupos e os três temas.
- Tooltips e descrições acessíveis explicam a finalidade de cada ferramenta.
- O título da janela identifica a função aberta; o caminho acima dele indica seu grupo e contexto.
- Clicar em Estudos e varreduras abre os estudos. Clicar em Comparar execuções abre as comparações. A última tela usada no grupo não altera o destino do clique.
- Editor de circuitos abre o rascunho editável. O circuito executado permanece uma consulta dos Resultados, com identificação própria.
- Configurações salvas abre o diálogo de parâmetros reutilizáveis sem trocar a execução selecionada ou o rascunho atual.
- Seletores redundantes de área deixam de disputar espaço com o menu. Os controles locais de preparação, resultados e visualização permanecem disponíveis.

Os rascunhos, anotações, simulações, referências científicas, exportações, preferências e splash foram preservados. O seletor de critério das comparações também se adapta à largura disponível com texto ampliado, mantendo sua explicação completa no tooltip.

## Capturas

A [galeria 0.24.1](screenshots/0.24.1/README.md) registra a navegação atual nas telas reais. O gerador utiliza dados temporários, simulações com sementes registradas e resolução nativa do Qt. Os índices, dimensões e hashes permitem conferir os arquivos. Os cenários demonstram o aplicativo e não substituem os experimentos do TCC.

```bash
python scripts/capture_gallery.py --output docs/screenshots/0.24.1 --scale 2 --overwrite
python scripts/verify_gallery.py docs/screenshots/0.24.1
```

## Verificações

Passaram **69 testes em 112,87 s**, cobrindo acessos diretos, seleção, teclado, grupos independentes, rascunhos, execução selecionada, tutorial, histórico, exportação e os três temas em diferentes dimensões e escalas de texto. O wheel foi aberto fora do projeto e seus **120 módulos Python** correspondem aos fontes. O teste de fluxo percorreu as 14 páginas, simulou casos ideais/ruidosos com e sem snapshots, executou ZNE e conferiu tutorial, importação/exportação e reabertura. As **66 capturas** foram verificadas por dimensões e hashes; a verificação de dependências também passou. Os resultados estão no [registro da validação](validacao-interface-0.24.1.json). As verificações locais usam Qt offscreen no Linux; a revisão visual manual nativa no Windows permanece pendente.

# Entrela 0.22 — base visual e próximos refinamentos

Esta entrega começa a refatoração da interface sobre os componentes Qt existentes. Os três estilos pedidos estão disponíveis em **Preferências → Aparência → Tema**. Grafite é o padrão para novas preferências; escolhas já salvas continuam válidas.

## Estilos disponíveis

| Estilo | Característica | Uso sugerido |
|---|---|---|
| **Grafite · padrão Entrela** | Fundo neutro, superfícies discretas e ciano suave | Trabalho cotidiano; preserva a identidade do Entrela |
| **Claro científico** | Fundo claro, texto escuro e destaque azul | Leitura, tabelas e ambientes iluminados |
| **Azul escuro** | Fundo azulado e destaque azul suave | Preferência pessoal para circuitos e visualizações |
| Automático | Grafite ou Claro científico conforme o sistema | Acompanhar a aparência do computador |

**Cor de destaque → Padrão do tema** usa a combinação de cada estilo. Ciano, azul, violeta e verde continuam disponíveis como personalizações independentes. Preferências antigas de tema claro/escuro, cor, tamanho de texto e densidade são preservadas. Uma cor anteriormente salva como Ciano continua sendo Ciano.

Abra a [galeria comparativa](galeria-interface.html) no navegador para alternar os estilos em cinco telas reais. As imagens também estão disponíveis diretamente:

| Tela | Grafite | Claro científico | Azul escuro |
|---|---|---|---|
| Configuração | [Imagem](images/0.22/grafite-simulacao.png) | [Imagem](images/0.22/claro-simulacao.png) | [Imagem](images/0.22/azulado-simulacao.png) |
| Resultados | [Imagem](images/0.22/grafite-resultados.png) | [Imagem](images/0.22/claro-resultados.png) | [Imagem](images/0.22/azulado-resultados.png) |
| Estados 3D | [Imagem](images/0.22/grafite-bloch.png) | [Imagem](images/0.22/claro-bloch.png) | [Imagem](images/0.22/azulado-bloch.png) |
| Histórico | [Imagem](images/0.22/grafite-historico.png) | [Imagem](images/0.22/claro-historico.png) | [Imagem](images/0.22/azulado-historico.png) |
| Preferências | [Imagem](images/0.22/grafite-preferencias.png) | [Imagem](images/0.22/claro-preferencias.png) | [Imagem](images/0.22/azulado-preferencias.png) |

## O que foi alterado

- Paletas em um módulo compartilhado, aplicadas aos componentes Qt, ícones e figuras existentes. Temas mudam a apresentação, sem recalcular resultados.
- Painéis com menos contornos e abas com seleção mais discreta. Campos mantêm contornos e foco; informações são agrupadas por espaçamento e hierarquia.
- Título da página concentrado na barra superior. Descrições, ajuda e ações locais permanecem nas páginas.
- Métricas de Resultados distribuídas em quatro, duas ou uma coluna conforme o espaço e o tamanho do texto. Fidelidade, pureza, energia e infidelidade continuam disponíveis.
- Explicação do tema selecionado em Preferências. O modo automático acompanha o sistema; redução de movimento e alto contraste continuam disponíveis nos três estilos.
- Foco de teclado dos botões definido após os estilos específicos, evitando que o estilo de uma ação oculte o contorno.

A splash restaurada, o ícone, os grupos inicialmente expandidos, os nomes na navegação estreita e o botão Buscar permanecem. Não houve alteração do motor de simulação, métricas, ruído, mitigação ou formatos dos registros.

## Análise e sequência recomendada

O projeto já possui design system, temas, escala de texto, densidade, tabelas compartilhadas e exportadores. A evolução deve consolidar essa base, em vez de criar outro conjunto de componentes em paralelo.

| Prioridade | Próximo trabalho | Resultado esperado |
|---|---|---|
| 1 | **Organização da simulação** | Parâmetros à esquerda e revisão à direita quando couberem; empilhamento em janelas menores. Manter execução/cancelamento acessíveis e distinguir rascunho de execução selecionada |
| 2 | **Área 3D** | Dar prioridade à cena. Agrupar reprodução, câmera e interpretação; tornar detalhes recolhíveis sem perder a etapa nem o qubit. Preservar desfoco, câmera independente e até quatro qubits por linha |
| 3 | **Gráficos** | Melhorar distribuição de altura, legendas e acesso aos controles. Usar cores e estilos de linha consistentes e permitir leitura dos dados por tabela. Manter unidades, referências e critérios de seleção explícitos |
| 4 | **Circuitos e histórico** | Dar mais espaço ao desenho e ao inspetor; tornar ações secundárias menos dispersas. Preservar consulta sem edição no histórico, estado da seleção, ajuda e versões do editor |
| 5 | **Preferências** | Separar Aparência, Área de trabalho, Visualizações, Acessibilidade e Exportação. Lembrar divisões dos painéis, permitir restaurar a disposição e testar uma escala que coordene também ícones e margens |
| 6 | **Telas de pesquisa e aprendizado** | Aplicar a mesma hierarquia em estudos, comparação, mitigação e caderno. Manter resultados no contexto da tarefa e apresentar requisitos nos estados vazios |

Os itens dessa tabela são próximos refinamentos, não funcionalidades concluídas nesta entrega. A mudança de paleta já atinge as páginas existentes; a reorganização completa de cada fluxo precisa de entregas verificáveis.

### Regras visuais para as próximas telas

- Corpo legível, títulos moderados e números alinhados. A escala de fonte já existe; a fonte depende das famílias disponíveis no computador.
- Uma ação principal por contexto; ações secundárias com texto claro. Ícones isolados somente quando o significado for claro, com tooltip e nome acessível.
- Espaçamentos repetíveis e divisores discretos. Evitar caixas dentro de caixas quando título e alinhamento resolvem o agrupamento.
- Cor de ação, estado de execução e série científica têm funções distintas. Comparações devem funcionar também com estilos de linha, marcadores e legendas.
- Acesso por teclado, redução de movimento e alto contraste fazem parte de cada componente. Texto ampliado deve reorganizar o conteúdo, sem exigir que o usuário diminua a fonte.
- Resultados continuam associados à configuração executada. Alterações em formulários não transformam dados anteriores em resultados da nova configuração.

### Configurações que fazem sentido acrescentar

Além das opções já existentes, priorizar **lembrar/restaurar a disposição dos painéis**, **grau de ajuda contextual** e **preferências de legenda e leitura dos gráficos**. A aparência da tela e o estilo científico de exportação precisam continuar independentes. Evitar multiplicar opções para cada borda ou botão.

## Verificação e limites

Os novos testes verificam os três temas, contraste dos textos e da ação principal, alto contraste, preservação dos arquivos e estados calculados, restauração do tema/cor e distribuição das métricas em 1440 × 960 e 1024 × 768 com fontes de 15 e 24 px. A tabela de linhas alternadas também é renderizada nos três temas para verificar legibilidade.

A suíte completa passou com **636 testes**, em 355,48 segundos. A validação encontrou uma rolagem global adicional na configuração com texto ampliado após abrir um resultado; o espaçamento do cabeçalho foi ajustado e o teste original passou novamente, preservando o tamanho de fonte escolhido.

O teste do laboratório percorreu as 14 páginas, execuções ideais e ruidosas com/sem snapshots, persistência, ZNE e tutorial. O wheel 0.22 foi aberto fora do repositório em Python isolado, verificando os três temas e a restauração de Azul escuro. Seus 113 módulos Python foram comparados com os arquivos da entrega, sem divergências. A verificação de dependências também passou.

Foram geradas 30 capturas: cinco telas nos três estilos, em 1440 × 960/fonte 15 e 1024 × 768/fonte 24. A galeria foi verificada no Chromium nas 15 combinações de estilo/tela e em largura de 390 px, sem rolagem horizontal. O registro da validação fica em `work/proposta-interface/` no ambiente de execução.

As capturas são feitas com **Qt offscreen no Linux**, usando o mesmo experimento ideal de Bell em armazenamento temporário. Elas documentam a interface e não são resultados experimentais para o TCC. Em Bell ideal, vetores locais nulos são esperados; as esferas sem seta não indicam ausência de estado global.

Capturas e testes geométricos não substituem validação manual no Windows, com escala de tela e fontes nativas. Essa validação permanece pendente. O contraste testado cobre as combinações registradas nos testes, não representa uma certificação integral de acessibilidade.

Para gerar novas capturas sem usar dados pessoais:

```bash
python scripts/preview_interface.py --output work/interface
python scripts/preview_interface.py --output work/interface-ampliada --width 1024 --height 768 --font-size 24
```

O script usa somente os temas de produção e não injeta estilos ou dados fictícios nas telas.

Se o navegador bloquear a abertura direta da galeria HTML, sirva somente a documentação local:

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Abra `http://127.0.0.1:8765/galeria-interface.html`. A galeria é documentação; os temas do aplicativo continuam sendo componentes nativos Qt.

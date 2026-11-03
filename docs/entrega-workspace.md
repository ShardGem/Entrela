# Recuperação e integração do workspace

Documento histórico da recuperação inicial. Para o estado atual, consulte [Evolução 0.14](evolucao-0.14.md), [Evolução 0.13](evolucao-0.13.md), [Circuitos 0.12](circuitos-interativos-0.12.md) e [Evolução 0.11](evolucao-0.11.md).

O pacote original de 54 arquivos foi recuperado do anexo parte_001.zip. As correções científicas
e de persistência foram reconstruídas e a integração didática foi concluída nesta entrega.
A especificação de produto descreve também etapas futuras; não representa uma lista de funções já implementadas.

## Entregue

- Motor científico compartilhado, configurações congeladas, sementes efetivas e versões registradas.
- Matrizes densidade no caso ruidoso, referência ideal e métricas calculadas do estado.
- Validação térmica correta, 1–6 qubits, estados zero/plus/Bell, ordens Trotter 2/4.
- Guiado/Avançado com os mesmos widgets e etapas livres.
- Doze exemplos copiados para edição sem alterar o catálogo.
- Tutorial de Bell com ações obrigatórias, pausa e progresso persistente.
- Resultados com gráficos, interpretação, tabela de probabilidades e metadados.
- Histórico, rascunhos, reabertura e comparação conservadora de sistemas e protocolos iguais.
- ZNE com escalas reais 1/3/5, compilação antes do folding e nenhum otimizador depois.
- Importação/exportação científica e paleta de comandos.
- Workers com sinal de resultado separado do término da thread, cancelamento cooperativo e proteção de resultados não salvos.

## Validação

A suíte inclui referência independente por exponencial de matriz, solução analítica de despolarização,
distribuição de Bell, oscilação de um spin, todos os exemplos, matrizes densidade ruidosas,
seed reprodutível, folding unitário, ZNE, JSON complexo, compatibilidade legada, escrita atômica,
e fluxo real de interface até salvar e reabrir. Executar:

```bash
/workspace/.venvs/entrela/bin/python -m pytest -q -p no:cacheprovider
/workspace/.venvs/entrela/bin/python scripts/cloud_smoke.py
```

O teste gráfico nesta máquina é offscreen. Não comprova comportamento em outros sistemas operacionais
nem acessibilidade com leitor de tela. Cancelar aguarda a operação Aer atual concluir.

## Escopo seguinte

Projetos, varreduras e relatórios foram entregues posteriormente (0.11); circuitos editáveis, na 0.12.
Um editor de Hamiltoniano personalizado permanece fora do escopo atual. Comparação de métricas mitigadas exige antes
um método que reconstrua um estado mitigado válido; o ZNE atual estima apenas um observável.

Publicação do ambiente e sincronização Git são operações separadas. A entrega só deve ser anunciada
como preservada no GitHub após conferir o SHA remoto e recuperar o código a partir dele.

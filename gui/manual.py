"""Scientific help, shared by the learning page and contextual dock."""
WELCOME_HTML = """
<h1 id="Início">Aprender o Entrela</h1>
<p>Use Configuração guiada para percorrer as etapas ou Todos os parâmetros (modo Avançado) para abrir as seções que precisar.
Os mesmos controles preservam a configuração ao alternar. O botão Buscar encontra comandos, exemplos e conceitos.</p>
<p>No modo Avançado, cada categoria pode ser expandida ou recolhida; seu cabeçalho resume os valores.
Use os botões ? ou a ajuda de cada campo para consultar significado, unidades e limites. A prévia do estado inicial
é descritiva e ideal; não calcula o efeito do ruído nem substitui uma execução.</p>
<p>Em janelas menores, alterne entre Parâmetros e Prévia e revisão. A barra de execução permanece acessível.
Configurações inválidas indicam o campo a revisar. O menu Exemplos carrega configurações da galeria sem executá-las.</p>
<h2 id="Qubits">Qubits e estado inicial</h2>
<p>São suportados de 1 a 6 qubits. |0…0⟩ é o estado zero; |+…+⟩ prepara superposição.
Bell usa H(q0) e CX(q0,q1), requer dois qubits e possui vetores locais nulos, mesmo sendo globalmente puro.
Nas bitstrings, q0 fica à direita.</p>
<h2 id="Hamiltoniano">Hamiltoniano</h2>
<p>Ising: H=+J ΣZZ+h ΣX. J positivo favorece antialinhamento no termo ZZ; J negativo favorece alinhamento.
Heisenberg: J Σ(XX+YY+ZZ). XY: J Σ(XX+YY). XXZ: J Σ(XX+YY+0,5ZZ). O campo h só atua no Ising.
A fronteira periódica fecha cadeias com mais de dois qubits.</p>
<h2 id="Evolução">Evolução</h2>
<p>Suzuki–Trotter de ordem 2 ou 4 aproxima a evolução do Hamiltoniano. Mais passos podem reduzir
o erro de aproximação, mas também adicionam operações sujeitas a ruído. Tempo adimensional, ℏ=1.</p>
<h2 id="Shots">Shots</h2><p>Número de amostras. Mais shots reduzem incerteza de amostragem, mas não corrigem
ruído físico. As métricas de estado são calculadas diretamente pelo simulador, não por contagens em uma única base.</p>
<h2 id="Semente">Semente</h2><p>Inteiro entre 0 e 4294967295. Campo vazio gera uma semente automática,
registrada no resultado. Reprodução entre versões diferentes não é garantida. Repetir a mesma semente não
produz observações independentes. Fidelidade e pureza calculadas da matriz densidade do ensemble não ganham
incerteza estatística pela simples troca da semente de amostragem.</p>
<h2 id="Ruído">Ruído</h2><p>O caso ideal usa vetores de estado. Com ruído, matrizes densidade representam
o ensemble. O canal incide nas portas, inclusive de preparação. O ruído térmico usa durações por porta 1q/2q configuráveis, com padrão de 50 ns,
como exemplo educativo; não representa calibração atual de hardware.</p>
<h2 id="T₁">T₁</h2><p>Tempo positivo de relaxamento da população, em µs.</p>
<h2 id="T₂">T₂</h2><p>Tempo positivo de perda de coerência, em µs. Para o canal térmico, T₂ ≤ 2T₁.
A correção sugerida é aplicada somente por clique.</p>
<h2 id="Fidelidade">Fidelidade</h2><p>Fidelidade de Uhlmann, na convenção ao quadrado.
Compara o estado final ao mesmo circuito Suzuki–Trotter sem ruído. Não mede erro de Trotter
em relação à evolução exata.</p>
<h2 id="Pureza">Pureza</h2><p>Tr(ρ²). Pureza global e local são diferentes: Bell tem pureza global 1,
mas cada qubit reduzido possui pureza 1/2.</p>
<h2 id="Mitigação">Mitigação</h2><p>ZNE extrapola Z de um qubit a ruído zero, por folding com escalas efetivas
1,3,5. Não reconstrói um estado mitigado e não garante melhoria. Estimativas não são truncadas ao intervalo físico.
Os erros padrão mostrados descrevem amostragem, não incerteza do modelo de extrapolação.</p>
<h2 id="Reprodutibilidade">Reprodutibilidade</h2><p>O histórico guarda configuração imutável, estados complexos,
contagens, tempos, versões e semente efetiva. O JSON pode ser importado como cópia independente.
Pacotes ZIP reúnem os arquivos; extraia o JSON do experimento para importá-lo.
Editar o formulário não altera execuções anteriores. Dê um nome ao criar a execução; em Histórico, use Visualizar para consultar os detalhes e Abrir para reutilizar os resultados. Descrição, objetivos, hipóteses e anotações documentam o estudo sem modificar os dados científicos originais.</p>
<h2 id="Protocolos">Protocolos e evidências</h2>
<p>Em Análises, registre pergunta, hipótese, controles e referência no TCC. Salvar nova revisão preserva
o plano anterior. Carregar protocolo reabre fonte e parâmetros; Calcular análise gera outra evidência.
A reprodução de uma análise usa as opções registradas. Documentação mostra os vínculos entre fonte,
estudos, protocolos e referências no texto.</p>
<h2 id="Análises">Estudos de ruído e amostragem</h2>
<p>Mapas de calor variam dois parâmetros em até 64 pontos reais. Estabilidade ZNE investiga viés,
variância amostral e RMSE de estimativas de Z. Orçamento equivalente distribui o mesmo total de shots
por método; isso não iguala profundidade ou tempo. Sementes distintas caracterizam amostragem, não
incerteza das fidelidades do ensemble. Ajustes linear e quadrático compartilham medições.</p>
<h2 id="Comparações">Comparações lado a lado</h2>
<p>Escolha as execuções A/B e selecione a visualização desejada. Estados e curvas são carregados em segundo plano; mensagens explicam quando os dados ou as configurações são incompatíveis. Bloch oferece câmeras e
snapshots sincronizados; sem grades temporais compatíveis, exibe estados finais. Observáveis ZNE
usam o baseline compilado do próprio ajuste. Não há estado mitigado reconstruído por extrapolação.</p>
<h2 id="Documentação">Documentação científica</h2>
<p>Exporte uma execução ou a comparação carregada como ZIP, PDF ou GIF. O pacote inclui dados integrais,
PNG/SVG/PDF, tabelas LaTeX, protocolos, manifesto e hashes. GIF usa snapshots reais, sem interpolação,
reprodução única e tempo didático. O pacote inclui a sequência PNG selecionada. Na página 3D, exporte
a vista atual com câmera e snapshot. JSON/CSV mantêm os dados de precisão integral. Relatórios PDF usam páginas A4 de 210 × 297 mm, texto vetorial e resolução configurável para imagens rasterizadas (padrão de 300 DPI).</p>
<h2 id="Conceitos">Conceitos e exemplos executáveis</h2>
<p>Em Aprender e consultar, pesquise os conceitos e abra seus detalhes. Circuitos demonstrativos abrem no editor e precisam ser executados para gerar dados; as previsões do material são analíticas e ideais. Shor e teletransporte são explicados conceitualmente: a plataforma não apresenta protocolos completos desses algoritmos como executados. Referências bibliográficas identificam as fontes; esta biblioteca não inclui links externos sem verificação.</p>
"""

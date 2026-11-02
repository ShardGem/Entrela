"""Scientific help, shared by the learning page and contextual dock."""
WELCOME_HTML = """
<h1 id="Início">Aprender o Entrela</h1>
<p>Use o modo Guiado para percorrer as etapas ou o Avançado para ver todos os parâmetros.
Os mesmos controles preservam a configuração ao alternar. Ctrl+K abre comandos, exemplos e conceitos.</p>
<p>No modo Avançado, a navegação por etapas desaparece: cada categoria fica disponível no mesmo formulário.
Use os botões ? ou a ajuda de cada campo para consultar significado, unidades e limites. A prévia do estado inicial
é descritiva e ideal; não calcula o efeito do ruído nem substitui uma execução.</p>
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
o ensemble. O canal incide nas portas, inclusive de preparação. O ruído térmico usa 50 ns por porta
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
contagens, tempos, versões e semente efetiva. Exportações JSON/ZIP podem ser importadas como cópias independentes.
Editar o formulário não altera execuções anteriores.</p>
"""

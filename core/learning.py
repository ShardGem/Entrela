"""Reviewed educational content and small executable unitary demonstrations.

Examples describe ideal mathematical predictions, never saved experimental
results. References are bibliographic records; no unverified web links are
offered by this offline catalogue.
"""

from dataclasses import dataclass
from html import escape
from math import pi

from core.circuit_document import CircuitDocument, CircuitGate


TEXTBOOK = (
    "Nielsen, M. A.; Chuang, I. L. Quantum Computation and Quantum Information. "
    "10th Anniversary Edition. Cambridge University Press, 2010."
)
GENTLE = (
    "Rieffel, E.; Polak, W. Quantum Computing: A Gentle Introduction. "
    "MIT Press, 2011."
)


def _circuit(qubits, *gates):
    return CircuitDocument(
        qubits,
        tuple(
            CircuitGate(g[0], tuple(g[1]), tuple(g[2]) if len(g) > 2 else ())
            for g in gates
        ),
    )


@dataclass(frozen=True)
class LearningConcept:
    key: str
    title: str
    category: str
    definition: str
    intuition: str
    mathematics: str
    visual: str
    example: str
    application: str
    exercise: str
    answer: str
    references: tuple[str, ...] = (TEXTBOOK,)
    demonstration: CircuitDocument | None = None
    demonstration_note: str = ""

    def search_text(self):
        return " ".join(
            (self.title, self.category, self.definition, self.intuition, self.application)
        )

    def to_html(self):
        sections = (
            ("Definição", self.definition),
            ("Uma ideia intuitiva", self.intuition),
            ("Fundamentação matemática", self.mathematics),
            ("O que observar na visualização", self.visual),
            ("Exemplo prático", self.example),
            ("Aplicações", self.application),
            ("Experimente pensar", self.exercise),
            ("Pista para conferir", self.answer),
        )
        body = "".join(
            f"<h2>{escape(title)}</h2><p>{escape(text)}</p>"
            for title, text in sections
        )
        demonstration = (
            "Circuito disponível para abrir no editor. Execute-o para gerar seus próprios dados. "
            if self.demonstration is not None
            else "Estudo conceitual: esta página não executa automaticamente o protocolo. "
        )
        bibliography = "".join(f"<li>{escape(ref)}</li>" for ref in self.references)
        return (
            f"<p>{escape(self.category)}</p><h1>{escape(self.title)}</h1>"
            + body
            + "<h2>Na plataforma</h2><p>"
            + escape(demonstration + self.demonstration_note)
            + "</p><h2>Referências e leitura complementar</h2><ul>"
            + bibliography
            + "</ul><p>As previsões dos exemplos são analíticas e ideais. "
            "Contagens finitas e canais de ruído podem alterar os resultados de uma execução.</p>"
        )


CONCEPTS = (
    LearningConcept(
        "qubit", "Qubit", "Fundamentos",
        "Um qubit é um sistema quântico com espaço de estados de dimensão dois. Um estado puro é descrito por duas amplitudes complexas normalizadas.",
        "As amplitudes não são duas probabilidades independentes: suas fases também influenciam operações e interferência. Uma medição em Z produz somente um dos resultados 0 ou 1.",
        "|ψ⟩ = α|0⟩ + β|1⟩, com |α|² + |β|² = 1. Em Z, P(0)=|α|² e P(1)=|β|². Uma fase global não muda essas previsões.",
        "Na esfera de Bloch, |0⟩ está em +Z e |1⟩ em −Z. Um vetor local nulo representa um estado misto reduzido; não significa ausência de qubit.",
        "Partindo de |0⟩, X prepara |1⟩. A previsão ideal é P(1)=1.",
        "É a unidade de informação de circuitos, sensores e protocolos de comunicação quântica.",
        "Qual é a probabilidade de obter 1 no estado √3/2 |0⟩ + 1/2 |1⟩?",
        "P(1)=|1/2|²=1/4. A soma das probabilidades é 1.",
        demonstration=_circuit(1, ("x", (0,))),
    ),
    LearningConcept(
        "superposicao", "Superposição", "Fundamentos",
        "Uma superposição é uma combinação linear de estados de uma base. Ser superposição depende da base escolhida.",
        "|+⟩ tem resultados igualmente prováveis em Z, mas um resultado definido na base X. O que a distingue de uma mistura é a coerência entre componentes.",
        "H|0⟩=|+⟩=(|0⟩+|1⟩)/√2. Sua matriz densidade tem elementos fora da diagonal: ρ₀₁=ρ₁₀=1/2.",
        "O vetor de Bloch vai de +Z para +X. A mistura equiprovável de |0⟩ e |1⟩ teria vetor nulo, embora o histograma Z fosse igual.",
        "Execute H em um qubit inicialmente em |0⟩. Depois acrescente outro H: H²=I e a probabilidade ideal de 0 volta a 1.",
        "Preparação de estados e criação de interferência em algoritmos e interferômetros.",
        "Por que um histograma 50%/50% em Z não prova, sozinho, que o estado é uma superposição pura?",
        "A mistura I/2 produz o mesmo histograma Z. É preciso informação em outras bases ou conhecimento da preparação.",
        demonstration=_circuit(1, ("h", (0,))),
    ),
    LearningConcept(
        "emaranhamento", "Emaranhamento", "Fundamentos",
        "Um estado composto é emaranhado quando não pode ser escrito como uma mistura de produtos de estados locais.",
        "O estado conjunto pode ser puro mesmo que cada parte isolada seja mista. Correlações em uma única base, por si só, não demonstram emaranhamento.",
        "Para |Φ+⟩=(|00⟩+|11⟩)/√2, ρ₀=Tr₁(|Φ+⟩⟨Φ+|)=I/2. A pureza global é 1 e a local é 1/2.",
        "Em Bell ideal, as duas setas locais encolhem a zero. As esferas locais não mostram todas as correlações do estado conjunto.",
        "H(q0), seguido de CX(q0,q1), prepara |Φ+⟩. Compare pureza global, purezas locais e a distribuição conjunta.",
        "Teletransporte, comunicação quântica e recursos de computação distribuída.",
        "A mistura 1/2 |00⟩⟨00| + 1/2 |11⟩⟨11| também dá apenas 00 e 11. Ela é emaranhada?",
        "Não: já está escrita como mistura de produtos. A coerência de Bell não aparece nesse histograma sozinho.",
        demonstration=_circuit(2, ("h", (0,)), ("cx", (0, 1))),
    ),
    LearningConcept(
        "medicao", "Medição quântica", "Fundamentos",
        "Uma medição associa probabilidades e estados condicionados aos resultados. O simulador amostra contagens na base computacional ao final do circuito.",
        "Shots repetem a preparação e a medição. Eles estimam probabilidades; não revelam todas as amplitudes de um único exemplar do estado.",
        "P(m)=Tr(Πₘρ). Se P(m)>0, o estado condicionado é ΠₘρΠₘ/P(m). Para Z, Π₀=|0⟩⟨0| e Π₁=|1⟩⟨1|.",
        "O histograma mostra frequências amostrais; Probabilidades no instante usa o estado calculado. Snapshots são anteriores à medição final, não trajetórias de colapso.",
        "H|0⟩ prevê P(0)=P(1)=1/2. Em 100 shots, obter exatamente 50 de cada não é obrigatório.",
        "Leitura de resultados, estimação de observáveis e protocolos de caracterização de estados.",
        "Aumentar de 100 para 10 000 shots elimina o ruído de decoerência?",
        "Não. A flutuação amostral típica diminui como 1/√N; o canal físico do modelo continua atuando.",
        demonstration=_circuit(1, ("h", (0,))),
        demonstration_note="O editor adiciona medição final de todos os qubits em Z; medições intermediárias não são suportadas.",
    ),
    LearningConcept(
        "bloch", "Esfera de Bloch", "Estados e visualização",
        "A esfera de Bloch representa qualquer matriz densidade de um qubit por um vetor real de comprimento no máximo 1.",
        "A direção resume os valores médios de X, Y e Z. O comprimento distingue estados puros locais de mistos; correlações entre qubits exigem outras informações.",
        "ρ=(I+xX+yY+zZ)/2; x=⟨X⟩, y=⟨Y⟩, z=⟨Z⟩. Tr(ρ²)=(1+|r|²)/2.",
        "A superfície corresponde a estados puros de um qubit; o centro é I/2. Rotacionar a câmera altera somente a vista, nunca o estado.",
        "H prepara +X; RZ(π/2) leva esse vetor a +Y. O histograma Z continua idealmente 50%/50%.",
        "Inspeção de rotações, coerência, relaxamento e estados reduzidos.",
        "Um vetor r=(0; 0; 0,6), com z=0,6, tem qual pureza?",
        "Para r=(0;0;0,6), a pureza é (1+0,36)/2=0,68.",
        demonstration=_circuit(1, ("h", (0,)), ("rz", (0,), (pi / 2,))),
    ),
    LearningConcept(
        "decoerencia", "Decoerência", "Estados e visualização",
        "Decoerência descreve a perda de coerência observável no sistema reduzido devido à interação com graus de liberdade não acompanhados.",
        "Um estado misto não representa apenas desconhecimento de uma seta clássica. T₁ descreve relaxamento da população e T₂ descreve a perda de coerência transversal.",
        "Para relaxamento ideal ao estado fundamental: z(t)=1+[z(0)−1]e^(−t/T₁); x,y decaem com T₂. Em um canal térmico Markoviano físico, T₂≤2T₁.",
        "A despolarização contrai vetores em direção ao centro. Relaxamento ao estado fundamental tende a +Z; a pureza pode diminuir e depois aumentar.",
        "Prepare |+⟩ e compare o mesmo circuito ideal com ruído despolarizador ou térmico. Uma única porta e muitas portas têm exposições diferentes ao canal.",
        "Estudo de limitações de dispositivos, modelagem de erros e escolha de estratégias de mitigação.",
        "Perda de pureza local sempre significa ruído?",
        "Não. Um subsistema de Bell ideal já é misto por emaranhamento; examine também o estado global e a referência ideal.",
        demonstration=_circuit(1, ("h", (0,)), ("id", (0,)), ("id", (0,)), ("id", (0,))),
        demonstration_note="Ative o ruído no editor para fazer a comparação. O modelo térmico usa durações assumidas por operação (padrão: 50 ns para portas 1q e 2q), configuráveis e sem calibração de hardware.",
    ),
    LearningConcept(
        "interferencia", "Interferência", "Estados e visualização",
        "Interferência ocorre quando amplitudes de caminhos indistinguíveis se somam antes de calcular probabilidades.",
        "Uma fase que não altera um histograma em uma etapa pode mudar o resultado após outra transformação. Amplitudes podem se reforçar ou se cancelar.",
        "H²=I e HZH=X. Assim, HZH|0⟩=|1⟩, enquanto HH|0⟩=|0⟩.",
        "Após H, Z muda +X para −X sem alterar probabilidades Z. O H seguinte converte essa fase relativa em população.",
        "Compare H–H com H–Z–H no mesmo qubit. Idealmente, o resultado final muda de 0 para 1.",
        "Amplificação de amplitudes, interferometria e leitura de propriedades de oráculos.",
        "Por que o Z isolado no estado |+⟩ não muda o histograma na base Z?",
        "Ele troca a fase relativa; os módulos das amplitudes permanecem iguais. Outra mudança de base revela a diferença.",
        demonstration=_circuit(1, ("h", (0,)), ("z", (0,)), ("h", (0,))),
    ),
    LearningConcept(
        "portas", "Portas quânticas", "Circuitos e operações",
        "Portas unitárias modelam transformações reversíveis de um sistema fechado. Medição e canais de ruído não são, em geral, portas unitárias sobre o sistema observado.",
        "Uma porta de um qubit rotaciona seu estado na esfera de Bloch. Portas controladas atuam no alvo de acordo com o estado do controle e podem criar emaranhamento.",
        "U†U=I. X=[[0,1],[1,0]], Z=diag(1,−1), H=(X+Z)/√2. Rᵢ(θ)=exp(−iθσᵢ/2).",
        "X troca os polos Z; Z gira a fase relativa. CX não copia um estado quântico arbitrário: pode correlacionar os qubits.",
        "Prepare H(q0), depois CX(q0,q1). No editor, confira a ordem controle/alvo e os ângulos em radianos.",
        "Construção de algoritmos, decomposição de evoluções e preparação de estados.",
        "X seguido de X deixa o estado inicial inalterado? Isso exige que o estado seja |0⟩?",
        "X²=I para qualquer estado de entrada, inclusive superposições e matrizes densidade.",
        demonstration=_circuit(1, ("x", (0,)), ("x", (0,))),
    ),
    LearningConcept(
        "circuitos", "Circuitos quânticos", "Circuitos e operações",
        "Um circuito especifica qubits e uma sequência de operações, incluindo a preparação e a leitura quando definidas.",
        "A ordem importa para operações que não comutam. Profundidade e quantidade de portas medem aspectos diferentes do custo e não equivalem ao tempo de CPU.",
        "Se U₁ é aplicado primeiro, então |ψfinal⟩=Uₙ⋯U₂U₁|ψinicial⟩. Em geral UV≠VU.",
        "As linhas representam qubits e as colunas mostram a sequência. Nas bitstrings do Entrela, q0 aparece à direita; controle e alvo seguem a ordem informada na porta.",
        "No par de Bell, H(q0) precede CX(q0,q1). Trocar a ordem a partir de |00⟩ não produz o mesmo estado.",
        "Descrição reproduzível de experimentos e interoperabilidade com formatos como OpenQASM.",
        "Duas portas em qubits distintos podem ocupar a mesma camada lógica? Isso garante duração física igual?",
        "Elas podem ser paralelas na análise de dependências. Duração física depende do dispositivo e do agendamento, ausentes nessa simples contagem.",
        demonstration=_circuit(2, ("h", (0,)), ("cx", (0, 1))),
        demonstration_note="O editor suporta de 1 a 6 qubits e até 200 portas unitárias, além de medição final em Z. JSON preserva o documento; OpenQASM 2 registra a fase global em um comentário Entrela.",
    ),
    LearningConcept(
        "bell", "Estados de Bell", "Circuitos e operações",
        "Os quatro estados de Bell formam uma base ortonormal de dois qubits maximamente emaranhados.",
        "Uma medição local é imprevisível, mas as medições conjuntas exibem correlações. Cada qubit isolado tem o mesmo estado I/2 nos quatro casos.",
        "|Φ±⟩=(|00⟩±|11⟩)/√2; |Ψ±⟩=(|01⟩±|10⟩)/√2. Em Φ+, ⟨ZZ⟩=1, ⟨XX⟩=1 e ⟨YY⟩=−1.",
        "O histograma Z separa Φ de Ψ, mas não distingue o sinal + do −. As duas esferas locais ficam no centro no caso ideal.",
        "H(q0) e CX(q0,q1) criam Φ+. Acrescente Z(q0) para Φ−; os histogramas Z continuam iguais.",
        "Teletransporte, codificação superdensa, testes de correlações e preparação de recursos.",
        "Qual mudança de base permite distinguir Φ+ de Φ− por correlações?",
        "Medir ambos em X: aplique H em cada qubit antes da leitura Z. Os sinais de ⟨XX⟩ são opostos.",
        demonstration=_circuit(2, ("h", (0,)), ("cx", (0, 1))),
    ),
    LearningConcept(
        "deutsch-jozsa", "Algoritmo de Deutsch–Jozsa", "Algoritmos e protocolos",
        "Sob a promessa de que f:{0,1}ⁿ→{0,1} é constante ou balanceada, o algoritmo distingue as duas classes com uma consulta ideal ao oráculo.",
        "O oráculo aplica f de forma reversível. Uma ancilla em |−⟩ converte o valor de f em fase; a interferência revela a classe prometida.",
        "U_f|x,y⟩=|x,y⊕f(x)⟩. Após as últimas Hadamard, a amplitude de |0…0⟩ é 2^(−n)Σₓ(−1)^f(x).",
        "Observe os qubits de entrada, não a ancilla. A conclusão depende da promessa; funções fora dela não são classificadas pela mesma regra.",
        "A demonstração usa n=1 e f(x)=x: X(q1), H(q0), H(q1), CX(q0,q1), H(q0). Idealmente q0=1; a ancilla q1 permanece em |−⟩.",
        "Introdução a oráculos, phase kickback e análise de complexidade por número de consultas.",
        "Remova CX do exemplo: qual função e qual saída em q0 são obtidas?",
        "O oráculo identidade representa f(x)=0, constante. O qubit de entrada termina em 0 no caso ideal.",
        references=(TEXTBOOK, "Deutsch, D.; Jozsa, R. Rapid solution of problems by quantum computation. Proceedings of the Royal Society A, 439, 553–558, 1992."),
        demonstration=_circuit(2, ("x", (1,)), ("h", (0,)), ("h", (1,)), ("cx", (0, 1)), ("h", (0,))),
        demonstration_note="Este circuito é o caso de uma entrada, com oráculo balanceado f(x)=x, não um gerador geral de oráculos.",
    ),
    LearningConcept(
        "grover", "Algoritmo de Grover", "Algoritmos e protocolos",
        "Grover amplifica a probabilidade de itens marcados por um oráculo em uma busca não estruturada.",
        "Uma reflexão muda a fase das soluções; outra reflete as amplitudes em torno de sua média. Iterações excessivas também podem reduzir a chance de sucesso.",
        "Com M soluções entre N itens, sin²θ=M/N e a probabilidade ideal após k iterações é sin²[(2k+1)θ]. O ganho de consultas é da ordem de √(N/M).",
        "As probabilidades finais concentram-se nos itens marcados. O histograma sozinho não revela o custo de implementar o oráculo.",
        "Para dois qubits, N=4 e uma solução |11⟩, uma iteração ideal é suficiente. CZ marca 11; H⊗H, X⊗X, CZ, X⊗X, H⊗H faz a difusão, até uma fase global.",
        "Busca sob oráculo, amplificação de amplitudes e subrotinas de algoritmos quânticos.",
        "Para N=4 e M=1, calcule a previsão após uma e após duas iterações.",
        "θ=π/6: uma iteração dá sin²(π/2)=1; duas dão sin²(5π/6)=1/4.",
        references=(TEXTBOOK, "Grover, L. K. A fast quantum mechanical algorithm for database search. Proceedings of the 28th ACM Symposium on Theory of Computing, 212–219, 1996."),
        demonstration=_circuit(2, ("h", (0,)), ("h", (1,)), ("cz", (0, 1)), ("h", (0,)), ("h", (1,)), ("x", (0,)), ("x", (1,)), ("cz", (0, 1)), ("x", (0,)), ("x", (1,)), ("h", (0,)), ("h", (1,))),
        demonstration_note="Exemplo específico de dois qubits, uma solução 11 e uma iteração. O oráculo não resolve uma base de dados real.",
    ),
    LearningConcept(
        "shor", "Algoritmo de Shor", "Algoritmos e protocolos",
        "Shor combina processamento clássico e busca quântica de ordem para fatorar inteiros em tempo polinomial no número de bits, no modelo ideal de circuitos.",
        "O núcleo encontra o período de aˣ mod N usando exponenciação modular reversível e estimação de fase; uma transformada de Fourier isolada não é o algoritmo completo.",
        "A ordem r satisfaz aʳ≡1 (mod N), com mdc(a,N)=1. Se r é par e a^(r/2)≠−1 (mod N), mdc(a^(r/2)±1,N) pode fornecer fatores.",
        "Resultados de estimação de fase precisam de pós-processamento por frações contínuas e verificação clássica. Distribuições didáticas calculadas no texto não são execuções.",
        "Para N=15 e a=2, a ordem é 4. Classicamente, mdc(2²−1,15)=3 e mdc(2²+1,15)=5. Esse cálculo explica a etapa posterior; não é fatoração quântica executada.",
        "Estudo de complexidade e consequências para sistemas criptográficos baseados em fatoração e logaritmos discretos.",
        "Encontrar r garante fatores em toda tentativa?",
        "Não. r pode ser ímpar ou produzir a^(r/2)≡−1. O procedimento repete escolhas e valida candidatos.",
        references=(TEXTBOOK, "Shor, P. W. Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer. SIAM Journal on Computing, 26, 1484–1509, 1997."),
        demonstration_note="Não há implementação completa de Shor nem rotina de exponenciação modular nesta página. Não se apresenta um circuito ilustrativo como fatoração executada.",
    ),
    LearningConcept(
        "teletransporte", "Teletransporte quântico", "Algoritmos e protocolos",
        "O protocolo transfere um estado de qubit utilizando um par emaranhado compartilhado, uma medição conjunta e dois bits clássicos.",
        "O estado não é clonado. O receptor só recupera a entrada após receber informação clássica e aplicar a correção; não há comunicação instantânea.",
        "Com a convenção de medir primeiro o qubit de entrada a e depois a metade do par b, a correção no receptor é ZᵃXᵇ, até fase global.",
        "O histograma de três qubits em Z, sozinho, não certifica a transferência de fases. A verificação compara o estado do receptor ao estado de entrada.",
        "Prepare |ψ⟩ e um par Bell. Aplique CX da entrada para a metade local do par e H na entrada; meça os dois qubits locais e corrija o terceiro pelos resultados.",
        "Redes quânticas, conexão de módulos e protocolos de computação baseados em emaranhamento.",
        "O receptor consegue conhecer |ψ⟩ antes da mensagem clássica?",
        "Não. Sem condicionar aos resultados, seu estado reduzido é I/2, independente de |ψ⟩.",
        references=(TEXTBOOK, "Bennett, C. H. et al. Teleporting an Unknown Quantum State via Dual Classical and Einstein-Podolsky-Rosen Channels. Physical Review Letters, 70, 1895–1899, 1993."),
        demonstration_note="O editor atual não suporta medições intermediárias nem feedforward clássico. Esta explicação não é apresentada como protocolo completo executável.",
    ),
    LearningConcept(
        "correcao-erros", "Correção de erros quânticos", "Robustez e validação",
        "Correção de erros codifica informação lógica em um subespaço maior para detectar síndromes e recuperar classes específicas de erros.",
        "Mede-se informação sobre o erro sem ler diretamente as amplitudes lógicas. Mitigação e correção são técnicas distintas: ZNE não cria um qubit lógico protegido.",
        "No código de repetição contra bit flip: α|0⟩+β|1⟩ → α|000⟩+β|111⟩. Ele corrige um X isolado, mas não um erro Z arbitrário.",
        "Estados locais podem se tornar mistos durante a codificação. A qualidade deve ser avaliada no estado lógico recuperado e com o modelo de erro explicitado.",
        "O exemplo prepara RY(0,6) no q0, codifica com duas CX, injeta X no q0, decodifica e aplica CCX(q1,q2,q0). O q0 é recuperado por uma implementação unitária educativa da correção.",
        "Memórias lógicas, computação tolerante a falhas e compreensão de síndromes e limiares.",
        "Um código que corrige um bit flip também corrige automaticamente um erro de fase Z?",
        "Não. O código de repetição na base computacional não protege a fase; códigos mais completos combinam verificações apropriadas.",
        references=(TEXTBOOK, "Shor, P. W. Scheme for reducing decoherence in quantum computer memory. Physical Review A, 52, R2493–R2496, 1995."),
        demonstration=_circuit(3, ("ry", (0,), (0.6,)), ("cx", (0, 1)), ("cx", (0, 2)), ("x", (0,)), ("cx", (0, 1)), ("cx", (0, 2)), ("ccx", (1, 2, 0))),
        demonstration_note="Demonstração coerente de um único X no q0, sem medições intermediárias de síndrome, sem tolerância a falhas e sem proteção geral contra decoerência.",
    ),
)

CONCEPT_BY_KEY = {concept.key: concept for concept in CONCEPTS}

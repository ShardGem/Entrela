"""Immutable educational presets. Every use produces a separate configuration."""
from dataclasses import dataclass,replace
from core.types import SystemConfig,SimulationProtocol,NoiseConfig,ExperimentConfig

@dataclass(frozen=True)
class ExampleDefinition:
    id: str
    title: str
    description: str
    objective: str
    expected: str
    level: str
    config: ExperimentConfig

    def create_config(self):
        return replace(self.config,system=replace(self.config.system),
                       protocol=replace(self.config.protocol),noise=replace(self.config.noise))

def preset(qubits=2,ham="Ising",J=1.,h=.5,state="zero",noise=False,kind="Despolarizador",**parameters):
    cfg=ExperimentConfig(SystemConfig(qubits,ham,J,h,False,state),SimulationProtocol(),
                         NoiseConfig(enabled=noise,kind=kind,**parameters),shots=4096,seed=42)
    cfg.validate()
    return cfg

EXAMPLES=(
    ExampleDefinition("first-qubit","Primeiro qubit","Superposição e vetor de Bloch.",
        "Preparar |+⟩ em um qubit.","X=+1; medições 0 e 1 próximas de 50%.","Iniciante",
        preset(1,J=0,h=0,state="plus")),
    ExampleDefinition("bell","Estado de Bell","Uma preparação H + CX em dois qubits.",
        "Criar e observar um par emaranhado.","Somente 00 e 11; pureza global 1 e vetores locais nulos.","Iniciante",
        preset(J=0,h=0,state="bell")),
    ExampleDefinition("spin-oscillation","Oscilação de um spin","Evolução sob um campo transversal.",
        "Observar rotação causada por H=0,5X.","P(1,t)=sin²(0,5t).","Iniciante",preset(1,J=0,h=.5)),
    ExampleDefinition("ising","Modelo de Ising","Interações ZZ e campo transversal X.",
        "Estudar uma cadeia de quatro qubits.","Compare as probabilidades ao longo do tempo.","Intermediário",
        preset(4)),
    ExampleDefinition("heisenberg","Modelo de Heisenberg","Acoplamento XX+YY+ZZ.",
        "Explorar interações isotrópicas.","O estado alinhado inicial é estacionário, salvo fase global.","Intermediário",
        preset(3,"Heisenberg",h=0)),
    ExampleDefinition("xy","Modelo XY","Interações XX+YY.",
        "Comparar a evolução a partir de |+…+⟩.","A evolução reflete as trocas entre spins.","Intermediário",
        preset(3,"XY",h=0,state="plus")),
    ExampleDefinition("xxz","Modelo XXZ","Anisotropia ZZ com coeficiente 0,5J.",
        "Investigar uma cadeia anisotrópica.","Compare com o exemplo XY usando a mesma preparação.","Intermediário",
        preset(3,"XXZ",h=0,state="plus")),
    ExampleDefinition("depolarizing-bell","Bell com despolarização","Compare com a referência ideal de Bell.",
        "Observar o efeito do ruído na preparação.","Podem aparecer 01 e 10; fidelidade e pureza diminuem.","Intermediário",
        preset(J=0,h=0,state="bell",noise=True,p1=.02,p2=.05)),
    ExampleDefinition("thermal-decoherence","Decoerência de um qubit","Relaxamento térmico após preparação de superposição.",
        "Analisar T₁ e T₂ durante operações.","O vetor pode contrair; o canal incide nas portas, não em tempo ocioso.","Intermediário",
        preset(1,J=0,h=.5,state="plus",noise=True,kind="Termico",t1_us=70,t2_us=100)),
    ExampleDefinition("noisy-ising","Ising com ruído","Cadeia ideal e ensemble ruidoso.",
        "Investigar perda de fidelidade em quatro qubits.","A referência é o mesmo circuito Trotter sem ruído.","Avançado",
        preset(4,noise=True)),
    ExampleDefinition("negative-coupling","Acoplamento negativo","A convenção de sinais do Ising.",
        "Explorar J negativo, que favorece alinhamento no termo +JZZ.","Compare energias para J positivo e negativo.","Intermediário",
        preset(3,J=-1,h=.5,state="plus")),
    ExampleDefinition("thermal-ising","Ising com relaxamento térmico","Ruído com T₂ maior que T₁, mas fisicamente válido.",
        "Estudar o limite T₂ ≤ 2T₁.","O exemplo usa T₁=70 µs e T₂=100 µs.","Avançado",
        preset(3,noise=True,kind="Termico",t1_us=70,t2_us=100)),
)

def get_example(identifier):
    for example in EXAMPLES:
        if example.id==identifier:return example
    raise ValueError("Exemplo desconhecido")

def create_example_config(identifier):
    return get_example(identifier).create_config()

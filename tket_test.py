import logging

from pytket import OpType
from pytket.qiskit import qiskit_to_tk, process_characterisation
from pytket.routing import Architecture, route, Placement
from pytket.device import Device
from pytket.passes import RepeatWithMetricPass, SequencePass, DecomposeBoxes, FullPeepholeOptimise, \
    CXMappingPass, CliffordSimp, SynthesiseIBM, DecomposeSwapsToCXs, RemoveRedundancies, CommuteThroughMultis
from pytket.routing import NoiseAwarePlacement, GraphPlacement

from qiskit import QuantumCircuit
from qiskit.test.mock import FakeTokyo, FakeRochester, FakeMelbourne
from qiskit.transpiler import CouplingMap

# Tested with pytket 0.6.1

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

directory = 'benchmarks_qasm/'

qasm_file = 'path to your qasm file'

q_circ = QuantumCircuit.from_qasm_file(qasm_file)

tk_circ = qiskit_to_tk(q_circ)

backend = FakeMelbourne()
coupling_list = backend.configuration().coupling_map
coupling_map = CouplingMap(coupling_list)

characterisation = process_characterisation(backend)
directed_arc = Device(characterisation.get("NodeErrors", {}),
                      characterisation.get("EdgeErrors", {}),
                      characterisation.get("Architecture", Architecture([])), )

comp_tk = tk_circ.copy()

DecomposeBoxes().apply(comp_tk)
FullPeepholeOptimise().apply(comp_tk)
CXMappingPass(directed_arc, NoiseAwarePlacement(directed_arc), directed_cx=True, delay_measures=True).apply(comp_tk)
DecomposeSwapsToCXs(directed_arc).apply(comp_tk)
cost = lambda c: c.n_gates_of_type(OpType.CX)
comp = RepeatWithMetricPass(SequencePass([CommuteThroughMultis(), RemoveRedundancies(), CliffordSimp(False)]), cost)
comp.apply(comp_tk)
SynthesiseIBM().apply(comp_tk)


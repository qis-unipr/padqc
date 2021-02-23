import logging

from qiskit import QuantumCircuit, transpile
from qiskit.test.mock import FakeTokyo, FakeRochester, FakeMelbourne
from qiskit.transpiler import CouplingMap

from padqc import compile
from padqc.converters import qasm_from_circuit, circuit_from_qasm
from padqc.steps import ChainLayout, Patterns, CancelCx, CancelH, MergeBarrier

# Tested with qiskit 0.21.0

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

coupling_list = FakeMelbourne().configuration().coupling_map

coupling_map = CouplingMap(coupling_list)

directory = 'benchmarks_qasm/'

qasm_file = 'path to your qasm file'

q_circ = QuantumCircuit.from_qasm_file(qasm_file)

padqc_circ = circuit_from_qasm(q_circ.qasm())

compile(padqc_circ, steps=[
    ChainLayout(coupling_list, n_qubits=padqc_circ.n_qubits),
    Patterns(),
    CancelH(),
    CancelCx(),
    MergeBarrier()
], iterate=True, explicit=True)

layout = padqc_circ.properties['layout']

padqc_sabre_chain = transpile(QuantumCircuit.from_qasm_str(qasm_from_circuit(padqc_circ)),
                              optimization_level=3, basis_gates=['u3', 'cx'],
                              coupling_map=coupling_map,
                              routing_method='sabre',
                              initial_layout=layout,
                              seed_transpiler=1000
                              )

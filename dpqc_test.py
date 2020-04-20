import logging
import os
import time
from os import path

from qiskit import QuantumCircuit, transpile, IBMQ
from qiskit.converters import circuit_to_dag
from qiskit.extensions.standard import SwapGate
from qiskit.test.mock import FakeTokyo
from qiskit.transpiler import CouplingMap, PassManager, Layout
from qiskit.transpiler.passes import *

from padqc import compile
from padqc.converters import qasm_from_circuit, circuit_from_qasm
from padqc.steps import ChainLayout, Patterns, DeterministicSwap, CancelCx, CancelH, MergeBarrier

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

IBMQ.load_account()


backend = IBMQ.get_provider().get_backend('ibmq_qasm_simulator')

coupling_list = FakeTokyo().configuration().coupling_map

coupling_map = CouplingMap(coupling_list)

directory = 'benchmarks_qasm/'

for file in os.listdir(directory):
    filename = file
    extension = '.'+filename.split('.')[-1]
    if path.exists(('results/tokyo/padqc/' + filename).replace(extension, '.res')):
        continue
    logger.info(filename+'\n')
    with open('log_tokyo_padqc.txt', 'a') as f:
        f.write(filename + '\n')
    
    # compile the circuit
    depth = 0
    n_cx = 0
    n_gates = 0
    running_time = 0
    start = time.time()

    with open(directory+filename, 'r') as f:
        qc = circuit_from_qasm(f.read())

    compile(qc, steps=[ChainLayout(coupling_list, n_qubits=qc.n_qubits),
                       Patterns(),
                       DeterministicSwap(coupling_list),
                       CancelH(),
                       CancelCx(),
                       MergeBarrier()
                       ], iterate=True)

    qc_compiled = QuantumCircuit.from_qasm_str(qasm_from_circuit(qc, optimize=False))
    pass_manager = PassManager()
    pass_manager.append([
        SetLayout(Layout.from_intlist(qc.properties['layout'], *qc_compiled.qregs)),
        FullAncillaAllocation(coupling_map), EnlargeWithAncilla(),
        ApplyLayout()
    ])


    def _direction_condition(property_set):
        return not property_set['is_direction_mapped']


    pass_manager.append([
        BarrierBeforeFinalMeasurements(),
        Unroll3qOrMore(),
        Decompose(SwapGate)
    ])


    def direction_condition(property_set):
        return not property_set['is_direction_mapped']


    if not coupling_map.is_symmetric:
        pass_manager.append(CheckCXDirection(coupling_map))
        pass_manager.append(CXDirection(coupling_map), condition=direction_condition)

    depth_check = [Depth(), FixedPoint('depth')]


    def opt_control(property_set):
        return not property_set['depth_fixed_point']


    basis_gates = ['u1', 'u2', 'u3', 'cx']
    opt = [
        RemoveResetInZeroState(),
        Collect2qBlocks(), ConsolidateBlocks(),
        Unroller(basis_gates),
        Optimize1qGates(), CommutativeCancellation(),
        OptimizeSwapBeforeMeasure(), RemoveDiagonalGatesBeforeMeasure()
    ]

    if coupling_map and not coupling_map.is_symmetric:
        opt.append(CXDirection(coupling_map))
    pass_manager.append(depth_check + opt, do_while=opt_control)

    qc_compiled = transpile(qc_compiled, initial_layout=qc.properties['layout'], backend=backend, coupling_map=coupling_map, pass_manager=pass_manager)
    end = time.time()
    depth = qc_compiled.depth()
    n_cx = len(circuit_to_dag(qc_compiled).twoQ_gates())
    n_gates = len(circuit_to_dag(qc_compiled).gate_nodes())
    running_time = str(round(end-start, 2))

    with open(('results/tokyo/padqc/' + filename).replace(extension, '.res'), 'w') as f:

        f.write('depth = %s\n' % str(depth))
        f.write('n_cx = %s\n' % str(n_cx))
        f.write('n_gates = %s\n' % str(n_gates))
        f.write('running time = %s\n seconds' % running_time)

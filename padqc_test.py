import logging
import os
from os import path

from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.circuit.library.standard_gates import SwapGate
from qiskit.test.mock import FakeTokyo
from qiskit.transpiler import CouplingMap, PassManager, Layout
from qiskit.transpiler.passes import *

from padqc import compile
from padqc.converters import qasm_from_circuit, circuit_from_qasm
from padqc.steps import ChainLayout, Patterns, DeterministicSwap, CancelCx, CancelH, MergeBarrier

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

coupling_list = FakeTokyo().configuration().coupling_map

coupling_map = CouplingMap(coupling_list)

directory = 'benchmarks_qasm/'

for file in os.listdir(directory):
    extension = '.'+file.split('.')[-1]
    if path.exists(('results/tokyo/padqc/' + file).replace(extension, '.res')):
        continue
    logger.info(file+'\n')
    with open('log_tokyo_padqc.txt', 'a') as f:
        f.write(file + '\n')
    
    # compile the circuit
    depth = 0
    n_cx = 0
    n_gates = 0

    with open(directory+file, 'r') as f:
        qc = circuit_from_qasm(f.read())

    compile(qc, steps=[ChainLayout(coupling_list, n_qubits=qc.n_qubits),
                       Patterns(),
                       CancelH(),
                       CancelCx(),
                       DeterministicSwap(coupling_list),
                       MergeBarrier()
                       ], iterate=True, explicit=True)

    patterns = qc.patterns

    qc_compiled = QuantumCircuit.from_qasm_str(qasm_from_circuit(qc, optimize=False))
    pass_manager = PassManager()
    pass_manager.append([
        SetLayout(Layout.from_intlist(qc.properties['layout'], *qc_compiled.qregs)),
        FullAncillaAllocation(coupling_map), EnlargeWithAncilla(),
        ApplyLayout()
    ])

    pass_manager.append([
        BarrierBeforeFinalMeasurements(),
        Unroll3qOrMore(),
        Decompose(SwapGate)
    ])

    depth_check = [Depth(), FixedPoint('depth')]


    def opt_control(property_set):
        return not property_set['depth_fixed_point']


    basis_gates = ['u3', 'cx']
    opt = [
        RemoveResetInZeroState(),
        Collect2qBlocks(), ConsolidateBlocks(),
        Unroller(basis_gates),
        Optimize1qGates(), CommutativeCancellation(),
        OptimizeSwapBeforeMeasure(), RemoveDiagonalGatesBeforeMeasure()
    ]

    pass_manager.append(depth_check + opt, do_while=opt_control)

    qc_compiled = pass_manager.run(qc_compiled)

    depth = qc_compiled.depth()
    n_cx = len(circuit_to_dag(qc_compiled).two_qubit_ops())
    n_gates = len(circuit_to_dag(qc_compiled).gate_nodes())

    with open(('results/tokyo/padqc/' + file).replace(extension, '.res'), 'w') as f:

        f.write('depth = %s\n' % str(depth))
        f.write('n_cx = %s\n' % str(n_cx))
        f.write('n_gates = %s\n' % str(n_gates))
        f.write('patterns = %s\n' % str(patterns))

    with open(('results/tokyo/padqc/circuits/' + file).replace(extension, '.qasm'), 'w') as f:
        f.write(qc_compiled.qasm())

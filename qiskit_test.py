import os
import sys
import time
from os import path

from qiskit import QuantumCircuit, transpile, IBMQ
from qiskit.compiler.transpile import _parse_transpile_args
from qiskit.converters import circuit_to_dag
from qiskit.extensions.standard import SwapGate
from qiskit.test.mock import FakeTokyo
from qiskit.transpiler import CouplingMap, PassManager
from qiskit.transpiler.passes import *
from qiskit.transpiler.preset_passmanagers import level_3_pass_manager

IBMQ.load_account()


backend = IBMQ.get_provider().get_backend('ibmq_qasm_simulator')

coupling_list = FakeTokyo().configuration().coupling_map

coupling_map = CouplingMap(coupling_list)

directory = 'benchmarks_qasm/'

i = None
fixed_file = None

for file in os.listdir(directory):
    if fixed_file is None:
        filename = file
    else:
        filename = fixed_file
    
    extension = '.'+filename.split('.')[-1]
    if sys.argv[1] == 'Basic' and path.exists(('results/tokyo/basic/' + filename).replace(extension, '.res')):
        continue
    if sys.argv[1] == 'Stochastic' and path.exists(('results/tokyo/stochastic/' + filename).replace(extension, '_9.res')):
        continue

    if sys.argv[1] == 'Basic':
        with open('log_tokyo_basic.txt', 'a') as f:
            f.write(filename + '\n')

    if sys.argv[1] == 'Stochastic':
        with open('log_tokyo_stochastic.txt', 'a') as f:
            f.write(filename + '\n')

    with open(directory+filename, 'r') as f:
        qc = QuantumCircuit.from_qasm_str(f.read())

    transpile_config = _parse_transpile_args([qc], backend, None,
                                             coupling_map, None,
                                             None, None, 3,
                                             PassManager(), None, None)[0]

    # compile the circuit
    running_time = '0.0'
    if i is None:
        count = 0
    else:
        count = i
    while count < 10:
        if sys.argv[1] == 'Stochastic' and path.exists(('results/tokyo/stochastic/' + filename).replace(extension, '_%d.res' % count)):
            count += 1
            continue

        pm = level_3_pass_manager(transpile_config)
        if sys.argv[1] == 'Basic':
            swap = [BarrierBeforeFinalMeasurements(), Unroll3qOrMore(), BasicSwap(coupling_map),
                    Decompose(SwapGate)]
            pm.replace(5, swap)
        start = time.time()
        qc_compiled = transpile(qc, backend=backend, coupling_map=coupling_map, pass_manager=pm)
        end = time.time()
        depth = qc_compiled.depth()
        n_cx = len(circuit_to_dag(qc_compiled).twoQ_gates())
        n_gates = len(circuit_to_dag(qc_compiled).gate_nodes())
        running_time = str(round(end - start, 2))

        if sys.argv[1] != 'Stochastic':
            with open(('results/tokyo/basic/' + filename).replace(extension, '.res'), 'w') as f:
                f.write('depth = %s\n' % str(depth))
                f.write('n_cx = %s\n' % str(n_cx))
                f.write('n_gates = %s\n' % str(n_gates))
                f.write('running time = %s\n seconds' % running_time)
            break
        else:
            with open(('results/tokyo/stochastic/' + filename).replace(extension, '_%d.res' % count), 'w') as f:
                f.write('depth = %s\n' % str(depth))
                f.write('n_cx = %s\n' % str(n_cx))
                f.write('n_gates = %s\n' % str(n_gates))
                f.write('running time = %s\n seconds' % running_time)
            count = count + 1

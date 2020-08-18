import os
import sys
from os import path

from qiskit import QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag
from qiskit.test.mock import FakeTokyo, FakeAlmaden

directory = 'benchmarks_qasm/'

if sys.argv[2] == 'tokyo':
    backend = FakeTokyo()
elif sys.argv[2] == 'almaden':
    backend = FakeAlmaden()
else:
    backend = FakeAlmaden()

i = None
fixed_file = None

for file in os.listdir(directory):
    if 'RYRZ' not in file and 'UCCSD' not in file:
        continue
    if fixed_file is None:
        filename = file
    else:
        filename = fixed_file

    extension = '.' + filename.split('.')[-1]
    if sys.argv[1] == 'Basic' and path.exists(('results/tokyo/basic/' + filename).replace(extension, '.res')):
        continue
    if sys.argv[1] == 'Stochastic' and path.exists(
            ('results/tokyo/stochastic/' + filename).replace(extension, '_9.res')):
        continue

    if sys.argv[1] == 'Basic':
        with open('log_tokyo_basic.txt', 'a') as f:
            f.write(filename + '\n')

    if sys.argv[1] == 'Stochastic':
        with open('log_tokyo_stochastic.txt', 'a') as f:
            f.write(filename + '\n')

    with open(directory + filename, 'r') as f:
        qc = QuantumCircuit.from_qasm_str(f.read())

    # compile the circuit
    if i is None:
        count = 0
    else:
        count = i
    while count < 10:
        if sys.argv[1] == 'Basic':
            qc_compiled = transpile(qc, optimization_level=3, routing_method='basic', backend=backend)
        elif sys.argv[1] == 'Stochastic' and not path.exists(
                ('results/tokyo/stochastic/' + filename).replace(extension, '_%d.res' % count)):
            qc_compiled = transpile(qc, optimization_level=3, routing_method='stochastic', backend=backend)
        else:
            count = count + 1
            continue
        depth = qc_compiled.depth()
        n_cx = len(circuit_to_dag(qc_compiled).two_qubit_ops())
        n_gates = len(circuit_to_dag(qc_compiled).gate_nodes())

        if sys.argv[1] != 'Stochastic':
            with open(('results/tokyo/basic/' + filename).replace(extension, '.res'), 'w') as f:
                f.write('depth = %s\n' % str(depth))
                f.write('n_cx = %s\n' % str(n_cx))
                f.write('n_gates = %s\n' % str(n_gates))
            break
        else:
            with open(('results/tokyo/stochastic/' + filename).replace(extension, '_%d.res' % count), 'w') as f:
                f.write('depth = %s\n' % str(depth))
                f.write('n_cx = %s\n' % str(n_cx))
                f.write('n_gates = %s\n' % str(n_gates))
            count = count + 1

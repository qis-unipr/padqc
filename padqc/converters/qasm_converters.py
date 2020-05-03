from networkx import topological_sort
from sympy import pi
from sympy.parsing.sympy_parser import parse_expr

from qiskit import QuantumCircuit, Aer
from qiskit.compiler.transpile import transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import Unroller, Optimize1qGates

from padqc.converters import QasmError
from padqc.gates import Cx
from padqc.gates.single_q_gates import Id, Pauli_X, Pauli_Y, Pauli_Z, Rx, Ry, Rz, Hadamard, Measure
from padqc.gates.base_gates import Barrier, DummyGate
from padqc.q_circuit import QCircuit
from padqc.steps import Decompose
from padqc.compiler import compile


def circuit_from_qasm(qasm):
    """Creates a QCircuit from a QASM circuit, uses Qiskit transpiler
    to unroll the QASM circuit into basic U gates.

    Args:
        qasm (str): a QASM circuit

    Returns:
        QCircuit: the QCircuit equivalent of the provided QASM circuit
    """

    pm = PassManager()
    pm.append(Unroller(['u3', 'cx']))
    qasm = transpile(QuantumCircuit.from_qasm_str(qasm), pass_manager=pm).qasm()
    q_circuit = QCircuit()
    lines = list(qasm.split(';\n'))
    for line in lines:
        if line.startswith('qreg'):
            q_circuit.add_q_register(line.split(' ')[-1].split('[')[0], int(line.split('[')[1][:-1]))
        elif line.startswith('creg'):
            q_circuit.add_c_register(line.split(' ')[-1].split('[')[0], int(line.split('[')[1][:-1]))
        else:
            if line.startswith('u3'):
                q_reg = _q_reg_1q_qasm_gate(line)
                q_arg = (q_circuit.q_regs[q_reg[0]][0], q_reg[1])
                params = _qasm_gate_params(line)
                # print(line)
                if params[0] == pi.evalf(5)/2 and params[1] == 0 and params[2] == pi.evalf(5):
                    # print('H')
                    q_circuit.h(q_arg)
                else:
                    q_circuit.dummy_gate(name='u3', q_args=[q_arg], params=params)
            elif line.startswith('cx'):
                q_regs = _q_regs_2q_qasm_gate(line)
                q_circuit.cx((q_circuit.q_regs[q_regs[0][0]][0], q_regs[0][1]),
                             (q_circuit.q_regs[q_regs[1][0]][0], q_regs[1][1]))
            elif line.startswith('measure'):
                q_reg = line.split(' ')[1]
                c_reg = line.split(' ')[3]
                q_circuit.measure((q_circuit.q_regs[q_reg.split('[')[0]][0], int(q_reg.split('[')[-1][:-1])),
                                  (q_circuit.c_regs[c_reg.split('[')[0]][0], int(c_reg.split('[')[-1][:-1])))
            elif line.startswith('barrier'):
                q_args = list()
                for q_arg in line.split(' ')[-1].split(','):
                    q_args.append((q_circuit.q_regs[q_arg.split('[')[0]][0], int(q_arg.split('[')[-1][:-1])))
                q_circuit.barrier(*q_args)
    return q_circuit


def qasm_from_circuit(q_circuit, **kwargs):
    """Creates a QASM from a QCircuit.

    Args:
        q_circuit (QCircuit): a QCircuit

    Returns:
        str: the QASM equivalent of the provided QCircuit
    """

    q_regs_id = {q_circuit.q_regs[reg][0]: (reg, q_circuit.q_regs[reg][1]) for reg in q_circuit.q_regs}
    c_regs_id = {q_circuit.c_regs[reg][0]: (reg, q_circuit.c_regs[reg][1]) for reg in q_circuit.c_regs}

    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\n'

    if len(q_regs_id) != 0:
        for q_reg_id in q_regs_id:
            qasm += 'qreg ' + q_regs_id[q_reg_id][0] + '[' + str(q_regs_id[q_reg_id][1]) + '];\n'
    else:
        raise QasmError("Quantum circuit must have at least one quantum register")
    if len(c_regs_id) != 0:
        for c_reg_id in c_regs_id:
            qasm += 'creg ' + c_regs_id[c_reg_id][0] + '[' + str(c_regs_id[c_reg_id][1]) + '];\n'

    compile(q_circuit=q_circuit, steps=[Decompose()])

    for node in topological_sort(q_circuit.q_graph.graph):
        if isinstance(node.gate, Id):
            q_arg = node.gate.q_args[0]
            qasm += 'id ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '];\n'
        elif isinstance(node.gate, Pauli_X):
            q_arg = node.gate.q_args[0]
            qasm += 'x ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '];\n'
        elif isinstance(node.gate, Pauli_Y):
            q_arg = node.gate.q_args[0]
            qasm += 'y ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '];\n'
        elif isinstance(node.gate, Pauli_Z):
            q_arg = node.gate.q_args[0]
            qasm += 'z ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '];\n'
        elif isinstance(node.gate, Rx):
            q_arg = node.gate.q_args[0]
            qasm += 'rx(' + str(node.gate.theta) + ') ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) \
                    + '];\n'
        elif isinstance(node.gate, Ry):
            q_arg = node.gate.q_args[0]
            qasm += 'ry(' + str(node.gate.theta) + ') ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) \
                    + '];\n'
        elif isinstance(node.gate, Rz):
            q_arg = node.gate.q_args[0]
            qasm += 'rz(' + str(node.gate.theta) + ') ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) \
                    + '];\n'
        elif isinstance(node.gate, Hadamard):
            q_arg = node.gate.q_args[0]
            qasm += 'h ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '];\n'
        elif isinstance(node.gate, Measure):
            q_arg = node.gate.q_args[0]
            c_arg = node.gate.c_arg
            qasm += 'measure ' + q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '] -> ' \
                    + c_regs_id[c_arg[0]][0] + '[' + str(c_arg[1]) + '];\n'
        elif isinstance(node.gate, Barrier):
            qasm += 'barrier '
            temp = ''
            for q_arg in node.gate.q_args:
                temp += q_regs_id[q_arg[0]][0] + '[' + str(q_arg[1]) + '],'
            temp = temp[:-1]
            qasm += temp + ';\n'
        elif isinstance(node.gate, Cx):
            control = node.gate.control
            target = node.gate.target
            qasm += 'cx ' + q_regs_id[control[0]][0] + '[' + str(control[1]) + '],' \
                    + q_regs_id[target[0]][0] + '[' + str(target[1]) + '];\n'
        elif isinstance(node.gate, DummyGate):
            q_arg = ''
            params = ''
            if len(node.gate.q_args) > 0:
                if len(node.gate.q_args) > 1:
                    q_args = [(q_regs_id[q_arg[0]][0], q_arg[1]) for q_arg in node.gate.q_args]
                    for q in q_args[:-1]:
                        q_arg += q[0] + '[' + str(q[1]) + '],'
                    q_arg += q_args[-1][0] + '[' + str(q_args[-1][1]) + ']'
                else:
                    q_arg += q_regs_id[node.gate.q_args[0][0]][0] + '[' + str(node.gate.q_args[0][1]) + ']'
            if len(node.gate.params) != 0:
                params += '('
                for param in node.gate.params[:-1]:
                    params += str(param) + ','
                params += str(node.gate.params[-1]) + ')'
            qasm += node.gate.name + params + ' '
            qasm += q_arg + ';\n'
    pm = PassManager()
    pm.append(Unroller(['u3', 'cx']))
    if 'optimize' in kwargs and kwargs['optimize'] is True:
        pm.append(Optimize1qGates())
    qasm = transpile(QuantumCircuit.from_qasm_str(qasm), pass_manager=pm).qasm()
    return qasm


def _q_reg_1q_qasm_gate(qasm_gate):
    """Obtains a tuple *(q_reg, q_arg)* from a one qubit gate QASM string,
        where *q_reg* is a quantum register name and *q_arg* is the quantum register index.

    Args:
        qasm_gate (str): a one qubit gate QASM string

    Returns:
        tuple: a tuple (q_reg, q_arg)
    """

    q_reg = qasm_gate.split(' ')[-1]
    return q_reg.split('[')[0], int(q_reg.split('[')[-1][:-1])


def _q_regs_2q_qasm_gate(qasm_gate):
    """Obtains a a list of tuples *[(q_reg, q_arg), (q_reg, q_arg)]* from a two qubit gate QASM string,
            where *q_reg* is a quantum register name and *q_arg* is the quantum register index.

        Args:
            qasm_gate (str): a two qubit gate QASM string

        Returns:
            list: a list of tuple of [(q_reg, q_arg), (q_reg, q_arg)]
        """

    q_regs = qasm_gate.split(' ')[-1].split(',')
    return [(q_regs[0].split('[')[0], int(q_regs[0].split('[')[-1][:-1])), (q_regs[1].split('[')[0], int(q_regs[1].split('[')[-1][:-1]))]


def _qasm_gate_params(qasm_gate):
    """Obtains a list of parameters [param1, param2, ...] as floats (or SymPy expressions)
    from a parametric one qubit gate QASM string.

    Args:
        qasm_gate (str): a one qubit gate QASM string

    Returns:
        list: a list of parameters [param1, param2, ...] as floats (or SymPy expressions)
    """

    params = list()
    # print(qasm_gate)
    for param in qasm_gate.split(' ')[0].split('(')[-1][:-1].split(','):
        if 'pi' in param:
            params.append(float(parse_expr(param)))
        else:
            params.append(float(param))
    # print(params)
    return params

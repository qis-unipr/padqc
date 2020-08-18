from .exceptions import QCircuitError
from padqc.q_graph import Graph
from ..gates import DummyGate


class QCircuit:
    """
    The quantum circuit class.
    """
    def __init__(self):
        self.q_graph = Graph()
        self.n_qubits = 0
        self.q_regs = dict()
        self.c_regs = dict()
        self._regs_to_phys_q = dict()
        self._layout = dict()
        self._properties = dict()
        self._properties['layout'] = list()
        self._properties['regs_to_physical'] = self._regs_to_phys_q
        self._properties['q_regs'] = self.q_regs
        self._properties['c_regs'] = self.c_regs
        self.patterns = 0

    @property
    def properties(self):
        return self._properties

    @property
    def q_regs_list(self):
        return [(q_reg[0], q) for q_reg in self.q_regs.values() for q in range(q_reg[1])]

    @property
    def c_regs_list(self):
        return [(c_reg[0], c) for c_reg in self.c_regs.values() for c in range(c_reg[1])]

    @property
    def layout(self):
        """
        Returns:
            dict: a dictionary {(q_reg_name, q_reg_index): physical_qubit, ...}
                representing the mapping of logical qubits to physical qubits
        """
        return self._regs_to_phys_q

    @layout.setter
    def layout(self, layout):
        self._regs_to_phys_q = layout
        self._properties['layout'] = [x[1] for x in layout.items()]

    def add_q_register(self, name, reg_dim):
        """Adds a quantum register to the circuit.

        Args:
            name (str): name of the quantum register
            reg_dim (int): dimension of the quantum register

        Returns:
            list: a list [(q_reg_id, q_reg_index), ...] of all logical qubits in the register
        """
        q_reg = self.q_graph._add_q_register(name, reg_dim)
        self.q_regs[name] = (q_reg[0][0], len(q_reg))
        for i in range(reg_dim):
            self._regs_to_phys_q[(q_reg[0][0], i)] = len(self._regs_to_phys_q)
            self._layout[(q_reg[0][0], i)] = (q_reg[0][0], i)
        self.n_qubits += reg_dim
        return q_reg

    def add_c_register(self, name, reg_dim):
        """Adds a classical register to the circuit.

        Args:
            name (str): name of the classical register
            reg_dim (int): dimension of the classical register

        Returns:
            list: a list [(c_reg_id, c_reg_index), ...] of all bits in the register
        """
        c_reg = self.q_graph._add_c_register(name, reg_dim)
        self.c_regs[name] = (c_reg[0][0], len(c_reg))
        return c_reg

    def depth(self):
        """
        Returns:
            int: the depth of the circuit
        """
        return self.q_graph.depth()

    def id(self, q):
        """Applies an Identity gate to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self.q_graph.id(self._layout[q])

    def x(self, q):
        """Applies a Pauli X gate to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self.q_graph.x(self._layout[q])

    def y(self, q):
        """Applies a Pauli Y gate to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self.q_graph.y(self._layout[q])

    def z(self, q):
        """Applies a Pauli Z gate to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self.q_graph.z(self._layout[q])

    def rx(self, q, theta):
        """Applies a rotation of an angle *theta* around the *x* axis to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        self.q_graph.rx(self._layout[q], theta)

    def ry(self, q, theta):
        """Applies a rotation of an angle *theta* around the *y* axis to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        self.q_graph.ry(self._layout[q], theta)

    def rz(self, q, theta):
        """Applies a rotation of an angle *theta* around the *z* axis to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        self.q_graph.rz(self._layout[q], theta)

    def h(self, q):
        """Applies an Hadamard gate to logical qubit *q*.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self.q_graph.h(self._layout[q])

    def cx(self, control, target):
        """Applies a CNOT gate between *control* and *target* logical qubits.

        Args:
            control (tuple): the control logical qubit
            target (tuple): the target logical qubit
        """
        self.q_graph.cx(self._layout[control], self._layout[target])

    def barrier(self, *q_args):
        """Applies a barrier an all logical qubits in *q_args*.

        Args:
            *q_args (): arbitrary sequence of logical qubits
        """
        self.q_graph.barrier([self._layout[q_arg] for q_arg in q_args])

    def measure(self, q_arg, c_arg):
        """Applies a measurement gate between *q_arg* and *c_arg*.

        Args:
            q_arg (tuple or list): a logical qubit (q_reg_id, q_reg_index) or a list of logical qubits
            c_arg (tuple or list): a classical bit (c_reg_id, c_reg_index) or a list of claasical bits
        """
        if isinstance(q_arg, list):
            if isinstance(c_arg, list):
                for q_arg, c_arg in zip(q_arg, c_arg):
                    self.q_graph.measure(self._layout[q_arg], c_arg)
            else:
                raise QCircuitError('Quantum register size (%d) different from classical register size (%d).'
                                    % (len(q_arg), len(c_arg)))
        else:
            if isinstance(c_arg, list):
                raise QCircuitError('Quantum register size (%d) different from classical register size (%d).'
                                    % (len(q_arg), len(c_arg)))
            self.q_graph.measure(self._layout[q_arg], c_arg)

    def composite_gate(self, composite_gate, **kwargs):
        """Applies a composite gate to the circuit.

        Args:
            composite_gate (CompositeGate): a composite gate
            **kwargs (): arbitrary sequence of keyword arguments identifying logical qubits,
            bits and gate parameters.
        """

        c_args = composite_gate.c_args
        q_args = composite_gate.q_args
        params = composite_gate.params
        decomposition = composite_gate.decomposition
        for key, value in kwargs.items():
            decomposition[key] = value
        final_composite_gate = composite_gate.copy
        final_composite_gate.decomposition = decomposition
        final_composite_gate.q_args = [self._layout[kwargs[q_arg]] for q_arg in q_args]
        final_composite_gate.c_args = [kwargs[c_arg] for c_arg in c_args]
        final_composite_gate.params = [kwargs[param] for param in params]
        self.q_graph._append_node(type='gate', op=final_composite_gate)

    def dummy_gate(self, name='dummy_gate', q_args=None, params=None):
        if params is None:
            params = []
        if q_args is None:
            q_args = []
        self.q_graph.dummy_gate(DummyGate(name=name, q_args=[self._layout[q_arg] for q_arg in q_args], params=params))

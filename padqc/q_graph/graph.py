import networkx as nx

from padqc.gates.single_q_gates import Hadamard, Id, Rx, Pauli_X, Pauli_Y, Pauli_Z, Ry, Rz, Measure
from padqc.gates.two_q_gates import Cx
from padqc.gates.base_gates import Input, Output, Classic, Barrier
from padqc.q_graph import Node
from .exceptions import GraphError


class Graph:
    """
    The Graph class.
    """
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.n_qubits = 0
        self._in_qubit = dict()
        self._out_qubit = dict()
        self._out_classic = dict()
        self.q_registers = dict()
        self.c_registers = dict()
        self._node_counter = 0

    def _q_reg_id_to_name(self, reg_id):
        """Gets quantum register name form its id.

        Args:
            reg_id (int): quantum register id

        Returns:
            str: quantum register name
        """
        for reg in self.q_registers:
            if self.q_registers[reg]['id'] == reg_id:
                return reg
        raise GraphError("Quantum register with id %d not found" % reg_id)

    def _q_reg_name_to_id(self, reg_name):
        """Gets quantum register id form its name.

        Args:
            reg_name (str): quantum register name

        Returns:
            int: quantum register id
        """
        if reg_name in self.q_registers:
            return self.q_registers[reg_name]['id']
        raise GraphError("Quantum register with name %d not found" % reg_name)

    def _c_reg_id_to_name(self, reg_id):
        """Gets classical register name form its id.

        Args:
            reg_id (int): classical register id

        Returns:
            str: classical register name
        """
        for reg in self.c_registers:
            if self.c_registers[reg]['id'] == reg_id:
                return reg
        raise GraphError("Classical register with id %d not found" % reg_id)

    def _c_reg_name_to_id(self, reg_name):
        """Gets classical register id form its name.

        Args:
            reg_name (str): classical register name

        Returns:
            int: classical register id
        """
        if reg_name in self.c_registers:
            return self.c_registers[reg_name]['id']
        raise GraphError("Classical register with name %d not found" % reg_name)

    def _add_q_register(self, register_name, reg_dim):
        """Adds input and output nodes for every qubit in a quantum register.

        Args:
            register_name (str): the register name
            reg_dim (int): the register dimension

        Returns:
            list: list of tuples (reg_id, reg_index)
        """
        if register_name in self.q_registers:
            raise GraphError("Register %s already exists" % register_name)
        self.q_registers[register_name] = {'id': len(self.q_registers), 'dim': reg_dim}
        for reg in range(reg_dim):
            input = self._add_node(Node(type='input',
                                        gate=Input(name='%s[%d]' % (register_name, reg),
                                                   q_arg=(self.q_registers[register_name]['id'], reg))))
            self._in_qubit[(self.q_registers[register_name]['id'], reg)] = input
            output = self._add_node(Node(type='output',
                                         gate=Output(name='%s[%d]' % (register_name, reg),
                                                     q_arg=(self.q_registers[register_name]['id'], reg))))
            self._out_qubit[(self.q_registers[register_name]['id'], reg)] = output
            self.graph.add_edge(input, output, name='%s[%d]' % (register_name, reg))
        self.n_qubits += reg_dim
        return [(self.q_registers[register_name]['id'], i) for i in range(reg_dim)]

    def _add_c_register(self, register_name, reg_dim):
        """Adds output nodes for every bit in a classical register.

        Args:
            register_name (str): the register name
            reg_dim (int): the register dimension

        Returns:
            list: list of tuples (reg_id, reg_index)
        """
        if register_name in self.c_registers:
            raise GraphError("Classical register_name %s already exists" % register_name)
        self.c_registers[register_name] = {'id': len(self.c_registers), 'dim': reg_dim}
        for reg in range(reg_dim):
            self._out_classic[(self.c_registers[register_name]['id'], reg)] = \
                Node(type='classic_output', gate=Classic(name='%s[%d]' % (register_name, reg),
                                                         c_arg=(self.c_registers[register_name]['id'], reg)))
            self.graph.add_node(self._out_classic[(self.c_registers[register_name]['id'], reg)])
        return [(self.c_registers[register_name]['id'], i) for i in range(reg_dim)]

    def _add_node(self, q_node):
        """Adds node to the graph.

        Args:
            q_node (q_graph.Node): node to be added

        Returns:
            q_graph.Node: the node added
        """
        q_node._node_id = self._node_counter
        self._node_counter += 1
        self.graph.add_node(q_node)
        return q_node

    def _append_node(self, type, op):
        """Append node to the ned of the graph, before output node.

        Args:
            type (str): node type
            op (gates.Gate): node gate
        """
        if isinstance(op, Measure):
            if self._c_reg_id_to_name(op.c_arg[0]) not in self.c_registers:
                raise GraphError("Classical register %s[%d] not found"
                                 % (self._c_reg_id_to_name(op.c_arg[0]), op.c_arg[1]))
            self.measure(op.q_args[0], op.c_arg)
        else:
            q_node = self._add_node(Node(type, op))
            for q in q_node.q_args:
                if self._q_reg_id_to_name(q[0]) not in self.q_registers:
                    self.graph.remove_node(q_node)
                    raise GraphError("Quantum register %s[%d] not found"
                                     % (self._c_reg_id_to_name(q[0]), q[1]))
                if self.graph.out_degree(self._out_qubit[q]) != 0:
                    self.graph.remove_node(q_node)
                    raise GraphError(
                        "Quantum register %s[%d] already measured" % (self._q_reg_id_to_name(q[0]), q[1]))
                n = self._out_qubit[q]
                pred = list(self.graph.predecessors(n))
                for p in pred:
                    self.graph.add_edge(p, q_node, name=self.graph.adj[p][n][0]['name'])
                self.graph.remove_edges_from([(p, n) for p in pred])
                self.graph.add_edge(q_node, n, name=n.name)

    def id(self, q):
        """Adds an Identity gate on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self._append_node(type='gate', op=Id(q))

    def x(self, q):
        """Adds a Pauli X gate on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self._append_node(type='gate', op=Pauli_X(q))

    def y(self, q):
        """Adds a Pauli Y gate on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self._append_node(type='gate', op=Pauli_Y(q))

    def z(self, q):
        """Adds a Pauli Z gate on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self._append_node(type='gate', op=Pauli_Z(q))

    def rx(self, q, theta):
        """Adds a rotation gate of an angle *theta* around the *x* axis on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        self._append_node(type='gate', op=Rx(q, theta))

    def ry(self, q, theta):
        """Adds a rotation gate of an angle *theta* around the *y* axis on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        self._append_node(type='gate', op=Ry(q, theta))

    def rz(self, q, theta):
        """Adds a rotation gate of an angle *theta* around the *z* axis on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        self._append_node(type='gate', op=Rz(q, theta))

    def h(self, q):
        """Adds a Hadamard gate on logical qubit *q* to the graph.

        Args:
            q (tuple): the logical qubit (q_reg_id, q_reg_index)
        """
        self._append_node(type='gate', op=Hadamard(q))

    def cx(self, c, t):
        """Adds a CNOT gate between *control* and *target* logical qubits to the graph.

        Args:
            c (tuple): the control logical qubit (q_reg_id, q_reg_index)
            t (tuple): the target logical qubit (q_reg_id, q_reg_index)
        """
        self._append_node(type='gate', op=Cx(c, t))

    def barrier(self, *q_args):
        """Adds a barrier an all logical qubits in *q_args* to the graph.

        Args:
            *q_args (): arbitrary sequence of logical qubits
        """
        self._append_node(type='barrier', op=Barrier(*q_args))

    def measure(self, q_arg, c_arg):
        """Adds a measurement gate between logical qubit *q_arg* output node
        and classical bit *c_arg* output node.

        Args:
            q_arg (tuple): a logical qubit (q_reg_id, q_reg_index)
            c_arg (tuple): a classical qubit (c_reg_id, c_reg_index)
        """
        if self.graph.out_degree(self._out_qubit[q_arg]) != 0:
            raise GraphError("Quantum register %s[%d] already measured" % (self._q_reg_id_to_name(q_arg[0]), q_arg[1]))
        if self.graph.in_degree(self._out_classic[c_arg]) != 0:
            raise GraphError("Classical register %s[%d] already used" % (self._c_reg_id_to_name(c_arg[0]), c_arg[1]))
        node = self._add_node(Node(type='gate', gate=Measure(q_arg, c_arg)))
        self.graph.add_edge(self._out_qubit[q_arg], node, name='%s[%d]' % (self._q_reg_id_to_name(q_arg[0]), q_arg[1]))
        self.graph.add_edge(node, self._out_classic[c_arg],
                            name='%s[%d] -> %s[%d]' % (self._q_reg_id_to_name(q_arg[0]), q_arg[1],
                                                       self._c_reg_id_to_name(c_arg[0]), c_arg[1]))

    def dummy_gate(self, gate):
        self._append_node(type='gate', op=gate)


    def _substitute_node(self, node, q_graph):
        """Substitutes *node* with *q_graph*

        Args:
            node (q_graph.Node): the node to be substituted
            q_graph (q_graph.Graph): the graph that will substitute the node
        """
        self.graph = nx.union(self.graph, q_graph.graph)
        predecessors = self.graph.predecessors(node)
        successors = self.graph.successors(node)
        for pred in predecessors:
            for q_arg in pred.q_args:
                if q_arg in node.gate.q_args:
                    self.graph.add_edge(pred, list(q_graph.graph.successors(q_graph._in_qubit[q_arg]))[0],
                                        name='%s[%d]' % (self._q_reg_id_to_name(q_arg[0]), q_arg[1]))
        for succ in successors:
            for q_arg in succ.q_args:
                if q_arg in node.gate.q_args:
                    self.graph.add_edge(list(q_graph.graph.predecessors(q_graph._out_qubit[q_arg]))[0], succ,
                                        name='%s[%d]' % (self._q_reg_id_to_name(q_arg[0]), q_arg[1]))
        for register in q_graph._in_qubit:
            self.graph.remove_node(q_graph._in_qubit[register])
            self.graph.remove_node(q_graph._out_qubit[register])
        self.graph.remove_node(node)

    def depth(self):
        depth = nx.dag_longest_path_length(self.graph) - 1
        return depth if depth != -1 else 0

    def layers(self):
        graph_layers = self.multigraph_layers()

        for graph_layer in graph_layers:
            op_nodes = [node for node in graph_layer if node.type != "input" and node.type != 'output']
            op_nodes = sorted(op_nodes, key=lambda nd: nd._node_id)

            new_layer = list()
            for node in op_nodes:
                new_layer.append(node)

            yield new_layer

    def multigraph_layers(self):
        predecessor_count = dict()
        cur_layer = [node for node in self._in_qubit.values()]
        next_layer = []
        while cur_layer:
            for node in cur_layer:
                for successor in self.graph.successors(node):
                    multiplicity = self.graph.number_of_edges(node, successor)
                    if successor in predecessor_count:
                        predecessor_count[successor] -= multiplicity
                    else:
                        predecessor_count[successor] = \
                            self.graph.in_degree(successor) - multiplicity
                    if predecessor_count[successor] == 0:
                        next_layer.append(successor)
                        del predecessor_count[successor]

            yield next_layer
            cur_layer = next_layer
            next_layer = []

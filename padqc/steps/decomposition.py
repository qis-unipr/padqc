from networkx import topological_sort

from padqc.gates.base_gates import CompositeGate
from padqc.q_graph import Graph
from padqc.steps import CompilingStep


class Decompose(CompilingStep):
    """
    Compiling step to decompose composite gates.
    """
    def __init__(self):
        super().__init__()
        pass

    def run(self, q_circuit):
        """Executes decomposition step.

        Args:
            q_circuit (q_circuit.QCircuit): the circuit on which to run the step
        """
        composite_nodes = [node for node in topological_sort(q_circuit.q_graph.graph)
                           if isinstance(node.gate, CompositeGate)]
        for node in composite_nodes:
            gate = node.gate
            decomposed_graph = Graph()
            decomposed_graph._node_counter = q_circuit.q_graph._node_counter
            for q_reg in q_circuit.q_regs:
                decomposed_graph._add_q_register(q_reg, q_circuit.q_regs[q_reg][1])
            for c_reg in q_circuit.c_regs:
                decomposed_graph._add_c_register(c_reg, q_circuit.c_regs[c_reg][1])
            for g in gate.gates:
                self._decomposed_graph(decomposed_graph, g, gate.decomposition)
            q_circuit.q_graph._node_counter = decomposed_graph._node_counter
            q_circuit.q_graph._substitute_node(node, decomposed_graph)

    def _decomposed_graph(self, decomposed_graph, gate, decomposition):
        """Recursively decompose a composite gate and adds its gates nodes to the decomposed graph.

        Args:
            decomposed_graph (q_graph.Graph):
            gate (tuple): tuple of gate parameters: (gate_name, q_args, c_args, params)
            decomposition (dict): the gate decomposition
        """
        if isinstance(gate[0], CompositeGate):
            for gate in gate[0].gates:
                self._decomposed_graph(decomposed_graph, gate, decomposition)
        else:
            op = decomposed_graph.__getattribute__(gate[0])
            if gate[0] == 'barrier':
                op([decomposition[q_arg] for q_arg in gate[1]])
            elif gate[0] == 'measure':
                op(decomposition[gate[1][0]], decomposition[gate[2][0]])
            elif gate[0] == 'cx':
                op(decomposition[gate[1][0]], decomposition[gate[1][1]])
            else:
                # rx, ry, rz
                if gate[3] is not None:
                    op(decomposition[gate[1][0]], decomposition[gate[3][0]])
                # x, y, z, id, h
                else:
                    op(decomposition[gate[1][0]])

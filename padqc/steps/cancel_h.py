import numpy as np

from networkx import topological_sort

from padqc.steps import CancellationStep


class CancelH(CancellationStep):
    """
    Cancellation step to cancel double Hadamard gate.
    """
    def __init__(self):
        super().__init__()
        pass

    @staticmethod
    def run(q_circuit):
        """Executes cancellation step.

        Args:
            q_circuit (q_circuit.QCircuit): the circuit on which to run the step

        Returns:
            bool: True if a cancellation was possible, False otherwise
        """
        q_graph = q_circuit.q_graph
        cancelled = False
        nodes = [op for op in topological_sort(q_graph.graph) if is_h(op)]
        removed = []
        for n in nodes:
            if n not in removed and is_h(n):
                succ = list(q_graph.graph.successors(n))
                if len(succ) >= 1:
                    d = succ[0]
                    if is_h(d) and d.q_args == n.q_args:
                        succ_edges = {e[2]['name']: e[1] for e in q_graph.graph.out_edges(d, data=True)}
                        pred_edges = {e[2]['name']: e[0] for e in q_graph.graph.in_edges(n, data=True)}
                        for q in pred_edges.keys():
                            q_graph.graph.add_edge(pred_edges[q], succ_edges[q], name=q)
                        q_graph.graph.remove_node(n)
                        q_graph.graph.remove_node(d)
                        removed.extend([d, n])
                        cancelled = True
        return cancelled


def is_h(gate):
    value = gate.name == 'h' or (gate.name == 'u3' and np.isclose(np.pi/2, gate.params[0]) and np.isclose(np.pi, gate.params[2]) and gate.params[1] == 0.0)
    return value

from networkx import topological_sort

from .base_steps import CancellationStep


class MergeBarrier(CancellationStep):
    """
        Cancellation step to merge double barriers.
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
        nodes = [op for op in topological_sort(q_graph.graph) if op.name == 'barrier']
        removed = []
        for n in nodes:
            if n not in removed:
                succ = list(q_graph.graph.successors(n))
                if len(succ) == 1 and succ[0].name == 'barrier' and succ[0].q_args == n.q_args:
                    d = succ[0]
                    succ_edges = {e[2]['name']: e[1] for e in q_graph.graph.out_edges(d, data=True)}
                    for q in succ_edges.keys():
                        q_graph.graph.add_edge(n, succ_edges[q], name=q)
                    q_graph.graph.remove_node(d)
                    removed.append(d)
                    cancelled = True
        return cancelled
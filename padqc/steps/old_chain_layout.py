import logging

from padqc.steps.base_steps import AnalysisStep

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


class ChainLayout(AnalysisStep):
    """
    Maps the qubits in a coupling map to a nearest-neighbor sequence of qubits, denoted as a *chain*.
    """

    def __init__(self, coupling_map, inverse=False):
        super().__init__()
        self._inverse = inverse
        self._coupling_map = coupling_map
        self._undirected_map = dict()
        self._chain = list()

    def run(self):
        """Executes the step.
        """
        self._undirected_map = self.undirected_map()
        logger.debug('Undirected map: ' + str(self._undirected_map))
        self._chain = self.find_chain()
        logger.info('Chain: ' + str(self._chain))
        if self._inverse is True:
            self._chain = self._chain[::-1]
        self._properties['layout'] = self._chain

    def find_chain(self, connected=None, n_qubits=None):
        """Finds a sequence of physical qubits such that qubit i has a connection
        with qubits (i-1) and (i+1) in undirected_map

        Args:
            connected (list): list of physical qubits already added to the sequence
            n_qubits (int): limits the number qubits to connect to at least n_qubits,
            defaults to len(undirected_map)

        Returns:
            list: list of physical qubits
        """
        n = len(self._undirected_map)
        if n_qubits is None:
            n_qubits = n
        if connected is None:
            connected = [0]
            return self.find_chain(n_qubits=n_qubits, connected=connected)
        neighbors = set(self._undirected_map[connected[-1]]).difference(connected)
        if connected[-1] == 0 and n - 1 in neighbors:
            neighbors.remove(n - 1)
        if connected[-1] - 1 not in self._undirected_map[connected[-1]]:
            next = min(neighbors)
        elif connected[-1] - 1 in neighbors:
            next = connected[-1] - 1
        elif connected[-1] + 1 not in self._undirected_map[connected[-1]]:
            next = max(neighbors)
        elif connected[-1] + 1 in neighbors:
            next = connected[-1] + 1
        else:
            next = min(neighbors)

        connected.append(self.check_move(connected, neighbors, next))
        if len(connected) >= n_qubits:
            return connected
        else:
            return self.find_chain(n_qubits=n_qubits, connected=connected)

    def check_move(self, connected, neighbors, next):
        """Checks if adding next to connected ends up isolating a qubit *q*,
        if so it returns *q* instead of next

        Args:
            connected (list): list of connected physical qubits so far
            neighbors (set): set of neighbors of last connected qubits
            next (int): next physical qubit to connect

        Returns:
            int: physical qubit to add to connected
        """
        neighbors.remove(next)
        for n in neighbors:
            if len(set(self._undirected_map[n]).difference(connected)) < 2:
                return n
        return next

    def undirected_map(self):
        """From the coupling map, obtains a dictionary representation of the directed
        and undirected coupling maps.

        Example:
            coupling_map = [(0, 1), (1, 2), (1, 3)]

            directed_map = {0: [1], 1: [2, 3], 2: [], 3: []}

            undirected_map = {0: [1], 1: [0, 2, 3], 2: [1], 3: [1]}

        Returns:
            tuple: the directed map and undirected map as dictionaries
        """
        undirected_map = dict()
        for edge in self._coupling_map:
            if edge[0] not in undirected_map:
                undirected_map.update({edge[0]: []})
            if edge[1] not in undirected_map:
                undirected_map.update({edge[1]: []})
            if edge[1] not in undirected_map[edge[0]]:
                undirected_map[edge[0]].append(edge[1])
            if edge[0] not in undirected_map[edge[1]]:
                undirected_map[edge[1]].append(edge[0])
        return undirected_map

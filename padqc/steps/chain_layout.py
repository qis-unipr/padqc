import logging

from padqc.steps.exceptions import StepError
from padqc.steps.base_steps import AnalysisStep

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


class ChainLayout(AnalysisStep):

    def __init__(self, coupling_map, n_qubits=None, inverse=False):
        super().__init__()
        self._inverse = inverse
        self._n_qubits = n_qubits
        if isinstance(coupling_map, list):
            self._coupling_map = coupling_map
        else:
            raise StepError('Coupling map of type %s is not valid' % coupling_map.__class__)
        self._undirected_map = dict()
        self._chain = list()

    def run(self):
        """Executes the step.
        """
        self._undirected_map = self.undirected_map()
        logger.debug('Undirected map: ' + str(self._undirected_map))
        self._chain = self.find_chain(n_qubits=self._n_qubits)
        if self._inverse is True:
            self._chain = self._chain[::-1]
        self._properties['layout'] = self._chain
        logger.info('Chain: %s' % self._chain)

    def find_chain(self, n_qubits=None):
        """Finds a sequence of physical qubits such that qubit i has a connection
        with qubits (i-1) and (i+1) in undirected_map

        Args:
            connected (list): list of physical qubits already added to the sequence
            n_qubits (int): limits the number qubits to connect to at least n_qubits,
            defaults to len(undirected_map)

        Returns:
            list: list of physical qubits
        """
        max_qubits = len(self._undirected_map.keys())
        if n_qubits is None:
            n_qubits = max_qubits
        if n_qubits > max_qubits:
            raise StepError('Number of qubits greater than device.')

        current = 0
        full_map = [current]
        isolated = []
        isolated_with_data = []
        explored = set()
        explored.add(current)
        to_explore = sorted(list(range(max_qubits)))
        to_explore.remove(current)

        last_back_step = None
        # loop over the coupling map until all qubits no more qubits
        # can be connected to the chain
        while len(explored) < max_qubits:
            neighbors = []
            no_neighbors = True
            for n in self._undirected_map[current]:
                if n not in explored:
                    no_neighbors = False
                    neighbors.append(n)
            logger.debug('Neighbors: %s' % str(neighbors))
            # try to select next qubit from neighbors of last connected qubit
            if no_neighbors is False:
                if current + 1 in neighbors:
                    next = current + 1
                else:
                    next = min(neighbors)

                explored.add(next)
                to_explore.remove(next)
                current = next
                full_map.append(next)

                # check that there are still qubits to explore
                if len(explored) < max_qubits - 1:
                    for n1 in self._undirected_map[next]:
                        if n1 not in explored:
                            to_remove = True
                            if len(self._undirected_map[n1]) == 1 and len(explored) < max_qubits - 1:
                                explored.add(n1)
                                to_explore.remove(n1)
                                isolated_with_data.append((next, n1))
                                isolated.append(n1)
                                continue
                            # check that the selected qubit does not lead to a dead end
                            for n2 in self._undirected_map[n1]:
                                if n2 not in explored or n2 == next:
                                    to_remove = False
                            if to_remove is True:
                                explored.add(n1)
                                to_explore.remove(n1)
                                isolated_with_data.append((next, n1))
                                isolated.append(n1)
            else:
                # if no neighbors are found, go back the chain until a new neighbor is found
                # and restart the loop from there
                logger.debug('last back step: %s' % str(last_back_step))
                if full_map[-2] != last_back_step and abs(to_explore[0] - current) < len(to_explore):
                    isolated_with_data.append((full_map[-2], current))
                    isolated.append(current)
                    full_map.remove(current)
                    current = full_map[-1]
                    last_back_step = current
                else:
                    break

            logger.debug('Full chain: %s' % str(full_map))
            logger.debug('Explored: %s' % str(explored))
            logger.debug('To Explore: %s' % str(to_explore))
            logger.debug('Isolated: %s' % str(isolated_with_data))

        # check for isolated qubits
        for q in range(max_qubits):
            if q not in explored and q not in isolated:
                for i in isolated:
                    if q in self._undirected_map[i]:
                        isolated_with_data.append((i, q))
                        isolated.append(q)
                        explored.add(q)
                        break
                for n in self._undirected_map[q]:
                    if n in full_map and q not in isolated:
                        isolated_with_data.append((n, q))
                        isolated.append(q)
                        explored.add(q)
                        break

        # if the chain is not long enough, add the isolated qubits
        remaining = n_qubits - len(full_map)
        if remaining > 0:
            logger.debug('Checking isolated')
        while remaining > 0:
            for next in isolated_with_data:
                logger.debug('Found isolated %s' % str(next))
                if next[0] in full_map:
                    if next[0] in isolated:
                        logger.debug('Adding %d after %d' % (next[0], next[1]))
                        full_map.insert(full_map.index(next[0]) + 1, next[1])
                    else:
                        logger.debug('Adding %d before %d' % (next[0], next[1]))
                        full_map.insert(full_map.index(next[0]), next[1])
                    isolated_with_data.remove(next)
                    remaining -= 1
                    break
        return full_map

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

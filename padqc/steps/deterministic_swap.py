import logging
from copy import deepcopy

from networkx import topological_sort

from padqc.q_circuit import QCircuit
from padqc.gates import Cx, Rz, Ry, Rx
from padqc.gates.single_q_gates import Measure
from padqc.gates.base_gates import Input, Output, Classic, Barrier, DummyGate
from padqc.q_graph import Graph, Node
from padqc.steps import CompilingStep, Decompose
from padqc.steps.exceptions import StepError

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


class DeterministicSwap(CompilingStep):
    """
    Compiling step for circuits characterized by nearest-neighbor CNOT sequences,
    adopts a deterministic SWAP strategy when needed.
    """

    def __init__(self, coupling_map, **kwargs):
        """
        Args:
            coupling_map (list): the coupling on which to compile the circuit,
                a list of tuples representing edges in the coupling map
            offset (int): if the circuit needs less qubits than there are in the coupling-map
                and offset is more than 0, DeterministicSwap will map qubits in the circuit to qubits
                in the layout in the interval [offset : n_qubits+offset] instead of [0 : n_qubits],
                where n_qubits is the number of qubits needed by the circuit
        """
        super().__init__()
        self.SWAP_DEPTH = 3
        self._coupling_map = coupling_map
        if 'offset' in kwargs:
            self._offset = kwargs['offset']
        else:
            self._offset = None
        self._wire_to_reg = dict()
        self._reg_to_wire = dict()
        self._layout = dict()
        self._depths = dict()
        self._measured = list()
        self._available = set()
        self._directed_map, self._undirected_map = self.maps_as_dict()
        logger.debug('Undirected map: ' + str(self._undirected_map))
        self._graph = Graph()

    def offset_tuning(self, q_circuit):
        """Compiles the first n/2 remote CNOTs in an n qubit circuit with different offset values
        to find the best depth-wise offset.

        Args:
            q_circuit (q_circuit.QCircuit): the quantum circuit for which the offset must be tuned
        """
        max_offset = len(self._chain) - q_circuit.n_qubits
        if max_offset == 0:
            logger.info('Offset set to 0')
            self._offset = 0
            return
        depths = list()
        stop = q_circuit.n_qubits // 2

        test_circuit = QCircuit()
        for q_reg in q_circuit.q_regs:
            test_circuit.add_q_register(q_reg, q_circuit.q_regs[q_reg][1])
        for c_reg in q_circuit.c_regs:
            test_circuit.add_c_register(c_reg, q_circuit.c_regs[c_reg][1])

        n_remotes_cx = 0
        remotes_cx = list()
        for node in topological_sort(q_circuit.q_graph.graph):
            if n_remotes_cx > stop:
                break
            gate = deepcopy(node.gate)
            if isinstance(gate, Cx):
                logger.debug('Cx[%s,%s]' % (str(gate.control), str(gate.target)))
                if abs(gate.control[0] - gate.target[0]) != 0:
                    if abs(gate.control[0] - gate.target[0]) == 1:
                        if gate.control[0] < gate.target[0] and \
                                gate.control[1] + 1 == q_circuit.q_regs[q_circuit.q_graph._q_reg_id_to_name(
                            gate.control[0])][1] and gate.target[1] == 0:
                            if (gate.control, gate.target) not in remotes_cx:
                                logger.debug('Remote Cx[%s,%s]' % (str(gate.control), str(gate.target)))
                                remotes_cx.append((gate.control, gate.target))
                                n_remotes_cx += 1
                        elif gate.control[0] > gate.target[0] and gate.target[1] + 1 == \
                                q_circuit.q_regs[q_circuit.q_graph._q_reg_id_to_name(gate.target[0])][1] and \
                                gate.control[1] == 0:
                            if (gate.control, gate.target) not in remotes_cx:
                                logger.debug('Remote Cx[%s,%s]' % (str(gate.control), str(gate.target)))
                                remotes_cx.append((gate.control, gate.target))
                                n_remotes_cx += 1
                        else:
                            continue
                    else:
                        if (gate.control, gate.target) not in remotes_cx:
                            logger.debug('Remote Cx[%s,%s]' % (str(gate.control), str(gate.target)))
                            remotes_cx.append((gate.control, gate.target))
                            n_remotes_cx += 1
                else:
                    if abs(gate.control[1] - gate.target[1]) != 1:
                        if (gate.control, gate.target) not in remotes_cx:
                            logger.debug('Remote Cx[%s,%s]' % (str(gate.control), str(gate.target)))
                            remotes_cx.append((gate.control, gate.target))
                            n_remotes_cx += 1
                test_circuit.q_graph._append_node(type=node.type, op=gate)

        if n_remotes_cx == 0:
            logger.info('No remote cnot found')
            logger.info('Offset set to 0')
            self._offset = 0
            return

        logger.debug('Found %d remote cnots.' % n_remotes_cx)

        for offset in range(max_offset + 1):
            logger.debug('Trying with offset %d' % offset)
            copy_test_cirucit = deepcopy(test_circuit)
            test_swapper = DeterministicSwap(coupling_map=self._coupling_map, offset=offset)
            test_swapper.properties = deepcopy(self.properties)
            test_swapper.run(copy_test_cirucit)

            depths.append(copy_test_cirucit.depth())
            logger.debug('Offset %d with circuit depth %d' % (offset, depths[offset]))
            best = min(depths)
            if depths[-1] > best and (depths[-1] / best) - 1 > 0.25:
                break
        self._offset = depths.index(min(depths))
        logger.info('Best offset %d with circuit depth %d' % (self._offset, depths[self._offset]))

    def run(self, q_circuit):
        """Executes the compiling step on *q_circuit*.

        Args:
            q_circuit (q_circuit.QCircuit): the circuit to be compiled
        """

        self._chain = self._properties['layout']

        if self._offset is None:
            logger.debug('Offset Tuning')
            self.offset_tuning(q_circuit)

        for q_reg in q_circuit.q_graph.q_registers:
            self._graph._add_q_register(q_reg, q_circuit.q_graph.q_registers[q_reg]['dim'])
        for c_reg in q_circuit.q_graph.c_registers:
            self._graph._add_c_register(c_reg, q_circuit.q_graph.c_registers[c_reg]['dim'])

        for q_reg in sorted(self._graph.q_registers.values(), key=lambda x: x['id']):
            for i in range(q_reg['dim']):
                self._wire_to_reg[len(self._wire_to_reg)] = (q_reg['id'], i)
                self._reg_to_wire[(q_reg['id'], i)] = len(self._reg_to_wire)
                self._layout[(q_reg['id'], i)] = (q_reg['id'], i)
                self._depths[len(self._wire_to_reg) - 1] = 0

        self._available = set(self._chain[self._offset:self._offset + len(self._wire_to_reg)])
        logger.debug(self._available)

        regs_to_phys_q = {(self._graph._q_reg_id_to_name(q_reg['id']), i): self.phys_q((q_reg['id'], i))
                          for q_reg in self._graph.q_registers.values() for i in range(q_reg['dim'])}

        q_circuit.layout = regs_to_phys_q
        Decompose().run(q_circuit)
        measure_nodes = list()
        for node in q_circuit.q_graph.graph.nodes:
            if isinstance(node.gate, Measure):
                measure_nodes.append(node)
        if len(measure_nodes) != 0:
            q_args = list()
            pred_nodes = list()
            for node in measure_nodes:
                q_args.extend(node.gate.q_args)
                for pred in list(q_circuit.q_graph.graph.predecessors(node)):
                    pred_nodes.append(pred)
                    q_circuit.q_graph.graph.remove_edge(pred, node)
            measure = q_circuit.q_graph._add_node(Node(type='barrier', gate=Barrier(q_args)))
            for node in measure_nodes:
                q_circuit.q_graph.graph.add_edge(measure, node, name='%s[%d]' % (
                    self._graph._q_reg_id_to_name(node.q_args[0][0]), node.q_args[0][1]))
            for pred in pred_nodes:
                for q_arg in pred.q_args:
                    if q_arg in q_args:
                        q_circuit.q_graph.graph.add_edge(pred, measure, name='%s[%d]' % (
                            self._graph._q_reg_id_to_name(q_arg[0]), q_arg[1]))

        for node in topological_sort(q_circuit.q_graph.graph):
            gate = node.gate
            if not isinstance(gate, (Input, Output, Classic)):
                if isinstance(gate, Cx):
                    if self.remote_cx(gate):
                        logger.debug('cx: %s - %s' % (str(gate.control), str(gate.target)))
                        self.chain_swap(self.path(gate.control, gate.target))
                    else:
                        logger.debug('cx: %s - %s' % (str(gate.control), str(gate.target)))
                    self.cx(gate.control, gate.target)
                elif isinstance(gate, Measure):
                    logger.debug('%s: %s' % (gate.name, str(gate.q_args)))
                    new_gate = deepcopy(gate)
                    new_gate.q_args = self._layout[gate.q_args[0]]
                    self._measured.append(self.phys_q(gate.q_args[0]))
                    self._graph._append_node(type=node.type, op=new_gate)
                elif isinstance(gate, Barrier):
                    new_gate = deepcopy(gate)
                    q_args = [self._layout[q_arg] for q_arg in gate.q_args]
                    new_gate.q_args = q_args
                    self._graph._append_node(type=node.type, op=new_gate)
                    self.update_depth(*gate.q_args)
                else:
                    if isinstance(gate, (Rx, Ry, Rz)):
                        logger.debug('%s: %s %s' % (gate.name, str(gate.q_args), str(gate.theta)))
                    else:
                        logger.debug('%s: %s' % (gate.name, str(gate.q_args)))
                    new_gate = deepcopy(gate)
                    if isinstance(gate, DummyGate):
                        new_gate.q_args = [self._layout[q_arg] for q_arg in gate.q_args]
                    else:
                        new_gate.q_args = self._layout[gate.q_args[0]]
                    self._graph._append_node(type=node.type, op=new_gate)
                    self.update_depth(gate.q_args[0])
        q_circuit._layout = self._layout
        q_circuit.q_graph = self._graph
        logger.info('Layout: %s' % str(q_circuit.properties['layout']))

    def cx(self, control, target):
        """Applies a CNOT or an inverted CNOT between control and target logical qubits,
        according to the coupling map.

        Args:
            control (tuple): control logical qubit (q_reg_id, q_reg_index)
            target (tuple): target logical qubit (c_reg_id, c_reg_index)
        """
        if self.phys_q(target) not in self._undirected_map[self.phys_q(control)]:
            raise StepError('CX between %s-%s not valid' % (str(self._layout[control]), str(self._layout[target])))
        self._graph._append_node(type='gate', op=Cx(self._layout[control], self._layout[target]))
        self.update_depth(control, target)

    def remote_cx(self, cx):
        """Cheks if a CNOT is remote.

        Args:
            cx (gates.Cx): the CNOT gate

        Returns:
            bool: True if the CNOT is remote, False otherwise
        """
        if self.phys_q(cx.target) in self._undirected_map[self.phys_q(cx.control)]:
            return False
        else:
            return True

    def wire(self, reg):
        """Returns the circuit wire of a logical qubit.

        Args:
            reg (tuple): the logical qubit (q_reg_id, q_reg_index)

        Returns:
            int: the wire
        """
        return self._reg_to_wire[reg]

    def reg(self, wire):
        """Returns the logical qubit of a circuit wire.

        Args:
            wire (int): the circuit wire

        Returns:
            tuple: the logical qubit (q_reg_id, q_reg_index)
        """
        return self._wire_to_reg[wire]

    def phys_q(self, reg):
        """Returns the physical qubit of a logical qubit.

        Args:
            reg (tuple): the logical qubit (q_reg_id, q_reg_index)

        Returns:
            int: the physical qubit
        """
        return self._chain[(self.wire(reg) + self._offset) % len(self._chain)]

    def update_depth(self, *args):
        """Increments depth of qubits in *args, if more than one qubit is specified
            they are considered from a multi-qubit gate and it sets the depths to the max
            depth between all of them

        Args:
            *args (): variable length logical qubits list
        """
        max_depth = max((self._depths[self.wire(q)] for q in args)) + 1
        for q in args:
            self._depths[self.wire(q)] = max_depth

    def path(self, control, target):
        """Finds path from control to target logical qubits using *bring_closer()* function

        Args:
            control (tuple): locigal control qubit
            target (tuple): logical target qubit

        Returns:
            list: path of wires from control to target logical qubits
        """
        q1, q2 = control, target
        if self.wire(control) > self.wire(target):
            q1, q2 = q2, q1
        path = self.bring_closer(q1, q2)
        return path

    def chain_swap(self, path):
        """Applies a sequence of SWAPs following path

        Args:
            path (list): path of wires to follow on which to apply a sequence a SWAP gates
        """
        logger.debug('Swap Path: %s' % str(path))
        for q1, q2 in zip(path[:-1], path[1:]):
            logger.debug('SWAP: %s-%s' % (self.reg(q1), self.reg(q2)))

            self.cx(self.reg(q1), self.reg(q2))
            self.cx(self.reg(q2), self.reg(q1))
            self.cx(self.reg(q1), self.reg(q2))

        for e, q in enumerate(path[:-1]):
            self._layout[self.reg(q)], self._layout[self.reg(path[e + 1])] = self._layout[
                                                                                 self.reg(path[e + 1])], \
                                                                             self._layout[self.reg(q)]
            self._reg_to_wire[self.reg(q)], self._reg_to_wire[self.reg(path[e + 1])] = \
                self.wire(self.reg(path[e + 1])), \
                self.wire(self.reg(q))
            self._wire_to_reg[q], self._wire_to_reg[path[e + 1]] = self.reg(path[e + 1]), self.reg(q)
        logger.debug('Wire to Reg layout after swap' + str(self._wire_to_reg) + '\n')
        logger.debug('Reg to Wire layout after swap' + str(self._reg_to_wire) + '\n')
        logger.debug('Reg to Reg layout after swap' + str(self._layout) + '\n')

    def bring_closer(self, q1, q2):
        """Moves logical qubit *q1* over a neighbor of logical qubit *q2* using *from_q1_to_q2()* function

        Args:
            q1 (tuple): logical qubit to move
            q2 (tuple): logical qubit to reach

        Returns:
            list: path of wires from q1 to q2
        """

        self._available = self._available.difference(
            self._measured)
        available_qubits = deepcopy(self._available)

        logger.debug('Available qubits: %s' % str(available_qubits))
        common_neighbours = set(self._undirected_map[self.phys_q(q1)]).intersection(
            self._undirected_map[self.phys_q(q2)]).intersection(available_qubits)
        logger.debug('Common neighbours: ' + str(common_neighbours))
        if len(common_neighbours) != 0:
            swap_to = min((q for q in common_neighbours),
                          key=lambda x: (
                              abs(x - self.phys_q(q2)), self._depths[self._chain.index(x) - self._offset]))
            logger.debug('Path: %s' % str([self.wire(q1), self._chain.index(swap_to) - self._offset]))
            return [self.wire(q1), self._chain.index(swap_to) - self._offset]
        else:
            path = self.from_q1_to_q2(q1, q2, available_qubits)
            logger.info('Path: ' + str(path))
            temp = path.copy()
            t = 0
            while t < len(temp) - 2:
                q = temp[t]
                loop = False
                for x in self._available.intersection(
                        self._undirected_map[self._chain[(q + self._offset) % len(self._chain)]]):
                    x_wire = self._chain.index(x)-self._offset
                    if x_wire in temp[t + 2:]:
                        loop = True
                        t = temp.index(x_wire)
                        for i in temp[temp.index(q) + 1:t]:
                            if i in path:
                                path.remove(i)
                if loop is False:
                    t += 1

            return path

    def from_q1_to_q2(self, q1, q2, available_qubits, path=None):
        """Finds a path from locigal qubit *q1* to logical qubit *q2* recursively

        Args:
            q1 (tuple): logical qubit to move
            q2 (tuple): logical qubit to reach
            available_qubits (set): set of physical qubits that can be used to create a path
            path (list): path from previous iterations

        Returns:
            list: path of wires from q1 to q2
        """
        best = None
        if path is None:
            path = [self.wire(q1)]
        logger.debug('Path: %s' % str(path))
        available_qubits = set(available_qubits).difference([self.phys_q(q1)])
        logger.debug('Available qubits: %s' % str(available_qubits))

        first_round = self.order_dist_by_depth(self.phys_q(q2),
                                               set(self._undirected_map[self.phys_q(q1)]).intersection(
                                                   available_qubits),
                                               available_qubits)

        if len(first_round) == 0:
            self.from_q1_to_q2(self.reg(path[-2]), q2, available_qubits.union(
                self._undirected_map[self._chain[(path[-2] + self._offset) % len(self._chain)]]).difference(
                [self._chain[(path[-1] + self._offset) % len(self._chain)]]).intersection(self._available),
                               path[:-1])
        logger.debug('Frist round: ' + str(first_round))
        if self.phys_q(q2) in [x[0] for x in first_round]:
            return path
        for q in first_round:
            if len(q) == 2:
                path.extend([self._chain.index(q[0]) - self._offset, self._chain.index(q[1]) - self._offset])
                return path
            logger.debug('Second round neighbours: ' + str(
                set(self._undirected_map[q[0]]).intersection(available_qubits).difference(
                    self._undirected_map[self.phys_q(q1)])))
            second_round = self.order_dist_by_depth(self.phys_q(q2),
                                                    set(self._undirected_map[q[0]]).intersection(
                                                        available_qubits).difference(
                                                        self._undirected_map[self.phys_q(q1)]),
                                                    set(available_qubits).difference([q[0]]))
            if len(second_round) == 0:
                continue
            logger.debug('Second round: ' + str(second_round))
            if len(second_round[0]) == 2:
                path.extend(
                    [self._chain.index(q[0]) - self._offset,
                     self._chain.index(second_round[0][0]) - self._offset,
                     self._chain.index(second_round[0][1]) - self._offset])
                return path
            if best is None or second_round[0][2] < best[1][1]:
                best = (q[0], (second_round[0][0], second_round[0][2]))
                logger.debug('Best: ' + str(best))
            if self.phys_q(q2) in [x[0] for x in second_round]:
                path.append(self._chain.index(q[0]) - self._offset)
                return path

        if best is None:
            return self.from_q1_to_q2(self.reg(path[-2]), q2, available_qubits.union(
                self._undirected_map[self._chain[(path[-2] + self._offset) % len(self._chain)]]).difference(
                self._undirected_map[self._chain[(path[-1] + self._offset) % len(self._chain)]]).intersection(
                self._available), path[:-1])

        path.append(self._chain.index(best[0]) - self._offset)
        return self.from_q1_to_q2(self.reg(self._chain.index(best[0]) - self._offset), q2,
                                  set(available_qubits).difference([best[0]]).difference(
                                      self._undirected_map[
                                          self._chain[(path[-2] + self._offset) % len(self._chain)]]),
                                  path=path)

    def order_dist_by_depth(self, q, neighbors, available_qubits):
        """Rates every qubit in neighbors based ont their depth and distance from neighbors of qubit *q*

        Args:
            q (int): physical qubit
            neighbors (set): set of physical qubits
            available_qubits (set): set physical qubits than can be used

        Returns:
            list: list of tuples (n, m, dist) where n is a qubit from neighbors,
            m is a qubit from the neighbors of q and dist is a distance estimate between n and m.
                If n and m are neighbors, ut return only the tuple (n, m) with no distance estimate
        """
        q_neighbors = set(self._undirected_map[q]).intersection(available_qubits)

        # neighbors are sorted using a cost function f
        # f = (SWAP_DEPTH * estimated_distance_between_n_and_q) + max_depth_between_n_and_q
        # where SWAP_DEPTH is the maximum cost in depth for a single
        logger.debug('Neighbors: %s' % neighbors)
        logger.debug('Q_Neighbors: %s' % q_neighbors)
        temp_evaluated = [(n, q, max(
            [self._depths[self._chain.index(n) - self._offset],
             self._depths[self._chain.index(q) - self._offset]])) for
                          n in
                          neighbors for q in q_neighbors if
                          abs(n - q) == 1 and q in self._undirected_map[n] or abs(n - q) != 1]
        evaluated = list()
        for e in temp_evaluated:
            chain_dist = abs(self._chain.index(e[0])-self._chain.index(e[1]))
            if abs(e[0]-e[1]) > chain_dist:
                evaluated.append((e[0], e[1], chain_dist*self.SWAP_DEPTH+e[2]))
            else:
                evaluated.append((e[0], e[1], abs(e[0]-e[1])*self.SWAP_DEPTH+e[2]))
        evaluated = sorted(evaluated, key=lambda x: x[2])
        logger.debug('Evaluated: ' + str(evaluated))
        # sometimes destination can be reached even if the estimated distance is not 1
        for e in evaluated:
            if e[0] in self._undirected_map[e[1]]:
                return [(e[0], e[1])]
        return evaluated

    def maps_as_dict(self):
        """From the coupling map, obtains a dictionary representation of the directed
        and undirected coupling maps.

        Example:
            coupling_map = [(0, 1), (1, 2), (1, 3)]

            directed_map = {0: [1], 1: [2, 3], 2: [], 3: []}

            undirected_map = {0: [1], 1: [0, 2, 3], 2: [1], 3: [1]}

        Returns:
            tuple: the directed map and undirected map as dictionaries
        """
        directed_map = dict()
        undirected_map = dict()
        for edge in self._coupling_map:
            if (edge[1], edge[0]) not in self._coupling_map:
                self.SWAP_DEPTH = 5
            if edge[0] not in directed_map:
                directed_map.update({edge[0]: []})
            if edge[0] not in undirected_map:
                undirected_map.update({edge[0]: []})
            if edge[1] not in directed_map:
                directed_map.update({edge[1]: []})
            if edge[1] not in undirected_map:
                undirected_map.update({edge[1]: []})
            directed_map[edge[0]].append(edge[1])
            if edge[1] not in undirected_map[edge[0]]:
                undirected_map[edge[0]].append(edge[1])
            if edge[0] not in undirected_map[edge[1]]:
                undirected_map[edge[1]].append(edge[0])
        return directed_map, undirected_map

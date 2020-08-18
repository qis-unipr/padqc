from padqc.gates import Cx, Hadamard
from padqc.q_graph import Graph, Node
from padqc.steps import TransformationStep


class Patterns(TransformationStep):
    """
    Transformation step for specific two-qubit gate patterns.
    """

    def __init__(self):
        super().__init__()
        self._num_qubits = None
        self._wires_to_id = {}
        self._id_to_wires = {}
        self._layers = None
        self._extra_layers = None
        self._skip = []
        self.patterns = 0

    def run(self, q_circuit):
        """Executes the transformation step.

        Args:
            q_circuit (q_circuit.QCircuit): the circuit on which to run the step
        """
        self._num_qubits = q_circuit.q_graph.n_qubits
        i = 0
        for q_reg in q_circuit.q_graph.q_registers.values():
            for q in range(q_reg['dim']):
                self._wires_to_id[(q_reg['id'], q)] = i
                self._id_to_wires[i] = (q_reg['id'], q)
                i += 1
        self.find_pattern(q_circuit)
        q_circuit.patterns = self.patterns

    def find_pattern(self, q_circuit):
        """Finds specific two-qubit gate patterns in *q_circuit*

        Args:
            q_circuit (q_circuit.QCircuit): the circuit into which to search for patterns
        """
        q_graph = q_circuit.q_graph
        new_graph = Graph()
        for register in q_graph.q_registers:
            new_graph._add_q_register(register, q_circuit.q_regs[register][1])
        for register in q_graph.c_registers:
            new_graph._add_c_register(register, q_circuit.c_regs[register][1])

        # get dag layers
        self._layers = [layer for layer in q_circuit.q_graph.layers()]
        # this is the list of new layers for the nearest-neighbor CNOT sequences
        self._extra_layers = {l: [] for l in range(len(self._layers))}

        # loop through all layers
        for i, layer in enumerate(self._layers):
            if i != 0:
                # add nearest-neighbor CNOT sequences in the right layer
                for node in self._extra_layers[i - 1]:
                    new_graph._append_node(node.type, node.gate)

            # check all gates in the layer
            for node in layer:
                temp = None
                # do not add gates that have been used in the transformation process
                if node in self._skip:
                    continue
                # every cnot could be the starting point for a CNOT cascade
                elif node.name == 'cx':
                    # check for a CNOT cascade
                    # print('Checking Cascade')
                    temp = self.check_cascade(node, i)
                    if temp is not None:
                        self._skip.extend(temp)
                        # print('Found Cascade')
                        self.patterns += 1
                    else:
                        # check for an inverted CNOT cascade
                        # print('Checking Inverse Cascade')
                        temp = self.check_inverse_cascade(node, i)
                        if temp is not None:
                            self._skip.extend(temp)
                            # print('Found Inverse Cascade')
                            self.patterns += 1
                        else:
                            # apply the CNOT if no cascade was found
                            self._skip.append(node)
                            new_graph._append_node(node.type, node.gate)
                else:
                    if node.type == 'gate':
                        self._skip.append(node)
                        new_graph._append_node(node.type, node.gate)
        q_circuit.q_graph = new_graph

    def check_cascade(self, node, layer_id):
        """Starting from *q_node*, searches for CNOT cascades
            and transform them into nearest-neighbor CNOT sequences.

        Args:
            layer_id (int): the layer index
            node (q_graph.Node): the node from which to start searching for a CNOT cascade

        Returns:
            list: a list of nodes to be skipped as they are part of an already transformed CNOT cascade
        """

        target = self._wires_to_id[node.q_args[1]]
        control = self._wires_to_id[node.q_args[0]]
        controls = [control]
        skip = [node]
        # qubits already added to the CNOT sequence
        used = set()
        used.add(target)
        used.add(control)
        # qubits that cannot be used anymore
        off_limits = set()
        before = {}
        after = []

        # flag to identify the direction of the cascade
        descending = False
        if control > target:
            descending = True

        count = 1
        last_layer = layer_id

        double_break = False
        # loop through layers until a max limit is reached
        while count < min([2 * self._num_qubits, len(self._layers) - layer_id]):
            for node in self._layers[layer_id + count]:
                if node in self._skip:
                    for qarg in node.q_args:
                        if self._wires_to_id[qarg] == target:
                            double_break = True
                            break
                else:
                    if node.name == 'cx':
                        # print('CX: ', node.q_args)
                        g_control = self._wires_to_id[node.q_args[0]]
                        g_target = self._wires_to_id[node.q_args[1]]
                        if g_control == target:
                            double_break = True
                            break
                        if g_control in off_limits or g_target in off_limits:
                            off_limits.add(g_control)
                            off_limits.add(g_target)
                            if g_control not in used:
                                used.add(g_control)
                            if g_target not in used:
                                used.add(g_target)
                            continue
                        # chek that the CNOT is part of the cascade
                        a = (g_target == target and g_control not in controls and g_control not in used)
                        b = (descending is True and g_control > target) \
                            or (descending is False and g_control < target)
                        if a and b:
                            # print('Adding to Cascade')
                            controls.append(g_control)
                            used.add(g_control)
                            skip.append(node)
                        # check if the CNOT interrupts the cascade
                        elif g_target != target and g_control != target:
                            # remember to put the CNOT after the transformation
                            if g_target not in used and g_control not in used:
                                if last_layer < layer_id + count:
                                    last_layer = layer_id + count
                            # updates used and off limits qubits when necessary
                            else:
                                off_limits.add(g_control)
                                off_limits.add(g_target)
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                                if g_control not in used:
                                    used.add(g_control)
                                if g_target not in used:
                                    used.add(g_target)
                        else:
                            # break the loop if the CNOT interrupts the cascade
                            double_break = True
                            break
                    else:
                        # ignore gates acting on off limits qubits
                        double_continue = False
                        for qarg in node.q_args:
                            if self._wires_to_id[qarg] in off_limits:
                                double_continue = True
                                continue
                        if double_continue is True:
                            continue

                        # for special multi-qubits gates, update used and off limits qubits properly,
                        # break the loop if necessary
                        if node.name in ["barrier", "snapshot", "save", "load", "noise"]:
                            qargs = [self._wires_to_id[qarg] for qarg in node.q_args]
                            if target in qargs:
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                                double_break = True
                                break
                            u = []
                            not_u = []
                            for qarg in qargs:
                                if qarg in used:
                                    off_limits.add(qarg)
                                    u.append(qarg)
                                else:
                                    not_u.append(qarg)
                            if len(u) == len(qargs):
                                # the transformation must be applied before this gate
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                            elif len(u) == 0:
                                # the transformation must be applied after this gate
                                if last_layer < layer_id + count:
                                    last_layer = layer_id + count
                            else:
                                # the transformation must be applied before this gate
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                                for qarg in not_u + u:
                                    used.add(qarg)
                                    off_limits.add(qarg)
                        else:
                            # print(node.name, node.q_args)
                            # check if one-qubits gates either interrupt the cascade,
                            # can be applied after or before
                            qarg = self._wires_to_id[node.q_args[0]]
                            if qarg == target:
                                after.append(node)
                                skip.append(node)
                                double_break = True
                                break
                            if qarg not in used:
                                # print('Before')
                                if qarg not in before:
                                    before[qarg] = []
                                before[qarg].append(node)
                            else:
                                # print('After')
                                after.append(node)
                            skip.append(node)
            count += 1
            if double_break is True:
                break
        # if a cascade was found
        if len(controls) > 1:
            if descending is True:
                controls = sorted(controls)
            else:
                controls = sorted(controls, reverse=True)

            # apply all gates that were encountered before the cascade
            for u in before:
                for node in before[u]:
                    self._extra_layers[last_layer].append(node)

            # apply the transformation
            for i in range(len(controls) - 1, 0, -1):
                self._extra_layers[last_layer].append(Node(type='gate',
                                                           gate=Cx(self._id_to_wires[controls[i]],
                                                                   self._id_to_wires[controls[i - 1]])))
            self._extra_layers[last_layer].append(
                Node(type='gate', gate=Cx(self._id_to_wires[controls[0]], self._id_to_wires[target])))
            for i in range(len(controls) - 1):
                self._extra_layers[last_layer].append(
                    Node(type='gate', gate=Cx(self._id_to_wires[controls[i + 1]],
                                              self._id_to_wires[controls[i]])))

            # apply all gates that were encountered after the cascade
            for node in after:
                self._extra_layers[last_layer].append(node)
        else:
            skip = None

        return skip

    def check_inverse_cascade(self, node, layer_id):
        """Starting from *q_node*, searches for inverted CNOT cascades
            and transforms them into nearest-neighbor CNOT sequences.

        Args:
            layer_id (int): the layer kindex
            node (q_graph.Node): the node from which to start searching for an inverted CNOT cascade

        Returns:
            list: a list of nodes to be skipped as they are part of
            an already transformed inverted CNOT cascade
        """
        target = self._wires_to_id[node.q_args[1]]
        control = self._wires_to_id[node.q_args[0]]
        targets = [target]
        skip = [node]
        # qubits already added to the CNOT sequence
        used = set()
        used.add(target)
        used.add(control)
        # qubits that cannot be used anymore
        off_limits = set()
        before = {}
        after = []

        # flag to identify the direction of the cascade
        descending = False
        if target > control:
            descending = True

        count = 1
        last_layer = layer_id

        double_break = False
        # loop through layers until a max limit is reached
        while count < min([2 * self._num_qubits, len(self._layers) - layer_id]):
            for node in self._layers[layer_id + count]:
                if node in self._skip:
                    for qarg in node.q_args:
                        if self._wires_to_id[qarg] == control:
                            double_break = True
                            break
                else:
                    if node.name == 'cx':
                        g_control = self._wires_to_id[node.q_args[0]]
                        g_target = self._wires_to_id[node.q_args[1]]
                        if g_target == control:
                            double_break = True
                            break
                        if g_control in off_limits or g_target in off_limits:
                            if last_layer > layer_id + count - 1:
                                last_layer = layer_id + count - 1
                            off_limits.add(g_control)
                            off_limits.add(g_target)
                            if g_control not in used:
                                used.add(g_control)
                            if g_target not in used:
                                used.add(g_target)
                            continue
                        # chek that the CNOT is part of the cascade
                        a = (g_control == control and g_target not in targets and g_target not in used)
                        b = (descending is True and g_target > control) or (
                                    descending is False and g_target < control)
                        if a and b:
                            targets.append(g_target)
                            used.add(g_target)
                            skip.append(node)
                        # check if the CNOT interrupts the cascade
                        elif g_control != control and g_target != control:
                            # remember to put the CNOT after the transformation
                            if g_control not in used and g_target not in used:
                                if last_layer < layer_id + count:
                                    last_layer = layer_id + count
                            # updates used and off limits qubits when necessary
                            else:
                                off_limits.add(g_control)
                                off_limits.add(g_target)
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                                if g_control not in used:
                                    used.add(g_control)
                                if g_target not in used:
                                    used.add(g_target)
                        else:
                            # break the loop if the CNOT interrupts the cascade
                            double_break = True
                            break
                    else:
                        # ignore gates acting on off limits qubits
                        double_continue = False
                        for qarg in node.q_args:
                            if self._wires_to_id[qarg] in off_limits:
                                double_continue = True
                                continue
                        if double_continue is True:
                            continue

                        # for special multi-qubits gates, update used and off limits qubits properly,
                        # break the loop if necessary
                        if node.name in ["barrier", "snapshot", "save", "load", "noise"]:
                            qargs = [self._wires_to_id[qarg] for qarg in node.q_args]
                            if control in qargs:
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                                double_break = True
                                break
                            u = []
                            not_u = []
                            for qarg in qargs:
                                if qarg in used:
                                    off_limits.add(qarg)
                                    u.append(qarg)
                                else:
                                    not_u.append(qarg)
                            if len(u) == len(qargs):
                                # the transformation must be applied before this gate
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                            elif len(u) == 0:
                                # the transformation must be applied after this gate
                                if last_layer < layer_id + count:
                                    last_layer = layer_id + count
                            else:
                                # the transformation must be applied before this gate
                                if last_layer > layer_id + count - 1:
                                    last_layer = layer_id + count - 1
                                for qarg in not_u + u:
                                    used.add(qarg)
                                    off_limits.add(qarg)
                        else:
                            # check if one-qubits gates either interrupt the cascade,
                            # can be applied after or before
                            qarg = self._wires_to_id[node.q_args[0]]
                            if qarg == control:
                                after.append(node)
                                skip.append(node)
                                double_break = True
                                break
                            if qarg not in used:
                                if qarg not in before:
                                    before[qarg] = []
                                before[qarg].append(node)
                                skip.append(node)
                            else:
                                after.append(node)
                                skip.append(node)

            count += 1
            if double_break is True:
                break
        # if an inverse cascade was found
        if len(targets) > 1:
            if descending is True:
                targets = sorted(targets)
            else:
                targets = sorted(targets, reverse=True)

            # apply all gates that were encountered before the cascade
            for u in before:
                for node in before[u]:
                    self._extra_layers[last_layer].append(node)

            # apply the transformation
            self._extra_layers[last_layer].append(
                Node(type='gate', gate=Hadamard(self._id_to_wires[control])))
            for t in targets:
                self._extra_layers[last_layer].append(Node(type='gate', gate=Hadamard(self._id_to_wires[t])))
            for i in range(len(targets) - 1, 0, -1):
                self._extra_layers[last_layer].append(Node(type='gate', gate=Cx(self._id_to_wires[targets[i]],
                                                                                self._id_to_wires[
                                                                                    targets[i - 1]])))
            self._extra_layers[last_layer].append(
                Node(type='gate', gate=Cx(self._id_to_wires[targets[0]], self._id_to_wires[control])))
            for i in range(len(targets) - 1):
                self._extra_layers[last_layer].append(
                    Node(type='gate', gate=Cx(self._id_to_wires[targets[i + 1]],
                                              self._id_to_wires[targets[i]])))
            self._extra_layers[last_layer].append(
                Node(type='gate', gate=Hadamard(self._id_to_wires[control])))
            for t in targets:
                self._extra_layers[last_layer].append(Node(type='gate', gate=Hadamard(self._id_to_wires[t])))

            # apply all gates that were encountered after the cascade
            for node in after:
                self._extra_layers[last_layer].append(node)
        else:
            skip = None

        return skip

from .exceptions import GraphError


class Node:
    """
    The graph node class.
    """
    def __init__(self, type, gate, id=-1):
        """
        Args:
            type (str): type of the node
            gate (gates.Gate): the gate
            id (int): node id.
        """
        if type not in ['input', 'output', 'classic_output', 'gate', 'barrier']:
            raise GraphError("Node type must be one fo the following: "
                             "input, output, classic_output, gate, barrier. Got %s instead." % type)
        self._type = type
        self._gate = gate
        self._node_id = id

    @property
    def name(self):
        """
        Returns:
            str: node gate name
        """
        return self._gate.name

    @property
    def type(self):
        """
        Returns:
            str: node gate type
        """
        return self._type

    @type.setter
    def type(self, type):
        self._type = type

    @property
    def gate(self):
        """
        Returns:
            gates.Gate: the node gate
        """
        return self._gate

    @property
    def data(self):
        """"
        Returns:
            dict: node gate data
        """
        return self.gate.data

    @property
    def params(self):
        """
        Returns:
            list: node gate parameters
        """

        return self.gate.params

    @property
    def q_args(self):
        """
        Returns:
            list: node gate quantum arguments
        """

        return self.gate.q_args

    @property
    def c_args(self):
        """
        Returns:
            list: node gate classical arguments
        """
        return self.gate.c_args

    def __hash__(self):
        return hash(id(self))


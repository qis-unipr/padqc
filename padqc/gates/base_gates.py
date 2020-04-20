from abc import abstractmethod
from copy import deepcopy

from .exceptions import GateError


class Gate:
    """
    The base class for every gate.
    """
    def __init__(self, name):
        """Initializes the gate with its name.

        Args:
            name (str): the name of the gate
        """
        self._name = name
        pass

    @property
    def name(self):
        return self._name

    @property
    @abstractmethod
    def data(self):
        """
        Returns:
            dict: a dictionary containing all gate information
        """
        pass


class Input(Gate):
    """
    A special gate, the starting point of qubit in the circuit.
    """
    def __init__(self, name, q_arg):
        """Initializes the gate with its name and its quantum argument, *q_arg* is tuple *(q_reg, q)*.

        Args:
            name (str): the name of the gate
            q_arg (tuple): a tuple (q_reg, q) where q_reg is a quantum register id
            and q is the quantum register index
        """
        super().__init__(name)
        self._q_arg = q_arg
        pass

    @property
    def q_args(self):
        return [self._q_arg]

    @property
    def data(self):
        return {'name': self.name, 'q_arg': self.q_args}


class Output(Gate):
    """
    A special gate, the ending point of qubit in the circuit.
    """
    def __init__(self, name, q_arg):
        """Initializes the gate with its name and its quantum argument, *q_arg* is tuple *(q_reg, q)*.

        Args:
            name (str): the name of the gate
            q_arg (tuple): a tuple (q_reg, q) where q_reg is a quantum register id
            and q is the quantum register index
        """
        super().__init__(name)
        self._q_arg = q_arg
        pass

    @property
    def q_args(self):
        return [self._q_arg]

    @property
    def data(self):
        return {'name': self.name, 'q_arg': self.q_args}


class Classic(Gate):
    """
    A special gate, it represents a classical bit.
    """
    def __init__(self, name, c_arg):
        """Initializes the gate with its name and its quantum argument, *c_arg* is tuple *(c_reg, c)*.

        Args:
            name (str): the name of the gate
            c_arg (tuple): a tuple (c_reg, c) where c_reg is a classical register id
            and c is the classical register index
        """
        super().__init__(name)
        self._c_arg = c_arg

    @property
    def c_arg(self):
        return self._c_arg

    @property
    def data(self):
        return {'name': self.name, 'c_arg': self.c_arg}


class SingleQGate(Gate):
    """
    The base calss for one qubit gates.
    """
    def __init__(self, name, q_arg):
        """Initializes the gate with its name and its quantum argument, *q_arg* is tuple *(q_reg, q)*.

        Args:
            name (str): the name of the gate
            q_arg (tuple): a tuple (q_reg, q) where q_reg is a quantum register id
            and q is the quantum register index
        """
        super().__init__(name)
        self._q_arg = q_arg

    @property
    def q_args(self):
        return [self._q_arg]

    @q_args.setter
    def q_args(self, q_arg):
        self._q_arg = q_arg

    @property
    def data(self):
        return {'name': self.name, 'q_args': [self.q_args]}


class TwoQGate(Gate):
    """
    The base class for two qubits gates.
    """
    def __init__(self, name, q_args):
        """Initializes the gate with its name and its quantum arguments,
        *q_args* is a list of tuples *[(q_reg, q), q_reg, q)]*.

        Args:
            name (str): the name of the gate
            q_args (list): a list of tuples (q_reg, q) where q_reg is a quantum register id
            and q is the quantum register index
        """
        if len(q_args) != 2:
            raise GateError("Expected 2 quantum arguments for %s, received %d arguments instead."
                            % (self.__class__, len(q_args)))
        super().__init__(name)
        self._q_args = q_args

    @property
    def q_args(self):
        return self._q_args

    @property
    def data(self):
        return {'name': self.name, 'q_args': self.q_args}


class Barrier(Gate):
    """
    A special gate preventing cancellation and transformations between gates before and after during circuit compilation.
    """
    def __init__(self, q_args):
        """Initializes the gate with its name and its quantum arguments, *q_args* is a list of tuple *[(q_reg, q), q_reg, q), ...]*.

        Args:
            q_args (list): a list of tuples (q_reg, q) where q_reg is a quantum register id
            and q is the quantum register index
        """
        super().__init__('barrier')
        q_args.sort()
        self._q_args = q_args

    @property
    def q_args(self):
        return self._q_args

    @q_args.setter
    def q_args(self, q_args):
        self._q_args = q_args

    @property
    def data(self):
        return {'name': self.name, 'q_args': self.q_args}


class CompositeGate(Gate):
    """
    A custom gate, composed by other gates, including other CompositeGates.

    Example:
                circuit = QCircuit()

                qr = circuit.add_q_register(name='qr', reg_dim=2)

                # create a composite gate applying an rx rotation by pi on quabit a
                and and ry rotation by pi on qubit b. Two times.

                rx_ry = CompositeGate('rx_ry', q_args=['a'], params=['alpha'])

                # first time

                rx_ry.add_gate(gate='rx', q_args=['a'], params=['alpha'])

                rx_ry.add_gate(gate='ry', q_args=['b'], params=['beta'])

                #second time, adding a copy of rx_ry to rx_ry itself

                rx_ry.add_gate(gate=rx_ry.copy)

                circuit.composite_gate(rx_ry, a=qr[0], b=qr[1], alpha=pi, beta=pi)
    """
    def __init__(self, name, q_args=None, c_args=None, params=None):
        """Initializes the gate with its name, optionally it accepts also quantum and classical arguments
        as well as parameters as key names.

        Args:
            name (str): the name of the composite gate
            q_args (list): a list of key strings, identifying the gate quantum arguments
            c_args (list): a list of key strings, identifying the gate classical arguments
            params (list): a list of key strings, identifying the gate parameters
        """
        super().__init__(name)
        if q_args is None:
            self._q_args = list()
        else:
            self._q_args = q_args
        if c_args is None:
            self._c_args = list()
        else:
            self._c_args = c_args
        if params is None:
            self._params = list()
        else:
            self._params = params
        self._gates = list()
        self._decomposition = dict()

    @property
    def copy(self):
        """
        Returns:
            CompositeGate: a copy of the gate
        """
        return deepcopy(self)

    @property
    def decomposition(self):
        """

        Returns: dict: the gate decomposition as a dict {q_arg_name: q_arg_value, c_arg_name: c_arg_value,
        param_name: param_value}

        """
        return self._decomposition

    @decomposition.setter
    def decomposition(self, decomposition):
        self._decomposition = decomposition

    def add_decompostion(self, decomposition_name):
        self._decomposition[decomposition_name] = None

    @property
    def q_args(self):
        return self._q_args

    @property
    def c_args(self):
        return self._c_args

    @property
    def params(self):
        return self._params

    @q_args.setter
    def q_args(self, q_args):
        self._q_args = q_args

    @c_args.setter
    def c_args(self, c_args):
        self._c_args = c_args

    @params.setter
    def params(self, params):
        self._params = params

    def add_q_arg(self, q_arg):
        """Add a quantum argument to the gate.

        Args:
            q_arg (str): the key string identifying the quantum argument

        """
        self._q_args.append(q_arg)
        self.add_decompostion(q_arg)

    def add_c_arg(self, c_arg):
        """Add a classical argument to the gate.

        Args:
            c_arg (str): the key string identifying the classical argument

        """
        self._c_args.append(c_arg)
        self.add_decompostion(c_arg)

    def add_param(self, param):
        """Add a parameter to the gate.

        Args:
            param (str): the key string identifying the parameter

        """
        self._params.append(param)
        self.add_decompostion(param)

    @property
    def gates(self):
        """

        Returns:
            list: the list of gates composing the composite gate as [(gate, q_args, c_args, params), ...]

        """
        return self._gates

    @gates.setter
    def gates(self, decomposition):
        self._gates = decomposition

    def add_gate(self, gate, q_args=None, c_args=None, params=None, mapping=None):
        """Adds a gate to the composite gate.

        Args: gate (str | gates.CompositeGate): the string gate name or a CompositeGate. Accepted gate
        names are: id, x, y, z, rx, ry, rz, h, cx, barrier and measure q_args (list): a list of key
        strings, identifying the gate quantum arguments c_args (list): a list of key strings, identifying
        the gate classical arguments params (list): a list of key strings, identifying the gate parameters
        mapping (dict): a dictionary that maps composite gate arguments to the arguments of
        a composite gate inside of it
        """
        if q_args is None and c_args is None:
            raise GateError("Gate needs at least one quantum argument or classical argument")
        if isinstance(gate, CompositeGate):
            if mapping is None:
                raise GateError("Must provide arguments mapping for composite gate inside a composite gate.")
            else:
                inv_mappimg = dict()
                for key, value in mapping.items():
                    inv_mappimg[value] = key
            if gate is self:
                gates = gate.copy.gates
            else:
                gates = gate.gates
            for g in gates:
                new_q_args = None
                new_c_args = None
                if g[1] is not None:
                    new_q_args = [inv_mappimg[q_arg] for q_arg in g[1]]
                if g[2] is not None:
                    new_q_args = [inv_mappimg[c_arg] for c_arg in g[2]]
                self.add_gate(gate=g[0], q_args=new_q_args,
                              c_args=new_c_args, params=g[3])
        else:
            if gate not in ['id', 'x', 'y', 'z', 'rx', 'ry', 'rz', 'h', 'cx', 'barrier', 'measure']:
                raise GateError("Gate must be either a CompositeGate or a string from: "
                                "[id, x, y, z, rx, ry, rz, h, cx, barrier, measure]")
            if q_args is not None:
                for q_arg in q_args:
                    if q_arg not in self.q_args:
                        self.add_q_arg(q_arg)
            if c_args is not None:
                for c_arg in c_args:
                    if c_arg not in self.c_args:
                        self.add_c_arg(c_arg)
            if params is not None:
                for param in params:
                    if param not in self.params:
                        self.add_param(param)
            self._gates.append((gate, q_args, c_args, params))

    @property
    def data(self):
        return {'name': self.name, 'q_args': self.q_args, 'c_args': self.c_args, 'params': self.params,
                'gates': self.gates, 'decomposition': self.decomposition}


class DummyGate(Gate):

    def __init__(self, name, q_args=None, params=None):
        super().__init__(name)
        if params is None:
            params = []
        if q_args is None:
            q_args = []
        self._q_args = q_args
        self._params = params

    @property
    def q_args(self):
        return self._q_args

    @property
    def c_args(self):
        return self._c_args

    @property
    def params(self):
        return self._params

    @q_args.setter
    def q_args(self, q_args):
        self._q_args = q_args

    @c_args.setter
    def c_args(self, c_args):
        self._c_args = c_args

    @params.setter
    def params(self, params):
        self._params = params

    @property
    def data(self):
        return {'name': self.name, 'q_args': self.q_args, 'c_args': self.c_args, 'params': self.params}

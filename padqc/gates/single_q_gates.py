from padqc.gates.base_gates import SingleQGate


class Id(SingleQGate):
    """
    The identity gate.
    """
    def __init__(self, q):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
        """
        super().__init__('id', q)


class Pauli_X(SingleQGate):
    """
    The Pauli X gate.
    """
    def __init__(self, q):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
        """
        super().__init__('x', q)


class Pauli_Y(SingleQGate):
    """
    The Pauli Y gate.
    """
    def __init__(self, q):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
        """
        super().__init__('y', q)


class Pauli_Z(SingleQGate):
    """
    The Pauli Z gate.
    """
    def __init__(self, q):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
        """
        super().__init__('z', q)


class Rx(SingleQGate):
    """
    A rotation around the *x* axis by an angle *theta*.
    """
    def __init__(self, q, theta):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        super().__init__('rx', q)
        self._theta = theta

    @property
    def theta(self):
        """
        Returns:
            float: the rotation angle
        """
        return self._theta

    @property
    def data(self):
        data = super().data
        data['theta'] = self.theta
        return data


class Ry(SingleQGate):
    """
    A rotation around the *y* axis by an angle *theta*.
    """
    def __init__(self, q, theta):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        super().__init__('ry', q)
        self._theta = theta

    @property
    def theta(self):
        """
        Returns:
            float: the rotation angle
        """
        return self._theta

    @property
    def data(self):
        data = super().data
        data['theta'] = self.theta
        return data


class Rz(SingleQGate):
    """
    A rotation around the *z* axis by an angle *theta*.
    """
    def __init__(self, q, theta):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
            theta (float): the rotation angle
        """
        super().__init__('rz', q)
        self._theta = theta

    @property
    def theta(self):
        """
        Returns:
            float: the rotation angle
        """
        return self._theta

    @property
    def data(self):
        data = super().data
        data['theta'] = self.theta
        return data


class Hadamard(SingleQGate):
    """
    The Hadamard gate.
    """
    def __init__(self, q):
        """
        Args:
            q (tuple): (q_reg_id, q_reg_index)
        """
        super().__init__('h', q)


class Measure(SingleQGate):
    """
    The measurement gate.
    """
    def __init__(self, q_arg, c_arg):
        """
        Args:
            q_arg (tuple): (q_reg_id, q_reg_index)
            c_arg (tuple): (c_reg_id, c_reg_index)
        """
        super().__init__('measure', q_arg)
        self._c_arg = c_arg

    @property
    def c_arg(self):
        return self._c_arg

    @property
    def data(self):
        data = super().data
        data['c_arg'] = self.c_arg
        return data

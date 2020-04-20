from padqc.gates.base_gates import TwoQGate


class Cx(TwoQGate):
    """
    The CNOT gate.
    """
    def __init__(self, control, target):
        """
        Args:
            control (tuple): (q_reg_id, q_reg_index)
            target (tuple): (q_reg_id, q_reg_index)
        """
        super().__init__('cx', [control, target])
        self._control = control
        self._target = target

    @property
    def control(self):
        return self._control

    @property
    def target(self):
        return self._target

    @property
    def data(self):
        data = super().data
        data['control'] = self.control
        data['target'] = self.target
        return data

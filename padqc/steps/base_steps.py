from abc import abstractmethod


class Step:
    """
    Base step class.
    """
    def __init__(self):
        self._properties = dict()
        pass

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, properties):
        self._properties = properties

    @staticmethod
    @abstractmethod
    def run(*args):
        pass


class AnalysisStep(Step):
    """
    Base analysis step class.
    """
    def __init__(self):
        super().__init__()
        pass

    @staticmethod
    @abstractmethod
    def run(*args):
        pass


class CancellationStep(Step):
    """
    Base cancellation step class.
    """
    def __init__(self):
        super().__init__()
        pass

    @staticmethod
    @abstractmethod
    def run(q_circuit):
        pass


class TransformationStep(Step):
    """
    Base compiling step calss.
    """
    def __init__(self):
        super().__init__()
        pass

    @staticmethod
    @abstractmethod
    def run(q_circuit):
        pass


class CompilingStep(Step):
    """
    Base compiling step calss.
    """
    def __init__(self):
        super().__init__()
        pass

    @staticmethod
    @abstractmethod
    def run(q_circuit):
        pass

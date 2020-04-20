import logging

from padqc.steps import Patterns, CancelH, CancelCx, ChainLayout, MergeBarrier, StepError
from padqc.steps.base_steps import AnalysisStep, CompilingStep, CancellationStep, TransformationStep

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


def compile(q_circuit, steps=None, iterate=False, layout=None, explicit=False):
    """Compiles a circuit following the specified steps.

    Args:
        q_circuit (QCircuit): the circuit to be compiled
        steps (list): a list of steps to follow for the compilation.
            Defaults to [Patterns(), CancelH(), CancelCx()]
        iterate (bool): if set to True, cancellation steps will be executed recursively
            until no further cancellation can be achieved. Defaults to False.
    """

    properties = q_circuit._properties
    properties['circuit'] = q_circuit
    if layout is not None:
        properties['layout'] = layout
    elif len(properties['layout']) == 0:
        properties['layout'] = [i for i in range(q_circuit.n_qubits)]
    if steps is None:
        steps = [Patterns(), CancelH(), CancelCx(), MergeBarrier()]
    else:
        if explicit is False:
            analysis_steps = list()
            cancellation_steps = list()
            transformation_steps = list()
            compiling_steps = list()
            merge_barrier = False
            for step in steps:
                if isinstance(step, AnalysisStep):
                    analysis_steps.append(step)
                elif isinstance(step, CancellationStep):
                    if isinstance(step, MergeBarrier):
                        merge_barrier = True
                    cancellation_steps.append(step)
                elif isinstance(step, TransformationStep):
                    transformation_steps.append(step)
                elif isinstance(step, CompilingStep):
                    compiling_steps.append(step)
                else:
                    raise StepError('%s is not a valid step.' % str(step.__class__))
            steps = list()
            steps.extend(analysis_steps)
            steps.extend(transformation_steps)
            steps.extend(compiling_steps)
            steps.extend(cancellation_steps)
            if merge_barrier is False:
                steps.append(MergeBarrier())

    for step in steps:
        if isinstance(step, ChainLayout) and steps.index(step) != 0:
            raise StepError('%s step must be executed before any other step.' % step.__class__)
    repeat = True
    iterating = False
    logger.debug('Steps: '+str(steps))
    while repeat:
        repeat = False
        for step in steps:
            logger.debug('Step: '+str(step.__class__))
            if isinstance(step, CancellationStep):
                step.properties = properties
                cancelled = step.run(q_circuit)
                repeat = cancelled or repeat
            else:
                if not iterating:
                    step.properties = properties
                    if isinstance(step, AnalysisStep):
                        step.run()
                    else:
                        step.run(q_circuit)
        if not iterate:
            repeat = False
        else:
            iterating = True

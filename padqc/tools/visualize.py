import os
import sys
import tempfile
from copy import deepcopy

from networkx.drawing.nx_pydot import to_pydot
from PIL import Image


def circuit_drawer(q_circuit, filename=None, scale=0.7, show=False):
    """Plots the graph representing operations in a quantum circuit.

    This function needs Graphviz to installed on your pc.
    See https://www.graphviz.org/

    Args:
        show (bool): if set to True, show the circuit
        q_circuit (q_circuit.QCircuit): the circuit to plot
        filename (str): file path to save image
        scale (float): scaling factor
    """

    g = deepcopy(q_circuit.q_graph.graph)
    g.graph['dpi'] = 100 * scale

    for node in g.nodes:
        n = g.nodes[node]
        n['label'] = node.name
        if node.type == 'gate':
            # n['label'] += str(node.data)
            n['color'] = 'blue'
            n['style'] = 'filled'
            n['fillcolor'] = 'lightblue'
        if node.type == 'input':
            n['color'] = 'black'
            n['style'] = 'filled'
            n['fillcolor'] = 'green'
        if node.type == 'output':
            n['color'] = 'black'
            n['style'] = 'filled'
            n['fillcolor'] = 'red'
        if node.type == 'classic_output':
            n['color'] = 'black'
            n['style'] = 'filled'
            n['fillcolor'] = 'grey'
        if node.type == 'barrier':
            n['color'] = 'black'
            n['style'] = 'filled'
            n['fillcolor'] = 'white'
    for e in g.edges(data=True):
        e[2]['label'] = e[2]['name']

    dot = to_pydot(g)

    if filename:
        dot.write_png(filename)
        image = Image.open(filename)
    else:
        tmp_path = os.getcwd() + 'dag.png'
        dot.write_png(tmp_path)
        image = Image.open(tmp_path)

    if show is True:
        if ('ipykernel' in sys.modules) and ('spyder' not in sys.modules):
            return image
        else:
            image.show()
    return image

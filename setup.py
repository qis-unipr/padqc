from setuptools import setup

setup(
    name='padqc',
    version='0.1',
    packages=['padqc', 'padqc.gates', 'padqc.steps', 'padqc.tools', 'padqc.q_graph', 'padqc.compiler',
              'padqc.q_circuit', 'padqc.converters'],
    url='https://github.com/qis-unipr/padqc',
    license='Apache License Version 2.0, January 2004 http://www.apache.org/licenses/, Copyright 2020 Davide Ferrari '
            'and Michele Amoretti',
    author='Davide Ferrari, Michele Amoretti',
    author_email='davide.ferrari8@studenti.unipr.it, michele.amoretti@unipr.it',
    description='Pattern-oriented Deterministic Quantum Compiler',
    install_requires=['networkx', 'pillow', 'pydot', 'qiskit', 'pulp'],
    classifiers=[
            "Programming Language :: Python :: 3.6",
            "Operating System :: OS Independent",
        ]
)

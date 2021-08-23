""" BioSimulators-compliant command-line interface to the `tellurium <http://tellurium.analogmachine.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from . import get_simulator_version
from ._version import __version__
from .config import Config
from .core import exec_sedml_docs_in_combine_archive
from .data_model import SedmlInterpreter, PlottingEngine
from biosimulators_utils.simulator.cli import build_cli
from biosimulators_utils.simulator.data_model import EnvironmentVariable
from biosimulators_utils.simulator.environ import ENVIRONMENT_VARIABLES
from unittest import mock

with mock.patch.dict('os.environ', {}):
    config = Config()

environment_variables = list(ENVIRONMENT_VARIABLES.values()) + [
    EnvironmentVariable(
        name='SEDML_INTERPRETER',
        description='SED-ML interpreter.',
        options=list(SedmlInterpreter.__members__.keys()),
        default=config.sedml_interpreter,
        more_info_url='https://docs.biosimulators.org/Biosimulators_tellurium/source/Biosimulators_tellurium.html',
    ),
    EnvironmentVariable(
        name='PLOTTING_ENGINE',
        description='Plotting engine.',
        options=list(PlottingEngine.__members__.keys()),
        default=config.plotting_engine,
        more_info_url='https://docs.biosimulators.org/Biosimulators_tellurium/source/Biosimulators_tellurium.html',
    ),
]

App = build_cli('biosimulators-tellurium', __version__,
                'tellurium', get_simulator_version(), 'http://tellurium.analogmachine.org',
                exec_sedml_docs_in_combine_archive,
                environment_variables=environment_variables)


def main():
    with App() as app:
        app.run()

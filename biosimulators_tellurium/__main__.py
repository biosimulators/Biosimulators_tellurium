""" BioSimulators-compliant command-line interface to the `tellurium <http://tellurium.analogmachine.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ._version import __version__
from .core import exec_sedml_docs_in_combine_archive
from biosimulators_utils.simulator.cli import build_cli
import tellurium

App = build_cli('tellurium', __version__,
                'tellurium', tellurium.__version__, 'http://tellurium.analogmachine.org',
                exec_sedml_docs_in_combine_archive)


def main():
    with App() as app:
        app.run()

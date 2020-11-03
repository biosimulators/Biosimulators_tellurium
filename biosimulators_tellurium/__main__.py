""" BioSimulators-compliant command-line interface to the `tellurium <http://tellurium.analogmachine.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-10
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .core import exec_combine_archive
import Biosimulators_tellurium
import cement


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = ("BioSimulators-compliant command-line interface to the "
                       "tellurium simulation program <http://tellurium.analogmachine.org>.")
        help = "tellurium"
        arguments = [
            (['-i', '--archive'], dict(type=str,
                                       required=True,
                                       help='Path to OMEX file which contains one or more SED-ML-encoded simulation experiments')),
            (['-o', '--out-dir'], dict(type=str,
                                       default='.',
                                       help='Directory to save outputs')),
            (['-v', '--version'], dict(action='version',
                                       version=Biosimulators_tellurium.__version__)),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        exec_combine_archive(args.archive, args.out_dir)


class App(cement.App):
    """ Command line application """
    class Meta:
        label = 'tellurium'
        base_controller = 'base'
        handlers = [
            BaseController,
        ]


def main():
    with App() as app:
        app.run()

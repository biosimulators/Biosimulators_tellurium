""" BioSimulations-compliant command-line interface to the `tellurium <http://tellurium.analogmachine.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import Biosimulations_tellurium
import cement
import os
import tellurium
import tellurium.sedml.tesedml
import tesedml as libsedml


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = "BioSimulations-compliant command-line interface to the tellurium simulation program"
        help = "Biosimulations-tellurium"
        arguments = [
            (['-i', '--sim-file'], dict(type=str,
                                        required=True,
                                        help='Path to SED-ML file which describes a simulation experiment')),
            (['-o', '--out-dir'], dict(type=str,
                                       default='.',
                                       help='Directory to save outputs')),
            (['-v', '--version'], dict(action='version',
                                       version='{} (tellurium {})'.format(Biosimulations_tellurium.__version__, tellurium.__version__))),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs

        # validate SED-ML file
        sedml_doc = libsedml.readSedML(args.sim_file)
        if sedml_doc.getErrorLog().getNumFailsWithSeverity(libsedml.LIBSEDML_SEV_ERROR):
            SystemExit(sedml_doc.getErrorLog().toString())

        # set plotting engine
        tellurium.setDefaultPlottingEngine('matplotlib')

        # generate machinery to execute SED-ML
        with open(args.sim_file, 'r') as file:
            factory = tellurium.sedml.tesedml.SEDMLCodeFactory(
                file.read(),
                workingDir=os.path.dirname(args.sim_file),
                saveOutputs=True,
                outputDir=args.out_dir)
        factory.reportFormat = "csv"
        factory.plotFormat = "png"

        # execute SED-ML
        factory.executePython()


class App(cement.App):
    """ Command line application """
    class Meta:
        label = 'Biosimulations-tellurium'
        base_controller = 'base'
        handlers = [
            BaseController,
        ]


def main():
    with App() as app:
        app.run()

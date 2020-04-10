""" BioSimulations-compliant command-line interface to the `tellurium <http://tellurium.analogmachine.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import Biosimulations_tellurium
import cement
import importlib
import libcombine
import os
import shutil
import tellurium
import tellurium.sedml.tesedml
import tellurium.utils.omex
import tempfile
import warnings
import zipfile
importlib.reload(libcombine)


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = "BioSimulations-compliant command-line interface to the tellurium simulation program"
        help = "tellurium"
        arguments = [
            (['-i', '--in-archive'], dict(type=str,
                                          required=True,
                                          help='Path to OMEX file which contains one or more SED-ML-encoded simulation experiments')),
            (['-o', '--out-dir'], dict(type=str,
                                       default='.',
                                       help='Directory to save outputs')),
            (['-v', '--version'], dict(action='version',
                                       version='{} (tellurium {})'.format(Biosimulations_tellurium.__version__, tellurium.__version__))),
        ]
        PLOTTING_ENGINE = 'matplotlib'

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        omex_path = args.in_archive
        out_dir = args.out_dir

        # set plotting engine
        tellurium.setDefaultPlottingEngine(self.Meta.PLOTTING_ENGINE)

        # check that archive exists and is in zip format
        if not os.path.isfile(omex_path):
            raise FileNotFoundError("File does not exist: {}".format(omex_path))

        if not zipfile.is_zipfile(omex_path):
            raise IOError("File is not an OMEX Combine Archive in zip format: {}".format(omex_path))

        # extract files from archive and simulate
        try:
            tmp_dir = tempfile.mkdtemp()

            # extract archive
            tellurium.utils.omex.extractCombineArchive(omexPath=omex_path, directory=tmp_dir)

            # get locations of SED-ML files from manifest of archive
            sedml_locations = tellurium.utils.omex.getLocationsByFormat(omexPath=omex_path, formatKey="sed-ml", method="omex")
            if not sedml_locations:
                # if the manifest doesn't describe any SED-ML files, try to find files with the extension .sedml in the archive
                sedml_locations = tellurium.utils.omex.getLocationsByFormat(omexPath=omex_path, formatKey="sed-ml", method="zip")
                warnings.warn(("The manifest of the COMBINE archive does not describe any SED-ML files. "
                               "Nevertheless, the following SED-ML files were found in the archive:{}").format(
                    ''.join('\n  ' + loc for loc in sedml_locations)))

            # run all sedml files
            for sedml_location in sedml_locations:
                sedml_path = os.path.join(tmp_dir, sedml_location)
                sedml_out_dir = os.path.join(out_dir, os.path.splitext(sedml_location)[0])
                if not os.path.isdir(sedml_out_dir):
                    os.makedirs(sedml_out_dir)
                factory = tellurium.sedml.tesedml.SEDMLCodeFactory(sedml_path,
                                                                   workingDir=os.path.dirname(sedml_path),
                                                                   createOutputs=True,
                                                                   saveOutputs=True,
                                                                   outputDir=sedml_out_dir,
                                                                   )
                factory.executePython()
        finally:
            shutil.rmtree(tmp_dir)


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

""" Utility methods for working with tellurium to execute COMBINE/OMEX archives

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import PlottingEngine
from tellurium.sedml.tesedml import SEDMLCodeFactory
from tellurium.utils.omex import getLocationsByFormat
import os
import shutil
import tellurium
import warnings

__all__ = [
    'get_sedml_locations_in_combine_archive',
]


def get_sedml_locations_in_combine_archive(archive_filename):
    """ Get the locations of the SED-ML files in a COMBINE/OMEX archive

    Arg:
        archive_filename (:obj:`str`): path to a COMBINE/OMEX archive

    Returns:
        :obj:`list` of :obj:`str`: list of the locations within the archive which are SED-ML files
    """
    # get the locations of the SED-ML files from the manifest of the COMBINE/OMEX archive
    locations = getLocationsByFormat(omexPath=archive_filename, formatKey="sed-ml", method="omex")

    # if the manifest for the archive doesn't describe any SED-ML files, find the files in the archive
    # that have the extension ``.sedml``
    if not locations:
        locations = getLocationsByFormat(omexPath=archive_filename, formatKey="sed-ml", method="zip")
        msg = ("The manifest of the COMBINE archive does not describe any SED-ML files. "
               "Nevertheless, the following SED-ML files were found in the archive:{}").format(
            ''.join('\n  ' + loc for loc in locations))
        warnings.warn(msg, UserWarning)

    return locations


def exec_sed_doc(archive_dirname, sedml_location, out_dir, plotting_engine=PlottingEngine.matplotlib):
    """
    Args:
        plotting_engine (:obj:`PlottingEngine`, optional): engine for generating plots
    """
    # Set the engine that tellurim uses for plotting
    tellurium.setDefaultPlottingEngine(plotting_engine.value)

    # Get the full path to the SED-ML file
    sedml_path = os.path.join(archive_dirname, sedml_location)

    #
    sedml_out_dir = os.path.join(out_dir, sedml_location)

    # Create a directory to store the outputs of the SED-ML file
    # - Reports: CSV files (Rows: time, Columns: data sets)
    # - Plots: PDF files
    if not os.path.isdir(sedml_out_dir):
        os.makedirs(sedml_out_dir)

    try:
        factory = SEDMLCodeFactory(sedml_path,
                                   workingDir=os.path.dirname(sedml_path),
                                   createOutputs=True,
                                   saveOutputs=True,
                                   outputDir=sedml_out_dir,
                                   )
        factory.executePython()
    except Exception:
        # clean up the temporary directory for the contents of the COMBINE/OMEX archive
        shutil.rmtree(archive_dirname)

        # re-raise exception
        raise

    # Convert the outputs to the BioSimulators formats
    # sedml_id = os.path.relpath(sedml_location, '.')

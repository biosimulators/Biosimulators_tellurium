""" Methods for using tellurium to execute SED tasks in COMBINE/OMEX archives and save their outputs

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import PlottingEngine
from .utils import get_sedml_locations_in_combine_archive, exec_sed_doc
import os
import shutil
import tellurium
import tellurium.sedml.tesedml
import tellurium.utils.omex
import tempfile
import zipfile

import libsedml
import importlib
importlib.reload(libsedml)


__all__ = ['exec_sedml_docs_in_combine_archive']


def exec_sedml_docs_in_combine_archive(archive_filename, out_dir,
                                       report_formats=None, plot_formats=None,
                                       bundle_outputs=None, keep_individual_outputs=None,
                                       plotting_engine=PlottingEngine.matplotlib):
    """ Execute the SED tasks defined in a COMBINE/OMEX archive and save the outputs

    Args:
        archive_filename (:obj:`str`): path to COMBINE/OMEX archive
        out_dir (:obj:`str`): path to store the outputs of the archive

            * CSV: directory in which to save outputs to files
              ``{ out_dir }/{ relative-path-to-SED-ML-file-within-archive }/{ report.id }.csv``
            * HDF5: directory in which to save a single HDF5 file (``{ out_dir }/reports.h5``),
              with reports at keys ``{ relative-path-to-SED-ML-file-within-archive }/{ report.id }`` within the HDF5 file

        report_formats (:obj:`list` of :obj:`ReportFormat`, optional): report format (e.g., csv or h5)
        plot_formats (:obj:`list` of :obj:`PlotFormat`, optional): report format (e.g., pdf)
        bundle_outputs (:obj:`bool`, optional): if :obj:`True`, bundle outputs into archives for reports and plots
        keep_individual_outputs (:obj:`bool`, optional): if :obj:`True`, keep individual output files
        plotting_engine (:obj:`PlottingEngine`, optional): engine for generating plots
    """
    # Check that the COMBINE/OMEX archive exists, and that it is in zip format
    if not os.path.isfile(archive_filename):
        raise FileNotFoundError("The COMBINE/OMEX archive file `{}` does not exist".format(archive_filename))

    if not zipfile.is_zipfile(archive_filename):
        raise IOError("COMBINE/OMEX archive `{}` is not in the zip format".format(archive_filename))

    # Create a temporary directory for the contents of the COMBINE/OMEX archive
    archive_dirname = tempfile.mkdtemp()

    # Extract the contents of the COMBINE/OMEX archive
    tellurium.utils.omex.extractCombineArchive(omexPath=archive_filename, directory=archive_dirname)

    # Get the locations of the SED-ML files within the COMBINE/OMEX archive
    sedml_locations = get_sedml_locations_in_combine_archive(archive_filename)

    # Execute each SED-ML file
    for sedml_location in sedml_locations:
        exec_sed_doc(archive_dirname, sedml_location, out_dir, plotting_engine)

    # bundle the outputs of the SED-ML files
    # TODO

    # clean up the temporary directory for the contents of the COMBINE/OMEX archive
    shutil.rmtree(archive_dirname)

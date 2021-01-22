""" Methods for using tellurium to execute SED tasks in COMBINE/OMEX archives and save their outputs

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
from biosimulators_utils.combine.exec import exec_sedml_docs_in_archive
from biosimulators_utils.log.data_model import Status, CombineArchiveLog, SedDocumentLog  # noqa: F401
from biosimulators_utils.plot.data_model import PlotFormat  # noqa: F401
from biosimulators_utils.report.data_model import DataSetResults, ReportResults, ReportFormat  # noqa: F401
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface
from biosimulators_utils.sedml.io import SedmlSimulationReader
from tellurium.sedml.tesedml import SEDMLCodeFactory
import glob
import os
import pandas
import shutil
import tellurium
import tempfile


__all__ = ['exec_sedml_docs_in_combine_archive']


def exec_sedml_docs_in_combine_archive(archive_filename, out_dir,
                                       report_formats=None, plot_formats=None,
                                       bundle_outputs=None, keep_individual_outputs=None):
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

    Returns:
        :obj:`CombineArchiveLog`: log
    """
    return exec_sedml_docs_in_archive(
        exec_sed_doc, archive_filename, out_dir,
        apply_xml_model_changes=True,
        sed_doc_executer_supported_features=(Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface),
        report_formats=report_formats,
        plot_formats=plot_formats,
        bundle_outputs=bundle_outputs,
        keep_individual_outputs=keep_individual_outputs,
        sed_doc_executer_logged_features=(),
    )


def exec_sed_doc(filename, working_dir, base_out_path, rel_out_path=None,
                 apply_xml_model_changes=True, report_formats=None, plot_formats=None,
                 log=None, indent=0):
    """
    Args:
        filename (:obj:`str`): a path to SED-ML file which defines a SED document
        working_dir (:obj:`str`): working directory of the SED document (path relative to which models are located)

        out_path (:obj:`str`): path to store the outputs

            * CSV: directory in which to save outputs to files
              ``{out_path}/{rel_out_path}/{report.id}.csv``
            * HDF5: directory in which to save a single HDF5 file (``{out_path}/reports.h5``),
              with reports at keys ``{rel_out_path}/{report.id}`` within the HDF5 file

        rel_out_path (:obj:`str`, optional): path relative to :obj:`out_path` to store the outputs
        apply_xml_model_changes (:obj:`bool`, optional): if :obj:`True`, apply any model changes specified in the SED-ML file before
            calling :obj:`task_executer`.
        report_formats (:obj:`list` of :obj:`ReportFormat`, optional): report format (e.g., csv or h5)
        plot_formats (:obj:`list` of :obj:`PlotFormat`, optional): plot format (e.g., pdf)
        log (:obj:`SedDocumentLog`, optional): execution status of document
        indent (:obj:`int`, optional): degree to indent status messages

    Returns:
        :obj:`ReportResults`: results of each report
    """
    # Set the engine that tellurium uses for plotting
    tellurium.setDefaultPlottingEngine(Config().plotting_engine.value)

    # Create a temporary for tellurium's outputs
    # - Reports: CSV (Rows: time, Columns: data sets)
    # - Plots: PDF
    tmp_out_dir = tempfile.mkdtemp()

    # Use tellurium to execute the SED document and generate the specified outputs
    try:
        factory = SEDMLCodeFactory(filename,
                                   workingDir=working_dir,
                                   createOutputs=True,
                                   saveOutputs=True,
                                   outputDir=tmp_out_dir,
                                   )
        for plot_format in (plot_formats or [PlotFormat.pdf]):
            factory.reportFormat = 'csv'
            factory.plotFormat = plot_format.value
            factory.executePython()
    except Exception:
        shutil.rmtree(tmp_out_dir)
        raise

    # Convert tellurium's CSV reports to the desired BioSimulators format(s)
    # - Transpose rows/columns
    # - Encode into BioSimulators format(s)
    doc = SedmlSimulationReader().run(filename)
    report_results = ReportResults()
    for report_filename in glob.glob(os.path.join(tmp_out_dir, '*.csv')):
        report_id = os.path.splitext(os.path.basename(report_filename))[0]

        # read report from CSV file produced by tellurium
        data_set_df = pandas.read_csv(report_filename).transpose()

        # create pseudo-report for ReportWriter
        report = next(report for report in doc.outputs if report.id == report_id)
        data_set_results = DataSetResults()
        for data_set in report.data_sets:
            data_set_results[data_set.id] = data_set_df.loc[data_set.label, :].to_numpy()

        # append to data structure of report results
        report_results[report_id] = data_set_results

        # save file in desired BioSimulators format(s)
        for report_format in report_formats:
            ReportWriter().run(report,
                               data_set_results,
                               base_out_path,
                               os.path.join(rel_out_path, report_id) if rel_out_path else report_id,
                               format=report_format)

    # Move the plot outputs to the permanent output directory
    out_dir = base_out_path
    if rel_out_path:
        out_dir = os.path.join(out_dir, rel_out_path)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    for plot_format in plot_formats:
        for plot_filename in glob.glob(os.path.join(tmp_out_dir, '*.' + plot_format.value)):
            shutil.move(plot_filename, out_dir)

    # Clean up the temporary directory for tellurium's outputs
    shutil.rmtree(tmp_out_dir)

    # Return a data structure with the results of the reports
    return report_results

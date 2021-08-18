""" Methods for using tellurium to execute SED tasks in COMBINE/OMEX archives and save their outputs

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
from biosimulators_utils.combine.exec import exec_sedml_docs_in_archive
from biosimulators_utils.log.data_model import Status, CombineArchiveLog, SedDocumentLog, StandardOutputErrorCapturerLevel  # noqa: F401
from biosimulators_utils.log.utils import init_sed_document_log, StandardOutputErrorCapturer
from biosimulators_utils.viz.data_model import VizFormat  # noqa: F401
from biosimulators_utils.report.data_model import DataSetResults, ReportResults, ReportFormat, SedDocumentResults  # noqa: F401
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface
from biosimulators_utils.sedml.io import SedmlSimulationReader, SedmlSimulationWriter
from tellurium.sedml.tesedml import SEDMLCodeFactory
import datetime
import glob
import os
import pandas
import shutil
import tellurium
import tempfile
import tellurium.sedml.tesedml


# correct KISAO to parameter mapping
tellurium.sedml.tesedml.KISAOS_ALGORITHMPARAMETERS[656] = ('variable_step_size', bool)


__all__ = ['exec_sedml_docs_in_combine_archive']


def exec_sedml_docs_in_combine_archive(archive_filename, out_dir,
                                       return_results=False,
                                       report_formats=None, plot_formats=None,
                                       bundle_outputs=None, keep_individual_outputs=None,
                                       raise_exceptions=True):
    """ Execute the SED tasks defined in a COMBINE/OMEX archive and save the outputs

    Args:
        archive_filename (:obj:`str`): path to COMBINE/OMEX archive
        out_dir (:obj:`str`): path to store the outputs of the archive

            * CSV: directory in which to save outputs to files
              ``{ out_dir }/{ relative-path-to-SED-ML-file-within-archive }/{ report.id }.csv``
            * HDF5: directory in which to save a single HDF5 file (``{ out_dir }/reports.h5``),
              with reports at keys ``{ relative-path-to-SED-ML-file-within-archive }/{ report.id }`` within the HDF5 file

        return_results (:obj:`bool`, optional): whether to return the result of each output of each SED-ML file
        report_formats (:obj:`list` of :obj:`ReportFormat`, optional): report format (e.g., csv or h5)
        plot_formats (:obj:`list` of :obj:`VizFormat`, optional): report format (e.g., pdf)
        bundle_outputs (:obj:`bool`, optional): if :obj:`True`, bundle outputs into archives for reports and plots
        keep_individual_outputs (:obj:`bool`, optional): if :obj:`True`, keep individual output files
        raise_exceptions (:obj:`bool`, optional): whether to raise exceptions

    Returns:
        :obj:`tuple`:

            * :obj:`SedDocumentResults`: results
            * :obj:`CombineArchiveLog`: log
    """
    return exec_sedml_docs_in_archive(
        exec_sed_doc, archive_filename, out_dir,
        apply_xml_model_changes=True,
        return_results=return_results,
        sed_doc_executer_supported_features=(Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface),
        report_formats=report_formats,
        plot_formats=plot_formats,
        bundle_outputs=bundle_outputs,
        keep_individual_outputs=keep_individual_outputs,
        sed_doc_executer_logged_features=(Report, Plot2D, Plot3D),
        raise_exceptions=raise_exceptions,
    )


def exec_sed_doc(filename, working_dir, base_out_path, rel_out_path=None,
                 apply_xml_model_changes=True, return_results=True, report_formats=None, plot_formats=None,
                 log=None, indent=0, log_level=StandardOutputErrorCapturerLevel.c):
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
        return_results (:obj:`bool`, optional): whether to return the result of each output of each SED-ML file
        report_formats (:obj:`list` of :obj:`ReportFormat`, optional): report format (e.g., csv or h5)
        plot_formats (:obj:`list` of :obj:`VizFormat`, optional): plot format (e.g., pdf)
        log (:obj:`SedDocumentLog`, optional): execution status of document
        indent (:obj:`int`, optional): degree to indent status messages
        log_level (:obj:`StandardOutputErrorCapturerLevel`, optional): level at which to log output

    Returns:
        :obj:`tuple`:

            * :obj:`ReportResults`: results of each report
            * :obj:`SedDocumentLog`: log of the document
    """
    doc = SedmlSimulationReader().run(filename)

    if not log:
        log = init_sed_document_log(doc)
    start_time = datetime.datetime.now()

    # Set the engine that tellurium uses for plotting
    tellurium.setDefaultPlottingEngine(Config().plotting_engine.value)

    # Create a temporary for tellurium's outputs
    # - Reports: CSV (Rows: time, Columns: data sets)
    # - Plots: PDF
    tmp_out_dir = tempfile.mkdtemp()

    # add a report for each plot to make tellurium output the data for each plot
    for output in doc.outputs:
        if isinstance(output, (Plot2D, Plot3D)):
            report = Report(
                id='__plot__' + output.id,
                name=output.name)

            data_generators = {}
            if isinstance(output, Plot2D):
                for curve in output.curves:
                    data_generators[curve.x_data_generator.id] = curve.x_data_generator
                    data_generators[curve.y_data_generator.id] = curve.y_data_generator

            elif isinstance(output, Plot3D):
                for surface in output.surfaces:
                    data_generators[surface.x_data_generator.id] = surface.x_data_generator
                    data_generators[surface.y_data_generator.id] = surface.y_data_generator
                    data_generators[surface.z_data_generator.id] = surface.z_data_generator

            for data_generator in data_generators.values():
                report.data_sets.append(DataSet(
                    id='__data_set__{}_{}'.format(output.id, data_generator.id),
                    name=data_generator.name,
                    label=data_generator.id,
                    data_generator=data_generator,
                ))

            report.data_sets.sort(key=lambda data_set: data_set.id)
            doc.outputs.append(report)

    filename_with_reports_for_plots = os.path.join(tmp_out_dir, 'simulation.sedml')
    SedmlSimulationWriter().run(doc, filename_with_reports_for_plots, validate_models_with_languages=False)

    # Use tellurium to execute the SED document and generate the specified outputs
    with StandardOutputErrorCapturer(relay=False, level=log_level) as captured:
        try:
            factory = SEDMLCodeFactory(filename_with_reports_for_plots,
                                       workingDir=working_dir,
                                       createOutputs=True,
                                       saveOutputs=True,
                                       outputDir=tmp_out_dir,
                                       )
            for plot_format in (plot_formats or [VizFormat.pdf]):
                factory.reportFormat = 'csv'
                factory.plotFormat = plot_format.value
                factory.executePython()

            log.output = captured.get_text()
            log.export()

        except Exception as exception:
            log.status = Status.FAILED
            log.exception = exception
            log.duration = (datetime.datetime.now() - start_time).total_seconds()
            log.output = captured.get_text()
            for output in log.outputs.values():
                output.status = Status.SKIPPED
            log.export()
            shutil.rmtree(tmp_out_dir)
            raise

    # Convert tellurium's CSV reports to the desired BioSimulators format(s)
    # - Transpose rows/columns
    # - Encode into BioSimulators format(s)
    if return_results:
        report_results = ReportResults()
    else:
        report_results = None

    for report_filename in glob.glob(os.path.join(tmp_out_dir, '*.csv')):
        report_id = os.path.splitext(os.path.basename(report_filename))[0]
        is_plot = report_id.startswith('__plot__')
        if is_plot:
            output_id = report_id[len('__plot__'):]
        else:
            output_id = report_id

        log.outputs[output_id].status = Status.RUNNING
        log.export()
        output_start_time = datetime.datetime.now()

        # read report from CSV file produced by tellurium
        data_set_df = pandas.read_csv(report_filename).transpose()

        # create pseudo-report for ReportWriter
        output = next(output for output in doc.outputs if output.id == report_id)
        if is_plot:
            output.id = output_id
        data_set_results = DataSetResults()
        for data_set in output.data_sets:
            if is_plot:
                data_set.id = data_set.id[len('__data_set__{}_'.format(output_id)):]
            data_set_results[data_set.id] = data_set_df.loc[data_set.label, :].to_numpy()

        # append to data structure of report results
        if return_results:
            report_results[output_id] = data_set_results

        # save file in desired BioSimulators format(s)
        for report_format in report_formats:
            ReportWriter().run(output,
                               data_set_results,
                               base_out_path,
                               os.path.join(rel_out_path, output_id) if rel_out_path else output_id,
                               format=report_format)

        log.outputs[output_id].status = Status.SUCCEEDED
        log.outputs[output_id].duration = (datetime.datetime.now() - output_start_time).total_seconds()
        log.export()

    # Move the plot outputs to the permanent output directory
    out_dir = base_out_path
    if rel_out_path:
        out_dir = os.path.join(out_dir, rel_out_path)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    for plot_format in plot_formats:
        for plot_filename in glob.glob(os.path.join(tmp_out_dir, '*.' + plot_format.value)):
            shutil.move(plot_filename, out_dir)

    # finalize log
    log.status = Status.SUCCEEDED
    log.duration = (datetime.datetime.now() - start_time).total_seconds()
    log.export()

    # Clean up the temporary directory for tellurium's outputs
    shutil.rmtree(tmp_out_dir)

    # Return a data structure with the results of the reports
    return report_results, log

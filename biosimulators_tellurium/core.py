""" Methods for using tellurium to execute SED tasks in COMBINE/OMEX archives and save their outputs

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config as SimulatorConfig
from .data_model import SedmlInterpreter, KISAO_ALGORITHM_MAP, PreprocesssedTask
from biosimulators_utils.combine.exec import exec_sedml_docs_in_archive
from biosimulators_utils.config import get_config, Config  # noqa: F401
from biosimulators_utils.log.data_model import Status, CombineArchiveLog, SedDocumentLog, StandardOutputErrorCapturerLevel, TaskLog  # noqa: F401
from biosimulators_utils.log.utils import init_sed_document_log, StandardOutputErrorCapturer
from biosimulators_utils.viz.data_model import VizFormat  # noqa: F401
from biosimulators_utils.report.data_model import DataSetResults, ReportResults, ReportFormat, SedDocumentResults, VariableResults  # noqa: F401
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml import exec as sedml_exec
from biosimulators_utils.sedml import validation
from biosimulators_utils.sedml.data_model import (
    Task, RepeatedTask, ModelLanguage, ModelAttributeChange, ComputeModelChange, SteadyStateSimulation, UniformTimeCourseSimulation,
    Symbol, Report, DataSet, Plot2D, Curve, Plot3D, Surface)
from biosimulators_utils.sedml.io import SedmlSimulationReader, SedmlSimulationWriter
from biosimulators_utils.simulator.utils import get_algorithm_substitution_policy
from biosimulators_utils.utils.core import raise_errors_warnings, validate_str_value, parse_value
from biosimulators_utils.warnings import warn, BioSimulatorsWarning
from kisao.data_model import AlgorithmSubstitutionPolicy, ALGORITHM_SUBSTITUTION_POLICY_LEVELS
from kisao.utils import get_preferred_substitute_algorithm_by_ids
from tellurium.sedml.tesedml import SEDMLCodeFactory
import copy
import datetime
import functools
import glob
import lxml.etree
import numpy
import os
import pandas
import shutil
import tellurium
import tempfile
import tellurium.sedml.tesedml
import roadrunner


__all__ = [
    'exec_sedml_docs_in_combine_archive',
    'exec_sed_doc',
    'exec_sed_task',
    'preprocess_sed_task',
]


def exec_sedml_docs_in_combine_archive(archive_filename, out_dir, config=None, simulator_config=None):
    """ Execute the SED tasks defined in a COMBINE/OMEX archive and save the outputs

    Args:
        archive_filename (:obj:`str`): path to COMBINE/OMEX archive
        out_dir (:obj:`str`): path to store the outputs of the archive

            * CSV: directory in which to save outputs to files
              ``{ out_dir }/{ relative-path-to-SED-ML-file-within-archive }/{ report.id }.csv``
            * HDF5: directory in which to save a single HDF5 file (``{ out_dir }/reports.h5``),
              with reports at keys ``{ relative-path-to-SED-ML-file-within-archive }/{ report.id }`` within the HDF5 file

        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`tuple`:

            * :obj:`SedDocumentResults`: results
            * :obj:`CombineArchiveLog`: log
    """
    if not simulator_config:
        simulator_config = SimulatorConfig()
    sedml_interpreter = simulator_config.sedml_interpreter

    if sedml_interpreter == SedmlInterpreter.biosimulators:
        apply_xml_model_changes = True
        sed_doc_executer_logged_features = (Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface)
    else:
        apply_xml_model_changes = False
        sed_doc_executer_logged_features = (Report, Plot2D, Plot3D)

    return exec_sedml_docs_in_archive(
        functools.partial(exec_sed_doc, simulator_config=simulator_config),
        archive_filename, out_dir,
        apply_xml_model_changes=apply_xml_model_changes,
        sed_doc_executer_supported_features=(Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface),
        sed_doc_executer_logged_features=sed_doc_executer_logged_features,
        config=config,
    )


def exec_sed_doc(doc, working_dir, base_out_path, rel_out_path=None,
                 apply_xml_model_changes=False,
                 log=None, indent=0, pretty_print_modified_xml_models=False,
                 log_level=StandardOutputErrorCapturerLevel.c, config=None, simulator_config=None):
    """ Execute the tasks specified in a SED document and generate the specified outputs

    Args:
        doc (:obj:`SedDocument` or :obj:`str`): SED document or a path to SED-ML file which defines a SED document
        working_dir (:obj:`str`): working directory of the SED document (path relative to which models are located)

        base_out_path (:obj:`str`): path to store the outputs

            * CSV: directory in which to save outputs to files
              ``{base_out_path}/{rel_out_path}/{report.id}.csv``
            * HDF5: directory in which to save a single HDF5 file (``{base_out_path}/reports.h5``),
              with reports at keys ``{rel_out_path}/{report.id}`` within the HDF5 file

        rel_out_path (:obj:`str`, optional): path relative to :obj:`base_out_path` to store the outputs
        apply_xml_model_changes (:obj:`bool`, optional): if :obj:`True`, apply any model changes specified in the SED-ML file before
            calling :obj:`task_executer`.
        log (:obj:`SedDocumentLog`, optional): log of the document
        indent (:obj:`int`, optional): degree to indent status messages
        pretty_print_modified_xml_models (:obj:`bool`, optional): if :obj:`True`, pretty print modified XML models
        log_level (:obj:`StandardOutputErrorCapturerLevel`, optional): level at which to log output
        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`tuple`:

            * :obj:`ReportResults`: results of each report
            * :obj:`SedDocumentLog`: log of the document
    """
    if not simulator_config:
        simulator_config = SimulatorConfig()
    sedml_interpreter = simulator_config.sedml_interpreter

    if sedml_interpreter == SedmlInterpreter.biosimulators:
        return exec_sed_doc_with_biosimulators(
            doc, working_dir, base_out_path,
            rel_out_path=rel_out_path,
            apply_xml_model_changes=apply_xml_model_changes,
            log=log,
            indent=indent,
            pretty_print_modified_xml_models=pretty_print_modified_xml_models,
            log_level=log_level,
            config=config,
            simulator_config=simulator_config)

    elif sedml_interpreter == SedmlInterpreter.tellurium:
        return exec_sed_doc_with_tellurium(
            doc, working_dir, base_out_path,
            rel_out_path=rel_out_path,
            apply_xml_model_changes=apply_xml_model_changes,
            log=log,
            indent=indent,
            pretty_print_modified_xml_models=pretty_print_modified_xml_models,
            log_level=log_level,
            config=config,
            simulator_config=simulator_config)

    else:
        raise NotImplementedError('`{}` is not a supported SED-ML interpreter.'.format(sedml_interpreter))


def exec_sed_doc_with_biosimulators(doc, working_dir, base_out_path, rel_out_path=None,
                                    apply_xml_model_changes=False,
                                    log=None, indent=0, pretty_print_modified_xml_models=False,
                                    log_level=StandardOutputErrorCapturerLevel.c, config=None, simulator_config=None):
    """ Execute the tasks specified in a SED document and generate the specified outputs

    Args:
        doc (:obj:`SedDocument` or :obj:`str`): SED document or a path to SED-ML file which defines a SED document
        working_dir (:obj:`str`): working directory of the SED document (path relative to which models are located)
        base_out_path (:obj:`str`): path to store the outputs

            * CSV: directory in which to save outputs to files
              ``{base_out_path}/{rel_out_path}/{report.id}.csv``
            * HDF5: directory in which to save a single HDF5 file (``{base_out_path}/reports.h5``),
              with reports at keys ``{rel_out_path}/{report.id}`` within the HDF5 file

        rel_out_path (:obj:`str`, optional): path relative to :obj:`base_out_path` to store the outputs
        apply_xml_model_changes (:obj:`bool`, optional): if :obj:`True`, apply any model changes specified in the SED-ML file before
            calling :obj:`task_executer`.
        log (:obj:`SedDocumentLog`, optional): log of the document
        indent (:obj:`int`, optional): degree to indent status messages
        pretty_print_modified_xml_models (:obj:`bool`, optional): if :obj:`True`, pretty print modified XML models
        log_level (:obj:`StandardOutputErrorCapturerLevel`, optional): level at which to log output
        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`tuple`:

            * :obj:`ReportResults`: results of each report
            * :obj:`SedDocumentLog`: log of the document
    """
    if not simulator_config:
        simulator_config = SimulatorConfig()
    else:
        simulator_config = copy.copy(simulator_config)
    simulator_config.sedml_interpreter = SedmlInterpreter.biosimulators

    sed_task_executer = functools.partial(exec_sed_task, simulator_config=simulator_config)
    # The value_executer's don't need the simulator_config.
    # get_value_executer = functools.partial(get_model_variable_value, simulator_config=simulator_config)
    # set_value_executer = functools.partial(set_model_variable_value, simulator_config=simulator_config)
    preprocessed_task_executer = functools.partial(preprocess_sed_task, simulator_config=simulator_config)
    return sedml_exec.exec_sed_doc(sed_task_executer, doc, working_dir, base_out_path,
                                   rel_out_path=rel_out_path,
                                   apply_xml_model_changes=True,
                                   log=log,
                                   indent=indent,
                                   pretty_print_modified_xml_models=pretty_print_modified_xml_models,
                                   log_level=log_level,
                                   config=config,
                                   get_value_executer=get_model_variable_value,
                                   set_value_executer=set_model_variable_value,
                                   preprocessed_task_executer=preprocessed_task_executer,
                                   reset_executer=reset_all_models)


def exec_sed_task(task, variables, preprocessed_task=None, log=None, config=None, simulator_config=None):
    ''' Execute a task and save its results

    Args:
        task (:obj:`Task`): task
        variables (:obj:`list` of :obj:`Variable`): variables that should be recorded
        preprocessed_task (:obj:`PreprocessedTask`, optional): preprocessed information about the task, including possible
            model changes and variables. This can be used to avoid repeatedly executing the same initialization for repeated
            calls to this method.
        log (:obj:`TaskLog`, optional): log for the task
        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`tuple`:

            :obj:`VariableResults`: results of variables
            :obj:`TaskLog`: log

    Raises:
        :obj:`ValueError`: if the task or an aspect of the task is not valid, or the requested output variables
            could not be recorded
        :obj:`NotImplementedError`: if the task is not of a supported type or involves an unsuported feature
    '''
    if not config:
        config = get_config()

    if config.LOG and not log:
        log = TaskLog()

    if preprocessed_task is None:
        preprocessed_task = preprocess_sed_task(task, variables, config=config, simulator_config=simulator_config)

    model = task.model
    sim = task.simulation
    road_runner = preprocessed_task.road_runners[task.id]

    # apply model changes
    if model.changes:
        raise_errors_warnings(validation.validate_model_change_types(model.changes, (ModelAttributeChange, ComputeModelChange, )),
                              error_summary='Task changes for model ' + model.id
                              + ' that are not attribute changes or compute model changes are not supported.')
        for change in model.changes:
            component_id = preprocessed_task.model_change_target_tellurium_id_maps[task.id][(change.model, change.target, change.symbol)]
            new_value = float(change.new_value)
            road_runner[component_id] = new_value

    # simulate
    if isinstance(sim, UniformTimeCourseSimulation):
        if sim.initial_time < sim.output_start_time:
            number_of_presim_points = (sim.output_end_time - sim.initial_time) / \
                (sim.output_end_time - sim.output_start_time) * sim.number_of_steps + 1

            number_of_presim_points = round(number_of_presim_points) - sim.number_of_steps
            number_of_presim_points = max(2, number_of_presim_points)
            road_runner.simulate(sim.initial_time, sim.output_start_time, number_of_presim_points)

        results = numpy.array(road_runner.simulate(sim.output_start_time, sim.output_end_time, sim.number_of_steps+1).tolist()).transpose()
    else:
        results = None
        simdists = [0, 0.1, 1, 10, 100, 1000]
        sd = 0
        lasterr = ""
        while sd < len(simdists) and results is None:
            try:
                if simdists[sd] > 0:
                    road_runner.resetAll()
                    if model.changes:
                        for change in model.changes:
                            component_id = preprocessed_task.model_change_target_tellurium_id_maps[task.id][(change.model,
                                                                                                             change.target,
                                                                                                             change.symbol)]
                            new_value = float(change.new_value)
                            road_runner[component_id] = new_value
                    road_runner.simulate(end=simdists[sd])
                road_runner.steadyState()
                results = road_runner.getSteadyStateValues()
            except Exception as e:
                lasterr = str(e)
            sd += 1
        if results is None:
            msg = 'Steady state analysis failed with algorithm `{}` ({}):'.format(
                preprocessed_task.algorithm_kisao_ids[task.id],
                KISAO_ALGORITHM_MAP[preprocessed_task.algorithm_kisao_ids[task.id]]['id'])
            msg += "\n   '" + lasterr + "'"
            for i_param in range(preprocessed_task.solvers[task.id].getNumParams()):
                param_name = preprocessed_task.solvers[task.id].getParamName(i_param)
                msg += '\n  - {}: {}'.format(param_name, getattr(preprocessed_task.solvers[task.id], param_name))
            raise ValueError(msg)

    # check simulation succeeded
    if config.VALIDATE_RESULTS and numpy.any(numpy.isnan(results)):
        msg = 'Simulation failed: ' + str(numpy.count_nonzero(numpy.isnan(results))) +\
              ' nan value(s) found in results with algorithm `{}` ({})'.format(
            preprocessed_task.algorithm_kisao_ids[task.id],
            KISAO_ALGORITHM_MAP[preprocessed_task.algorithm_kisao_ids[task.id]]['id'])
        for i_param in range(preprocessed_task.solvers[task.id].getNumParams()):
            param_name = preprocessed_task.solvers[task.id].getParamName(i_param)
            msg += '\n  - {}: {}'.format(param_name, getattr(preprocessed_task.solvers[task.id], param_name))
        raise ValueError(msg)

    # record results
    variable_results = VariableResults()
    for variable, result in zip(variables, results):
        if isinstance(sim, UniformTimeCourseSimulation):
            result = result[-(sim.number_of_points + 1):]

        variable_results[variable.id] = result

    # log action
    if config.LOG:
        log.algorithm = preprocessed_task.algorithm_kisao_ids[task.id]
        log.simulator_details = {
            'method': 'simulate' if isinstance(sim, UniformTimeCourseSimulation) else 'steadyState',
            'solver': preprocessed_task.solvers[task.id].getName(),
        }
        for i_param in range(preprocessed_task.solvers[task.id].getNumParams()):
            param_name = preprocessed_task.solvers[task.id].getParamName(i_param)
            log.simulator_details[param_name] = getattr(preprocessed_task.solvers[task.id], param_name)

    # return results and log
    return variable_results, log


def get_all_tasks_from_task(task):
    ret = set()
    if isinstance(task, Task):
        ret.add(task)
        return ret
    elif isinstance(task, RepeatedTask):
        for sub_task in task.sub_tasks:
            subtasks = get_all_tasks_from_task(sub_task.task)
            ret.update(subtasks)
        return ret
    else:
        raise NotImplementedError("Tasks other than 'Task' or 'RepeatedTask' are not supported.")


def get_all_task_changes_from_task(task):
    ret = set()
    if isinstance(task, Task):
        return ret
    elif isinstance(task, RepeatedTask):
        ret.update(task.changes)
        for sub_task in task.sub_tasks:
            subtask_changes = get_all_task_changes_from_task(sub_task.task)
            ret.update(subtask_changes)
        return ret
    else:
        raise NotImplementedError("Tasks other than 'Task' or 'RepeatedTask' are not supported.")


def reset_all_models(preprocessed_task):
    for taskid in preprocessed_task.road_runners:
        preprocessed_task.road_runners[taskid].resetAll()


def preprocess_sed_task(task, variables, config=None, simulator_config=None):
    """ Preprocess a SED task, including its possible model changes and variables. This is useful for avoiding
    repeatedly initializing tasks on repeated calls of :obj:`exec_sed_task`.

    Args:
        task (:obj:`Task`): task
        variables (:obj:`list` of :obj:`Variable`): variables that should be recorded
        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`PreprocessedTask`: preprocessed information about the task
    """
    if not simulator_config:
        simulator_config = SimulatorConfig()
    sedml_interpreter = simulator_config.sedml_interpreter

    if sedml_interpreter != SedmlInterpreter.biosimulators:
        raise NotImplementedError('`{}` is not a supported SED-ML interpreter.'.format(sedml_interpreter))

    if not config:
        config = get_config()

    alltasks = get_all_tasks_from_task(task)
    alltaskchanges = get_all_task_changes_from_task(task)

    if config.VALIDATE_SEDML:
        for subtask in alltasks:
            model = subtask.model
            sim = subtask.simulation
            raise_errors_warnings(validation.validate_task(subtask),
                                  error_summary='Task `{}` is invalid.'.format(task.id))
            raise_errors_warnings(validation.validate_model_language(model.language, ModelLanguage.SBML),
                                  error_summary='Language for model `{}` is not supported.'.format(model.id))
            raise_errors_warnings(*validation.validate_model_changes(subtask.model),
                                  error_summary='Changes for model `{}` are invalid.'.format(model.id))
            raise_errors_warnings(validation.validate_simulation_type(sim, (SteadyStateSimulation, UniformTimeCourseSimulation)),
                                  error_summary='{} `{}` is not supported.'.format(sim.__class__.__name__, sim.id))
            raise_errors_warnings(*validation.validate_simulation(sim),
                                  error_summary='Simulation `{}` is invalid.'.format(sim.id))
            raise_errors_warnings(*validation.validate_data_generator_variables(variables),
                                  error_summary='Data generator variables for task `{}` are invalid.'.format(subtask.id))

    allroadrunners = {}
    model_change_target_tellurium_id_maps = {}
    exec_alg_kisao_ids = {}
    variable_target_tellurium_observable_maps = {}
    solvers = {}
    for subtasks in alltasks:
        model = subtask.model
        allchanges = model.changes + list(alltaskchanges)
        sim = subtask.simulation
        model_etree = lxml.etree.parse(model.source)

        if config.VALIDATE_SEDML_MODELS:
            raise_errors_warnings(*validation.validate_model(model, [], working_dir='.'),
                                  error_summary='Model `{}` is invalid.'.format(model.id),
                                  warning_summary='Model `{}` may be invalid.'.format(model.id))

        # read model
        road_runner = roadrunner.RoadRunner()
        road_runner = roadrunner.RoadRunner(road_runner.getParamPromotedSBML(model.source))

        # get algorithm to execute
        algorithm_substitution_policy = get_algorithm_substitution_policy(config=config)
        exec_alg_kisao_id = get_preferred_substitute_algorithm_by_ids(
            sim.algorithm.kisao_id, KISAO_ALGORITHM_MAP.keys(),
            substitution_policy=algorithm_substitution_policy)
        alg_props = KISAO_ALGORITHM_MAP[exec_alg_kisao_id]

        if alg_props['id'] == 'nleq2':
            solver = road_runner.getSteadyStateSolver()
            if config.VALIDATE_SEDML:
                raise_errors_warnings(validation.validate_simulation_type(sim, (SteadyStateSimulation,)),
                                      error_summary='{} `{}` is not supported.'.format(sim.__class__.__name__, sim.id))

        else:
            road_runner.setIntegrator(alg_props['id'])
            solver = road_runner.getIntegrator()
            if config.VALIDATE_SEDML:
                raise_errors_warnings(validation.validate_simulation_type(sim, (UniformTimeCourseSimulation,)),
                                      error_summary='{} `{}` is not supported.'.format(sim.__class__.__name__, sim.id))

        # set the parameters of the solver
        for change in sim.algorithm.changes:
            param_props = alg_props['parameters'].get(change.kisao_id, None)
            if not config.VALIDATE_SEDML or param_props:
                if not config.VALIDATE_SEDML or validate_str_value(change.new_value, param_props['type']):
                    new_value = parse_value(change.new_value, param_props['type'])
                    att = param_props['id']
                    if "roadrunner_attribute" in param_props:
                        att = param_props['roadrunner_attribute']
                    setattr(solver, att, new_value)

                else:
                    if (
                        exec_alg_kisao_id == sim.algorithm.kisao_id and
                        ALGORITHM_SUBSTITUTION_POLICY_LEVELS[algorithm_substitution_policy]
                        <= ALGORITHM_SUBSTITUTION_POLICY_LEVELS[AlgorithmSubstitutionPolicy.NONE]
                    ):
                        msg = "'{}' is not a valid {} value for parameter {}".format(
                            change.new_value, param_props['type'].name, change.kisao_id)
                        raise ValueError(msg)
                    else:
                        msg = "'{}' was ignored because it is not a valid {} value for parameter {}".format(
                            change.new_value, param_props['type'].name, change.kisao_id)
                        warn(msg, BioSimulatorsWarning)

            else:
                if (
                    exec_alg_kisao_id == sim.algorithm.kisao_id and
                    ALGORITHM_SUBSTITUTION_POLICY_LEVELS[algorithm_substitution_policy]
                    <= ALGORITHM_SUBSTITUTION_POLICY_LEVELS[AlgorithmSubstitutionPolicy.NONE]
                ):
                    msg = "".join([
                        "Algorithm parameter with KiSAO id '{}' is not supported. ".format(change.kisao_id),
                        "Parameter must have one of the following KiSAO ids:\n  - {}".format('\n  - '.join(
                            '{}: {} ({})'.format(kisao_id, param_props['id'], param_props['name'])
                            for kisao_id, param_props in alg_props['parameters'].items())),
                    ])
                    raise NotImplementedError(msg)
                else:
                    msg = "".join([
                        "Algorithm parameter with KiSAO id '{}' was ignored because it is not supported. ".format(change.kisao_id),
                        "Parameter must have one of the following KiSAO ids:\n  - {}".format('\n  - '.join(
                            '{}: {} ({})'.format(kisao_id, param_props['id'], param_props['name'])
                            for kisao_id, param_props in alg_props['parameters'].items())),
                    ])
                    warn(msg, BioSimulatorsWarning)

        # validate model changes and build map
        if isinstance(subtask, RepeatedTask):
            allchanges = allchanges + subtask.changes
        model_change_target_tellurium_id_map = get_model_change_target_tellurium_change_map(
            model_etree, allchanges, exec_alg_kisao_id, road_runner.model, model.id)

        # validate variables and build map
        variable_target_tellurium_observable_map = get_variable_target_tellurium_observable_map(
            model_etree, sim, exec_alg_kisao_id, variables, road_runner.model, model.id)

        variable_tellurium_observable_ids = []
        for variable in variables:
            tellurium_id = variable_target_tellurium_observable_map[(model.id, variable.target, variable.symbol)]
            variable_tellurium_observable_ids.append(tellurium_id)

        road_runner.timeCourseSelections = variable_tellurium_observable_ids
        road_runner.steadyStateSelections = variable_tellurium_observable_ids
        # Add the variables to the dictionaries:
        allroadrunners[subtask.id] = road_runner
        model_change_target_tellurium_id_maps[subtask.id] = model_change_target_tellurium_id_map
        exec_alg_kisao_ids[subtask.id] = exec_alg_kisao_id
        variable_target_tellurium_observable_maps[subtask.id] = variable_target_tellurium_observable_map
        solvers[subtask.id] = solver

    # return preprocssed information about the task
    return PreprocesssedTask(
        road_runners=allroadrunners,
        solvers=solvers,
        model_change_target_tellurium_id_maps=model_change_target_tellurium_id_maps,
        algorithm_kisao_ids=exec_alg_kisao_ids,
        variable_target_tellurium_observable_maps=variable_target_tellurium_observable_maps,
    )


def get_model_variable_value(model, variable, preprocessed_task):
    if preprocessed_task is None:
        raise ValueError("Tellurium cannot obtain a model value without a working preprocessed_task.")
    for taskid in preprocessed_task.variable_target_tellurium_observable_maps:
        submap = preprocessed_task.variable_target_tellurium_observable_maps[taskid]
        if (model.id, variable.target, variable.symbol) in submap:
            return submap[(model.id, variable.target, variable.symbol)]
    raise ValueError("No stored variable with target '" + variable.target + "' and symbol '" +
                     str(variable.symbol if variable.symbol else '') + "' in model " + model.id)


def set_model_variable_value(model, target, symbol, value, preprocessed_task):
    value = float(value)
    if preprocessed_task is None:
        raise ValueError("Tellurium cannot set a model value without a working preprocessed_task.")
    success = False
    for taskid in preprocessed_task.variable_target_tellurium_observable_maps:
        submap = preprocessed_task.variable_target_tellurium_observable_maps[taskid]
        if (model.id, target, symbol) in submap:
            tellurium_id = submap[(model.id, target, symbol)]
            preprocessed_task.road_runners[taskid][tellurium_id] = value
            success = True
    if not success:
        for taskid in preprocessed_task.model_change_target_tellurium_id_maps:
            submap = preprocessed_task.model_change_target_tellurium_id_maps[taskid]
            if (model.id, target, symbol) in submap:
                tellurium_id = submap[(model.id, target, symbol)]
                preprocessed_task.road_runners[taskid][tellurium_id] = value
                success = True
    if not success:
        if "reaction[" in target and "kineticLaw/" in target:
            raise NotImplementedError("Unable to process a change to model '" + model.id + "' with the target "
                                      + target + " because changing local parameters is not yet implemented.")
        raise ValueError("No stored variable with target '" + target + "' and symbol '" +
                         str(symbol if symbol else '') + "' in model " + model.id)


def get_model_change_target_tellurium_change_map(model_etree, changes, alg_kisao_id, model, model_id):
    """ Get a mapping from XML XPath targets for model changes to tellurium identifiers for model changes

    Args:
        model_etree (:obj:`lxml.etree._ElementTree`): element tree for model
        changes (:obj:`list` of :obj:`ModelChange`): list of model changes
        alg_kisao_id (:obj:`str`): algorithm KiSAO id
        model (:obj:`roadrunner.roadrunner.ExecutableModel`): model

    Returns:
        :obj:`dict`: dictionary that maps the targets of changes to their corresponding tellurium identifiers
    """
    change_targets_to_sbml_ids = validation.validate_target_xpaths(changes, model_etree, attr='id', separator="_")

    species_ids = model.getFloatingSpeciesIds() + model.getBoundarySpeciesIds()
    component_ids = species_ids + model.getGlobalParameterIds() + model.getCompartmentIds()

    target_tellurium_id_map = {}

    for i_change, change in enumerate(changes):
        if not isinstance(change, ModelAttributeChange) and not isinstance(change, ComputeModelChange):
            continue
        if hasattr(model, "change") and change.model.id != model_id:
            raise NotImplementedError("Unable to process a change to model '" + change.model_id
                                      + "' inside a task concerning model '" + model_id + "'")
        if hasattr(model, "symbol") and change.symbol:
            raise NotImplementedError("Unable to process a change to model '" + change.model_id
                                      + "' with the symbol '" + change.symbol + "'")
        else:
            change.symbol = None
        __, sep, __ = change.target.rpartition('/@')

        sbml_id = change_targets_to_sbml_ids[change.target]

        if alg_kisao_id == 'KISAO_0000029' and sbml_id in species_ids:
            target_tellurium_id_map[(model_id, change.target, change.symbol)] = '[' + sbml_id + ']'
        elif sbml_id in component_ids:
            target_tellurium_id_map[(model_id, change.target, change.symbol)] = sbml_id

    return target_tellurium_id_map


def get_variable_target_tellurium_observable_map(model_etree, simulation, alg_kisao_id, variables, model, model_id):
    """ Get a mapping from XML XPath targets for variables of data generators to their corresponding tellurium identifiers

    Args:
        model_etree (:obj:`lxml.etree._ElementTree`): element tree for model
        simulation (:obj:`Simulation`): simulation
        alg_kisao_id (:obj:`str`): algorithm KiSAO id
        variables (:obj:`list` of :obj:`Variable`): list of variables
        model (:obj:`roadrunner.roadrunner.ExecutableModel`): model

    Returns:
        :obj:`dict`: dictionary that maps tuples of variable targets and symbols to their corresponding tellurium identifiers
    """
    variable_targets_to_sbml_ids = validation.validate_target_xpaths(variables, model_etree, attr='id')

    all_sbml_ids = model.getAllTimeCourseComponentIds()
    species_sbml_ids = model.getBoundarySpeciesIds() + model.getFloatingSpeciesIds()

    target_tellurium_observable_map = {}

    invalid_symbols = []
    invalid_targets = []

    for variable in variables:
        if variable.symbol:
            if variable.symbol == Symbol.time.value and isinstance(simulation, UniformTimeCourseSimulation):
                target_tellurium_observable_map[(model_id, variable.target, variable.symbol)] = 'time'
            else:
                invalid_symbols.append(variable.symbol)

        else:
            sbml_id = variable_targets_to_sbml_ids.get(variable.target, None)

            if sbml_id in all_sbml_ids:
                if alg_kisao_id != 'KISAO_0000029' and sbml_id in species_sbml_ids:
                    target_tellurium_observable_map[(model_id, variable.target, variable.symbol)] = '[' + sbml_id + ']'
                else:
                    target_tellurium_observable_map[(model_id, variable.target, variable.symbol)] = sbml_id

            else:
                invalid_targets.append(variable.target)

    if invalid_symbols:
        msg = (
            'The following symbols are not supported:\n  - {}'
            '\n'
            '\n'
            'Only following symbols are supported:\n  - {}'
        ).format(
            '\n  - '.join(sorted(invalid_symbols)),
            '\n  - '.join(sorted([Symbol.time.value])),
        )
        raise NotImplementedError(msg)

    if invalid_targets:
        valid_targets = []
        for species_sbml_id in species_sbml_ids:
            valid_targets.append("/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='{}']".format(species_sbml_id))
        for rxn_id in model.getReactionIds():
            valid_targets.append("/sbml:sbml/sbml:model/sbml:listOfReactions/sbml:reaction[@id='{}']".format(rxn_id))

        msg = (
            'The following targets are not supported:\n  - {}'
            '\n'
            '\n'
            'Only following targets are supported:\n  - {}'
        ).format(
            '\n  - '.join(sorted(invalid_targets)),
            '\n  - '.join(sorted(valid_targets)),
        )
        raise ValueError(msg)

    return target_tellurium_observable_map


def exec_sed_doc_with_tellurium(doc, working_dir, base_out_path, rel_out_path=None,
                                apply_xml_model_changes=True,
                                log=None, indent=0, pretty_print_modified_xml_models=False,
                                log_level=StandardOutputErrorCapturerLevel.c, config=None, simulator_config=None):
    """
    Args:
        doc (:obj:`SedDocument` or :obj:`str`): SED document or a path to SED-ML file which defines a SED document
        working_dir (:obj:`str`): working directory of the SED document (path relative to which models are located)
        base_out_path (:obj:`str`): path to store the outputs

            * CSV: directory in which to save outputs to files
              ``{base_out_path}/{rel_out_path}/{report.id}.csv``
            * HDF5: directory in which to save a single HDF5 file (``{base_out_path}/reports.h5``),
              with reports at keys ``{rel_out_path}/{report.id}`` within the HDF5 file

        rel_out_path (:obj:`str`, optional): path relative to :obj:`base_out_path` to store the outputs
        apply_xml_model_changes (:obj:`bool`, optional): if :obj:`True`, apply any model changes specified in the SED-ML file before
            calling :obj:`task_executer`.
        log (:obj:`SedDocumentLog`, optional): execution status of document
        indent (:obj:`int`, optional): degree to indent status messages
        pretty_print_modified_xml_models (:obj:`bool`, optional): if :obj:`True`, pretty print modified XML models
        log_level (:obj:`StandardOutputErrorCapturerLevel`, optional): level at which to log output
        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`tuple`:

            * :obj:`ReportResults`: results of each report
            * :obj:`SedDocumentLog`: log of the document
    """
    if not config:
        config = get_config()
    if not simulator_config:
        simulator_config = SimulatorConfig()

    if isinstance(doc, str):
        doc = SedmlSimulationReader().run(doc)

    if config.LOG and not log:
        log = init_sed_document_log(doc)
    start_time = datetime.datetime.now()

    # Set the engine that tellurium uses for plotting
    tellurium.setDefaultPlottingEngine(simulator_config.plotting_engine.value)

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
            labels = {}
            if isinstance(output, Plot3D):
                for surface in output.surfaces:
                    data_generators[surface.x_data_generator.id] = surface.x_data_generator
                    labels[surface.x_data_generator.id] = surface.x_data_generator.name or surface.x_data_generator.id

                    data_generators[surface.y_data_generator.id] = surface.y_data_generator
                    labels[surface.x_data_generator.id] = surface.y_data_generator.name or surface.y_data_generator.id

                    data_generators[surface.z_data_generator.id] = surface.z_data_generator
                    labels[surface.y_data_generator.id] = surface.name or surface.z_data_generator.name or surface.z_data_generator.id

            elif isinstance(output, Plot2D):
                for curve in output.curves:
                    data_generators[curve.x_data_generator.id] = curve.x_data_generator
                    labels[curve.x_data_generator.id] = curve.x_data_generator.name or curve.x_data_generator.id

                    data_generators[curve.y_data_generator.id] = curve.y_data_generator
                    labels[curve.y_data_generator.id] = curve.name or curve.y_data_generator.name or curve.y_data_generator.id

            # print("LS DEBUG:  Labels are " + str(labels))

            for data_generator in data_generators.values():
                report.data_sets.append(DataSet(
                    id='__data_set__{}_{}'.format(output.id, data_generator.id),
                    name=data_generator.name,
                    label=labels[data_generator.id],
                    data_generator=data_generator,
                ))

            report.data_sets.sort(key=lambda data_set: data_set.id)
            doc.outputs.append(report)

    filename_with_reports_for_plots = os.path.join(tmp_out_dir, 'simulation.sedml')
    SedmlSimulationWriter().run(doc, filename_with_reports_for_plots, validate_models_with_languages=False)

    # Use tellurium to execute the SED document and generate the specified outputs
    viz_formats = [VizFormat(format_value) for format_value in config.VIZ_FORMATS]
    with StandardOutputErrorCapturer(relay=False, level=log_level, disabled=not config.LOG) as captured:
        try:
            factory = SEDMLCodeFactory(filename_with_reports_for_plots,
                                       workingDir=working_dir,
                                       createOutputs=True,
                                       saveOutputs=True,
                                       outputDir=tmp_out_dir,
                                       )
            for viz_format in (viz_formats or [VizFormat.pdf]):
                factory.reportFormat = 'csv'
                factory.plotFormat = viz_format.value
                factory.executePython()

            if config.LOG:
                log.output = captured.get_text()
                log.export()

        except Exception as exception:
            if config.LOG:
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
    if config.COLLECT_SED_DOCUMENT_RESULTS:
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

        if config.LOG:
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
        if config.COLLECT_SED_DOCUMENT_RESULTS:
            report_results[output_id] = data_set_results

        # save file in desired BioSimulators format(s)
        report_formats = [ReportFormat(format_value) for format_value in config.REPORT_FORMATS]
        for report_format in report_formats:
            ReportWriter().run(output,
                               data_set_results,
                               base_out_path,
                               os.path.join(rel_out_path, output_id) if rel_out_path else output_id,
                               format=report_format)

        if config.LOG:
            log.outputs[output_id].status = Status.SUCCEEDED
            log.outputs[output_id].duration = (datetime.datetime.now() - output_start_time).total_seconds()
            log.export()

    # Move the plot outputs to the permanent output directory
    out_dir = base_out_path
    if rel_out_path:
        out_dir = os.path.join(out_dir, rel_out_path)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    for viz_format in viz_formats:
        for viz_filename in glob.glob(os.path.join(tmp_out_dir, '*.' + viz_format.value)):
            shutil.move(viz_filename, out_dir)

    # finalize log
    if config.LOG:
        log.status = Status.SUCCEEDED
        log.duration = (datetime.datetime.now() - start_time).total_seconds()
        log.export()

    # Clean up the temporary directory for tellurium's outputs
    shutil.rmtree(tmp_out_dir)

    # Return a data structure with the results of the reports
    return report_results, log

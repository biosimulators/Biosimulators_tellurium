""" Tests of the tellurium command-line interface

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from biosimulators_tellurium import __main__
from biosimulators_tellurium import core
from biosimulators_tellurium.config import Config as SimulatorConfig
from biosimulators_tellurium.data_model import SedmlInterpreter
from biosimulators_utils.archive.io import ArchiveReader
from biosimulators_utils.combine import data_model as combine_data_model
from biosimulators_utils.combine.io import CombineArchiveWriter
from biosimulators_utils.config import get_config
from biosimulators_utils.log.data_model import Status
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.report import data_model as report_data_model
from biosimulators_utils.sedml import data_model as sedml_data_model
from biosimulators_utils.sedml.data_model import Report, DataSet
from biosimulators_utils.sedml.io import SedmlSimulationWriter
from biosimulators_utils.sedml.utils import append_all_nested_children_to_doc
from biosimulators_utils.simulator.exec import exec_sedml_docs_in_archive_with_containerized_simulator
from biosimulators_utils.simulator.specs import gen_algorithms_from_specs
from biosimulators_utils.warnings import BioSimulatorsWarning
from kisao.exceptions import AlgorithmCannotBeSubstitutedException
from kisao.warnings import AlgorithmSubstitutedWarning
from unittest import mock
import copy
import json
import numpy
import numpy.testing
import os
import PyPDF2
import shutil
import tellurium.sedml.tesedml
import tempfile
import unittest
import yaml


class CoreTestCase(unittest.TestCase):
    FIXTURES_DIRNAME = os.path.join(os.path.dirname(__file__), 'fixtures')
    EXAMPLE_MODEL_FILENAME = os.path.join(os.path.dirname(__file__), 'fixtures', 'BIOMD0000000003_url.xml')
    NAMESPACES = {
        'sbml': 'http://www.sbml.org/sbml/level2/version4',
    }
    SPECIFICATIONS_FILENAME = os.path.join(os.path.dirname(__file__), '..', 'biosimulators.json')
    DOCKER_IMAGE = 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:latest'

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    # BioSimulators SED-ML interpreter
    def test_exec_sed_task_successfully_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=0.,
                output_start_time=0.,
                output_end_time=10.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                    changes=[
                        sedml_data_model.AlgorithmParameterChange(
                            kisao_id='KISAO_0000209',
                            new_value='1e-8',
                        )
                    ]
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='V1',
                target="/sbml:sbml/sbml:model/sbml:listOfParameters/sbml:parameter[@id='V1']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='VM1',
                target="/sbml:sbml/sbml:model/sbml:listOfParameters/sbml:parameter[@id='VM1']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='reaction1',
                target="/sbml:sbml/sbml:model/sbml:listOfReactions/sbml:reaction[@id='reaction1']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='cell',
                target="/sbml:sbml/sbml:model/sbml:listOfCompartments/sbml:compartment[@id='cell']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        variable_results, log = core.exec_sed_task(task, variables)

        # check that the simulation was executed correctly
        self.assertEqual(set(variable_results.keys()), set(['Time', 'C', 'V1', 'VM1', 'reaction1', 'cell']))
        for variable_result in variable_results.values():
            self.assertFalse(numpy.any(numpy.isnan(variable_result)))
        numpy.testing.assert_allclose(
            variable_results['Time'],
            numpy.linspace(
                task.simulation.output_start_time,
                task.simulation.output_end_time,
                task.simulation.number_of_points + 1,
            ))
        numpy.testing.assert_allclose(
            variable_results['VM1'],
            numpy.full((task.simulation.number_of_points + 1,), 3.))
        numpy.testing.assert_allclose(
            variable_results['cell'],
            numpy.full((task.simulation.number_of_points + 1,), 1.))

        # check that log can be serialized to JSON
        self.assertEqual(log.algorithm, 'KISAO_0000019')
        self.assertEqual(log.simulator_details['solver'], 'cvode')
        self.assertEqual(log.simulator_details['relative_tolerance'], 1e-8)

        json.dumps(log.to_json())

        log.out_dir = self.dirname
        log.export()
        with open(os.path.join(self.dirname, get_config().LOG_PATH), 'rb') as file:
            log_data = yaml.load(file, Loader=yaml.Loader)
        json.dumps(log_data)

    def test_exec_sed_task_positive_initial_time_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=10.,
                output_start_time=10.,
                output_end_time=20.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        variable_results, log = core.exec_sed_task(task, variables)

        # check that the simulation was executed correctly
        self.assertEqual(set(variable_results.keys()), set(['Time', 'C']))
        for variable_result in variable_results.values():
            self.assertFalse(numpy.any(numpy.isnan(variable_result)))
        numpy.testing.assert_allclose(
            variable_results['Time'],
            numpy.linspace(
                task.simulation.output_start_time,
                task.simulation.output_end_time,
                task.simulation.number_of_points + 1,
            ))

    def test_exec_sed_task_negative_initial_time_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=-10.,
                output_start_time=-10.,
                output_end_time=10.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        variable_results, log = core.exec_sed_task(task, variables)

        # check that the simulation was executed correctly
        self.assertEqual(set(variable_results.keys()), set(['Time', 'C']))
        for variable_result in variable_results.values():
            self.assertFalse(numpy.any(numpy.isnan(variable_result)))
        numpy.testing.assert_allclose(
            variable_results['Time'],
            numpy.linspace(
                task.simulation.output_start_time,
                task.simulation.output_end_time,
                task.simulation.number_of_points + 1,
            ))

    def test_exec_sed_task_positive_output_start_time_time_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=10.,
                output_start_time=20.,
                output_end_time=30.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        variable_results, log = core.exec_sed_task(task, variables)

        # check that the simulation was executed correctly
        self.assertEqual(set(variable_results.keys()), set(['Time', 'C']))
        for variable_result in variable_results.values():
            self.assertFalse(numpy.any(numpy.isnan(variable_result)))
        numpy.testing.assert_allclose(
            variable_results['Time'],
            numpy.linspace(
                task.simulation.output_start_time,
                task.simulation.output_end_time,
                task.simulation.number_of_points + 1,
            ))

    def test_exec_sed_task_steady_state_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.SteadyStateSimulation(
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000569',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='M',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='M']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        variable_results, log = core.exec_sed_task(task, variables)

        # check that the simulation was executed correctly
        self.assertEqual(set(variable_results.keys()), set(['C', 'M']))
        for variable_result in variable_results.values():
            self.assertFalse(numpy.any(numpy.isnan(variable_result)))
        self.assertGreater(variable_results['C'], 0)
        self.assertGreater(variable_results['M'], 0)

    def test_exec_sed_task_alg_substitution_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=0.,
                output_start_time=0.,
                output_end_time=10.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        task_2 = copy.deepcopy(task)
        task_2.simulation.algorithm.kisao_id = 'KISAO_0000088'
        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'NONE'}):
            with self.assertRaises(AlgorithmCannotBeSubstitutedException):
                core.exec_sed_task(task_2, variables)

        task_2 = copy.deepcopy(task)
        task_2.simulation.algorithm.kisao_id = 'KISAO_0000088'
        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'SIMILAR_VARIABLES'}):
            with self.assertWarns(AlgorithmSubstitutedWarning):
                core.exec_sed_task(task_2, variables)

        task_2 = copy.deepcopy(task)
        task_2.simulation.algorithm.changes.append(sedml_data_model.AlgorithmParameterChange(
            kisao_id='KISAO_0000488',
            new_value='1',
        ))
        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'NONE'}):
            with self.assertRaises(NotImplementedError):
                core.exec_sed_task(task_2, variables)

        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'SIMILAR_VARIABLES'}):
            with self.assertWarns(BioSimulatorsWarning):
                core.exec_sed_task(task_2, variables)

        task_2 = copy.deepcopy(task)
        task_2.simulation.algorithm.changes.append(sedml_data_model.AlgorithmParameterChange(
            kisao_id='KISAO_0000209',
            new_value='abc',
        ))
        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'NONE'}):
            with self.assertRaises(ValueError):
                core.exec_sed_task(task_2, variables)

        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'SIMILAR_VARIABLES'}):
            with self.assertWarns(BioSimulatorsWarning):
                core.exec_sed_task(task_2, variables)

    def test_exec_sed_task_error_handling_with_biosimulators(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=0.,
                output_start_time=0.,
                output_end_time=10.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        simulator_config = SimulatorConfig()

        simulator_config.sedml_interpreter = SedmlInterpreter.tellurium
        with self.assertRaises(NotImplementedError):
            variable_results, log = core.exec_sed_task(task, variables, simulator_config=simulator_config)

        variables_2 = copy.deepcopy(variables)
        variables_2[0].symbol = 'mass'
        simulator_config.sedml_interpreter = SedmlInterpreter.biosimulators
        with self.assertRaises(NotImplementedError):
            variable_results, log = core.exec_sed_task(task, variables_2, simulator_config=simulator_config)

        variables_2 = copy.deepcopy(variables)
        variables_2[1].target = '/sbml:sbml'
        simulator_config.sedml_interpreter = SedmlInterpreter.biosimulators
        with self.assertRaisesRegex(ValueError, 'targets are not supported'):
            variable_results, log = core.exec_sed_task(task, variables_2, simulator_config=simulator_config)

        task_2 = copy.deepcopy(task)
        task_2.simulation.output_start_time = 1.5
        simulator_config.sedml_interpreter = SedmlInterpreter.biosimulators
        with self.assertRaises(NotImplementedError):
            variable_results, log = core.exec_sed_task(task_2, variables, simulator_config=simulator_config)

    def test_exec_sed_task_with_preprocesssed_task(self):
        # configure simulation
        task = sedml_data_model.Task(
            model=sedml_data_model.Model(
                source=self.EXAMPLE_MODEL_FILENAME,
                language=sedml_data_model.ModelLanguage.SBML.value,
                changes=[
                    sedml_data_model.ModelAttributeChange(
                        target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                        target_namespaces=self.NAMESPACES,
                        new_value=0.011,
                    ),
                    sedml_data_model.ModelAttributeChange(
                        target="/sbml:sbml/sbml:model/sbml:listOfParameters/sbml:parameter[@id='VM1']",
                        target_namespaces=self.NAMESPACES,
                        new_value=3.01,
                    ),
                    sedml_data_model.ModelAttributeChange(
                        target="/sbml:sbml/sbml:model/sbml:listOfCompartments/sbml:compartment[@id='cell']",
                        target_namespaces=self.NAMESPACES,
                        new_value=1.01,
                    ),
                ],
            ),
            simulation=sedml_data_model.UniformTimeCourseSimulation(
                initial_time=0.,
                output_start_time=0.,
                output_end_time=10.,
                number_of_points=10,
                algorithm=sedml_data_model.Algorithm(
                    kisao_id='KISAO_0000019',
                ),
            ),
        )

        variables = [
            sedml_data_model.Variable(
                id='Time',
                symbol=sedml_data_model.Symbol.time,
                task=task),
            sedml_data_model.Variable(
                id='C',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='M',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='M']",
                target_namespaces=self.NAMESPACES,
                task=task),
            sedml_data_model.Variable(
                id='X',
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='X']",
                target_namespaces=self.NAMESPACES,
                task=task),
        ]

        # execute simulation
        task.model.changes[0].target = "/sbml:sbml/sbml:model"
        with self.assertRaisesRegex(ValueError, 'targets for the following changes are not valid'):
            preprocessed_task = core.preprocess_sed_task(task, variables)

        task.model.changes[0].target = "/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']"
        task.simulation.algorithm.kisao_id = 'KISAO_0000029'
        preprocessed_task = core.preprocess_sed_task(task, variables)

        task.simulation.algorithm.kisao_id = 'KISAO_0000019'
        preprocessed_task = core.preprocess_sed_task(task, variables)

        task.model.changes = []
        task.simulation.number_of_points = 1
        preprocessed_task = core.preprocess_sed_task(task, variables)
        variable_results, log = core.exec_sed_task(task, variables, preprocessed_task=preprocessed_task)
        end_c = variable_results['C'][-1]

        task.simulation.output_end_time /= 2
        preprocessed_task = core.preprocess_sed_task(task, variables)
        variable_results, log = core.exec_sed_task(task, variables, preprocessed_task=preprocessed_task)
        with self.assertRaises(AssertionError):
            numpy.testing.assert_allclose(variable_results['C'][-1], end_c)
        mid_c = preprocessed_task.road_runners[task.id]['C']
        mid_m = preprocessed_task.road_runners[task.id]['M']
        mid_x = preprocessed_task.road_runners[task.id]['X']
        self.assertIsInstance(mid_c, float)

        variable_results, log = core.exec_sed_task(task, variables, preprocessed_task=preprocessed_task)
        numpy.testing.assert_allclose(variable_results['C'][-1], end_c)

        task.model.changes = [
            sedml_data_model.ModelAttributeChange(
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                new_value=mid_c,
            ),
            sedml_data_model.ModelAttributeChange(
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='M']",
                target_namespaces=self.NAMESPACES,
                new_value=mid_m,
            ),
            sedml_data_model.ModelAttributeChange(
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='X']",
                target_namespaces=self.NAMESPACES,
                new_value=mid_x,
            ),
        ]
        preprocessed_task = core.preprocess_sed_task(task, variables)
        variable_results, log = core.exec_sed_task(task, variables, preprocessed_task=preprocessed_task)
        numpy.testing.assert_allclose(variable_results['C'][-1], end_c)

        # check that the simulation was executed correctly
        self.assertEqual(set(variable_results.keys()), set(['Time', 'C', 'M', 'X']))
        for variable_result in variable_results.values():
            self.assertFalse(numpy.any(numpy.isnan(variable_result)))
        numpy.testing.assert_allclose(
            variable_results['Time'],
            numpy.linspace(
                task.simulation.output_start_time,
                task.simulation.output_end_time,
                task.simulation.number_of_points + 1,
            ))

        # check changes can be strings
        task.model.changes = [
            sedml_data_model.ModelAttributeChange(
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                target_namespaces=self.NAMESPACES,
                new_value=str(mid_c),
            ),
            sedml_data_model.ModelAttributeChange(
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='M']",
                target_namespaces=self.NAMESPACES,
                new_value=str(mid_m),
            ),
            sedml_data_model.ModelAttributeChange(
                target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='X']",
                target_namespaces=self.NAMESPACES,
                new_value=str(mid_x),
            ),
        ]
        variable_results, log = core.exec_sed_task(task, variables, preprocessed_task=preprocessed_task)
        numpy.testing.assert_allclose(variable_results['C'][-1], end_c)

    def test_exec_sedml_docs_in_combine_archive_successfully_with_biosimulators(self):
        doc, archive_filename = self._build_combine_archive()

        out_dir = os.path.join(self.dirname, 'out')

        config = get_config()
        config.REPORT_FORMATS = [report_data_model.ReportFormat.h5]
        config.BUNDLE_OUTPUTS = True
        config.KEEP_INDIVIDUAL_OUTPUTS = True

        _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, out_dir, config=config)
        if log.exception:
            raise log.exception
        self.assertEqual(log.sed_documents['sim.sedml'].tasks['task_1'].status, Status.SUCCEEDED)

        self._assert_combine_archive_outputs(doc, out_dir)

    def _build_combine_archive(self, algorithm=None):
        doc = self._build_sed_doc(algorithm=algorithm)

        archive_dirname = os.path.join(self.dirname, 'archive')
        if not os.path.isdir(archive_dirname):
            os.mkdir(archive_dirname)

        model_filename = os.path.join(archive_dirname, 'model.xml')
        shutil.copyfile(self.EXAMPLE_MODEL_FILENAME, model_filename)

        sim_filename = os.path.join(archive_dirname, 'sim.sedml')
        SedmlSimulationWriter().run(doc, sim_filename)

        archive = combine_data_model.CombineArchive(
            contents=[
                combine_data_model.CombineArchiveContent(
                    'model.xml', combine_data_model.CombineArchiveContentFormat.SBML.value),
                combine_data_model.CombineArchiveContent(
                    'sim.sedml', combine_data_model.CombineArchiveContentFormat.SED_ML.value),
            ],
        )
        archive_filename = os.path.join(self.dirname, 'archive.omex')
        CombineArchiveWriter().run(archive, archive_dirname, archive_filename)

        return (doc, archive_filename)

    def _build_sed_doc(self, algorithm=None):
        if algorithm is None:
            algorithm = sedml_data_model.Algorithm(
                kisao_id='KISAO_0000019',
            )

        doc = sedml_data_model.SedDocument()
        doc.models.append(sedml_data_model.Model(
            id='model',
            source='model.xml',
            language=sedml_data_model.ModelLanguage.SBML.value,
        ))
        if algorithm.kisao_id == 'KISAO_0000569':
            doc.simulations.append(sedml_data_model.SteadyStateSimulation(
                id='sim_steady_state',
                algorithm=algorithm,
            ))
        else:
            doc.simulations.append(sedml_data_model.UniformTimeCourseSimulation(
                id='sim_time_course',
                initial_time=0.,
                output_start_time=0.,
                output_end_time=10.,
                number_of_points=10,
                algorithm=algorithm,
            ))

        doc.tasks.append(sedml_data_model.Task(
            id='task_1',
            model=doc.models[0],
            simulation=doc.simulations[0],
        ))

        if algorithm.kisao_id != 'KISAO_0000569':
            doc.data_generators.append(sedml_data_model.DataGenerator(
                id='data_gen_time',
                variables=[
                    sedml_data_model.Variable(
                        id='var_time',
                        symbol=sedml_data_model.Symbol.time.value,
                        task=doc.tasks[0],
                    ),
                ],
                math='var_time',
            ))
        doc.data_generators.append(sedml_data_model.DataGenerator(
            id='data_gen_C',
            variables=[
                sedml_data_model.Variable(
                    id='var_C',
                    target="/sbml:sbml/sbml:model/sbml:listOfSpecies/sbml:species[@id='C']",
                    target_namespaces=self.NAMESPACES,
                    task=doc.tasks[0],
                ),
            ],
            math='var_C',
        ))

        report = sedml_data_model.Report(id='report')
        doc.outputs.append(report)
        if algorithm.kisao_id != 'KISAO_0000569':
            report.data_sets.append(sedml_data_model.DataSet(id='data_set_time', label='Time', data_generator=doc.data_generators[0]))
        report.data_sets.append(sedml_data_model.DataSet(id='data_set_C', label='C', data_generator=doc.data_generators[-1]))

        append_all_nested_children_to_doc(doc)

        return doc

    def _assert_combine_archive_outputs(self, doc, out_dir):
        self.assertEqual(set(['reports.h5']).difference(set(os.listdir(out_dir))), set())

        report = ReportReader().run(doc.outputs[0], out_dir, 'sim.sedml/report', format=report_data_model.ReportFormat.h5)

        self.assertEqual(sorted(report.keys()), sorted([d.id for d in doc.outputs[0].data_sets]))

        sim = doc.tasks[0].simulation
        if doc.simulations[0].algorithm.kisao_id == 'KISAO_0000569':
            self.assertIn(report[doc.outputs[0].data_sets[0].id].shape, [(), (1,)])
            self.assertIsInstance(report[doc.outputs[0].data_sets[0].id].tolist(), (float, list))
        else:
            self.assertEqual(len(report[doc.outputs[0].data_sets[0].id]), sim.number_of_points + 1)

        for data_set_result in report.values():
            self.assertFalse(numpy.any(numpy.isnan(data_set_result)))

        if doc.simulations[0].algorithm.kisao_id != 'KISAO_0000569':
            self.assertIn('data_set_time', report)
            numpy.testing.assert_allclose(report[doc.outputs[0].data_sets[0].id],
                                          numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1))

    # all SED-ML interpreters
    def test_exec_sedml_docs_in_combine_archive(self):
        for sedml_interpreter in SedmlInterpreter.__members__.values():
            simulator_config = SimulatorConfig()
            simulator_config.sedml_interpreter = sedml_interpreter

            # with reports
            archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'reports')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception

            self._assert_curated_combine_archive_outputs(dirname, reports=True, plots=False)

            # with plots
            archive_filename = 'tests/fixtures/BIOMD0000000297-with-plots.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'plots')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception

            self._assert_curated_combine_archive_outputs(dirname, reports=False, plots=True)

            # with reports and plots
            archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'reports-and-plots')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception

    def test_exec_sedml_docs_in_combine_archive_with_all_algorithms(self):
        for sedml_interpreter in SedmlInterpreter.__members__.values():
            for alg in gen_algorithms_from_specs(self.SPECIFICATIONS_FILENAME).values():
                doc, archive_filename = self._build_combine_archive(algorithm=alg)
                out_dir = os.path.join(self.dirname, sedml_interpreter.name, alg.kisao_id)

                config = get_config()
                config.COLLECT_COMBINE_ARCHIVE_RESULTS = True
                config.REPORT_FORMATS = [report_data_model.ReportFormat.h5]
                config.BUNDLE_OUTPUTS = True
                config.KEEP_INDIVIDUAL_OUTPUTS = True

                simulator_config = SimulatorConfig()
                simulator_config.sedml_interpreter = sedml_interpreter

                results, log = core.exec_sedml_docs_in_combine_archive(archive_filename, out_dir,
                                                                       config=config,
                                                                       simulator_config=simulator_config)
                self.assertEqual(set(results.keys()), set(['sim.sedml']))
                self.assertEqual(set(results['sim.sedml'].keys()), set(['report']))
                if alg.kisao_id == 'KISAO_0000569':
                    self.assertEqual(set(results['sim.sedml']['report'].keys()), set(['data_set_C']))
                else:
                    self.assertEqual(set(results['sim.sedml']['report'].keys()), set(['data_set_time', 'data_set_C']))
                if log.exception:
                    raise log.exception
                self._assert_combine_archive_outputs(doc, out_dir)

    def test_exec_sed_doc(self):
        with mock.patch('biosimulators_tellurium.core.exec_sed_doc_with_biosimulators', return_value=None):
            core.exec_sed_doc(None, None, None)

        simulator_config = SimulatorConfig()
        simulator_config.sedml_interpreter = 'undefined'
        with self.assertRaises(NotImplementedError):
            core.exec_sed_doc(None, None, None, simulator_config=simulator_config)

    # tellurium error handling
    def test_exec_sedml_docs_in_combine_archive_with_tellurium_error_handling(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'

        simulator_config = SimulatorConfig()
        simulator_config.sedml_interpreter = SedmlInterpreter.tellurium

        with mock.patch.object(tellurium.sedml.tesedml.SEDMLCodeFactory, 'executePython', side_effect=Exception('my error')):
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, self.dirname, simulator_config=simulator_config)
        with self.assertRaisesRegex(Exception, 'my error'):
            if log.exception:
                raise log.exception

    # CLI and Docker image

    def test_exec_sedml_docs_in_combine_archive_with_cli(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'
        env = self._get_combine_archive_exec_env()

        with mock.patch.dict(os.environ, env):
            with __main__.App(argv=['-i', archive_filename, '-o', self.dirname]) as app:
                app.run()

        self._assert_curated_combine_archive_outputs(self.dirname, reports=True, plots=True)

    def test_sim_with_docker_image(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'
        env = self._get_combine_archive_exec_env()

        exec_sedml_docs_in_archive_with_containerized_simulator(
            archive_filename, self.dirname, self.DOCKER_IMAGE, environment=env, pull_docker_image=False)

        self._assert_curated_combine_archive_outputs(self.dirname, reports=True, plots=True)

    def test_repeated_task_with_change(self):
        for sedml_interpreter in SedmlInterpreter.__members__.values():
            simulator_config = SimulatorConfig()
            simulator_config.sedml_interpreter = sedml_interpreter

            archive_filename = 'tests/fixtures/repeat_basic.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'reports')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception


    def test_repeated_task_with_change_and_no_reset(self):
        for sedml_interpreter in SedmlInterpreter.__members__.values():
            simulator_config = SimulatorConfig()
            simulator_config.sedml_interpreter = sedml_interpreter

            archive_filename = 'tests/fixtures/repeat_no_reset.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'reports')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception


    def test_repeated_task_with_change_to_initial_assignment(self):
        for sedml_interpreter in SedmlInterpreter.__members__.values():
            simulator_config = SimulatorConfig()
            simulator_config.sedml_interpreter = sedml_interpreter

            archive_filename = 'tests/fixtures/repeat_initial_assignment.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'reports')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception


    def test_change_to_initial_assignment(self):
        for sedml_interpreter in SedmlInterpreter.__members__.values():
            simulator_config = SimulatorConfig()
            simulator_config.sedml_interpreter = sedml_interpreter

            archive_filename = 'tests/fixtures/change_initial_assignment.omex'

            dirname = os.path.join(self.dirname, sedml_interpreter.name, 'reports')
            _, log = core.exec_sedml_docs_in_combine_archive(archive_filename, dirname, simulator_config=simulator_config)
            if log.exception:
                raise log.exception

    # helper methods
    def _get_combine_archive_exec_env(self):
        return {
            'REPORT_FORMATS': 'h5,csv'
        }

    def _assert_curated_combine_archive_outputs(self, dirname, reports=True, plots=True):
        expected_files = set()

        if reports or plots:
            expected_files.add('reports.h5')
        else:
            self.assertNotIn('reports.h5', os.listdir(dirname))

        if plots:
            expected_files.add('plots.zip')
        else:
            self.assertNotIn('plots.zip', os.listdir(dirname))

        self.assertEqual(expected_files.difference(set(os.listdir(dirname))), set())

        # check that the expected reports where created at the expected locations with the expected values
        if reports:
            if not plots:
                self.assertEqual(set(ReportReader().get_ids(dirname)), set([
                    'ex1/BIOMD0000000297.sedml/report_1_task1',
                    'ex2/BIOMD0000000297.sedml/report_1_task1',
                ]))
            else:
                self.assertEqual(set([
                    'ex1/BIOMD0000000297.sedml/report_1_task1',
                    'ex2/BIOMD0000000297.sedml/report_1_task1',
                ]).difference(set(ReportReader().get_ids(dirname))), set([]))

            report = Report(
                data_sets=[
                    DataSet(id='data_set_time', label='time'),
                    DataSet(id='data_set_PSwe1M', label='PSwe1M'),
                    DataSet(id='data_set_Swe1M', label='Swe1M'),
                    DataSet(id='data_set_Swe1', label='Swe1'),
                ],
            )

            if reports and not plots:
                report.data_sets.append(DataSet(id='data_set_kswe', label='kwse'))
                report.data_sets.append(DataSet(id='data_set_kswe_prime', label="kwse'"))
                report.data_sets.append(DataSet(id='data_set_R1', label="Clb-Sic dissociation"))
                report.data_sets.append(DataSet(id='data_set_compartment', label="compartment"))

            report_results = ReportReader().run(report, dirname, 'ex1/BIOMD0000000297.sedml/report_1_task1')
            for data_set_result in report_results.values():
                self.assertFalse(numpy.any(numpy.isnan(data_set_result)))
            numpy.testing.assert_allclose(report_results[report.data_sets[0].id], numpy.linspace(0., 140., 140 + 1))

            if reports and not plots:
                print(report_results.keys())
                numpy.testing.assert_allclose(report_results['data_set_kswe_prime'], numpy.full((140 + 1,), 2.))
                numpy.testing.assert_allclose(report_results['data_set_compartment'], numpy.full((140 + 1,), 1.))

        # check that expected plots where created at the expected locations
        if plots:
            if not reports:
                self.assertEqual(set(ReportReader().get_ids(dirname)), set([
                    'ex1/BIOMD0000000297.sedml/plot_1_task1',
                    'ex1/BIOMD0000000297.sedml/plot_3_task1',
                    'ex2/BIOMD0000000297.sedml/plot_1_task1',
                    'ex2/BIOMD0000000297.sedml/plot_3_task1',
                ]))
            else:
                self.assertEqual(set([
                    'ex1/BIOMD0000000297.sedml/plot_1_task1',
                    'ex1/BIOMD0000000297.sedml/plot_3_task1',
                    'ex2/BIOMD0000000297.sedml/plot_1_task1',
                    'ex2/BIOMD0000000297.sedml/plot_3_task1',
                ]).difference(set(ReportReader().get_ids(dirname))), set([]))

            plots_dir = os.path.join(self.dirname, 'plots')
            archive = ArchiveReader().run(os.path.join(dirname, 'plots.zip'), plots_dir)
            self.assertEqual(set(file.archive_path for file in archive.files), set([
                'ex1/BIOMD0000000297.sedml/plot_1_task1.pdf',
                'ex1/BIOMD0000000297.sedml/plot_3_task1.pdf',
                'ex2/BIOMD0000000297.sedml/plot_1_task1.pdf',
                'ex2/BIOMD0000000297.sedml/plot_3_task1.pdf',
            ]))

            # check that the plots are valid PDFs
            for archive_file in archive.files:
                with open(archive_file.local_path, 'rb') as file:
                    PyPDF2.PdfReader(file)


class CliTestCase(unittest.TestCase):
    def test_raw_cli(self):
        with mock.patch('sys.argv', ['', '--help']):
            with self.assertRaises(SystemExit) as context:
                __main__.main()
                self.assertRegex(context.Exception, 'usage: ')

if __name__ == "__main__":
    unittest.main()

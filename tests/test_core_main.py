""" Tests of the tellurium command-line interface

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from biosimulators_tellurium import __main__
from biosimulators_tellurium import core
from biosimulators_utils.archive.io import ArchiveReader
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml.data_model import Report, DataSet
from biosimulators_utils.simulator.exec import exec_sedml_docs_in_archive_with_containerized_simulator
from unittest import mock
import numpy
import os
import PyPDF2
import shutil
import tellurium.sedml.tesedml
import tempfile
import unittest


class CliTestCase(unittest.TestCase):
    DOCKER_IMAGE = 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:latest'

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_exec_sedml_docs_in_combine_archive(self):
        # with reports
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports.omex'

        dirname = os.path.join(self.dirname, 'reports')
        core.exec_sedml_docs_in_combine_archive(archive_filename, dirname)

        self._assert_combine_archive_outputs(dirname, reports=True, plots=False)

        # with plots
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-plots.omex'

        dirname = os.path.join(self.dirname, 'plots')
        core.exec_sedml_docs_in_combine_archive(archive_filename, dirname)

        self._assert_combine_archive_outputs(dirname, reports=False, plots=True)

        # with reports and plots
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'

        dirname = os.path.join(self.dirname, 'reports-and-plots')
        core.exec_sedml_docs_in_combine_archive(archive_filename, dirname)

        self._assert_combine_archive_outputs(dirname, reports=True, plots=True)

    def test_exec_sedml_docs_in_combine_archive_with_tellurium_error(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'

        with self.assertRaisesRegex(Exception, 'my error'):
            with mock.patch.object(tellurium.sedml.tesedml.SEDMLCodeFactory, 'executePython', side_effect=Exception('my error')):
                core.exec_sedml_docs_in_combine_archive(archive_filename, self.dirname)

    def test_exec_sedml_docs_in_combine_archive_with_cli(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'
        env = self._get_combine_archive_exec_env()

        with mock.patch.dict(os.environ, env):
            with __main__.App(argv=['-i', archive_filename, '-o', self.dirname]) as app:
                app.run()

        self._assert_combine_archive_outputs(self.dirname, reports=True, plots=True)

    def test_sim_with_docker_image(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297-with-reports-and-plots.omex'
        env = self._get_combine_archive_exec_env()

        exec_sedml_docs_in_archive_with_containerized_simulator(
            archive_filename, self.dirname, self.DOCKER_IMAGE, environment=env, pull_docker_image=False)

        self._assert_combine_archive_outputs(self.dirname, reports=True, plots=True)

    def _get_combine_archive_exec_env(self):
        return {
            'REPORT_FORMATS': 'h5,csv'
        }

    def _assert_combine_archive_outputs(self, dirname, reports=True, plots=True):
        expected_files = set()

        if reports:
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
            self.assertEqual(set(ReportReader().get_ids(dirname)), set([
                'ex1/BIOMD0000000297.sedml/report_1_task1',
                'ex2/BIOMD0000000297.sedml/report_1_task1',
            ]))

            report = Report(
                data_sets=[
                    DataSet(id='data_set_time', label='time'),
                    DataSet(id='data_set_PSwe1M', label='PSwe1M'),
                    DataSet(id='data_set_Swe1M', label='Swe1M'),
                    DataSet(id='data_set_Swe1', label='Swe1'),
                ],
            )

            report_results = ReportReader().run(report, dirname, 'ex1/BIOMD0000000297.sedml/report_1_task1')
            for data_set_result in report_results.values():
                self.assertFalse(numpy.any(numpy.isnan(data_set_result)))
            numpy.testing.assert_allclose(report_results[report.data_sets[0].id], numpy.linspace(0., 140., 140 + 1))

        # check that expected plots where created at the expected locations
        if plots:
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
                    PyPDF2.PdfFileReader(file)

    def test_raw_cli(self):
        with mock.patch('sys.argv', ['', '--help']):
            with self.assertRaises(SystemExit) as context:
                __main__.main()
                self.assertRegex(context.Exception, 'usage: ')

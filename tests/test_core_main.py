""" Tests of the tellurium command-line interface

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from biosimulators_tellurium import __main__
from biosimulators_tellurium import core
from biosimulators_utils.simulator.exec import exec_sedml_docs_in_archive_with_containerized_simulator
from unittest import mock
import os
import PyPDF2
import shutil
import tempfile
import unittest


class CliTestCase(unittest.TestCase):
    DOCKER_IMAGE = 'ghcr.io/biosimulators/biosimulators_tellurium/tellurium:latest'

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_exec_sedml_docs_in_combine_archive(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297.omex'

        core.exec_sedml_docs_in_combine_archive(archive_filename, self.dirname)

        self._assert_combine_archive_outputs(self.dirname)

    def test_exec_sedml_docs_in_combine_archive_with_cli(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297.omex'
        env = self._get_combine_archive_exec_env()

        with mock.patch.dict(os.environ, env):
            with __main__.App(argv=['-i', archive_filename, '-o', self.dirname]) as app:
                app.run()

        self._assert_combine_archive_outputs(self.dirname)

    def test_sim_with_docker_image(self):
        archive_filename = 'tests/fixtures/BIOMD0000000297.omex'
        env = self._get_combine_archive_exec_env()

        exec_sedml_docs_in_archive_with_containerized_simulator(
            archive_filename, self.dirname, self.DOCKER_IMAGE, environment=env, pull_docker_image=False)

        self._assert_combine_archive_outputs(self.dirname)

    def _get_combine_archive_exec_env(self):
        return {
            'REPORT_FORMATS': 'h5,csv'
        }

    def _assert_combine_archive_outputs(self, dirname):
        self.assertEqual(set(os.listdir(dirname)), set(['ex1', 'ex2']))
        self.assertEqual(set(os.listdir(os.path.join(dirname, 'ex1'))), set(['BIOMD0000000297.sedml']))
        self.assertEqual(set(os.listdir(os.path.join(dirname, 'ex2'))), set(['BIOMD0000000297.sedml']))
        self.assertEqual(set(os.listdir(os.path.join(dirname, 'ex1', 'BIOMD0000000297.sedml'))),
                         set(['plot_1_task1.pdf', 'plot_3_task1.pdf']))
        self.assertEqual(set(os.listdir(os.path.join(dirname, 'ex2', 'BIOMD0000000297.sedml'))),
                         set(['plot_1_task1.pdf', 'plot_3_task1.pdf']))

        # check that the plots are valid PDFs
        files = [
            os.path.join(dirname, 'ex1', 'BIOMD0000000297.sedml', 'plot_1_task1.pdf'),
            os.path.join(dirname, 'ex1', 'BIOMD0000000297.sedml', 'plot_3_task1.pdf'),
            os.path.join(dirname, 'ex2', 'BIOMD0000000297.sedml', 'plot_1_task1.pdf'),
            os.path.join(dirname, 'ex2', 'BIOMD0000000297.sedml', 'plot_3_task1.pdf'),
        ]
        for file in files:
            with open(file, 'rb') as file:
                PyPDF2.PdfFileReader(file)

    def test_raw_cli(self):
        with mock.patch('sys.argv', ['', '--help']):
            with self.assertRaises(SystemExit) as context:
                __main__.main()
                self.assertRegex(context.Exception, 'usage: ')

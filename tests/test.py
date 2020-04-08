""" Tests of the tellurium command-line interface

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from Biosimulations_tellurium import __main__
import Biosimulations_tellurium
import capturer
import docker
import imghdr
import os
import shutil
import tempfile
import unittest


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_help(self):
        with self.assertRaises(SystemExit):
            with __main__.App(argv=['--help']) as app:
                app.run()

    def test_version(self):
        with __main__.App(argv=['-v']) as app:
            with capturer.CaptureOutput(merged=False, relay=False) as captured:
                with self.assertRaises(SystemExit):
                    app.run()
                self.assertIn(Biosimulations_tellurium.__version__, captured.stdout.get_text())
                self.assertEqual(captured.stderr.get_text(), '')

        with __main__.App(argv=['--version']) as app:
            with capturer.CaptureOutput(merged=False, relay=False) as captured:
                with self.assertRaises(SystemExit):
                    app.run()
                self.assertIn(Biosimulations_tellurium.__version__, captured.stdout.get_text())
                self.assertEqual(captured.stderr.get_text(), '')

    def test_sim_short_arg_names(self):
        sim_filename = 'tests/fixtures/BIOMD0000000297.sedml'
        with __main__.App(argv=['-i', sim_filename, '-o', self.dirname]) as app:
            app.run()
        self.assert_outputs_created(self.dirname)

    def test_sim_short_long_names(self):
        sim_filename = 'tests/fixtures/BIOMD0000000297.sedml'
        with __main__.App(argv=['--sim-file', sim_filename, '--out-dir', self.dirname]) as app:
            app.run()
        self.assert_outputs_created(self.dirname)

    @unittest.skipIf(os.getenv('CI', '0') in ['1', 'true'], 'Docker not setup in CI')
    def test_build_docker_image(self):
        docker_client = docker.from_env()

        # build image
        image_repo = 'crbm/biosimulations_tellurium'
        image_tag = Biosimulations_tellurium.__version__
        image, _ = docker_client.images.build(
            path='.',
            dockerfile='Dockerfile',
            pull=True,
            rm=True,
        )
        image.tag(image_repo, tag='latest')
        image.tag(image_repo, tag=image_tag)

    @unittest.skipIf(os.getenv('CI', '0') in ['1', 'true'], 'Docker not setup in CI')
    def test_sim_with_docker_image(self):
        docker_client = docker.from_env()

        # image config
        image_repo = 'crbm/biosimulations_tellurium'
        image_tag = Biosimulations_tellurium.__version__

        # setup input and output directories
        in_dir = os.path.join(self.dirname, 'in')
        out_dir = os.path.join(self.dirname, 'out')
        os.makedirs(in_dir)
        os.makedirs(out_dir)

        # copy model and simulation to temporary directory which will be mounted into container
        shutil.copyfile('tests/fixtures/BIOMD0000000297.xml', os.path.join(in_dir, 'BIOMD0000000297.xml'))
        shutil.copyfile('tests/fixtures/BIOMD0000000297.sedml', os.path.join(in_dir, 'BIOMD0000000297.sedml'))

        # run image
        docker_client.containers.run(
            image_repo + ':' + image_tag,
            volumes={
                in_dir: {
                    'bind': '/root/in',
                    'mode': 'ro',
                },
                out_dir: {
                    'bind': '/root/out',
                    'mode': 'rw',
                }
            },
            command=['-i', '/root/in/BIOMD0000000297.sedml', '-o', '/root/out'],
            tty=True,
            remove=True)

        self.assert_outputs_created(out_dir)

    def assert_outputs_created(self, dirname):
        self.assertEqual(set(os.listdir(dirname)), set(['plot_1_task1.png', 'plot_3_task1.png']))
        self.assertEqual(imghdr.what(os.path.join(dirname, 'plot_1_task1.png')), 'png')
        self.assertEqual(imghdr.what(os.path.join(dirname, 'plot_3_task1.png')), 'png')

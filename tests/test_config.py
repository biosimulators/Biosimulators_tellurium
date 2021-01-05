from biosimulators_tellurium.config import Config
from biosimulators_tellurium.data_model import PlottingEngine
from unittest import mock
import os
import unittest


class ConfigTestCase(unittest.TestCase):
    def test_Config(self):
        with mock.patch.dict(os.environ, {'PLOTTING_ENGINE': PlottingEngine.matplotlib.value}):
            self.assertEqual(Config().plotting_engine, PlottingEngine.matplotlib)

        with mock.patch.dict(os.environ, {'PLOTTING_ENGINE': PlottingEngine.plotly.value}):
            self.assertEqual(Config().plotting_engine, PlottingEngine.plotly)

        with mock.patch.dict(os.environ, {'PLOTTING_ENGINE': 'unsupported'}):
            with self.assertRaises(NotImplementedError):
                self.assertEqual(Config().plotting_engine, PlottingEngine.plotly)

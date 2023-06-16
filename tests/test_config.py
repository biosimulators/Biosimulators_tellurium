from biosimulators_tellurium.config import Config
from biosimulators_tellurium.data_model import SedmlInterpreter, PlottingEngine
from unittest import mock
import os
import unittest


class ConfigTestCase(unittest.TestCase):
    def test_Config(self):
        # SED-ML interpeter
        with mock.patch.dict(os.environ, {'SEDML_INTERPRETER': SedmlInterpreter.biosimulators.value}):
            self.assertEqual(Config().sedml_interpreter, SedmlInterpreter.biosimulators)

        with mock.patch.dict(os.environ, {'SEDML_INTERPRETER': SedmlInterpreter.tellurium.value}):
            self.assertEqual(Config().sedml_interpreter, SedmlInterpreter.tellurium)

        with mock.patch.dict(os.environ, {'SEDML_INTERPRETER': 'unsupported'}):
            with self.assertRaises(NotImplementedError):
                Config()

        # plotting engine
        with mock.patch.dict(os.environ, {'PLOTTING_ENGINE': PlottingEngine.matplotlib.value}):
            self.assertEqual(Config().plotting_engine, PlottingEngine.matplotlib)

        with mock.patch.dict(os.environ, {'PLOTTING_ENGINE': PlottingEngine.plotly.value}):
            self.assertEqual(Config().plotting_engine, PlottingEngine.plotly)

        with mock.patch.dict(os.environ, {'PLOTTING_ENGINE': 'unsupported'}):
            with self.assertRaises(NotImplementedError):
                Config()

if __name__ == "__main__":
    unittest.main()

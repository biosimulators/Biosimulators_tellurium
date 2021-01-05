from biosimulators_tellurium.data_model import PlottingEngine
import unittest


class DataModelTestCase(unittest.TestCase):
    def test_PlottingEngine(self):
        self.assertEqual(PlottingEngine.matplotlib.value, 'matplotlib')
        self.assertEqual(PlottingEngine.plotly.value, 'plotly')

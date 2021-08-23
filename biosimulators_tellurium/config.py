""" Configuration

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import SedmlInterpreter, PlottingEngine
import os

__all__ = ['Config']


class Config(object):
    """ Configuration

    Attributes:
        sedml_interpreter (:obj:`SedmlInterpreter`): SED-ML interpreter
        plotting_engine (:obj:`PlottingEngine`): plotting engine
    """

    def __init__(self):
        sedml_interpreter = os.getenv('SEDML_INTERPRETER', SedmlInterpreter.biosimulators.name)
        if sedml_interpreter not in SedmlInterpreter.__members__:
            raise NotImplementedError(('`{}` is a not a supported SED-ML interpreter. '
                                       'The following SED-ML interpreters are supported:\n  - {}').format(
                sedml_interpreter, '\n  - '.join(sorted('`' + name + '`' for name in SedmlInterpreter.__members__.keys()))))

        self.sedml_interpreter = SedmlInterpreter[sedml_interpreter]

        plotting_engine = os.getenv('PLOTTING_ENGINE', PlottingEngine.matplotlib.name)
        if plotting_engine not in PlottingEngine.__members__:
            raise NotImplementedError(('`{}` is a not a supported plotting engine. '
                                       'The following plotting engines are supported:\n  - {}').format(
                plotting_engine, '\n  - '.join(sorted('`' + name + '`' for name in PlottingEngine.__members__.keys()))))

        self.plotting_engine = PlottingEngine[plotting_engine]

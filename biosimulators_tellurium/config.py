""" Configuration

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import PlottingEngine
import os

__all__ = ['Config']


class Config(object):
    """ Configuration

    Attributes:
        plotting_engine (:obj:`PlottingEngine`): plotting engine
    """

    def __init__(self):
        plotting_engine = os.getenv('PLOTTING_ENGINE', 'matplotlib')
        if plotting_engine not in PlottingEngine.__members__:
            raise NotImplementedError(('`{}` is a not a valid plotting engine for tellurium. '
                                       'tellurium supports the following plotting engines:\n  - {}').format(
                plotting_engine, '\n  - '.join(sorted('`' + name + '`' for name in PlottingEngine.__members__.keys()))))

        self.plotting_engine = PlottingEngine[plotting_engine]

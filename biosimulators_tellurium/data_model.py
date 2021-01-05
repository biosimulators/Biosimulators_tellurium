""" Data model for working with tellurium to execute COMBINE/OMEX archives

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-04
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import enum

__all__ = [
    'PlottingEngine',
]


class PlottingEngine(str, enum.Enum):
    """ Engine that tellurium uses for plottting """
    matplotlib = 'matplotlib'
    plotly = 'plotly'

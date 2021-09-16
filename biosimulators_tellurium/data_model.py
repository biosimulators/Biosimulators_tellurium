""" Data model for using tellurium to execute SED-ML documents

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-08-23
:Copyright: 2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from biosimulators_utils.data_model import ValueType
import collections
import dataclasses
import enum
import roadrunner
import typing

__all__ = [
    'SedmlInterpreter',
    'PlottingEngine',
    'KISAO_ALGORITHM_MAP',
    'PreprocesssedTask',
]


class SedmlInterpreter(str, enum.Enum):
    """ Code that interprets SED-ML """
    biosimulators = 'biosimulators'  # biosimulators_utils.sedml.exec
    tellurium = 'tellurium'  # tellurium.sedml.tesedml import SEDMLCodeFactory


class PlottingEngine(str, enum.Enum):
    """ Engine that tellurium uses for plottting """
    matplotlib = 'matplotlib'
    plotly = 'plotly'


KISAO_ALGORITHM_MAP = collections.OrderedDict([
    ('KISAO_0000019', {
        'kisao_id': 'KISAO_0000019',
        'id': 'cvode',
        'name': "CVODE",
        'parameters': {
            'KISAO_0000209': {
                'kisao_id': 'KISAO_0000209',
                'id': 'relative_tolerance',
                'name': 'relative tolerance',
                'type': ValueType.float,
                'default': 0.000001,
            },
            'KISAO_0000211': {
                'kisao_id': 'KISAO_0000211',
                'id': 'absolute_tolerance',
                'name': 'absolute tolerance',
                'type': ValueType.float,
                'default': 1e-12,
            },
            'KISAO_0000220': {
                'kisao_id': 'KISAO_0000220',
                'id': 'maximum_bdf_order',
                'name': 'Maximum Backward Differentiation Formula (BDF) order',
                'type': ValueType.integer,
                'default': 5,
            },
            'KISAO_0000219': {
                'kisao_id': 'KISAO_0000219',
                'id': 'maximum_adams_order',
                'name': 'Maximum Adams order',
                'type': ValueType.integer,
                'default': 12,
            },
            'KISAO_0000415': {
                'kisao_id': 'KISAO_0000415',
                'id': 'maximum_num_steps',
                'name': 'Maximum number of steps',
                'type': ValueType.integer,
                'default': 20000,
            },
            'KISAO_0000467': {
                'kisao_id': 'KISAO_0000467',
                'id': 'maximum_time_step',
                'name': 'Maximum time step',
                'type': ValueType.float,
                'default': None,
            },
            'KISAO_0000485': {
                'kisao_id': 'KISAO_0000485',
                'id': 'minimum_time_step',
                'name': 'Minimum time step',
                'type': ValueType.float,
                'default': None,
            },
            'KISAO_0000559': {
                'kisao_id': 'KISAO_0000559',
                'id': 'initial_time_step',
                'name': 'Initial time step',
                'type': ValueType.float,
                'default': None,
            },
            'KISAO_0000671': {
                'kisao_id': 'KISAO_0000671',
                'id': 'stiff',
                'name': 'Stiff',
                'type': ValueType.boolean,
                'default': True,
            },
            'KISAO_0000670': {
                'kisao_id': 'KISAO_0000670',
                'id': 'multiple_steps',
                'name': 'Multiple steps',
                'type': ValueType.boolean,
                'default': False,
            },
        },
    }),
    ('KISAO_0000030', {
        'kisao_id': 'KISAO_0000030',
        'id': 'euler',
        'name': "Forward Euler method",
        'parameters': {}
    }),
    ('KISAO_0000032', {
        'kisao_id': 'KISAO_0000032',
        'id': 'rk4',
        'name': "Runge-Kutta fourth order method",
        'parameters': {}
    }),
    ('KISAO_0000086', {
        'kisao_id': 'KISAO_0000086',
        'id': 'rk45',
        'name': "Fehlberg method",
        'parameters': {
            'KISAO_0000467': {
                'kisao_id': 'KISAO_0000467',
                'id': 'maximum_time_step',
                'name': 'Maximum time step',
                'type': ValueType.float,
                'default': 1.0,
            },
            'KISAO_0000485': {
                'kisao_id': 'KISAO_0000485',
                'id': 'minimum_time_step',
                'name': 'Minimum time step',
                'type': ValueType.float,
                'default': 1e-12,
            },
            'KISAO_0000597': {
                'kisao_id': 'KISAO_0000597',
                'id': 'epsilon',
                'name': 'Epsilon',
                'type': ValueType.float,
                'default': 0.000000000001,
            },
        }
    }),
    ('KISAO_0000029', {
        'kisao_id': 'KISAO_0000029',
        'id': 'gillespie',
        'name': "Gillespie direct method of the Stochastic Simulation Algorithm (SSA)",
        'parameters': {
            'KISAO_0000488': {
                'kisao_id': 'KISAO_0000488',
                'id': 'seed',
                'name': 'Random number generator seed',
                'type': ValueType.integer,
                'default': None,
            },
            'KISAO_0000673': {
                'kisao_id': 'KISAO_0000673',
                'id': 'nonnegative',
                'name': 'Skip reactions which would result in negative species amounts',
                'type': ValueType.boolean,
                'default': False,
            },
        }
    }),
    ('KISAO_0000569', {
        'kisao_id': 'KISAO_0000569',
        'id': 'nleq2',
        'name': "Newton-type method for solveing non-linear (NL) equations (EQ)",
        'parameters': {
            'KISAO_0000209': {
                'kisao_id': 'KISAO_0000209',
                'id': 'relative_tolerance',
                'name': 'Relative tolerance',
                'type': ValueType.float,
                'default': 1e-12,
            },
            'KISAO_0000486': {
                'kisao_id': 'KISAO_0000486',
                'id': 'maximum_iterations',
                'name': 'Maximum number of iterations',
                'type': ValueType.integer,
                'default': 100,
            },
            'KISAO_0000487': {
                'kisao_id': 'KISAO_0000487',
                'id': 'minimum_damping',
                'name': 'Minimum damping factor',
                'type': ValueType.float,
                'default': 1e-20,
            },
            'KISAO_0000674': {
                'kisao_id': 'KISAO_0000674',
                'id': 'allow_presimulation',
                'name': 'Presimulate',
                'type': ValueType.boolean,
                'default': False,
            },
            'KISAO_0000675': {
                'kisao_id': 'KISAO_0000675',
                'id': 'broyden_method',
                'name': 'Broyden method',
                'type': ValueType.integer,
                'default': 0,
            },
            'KISAO_0000676': {
                'kisao_id': 'KISAO_0000676',
                'id': 'linearity',
                'name': 'Degree of linearity',
                'type': ValueType.integer,
                'default': 3,
            },
            'KISAO_0000677': {
                'kisao_id': 'KISAO_0000677',
                'id': 'presimulation_maximum_steps',
                'name': 'Maximum number of steps for presimulation',
                'type': ValueType.integer,
                'default': 100,
            },
            'KISAO_0000678': {
                'kisao_id': 'KISAO_0000678',
                'id': 'approx_maximum_steps',
                'name': 'Maximum number of steps for approximation',
                'type': ValueType.integer,
                'default': 10000,
            },
            'KISAO_0000679': {
                'kisao_id': 'KISAO_0000679',
                'id': 'approx_time',
                'name': 'Maximum amount of time for approximation',
                'type': ValueType.float,
                'default': 10000,
            },
            'KISAO_0000680': {
                'kisao_id': 'KISAO_0000680',
                'id': 'presimulation_time',
                'name': 'Amount of time to presimulate',
                'type': ValueType.float,
                'default': 100,
            },

            'KISAO_0000682': {
                'kisao_id': 'KISAO_0000682',
                'id': 'allow_approx',
                'name': 'Whether to find an approximate solution if an exact solution could not be found',
                'type': ValueType.boolean,
                'default': False,
            },
            'KISAO_0000683': {
                'kisao_id': 'KISAO_0000683',
                'id': 'approx_tolerance',
                'name': 'Relative tolerance for an approximate solution',
                'type': ValueType.float,
                'default': 0.000001,
            },
        }
    }),
])


@dataclasses.dataclass
class PreprocesssedTask(object):
    """ Processed information about a SED task

    Attributes:
        road_runner (:obj:`roadrunner.RoadRunner`): Road Runner instance with model
        solver (:obj:`roadrunner.Integrator` or :obj:`roadrunner.SteadyStateSolver`): solver
        model_change_target_tellurium_id_map (:obj:`dict`): dictionary that maps the targets of
            changes to their corresponding tellurium identifiers (tuples of their type and index within their type)
        algorithm_kisao_id (:obj:`str`): KiSAO id of algorithm to execute
        variable_target_tellurium_observable_map (:obj:`dict`): dictionary that maps tuples of variable targets and
            symbols to their corresponding tellurium observable identifiers
    """
    road_runner: roadrunner.RoadRunner
    solver: typing.Union[roadrunner.Integrator, roadrunner.SteadyStateSolver]
    model_change_target_tellurium_id_map: dict
    algorithm_kisao_id: str
    variable_target_tellurium_observable_map: dict

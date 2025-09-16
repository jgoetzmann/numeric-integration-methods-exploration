"""
Novel Numerical Integration Methods

A machine learning system for discovering new Runge-Kutta integration schemes (Butcher tables)
that can outperform classical methods in terms of accuracy, efficiency, and stability.
"""

__version__ = "1.0.0"
__author__ = "Jack Goetzmann"
__email__ = "jmgoetzmann6@gmail.com"

# Core modules
from .core import butcher_tables, integrator_runner, metrics, ode_dataset
from .models import model
from .training import train
from .storage import database
from .visualization import visualization

__all__ = [
    "butcher_tables",
    "integrator_runner", 
    "metrics",
    "ode_dataset",
    "model",
    "train",
    "database",
    "visualization"
]

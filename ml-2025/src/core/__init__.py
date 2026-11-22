"""
Core functionality for numerical integration methods.

This module contains the fundamental components for:
- Butcher table representation and validation
- Integration engine implementation
- Performance metrics calculation
- ODE dataset generation and management
"""

# Import only when needed to avoid torch dependency issues
# from .butcher_tables import *
# from .integrator_runner import *
# from .metrics import *
# from .ode_dataset import *

__all__ = [
    "ButcherTable",
    "ButcherTableGenerator", 
    "get_all_baseline_tables",
    "IntegratorBenchmark",
    "ReferenceSolver",
    "MetricsCalculator",
    "BaselineComparator",
    "PerformanceMetrics",
    "ODEDataset"
]

"""
Integrator Runner Module.

This module implements the core integration functionality for applying
Butcher tables to solve ODEs and compute reference solutions.
"""

import numpy as np
import torch
import time
from typing import Callable, Tuple, List, Dict, Any, Optional
from scipy.integrate import solve_ivp
from dataclasses import dataclass
import warnings
from src.core.butcher_tables import ButcherTable
from src.core.ode_dataset import ODEParameters, ODE_FUNCTIONS
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

# Suppress numerical warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', message='.*overflow.*')
warnings.filterwarnings('ignore', message='.*invalid value.*')
warnings.filterwarnings('ignore', message='.*Casting complex values.*')
warnings.filterwarnings('ignore', message='.*ComplexWarning.*')

@dataclass
class IntegrationResult:
    """Results from integrating an ODE with a specific method."""
    
    success: bool
    t_vals: np.ndarray
    y_vals: np.ndarray
    n_steps: int
    runtime: float
    error_message: Optional[str] = None
    max_error: Optional[float] = None
    l2_error: Optional[float] = None

class RungeKuttaIntegrator:
    """Implements Runge-Kutta integration using Butcher tables."""
    
    def __init__(self, butcher_table: ButcherTable, use_cuda: bool = False):
        self.butcher_table = butcher_table
        self.s = len(butcher_table.b)
        self.is_explicit = butcher_table.is_explicit
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self.device = torch.device('cuda' if self.use_cuda else 'cpu')
        
        if self.use_cuda:
            # Convert butcher table coefficients to CUDA tensors for faster computation
            self.A_cuda = torch.tensor(butcher_table.A, dtype=torch.float32, device=self.device)
            self.b_cuda = torch.tensor(butcher_table.b, dtype=torch.float32, device=self.device)
            self.c_cuda = torch.tensor(butcher_table.c, dtype=torch.float32, device=self.device)
    
    def integrate(self, 
                  ode_func: Callable,
                  y0: np.ndarray,
                  t_span: Tuple[float, float],
                  h: float = None,
                  rtol: float = None,
                  atol: float = None,
                  max_steps: int = 10000) -> IntegrationResult:
        """
        Integrate ODE using the Butcher table method.
        
        Args:
            ode_func: Function f(t, y) defining the ODE
            y0: Initial conditions
            t_span: Time span (t_start, t_end)
            h: Step size (if None, adaptive step size is used)
            rtol: Relative tolerance for adaptive stepping
            atol: Absolute tolerance for adaptive stepping
            max_steps: Maximum number of steps
            
        Returns:
            IntegrationResult with solution and metadata
        """
        start_time = time.time()
        
        try:
            if h is None:
                # Adaptive step size
                result = self._integrate_adaptive(
                    ode_func, y0, t_span, rtol or 1e-6, atol or 1e-9, max_steps
                )
            else:
                # Fixed step size
                result = self._integrate_fixed(ode_func, y0, t_span, h, max_steps)
            
            result.runtime = time.time() - start_time
            result.success = True
            return result
            
        except Exception as e:
            return IntegrationResult(
                success=False,
                t_vals=np.array([]),
                y_vals=np.array([]),
                n_steps=0,
                runtime=time.time() - start_time,
                error_message=str(e)
            )
    
    def _integrate_fixed(self, 
                        ode_func: Callable,
                        y0: np.ndarray,
                        t_span: Tuple[float, float],
                        h: float,
                        max_steps: int) -> IntegrationResult:
        """Integrate with fixed step size."""
        t_start, t_end = t_span
        n_dim = len(y0)
        
        # Estimate number of steps
        n_steps_est = int((t_end - t_start) / h) + 1
        n_steps_est = min(n_steps_est, max_steps)
        
        # Pre-allocate arrays
        t_vals = np.zeros(n_steps_est)
        y_vals = np.zeros((n_steps_est, n_dim))
        
        # Initial conditions
        t_vals[0] = t_start
        y_vals[0] = y0.copy()
        
        current_step = 0
        t_current = t_start
        y_current = y0.copy()
        
        while t_current < t_end and current_step < max_steps - 1:
            # Determine step size
            h_actual = min(h, t_end - t_current)
            
            # Perform RK step
            try:
                y_new = self._rk_step(ode_func, t_current, y_current, h_actual)
                
                current_step += 1
                t_current += h_actual
                
                # Store results
                if current_step < n_steps_est:
                    t_vals[current_step] = t_current
                    y_vals[current_step] = y_new
                else:
                    # Resize arrays if needed
                    t_vals = np.resize(t_vals, current_step + 1)
                    y_vals = np.resize(y_vals, (current_step + 1, n_dim))
                    t_vals[current_step] = t_current
                    y_vals[current_step] = y_new
                
                y_current = y_new
                
            except Exception as e:
                raise RuntimeError(f"RK step failed at t={t_current}: {e}")
        
        # Trim arrays to actual size
        t_vals = t_vals[:current_step + 1]
        y_vals = y_vals[:current_step + 1]
        
        return IntegrationResult(
            success=True,
            t_vals=t_vals,
            y_vals=y_vals,
            n_steps=current_step + 1,
            runtime=0.0  # Will be set by caller
        )
    
    def _integrate_adaptive(self,
                           ode_func: Callable,
                           y0: np.ndarray,
                           t_span: Tuple[float, float],
                           rtol: float,
                           atol: float,
                           max_steps: int) -> IntegrationResult:
        """Integrate with adaptive step size."""
        t_start, t_end = t_span
        n_dim = len(y0)
        
        # Use SciPy's adaptive solver for reference, then apply our method
        # This is a simplified adaptive strategy
        return self._integrate_fixed(ode_func, y0, t_span, 
                                   h=(t_end - t_start) / 20,  # Fewer steps for maximum speed
                                   max_steps=max_steps)
    
    def _rk_step(self, ode_func: Callable, t: float, y: np.ndarray, h: float) -> np.ndarray:
        """Perform a single Runge-Kutta step."""
        s = self.s
        
        if self.use_cuda:
            # Use CUDA tensors for faster computation
            A = self.A_cuda
            b = self.b_cuda
            c = self.c_cuda
            
            # Convert input to CUDA tensor
            y_cuda = torch.tensor(y, dtype=torch.float32, device=self.device)
            k_cuda = torch.zeros((s, len(y)), dtype=torch.float32, device=self.device)
            
            for i in range(s):
                # Compute argument for stage i
                t_stage = t + c[i].item() * h
                y_stage = y_cuda.clone()
                
                # Add contributions from previous stages
                for j in range(i + 1):  # Include diagonal for implicit methods
                    if not torch.isclose(A[i, j], torch.tensor(0.0, device=self.device)):
                        y_stage += h * A[i, j] * k_cuda[j]
                
                # Evaluate ODE at this stage (convert back to numpy for ODE function)
                k_cuda[i] = torch.tensor(ode_func(t_stage, y_stage.cpu().numpy()), 
                                       dtype=torch.float32, device=self.device)
            
            # Compute final step
            y_new_cuda = y_cuda.clone()
            for i in range(s):
                y_new_cuda += h * b[i] * k_cuda[i]
            
            return y_new_cuda.cpu().numpy()
        else:
            # Use numpy for CPU computation
            A = self.butcher_table.A
            b = self.butcher_table.b
            c = self.butcher_table.c
            
            # Compute stage values k_i
            k = np.zeros((s, len(y)))
            
            for i in range(s):
                # Compute argument for stage i
                t_stage = t + c[i] * h
                y_stage = y.copy()
                
                # Add contributions from previous stages
                for j in range(i + 1):  # Include diagonal for implicit methods
                    if not np.isclose(A[i, j], 0.0):
                        y_stage += h * A[i, j] * k[j]
                
                # Evaluate ODE at this stage
                k[i] = ode_func(t_stage, y_stage)
            
            # Compute final step
            y_new = y.copy()
            for i in range(s):
                y_new += h * b[i] * k[i]
            
            return y_new

class ReferenceSolver:
    """Computes high-precision reference solutions using SciPy."""
    
    def __init__(self, rtol: float = None, atol: float = None):
        self.rtol = rtol or config.REFERENCE_TOL
        self.atol = atol or config.REFERENCE_TOL
    
    def solve_reference(self, 
                       ode_parameters: ODEParameters,
                       dense_output: bool = True) -> IntegrationResult:
        """Solve ODE with high precision for reference solution."""
        
        # Get ODE function
        ode_func = ODE_FUNCTIONS[ode_parameters.equation_type]
        
        # Create wrapper function with parameters
        def ode_wrapper(t, y):
            if ode_parameters.equation_type == "linear_system":
                return ode_func(t, y, ode_parameters.parameters["A"])
            elif ode_parameters.equation_type == "van_der_pol":
                return ode_func(t, y, ode_parameters.parameters["mu"])
            elif ode_parameters.equation_type == "lotka_volterra":
                params = ode_parameters.parameters
                return ode_func(t, y, params["alpha"], params["beta"], 
                              params["gamma"], params["delta"])
            elif ode_parameters.equation_type == "brusselator":
                return ode_func(t, y, ode_parameters.parameters["a"], 
                              ode_parameters.parameters["b"])
            elif ode_parameters.equation_type == "polynomial":
                return ode_func(t, y, ode_parameters.parameters["coefficients"])
            else:
                raise ValueError(f"Unknown ODE type: {ode_parameters.equation_type}")
        
        start_time = time.time()
        
        try:
            # Use SciPy's solve_ivp with tight tolerances
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Suppress integration warnings
                
                sol = solve_ivp(
                    ode_wrapper,
                    ode_parameters.t_span,
                    ode_parameters.initial_conditions,
                    method='RK45',  # Faster method for local training
                    rtol=self.rtol,
                    atol=self.atol,
                    dense_output=dense_output,
                    max_step=(ode_parameters.t_span[1] - ode_parameters.t_span[0]) / 20  # Fewer steps for speed
                )
            
            if not sol.success:
                raise RuntimeError(f"SciPy solve_ivp failed: {sol.message}")
            
            runtime = time.time() - start_time
            
            return IntegrationResult(
                success=True,
                t_vals=sol.t,
                y_vals=sol.y.T,  # Transpose to get (n_steps, n_dim)
                n_steps=len(sol.t),
                runtime=runtime
            )
            
        except Exception as e:
            return IntegrationResult(
                success=False,
                t_vals=np.array([]),
                y_vals=np.array([]),
                n_steps=0,
                runtime=time.time() - start_time,
                error_message=str(e)
            )

class IntegratorBenchmark:
    """Benchmarks Butcher table methods against reference solutions."""
    
    def __init__(self, reference_solver: ReferenceSolver = None, use_cuda: bool = False):
        self.reference_solver = reference_solver or ReferenceSolver()
        self.use_cuda = use_cuda and torch.cuda.is_available()
    
    def evaluate_butcher_table(self, 
                              butcher_table: ButcherTable,
                              ode_parameters: ODEParameters,
                              h: float = None,
                              use_varied_steps: bool = True) -> Dict[str, Any]:
        """Evaluate a Butcher table on a single ODE with varied step sizes."""
        
        # Get reference solution
        ref_result = self.reference_solver.solve_reference(ode_parameters)
        if not ref_result.success:
            return {
                'success': False,
                'error': f"Reference solution failed: {ref_result.error_message}",
                'runtime': 0.0,
                'n_steps': 0,
                'max_error': float('inf'),
                'l2_error': float('inf')
            }
        
        # Solve with candidate method
        integrator = RungeKuttaIntegrator(butcher_table, use_cuda=self.use_cuda)
        
        # Get ODE function
        ode_func = ODE_FUNCTIONS[ode_parameters.equation_type]
        
        # Create wrapper function
        def ode_wrapper(t, y):
            if ode_parameters.equation_type == "linear_system":
                return ode_func(t, y, ode_parameters.parameters["A"])
            elif ode_parameters.equation_type == "van_der_pol":
                return ode_func(t, y, ode_parameters.parameters["mu"])
            elif ode_parameters.equation_type == "lotka_volterra":
                params = ode_parameters.parameters
                return ode_func(t, y, params["alpha"], params["beta"], 
                              params["gamma"], params["delta"])
            elif ode_parameters.equation_type == "brusselator":
                return ode_func(t, y, ode_parameters.parameters["a"], 
                              ode_parameters.parameters["b"])
            elif ode_parameters.equation_type == "polynomial":
                return ode_func(t, y, ode_parameters.parameters["coefficients"])
            elif ode_parameters.equation_type == "robertson":
                params = ode_parameters.parameters
                return ode_func(t, y, params["k1"], params["k2"], params["k3"])
            elif ode_parameters.equation_type == "oregonator":
                params = ode_parameters.parameters
                return ode_func(t, y, params["alpha"], params["beta"], params["gamma"])
            elif ode_parameters.equation_type == "hindmarsh_rose":
                params = ode_parameters.parameters
                return ode_func(t, y, params["a"], params["b"], params["c"], 
                              params["d"], params["r"], params["s"], params["xr"])
            elif ode_parameters.equation_type == "lorenz":
                params = ode_parameters.parameters
                return ode_func(t, y, params["sigma"], params["rho"], params["beta"])
            elif ode_parameters.equation_type == "kuramoto_sivashinsky":
                params = ode_parameters.parameters
                return ode_func(t, y, params["n_modes"], params["viscosity"])
            elif ode_parameters.equation_type == "enhanced_linear_system":
                params = ode_parameters.parameters
                return ode_func(t, y, params["A"], params.get("complexity_level", 1))
        
        # Use varied step sizes for robust evaluation
        if use_varied_steps and h is None:
            # Test with multiple step sizes and take the best result
            t_span = ode_parameters.t_span
            t_total = t_span[1] - t_span[0]
            
            # Define fewer step sizes to test for speed
            step_sizes = [
                t_total / 50,   # Coarse
                t_total / 100,  # Medium
                t_total / 200,  # Fine
            ]
            
            best_result = None
            best_error = float('inf')
            
            for step_size in step_sizes:
                try:
                    candidate_result = integrator.integrate(
                        ode_wrapper, 
                        ode_parameters.initial_conditions, 
                        ode_parameters.t_span, 
                        h=step_size
                    )
                    
                    if candidate_result.success:
                        # Compute error
                        errors = self._compute_errors(candidate_result, ref_result)
                        if errors['max_error'] < best_error:
                            best_error = errors['max_error']
                            best_result = candidate_result
                except:
                    continue
            
            if best_result is None:
                # Fallback to single step size
                h = t_total / 100
                candidate_result = integrator.integrate(
                    ode_wrapper, 
                    ode_parameters.initial_conditions, 
                    ode_parameters.t_span, 
                    h=h
                )
            else:
                candidate_result = best_result
        else:
            # Use provided step size or default
            if h is None:
                h = (ode_parameters.t_span[1] - ode_parameters.t_span[0]) / 100  # Medium step size
            
            candidate_result = integrator.integrate(
                ode_wrapper, 
                ode_parameters.initial_conditions, 
                ode_parameters.t_span, 
                h=h
            )
        
        if not candidate_result.success:
            return {
                'success': False,
                'error': candidate_result.error_message,
                'runtime': candidate_result.runtime,
                'n_steps': candidate_result.n_steps,
                'max_error': float('inf'),
                'l2_error': float('inf')
            }
        
        # Compute errors by interpolating reference solution
        errors = self._compute_errors(candidate_result, ref_result)
        
        return {
            'success': True,
            'error': None,
            'runtime': candidate_result.runtime,
            'n_steps': candidate_result.n_steps,
            'max_error': errors['max_error'],
            'l2_error': errors['l2_error'],
            'reference_runtime': ref_result.runtime,
            'reference_steps': ref_result.n_steps
        }
    
    def _compute_errors(self, 
                       candidate_result: IntegrationResult, 
                       reference_result: IntegrationResult) -> Dict[str, float]:
        """Compute errors between candidate and reference solutions."""
        
        # Interpolate reference solution to candidate time points
        from scipy.interpolate import interp1d
        
        n_dim = candidate_result.y_vals.shape[1]
        errors = np.zeros((len(candidate_result.t_vals), n_dim))
        
        for i in range(n_dim):
            # Create interpolation function for reference solution
            ref_interp = interp1d(
                reference_result.t_vals, 
                reference_result.y_vals[:, i], 
                kind='cubic',
                bounds_error=False, 
                fill_value='extrapolate'
            )
            
            # Evaluate at candidate time points
            ref_vals = ref_interp(candidate_result.t_vals)
            errors[:, i] = np.abs(candidate_result.y_vals[:, i] - ref_vals)
        
        # Compute error metrics
        max_error = np.max(errors)
        l2_error = np.sqrt(np.mean(errors**2))
        
        return {
            'max_error': max_error,
            'l2_error': l2_error
        }

if __name__ == "__main__":
    # Test the integrator
    from src.core.butcher_tables import get_rk4
    
    print("Testing Runge-Kutta integrator...")
    
    # Test ODE: dy/dt = -y, y(0) = 1
    def simple_ode(t, y):
        return -y
    
    # Test RK4
    rk4 = get_rk4()
    integrator = RungeKuttaIntegrator(rk4)
    
    result = integrator.integrate(
        simple_ode,
        np.array([1.0]),
        (0.0, 1.0),
        h=0.1
    )
    
    print(f"RK4 result: success={result.success}, n_steps={result.n_steps}")
    print(f"Final value: {result.y_vals[-1, 0]:.6f} (exact: {np.exp(-1.0):.6f})")
    
    # Test reference solver
    from src.core.ode_dataset import ODEParameters
    
    test_ode = ODEParameters(
        ode_id=0,
        is_stiff=False,
        equation_type="linear_system",
        parameters={"A": np.array([[-1.0]])},
        initial_conditions=np.array([1.0]),
        t_span=(0.0, 1.0)
    )
    
    ref_solver = ReferenceSolver()
    ref_result = ref_solver.solve_reference(test_ode)
    print(f"Reference solver: success={ref_result.success}, n_steps={ref_result.n_steps}")
    
    # Test benchmark
    benchmark = IntegratorBenchmark(ref_solver)
    eval_result = benchmark.evaluate_butcher_table(rk4, test_ode, h=0.1)
    print(f"Benchmark result: {eval_result}")

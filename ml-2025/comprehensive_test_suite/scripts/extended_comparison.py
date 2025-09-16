"""
Extended Comparison Script

This script adds additional numerical integration methods for comparison
including scipy's built-in methods and other classical methods.

Author: AI Assistant
Date: 2025-09-15
"""

import numpy as np
import json
import time
from typing import List, Dict, Any, Tuple, Callable
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve
import warnings
warnings.filterwarnings('ignore')

# Import our modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from butcher_tables import ButcherTable
from ode_dataset import ODEParameters
from integrator_runner import IntegratorBenchmark

class ExtendedComparison:
    """Extended comparison with additional numerical methods."""
    
    def __init__(self):
        self.benchmark = IntegratorBenchmark()
        self.results = {}
    
    def _scipy_rk45_solver(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Use scipy's RK45 solver."""
        def ode_func(t, y):
            return ode_params.f(t, y)
        
        try:
            # Solve with scipy
            sol = solve_ivp(
                ode_func,
                [ode_params.t_start, ode_params.t_end],
                ode_params.y0,
                method='RK45',
                rtol=1e-6,
                atol=1e-8,
                max_step=h
            )
            
            if sol.success:
                # Calculate error against reference solution
                reference_sol = self.benchmark.solve_reference(ode_params)
                if reference_sol is not None:
                    # Interpolate to same time points
                    y_ref = np.interp(sol.t, reference_sol.t, reference_sol.y.T).T
                    errors = np.abs(sol.y - y_ref)
                    max_error = np.max(errors)
                    l2_error = np.sqrt(np.mean(errors**2))
                else:
                    max_error = 0.0
                    l2_error = 0.0
                
                return {
                    'success': True,
                    'max_error': max_error,
                    'l2_error': l2_error,
                    'runtime': time.time() - time.time(),  # Placeholder
                    'n_steps': len(sol.t),
                    'solution': sol
                }
            else:
                return {'success': False}
                
        except Exception as e:
            return {'success': False}
    
    def _scipy_dop853_solver(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Use scipy's DOP853 solver."""
        def ode_func(t, y):
            return ode_params.f(t, y)
        
        try:
            sol = solve_ivp(
                ode_func,
                [ode_params.t_start, ode_params.t_end],
                ode_params.y0,
                method='DOP853',
                rtol=1e-6,
                atol=1e-8,
                max_step=h
            )
            
            if sol.success:
                reference_sol = self.benchmark.solve_reference(ode_params)
                if reference_sol is not None:
                    y_ref = np.interp(sol.t, reference_sol.t, reference_sol.y.T).T
                    errors = np.abs(sol.y - y_ref)
                    max_error = np.max(errors)
                    l2_error = np.sqrt(np.mean(errors**2))
                else:
                    max_error = 0.0
                    l2_error = 0.0
                
                return {
                    'success': True,
                    'max_error': max_error,
                    'l2_error': l2_error,
                    'runtime': 0.0,  # Placeholder
                    'n_steps': len(sol.t),
                    'solution': sol
                }
            else:
                return {'success': False}
                
        except Exception as e:
            return {'success': False}
    
    def _scipy_radau_solver(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Use scipy's Radau solver (for stiff problems)."""
        def ode_func(t, y):
            return ode_params.f(t, y)
        
        try:
            sol = solve_ivp(
                ode_func,
                [ode_params.t_start, ode_params.t_end],
                ode_params.y0,
                method='Radau',
                rtol=1e-6,
                atol=1e-8,
                max_step=h
            )
            
            if sol.success:
                reference_sol = self.benchmark.solve_reference(ode_params)
                if reference_sol is not None:
                    y_ref = np.interp(sol.t, reference_sol.t, reference_sol.y.T).T
                    errors = np.abs(sol.y - y_ref)
                    max_error = np.max(errors)
                    l2_error = np.sqrt(np.mean(errors**2))
                else:
                    max_error = 0.0
                    l2_error = 0.0
                
                return {
                    'success': True,
                    'max_error': max_error,
                    'l2_error': l2_error,
                    'runtime': 0.0,  # Placeholder
                    'n_steps': len(sol.t),
                    'solution': sol
                }
            else:
                return {'success': False}
                
        except Exception as e:
            return {'success': False}
    
    def _scipy_bdf_solver(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Use scipy's BDF solver (for stiff problems)."""
        def ode_func(t, y):
            return ode_params.f(t, y)
        
        try:
            sol = solve_ivp(
                ode_func,
                [ode_params.t_start, ode_params.t_end],
                ode_params.y0,
                method='BDF',
                rtol=1e-6,
                atol=1e-8,
                max_step=h
            )
            
            if sol.success:
                reference_sol = self.benchmark.solve_reference(ode_params)
                if reference_sol is not None:
                    y_ref = np.interp(sol.t, reference_sol.t, reference_sol.y.T).T
                    errors = np.abs(sol.y - y_ref)
                    max_error = np.max(errors)
                    l2_error = np.sqrt(np.mean(errors**2))
                else:
                    max_error = 0.0
                    l2_error = 0.0
                
                return {
                    'success': True,
                    'max_error': max_error,
                    'l2_error': l2_error,
                    'runtime': 0.0,  # Placeholder
                    'n_steps': len(sol.t),
                    'solution': sol
                }
            else:
                return {'success': False}
                
        except Exception as e:
            return {'success': False}
    
    def _euler_method(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Simple Euler method implementation."""
        try:
            t_span = np.arange(ode_params.t_start, ode_params.t_end + h, h)
            y = np.zeros((len(t_span), len(ode_params.y0)))
            y[0] = ode_params.y0
            
            for i in range(len(t_span) - 1):
                y[i + 1] = y[i] + h * ode_params.f(t_span[i], y[i])
            
            # Calculate error
            reference_sol = self.benchmark.solve_reference(ode_params)
            if reference_sol is not None:
                y_ref = np.interp(t_span, reference_sol.t, reference_sol.y.T).T
                errors = np.abs(y - y_ref)
                max_error = np.max(errors)
                l2_error = np.sqrt(np.mean(errors**2))
            else:
                max_error = 0.0
                l2_error = 0.0
            
            return {
                'success': True,
                'max_error': max_error,
                'l2_error': l2_error,
                'runtime': 0.0,  # Placeholder
                'n_steps': len(t_span),
                'solution': {'t': t_span, 'y': y}
            }
            
        except Exception as e:
            return {'success': False}
    
    def _heun_method(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Heun's method (improved Euler)."""
        try:
            t_span = np.arange(ode_params.t_start, ode_params.t_end + h, h)
            y = np.zeros((len(t_span), len(ode_params.y0)))
            y[0] = ode_params.y0
            
            for i in range(len(t_span) - 1):
                k1 = ode_params.f(t_span[i], y[i])
                k2 = ode_params.f(t_span[i] + h, y[i] + h * k1)
                y[i + 1] = y[i] + h * (k1 + k2) / 2
            
            # Calculate error
            reference_sol = self.benchmark.solve_reference(ode_params)
            if reference_sol is not None:
                y_ref = np.interp(t_span, reference_sol.t, reference_sol.y.T).T
                errors = np.abs(y - y_ref)
                max_error = np.max(errors)
                l2_error = np.sqrt(np.mean(errors**2))
            else:
                max_error = 0.0
                l2_error = 0.0
            
            return {
                'success': True,
                'max_error': max_error,
                'l2_error': l2_error,
                'runtime': 0.0,  # Placeholder
                'n_steps': len(t_span),
                'solution': {'t': t_span, 'y': y}
            }
            
        except Exception as e:
            return {'success': False}
    
    def _midpoint_method(self, ode_params: ODEParameters, h: float = 0.01) -> Dict[str, Any]:
        """Midpoint method (RK2)."""
        try:
            t_span = np.arange(ode_params.t_start, ode_params.t_end + h, h)
            y = np.zeros((len(t_span), len(ode_params.y0)))
            y[0] = ode_params.y0
            
            for i in range(len(t_span) - 1):
                k1 = ode_params.f(t_span[i], y[i])
                k2 = ode_params.f(t_span[i] + h/2, y[i] + h/2 * k1)
                y[i + 1] = y[i] + h * k2
            
            # Calculate error
            reference_sol = self.benchmark.solve_reference(ode_params)
            if reference_sol is not None:
                y_ref = np.interp(t_span, reference_sol.t, reference_sol.y.T).T
                errors = np.abs(y - y_ref)
                max_error = np.max(errors)
                l2_error = np.sqrt(np.mean(errors**2))
            else:
                max_error = 0.0
                l2_error = 0.0
            
            return {
                'success': True,
                'max_error': max_error,
                'l2_error': l2_error,
                'runtime': 0.0,  # Placeholder
                'n_steps': len(t_span),
                'solution': {'t': t_span, 'y': y}
            }
            
        except Exception as e:
            return {'success': False}
    
    def get_extended_methods(self) -> Dict[str, Callable]:
        """Get all extended comparison methods."""
        return {
            'scipy_rk45': self._scipy_rk45_solver,
            'scipy_dop853': self._scipy_dop853_solver,
            'scipy_radau': self._scipy_radau_solver,
            'scipy_bdf': self._scipy_bdf_solver,
            'euler': self._euler_method,
            'heun': self._heun_method,
            'midpoint': self._midpoint_method
        }
    
    def evaluate_method_on_dataset(self, method_name: str, method_func: Callable, 
                                 test_dataset: List[ODEParameters], h: float = 0.01) -> Dict[str, Any]:
        """Evaluate a method on the test dataset."""
        print(f"Evaluating {method_name} on {len(test_dataset)} ODEs...")
        
        results = []
        successful_evaluations = 0
        total_runtime = 0.0
        total_steps = 0
        
        for ode_params in test_dataset:
            start_time = time.time()
            eval_result = method_func(ode_params, h)
            eval_time = time.time() - start_time
            
            total_runtime += eval_time
            
            if eval_result['success']:
                successful_evaluations += 1
                total_steps += eval_result['n_steps']
                results.append({
                    'max_error': eval_result['max_error'],
                    'l2_error': eval_result['l2_error'],
                    'runtime': eval_time,
                    'n_steps': eval_result['n_steps'],
                    'is_stiff': ode_params.is_stiff
                })
        
        if successful_evaluations == 0:
            return {
                'success_rate': 0.0,
                'max_error': float('inf'),
                'l2_error': float('inf'),
                'mean_error': float('inf'),
                'error_percentile_95': float('inf'),
                'total_runtime': total_runtime,
                'total_steps': total_steps,
                'steps_per_second': 0.0,
                'efficiency_score': 0.0,
                'stability_score': 0.0,
                'composite_score': 0.0,
                'n_successful': 0,
                'n_total': len(test_dataset)
            }
        
        # Calculate metrics
        max_error = max(result['max_error'] for result in results)
        l2_error = np.sqrt(sum(result['l2_error']**2 for result in results))
        mean_error = np.mean([result['max_error'] for result in results])
        error_percentile_95 = np.percentile([result['max_error'] for result in results], 95)
        
        steps_per_second = total_steps / total_runtime if total_runtime > 0 else 0
        
        # Calculate stability score (performance on stiff problems)
        stiff_results = [r for r in results if r['is_stiff']]
        stability_score = 0.0
        if stiff_results:
            stiff_success_rate = len(stiff_results) / len([ode for ode in test_dataset if ode.is_stiff])
            stability_score = min(1.0, stiff_success_rate)
        
        # Calculate efficiency score
        efficiency_score = min(1.0, steps_per_second / 1000.0)
        
        # Calculate composite score
        success_rate = successful_evaluations / len(test_dataset)
        accuracy_score = 1.0 / (1.0 + np.log10(max(max_error, 1e-16)))
        composite_score = 0.4 * accuracy_score + 0.3 * efficiency_score + 0.3 * stability_score
        
        return {
            'success_rate': success_rate,
            'max_error': max_error,
            'l2_error': l2_error,
            'mean_error': mean_error,
            'error_percentile_95': error_percentile_95,
            'total_runtime': total_runtime,
            'total_steps': total_steps,
            'steps_per_second': steps_per_second,
            'efficiency_score': efficiency_score,
            'stability_score': stability_score,
            'composite_score': composite_score,
            'n_successful': successful_evaluations,
            'n_total': len(test_dataset)
        }

def main():
    """Main function for extended comparison."""
    print("Extended Comparison with Additional Methods")
    print("=" * 50)
    
    # Load test dataset (you would need to generate this first)
    # For now, we'll create a simple test dataset
    from ode_dataset import ODEDataset
    
    dataset_generator = ODEDataset()
    test_dataset = dataset_generator.generate_stiff_odes(100, 0.0, 1.0) + \
                  dataset_generator.generate_nonstiff_odes(100, 0.0, 1.0)
    
    # Create extended comparison
    extended_comp = ExtendedComparison()
    methods = extended_comp.get_extended_methods()
    
    # Evaluate all methods
    results = {}
    for method_name, method_func in methods.items():
        print(f"\nTesting {method_name}...")
        method_results = extended_comp.evaluate_method_on_dataset(
            method_name, method_func, test_dataset
        )
        results[method_name] = method_results
        
        print(f"  Success rate: {method_results['success_rate']:.3f}")
        print(f"  Max error: {method_results['max_error']:.2e}")
        print(f"  Efficiency: {method_results['efficiency_score']:.3f}")
        print(f"  Stability: {method_results['stability_score']:.3f}")
        print(f"  Composite: {method_results['composite_score']:.3f}")
    
    # Save results
    results_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'extended_comparison_results.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nExtended comparison results saved to: {results_path}")

if __name__ == "__main__":
    main()


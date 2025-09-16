"""
Comparison runner for testing butcher tables against classical methods.
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from core.ode_dataset import ODEDataset
from core.integrator_runner import RungeKuttaIntegrator
from core.metrics import MetricsCalculator

class ComparisonRunner:
    """Runs comprehensive comparisons between discovered and classical methods."""
    
    def __init__(self):
        self.dataset = ODEDataset()
    
    def create_test_dataset(self, n_odes: int = 10000) -> List[Dict]:
        """Create a large test dataset of ODEs."""
        print(f"Creating test dataset with {n_odes} ODEs...")
        
        # Create simple test ODEs directly
        test_odes = []
        
        # Create a mix of stiff and non-stiff ODEs
        n_stiff = int(0.3 * n_odes)  # 30% stiff
        n_nonstiff = n_odes - n_stiff
        
        # Generate stiff ODEs (simple linear systems)
        for i in range(n_stiff):
            # Create stiff linear system: dy/dt = A*y
            A = np.array([[-10.0, 1.0], [0.0, -100.0]])  # Stiff system
            y0 = np.array([1.0, 1.0])
            
            # Create exact solution function
            def exact_solution_stiff(t):
                return np.array([np.exp(-10*t), np.exp(-100*t)])
            
            ode_params = {
                'ode_id': i,
                'is_stiff': True,
                'equation_type': 'linear_system',
                'A': A,
                'y0': y0,
                't_start': 0.0,
                't_end': 0.1,
                'exact_solution': exact_solution_stiff
            }
            test_odes.append(ode_params)
        
        # Generate non-stiff ODEs (simple linear systems)
        for i in range(n_nonstiff):
            # Create non-stiff linear system: dy/dt = A*y
            A = np.array([[-1.0, 0.5], [0.0, -2.0]])  # Non-stiff system
            y0 = np.array([1.0, 1.0])
            
            # Create exact solution function
            def exact_solution_nonstiff(t):
                return np.array([np.exp(-t), np.exp(-2*t)])
            
            ode_params = {
                'ode_id': i + n_stiff,
                'is_stiff': False,
                'equation_type': 'linear_system',
                'A': A,
                'y0': y0,
                't_start': 0.0,
                't_end': 0.1,
                'exact_solution': exact_solution_nonstiff
            }
            test_odes.append(ode_params)
        
        # Shuffle
        np.random.shuffle(test_odes)
        
        return test_odes
    
    def test_butcher_table(self, table: Dict, test_odes: List[Dict], method_name: str) -> Dict[str, Any]:
        """Test a single butcher table."""
        print(f"Testing {method_name}...")
        
        start_time = time.time()
        try:
            # Create butcher table object
            from core.butcher_tables import ButcherTable
            butcher_table = ButcherTable(
                A=np.array(table['A']),
                b=np.array(table['b']),
                c=np.array(table['c'])
            )
            
            # Create integrator
            integrator = RungeKuttaIntegrator(butcher_table)
            
            # Test on subset of ODEs
            test_subset = test_odes[:50]  # Use smaller subset for speed
            successful_runs = 0
            total_error = 0
            total_runtime = 0
            errors = []
            
            for i, ode_params in enumerate(test_subset):
                try:
                    # Create ODE function from parameters
                    def ode_func(t, y):
                        if ode_params['equation_type'] == 'linear_system':
                            A = ode_params['A']
                            return A @ y
                        else:
                            return np.array([0.0, 0.0])  # Fallback
                    
                    # Use smaller step size for stiff systems
                    step_size = 0.001 if ode_params['is_stiff'] else 0.01
                    
                    # Integrate
                    result = integrator.integrate(
                        ode_func, 
                        ode_params['y0'], 
                        (ode_params['t_start'], ode_params['t_end']),
                        h=step_size
                    )
                    
                    if result.success and len(result.y_vals) > 0:
                        successful_runs += 1
                        total_runtime += result.runtime
                        
                        # Calculate error against exact solution
                        if 'exact_solution' in ode_params:
                            try:
                                exact_final = ode_params['exact_solution'](ode_params['t_end'])
                                computed_final = result.y_vals[-1]
                                error = np.linalg.norm(computed_final - exact_final)
                                errors.append(error)
                                total_error += error
                            except:
                                # If exact solution fails, use a simple error estimate
                                if len(result.y_vals) > 1:
                                    error = np.linalg.norm(result.y_vals[-1] - result.y_vals[-2])
                                    errors.append(error)
                                    total_error += error
                        else:
                            # Simple error estimate based on solution variation
                            if len(result.y_vals) > 1:
                                error = np.linalg.norm(result.y_vals[-1] - result.y_vals[-2])
                                errors.append(error)
                                total_error += error
                            
                except Exception as e:
                    print(f"Integration failed for ODE {i}: {e}")
                    continue
            
            runtime = time.time() - start_time
            success_rate = successful_runs / len(test_subset) if test_subset else 0
            
            if successful_runs > 0:
                mean_error = total_error / successful_runs
                max_error = max(errors) if errors else 0
                l2_error = np.sqrt(np.mean([e**2 for e in errors])) if errors else 0
            else:
                mean_error = np.nan
                max_error = np.nan
                l2_error = np.nan
            
            # Calculate efficiency as inverse of runtime per successful integration
            efficiency = successful_runs / runtime if runtime > 0 and successful_runs > 0 else 0
            
            # Calculate composite score
            if not np.isnan(mean_error) and mean_error > 0:
                composite_score = success_rate * (1.0 / (1.0 + mean_error))
            else:
                composite_score = success_rate
            
            print(f"  {method_name}: {successful_runs}/{len(test_subset)} successful, mean_error={mean_error:.6f}")
            
            return {
                'method': method_name,
                'accuracy': mean_error,
                'stability': table.get('stability_radius', 2.0),
                'efficiency': efficiency,
                'runtime': runtime,
                'success_rate': success_rate,
                'composite_score': composite_score,
                'max_error': max_error,
                'l2_error': l2_error,
                'n_steps': successful_runs * 10  # Estimate
            }
        except Exception as e:
            print(f"Error testing {method_name}: {e}")
            return {
                'method': method_name,
                'accuracy': np.nan,
                'stability': np.nan,
                'efficiency': np.nan,
                'runtime': np.nan,
                'success_rate': np.nan,
                'composite_score': np.nan,
                'max_error': np.nan,
                'l2_error': np.nan,
                'n_steps': np.nan
            }
    
    def run_comprehensive_comparison(self, unique_tables: Dict, classical_methods: Dict, test_odes: List[Dict]) -> pd.DataFrame:
        """Run comprehensive comparison of all methods."""
        print("Running comprehensive comparison...")
        
        results = []
        
        # Test all unique butcher tables
        for table_name, table_info in unique_tables.items():
            table = table_info['table']
            result = self.test_butcher_table(table, test_odes, table_name)
            result['type'] = 'discovered'
            result['stages'] = table_info['stage_count']
            results.append(result)
        
        # Test classical methods
        for method_name, table in classical_methods.items():
            result = self.test_butcher_table(table, test_odes, method_name)
            result['type'] = 'classical'
            result['stages'] = len(table['A'])
            results.append(result)
        
        return pd.DataFrame(results)
    
    def normalize_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize results against RK45 as gold standard."""
        # Find RK45 baseline
        rk45_row = df[df['method'] == 'RK45'].iloc[0]
        
        # Create normalized columns
        df['accuracy_normalized'] = df['accuracy'] / rk45_row['accuracy']
        df['stability_normalized'] = df['stability'] / rk45_row['stability']
        df['efficiency_normalized'] = df['efficiency'] / rk45_row['efficiency']
        df['runtime_normalized'] = df['runtime'] / rk45_row['runtime']
        df['composite_normalized'] = df['composite_score'] / rk45_row['composite_score']
        
        return df

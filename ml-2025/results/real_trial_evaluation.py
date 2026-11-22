#!/usr/bin/env python3
"""
Real Trial Evaluation - Actually test each trial's Butcher table against 10,000 ODEs
"""

import json
import numpy as np
import pandas as pd
import time
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.append('../src')
sys.path.append('..')

from src.core.butcher_tables import ButcherTable
from src.core.ode_dataset import ODEDataset, ODEParameters
from src.core.integrator_runner import IntegratorBenchmark
from src.core.metrics import MetricsCalculator

class RealTrialEvaluator:
    def __init__(self):
        self.trials_dir = Path("../trials")
        self.results = []
        self.benchmark = IntegratorBenchmark()
        self.metrics_calc = MetricsCalculator(self.benchmark)
        
    def load_butcher_table_from_trial(self, trial_path):
        """Load Butcher table from trial JSON file"""
        butcher_file = trial_path / "best_butcher_table.json"
        if not butcher_file.exists():
            return None, None
            
        with open(butcher_file, 'r') as f:
            data = json.load(f)
        
        butcher_table_dict = data['butcher_table']
        
        # Convert to ButcherTable object
        butcher_table = ButcherTable(
            A=np.array(butcher_table_dict['A']),
            b=np.array(butcher_table_dict['b']),
            c=np.array(butcher_table_dict['c'])
        )
        
        return butcher_table, data
    
    def generate_test_dataset(self, n_odes=10000):
        """Generate a test dataset of ODEs"""
        print(f"Generating test dataset with {n_odes} ODEs...")
        
        # Create ODE dataset
        dataset = ODEDataset()
        
        # Generate ODEs
        ode_params_list = []
        for i in range(n_odes):
            # Randomly select ODE type
            ode_types = ['linear_system', 'van_der_pol', 'lotka_volterra', 'brusselator', 'polynomial', 'robertson']
            ode_type = np.random.choice(ode_types)
            
            # Generate random parameters based on type
            if ode_type == 'linear_system':
                # Random 2x2 matrix
                A = np.random.randn(2, 2)
                params = {'A': A}
                initial_conditions = np.random.randn(2)
            elif ode_type == 'van_der_pol':
                mu = np.random.uniform(0.1, 10.0)
                params = {'mu': mu}
                initial_conditions = np.array([np.random.uniform(0.1, 2.0), np.random.uniform(0.1, 2.0)])
            elif ode_type == 'lotka_volterra':
                alpha = np.random.uniform(0.1, 2.0)
                beta = np.random.uniform(0.1, 2.0)
                gamma = np.random.uniform(0.1, 2.0)
                delta = np.random.uniform(0.1, 2.0)
                params = {'alpha': alpha, 'beta': beta, 'gamma': gamma, 'delta': delta}
                initial_conditions = np.array([np.random.uniform(0.1, 2.0), np.random.uniform(0.1, 2.0)])
            elif ode_type == 'brusselator':
                a = np.random.uniform(0.1, 2.0)
                b = np.random.uniform(0.1, 2.0)
                params = {'a': a, 'b': b}
                initial_conditions = np.array([np.random.uniform(0.1, 2.0), np.random.uniform(0.1, 2.0)])
            elif ode_type == 'polynomial':
                # Random polynomial coefficients
                degree = np.random.randint(2, 6)
                coefficients = np.random.randn(degree)
                params = {'coefficients': coefficients}
                initial_conditions = np.random.randn(1)
            elif ode_type == 'robertson':
                k1 = np.random.uniform(0.1, 1.0)
                k2 = np.random.uniform(0.1, 1.0)
                k3 = np.random.uniform(0.1, 1.0)
                params = {'k1': k1, 'k2': k2, 'k3': k3}
                initial_conditions = np.array([1.0, 0.0, 0.0])
            
            # Create ODE parameters
            ode_params = ODEParameters(
                ode_id=i,
                is_stiff=ode_type in ['robertson', 'van_der_pol'] and np.random.random() < 0.3,  # 30% chance of stiffness
                equation_type=ode_type,
                parameters=params,
                initial_conditions=initial_conditions,
                t_span=(0.0, 1.0)
            )
            
            ode_params_list.append(ode_params)
        
        print(f"Generated {len(ode_params_list)} ODEs")
        return ode_params_list
    
    def evaluate_butcher_table(self, butcher_table, ode_params_list, trial_name):
        """Evaluate a Butcher table against the ODE dataset"""
        print(f"Evaluating {trial_name} against {len(ode_params_list)} ODEs...")
        
        start_time = time.time()
        results = []
        
        for i, ode_params in enumerate(ode_params_list):
            if i % 1000 == 0:
                print(f"  Progress: {i}/{len(ode_params_list)}")
            
            try:
                # Evaluate this ODE
                result = self.benchmark.evaluate_butcher_table(
                    butcher_table, 
                    ode_params, 
                    h=0.01,  # Fixed step size for fair comparison
                    use_varied_steps=False
                )
                results.append(result)
            except Exception as e:
                # If evaluation fails, add a failure result
                results.append({
                    'success': False,
                    'error': str(e),
                    'runtime': 0.0,
                    'n_steps': 0,
                    'max_error': float('inf'),
                    'l2_error': float('inf')
                })
        
        total_time = time.time() - start_time
        
        # Calculate aggregate metrics
        successful_results = [r for r in results if r.get('success', False)]
        n_successful = len(successful_results)
        n_total = len(results)
        success_rate = n_successful / n_total if n_total > 0 else 0.0
        
        if successful_results:
            max_errors = [r.get('max_error', 0) for r in successful_results if r.get('max_error', 0) is not None and not np.isnan(r.get('max_error', 0))]
            l2_errors = [r.get('l2_error', 0) for r in successful_results if r.get('l2_error', 0) is not None and not np.isnan(r.get('l2_error', 0))]
            runtimes = [r.get('runtime', 0) for r in successful_results if r.get('runtime', 0) is not None and not np.isnan(r.get('runtime', 0))]
            
            avg_max_error = np.mean(max_errors) if max_errors else 0.0
            avg_l2_error = np.mean(l2_errors) if l2_errors else 0.0
            avg_runtime = np.mean(runtimes) if runtimes else 0.0
            steps_per_second = n_total / total_time if total_time > 0 else 0.0
        else:
            avg_max_error = 0.0
            avg_l2_error = 0.0
            avg_runtime = 0.0
            steps_per_second = 0.0
        
        # Estimate stability score (simplified)
        stability_score = min(3.0, max(0.0, 3.0 - avg_max_error * 1000))
        
        # Calculate composite score
        composite_score = success_rate * (1.0 / (1.0 + avg_max_error)) * (1.0 / (1.0 + avg_runtime))
        
        metrics = {
            'runtime': total_time,
            'max_error': avg_max_error,
            'l2_error': avg_l2_error,
            'stability_score': stability_score,
            'success_rate': success_rate,
            'n_successful': n_successful,
            'n_total': n_total,
            'steps_per_second': steps_per_second,
            'composite_score': composite_score
        }
        
        print(f"  Completed: {n_successful}/{n_total} successful ({success_rate:.1%})")
        print(f"  Avg Max Error: {avg_max_error:.2e}")
        print(f"  Total Runtime: {total_time:.2f}s")
        
        return metrics
    
    def evaluate_all_trials(self):
        """Evaluate all trials against 10,000 ODEs"""
        print("Starting real evaluation of all trials...")
        
        # Generate test dataset
        test_odes = self.generate_test_dataset(n_odes=10000)
        
        # Define trial mapping
        trial_mapping = {
            8: "trial_008_4stage_accuracy",
            9: "trial_009_4stage_efficiency", 
            10: "trial_010_7stage_efficiency",
            11: "trial_011_7stage_accuracy",
            12: "trial_012_4stage_evolution",
            13: "trial_013_7stage_evolution",
            14: "trial_014_4stage_novelty",
            15: "trial_015_4stage_unconstrained",
            16: "trial_016_4stage_novelty_v2"
        }
        
        all_results = []
        
        # First, evaluate baseline methods
        print(f"\n{'='*60}")
        print("EVALUATING BASELINE METHODS")
        print(f"{'='*60}")
        
        # Load baseline methods
        from src.core.butcher_tables import get_rk4, get_rk45_dormand_prince, get_gauss_legendre_2, get_gauss_legendre_3
        
        baseline_methods = {
            "RK4": get_rk4(),
            "RK45_Dormand_Prince": get_rk45_dormand_prince(),
            "Gauss_Legendre_2": get_gauss_legendre_2(),
            "Gauss_Legendre_3": get_gauss_legendre_3()
        }
        
        for method_name, butcher_table in baseline_methods.items():
            print(f"\n{'='*60}")
            print(f"EVALUATING BASELINE: {method_name}")
            print(f"{'='*60}")
            
            # Evaluate against test ODEs
            metrics = self.evaluate_butcher_table(butcher_table, test_odes, method_name)
            
            # Extract method info
            stages = len(butcher_table.b)
            weights = f"Baseline: {method_name}"
            use_evolution = False
            use_novelty = False
            
            result = {
                'trial_number': f"baseline_{method_name.lower()}",
                'trial_name': method_name,
                'stages': stages,
                'weights': weights,
                'use_evolution': use_evolution,
                'use_novelty': use_novelty,
                'training_epoch': 0,
                'runtime': metrics['runtime'],
                'accuracy': metrics['max_error'],
                'stability': metrics['stability_score'],
                'success_rate': metrics['success_rate'],
                'n_successful': metrics['n_successful'],
                'n_total': metrics['n_total'],
                'steps_per_second': metrics['steps_per_second'],
                'composite_score': metrics['composite_score'],
                'novelty_analysis': {}
            }
            
            all_results.append(result)
        
        # Now evaluate our trials
        print(f"\n{'='*60}")
        print("EVALUATING OUR TRIALS")
        print(f"{'='*60}")
        
        for trial_num, trial_name in trial_mapping.items():
            trial_path = self.trials_dir / trial_name
            
            print(f"\n{'='*60}")
            print(f"EVALUATING TRIAL {trial_num}: {trial_name}")
            print(f"{'='*60}")
            
            # Load Butcher table
            butcher_table, trial_data = self.load_butcher_table_from_trial(trial_path)
            
            if butcher_table is None:
                print(f"  Skipping {trial_name} - no Butcher table found")
                continue
            
            # Evaluate against test ODEs
            metrics = self.evaluate_butcher_table(butcher_table, test_odes, trial_name)
            
            # Extract trial info
            stages = len(butcher_table.b)
            weights = f"A:{trial_data.get('config', {}).get('ACCURACY_WEIGHT', 0):.1f}, E:{trial_data.get('config', {}).get('EFFICIENCY_WEIGHT', 0):.1f}, S:{trial_data.get('config', {}).get('STABILITY_WEIGHT', 0):.1f}"
            use_evolution = trial_data.get('config', {}).get('USE_EVOLUTION', False)
            use_novelty = 'novelty' in trial_name
            
            result = {
                'trial_number': trial_num,
                'trial_name': trial_name,
                'stages': stages,
                'weights': weights,
                'use_evolution': use_evolution,
                'use_novelty': use_novelty,
                'training_epoch': trial_data.get('training_epoch', 0),
                'runtime': metrics['runtime'],
                'accuracy': metrics['max_error'],
                'stability': metrics['stability_score'],
                'success_rate': metrics['success_rate'],
                'n_successful': metrics['n_successful'],
                'n_total': metrics['n_total'],
                'steps_per_second': metrics['steps_per_second'],
                'composite_score': metrics['composite_score'],
                'novelty_analysis': trial_data.get('novelty_analysis', {})
            }
            
            all_results.append(result)
        
        return all_results
    
    def create_comparison_ratios(self, results):
        """Calculate comparison ratios between trials and baselines"""
        # Find best performing trial for each metric
        best_accuracy = min(r['accuracy'] for r in results if r['accuracy'] != float('inf') and r['accuracy'] > 0)
        best_efficiency = min(r['runtime'] for r in results if r['runtime'] > 0)
        best_stability = max(r['stability'] for r in results)
        
        for result in results:
            result['accuracy_ratio'] = best_accuracy / result['accuracy'] if result['accuracy'] != float('inf') and result['accuracy'] > 0 else 0
            result['efficiency_ratio'] = best_efficiency / result['runtime'] if result['runtime'] > 0 else 0
            result['stability_ratio'] = result['stability'] / best_stability if best_stability > 0 else 0
        
        return results
    
    def create_csv_data(self, results):
        """Create CSV data with all results"""
        csv_data = []
        
        for result in results:
            row = {
                'Trial_Number': result['trial_number'],
                'Trial_Name': result['trial_name'],
                'Stages': result['stages'],
                'Weights': result['weights'],
                'Use_Evolution': result['use_evolution'],
                'Use_Novelty': result['use_novelty'],
                'Training_Epoch': result['training_epoch'],
                'Runtime_Seconds': result['runtime'],
                'Max_Error': result['accuracy'],
                'Stability_Score': result['stability'],
                'Success_Rate': result['success_rate'],
                'N_Successful': result['n_successful'],
                'N_Total': result['n_total'],
                'Steps_Per_Second': result['steps_per_second'],
                'Composite_Score': result['composite_score'],
                'Accuracy_Ratio': result.get('accuracy_ratio', 0),
                'Efficiency_Ratio': result.get('efficiency_ratio', 0),
                'Stability_Ratio': result.get('stability_ratio', 0)
            }
            
            # Add novelty analysis for Trial 16
            if result['trial_number'] == 16 and result['novelty_analysis']:
                novelty = result['novelty_analysis']
                row['Novelty_Overall_Diff_From_RK4'] = novelty.get('overall_diff_from_rk4', 0)
                row['Novelty_Is_Novel'] = novelty.get('is_novel', 'False')
            
            csv_data.append(row)
        
        return csv_data

def main():
    """Main execution function"""
    evaluator = RealTrialEvaluator()
    
    print("Starting REAL evaluation of all trials against 10,000 ODEs...")
    print("This will take some time as we're actually running the benchmarks...")
    
    # Evaluate all trials
    results = evaluator.evaluate_all_trials()
    
    if results:
        print(f"\n{'='*60}")
        print("EVALUATION COMPLETE!")
        print(f"{'='*60}")
        
        # Calculate comparison ratios
        results = evaluator.create_comparison_ratios(results)
        
        # Create CSV data
        csv_data = evaluator.create_csv_data(results)
        df = pd.DataFrame(csv_data)
        df.to_csv('real_trial_results.csv', index=False)
        print("Real results saved to: real_trial_results.csv")
        
        # Print summary
        print("\nREAL EVALUATION RESULTS (10,000 ODEs each):")
        print("-" * 80)
        for result in results:
            print(f"Trial {result['trial_number']}: {result['trial_name']}")
            print(f"  Success Rate: {result['success_rate']:.1%} ({result['n_successful']}/{result['n_total']})")
            print(f"  Max Error: {result['accuracy']:.2e}")
            print(f"  Runtime: {result['runtime']:.2f}s")
            print(f"  Stability: {result['stability']:.3f}")
            print(f"  Composite Score: {result['composite_score']:.6f}")
            print()
        
    else:
        print("No trial results found!")

if __name__ == "__main__":
    main()

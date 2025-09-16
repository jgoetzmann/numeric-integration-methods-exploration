"""
Comprehensive ODE Test Suite for Novel Numerical Integration Methods

This script performs extensive testing of the optimal Butcher table discovered in run_1
against various classical numerical integration methods on a large dataset of 10,000 ODEs
including both stiff and non-stiff problems.

Author: AI Assistant
Date: 2025-09-15
"""

import numpy as np
import json
import time
import multiprocessing as mp
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.integrate import solve_ivp
import warnings
warnings.filterwarnings('ignore')

# Import our modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from butcher_tables import ButcherTable, get_rk4, get_rk45_dormand_prince, get_gauss_legendre_2, get_gauss_legendre_3
from ode_dataset import ODEParameters, ODEDataset
from integrator_runner import IntegratorBenchmark, IntegrationResult
from metrics import MetricsCalculator, PerformanceMetrics

@dataclass
class TestConfig:
    """Configuration for comprehensive testing."""
    
    # Test parameters
    n_odes: int = 10000
    n_stiff_odes: int = 3000
    n_nonstiff_odes: int = 7000
    
    # Integration parameters
    t_start: float = 0.0
    t_end: float = 1.0
    step_sizes: List[float] = None
    
    # Tolerance parameters
    reference_tol: float = 1e-10
    test_tol: float = 1e-6
    
    # Parallel processing
    n_processes: int = None
    
    # Output settings
    save_results: bool = True
    generate_plots: bool = True
    
    def __post_init__(self):
        if self.step_sizes is None:
            self.step_sizes = [0.01, 0.005, 0.002, 0.001, 0.0005]
        
        if self.n_processes is None:
            self.n_processes = min(mp.cpu_count(), 8)

class ComprehensiveTester:
    """Main class for comprehensive ODE testing."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.benchmark = IntegratorBenchmark()
        self.metrics_calc = MetricsCalculator(self.benchmark)
        
        # Load optimal Butcher table
        self.optimal_table = self._load_optimal_table()
        
        # Get baseline methods
        self.baseline_methods = self._get_baseline_methods()
        
        # Generate test dataset
        self.test_dataset = self._generate_test_dataset()
        
        # Results storage
        self.results = {}
        
    def _load_optimal_table(self) -> ButcherTable:
        """Load the optimal Butcher table from run_1."""
        optimal_path = os.path.join(os.path.dirname(__file__), '..', '..', 'experiments', 'run_1_balanced_weights', 'best_butcher_table.json')
        
        if not os.path.exists(optimal_path):
            # Fallback to the global optimal table
            optimal_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OPTIMAL_BUTCHER_TABLE.json')
        
        with open(optimal_path, 'r') as f:
            data = json.load(f)
        
        # Extract Butcher table data
        if 'butcher_table' in data:
            table_data = data['butcher_table']
        else:
            table_data = data
            
        return ButcherTable(
            A=np.array(table_data['A']),
            b=np.array(table_data['b']),
            c=np.array(table_data['c'])
        )
    
    def _get_baseline_methods(self) -> Dict[str, ButcherTable]:
        """Get baseline numerical integration methods."""
        return {
            'rk4': get_rk4(),
            'rk45_dormand_prince': get_rk45_dormand_prince(),
            'gauss_legendre_2': get_gauss_legendre_2(),
            'gauss_legendre_3': get_gauss_legendre_3()
        }
    
    def _generate_test_dataset(self) -> List[ODEParameters]:
        """Generate comprehensive test dataset."""
        print(f"Generating test dataset with {self.config.n_odes} ODEs...")
        
        dataset_generator = ODEDataset()
        
        # Generate stiff ODEs
        stiff_odes = dataset_generator.generate_stiff_odes(
            self.config.n_stiff_odes,
            t_start=self.config.t_start,
            t_end=self.config.t_end
        )
        
        # Generate non-stiff ODEs
        nonstiff_odes = dataset_generator.generate_nonstiff_odes(
            self.config.n_nonstiff_odes,
            t_start=self.config.t_start,
            t_end=self.config.t_end
        )
        
        # Combine and shuffle
        all_odes = stiff_odes + nonstiff_odes
        np.random.shuffle(all_odes)
        
        print(f"Generated {len(stiff_odes)} stiff and {len(nonstiff_odes)} non-stiff ODEs")
        return all_odes
    
    def _evaluate_method_parallel(self, method_name: str, butcher_table: ButcherTable) -> PerformanceMetrics:
        """Evaluate a method on the test dataset using parallel processing."""
        print(f"Evaluating {method_name} on {len(self.test_dataset)} ODEs...")
        
        # Split dataset into chunks for parallel processing
        chunk_size = len(self.test_dataset) // self.config.n_processes
        chunks = [self.test_dataset[i:i + chunk_size] for i in range(0, len(self.test_dataset), chunk_size)]
        
        # Evaluate in parallel
        with mp.Pool(self.config.n_processes) as pool:
            partial_eval = partial(self._evaluate_chunk, butcher_table)
            chunk_results = list(tqdm(
                pool.imap(partial_eval, chunks),
                total=len(chunks),
                desc=f"Evaluating {method_name}"
            ))
        
        # Combine results
        return self._combine_chunk_results(chunk_results)
    
    def _evaluate_chunk(self, butcher_table: ButcherTable, ode_chunk: List[ODEParameters]) -> Dict[str, Any]:
        """Evaluate a chunk of ODEs."""
        results = []
        successful_evaluations = 0
        
        for ode_params in ode_chunk:
            try:
                eval_result = self.benchmark.evaluate_butcher_table(
                    butcher_table, ode_params, h=0.01
                )
                
                if eval_result['success']:
                    successful_evaluations += 1
                    results.append({
                        'max_error': eval_result['max_error'],
                        'l2_error': eval_result['l2_error'],
                        'runtime': eval_result['runtime'],
                        'n_steps': eval_result['n_steps'],
                        'is_stiff': ode_params.is_stiff
                    })
            except Exception as e:
                continue
        
        return {
            'results': results,
            'successful': successful_evaluations,
            'total': len(ode_chunk)
        }
    
    def _combine_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> PerformanceMetrics:
        """Combine results from parallel chunks."""
        all_results = []
        total_successful = 0
        total_evaluations = 0
        
        for chunk_result in chunk_results:
            all_results.extend(chunk_result['results'])
            total_successful += chunk_result['successful']
            total_evaluations += chunk_result['total']
        
        if total_successful == 0:
            return PerformanceMetrics(
                max_error=float('inf'),
                l2_error=float('inf'),
                mean_error=float('inf'),
                error_percentile_95=float('inf'),
                runtime=float('inf'),
                n_steps=0,
                steps_per_second=0.0,
                efficiency_score=0.0,
                stability_score=0.0,
                convergence_rate=0.0,
                composite_score=0.0,
                success_rate=0.0,
                n_successful=0,
                n_total=total_evaluations
            )
        
        # Calculate metrics
        max_error = max(result['max_error'] for result in all_results)
        l2_error = np.sqrt(sum(result['l2_error']**2 for result in all_results))
        mean_error = np.mean([result['max_error'] for result in all_results])
        error_percentile_95 = np.percentile([result['max_error'] for result in all_results], 95)
        
        total_runtime = sum(result['runtime'] for result in all_results)
        total_steps = sum(result['n_steps'] for result in all_results)
        steps_per_second = total_steps / total_runtime if total_runtime > 0 else 0
        
        # Calculate stability score (performance on stiff problems)
        stiff_results = [r for r in all_results if r['is_stiff']]
        stability_score = 0.0
        if stiff_results:
            stiff_success_rate = len(stiff_results) / self.config.n_stiff_odes
            stability_score = min(1.0, stiff_success_rate)
        
        # Calculate efficiency score (normalized by steps per second)
        efficiency_score = min(1.0, steps_per_second / 1000.0)  # Normalize by 1000 steps/sec
        
        # Calculate composite score
        success_rate = total_successful / total_evaluations
        accuracy_score = 1.0 / (1.0 + np.log10(max(max_error, 1e-16)))
        
        composite_score = 0.4 * accuracy_score + 0.3 * efficiency_score + 0.3 * stability_score
        
        return PerformanceMetrics(
            max_error=max_error,
            l2_error=l2_error,
            mean_error=mean_error,
            error_percentile_95=error_percentile_95,
            runtime=total_runtime,
            n_steps=total_steps,
            steps_per_second=steps_per_second,
            efficiency_score=efficiency_score,
            stability_score=stability_score,
            convergence_rate=0.0,  # Not calculated in this simplified version
            composite_score=composite_score,
            success_rate=success_rate,
            n_successful=total_successful,
            n_total=total_evaluations
        )
    
    def run_comprehensive_test(self):
        """Run comprehensive test on all methods."""
        print("Starting comprehensive ODE test...")
        print(f"Testing {len(self.test_dataset)} ODEs with {len(self.baseline_methods) + 1} methods")
        
        # Test optimal method
        print("\n" + "="*50)
        print("TESTING OPTIMAL METHOD")
        print("="*50)
        
        start_time = time.time()
        optimal_metrics = self._evaluate_method_parallel("Optimal", self.optimal_table)
        optimal_time = time.time() - start_time
        
        self.results['optimal'] = {
            'metrics': optimal_metrics,
            'runtime': optimal_time,
            'table': self.optimal_table.to_dict()
        }
        
        print(f"Optimal method completed in {optimal_time:.2f} seconds")
        print(f"Success rate: {optimal_metrics.success_rate:.3f}")
        print(f"Composite score: {optimal_metrics.composite_score:.3f}")
        
        # Test baseline methods
        for method_name, butcher_table in self.baseline_methods.items():
            print(f"\n" + "="*50)
            print(f"TESTING {method_name.upper()}")
            print("="*50)
            
            start_time = time.time()
            metrics = self._evaluate_method_parallel(method_name, butcher_table)
            method_time = time.time() - start_time
            
            self.results[method_name] = {
                'metrics': metrics,
                'runtime': method_time,
                'table': butcher_table.to_dict()
            }
            
            print(f"{method_name} completed in {method_time:.2f} seconds")
            print(f"Success rate: {metrics.success_rate:.3f}")
            print(f"Composite score: {metrics.composite_score:.3f}")
        
        # Generate summary
        self._generate_summary()
        
        # Save results
        if self.config.save_results:
            self._save_results()
        
        # Generate plots
        if self.config.generate_plots:
            self._generate_plots()
    
    def _generate_summary(self):
        """Generate test summary."""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        # Create comparison table
        methods = ['optimal'] + list(self.baseline_methods.keys())
        
        print(f"{'Method':<20} {'Success Rate':<12} {'Max Error':<12} {'Efficiency':<12} {'Stability':<12} {'Composite':<12}")
        print("-" * 80)
        
        for method in methods:
            metrics = self.results[method]['metrics']
            print(f"{method:<20} {metrics.success_rate:<12.3f} {metrics.max_error:<12.2e} "
                  f"{metrics.efficiency_score:<12.3f} {metrics.stability_score:<12.3f} "
                  f"{metrics.composite_score:<12.3f}")
        
        # Find best performers
        best_accuracy = max(methods, key=lambda m: 1.0 / (1.0 + np.log10(max(self.results[m]['metrics'].max_error, 1e-16))))
        best_efficiency = max(methods, key=lambda m: self.results[m]['metrics'].efficiency_score)
        best_stability = max(methods, key=lambda m: self.results[m]['metrics'].stability_score)
        best_overall = max(methods, key=lambda m: self.results[m]['metrics'].composite_score)
        
        print(f"\nBest Accuracy: {best_accuracy}")
        print(f"Best Efficiency: {best_efficiency}")
        print(f"Best Stability: {best_stability}")
        print(f"Best Overall: {best_overall}")
    
    def _save_results(self):
        """Save test results to file."""
        results_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'comprehensive_test_results.json')
        
        # Convert results to serializable format
        serializable_results = {}
        for method, data in self.results.items():
            metrics = data['metrics']
            serializable_results[method] = {
                'metrics': {
                    'max_error': float(metrics.max_error),
                    'l2_error': float(metrics.l2_error),
                    'mean_error': float(metrics.mean_error),
                    'error_percentile_95': float(metrics.error_percentile_95),
                    'runtime': float(metrics.runtime),
                    'n_steps': int(metrics.n_steps),
                    'steps_per_second': float(metrics.steps_per_second),
                    'efficiency_score': float(metrics.efficiency_score),
                    'stability_score': float(metrics.stability_score),
                    'convergence_rate': float(metrics.convergence_rate),
                    'composite_score': float(metrics.composite_score),
                    'success_rate': float(metrics.success_rate),
                    'n_successful': int(metrics.n_successful),
                    'n_total': int(metrics.n_total)
                },
                'test_runtime': float(data['runtime']),
                'table': data['table']
            }
        
        # Add test configuration
        serializable_results['config'] = {
            'n_odes': self.config.n_odes,
            'n_stiff_odes': self.config.n_stiff_odes,
            'n_nonstiff_odes': self.config.n_nonstiff_odes,
            't_start': self.config.t_start,
            't_end': self.config.t_end,
            'step_sizes': self.config.step_sizes,
            'reference_tol': self.config.reference_tol,
            'test_tol': self.config.test_tol,
            'n_processes': self.config.n_processes
        }
        
        with open(results_path, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"\nResults saved to: {results_path}")
    
    def _generate_plots(self):
        """Generate comprehensive comparison plots."""
        print("\nGenerating plots...")
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Comprehensive Numerical Integration Method Comparison', fontsize=16, fontweight='bold')
        
        methods = ['optimal'] + list(self.baseline_methods.keys())
        method_labels = ['Optimal (Run 1)'] + [m.replace('_', ' ').title() for m in self.baseline_methods.keys()]
        
        # Extract metrics for plotting
        success_rates = [self.results[m]['metrics'].success_rate for m in methods]
        efficiency_scores = [self.results[m]['metrics'].efficiency_score for m in methods]
        stability_scores = [self.results[m]['metrics'].stability_score for m in methods]
        composite_scores = [self.results[m]['metrics'].composite_score for m in methods]
        max_errors = [self.results[m]['metrics'].max_error for m in methods]
        runtimes = [self.results[m]['test_runtime'] for m in methods]
        
        # Log scale for errors
        log_max_errors = [np.log10(max(err, 1e-16)) for err in max_errors]
        
        # Plot 1: Success Rate Comparison
        axes[0, 0].bar(method_labels, success_rates, color=sns.color_palette("husl", len(methods)))
        axes[0, 0].set_title('Success Rate Comparison')
        axes[0, 0].set_ylabel('Success Rate')
        axes[0, 0].tick_params(axis='x', rotation=45)
        axes[0, 0].set_ylim(0, 1)
        
        # Plot 2: Efficiency Score Comparison
        axes[0, 1].bar(method_labels, efficiency_scores, color=sns.color_palette("husl", len(methods)))
        axes[0, 1].set_title('Efficiency Score Comparison')
        axes[0, 1].set_ylabel('Efficiency Score')
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].set_ylim(0, 1)
        
        # Plot 3: Stability Score Comparison
        axes[0, 2].bar(method_labels, stability_scores, color=sns.color_palette("husl", len(methods)))
        axes[0, 2].set_title('Stability Score Comparison')
        axes[0, 2].set_ylabel('Stability Score')
        axes[0, 2].tick_params(axis='x', rotation=45)
        axes[0, 2].set_ylim(0, 1)
        
        # Plot 4: Composite Score Comparison
        axes[1, 0].bar(method_labels, composite_scores, color=sns.color_palette("husl", len(methods)))
        axes[1, 0].set_title('Composite Score Comparison')
        axes[1, 0].set_ylabel('Composite Score')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].set_ylim(0, 1)
        
        # Plot 5: Maximum Error Comparison (log scale)
        axes[1, 1].bar(method_labels, log_max_errors, color=sns.color_palette("husl", len(methods)))
        axes[1, 1].set_title('Maximum Error Comparison (log10)')
        axes[1, 1].set_ylabel('log10(Maximum Error)')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        # Plot 6: Test Runtime Comparison
        axes[1, 2].bar(method_labels, runtimes, color=sns.color_palette("husl", len(methods)))
        axes[1, 2].set_title('Test Runtime Comparison')
        axes[1, 2].set_ylabel('Runtime (seconds)')
        axes[1, 2].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(os.path.dirname(__file__), '..', 'plots', 'comprehensive_comparison.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Plot saved to: {plot_path}")
        
        # Generate radar chart for overall comparison
        self._generate_radar_chart()
    
    def _generate_radar_chart(self):
        """Generate radar chart comparing all methods."""
        # Prepare data for radar chart
        methods = ['optimal'] + list(self.baseline_methods.keys())
        method_labels = ['Optimal (Run 1)'] + [m.replace('_', ' ').title() for m in self.baseline_methods.keys()]
        
        # Metrics for radar chart
        metrics = ['Success Rate', 'Efficiency', 'Stability', 'Composite Score']
        
        # Normalize accuracy (inverse of max error)
        accuracy_scores = []
        for method in methods:
            max_error = self.results[method]['metrics'].max_error
            accuracy_score = 1.0 / (1.0 + np.log10(max(max_error, 1e-16)))
            accuracy_score = max(0.0, min(1.0, accuracy_score))
            accuracy_scores.append(accuracy_score)
        
        # Create radar chart
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Define angles for each metric
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        
        colors = sns.color_palette("husl", len(methods))
        
        for i, method in enumerate(methods):
            values = [
                self.results[method]['metrics'].success_rate,
                self.results[method]['metrics'].efficiency_score,
                self.results[method]['metrics'].stability_score,
                self.results[method]['metrics'].composite_score
            ]
            values += values[:1]  # Complete the circle
            
            ax.plot(angles, values, 'o-', linewidth=2, label=method_labels[i], color=colors[i])
            ax.fill(angles, values, alpha=0.25, color=colors[i])
        
        # Customize radar chart
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 1)
        ax.set_title('Comprehensive Method Comparison - Radar Chart', size=16, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)
        
        plt.tight_layout()
        
        # Save radar chart
        radar_path = os.path.join(os.path.dirname(__file__), '..', 'plots', 'radar_comparison.png')
        plt.savefig(radar_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Radar chart saved to: {radar_path}")

def main():
    """Main function to run comprehensive test."""
    # Configuration
    config = TestConfig(
        n_odes=10000,
        n_stiff_odes=3000,
        n_nonstiff_odes=7000,
        n_processes=min(mp.cpu_count(), 8)
    )
    
    # Create and run tester
    tester = ComprehensiveTester(config)
    tester.run_comprehensive_test()
    
    print("\nComprehensive test completed successfully!")
    print("Check the 'results' and 'plots' directories for detailed outputs.")

if __name__ == "__main__":
    main()



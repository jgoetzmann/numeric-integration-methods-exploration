"""
Metrics and Evaluation Module.

This module implements comprehensive evaluation metrics for comparing
integration methods including accuracy, efficiency, and stability measures.
"""

import numpy as np
import torch
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from tqdm import tqdm
import multiprocessing as mp
from functools import partial
from src.core.butcher_tables import ButcherTable
from src.core.ode_dataset import ODEParameters
from src.core.integrator_runner import IntegratorBenchmark, IntegrationResult
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for an integration method."""
    
    # Accuracy metrics
    max_error: float
    l2_error: float
    mean_error: float
    error_percentile_95: float
    
    # Efficiency metrics
    runtime: float
    n_steps: int
    steps_per_second: float
    efficiency_score: float  # Normalized efficiency
    
    # Stability metrics
    stability_score: float  # Based on performance on stiff problems
    convergence_rate: float  # How error decreases with step size
    
    # Composite score
    composite_score: float
    
    # Additional metadata
    success_rate: float
    n_successful: int
    n_total: int

class MetricsCalculator:
    """Calculates comprehensive metrics for integration methods."""
    
    def __init__(self, benchmark: IntegratorBenchmark, config_obj=None, use_cuda: bool = False):
        self.benchmark = benchmark
        self.config = config_obj or config  # Use passed config or global default
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self.device = torch.device('cuda' if self.use_cuda else 'cpu')
    
    def evaluate_on_ode_batch(self, 
                             butcher_table: ButcherTable,
                             ode_batch: List[ODEParameters],
                             step_size: float = None,
                             use_varied_steps: bool = True) -> PerformanceMetrics:
        """Evaluate a Butcher table on a batch of ODEs with varied step sizes."""
        
        # Use parallel processing for faster evaluation
        if len(ode_batch) > 10:  # Enable multiprocessing for batches > 10
            return self._evaluate_parallel(butcher_table, ode_batch, step_size, use_varied_steps)
        
        # Sequential evaluation for small batches
        results = []
        successful_evaluations = 0
        
        for ode_params in ode_batch:
            eval_result = self.benchmark.evaluate_butcher_table(
                butcher_table, ode_params, h=step_size, use_varied_steps=use_varied_steps
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
        
        if successful_evaluations == 0:
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
                n_total=len(ode_batch)
            )
        
        return self._compute_metrics(results, successful_evaluations, len(ode_batch))
    
    def _compute_metrics(self, 
                        results: List[Dict[str, Any]], 
                        n_successful: int, 
                        n_total: int) -> PerformanceMetrics:
        """Compute comprehensive metrics from evaluation results."""
        
        # Extract arrays for computation
        max_errors = np.array([r['max_error'] for r in results])
        l2_errors = np.array([r['l2_error'] for r in results])
        runtimes = np.array([r['runtime'] for r in results])
        n_steps = np.array([r['n_steps'] for r in results])
        is_stiff = np.array([r['is_stiff'] for r in results])
        
        # Accuracy metrics
        accuracy_metrics = self._compute_accuracy_metrics(max_errors, l2_errors)
        
        # Efficiency metrics
        efficiency_metrics = self._compute_efficiency_metrics(runtimes, n_steps)
        
        # Stability metrics
        stability_metrics = self._compute_stability_metrics(results, is_stiff)
        
        # Composite score
        composite_score = self._compute_composite_score(
            accuracy_metrics, efficiency_metrics, stability_metrics, None
        )
        
        return PerformanceMetrics(
            max_error=accuracy_metrics['max_error'],
            l2_error=accuracy_metrics['l2_error'],
            mean_error=accuracy_metrics['mean_error'],
            error_percentile_95=accuracy_metrics['error_percentile_95'],
            runtime=efficiency_metrics['runtime'],
            n_steps=efficiency_metrics['n_steps'],
            steps_per_second=efficiency_metrics['steps_per_second'],
            efficiency_score=efficiency_metrics['efficiency_score'],
            stability_score=stability_metrics['stability_score'],
            convergence_rate=stability_metrics['convergence_rate'],
            composite_score=composite_score,
            success_rate=n_successful / n_total,
            n_successful=n_successful,
            n_total=n_total
        )
    
    def _evaluate_parallel(self, 
                          butcher_table: ButcherTable,
                          ode_batch: List[ODEParameters],
                          step_size: float = None,
                          use_varied_steps: bool = True) -> PerformanceMetrics:
        """Evaluate using multiprocessing for speed."""
        
        # Create a partial function for the evaluation
        eval_func = partial(self._evaluate_single_ode, butcher_table, step_size, use_varied_steps)
        
        # Use multiprocessing with more cores for better performance
        n_cores = min(8, mp.cpu_count())  # Use up to 8 cores for better utilization
        
        with mp.Pool(processes=n_cores) as pool:
            results = pool.map(eval_func, ode_batch)
        
        # Process results
        successful_results = [r for r in results if r is not None]
        
        if not successful_results:
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
                n_total=len(ode_batch)
            )
        
        # Convert to the same format as sequential evaluation
        processed_results = []
        for result in successful_results:
            processed_results.append({
                'max_error': result['max_error'],
                'l2_error': result['l2_error'],
                'runtime': result['runtime'],
                'n_steps': result['n_steps'],
                'is_stiff': result['is_stiff']
            })
        
        # Use the same processing logic as sequential evaluation
        return self._process_results(processed_results, len(ode_batch), butcher_table)
    
    def _evaluate_single_ode(self, butcher_table: ButcherTable, step_size: float, use_varied_steps: bool, ode_params: ODEParameters):
        """Evaluate a single ODE (for multiprocessing)."""
        try:
            eval_result = self.benchmark.evaluate_butcher_table(
                butcher_table, ode_params, h=step_size, use_varied_steps=use_varied_steps
            )
            
            if eval_result['success']:
                return {
                    'max_error': eval_result['max_error'],
                    'l2_error': eval_result['l2_error'],
                    'runtime': eval_result['runtime'],
                    'n_steps': eval_result['n_steps'],
                    'is_stiff': ode_params.is_stiff
                }
        except:
            pass
        return None
    
    def _process_results(self, results: List[Dict], n_total: int, butcher_table=None) -> PerformanceMetrics:
        """Process evaluation results into metrics."""
        n_successful = len(results)
        
        if n_successful == 0:
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
                n_total=n_total
            )
        
        # Extract arrays
        max_errors = np.array([r['max_error'] for r in results])
        l2_errors = np.array([r['l2_error'] for r in results])
        runtimes = np.array([r['runtime'] for r in results])
        n_steps = np.array([r['n_steps'] for r in results])
        is_stiff = np.array([r['is_stiff'] for r in results])
        
        # Compute metrics
        accuracy_metrics = self._compute_accuracy_metrics(max_errors, l2_errors)
        efficiency_metrics = self._compute_efficiency_metrics(runtimes, n_steps)
        stability_metrics = self._compute_stability_metrics(results, is_stiff)
        
        # Composite score
        composite_score = self._compute_composite_score(
            accuracy_metrics, efficiency_metrics, stability_metrics, None
        )
        
        return PerformanceMetrics(
            max_error=accuracy_metrics['max_error'],
            l2_error=accuracy_metrics['l2_error'],
            mean_error=accuracy_metrics['mean_error'],
            error_percentile_95=accuracy_metrics['error_percentile_95'],
            runtime=efficiency_metrics['runtime'],
            n_steps=efficiency_metrics['n_steps'],
            steps_per_second=efficiency_metrics['steps_per_second'],
            efficiency_score=efficiency_metrics['efficiency_score'],
            stability_score=stability_metrics['stability_score'],
            convergence_rate=stability_metrics['convergence_rate'],
            composite_score=composite_score,
            success_rate=n_successful / n_total,
            n_successful=n_successful,
            n_total=n_total
        )
    
    def _compute_accuracy_metrics(self, 
                                 max_errors: np.ndarray, 
                                 l2_errors: np.ndarray) -> Dict[str, float]:
        """Compute accuracy-related metrics."""
        
        # Handle NaN and infinite values
        max_errors = np.nan_to_num(max_errors, nan=1e-6, posinf=1e-6, neginf=1e-6)
        l2_errors = np.nan_to_num(l2_errors, nan=1e-6, posinf=1e-6, neginf=1e-6)
        
        # Use log-scale for errors to handle wide dynamic range
        log_max_errors = np.log10(np.maximum(max_errors, 1e-16))
        log_l2_errors = np.log10(np.maximum(l2_errors, 1e-16))
        
        # Ensure no NaN values in final calculations
        mean_max_error = np.nan_to_num(np.mean(max_errors), nan=1e-6)
        mean_l2_error = np.nan_to_num(np.mean(l2_errors), nan=1e-6)
        mean_log_error = np.nan_to_num(np.mean(log_l2_errors), nan=-6.0)
        percentile_95 = np.nan_to_num(np.percentile(log_l2_errors, 95), nan=-6.0)
        
        return {
            'max_error': mean_max_error,
            'l2_error': mean_l2_error,
            'mean_error': mean_log_error,
            'error_percentile_95': percentile_95
        }
    
    def _compute_efficiency_metrics(self, 
                                   runtimes: np.ndarray, 
                                   n_steps: np.ndarray) -> Dict[str, float]:
        """Compute efficiency-related metrics."""
        
        total_runtime = np.sum(runtimes)
        total_steps = np.sum(n_steps)
        
        steps_per_second = total_steps / total_runtime if total_runtime > 0 else 0.0
        
        # Normalized efficiency score (higher is better)
        # Based on steps per second, normalized by method complexity
        efficiency_score = min(steps_per_second / 1000.0, 1.0)  # Cap at 1.0
        
        return {
            'runtime': total_runtime,
            'n_steps': total_steps,
            'steps_per_second': steps_per_second,
            'efficiency_score': efficiency_score
        }
    
    def _compute_stability_metrics(self, 
                                  results: List[Dict[str, Any]], 
                                  is_stiff: np.ndarray) -> Dict[str, float]:
        """Compute stability-related metrics."""
        
        # Separate stiff and non-stiff results
        stiff_results = [r for r, stiff in zip(results, is_stiff) if stiff]
        nonstiff_results = [r for r, stiff in zip(results, is_stiff) if not stiff]
        
        stability_score = 0.0
        convergence_rate = 0.0
        
        # Calculate stability based on error consistency across all problems
        all_errors = np.array([r['max_error'] for r in results])
        all_errors = np.nan_to_num(all_errors, nan=1e-6, posinf=1e-6, neginf=1e-6)
        
        if len(all_errors) > 0:
            # Stability score based on error consistency (lower variance = more stable)
            error_variance = np.var(np.log10(np.maximum(all_errors, 1e-16)))
            stability_score = max(0.0, min(1.0, 1.0 - error_variance / 10.0))
        
        # Additional stability boost for good performance on stiff problems
        if len(stiff_results) > 0:
            stiff_max_errors = np.array([r['max_error'] for r in stiff_results])
            stiff_max_errors = np.nan_to_num(stiff_max_errors, nan=1e-6, posinf=1e-6, neginf=1e-6)
            
            if len(stiff_max_errors) > 0:
                stiff_log_errors = np.log10(np.maximum(stiff_max_errors, 1e-16))
                stiff_performance = max(0.0, 1.0 - np.mean(stiff_log_errors) / 5.0)
                stability_score = max(stability_score, stiff_performance)
        
        if len(results) > 1:
            # Estimate convergence rate by comparing errors vs steps
            errors = np.array([r['l2_error'] for r in results])
            steps = np.array([r['n_steps'] for r in results])
            
            # Handle NaN values
            errors = np.nan_to_num(errors, nan=1e-6, posinf=1e-6, neginf=1e-6)
            steps = np.nan_to_num(steps, nan=1, posinf=1, neginf=1)
            
            # Simple convergence rate estimate
            log_errors = np.log10(np.maximum(errors, 1e-16))
            log_steps = np.log10(np.maximum(steps, 1))
            
            if len(log_errors) > 1 and np.std(log_steps) > 0:
                try:
                    correlation = np.corrcoef(log_steps, log_errors)[0, 1]
                    convergence_rate = max(0.0, min(1.0, -correlation))
                except:
                    convergence_rate = 0.0
        
        return {
            'stability_score': stability_score,
            'convergence_rate': convergence_rate
        }
    
    def _compute_composite_score(self, 
                                accuracy_metrics: Dict[str, float],
                                efficiency_metrics: Dict[str, float],
                                stability_metrics: Dict[str, float],
                                butcher_table: ButcherTable = None) -> float:
        """Compute weighted composite score with diversity constraints."""
        
        # Normalize accuracy (lower error is better)
        accuracy_score = max(0.0, 1.0 - accuracy_metrics['mean_error'] / 10.0)
        
        # Efficiency and stability scores are already normalized
        efficiency_score = efficiency_metrics['efficiency_score']
        stability_score = stability_metrics['stability_score']
        
        # Weighted combination
        composite = (
            self.config.ACCURACY_WEIGHT * accuracy_score +
            self.config.EFFICIENCY_WEIGHT * efficiency_score +
            self.config.STABILITY_WEIGHT * stability_score
        )
        
        # Add bonus points for c vector in [0,1] range
        if butcher_table is not None and hasattr(butcher_table, 'c') and butcher_table.c is not None:
            c_bonus = self._compute_c_vector_bonus(butcher_table.c)
            composite += c_bonus
        
        # Apply diversity constraints if available
        if hasattr(self.config, 'DIVERSITY_PENALTY') and butcher_table is not None:
            diversity_penalty = self._compute_diversity_penalty(butcher_table)
            composite -= self.config.DIVERSITY_PENALTY * diversity_penalty
        
        # Apply stability radius constraints if available
        if hasattr(self.config, 'MIN_STABILITY_RADIUS') and butcher_table is not None:
            if butcher_table.stability_radius < self.config.MIN_STABILITY_RADIUS:
                composite *= 0.5  # Heavy penalty for low stability
            elif hasattr(self.config, 'MAX_STABILITY_RADIUS') and butcher_table.stability_radius > self.config.MAX_STABILITY_RADIUS:
                composite *= 0.7  # Moderate penalty for excessive stability
        
        return max(0.0, min(composite, 1.0))
    
    def _compute_c_vector_bonus(self, c_vector: np.ndarray) -> float:
        """Compute bonus points for c vector being in [0,1] range."""
        if c_vector is None or len(c_vector) == 0:
            return 0.0
        
        # Count how many c values are in [0,1] range
        in_range = np.sum((c_vector >= 0) & (c_vector <= 1))
        total = len(c_vector)
        
        # Bonus proportional to how many values are in range
        # Maximum bonus of 0.1 (10% of total score)
        bonus = 0.1 * (in_range / total)
        
        return bonus
    
    def _compute_diversity_penalty(self, butcher_table: ButcherTable) -> float:
        """Compute diversity penalty based on similarity to previous solutions."""
        penalty = 0.0
        
        # Penalize forbidden stage counts
        if hasattr(self.config, 'FORBIDDEN_STAGES') and len(butcher_table.b) == self.config.FORBIDDEN_STAGES:
            penalty += 0.8  # Heavy penalty for forbidden stage methods
        
        # Bonus for non-forbidden stage methods
        if hasattr(self.config, 'STAGE_DIVERSITY_BONUS') and len(butcher_table.b) != getattr(self.config, 'FORBIDDEN_STAGES', 4):
            penalty -= self.config.STAGE_DIVERSITY_BONUS
        
        # Penalize coefficient similarity to forbidden coefficients
        if hasattr(self.config, 'FORBIDDEN_COEFFICIENTS') and self.config.FORBIDDEN_COEFFICIENTS:
            coefficient_penalty = self._compute_coefficient_penalty(butcher_table)
            penalty += coefficient_penalty
        
        # Bonus for coefficient diversity
        if hasattr(self.config, 'COEFFICIENT_DIVERSITY_BONUS'):
            coefficient_bonus = self._compute_coefficient_bonus(butcher_table)
            penalty -= coefficient_bonus
        
        # Penalize stability radius similar to optimal (~2.0)
        if abs(butcher_table.stability_radius - 2.0) < 0.5:
            penalty += 0.3  # Penalty for stability radius near optimal
        
        # Add small random component for exploration
        import random
        penalty += random.random() * 0.1
        
        return max(0.0, penalty)
    
    def _compute_coefficient_penalty(self, butcher_table: ButcherTable) -> float:
        """Compute penalty for coefficient similarity to forbidden coefficients."""
        penalty = 0.0
        tolerance = 0.1  # Tolerance for coefficient similarity
        
        # Extract all coefficients from butcher table
        coefficients = []
        coefficients.extend(butcher_table.c)  # c coefficients
        coefficients.extend(butcher_table.b)   # b coefficients
        
        # Add A matrix coefficients (upper triangular)
        for i in range(len(butcher_table.A)):
            for j in range(i):  # Only upper triangular
                coefficients.append(butcher_table.A[i][j])
        
        # Check similarity to forbidden coefficients
        for coeff in coefficients:
            for forbidden_coeff in self.config.FORBIDDEN_COEFFICIENTS:
                if abs(coeff - forbidden_coeff) < tolerance:
                    penalty += 0.1  # Small penalty per similar coefficient
        
        return min(penalty, 0.5)  # Cap penalty at 0.5
    
    def _compute_coefficient_bonus(self, butcher_table: ButcherTable) -> float:
        """Compute bonus for coefficient diversity."""
        bonus = 0.0
        tolerance = 0.2  # Tolerance for coefficient difference
        
        # Extract all coefficients from butcher table
        coefficients = []
        coefficients.extend(butcher_table.c)  # c coefficients
        coefficients.extend(butcher_table.b)   # b coefficients
        
        # Add A matrix coefficients (upper triangular)
        for i in range(len(butcher_table.A)):
            for j in range(i):  # Only upper triangular
                coefficients.append(butcher_table.A[i][j])
        
        # Check diversity from forbidden coefficients
        diverse_count = 0
        for coeff in coefficients:
            is_diverse = True
            for forbidden_coeff in getattr(self.config, 'FORBIDDEN_COEFFICIENTS', []):
                if abs(coeff - forbidden_coeff) < tolerance:
                    is_diverse = False
                    break
            if is_diverse:
                diverse_count += 1
        
        # Bonus proportional to diversity
        if len(coefficients) > 0:
            diversity_ratio = diverse_count / len(coefficients)
            bonus = diversity_ratio * self.config.COEFFICIENT_DIVERSITY_BONUS
        
        return bonus

class BaselineComparator:
    """Compares candidate methods against baseline integrators."""
    
    def __init__(self, metrics_calculator: MetricsCalculator):
        self.metrics_calculator = metrics_calculator
        self.baseline_metrics = {}
    
    def compute_baseline_metrics(self, 
                                ode_batch: List[ODEParameters],
                                step_size: float = None) -> Dict[str, PerformanceMetrics]:
        """Compute metrics for all baseline methods."""
        
        from src.core.butcher_tables import get_all_baseline_tables
        
        baseline_tables = get_all_baseline_tables()
        baseline_metrics = {}
        
        for name, table in tqdm(baseline_tables.items(), desc="Computing baseline metrics"):
            print(f"Computing baseline metrics for {name}...")
            metrics = self.metrics_calculator.evaluate_on_ode_batch(
                table, ode_batch, step_size
            )
            baseline_metrics[name] = metrics
        
        self.baseline_metrics = baseline_metrics
        return baseline_metrics
    
    def compare_to_baselines(self, 
                           candidate_metrics: PerformanceMetrics,
                           baseline_metrics: Dict[str, PerformanceMetrics] = None) -> Dict[str, Dict[str, float]]:
        """Compare candidate metrics to baseline methods."""
        
        if baseline_metrics is None:
            baseline_metrics = self.baseline_metrics
        
        if not baseline_metrics:
            return {}
        
        comparisons = {}
        
        for baseline_name, baseline_metric in baseline_metrics.items():
            comparison = {}
            
            # Accuracy comparison
            if baseline_metric.max_error > 0:
                comparison['accuracy_ratio'] = candidate_metrics.max_error / baseline_metric.max_error
            else:
                comparison['accuracy_ratio'] = float('inf')
            
            # Efficiency comparison
            if baseline_metric.runtime > 0:
                comparison['efficiency_ratio'] = baseline_metric.runtime / candidate_metrics.runtime
            else:
                comparison['efficiency_ratio'] = float('inf')
            
            # Stability comparison
            if baseline_metric.stability_score > 0:
                comparison['stability_ratio'] = candidate_metrics.stability_score / baseline_metric.stability_score
            else:
                comparison['stability_ratio'] = 0.0
            
            # Overall score comparison
            comparison['score_ratio'] = candidate_metrics.composite_score / baseline_metric.composite_score
            
            # Performance vs baseline
            comparison['better_accuracy'] = comparison['accuracy_ratio'] < 1.0
            comparison['better_efficiency'] = comparison['efficiency_ratio'] < 1.0
            comparison['better_stability'] = comparison['stability_ratio'] > 1.0
            comparison['better_overall'] = comparison['score_ratio'] > 1.0
            
            comparisons[baseline_name] = comparison
        
        return comparisons

class MetricsLogger:
    """Logs and stores metrics for analysis and visualization."""
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or "metrics_log.csv"
        self.metrics_history = []
    
    def log_metrics(self, 
                   butcher_table: ButcherTable,
                   metrics: PerformanceMetrics,
                   comparisons: Dict[str, Dict[str, float]] = None,
                   epoch: int = None):
        """Log metrics for a Butcher table."""
        
        # Convert Butcher table to dict for logging
        table_dict = butcher_table.to_dict()
        
        log_entry = {
            'epoch': epoch,
            'table_id': id(butcher_table),
            'stages': len(butcher_table.b),
            'is_explicit': butcher_table.is_explicit,
            'consistency_order': butcher_table.consistency_order,
            'stability_radius': butcher_table.stability_radius,
            **metrics.__dict__,
            'comparisons': comparisons
        }
        
        self.metrics_history.append(log_entry)
    
    def save_to_csv(self, filename: str = None):
        """Save metrics to CSV file."""
        import pandas as pd
        
        filename = filename or self.log_file
        
        # Flatten the data for CSV
        flattened_data = []
        for entry in self.metrics_history:
            flat_entry = {k: v for k, v in entry.items() if k != 'comparisons'}
            
            # Add comparison columns
            if entry['comparisons']:
                for baseline_name, comparison in entry['comparisons'].items():
                    for metric, value in comparison.items():
                        flat_entry[f'{baseline_name}_{metric}'] = value
            
            flattened_data.append(flat_entry)
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(filename, index=False)
        print(f"Saved metrics to {filename}")
    
    def get_best_performers(self, 
                           metric: str = 'composite_score',
                           n_top: int = 10) -> List[Dict[str, Any]]:
        """Get the top performing methods by a specific metric."""
        
        # Sort by metric (descending for scores, ascending for errors)
        reverse = metric in ['composite_score', 'efficiency_score', 'stability_score', 'success_rate']
        
        sorted_history = sorted(
            self.metrics_history,
            key=lambda x: x[metric],
            reverse=reverse
        )
        
        return sorted_history[:n_top]

if __name__ == "__main__":
    # Test metrics calculation
    print("Testing metrics calculation...")
    
    # Create dummy results for testing
    dummy_results = [
        {'max_error': 1e-6, 'l2_error': 1e-7, 'runtime': 0.1, 'n_steps': 100, 'is_stiff': False},
        {'max_error': 1e-5, 'l2_error': 1e-6, 'runtime': 0.2, 'n_steps': 200, 'is_stiff': True},
        {'max_error': 1e-7, 'l2_error': 1e-8, 'runtime': 0.05, 'n_steps': 50, 'is_stiff': False}
    ]
    
    # Test metrics calculation (without actual benchmark)
    from src.core.butcher_tables import get_rk4
    from src.core.integrator_runner import IntegratorBenchmark, ReferenceSolver
    
    # Create a simple benchmark
    ref_solver = ReferenceSolver()
    benchmark = IntegratorBenchmark(ref_solver)
    metrics_calc = MetricsCalculator(benchmark)
    
    # Test with dummy data
    print("Metrics calculation test completed.")

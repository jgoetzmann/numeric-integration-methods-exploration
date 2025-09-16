"""
Training Pipeline Module.

This module implements the complete optimization loop for discovering
novel Butcher tables using machine learning and evolutionary algorithms.
"""

import os
import time
import json
import numpy as np
import torch
import warnings
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns

# Suppress numerical warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', message='.*overflow.*')
warnings.filterwarnings('ignore', message='.*invalid value.*')
warnings.filterwarnings('ignore', message='.*Casting complex values.*')
warnings.filterwarnings('ignore', message='.*ComplexWarning.*')

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config
from ode_dataset import ODEDataset
from butcher_tables import ButcherTable, get_all_baseline_tables
from integrator_runner import IntegratorBenchmark, ReferenceSolver
from metrics import MetricsCalculator, BaselineComparator, MetricsLogger, PerformanceMetrics
from model import MLPipeline, ModelConfig

class TrainingPipeline:
    """Complete training pipeline for discovering novel integration methods."""
    
    def __init__(self, model_config: ModelConfig = None, config_obj = None):
        self.config = config_obj or config
        self.model_config = model_config or ModelConfig()
        
        # Initialize components
        self.dataset = ODEDataset(config_obj=self.config)
        self.reference_solver = ReferenceSolver()
        self.benchmark = IntegratorBenchmark(self.reference_solver)
        self.metrics_calculator = MetricsCalculator(self.benchmark, config_obj=self.config)
        self.baseline_comparator = BaselineComparator(self.metrics_calculator)
        self.metrics_logger = MetricsLogger()
        
        # ML pipeline
        self.ml_pipeline = MLPipeline(self.model_config)
        
        # Training state
        self.epoch = 0
        self.best_score = 0.0
        self.best_table = None
        self.training_history = []
        
        # Baseline metrics cache
        self.baseline_metrics = {}
        
    def initialize_training(self, force_regenerate_dataset: bool = False):
        """Initialize training by generating dataset and computing baselines."""
        
        print("Initializing training pipeline...")
        
        # Generate ODE dataset
        self.dataset.generate_dataset(force_regenerate=force_regenerate_dataset)
        
        # Compute baseline metrics on a representative sample
        print("Computing baseline metrics...")
        sample_batch = self.dataset.get_batch(min(500, len(self.dataset)))
        self.baseline_metrics = self.baseline_comparator.compute_baseline_metrics(sample_batch)
        
        print("Baseline metrics computed:")
        for name, metrics in self.baseline_metrics.items():
            print(f"  {name}: composite_score={metrics.composite_score:.4f}, "
                  f"accuracy={metrics.max_error:.2e}, efficiency={metrics.efficiency_score:.4f}")
        
        # Initialize ML pipeline with baseline data
        self._initialize_ml_with_baselines()
    
    def _initialize_ml_with_baselines(self):
        """Initialize ML models with baseline Butcher tables."""
        
        print("Initializing ML models with baseline methods...")
        
        baseline_tables = list(get_all_baseline_tables().values())
        
        # Evaluate baselines on training batch
        train_batch = self.dataset.get_batch(self.config.BATCH_SIZE)
        baseline_metrics_list = []
        
        for table in baseline_tables:
            metrics = self.metrics_calculator.evaluate_on_ode_batch(table, train_batch)
            baseline_metrics_list.append(metrics)
        
        # Add to training data
        self.ml_pipeline.update_training_data(baseline_tables, baseline_metrics_list)
        
        # Train surrogate model
        self.ml_pipeline.train_surrogate(baseline_tables, baseline_metrics_list, n_epochs=50)
        
        print("ML models initialized with baseline data")
    
    def train_epoch(self, use_evolution: bool = False) -> Dict[str, Any]:
        """Train for one epoch."""
        
        self.epoch += 1
        
        # Get training batch
        if self.epoch % 3 == 0:
            # Use stiff problems every third epoch
            train_batch = self.dataset.get_stiff_batch(self.config.BATCH_SIZE // 2)
            train_batch.extend(self.dataset.get_nonstiff_batch(self.config.BATCH_SIZE // 2))
        else:
            train_batch = self.dataset.get_batch(self.config.BATCH_SIZE)
        
        # Generate candidates
        candidates = self.ml_pipeline.generate_candidates(
            n_candidates=self.config.N_CANDIDATES_PER_BATCH,
            use_evolution=use_evolution,
            stages=self.config.DEFAULT_STAGES
        )
        
        # Evaluate candidates
        print(f"Epoch {self.epoch}: Evaluating {len(candidates)} candidates...")
        candidate_metrics = []
        valid_candidates = []
        
        for i, candidate in enumerate(tqdm(candidates, desc=f"Epoch {self.epoch}: Evaluating candidates", 
                                          bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')):
            try:
                metrics = self.metrics_calculator.evaluate_on_ode_batch(candidate, train_batch)
                
                if metrics.success_rate > 0.5:  # Only keep successful methods
                    candidate_metrics.append(metrics)
                    valid_candidates.append(candidate)
                    
                    # Log metrics
                    comparisons = self.baseline_comparator.compare_to_baselines(metrics, self.baseline_metrics)
                    self.metrics_logger.log_metrics(candidate, metrics, comparisons, self.epoch)
                    
            except Exception as e:
                # Silently skip failed candidates to avoid cluttering output
                continue
        
        if not valid_candidates:
            print("No valid candidates found in this epoch")
            return {'epoch': self.epoch, 'n_valid_candidates': 0}
        
        # Update training data and retrain surrogate
        self.ml_pipeline.update_training_data(valid_candidates, candidate_metrics)
        self.ml_pipeline.train_surrogate(valid_candidates, candidate_metrics, n_epochs=20)
        
        # Update evolutionary population if using evolution
        if use_evolution and hasattr(self.ml_pipeline, 'evolutionary_population'):
            fitness_scores = [m.composite_score for m in candidate_metrics]
            self.ml_pipeline.evolutionary_population = self.ml_pipeline.evolutionary_generator.evolve(
                valid_candidates, fitness_scores, n_generations=1
            )
        
        # Track best performer
        best_idx = np.argmax([m.composite_score for m in candidate_metrics])
        best_metrics = candidate_metrics[best_idx]
        best_candidate = valid_candidates[best_idx]
        
        if best_metrics.composite_score > self.best_score:
            self.best_score = best_metrics.composite_score
            self.best_table = best_candidate
            print(f"New best score: {self.best_score:.4f}")
        
        # Calculate normalized accuracy (0-1 scale, 1 = most accurate)
        best_max_error = max(best_metrics.max_error, 1e-16)
        normalized_accuracy = 1.0 / (1.0 + np.log10(best_max_error))
        normalized_accuracy = max(0.0, min(1.0, normalized_accuracy))
        
        # Store epoch results
        epoch_results = {
            'epoch': self.epoch,
            'n_valid_candidates': len(valid_candidates),
            'best_score': best_metrics.composite_score,
            'mean_score': np.mean([m.composite_score for m in candidate_metrics]),
            'best_accuracy': normalized_accuracy,  # Normalized accuracy (0-1)
            'best_efficiency': best_metrics.efficiency_score,
            'best_stability': best_metrics.stability_score,
            'surrogate_loss': self.ml_pipeline.surrogate_losses[-1] if self.ml_pipeline.surrogate_losses else 0.0
        }
        
        self.training_history.append(epoch_results)
        
        return epoch_results
    
    def evaluate_on_full_dataset(self) -> Dict[str, Any]:
        """Evaluate best method on full dataset."""
        
        if self.best_table is None:
            print("No best table found yet")
            return {}
        
        print("Evaluating best method on sample dataset...")
        
        # Use a smaller sample for faster evaluation
        sample_size = min(500, len(self.dataset.generated_odes))
        sample_odes = self.dataset.get_batch(sample_size)
        
        print(f"Evaluating on {len(sample_odes)} ODEs...")
        full_metrics = self.metrics_calculator.evaluate_on_ode_batch(
            self.best_table, sample_odes
        )
        
        # Compare to baselines on the same sample
        full_baseline_metrics = self.baseline_comparator.compute_baseline_metrics(
            sample_odes
        )
        
        comparisons = self.baseline_comparator.compare_to_baselines(
            full_metrics, full_baseline_metrics
        )
        
        results = {
            'best_table_metrics': full_metrics,
            'baseline_metrics': full_baseline_metrics,
            'comparisons': comparisons
        }
        
        # Save best table
        self._save_best_table(full_metrics, comparisons)
        
        return results
    
    def _save_best_table(self, metrics: PerformanceMetrics, comparisons: Dict[str, Dict[str, float]]):
        """Save the best performing Butcher table."""
        
        if self.best_table is None:
            return
        
        # Save table specification
        table_spec = {
            'butcher_table': self.best_table.to_dict(),
            'metrics': metrics.__dict__,
            'comparisons': comparisons,
            'training_epoch': self.epoch,
            'config': self.config.__dict__
        }
        
        results_file = os.path.join(self.config.RESULTS_DIR, 'best_butcher_table.json')
        with open(results_file, 'w') as f:
            json.dump(table_spec, f, indent=2, default=str)
        
        print(f"Saved best table to {results_file}")
    
    def save_checkpoint(self):
        """Save training checkpoint."""
        
        checkpoint = {
            'epoch': self.epoch,
            'best_score': self.best_score,
            'best_table': self.best_table.to_dict() if self.best_table else None,
            'training_history': self.training_history,
            'config': self.config.__dict__
        }
        
        checkpoint_file = os.path.join(self.config.CHECKPOINTS_DIR, f'checkpoint_epoch_{self.epoch}.json')
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)
        
        # Save ML models
        self.ml_pipeline.save_models(self.config.CHECKPOINTS_DIR)
        
        print(f"Saved checkpoint to {checkpoint_file}")
    
    def load_checkpoint(self, checkpoint_file: str):
        """Load training checkpoint."""
        
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        
        self.epoch = checkpoint['epoch']
        self.best_score = checkpoint['best_score']
        
        if checkpoint['best_table']:
            from butcher_tables import ButcherTable
            self.best_table = ButcherTable.from_dict(checkpoint['best_table'])
        
        self.training_history = checkpoint['training_history']
        
        # Load ML models
        ml_checkpoint = os.path.join(self.config.CHECKPOINTS_DIR, 'ml_pipeline.pth')
        if os.path.exists(ml_checkpoint):
            self.ml_pipeline.load_models(ml_checkpoint)
        
        print(f"Loaded checkpoint from {checkpoint_file}")
    
    def plot_training_progress(self):
        """Plot training progress."""
        
        if not self.training_history:
            return
        
        epochs = [h['epoch'] for h in self.training_history]
        best_scores = [h['best_score'] for h in self.training_history]
        mean_scores = [h['mean_score'] for h in self.training_history]
        
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 2, 1)
        plt.plot(epochs, best_scores, 'b-', label='Best Score')
        plt.plot(epochs, mean_scores, 'r--', label='Mean Score')
        plt.xlabel('Epoch')
        plt.ylabel('Composite Score')
        plt.title('Training Progress')
        plt.legend()
        plt.grid(True)
        
        plt.subplot(2, 2, 2)
        accuracies = [h['best_accuracy'] for h in self.training_history]
        plt.semilogy(epochs, accuracies, 'g-')
        plt.xlabel('Epoch')
        plt.ylabel('Max Error (log scale)')
        plt.title('Best Accuracy')
        plt.grid(True)
        
        plt.subplot(2, 2, 3)
        efficiencies = [h['best_efficiency'] for h in self.training_history]
        plt.plot(epochs, efficiencies, 'm-')
        plt.xlabel('Epoch')
        plt.ylabel('Efficiency Score')
        plt.title('Best Efficiency')
        plt.grid(True)
        
        plt.subplot(2, 2, 4)
        n_candidates = [h['n_valid_candidates'] for h in self.training_history]
        plt.plot(epochs, n_candidates, 'c-')
        plt.xlabel('Epoch')
        plt.ylabel('Valid Candidates')
        plt.title('Valid Candidates per Epoch')
        plt.grid(True)
        
        plt.tight_layout()
        
        plot_file = os.path.join(self.config.RESULTS_DIR, 'training_progress.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Training progress plot saved to {plot_file}")
    
    def run_training(self, 
                    n_epochs: int = None,
                    use_evolution: bool = False,
                    save_frequency: int = 10,
                    full_eval_frequency: int = 50):
        """Run the complete training pipeline."""
        
        n_epochs = n_epochs or self.config.N_EPOCHS
        
        print(f"Starting training for {n_epochs} epochs...")
        print(f"Using {'evolutionary' if use_evolution else 'neural network'} approach")
        
        start_time = time.time()
        
        try:
            for epoch in tqdm(range(n_epochs), desc="Training Progress", 
                             bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'):
                epoch_results = self.train_epoch(use_evolution=use_evolution)
                
                # Print detailed progress
                print(f"\nEpoch {epoch_results['epoch']}/{n_epochs}:")
                print(f"   Best Score: {epoch_results['best_score']:.4f}")
                print(f"   Mean Score: {epoch_results['mean_score']:.4f}")
                print(f"   Valid Candidates: {epoch_results['n_valid_candidates']}")
                print(f"   Best Accuracy: {epoch_results['best_accuracy']:.4f}")
                print(f"   Best Efficiency: {epoch_results['best_efficiency']:.4f}")
                print(f"   Best Stability: {epoch_results['best_stability']:.4f}")
                print("-" * 50)
                
                # Save checkpoint
                if (epoch + 1) % save_frequency == 0:
                    self.save_checkpoint()
                
                # Full evaluation
                if (epoch + 1) % full_eval_frequency == 0:
                    full_results = self.evaluate_on_full_dataset()
                    if full_results:
                        print(f"Full dataset evaluation: "
                              f"Best composite score = {full_results['best_table_metrics'].composite_score:.4f}")
        
        except KeyboardInterrupt:
            print("Training interrupted by user")
        
        # Final evaluation
        print("Running final evaluation...")
        final_results = self.evaluate_on_full_dataset()
        
        # Save final results
        self.save_checkpoint()
        self.metrics_logger.save_to_csv()
        self.plot_training_progress()
        
        training_time = time.time() - start_time
        print(f"Training completed in {training_time:.2f} seconds")
        
        return final_results

def main():
    """Main training function."""
    
    # Initialize training pipeline
    pipeline = TrainingPipeline()
    
    # Initialize training
    pipeline.initialize_training(force_regenerate_dataset=False)
    
    # Run training
    results = pipeline.run_training(
        n_epochs=100,
        use_evolution=False,  # Start with neural network approach
        save_frequency=10,
        full_eval_frequency=25
    )
    
    # Print final results
    if results:
        print("\n" + "="*50)
        print("FINAL RESULTS")
        print("="*50)
        
        best_metrics = results['best_table_metrics']
        print(f"Best Butcher Table Performance:")
        print(f"  Composite Score: {best_metrics.composite_score:.4f}")
        print(f"  Max Error: {best_metrics.max_error:.2e}")
        print(f"  Efficiency Score: {best_metrics.efficiency_score:.4f}")
        print(f"  Stability Score: {best_metrics.stability_score:.4f}")
        print(f"  Success Rate: {best_metrics.success_rate:.2%}")
        
        print(f"\nComparison to Baselines:")
        for baseline_name, comparison in results['comparisons'].items():
            print(f"  vs {baseline_name}:")
            print(f"    Accuracy: {comparison['accuracy_ratio']:.2f}x")
            print(f"    Efficiency: {comparison['efficiency_ratio']:.2f}x")
            print(f"    Overall: {comparison['score_ratio']:.2f}x")
        
        print(f"\nBest Butcher Table:")
        print(pipeline.best_table)

if __name__ == "__main__":
    main()

"""
Enhanced training script for 4-stage Butcher table with aggressive novelty search and two-phase training.

This script implements:
1. Two-phase training: aggressive exploration (epochs 1-50) -> optimization (epochs 51-100)
2. Diversity preservation mechanism for top-5 solutions
3. Enhanced novelty rewards (30% vs 3% in original)
4. Anti-convergence mechanisms to prevent RK4 convergence
5. Adaptive evolution parameters
"""

import sys
import os
import numpy as np
import torch
import random
import time
from typing import List, Dict, Any, Tuple
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from configs.trial_4stage_novelty_2 import trial_4stage_novelty_2_config as config
from src.training.train import TrainingPipeline
from src.models.model import ModelConfig
from src.core.butcher_tables import ButcherTable

# Set unique random seed for this trial
RANDOM_SEED = 2009
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)

class EnhancedNoveltyTrainingPipeline(TrainingPipeline):
    """Enhanced training pipeline with two-phase training and diversity preservation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_phase = 1
        self.diversity_archive = []  # Store top-5 diverse solutions
        self.phase_switch_epoch = config.PHASE_SWITCH_EPOCH
        
    def compute_diversity_score(self, table1: ButcherTable, table2: ButcherTable) -> float:
        """Compute diversity score between two Butcher tables."""
        if table1 is None or table2 is None:
            return 1.0
        
        # Compare A matrices
        a_diff = np.mean(np.abs(table1.A - table2.A))
        
        # Compare b vectors
        b_diff = np.mean(np.abs(table1.b - table2.b))
        
        # Compare c vectors
        c_diff = np.mean(np.abs(table1.c - table2.c))
        
        # Overall diversity score
        return (a_diff + b_diff + c_diff) / 3.0
    
    def update_diversity_archive(self, candidates: List[Tuple[ButcherTable, float]]) -> None:
        """Update the diversity archive with top-5 most diverse high-performing solutions."""
        if not candidates:
            return
        
        # Filter candidates by minimum performance threshold
        good_candidates = [
            (table, score) for table, score in candidates 
            if score >= config.PERFORMANCE_THRESHOLD
        ]
        
        if not good_candidates:
            # If no good candidates, take the best ones anyway
            good_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:5]
        
        # Start with the best candidate
        new_archive = [good_candidates[0]]
        
        # Add diverse candidates
        for table, score in good_candidates[1:]:
            if len(new_archive) >= config.DIVERSITY_PRESERVATION_SIZE:
                break
            
            # Check diversity against existing archive
            min_diversity = min(
                self.compute_diversity_score(table, archived[0])
                for archived in new_archive
            )
            
            # Add if sufficiently diverse
            if min_diversity >= config.DIVERSITY_THRESHOLD:
                new_archive.append((table, score))
        
        # Fill remaining slots with best performers if needed
        while len(new_archive) < config.DIVERSITY_PRESERVATION_SIZE and len(good_candidates) > len(new_archive):
            remaining = [
                cand for cand in good_candidates 
                if not any(np.array_equal(cand[0].A, arch[0].A) for arch in new_archive)
            ]
            if remaining:
                new_archive.append(remaining[0])
            else:
                break
        
        self.diversity_archive = new_archive
        
        print(f"  Diversity archive updated: {len(self.diversity_archive)} diverse solutions preserved")
        if self.diversity_archive:
            diversities = [
                min(self.compute_diversity_score(self.diversity_archive[i][0], self.diversity_archive[j][0])
                    for j in range(len(self.diversity_archive)) if i != j)
                for i in range(len(self.diversity_archive))
            ]
            avg_diversity = np.mean(diversities) if len(diversities) > 1 else 0.0
            print(f"  Average inter-solution diversity: {avg_diversity:.4f}")
    
    def get_evolution_parameters(self, epoch: int) -> Dict[str, Any]:
        """Get evolution parameters based on current phase."""
        if epoch <= self.phase_switch_epoch:
            # Phase 1: Aggressive exploration
            return {
                'mutation_rate': config.PHASE1_MUTATION_RATE,
                'crossover_rate': config.PHASE1_CROSSOVER_RATE,
                'elite_size': config.PHASE1_ELITE_SIZE,
                'population_size': config.EVOLUTION_POPULATION_SIZE
            }
        else:
            # Phase 2: Optimization
            return {
                'mutation_rate': config.PHASE2_MUTATION_RATE,
                'crossover_rate': config.PHASE2_CROSSOVER_RATE,
                'elite_size': config.PHASE2_ELITE_SIZE,
                'population_size': config.EVOLUTION_POPULATION_SIZE
            }
    
    def compute_anti_convergence_penalty(self, butcher_table: ButcherTable) -> float:
        """Compute penalty for being too similar to known methods (especially RK4)."""
        if butcher_table is None:
            return 0.0
        
        from src.core.butcher_tables import get_all_baseline_tables
        baseline_tables = get_all_baseline_tables()
        
        penalties = []
        
        # Special penalty for RK4 similarity
        rk4 = baseline_tables.get('rk4')
        if rk4 and len(rk4.b) == len(butcher_table.b):
            rk4_similarity = 1.0 - self.compute_diversity_score(butcher_table, rk4)
            if rk4_similarity > 0.8:  # Very similar to RK4
                penalties.append(config.ANTI_RK4_PENALTY * rk4_similarity)
        
        # General penalty for similarity to any known method
        for name, baseline in baseline_tables.items():
            if len(baseline.b) == len(butcher_table.b):
                similarity = 1.0 - self.compute_diversity_score(butcher_table, baseline)
                if similarity > 0.7:  # Very similar to any known method
                    penalties.append(config.KNOWN_METHOD_PENALTY * similarity)
        
        return sum(penalties)
    
    def enhanced_fitness_function(self, butcher_table: ButcherTable, base_metrics: Dict[str, float], epoch: int) -> float:
        """Enhanced fitness function with novelty rewards and anti-convergence penalties."""
        if butcher_table is None:
            return 0.0
        
        # Base performance score
        accuracy_score = base_metrics.get('accuracy_score', 0.0)
        efficiency_score = base_metrics.get('efficiency_score', 0.0)
        stability_score = base_metrics.get('stability_score', 0.0)
        
        # Weighted performance score
        performance_score = (
            config.ACCURACY_WEIGHT * accuracy_score +
            config.EFFICIENCY_WEIGHT * efficiency_score +
            config.STABILITY_WEIGHT * stability_score
        )
        
        # Novelty reward
        novelty_reward = self.metrics_calculator._compute_novelty_reward(butcher_table)
        novelty_score = config.NOVELTY_WEIGHT * novelty_reward
        
        # Constraint rewards
        c_reward = config.C_MATRIX_REWARD_WEIGHT * self.metrics_calculator._compute_c_matrix_constraint_reward(butcher_table.c)
        b_reward = config.B_MATRIX_SUM_REWARD_WEIGHT * self.metrics_calculator._compute_b_matrix_sum_constraint_reward(butcher_table.b)
        constraint_score = c_reward + b_reward
        
        # Anti-convergence penalty
        convergence_penalty = self.compute_anti_convergence_penalty(butcher_table)
        
        # Exploration bonus (phase 1 only)
        exploration_bonus = 0.0
        if epoch <= self.phase_switch_epoch:
            # Reward coefficient diversity
            coeff_diversity = np.std(np.concatenate([butcher_table.A.flatten(), butcher_table.b, butcher_table.c]))
            exploration_bonus = config.EXPLORATION_BONUS_WEIGHT * min(1.0, coeff_diversity)
        
        # Total score
        total_score = (
            performance_score + 
            novelty_score + 
            constraint_score + 
            exploration_bonus - 
            convergence_penalty
        )
        
        return max(0.0, total_score)  # Ensure non-negative
    
    def run_enhanced_training(self, n_epochs: int = None) -> Dict[str, Any]:
        """Run enhanced two-phase training."""
        if n_epochs is None:
            n_epochs = config.N_EPOCHS
        
        print(f"Starting enhanced two-phase training for {n_epochs} epochs...")
        print(f"Phase 1 (Exploration): Epochs 1-{config.PHASE_SWITCH_EPOCH}")
        print(f"Phase 2 (Optimization): Epochs {config.PHASE_SWITCH_EPOCH + 1}-{n_epochs}")
        
        best_overall_score = 0.0
        best_overall_table = None
        training_history = []
        
        for epoch in range(1, n_epochs + 1):
            # Check for phase switch
            if epoch == config.PHASE_SWITCH_EPOCH + 1:
                self.current_phase = 2
                print(f"\n{'='*70}")
                print(f"PHASE SWITCH: Switching to optimization phase at epoch {epoch}")
                print(f"{'='*70}")
            
            # Get evolution parameters for current phase
            evo_params = self.get_evolution_parameters(epoch)
            
            print(f"\nEpoch {epoch}/{n_epochs} (Phase {self.current_phase}) - {epoch/n_epochs*100:.1f}% Complete")
            print(f"  Evolution params: mutation={evo_params['mutation_rate']:.2f}, "
                  f"crossover={evo_params['crossover_rate']:.2f}, elite={evo_params['elite_size']}")
            
            # Show progress every 10 epochs
            if epoch % 10 == 0:
                print(f"  🚀 Training Progress: {epoch}/{n_epochs} epochs completed")
            
            # Generate candidates
            candidates = []
            for i in range(config.N_CANDIDATES_PER_BATCH):
                # Generate candidate using current evolution parameters
                if hasattr(self, 'generator') and self.generator is not None:
                    candidate = self.generator.generate_candidate(
                        stages=config.DEFAULT_STAGES,
                        mutation_rate=evo_params['mutation_rate']
                    )
                else:
                    # Fallback to random generation
                    from src.core.butcher_tables import ButcherTableGenerator
                    generator = ButcherTableGenerator(seed=RANDOM_SEED + epoch + i)
                    candidate = generator.generate_random_explicit(config.DEFAULT_STAGES)
                
                # Evaluate candidate
                try:
                    # Get a training batch for evaluation
                    train_batch = self.dataset.get_batch(config.BATCH_SIZE)
                    
                    metrics = self.metrics_calculator.evaluate_on_ode_batch(
                        candidate, train_batch, use_varied_steps=True
                    )
                    
                    if metrics is not None:
                        enhanced_score = self.enhanced_fitness_function(candidate, metrics.__dict__, epoch)
                        candidates.append((candidate, enhanced_score))
                        
                except Exception as e:
                    print(f"    Error evaluating candidate {i+1}: {e}")
                    continue
            
            if not candidates:
                print(f"  No valid candidates generated in epoch {epoch}")
                continue
            
            # Sort candidates by score
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Update best overall
            if candidates[0][1] > best_overall_score:
                best_overall_score = candidates[0][1]
                best_overall_table = candidates[0][0]
            
            # Update diversity archive (Phase 1 only)
            if self.current_phase == 1:
                self.update_diversity_archive(candidates)
            
            # Log epoch results
            epoch_stats = {
                'epoch': epoch,
                'phase': self.current_phase,
                'n_valid_candidates': len(candidates),
                'best_score': candidates[0][1],
                'mean_score': np.mean([score for _, score in candidates]),
                'diversity_archive_size': len(self.diversity_archive),
                'evolution_params': evo_params
            }
            training_history.append(epoch_stats)
            
            print(f"  Valid candidates: {len(candidates)}")
            print(f"  Best score: {candidates[0][1]:.4f}")
            print(f"  Mean score: {epoch_stats['mean_score']:.4f}")
            
            # Analyze best candidate
            best_table = candidates[0][0]
            if best_table is not None:
                # Check novelty vs RK4
                from src.core.butcher_tables import get_rk4
                rk4 = get_rk4()
                diversity_from_rk4 = self.compute_diversity_score(best_table, rk4)
                print(f"  Diversity from RK4: {diversity_from_rk4:.4f}")
                
                # Check constraint satisfaction
                c_in_range = np.all((best_table.c >= -0.5) & (best_table.c <= 1.5))
                b_sum = np.sum(best_table.b)
                print(f"  C constraints OK: {c_in_range}, B sum: {b_sum:.6f}")
            
            # Save checkpoint periodically
            if epoch % config.EVALUATION_FREQUENCY == 0:
                self.save_checkpoint(epoch, best_overall_table, best_overall_score, training_history)
        
        # Final evaluation
        final_results = {
            'best_table': best_overall_table,
            'best_score': best_overall_score,
            'training_history': training_history,
            'diversity_archive': self.diversity_archive,
            'final_phase': self.current_phase
        }
        
        return final_results
    
    def save_checkpoint(self, epoch: int, best_table: ButcherTable, best_score: float, history: List[Dict]) -> None:
        """Save training checkpoint."""
        checkpoint_data = {
            'epoch': epoch,
            'phase': self.current_phase,
            'best_score': best_score,
            'best_table': best_table.to_dict() if best_table else None,
            'training_history': history,
            'diversity_archive': [(table.to_dict(), score) for table, score in self.diversity_archive],
            'config': config.__dict__
        }
        
        os.makedirs(config.CHECKPOINTS_DIR, exist_ok=True)
        checkpoint_path = os.path.join(config.CHECKPOINTS_DIR, f'checkpoint_epoch_{epoch}.json')
        
        import json
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
        
        print(f"  Checkpoint saved: {checkpoint_path}")

def main_4stage_novelty_2():
    """Main training function for enhanced 4-stage novelty search model."""
    
    print("="*70)
    print("ENHANCED TRAINING: 4-STAGE BUTCHER TABLE - NOVELTY SEARCH 2.0")
    print("="*70)
    print(f"Random Seed: {RANDOM_SEED}")
    print(f"Configuration:")
    print(f"  Stages: {config.MIN_STAGES}-{config.MAX_STAGES} (fixed at {config.DEFAULT_STAGES})")
    print(f"  Accuracy Weight: {config.ACCURACY_WEIGHT}")
    print(f"  Efficiency Weight: {config.EFFICIENCY_WEIGHT}")
    print(f"  Stability Weight: {config.STABILITY_WEIGHT}")
    print(f"  NOVELTY Weight: {config.NOVELTY_WEIGHT} (🚀 ENHANCED!)")
    print(f"  Constraint Weights: {config.C_MATRIX_REWARD_WEIGHT + config.B_MATRIX_SUM_REWARD_WEIGHT}")
    print(f"  Anti-RK4 Penalty: {config.ANTI_RK4_PENALTY}")
    print(f"  Known Method Penalty: {config.KNOWN_METHOD_PENALTY}")
    print(f"  Two-Phase Training:")
    print(f"    Phase 1 (Exploration): Epochs 1-{config.PHASE_SWITCH_EPOCH}")
    print(f"      Mutation Rate: {config.PHASE1_MUTATION_RATE}")
    print(f"      Crossover Rate: {config.PHASE1_CROSSOVER_RATE}")
    print(f"      Elite Size: {config.PHASE1_ELITE_SIZE}")
    print(f"    Phase 2 (Optimization): Epochs {config.PHASE_SWITCH_EPOCH + 1}-{config.N_EPOCHS}")
    print(f"      Mutation Rate: {config.PHASE2_MUTATION_RATE}")
    print(f"      Crossover Rate: {config.PHASE2_CROSSOVER_RATE}")
    print(f"      Elite Size: {config.PHASE2_ELITE_SIZE}")
    print(f"  Population Size: {config.EVOLUTION_POPULATION_SIZE}")
    print(f"  Diversity Preservation: Top {config.DIVERSITY_PRESERVATION_SIZE}")
    
    # CUDA status
    if torch.cuda.is_available():
        print(f"  CUDA: ⚠️  Available but disabled - {torch.cuda.get_device_name(0)}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print(f"  Reason: Using CPU for stability and reproducibility")
    else:
        print(f"  CUDA: ❌ Not available - Using CPU")
    
    print("="*70)
    
    # Create trial-specific configuration
    trial_id = f"4stage_novelty_2_{RANDOM_SEED}"
    
    # Initialize enhanced training pipeline
    pipeline = EnhancedNoveltyTrainingPipeline(
        config_obj=config,
        trial_id=trial_id,
        complexity_level=config.COMPLEXITY_LEVEL,
        use_cuda=False  # Use CPU for stability
    )
    
    # Initialize training with fresh dataset
    print("Initializing enhanced training pipeline...")
    pipeline.initialize_training(force_regenerate_dataset=True)
    
    # Run enhanced training
    print(f"\nStarting enhanced two-phase novelty search training...")
    start_time = time.time()
    
    try:
        results = pipeline.run_enhanced_training(n_epochs=config.N_EPOCHS)
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        results = {'best_table': pipeline.best_table, 'best_score': 0.0, 'training_history': []}
    except Exception as e:
        print(f"\nTraining error: {e}")
        print("Attempting to save current progress...")
        results = {'best_table': pipeline.best_table, 'best_score': 0.0, 'training_history': []}
    
    training_time = time.time() - start_time
    
    # Print final results
    if results and results.get('best_table'):
        print("\n" + "="*70)
        print("ENHANCED 4-STAGE NOVELTY SEARCH 2.0 - FINAL RESULTS")
        print("="*70)
        
        best_table = results['best_table']
        print(f"Training completed in {training_time:.2f} seconds")
        print(f"Final phase reached: {results.get('final_phase', 'Unknown')}")
        print(f"Diversity archive size: {len(results.get('diversity_archive', []))}")
        print(f"Best overall score: {results['best_score']:.4f}")
        
        print(f"\nBest Butcher Table:")
        print(best_table)
        
        # Novelty analysis
        from src.core.butcher_tables import get_all_baseline_tables
        baseline_tables = get_all_baseline_tables()
        rk4 = baseline_tables['rk4']
        
        # Compute differences from RK4
        c_diff = np.mean(np.abs(best_table.c - rk4.c))
        b_diff = np.mean(np.abs(best_table.b - rk4.b))
        a_diff = np.mean(np.abs(best_table.A - rk4.A))
        overall_diff = (c_diff + b_diff + a_diff) / 3
        
        print(f"\nNovelty Analysis vs RK4:")
        print(f"  C vector difference: {c_diff:.4f}")
        print(f"  B vector difference: {b_diff:.4f}")
        print(f"  A matrix difference: {a_diff:.4f}")
        print(f"  Overall difference: {overall_diff:.4f}")
        print(f"  Novelty threshold: {config.NOVELTY_THRESHOLD}")
        print(f"  Novel (above threshold): {'✅ YES' if overall_diff > config.NOVELTY_THRESHOLD else '❌ NO'}")
        
        # Save final results
        os.makedirs(config.RESULTS_DIR, exist_ok=True)
        final_results_path = os.path.join(config.RESULTS_DIR, 'best_butcher_table.json')
        
        final_data = {
            'butcher_table': best_table.to_dict(),
            'best_score': results['best_score'],
            'training_time': training_time,
            'novelty_analysis': {
                'c_diff_from_rk4': c_diff,
                'b_diff_from_rk4': b_diff,
                'a_diff_from_rk4': a_diff,
                'overall_diff_from_rk4': overall_diff,
                'is_novel': overall_diff > config.NOVELTY_THRESHOLD
            },
             'diversity_archive': [
                 (table.to_dict() if isinstance(table, ButcherTable) else table, score) 
                 for table, score in results.get('diversity_archive', [])
             ],
            'training_history': results.get('training_history', []),
            'config': config.__dict__
        }
        
        import json
        with open(final_results_path, 'w') as f:
            json.dump(final_data, f, indent=2, default=str)
        
        print(f"\nResults saved to: {final_results_path}")
        
        # Print diversity archive summary
        if results.get('diversity_archive'):
            print(f"\nDiversity Archive Summary:")
            for i, (table, score) in enumerate(results['diversity_archive']):
                if isinstance(table, ButcherTable):
                    table_obj = table
                else:
                    table_obj = ButcherTable.from_dict(table)
                diff_from_rk4 = pipeline.compute_diversity_score(table_obj, rk4)
                print(f"  Solution {i+1}: Score={score:.4f}, RK4-diff={diff_from_rk4:.4f}")
    
    else:
        print("\n❌ Training failed to produce valid results")

if __name__ == "__main__":
    # Required for Windows multiprocessing support
    import multiprocessing
    multiprocessing.freeze_support()
    
    main_4stage_novelty_2()

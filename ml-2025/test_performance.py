#!/usr/bin/env python3
"""
Performance Test Script.

This script tests the performance improvements made to the training pipeline.
"""

import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from configs.base import config
from src.core.performance_monitor import PerformanceMonitor
from src.training.train import TrainingPipeline

def test_performance_improvements():
    """Test the performance improvements."""
    
    print("Testing Performance Improvements")
    print("=" * 50)
    
    # Create performance monitor
    monitor = PerformanceMonitor(sampling_interval=0.5)
    monitor.start_monitoring()
    
    try:
        # Initialize training pipeline with smaller dataset for testing
        config.N_ODES = 100  # Smaller dataset for testing
        config.BATCH_SIZE = 50
        config.N_CANDIDATES_PER_BATCH = 25
        config.N_EPOCHS = 5  # Just a few epochs for testing
        
        print(f"Configuration:")
        print(f"  Dataset size: {config.N_ODES}")
        print(f"  Batch size: {config.BATCH_SIZE}")
        print(f"  Candidates per batch: {config.N_CANDIDATES_PER_BATCH}")
        print(f"  Epochs: {config.N_EPOCHS}")
        print()
        
        # Initialize pipeline
        print("Initializing training pipeline...")
        pipeline = TrainingPipeline(trial_id="performance_test", complexity_level=1)
        
        # Initialize training
        print("Initializing training...")
        pipeline.initialize_training(force_regenerate_dataset=True)
        
        # Run a few epochs
        print("Running training epochs...")
        for epoch in range(config.N_EPOCHS):
            print(f"\nEpoch {epoch + 1}/{config.N_EPOCHS}")
            start_time = time.time()
            
            epoch_results = pipeline.train_epoch(use_evolution=False)
            
            epoch_time = time.time() - start_time
            print(f"Epoch completed in {epoch_time:.2f} seconds")
            print(f"  Valid candidates: {epoch_results['n_valid_candidates']}")
            print(f"  Best score: {epoch_results['best_score']:.4f}")
            print(f"  Mean score: {epoch_results['mean_score']:.4f}")
        
        print("\nPerformance test completed!")
        
    except Exception as e:
        print(f"Error during performance test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop monitoring and print report
        monitor.stop_monitoring()
        monitor.print_performance_report()

if __name__ == "__main__":
    test_performance_improvements()

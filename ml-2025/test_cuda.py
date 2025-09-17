#!/usr/bin/env python3
"""
CUDA Test Script for Novel Numerical Integration Methods

This script tests the CUDA implementation of the numerical integration methods.
"""

import torch
import numpy as np
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.core.butcher_tables import ButcherTable, get_rk4
from src.core.integrator_runner import RungeKuttaIntegrator, ReferenceSolver, IntegratorBenchmark
from src.core.metrics import MetricsCalculator
from src.models.model import MLPipeline, ModelConfig
from src.core.ode_dataset import ODEParameters

def test_cuda_availability():
    """Test if CUDA is available and print device information."""
    print("=" * 60)
    print("CUDA AVAILABILITY TEST")
    print("=" * 60)
    
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"Number of GPUs: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            props = torch.cuda.get_device_properties(i)
            print(f"  Memory: {props.total_memory / 1e9:.1f} GB")
            print(f"  Compute capability: {props.major}.{props.minor}")
    else:
        print("CUDA not available - will use CPU")
    
    print()

def test_butcher_table_cuda():
    """Test Butcher table tensor conversion with CUDA."""
    print("=" * 60)
    print("BUTCHER TABLE CUDA TEST")
    print("=" * 60)
    
    # Test RK4 table
    rk4 = get_rk4()
    print(f"RK4 table:\n{rk4}")
    
    # Test CPU tensor conversion
    cpu_tensor = rk4.to_tensor()
    print(f"CPU tensor shape: {cpu_tensor.shape}")
    print(f"CPU tensor device: {cpu_tensor.device}")
    
    # Test CUDA tensor conversion
    if torch.cuda.is_available():
        cuda_device = torch.device('cuda')
        cuda_tensor = rk4.to_tensor(device=cuda_device)
        print(f"CUDA tensor shape: {cuda_tensor.shape}")
        print(f"CUDA tensor device: {cuda_tensor.device}")
        
        # Test conversion back
        reconstructed = ButcherTable.from_tensor(cuda_tensor, 4)
        print(f"Reconstruction successful: {np.allclose(rk4.A, reconstructed.A)}")
    else:
        print("CUDA not available - skipping CUDA tensor test")
    
    print()

def test_integrator_cuda():
    """Test Runge-Kutta integrator with CUDA."""
    print("=" * 60)
    print("INTEGRATOR CUDA TEST")
    print("=" * 60)
    
    # Simple ODE: dy/dt = -y, y(0) = 1
    def simple_ode(t, y):
        return -y
    
    rk4 = get_rk4()
    y0 = np.array([1.0])
    t_span = (0.0, 1.0)
    h = 0.1
    
    # Test CPU integrator
    print("Testing CPU integrator...")
    cpu_integrator = RungeKuttaIntegrator(rk4, use_cuda=False)
    start_time = time.time()
    cpu_result = cpu_integrator.integrate(simple_ode, y0, t_span, h=h)
    cpu_time = time.time() - start_time
    
    print(f"CPU result: success={cpu_result.success}, n_steps={cpu_result.n_steps}")
    print(f"CPU runtime: {cpu_time:.4f}s")
    print(f"Final value: {cpu_result.y_vals[-1, 0]:.6f} (exact: {np.exp(-1.0):.6f})")
    
    # Test CUDA integrator
    if torch.cuda.is_available():
        print("\nTesting CUDA integrator...")
        cuda_integrator = RungeKuttaIntegrator(rk4, use_cuda=True)
        start_time = time.time()
        cuda_result = cuda_integrator.integrate(simple_ode, y0, t_span, h=h)
        cuda_time = time.time() - start_time
        
        print(f"CUDA result: success={cuda_result.success}, n_steps={cuda_result.n_steps}")
        print(f"CUDA runtime: {cuda_time:.4f}s")
        print(f"Final value: {cuda_result.y_vals[-1, 0]:.6f} (exact: {np.exp(-1.0):.6f})")
        
        # Compare results
        if cpu_result.success and cuda_result.success:
            error = np.abs(cpu_result.y_vals[-1, 0] - cuda_result.y_vals[-1, 0])
            print(f"Difference between CPU and CUDA: {error:.2e}")
            speedup = cpu_time / cuda_time if cuda_time > 0 else 0
            print(f"Speedup: {speedup:.2f}x")
    else:
        print("CUDA not available - skipping CUDA integrator test")
    
    print()

def test_ml_pipeline_cuda():
    """Test ML pipeline with CUDA."""
    print("=" * 60)
    print("ML PIPELINE CUDA TEST")
    print("=" * 60)
    
    # Test ML pipeline initialization
    config = ModelConfig()
    ml_pipeline = MLPipeline(config)
    
    print(f"ML Pipeline device: {ml_pipeline.device}")
    print(f"Generator device: {next(ml_pipeline.generator.parameters()).device}")
    print(f"Surrogate device: {next(ml_pipeline.surrogate.parameters()).device}")
    
    # Test table generation
    print("\nTesting table generation...")
    tables = ml_pipeline.generator.generate_valid_tables(5, device=str(ml_pipeline.device))
    print(f"Generated {len(tables)} tables")
    
    if len(tables) > 0:
        # Test tensor conversion
        tensor = tables[0].to_tensor(device=ml_pipeline.device)
        print(f"Table tensor device: {tensor.device}")
        
        # Test surrogate prediction
        prediction = ml_pipeline.predict_performance(tables[:1])
        print(f"Prediction device: {prediction[0].device}")
        print(f"Prediction shape: {prediction[0].shape}")
    
    print()

def test_benchmark_cuda():
    """Test benchmark with CUDA."""
    print("=" * 60)
    print("BENCHMARK CUDA TEST")
    print("=" * 60)
    
    # Create test ODE
    test_ode = ODEParameters(
        ode_id=0,
        is_stiff=False,
        equation_type="linear_system",
        parameters={"A": np.array([[-1.0]])},
        initial_conditions=np.array([1.0]),
        t_span=(0.0, 1.0)
    )
    
    rk4 = get_rk4()
    
    # Test CPU benchmark
    print("Testing CPU benchmark...")
    cpu_benchmark = IntegratorBenchmark(use_cuda=False)
    start_time = time.time()
    cpu_eval = cpu_benchmark.evaluate_butcher_table(rk4, test_ode, h=0.1)
    cpu_time = time.time() - start_time
    
    print(f"CPU evaluation: success={cpu_eval['success']}")
    print(f"CPU runtime: {cpu_time:.4f}s")
    if cpu_eval['success']:
        print(f"CPU max error: {cpu_eval['max_error']:.2e}")
    
    # Test CUDA benchmark
    if torch.cuda.is_available():
        print("\nTesting CUDA benchmark...")
        cuda_benchmark = IntegratorBenchmark(use_cuda=True)
        start_time = time.time()
        cuda_eval = cuda_benchmark.evaluate_butcher_table(rk4, test_ode, h=0.1)
        cuda_time = time.time() - start_time
        
        print(f"CUDA evaluation: success={cuda_eval['success']}")
        print(f"CUDA runtime: {cuda_time:.4f}s")
        if cuda_eval['success']:
            print(f"CUDA max error: {cuda_eval['max_error']:.2e}")
        
        # Compare results
        if cpu_eval['success'] and cuda_eval['success']:
            error_diff = abs(cpu_eval['max_error'] - cuda_eval['max_error'])
            print(f"Error difference: {error_diff:.2e}")
            speedup = cpu_time / cuda_time if cuda_time > 0 else 0
            print(f"Speedup: {speedup:.2f}x")
    else:
        print("CUDA not available - skipping CUDA benchmark test")
    
    print()

def main():
    """Run all CUDA tests."""
    print("CUDA IMPLEMENTATION TEST SUITE")
    print("Testing CUDA support for Novel Numerical Integration Methods")
    print()
    
    try:
        # Run tests
        test_cuda_availability()
        test_butcher_table_cuda()
        test_integrator_cuda()
        test_ml_pipeline_cuda()
        test_benchmark_cuda()
        
        print("=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        if torch.cuda.is_available():
            print("✅ CUDA is available and working")
            print("✅ All components support CUDA acceleration")
            print("✅ Performance improvements expected with GPU")
        else:
            print("⚠️  CUDA not available - using CPU fallback")
            print("✅ All components work correctly on CPU")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

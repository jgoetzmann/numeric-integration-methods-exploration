"""
Quick Test Script - Verifies the test suite works before running full test
"""

import os
import sys
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.core.butcher_tables import ButcherTable, get_rk4
        print("✓ butcher_tables imported successfully")
        
        from src.core.integrator_runner import IntegratorBenchmark, IntegrationResult
        print("✓ integrator_runner imported successfully")
        
        from src.core.ode_dataset import ODEParameters, ODEDataset
        print("✓ ode_dataset imported successfully")
        
        from src.core.metrics import PerformanceMetrics, MetricsCalculator
        print("✓ metrics imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality with a small dataset."""
    print("\nTesting basic functionality...")
    
    try:
        from butcher_tables import get_rk4
        from integrator_runner import IntegratorBenchmark
        from ode_dataset import ODEDataset
        
        # Create a small test dataset
        dataset_generator = ODEDataset()
        test_odes = dataset_generator.generate_nonstiff_odes(5, 0.0, 0.1)
        
        # Test RK4
        rk4 = get_rk4()
        benchmark = IntegratorBenchmark()
        
        results = []
        for ode in test_odes:
            result = benchmark.evaluate_butcher_table(rk4, ode, h=0.01)
            results.append(result['success'])
        
        success_rate = sum(results) / len(results)
        print(f"✓ Basic test completed - Success rate: {success_rate:.2f}")
        
        return success_rate > 0.5
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

def test_optimal_table_loading():
    """Test loading the optimal Butcher table."""
    print("\nTesting optimal table loading...")
    
    try:
        # Try to load from run_1 first
        run1_path = os.path.join(os.path.dirname(__file__), '..', '..', 'experiments', 'run_1_balanced_weights', 'best_butcher_table.json')
        optimal_path = os.path.join(os.path.dirname(__file__), '..', '..', 'OPTIMAL_BUTCHER_TABLE.json')
        
        table_path = None
        if os.path.exists(run1_path):
            table_path = run1_path
            print("✓ Found run_1 optimal table")
        elif os.path.exists(optimal_path):
            table_path = optimal_path
            print("✓ Found global optimal table")
        else:
            print("✗ No optimal table found")
            return False
        
        # Load and test the table
        import json
        with open(table_path, 'r') as f:
            data = json.load(f)
        
        if 'butcher_table' in data:
            table_data = data['butcher_table']
        else:
            table_data = data
            
        from butcher_tables import ButcherTable
        table = ButcherTable(
            A=np.array(table_data['A']),
            b=np.array(table_data['b']),
            c=np.array(table_data['c'])
        )
        
        print(f"✓ Optimal table loaded - Stages: {len(table.b)}, Order: {table.consistency_order}")
        return True
        
    except Exception as e:
        print(f"✗ Optimal table loading failed: {e}")
        return False

def main():
    """Run quick tests."""
    print("QUICK TEST SUITE")
    print("=" * 30)
    
    tests_passed = 0
    total_tests = 3
    
    # Test imports
    if test_imports():
        tests_passed += 1
    
    # Test optimal table loading
    if test_optimal_table_loading():
        tests_passed += 1
    
    # Test basic functionality
    if test_basic_functionality():
        tests_passed += 1
    
    print(f"\nQuick test results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! Ready to run comprehensive test.")
        return True
    else:
        print("✗ Some tests failed. Please fix issues before running comprehensive test.")
        return False

if __name__ == "__main__":
    main()



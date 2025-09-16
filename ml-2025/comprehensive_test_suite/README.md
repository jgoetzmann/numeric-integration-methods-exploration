# Comprehensive ODE Testing Suite

This directory contains a comprehensive testing suite for evaluating the optimal Butcher table discovered in run_1 against various classical numerical integration methods.

## Overview

The testing suite performs extensive evaluation on 10,000 ODEs (both stiff and non-stiff) and compares the optimal method against:
- RK4 (Classic 4th order Runge-Kutta)
- RK45 (Dormand-Prince)
- Gauss-Legendre methods (2 and 3 stages)
- Additional methods via extended comparison

## Directory Structure

```
comprehensive_test_suite/
├── scripts/                    # Test scripts
│   ├── comprehensive_ode_test.py      # Main comprehensive test
│   ├── extended_comparison.py         # Additional method comparisons
│   ├── performance_analyzer.py        # Detailed analysis and plots
│   └── run_comprehensive_test.py      # Main runner script
├── results/                    # Test results and reports
├── plots/                      # Generated visualization plots
├── data/                       # Test datasets
└── README.md                   # This file
```

## Quick Start

### Run Complete Test Suite

```bash
cd comprehensive_test_suite/scripts
python run_comprehensive_test.py
```

### Run with Custom Parameters

```bash
python run_comprehensive_test.py --odes 5000 --processes 4
```

### Run Individual Components

```bash
# Main comprehensive test only
python comprehensive_ode_test.py

# Extended comparison only
python extended_comparison.py

# Performance analysis only (requires results from main test)
python performance_analyzer.py
```

## Test Configuration

The test suite can be configured via command-line arguments:

- `--odes N`: Number of ODEs to test (default: 10000)
- `--processes N`: Number of parallel processes (default: auto)
- `--skip-main`: Skip main comprehensive test
- `--skip-extended`: Skip extended comparison
- `--skip-analysis`: Skip performance analysis

## Test Components

### 1. Main Comprehensive Test (`comprehensive_ode_test.py`)

- Tests the optimal Butcher table from run_1
- Compares against baseline methods (RK4, RK45, Gauss-Legendre)
- Evaluates on 10,000 ODEs (3,000 stiff + 7,000 non-stiff)
- Uses parallel processing for efficiency
- Generates comprehensive metrics and comparisons

### 2. Extended Comparison (`extended_comparison.py`)

- Adds additional numerical methods for comparison:
  - Scipy's built-in solvers (RK45, DOP853, Radau, BDF)
  - Classical methods (Euler, Heun, Midpoint)
- Provides broader method coverage
- Smaller dataset for faster execution

### 3. Performance Analysis (`performance_analyzer.py`)

- Detailed statistical analysis of results
- Comprehensive visualization plots
- Performance rankings and comparisons
- Generates detailed reports and CSV data

## Output Files

### Results Directory

- `comprehensive_test_results.json`: Main test results with metrics
- `extended_comparison_results.json`: Extended method comparisons
- `performance_report.txt`: Detailed performance analysis
- `performance_data.csv`: CSV data for further analysis
- `test_summary.txt`: Overall test suite summary

### Plots Directory

- `comprehensive_comparison.png`: Main comparison visualizations
- `radar_comparison.png`: Radar chart of method performance
- `detailed_performance_analysis.png`: Detailed analysis plots

## Performance Metrics

The test suite evaluates methods on multiple criteria:

### Accuracy Metrics
- Maximum error across all test problems
- L2 error norm
- Mean error and 95th percentile
- Success rate on test problems

### Efficiency Metrics
- Steps per second
- Total runtime
- Normalized efficiency score

### Stability Metrics
- Performance on stiff problems
- Success rate on stiff ODEs
- Stability score

### Composite Score
- Weighted combination of accuracy, efficiency, and stability
- Primary ranking metric

## Expected Results

Based on previous training runs, the optimal Butcher table from run_1 is expected to show:

- **High efficiency**: Competitive or superior to classical methods
- **Good stability**: Robust performance on stiff problems
- **Balanced accuracy**: Good accuracy across problem types
- **Overall superiority**: Best composite score across all metrics

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the correct directory and all dependencies are installed
2. **Memory Issues**: Reduce the number of ODEs or processes for systems with limited memory
3. **Long Runtime**: The full test can take 30-60 minutes; use smaller datasets for faster testing

### Dependencies

Required Python packages:
- numpy
- scipy
- matplotlib
- seaborn
- tqdm
- pandas

### System Requirements

- **RAM**: 8GB+ recommended for full test (10,000 ODEs)
- **CPU**: Multi-core processor recommended for parallel processing
- **Storage**: ~1GB for results and plots

## Interpretation Guide

### Understanding Results

1. **Success Rate**: Percentage of problems solved successfully
2. **Composite Score**: Overall performance (0-1, higher is better)
3. **Efficiency Score**: Computational speed (normalized)
4. **Stability Score**: Performance on difficult stiff problems

### Key Comparisons

- **Optimal vs RK4**: Efficiency and accuracy comparison
- **Optimal vs RK45**: Adaptive vs fixed-step comparison
- **Optimal vs Gauss-Legendre**: Explicit vs implicit comparison

## Advanced Usage

### Custom Test Datasets

Modify the test configuration to use custom ODE datasets:

```python
# In comprehensive_ode_test.py
config = TestConfig(
    n_odes=5000,
    n_stiff_odes=2000,
    n_nonstiff_odes=3000,
    # ... other parameters
)
```

### Custom Method Comparisons

Add new methods by extending the baseline methods dictionary:

```python
# In comprehensive_ode_test.py
self.baseline_methods['custom_method'] = your_butcher_table
```

## Contributing

To add new test methods or improve the test suite:

1. Extend the baseline methods in `comprehensive_ode_test.py`
2. Add new comparison methods in `extended_comparison.py`
3. Enhance analysis capabilities in `performance_analyzer.py`

## License

This test suite is part of the Novel Numerical Integration Methods project.

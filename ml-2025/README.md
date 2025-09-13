# Novel Numerical Integration Methods

A machine learning system for discovering new Runge-Kutta integration schemes (Butcher tables) that can outperform classical methods in terms of accuracy, efficiency, and stability.

## Project Overview

This project implements a comprehensive framework for automatically generating and evaluating novel numerical integration methods using machine learning and evolutionary algorithms. The system discovers new Butcher tables that can compete with or outperform established baselines like RK4, RK45, and implicit methods.

## Features

- **Comprehensive ODE Dataset**: 10,000 static ODEs (mix of stiff and non-stiff problems)
- **Butcher Table Representation**: Flexible representation and validation of Runge-Kutta schemes
- **Multiple ML Approaches**: Neural network generators and evolutionary algorithms
- **Surrogate Evaluation**: Fast performance prediction using neural networks
- **Comprehensive Metrics**: Accuracy, efficiency, stability, and composite scoring
- **Baseline Comparisons**: Evaluation against classical methods (RK4, RK45, Gauss-Legendre)
- **Database Storage**: SQLite database for tracking all experiments and results
- **Rich Visualizations**: Interactive plots and comprehensive reporting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Novel-Numerical-Integration-Methods.git
cd Novel-Numerical-Integration-Methods
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Training
```python
from train import TrainingPipeline

# Initialize and run training
pipeline = TrainingPipeline()
pipeline.initialize_training()
results = pipeline.run_training(n_epochs=100)
```

### Generate and Evaluate Butcher Tables
```python
from butcher_tables import ButcherTableGenerator
from integrator_runner import IntegratorBenchmark, ReferenceSolver
from metrics import MetricsCalculator

# Generate random Butcher table
generator = ButcherTableGenerator()
table = generator.generate_random_explicit(stages=4)

# Evaluate performance
ref_solver = ReferenceSolver()
benchmark = IntegratorBenchmark(ref_solver)
metrics_calc = MetricsCalculator(benchmark)

# Load ODE dataset
from ode_dataset import ODEDataset
dataset = ODEDataset()
dataset.generate_dataset()

# Evaluate on batch of ODEs
batch = dataset.get_batch(100)
metrics = metrics_calc.evaluate_on_ode_batch(table, batch)
print(f"Composite Score: {metrics.composite_score:.4f}")
```

### Visualize Results
```python
from visualization import ButcherTableVisualizer, ReportGenerator

# Visualize a Butcher table
visualizer = ButcherTableVisualizer()
visualizer.plot_butcher_table(table)

# Generate comprehensive report
report_gen = ReportGenerator()
report_gen.generate_experiment_report("results/integrator_results.db")
```

## Project Structure

```
├── config.py                 # Configuration settings
├── ode_dataset.py           # ODE generation and management
├── butcher_tables.py        # Butcher table representation
├── integrator_runner.py     # Integration and benchmarking
├── metrics.py              # Performance metrics calculation
├── model.py                # ML models (generator, surrogate)
├── train.py                # Training pipeline
├── database.py             # Database storage and logging
├── visualization.py        # Plotting and reporting
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Key Components

### 1. ODE Dataset (`ode_dataset.py`)
- Generates 10,000 diverse ODEs (linear systems, Van der Pol, Lotka-Volterra, etc.)
- Mix of stiff and non-stiff problems
- Batching functionality for training
- Pre-computed reference solutions

### 2. Butcher Table Representation (`butcher_tables.py`)
- Flexible representation of RK schemes
- Validation and consistency checking
- Order calculation
- Tensor conversion for ML models
- Classic baseline methods included

### 3. Integration Engine (`integrator_runner.py`)
- Implements RK integration using Butcher tables
- High-precision reference solver
- Comprehensive benchmarking system
- Error computation and analysis

### 4. Metrics System (`metrics.py`)
- Multi-dimensional evaluation (accuracy, efficiency, stability)
- Composite scoring with configurable weights
- Baseline comparison framework
- Statistical analysis tools

### 5. ML Models (`model.py`)
- Neural network generator for creating Butcher tables
- Surrogate evaluator for fast performance prediction
- Evolutionary algorithm alternative
- Training and optimization utilities

### 6. Training Pipeline (`train.py`)
- Complete optimization loop
- Batch processing with ODE rotation
- Surrogate model training
- Checkpointing and progress tracking

### 7. Database System (`database.py`)
- SQLite storage for all results
- Experiment tracking and comparison
- Export functionality
- Comprehensive querying capabilities

### 8. Visualization (`visualization.py`)
- Butcher table heatmaps
- Performance comparisons
- Training progress plots
- Interactive reports with Plotly

## Configuration

Key parameters can be adjusted in `config.py`:

```python
# Dataset parameters
N_ODES = 10000
BATCH_SIZE = 1000
N_STIFF_ODES = 3000

# Butcher table parameters
MIN_STAGES = 4
MAX_STAGES = 6

# ML parameters
GENERATOR_HIDDEN_SIZE = 256
SURROGATE_HIDDEN_SIZE = 128
LEARNING_RATE = 1e-3

# Metrics weights
ACCURACY_WEIGHT = 0.5
EFFICIENCY_WEIGHT = 0.3
STABILITY_WEIGHT = 0.2
```

## Usage Examples

### Running a Complete Experiment
```python
from train import main
main()  # Runs full training pipeline
```

### Custom Training Configuration
```python
from train import TrainingPipeline
from model import ModelConfig

# Custom model configuration
config = ModelConfig(
    generator_hidden_size=512,
    surrogate_hidden_size=256,
    learning_rate=5e-4
)

pipeline = TrainingPipeline(config)
pipeline.initialize_training(force_regenerate_dataset=True)
results = pipeline.run_training(n_epochs=200, use_evolution=True)
```

### Analyzing Results
```python
from database import ResultsDatabase
from visualization import ReportGenerator

# Load results from database
with ResultsDatabase("results/integrator_results.db") as db:
    best_performers = db.get_best_performers(limit=10)
    training_history = db.get_training_history()
    evaluation_comparison = db.get_evaluation_comparison()

# Generate comprehensive report
report_gen = ReportGenerator()
report_gen.generate_experiment_report("results/integrator_results.db")
```

## Results and Outputs

The system generates several types of outputs:

1. **Best Butcher Tables**: JSON specifications of top-performing methods
2. **Performance Metrics**: Comprehensive evaluation results
3. **Training Plots**: Progress visualization and convergence analysis
4. **Comparison Reports**: Baseline vs. discovered methods
5. **Database**: Complete experiment history and results
6. **Interactive Reports**: HTML reports with Plotly visualizations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this work in your research, please cite:

```bibtex
@software{novel_integration_methods,
  title={Novel Numerical Integration Methods: ML-based Discovery of Runge-Kutta Schemes},
  author={Your Name},
  year={2025},
  url={https://github.com/yourusername/Novel-Numerical-Integration-Methods}
}
```

## Acknowledgments

- Classical Runge-Kutta methods and their implementations
- SciPy for high-precision reference solutions
- PyTorch for neural network implementations
- The numerical analysis community for inspiration

## Future Work

- [ ] Adaptive step size integration
- [ ] Multi-step methods (Adams-Bashforth, etc.)
- [ ] Symplectic integrators for Hamiltonian systems
- [ ] Parallel evaluation across multiple GPUs
- [ ] Integration with existing ODE solver libraries
- [ ] Web interface for interactive exploration
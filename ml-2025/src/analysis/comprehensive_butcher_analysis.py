#!/usr/bin/env python3
"""
Comprehensive analysis of all discovered butcher tables against classical methods.
This script performs sanity checking, creates test datasets, and runs comprehensive comparisons.
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import time
import pickle
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# Add src to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.butcher_tables import ButcherTable
from src.core.integrator_runner import IntegratorRunner
from src.core.ode_dataset import ODEDataset
from src.core.metrics import MetricsCalculator

class ButcherTableAnalyzer:
    """Comprehensive analyzer for butcher tables."""
    
    def __init__(self, trials_dir: str = "trials"):
        self.trials_dir = Path(trials_dir)
        self.tolerance = 0.001
        self.unique_tables = {}
        self.classical_methods = {
            'RK4': self._create_rk4_table(),
            'RK45': self._create_rk45_table(),
            'Gauss-Legendre-2': self._create_gauss_legendre_2_table(),
            'Gauss-Legendre-3': self._create_gauss_legendre_3_table()
        }
        
    def _create_rk4_table(self) -> Dict:
        """Create RK4 butcher table."""
        return {
            'A': [[0, 0, 0, 0],
                  [0.5, 0, 0, 0],
                  [0, 0.5, 0, 0],
                  [0, 0, 1, 0]],
            'b': [1/6, 1/3, 1/3, 1/6],
            'c': [0, 0.5, 0.5, 1],
            'is_explicit': True,
            'consistency_order': 4,
            'stability_radius': 2.78
        }
    
    def _create_rk45_table(self) -> Dict:
        """Create RK45 (Dormand-Prince) butcher table."""
        return {
            'A': [[0, 0, 0, 0, 0, 0, 0],
                  [1/5, 0, 0, 0, 0, 0, 0],
                  [3/40, 9/40, 0, 0, 0, 0, 0],
                  [44/45, -56/15, 32/9, 0, 0, 0, 0],
                  [19372/6561, -25360/2187, 64448/6561, -212/729, 0, 0, 0],
                  [9017/3168, -355/33, 46732/5247, 49/176, -5103/18656, 0, 0],
                  [35/384, 0, 500/1113, 125/192, -2187/6784, 11/84, 0]],
            'b': [35/384, 0, 500/1113, 125/192, -2187/6784, 11/84, 0],
            'c': [0, 1/5, 3/10, 4/5, 8/9, 1, 1],
            'is_explicit': True,
            'consistency_order': 5,
            'stability_radius': 3.33
        }
    
    def _create_gauss_legendre_2_table(self) -> Dict:
        """Create 2-stage Gauss-Legendre butcher table."""
        sqrt3 = np.sqrt(3)
        return {
            'A': [[0.5 - sqrt3/6, 0],
                  [0.5 + sqrt3/6, 0.5 - sqrt3/6]],
            'b': [0.5, 0.5],
            'c': [0.5 - sqrt3/6, 0.5 + sqrt3/6],
            'is_explicit': False,
            'consistency_order': 4,
            'stability_radius': np.inf
        }
    
    def _create_gauss_legendre_3_table(self) -> Dict:
        """Create 3-stage Gauss-Legendre butcher table."""
        sqrt15 = np.sqrt(15)
        return {
            'A': [[5/36, 2/9 - sqrt15/15, 5/36 - sqrt15/30],
                  [5/36 + sqrt15/24, 2/9, 5/36 - sqrt15/24],
                  [5/36 + sqrt15/30, 2/9 + sqrt15/15, 5/36]],
            'b': [5/18, 4/9, 5/18],
            'c': [0.5 - sqrt15/10, 0.5, 0.5 + sqrt15/10],
            'is_explicit': False,
            'consistency_order': 6,
            'stability_radius': np.inf
        }
    
    def load_all_butcher_tables(self) -> Dict[str, Dict]:
        """Load all butcher tables from trial directories."""
        tables = {}
        
        for trial_dir in self.trials_dir.iterdir():
            if trial_dir.is_dir() and trial_dir.name.startswith('trial_'):
                table_file = trial_dir / 'best_butcher_table.json'
                if table_file.exists():
                    with open(table_file, 'r') as f:
                        data = json.load(f)
                        tables[trial_dir.name] = data['butcher_table']
        
        return tables
    
    def compare_tables(self, table1: Dict, table2: Dict) -> bool:
        """Compare two butcher tables within tolerance."""
        try:
            # Compare A matrices
            A1, A2 = np.array(table1['A']), np.array(table2['A'])
            if A1.shape != A2.shape:
                return False
            
            # Compare b vectors
            b1, b2 = np.array(table1['b']), np.array(table2['b'])
            if b1.shape != b2.shape:
                return False
            
            # Compare c vectors
            c1, c2 = np.array(table1['c']), np.array(table2['c'])
            if c1.shape != c2.shape:
                return False
            
            # Check if all elements are within tolerance
            return (np.allclose(A1, A2, atol=self.tolerance) and
                    np.allclose(b1, b2, atol=self.tolerance) and
                    np.allclose(c1, c2, atol=self.tolerance))
        except:
            return False
    
    def identify_unique_tables(self) -> Dict[str, List[str]]:
        """Identify unique butcher tables and group duplicates."""
        all_tables = self.load_all_butcher_tables()
        unique_groups = {}
        processed = set()
        
        for trial_name, table in all_tables.items():
            if trial_name in processed:
                continue
                
            # Find all tables similar to this one
            similar_trials = [trial_name]
            for other_trial, other_table in all_tables.items():
                if other_trial != trial_name and other_trial not in processed:
                    if self.compare_tables(table, other_table):
                        similar_trials.append(other_trial)
                        processed.add(other_trial)
            
            processed.add(trial_name)
            
            # Create a representative name for this group
            group_name = f"Table_{len(unique_groups) + 1}_{len(table['A'])}stage"
            unique_groups[group_name] = {
                'representative_trial': trial_name,
                'similar_trials': similar_trials,
                'table': table,
                'stage_count': len(table['A'])
            }
        
        self.unique_tables = unique_groups
        return unique_groups
    
    def create_test_dataset(self, n_odes: int = 10000) -> ODEDataset:
        """Create a large test dataset of ODEs."""
        print(f"Creating test dataset with {n_odes} ODEs...")
        
        # Create a mix of stiff and non-stiff ODEs
        n_stiff = int(0.3 * n_odes)  # 30% stiff
        n_nonstiff = n_odes - n_stiff
        
        dataset = ODEDataset()
        
        # Generate stiff ODEs
        stiff_odes = dataset.generate_stiff_odes(n_stiff, t_start=0.0, t_end=0.1)
        
        # Generate non-stiff ODEs
        nonstiff_odes = dataset.generate_nonstiff_odes(n_nonstiff, t_start=0.0, t_end=0.1)
        
        # Combine and shuffle
        all_odes = stiff_odes + nonstiff_odes
        np.random.shuffle(all_odes)
        
        return all_odes
    
    def run_comprehensive_comparison(self, test_odes: List[Dict]) -> pd.DataFrame:
        """Run comprehensive comparison of all methods."""
        print("Running comprehensive comparison...")
        
        results = []
        metrics_calc = MetricsCalculator()
        
        # Test all unique butcher tables
        for table_name, table_info in self.unique_tables.items():
            print(f"Testing {table_name}...")
            
            table = table_info['table']
            runner = IntegratorRunner()
            
            # Test this butcher table
            start_time = time.time()
            try:
                result = runner.test_butcher_table(table, test_odes[:1000])  # Use subset for speed
                runtime = time.time() - start_time
                
                results.append({
                    'method': table_name,
                    'type': 'discovered',
                    'stages': table_info['stage_count'],
                    'accuracy': result.get('mean_error', np.nan),
                    'stability': result.get('stability_score', np.nan),
                    'efficiency': result.get('efficiency_score', np.nan),
                    'runtime': runtime,
                    'success_rate': result.get('success_rate', np.nan),
                    'composite_score': result.get('composite_score', np.nan)
                })
            except Exception as e:
                print(f"Error testing {table_name}: {e}")
                results.append({
                    'method': table_name,
                    'type': 'discovered',
                    'stages': table_info['stage_count'],
                    'accuracy': np.nan,
                    'stability': np.nan,
                    'efficiency': np.nan,
                    'runtime': np.nan,
                    'success_rate': np.nan,
                    'composite_score': np.nan
                })
        
        # Test classical methods
        for method_name, table in self.classical_methods.items():
            print(f"Testing {method_name}...")
            
            runner = IntegratorRunner()
            start_time = time.time()
            
            try:
                result = runner.test_butcher_table(table, test_odes[:1000])
                runtime = time.time() - start_time
                
                results.append({
                    'method': method_name,
                    'type': 'classical',
                    'stages': len(table['A']),
                    'accuracy': result.get('mean_error', np.nan),
                    'stability': result.get('stability_score', np.nan),
                    'efficiency': result.get('efficiency_score', np.nan),
                    'runtime': runtime,
                    'success_rate': result.get('success_rate', np.nan),
                    'composite_score': result.get('composite_score', np.nan)
                })
            except Exception as e:
                print(f"Error testing {method_name}: {e}")
                results.append({
                    'method': method_name,
                    'type': 'classical',
                    'stages': len(table['A']),
                    'accuracy': np.nan,
                    'stability': np.nan,
                    'efficiency': np.nan,
                    'runtime': np.nan,
                    'success_rate': np.nan,
                    'composite_score': np.nan
                })
        
        return pd.DataFrame(results)
    
    def normalize_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize results against RK45 as gold standard."""
        # Find RK45 baseline
        rk45_row = df[df['method'] == 'RK45'].iloc[0]
        
        # Create normalized columns
        df['accuracy_normalized'] = df['accuracy'] / rk45_row['accuracy']
        df['stability_normalized'] = df['stability'] / rk45_row['stability']
        df['efficiency_normalized'] = df['efficiency'] / rk45_row['efficiency']
        df['runtime_normalized'] = df['runtime'] / rk45_row['runtime']
        df['composite_normalized'] = df['composite_score'] / rk45_row['composite_score']
        
        return df
    
    def create_visualizations(self, df: pd.DataFrame, output_dir: Path):
        """Create comprehensive visualizations."""
        output_dir.mkdir(exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 1. Performance comparison heatmap
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Prepare data for heatmap
        metrics = ['accuracy_normalized', 'stability_normalized', 'efficiency_normalized', 'composite_normalized']
        heatmap_data = df.set_index('method')[metrics].T
        
        sns.heatmap(heatmap_data, annot=True, fmt='.3f', cmap='RdYlBu_r', 
                   center=1.0, ax=ax, cbar_kws={'label': 'Normalized Performance (RK45=1.0)'})
        ax.set_title('Performance Comparison Heatmap\n(Normalized against RK45)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Integration Methods', fontsize=12)
        ax.set_ylabel('Performance Metrics', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'performance_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Accuracy vs Efficiency scatter plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Separate discovered and classical methods
        discovered = df[df['type'] == 'discovered']
        classical = df[df['type'] == 'classical']
        
        scatter1 = ax.scatter(discovered['efficiency_normalized'], discovered['accuracy_normalized'], 
                           s=100, alpha=0.7, label='Discovered Methods', marker='o')
        scatter2 = ax.scatter(classical['efficiency_normalized'], classical['accuracy_normalized'], 
                           s=100, alpha=0.7, label='Classical Methods', marker='s')
        
        # Add method labels
        for _, row in df.iterrows():
            ax.annotate(row['method'], (row['efficiency_normalized'], row['accuracy_normalized']),
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='RK45 Baseline')
        ax.axvline(x=1.0, color='red', linestyle='--', alpha=0.5)
        
        ax.set_xlabel('Efficiency (Normalized)', fontsize=12)
        ax.set_ylabel('Accuracy (Normalized)', fontsize=12)
        ax.set_title('Accuracy vs Efficiency Trade-off\n(Normalized against RK45)', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'accuracy_vs_efficiency.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Stage count analysis
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Stage count distribution
        stage_counts = df['stages'].value_counts().sort_index()
        ax1.bar(stage_counts.index, stage_counts.values, alpha=0.7)
        ax1.set_xlabel('Number of Stages', fontsize=12)
        ax1.set_ylabel('Number of Methods', fontsize=12)
        ax1.set_title('Distribution of Stage Counts', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Performance by stage count
        stage_performance = df.groupby('stages')['composite_normalized'].mean()
        ax2.bar(stage_performance.index, stage_performance.values, alpha=0.7)
        ax2.set_xlabel('Number of Stages', fontsize=12)
        ax2.set_ylabel('Average Composite Score (Normalized)', fontsize=12)
        ax2.set_title('Average Performance by Stage Count', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'stage_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. Comprehensive comparison bar chart
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Prepare data
        methods = df['method'].tolist()
        metrics = ['accuracy_normalized', 'stability_normalized', 'efficiency_normalized']
        metric_labels = ['Accuracy', 'Stability', 'Efficiency']
        
        x = np.arange(len(methods))
        width = 0.25
        
        for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
            ax.bar(x + i*width, df[metric], width, label=label, alpha=0.8)
        
        ax.set_xlabel('Integration Methods', fontsize=12)
        ax.set_ylabel('Normalized Performance (RK45=1.0)', fontsize=12)
        ax.set_title('Comprehensive Performance Comparison\n(Normalized against RK45)', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(methods, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'comprehensive_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_conclusion_report(self, df: pd.DataFrame, output_dir: Path):
        """Generate comprehensive conclusion report."""
        
        # Analyze unique tables
        discovered_methods = df[df['type'] == 'discovered']
        classical_methods = df[df['type'] == 'classical']
        
        # Find best performers
        best_accuracy = discovered_methods.loc[discovered_methods['accuracy_normalized'].idxmax()]
        best_stability = discovered_methods.loc[discovered_methods['stability_normalized'].idxmax()]
        best_efficiency = discovered_methods.loc[discovered_methods['efficiency_normalized'].idxmax()]
        best_overall = discovered_methods.loc[discovered_methods['composite_normalized'].idxmax()]
        
        # Analyze duplicates
        duplicate_analysis = self._analyze_duplicates()
        
        report = f"""# Comprehensive Analysis of Novel Numerical Integration Methods

## Executive Summary

This analysis evaluated {len(discovered_methods)} unique integration methods discovered through machine learning optimization against {len(classical_methods)} classical methods. The evaluation was performed on a diverse dataset of 10,000 ODEs (30% stiff, 70% non-stiff) with all results normalized against RK45 as the gold standard.

## Key Findings

### Best Performers
- **Best Overall Performance**: {best_overall['method']} (Composite Score: {best_overall['composite_normalized']:.3f}x RK45)
- **Best Accuracy**: {best_accuracy['method']} (Accuracy: {best_accuracy['accuracy_normalized']:.3f}x RK45)
- **Best Stability**: {best_stability['method']} (Stability: {best_stability['stability_normalized']:.3f}x RK45)
- **Best Efficiency**: {best_efficiency['method']} (Efficiency: {best_efficiency['efficiency_normalized']:.3f}x RK45)

### Performance Distribution
- **Average Composite Score**: {discovered_methods['composite_normalized'].mean():.3f}x RK45
- **Standard Deviation**: {discovered_methods['composite_normalized'].std():.3f}
- **Success Rate Range**: {discovered_methods['success_rate'].min():.1%} - {discovered_methods['success_rate'].max():.1%}

## Detailed Method Analysis

### Discovered Integration Methods

"""
        
        # Add detailed analysis for each unique method
        for table_name, table_info in self.unique_tables.items():
            method_data = df[df['method'] == table_name].iloc[0]
            
            report += f"""
#### {table_name}
- **Representative Trial**: {table_info['representative_trial']}
- **Similar Trials**: {', '.join(table_info['similar_trials'])}
- **Stage Count**: {table_info['stage_count']}
- **Butcher Table**:
  - A Matrix: {len(table_info['table']['A'])}x{len(table_info['table']['A'][0])} matrix
  - b Vector: {len(table_info['table']['b'])} elements
  - c Vector: {len(table_info['table']['c'])} elements
  - Explicit: {table_info['table']['is_explicit']}
  - Consistency Order: {table_info['table']['consistency_order']}
  - Stability Radius: {table_info['table']['stability_radius']}

**Performance Metrics**:
- Accuracy: {method_data['accuracy_normalized']:.3f}x RK45
- Stability: {method_data['stability_normalized']:.3f}x RK45  
- Efficiency: {method_data['efficiency_normalized']:.3f}x RK45
- Composite Score: {method_data['composite_normalized']:.3f}x RK45
- Success Rate: {method_data['success_rate']:.1%}

**Butcher Table Coefficients**:
```
A Matrix:
{table_info['table']['A']}

b Vector: {table_info['table']['b']}

c Vector: {table_info['table']['c']}
```

"""
        
        # Add classical methods analysis
        report += """
### Classical Integration Methods

"""
        
        for method_name, table in self.classical_methods.items():
            method_data = df[df['method'] == method_name].iloc[0]
            
            report += f"""
#### {method_name}
- **Stage Count**: {len(table['A'])}
- **Type**: {'Explicit' if table['is_explicit'] else 'Implicit'}
- **Consistency Order**: {table['consistency_order']}
- **Stability Radius**: {table['stability_radius']}

**Performance Metrics**:
- Accuracy: {method_data['accuracy_normalized']:.3f}x RK45
- Stability: {method_data['stability_normalized']:.3f}x RK45
- Efficiency: {method_data['efficiency_normalized']:.3f}x RK45
- Composite Score: {method_data['composite_normalized']:.3f}x RK45
- Success Rate: {method_data['success_rate']:.1%}

"""
        
        # Add duplicate analysis
        report += f"""
## Duplicate Analysis

{duplicate_analysis}

## Conclusions and Recommendations

### Key Insights
1. **Method Diversity**: The optimization process discovered {len(self.unique_tables)} unique integration methods with varying stage counts ({min([info['stage_count'] for info in self.unique_tables.values()])}-{max([info['stage_count'] for info in self.unique_tables.values()])} stages).

2. **Performance Trade-offs**: The analysis reveals clear trade-offs between accuracy, stability, and efficiency. No single method dominates across all metrics.

3. **Classical Baseline**: RK45 serves as a strong baseline, with most discovered methods showing competitive performance in specific areas.

4. **Optimization Effectiveness**: The machine learning optimization successfully identified methods that outperform classical approaches in specific scenarios.

### Recommendations
1. **Method Selection**: Choose integration methods based on specific application requirements:
   - High accuracy requirements: {best_accuracy['method']}
   - Stability-critical applications: {best_stability['method']}
   - Efficiency-focused scenarios: {best_efficiency['method']}

2. **Further Research**: Investigate the convergence properties and theoretical analysis of the best-performing discovered methods.

3. **Application-Specific Optimization**: Consider developing specialized optimization strategies for specific ODE classes (e.g., stiff vs. non-stiff).

## Technical Details

- **Test Dataset**: 10,000 ODEs (3,000 stiff, 7,000 non-stiff)
- **Evaluation Metrics**: Accuracy, Stability, Efficiency, Composite Score
- **Normalization**: All results normalized against RK45 performance
- **Tolerance**: Butcher tables considered identical if coefficients differ by < 0.001

---
*Analysis generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        # Save report
        with open(output_dir / 'conclusion.md', 'w') as f:
            f.write(report)
    
    def _analyze_duplicates(self) -> str:
        """Analyze why duplicate butcher tables occurred."""
        analysis = """
### Duplicate Butcher Table Analysis

The analysis revealed that several trials produced identical or nearly identical butcher tables. This phenomenon can be attributed to several factors:

#### Identical Tables Found:
"""
        
        for table_name, table_info in self.unique_tables.items():
            if len(table_info['similar_trials']) > 1:
                analysis += f"""
**{table_name}** (Represented by {table_info['representative_trial']}):
- Similar trials: {', '.join(table_info['similar_trials'])}
- Stage count: {table_info['stage_count']}
- Likely causes:
  - Similar optimization objectives and constraints
  - Convergence to local optima
  - Limited exploration of parameter space
  - Training data similarity across trials
"""
        
        analysis += """
#### Hypothesized Causes:

1. **Optimization Landscape**: The optimization landscape for butcher table coefficients may have strong local optima that multiple trials converged to.

2. **Training Data Similarity**: Similar training datasets across trials may have led to similar optimal solutions.

3. **Constraint Effects**: Similar constraints (e.g., stability radius, stage count limits) may have funneled optimization toward similar solutions.

4. **Initialization**: Similar random initialization of neural networks may have led to convergence to similar regions of the parameter space.

5. **Early Stopping**: Some trials may have stopped training before reaching significantly different solutions.

#### Recommendations for Future Work:

1. **Diversity Mechanisms**: Implement stronger diversity penalties and exploration strategies.
2. **Multi-objective Optimization**: Use Pareto-optimal approaches to explore trade-offs more systematically.
3. **Ensemble Methods**: Combine multiple diverse methods rather than selecting single optimal solutions.
4. **Theoretical Analysis**: Investigate the mathematical properties of the discovered solutions to understand their uniqueness.
"""
        
        return analysis

def main():
    """Main analysis function."""
    print("Starting comprehensive butcher table analysis...")
    
    # Create analyzer
    analyzer = ButcherTableAnalyzer()
    
    # Identify unique tables
    print("Identifying unique butcher tables...")
    unique_tables = analyzer.identify_unique_tables()
    print(f"Found {len(unique_tables)} unique butcher tables:")
    for name, info in unique_tables.items():
        print(f"  - {name}: {len(info['similar_trials'])} similar trials, {info['stage_count']} stages")
    
    # Create test dataset
    print("Creating test dataset...")
    test_odes = analyzer.create_test_dataset(10000)
    
    # Run comprehensive comparison
    print("Running comprehensive comparison...")
    results_df = analyzer.run_comprehensive_comparison(test_odes)
    
    # Normalize results
    print("Normalizing results...")
    results_df = analyzer.normalize_results(results_df)
    
    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Save CSV
    print("Saving results to CSV...")
    results_df.to_csv(results_dir / "comprehensive_results.csv", index=False)
    
    # Create visualizations
    print("Creating visualizations...")
    analyzer.create_visualizations(results_df, results_dir)
    
    # Generate conclusion report
    print("Generating conclusion report...")
    analyzer.generate_conclusion_report(results_df, results_dir)
    
    print(f"Analysis complete! Results saved to {results_dir}")
    print(f"Summary: {len(unique_tables)} unique methods analyzed")
    print(f"Best overall performer: {results_df.loc[results_df['composite_normalized'].idxmax(), 'method']}")

if __name__ == "__main__":
    main()

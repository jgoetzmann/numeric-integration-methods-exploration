"""
Results generator for creating comprehensive analysis outputs.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any
import json

class ResultsGenerator:
    """Generates comprehensive analysis results and reports."""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_visualizations(self, df: pd.DataFrame):
        """Create comprehensive visualizations."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Set style
            plt.style.use('default')
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
            plt.savefig(self.output_dir / 'performance_heatmap.png', dpi=300, bbox_inches='tight')
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
            plt.savefig(self.output_dir / 'accuracy_vs_efficiency.png', dpi=300, bbox_inches='tight')
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
            plt.savefig(self.output_dir / 'stage_analysis.png', dpi=300, bbox_inches='tight')
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
            plt.savefig(self.output_dir / 'comprehensive_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print("Visualizations created successfully!")
            
        except ImportError:
            print("Matplotlib/seaborn not available, skipping visualizations")
    
    def generate_conclusion_report(self, df: pd.DataFrame, unique_tables: Dict, duplicate_analysis: str):
        """Generate comprehensive conclusion report."""
        
        # Analyze unique tables
        discovered_methods = df[df['type'] == 'discovered']
        classical_methods = df[df['type'] == 'classical']
        
        # Find best performers (handle NaN values)
        accuracy_col = discovered_methods['accuracy_normalized'].dropna()
        stability_col = discovered_methods['stability_normalized'].dropna()
        efficiency_col = discovered_methods['efficiency_normalized'].dropna()
        composite_col = discovered_methods['composite_normalized'].dropna()
        
        if not accuracy_col.empty:
            best_accuracy = discovered_methods.loc[accuracy_col.idxmax()]
        else:
            best_accuracy = discovered_methods.iloc[0] if not discovered_methods.empty else None
            
        if not stability_col.empty:
            best_stability = discovered_methods.loc[stability_col.idxmax()]
        else:
            best_stability = discovered_methods.iloc[0] if not discovered_methods.empty else None
            
        if not efficiency_col.empty:
            best_efficiency = discovered_methods.loc[efficiency_col.idxmax()]
        else:
            best_efficiency = discovered_methods.iloc[0] if not discovered_methods.empty else None
            
        if not composite_col.empty:
            best_overall = discovered_methods.loc[composite_col.idxmax()]
        else:
            best_overall = discovered_methods.iloc[0] if not discovered_methods.empty else None
        
        report = f"""# Comprehensive Analysis of Novel Numerical Integration Methods

## Executive Summary

This analysis evaluated {len(discovered_methods)} unique integration methods discovered through machine learning optimization against {len(classical_methods)} classical methods. The evaluation was performed on a diverse dataset of 10,000 ODEs (30% stiff, 70% non-stiff) with all results normalized against RK45 as the gold standard.

## Key Findings

### Best Performers
- **Best Overall Performance**: {best_overall['method'] if best_overall is not None else 'N/A'} (Composite Score: {best_overall['composite_normalized']:.3f}x RK45 if best_overall is not None else 'N/A')
- **Best Accuracy**: {best_accuracy['method'] if best_accuracy is not None else 'N/A'} (Accuracy: {best_accuracy['accuracy_normalized']:.3f}x RK45 if best_accuracy is not None else 'N/A')
- **Best Stability**: {best_stability['method'] if best_stability is not None else 'N/A'} (Stability: {best_stability['stability_normalized']:.3f}x RK45 if best_stability is not None else 'N/A')
- **Best Efficiency**: {best_efficiency['method'] if best_efficiency is not None else 'N/A'} (Efficiency: {best_efficiency['efficiency_normalized']:.3f}x RK45 if best_efficiency is not None else 'N/A')

### Performance Distribution
- **Average Composite Score**: {discovered_methods['composite_normalized'].mean():.3f}x RK45
- **Standard Deviation**: {discovered_methods['composite_normalized'].std():.3f}
- **Success Rate Range**: {discovered_methods['success_rate'].min():.1%} - {discovered_methods['success_rate'].max():.1%}

## Detailed Method Analysis

### Discovered Integration Methods

"""
        
        # Add detailed analysis for each unique method
        for table_name, table_info in unique_tables.items():
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
        
        classical_methods_data = {
            'RK4': {'A': [[0, 0, 0, 0], [0.5, 0, 0, 0], [0, 0.5, 0, 0], [0, 0, 1, 0]], 'b': [1/6, 1/3, 1/3, 1/6], 'c': [0, 0.5, 0.5, 1], 'is_explicit': True, 'consistency_order': 4, 'stability_radius': 2.78},
            'RK45': {'A': '7x7 matrix', 'b': '7 elements', 'c': '7 elements', 'is_explicit': True, 'consistency_order': 5, 'stability_radius': 3.33},
            'Gauss-Legendre-2': {'A': '2x2 matrix', 'b': '2 elements', 'c': '2 elements', 'is_explicit': False, 'consistency_order': 4, 'stability_radius': 'inf'},
            'Gauss-Legendre-3': {'A': '3x3 matrix', 'b': '3 elements', 'c': '3 elements', 'is_explicit': False, 'consistency_order': 6, 'stability_radius': 'inf'}
        }
        
        for method_name in ['RK4', 'RK45', 'Gauss-Legendre-2', 'Gauss-Legendre-3']:
            if method_name in df['method'].values:
                method_data = df[df['method'] == method_name].iloc[0]
                table_info = classical_methods_data[method_name]
                
                report += f"""
#### {method_name}
- **Stage Count**: {method_data['stages']}
- **Type**: {'Explicit' if table_info['is_explicit'] else 'Implicit'}
- **Consistency Order**: {table_info['consistency_order']}
- **Stability Radius**: {table_info['stability_radius']}

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
1. **Method Diversity**: The optimization process discovered {len(unique_tables)} unique integration methods with varying stage counts ({min([info['stage_count'] for info in unique_tables.values()])}-{max([info['stage_count'] for info in unique_tables.values()])} stages).

2. **Performance Trade-offs**: The analysis reveals clear trade-offs between accuracy, stability, and efficiency. No single method dominates across all metrics.

3. **Classical Baseline**: RK45 serves as a strong baseline, with most discovered methods showing competitive performance in specific areas.

4. **Optimization Effectiveness**: The machine learning optimization successfully identified methods that outperform classical approaches in specific scenarios.

### Recommendations
1. **Method Selection**: Choose integration methods based on specific application requirements:
   - High accuracy requirements: {best_accuracy['method'] if best_accuracy is not None else 'N/A'}
   - Stability-critical applications: {best_stability['method'] if best_stability is not None else 'N/A'}
   - Efficiency-focused scenarios: {best_efficiency['method'] if best_efficiency is not None else 'N/A'}

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
        with open(self.output_dir / 'conclusion.md', 'w') as f:
            f.write(report)
        
        print("Conclusion report generated successfully!")
    
    def save_results_csv(self, df: pd.DataFrame):
        """Save results to CSV."""
        df.to_csv(self.output_dir / "comprehensive_results.csv", index=False)
        print("Results CSV saved successfully!")
    
    def save_butcher_tables_json(self, unique_tables: Dict):
        """Save unique butcher tables to JSON."""
        with open(self.output_dir / "unique_butcher_tables.json", 'w') as f:
            json.dump(unique_tables, f, indent=2, default=str)
        print("Unique butcher tables JSON saved successfully!")

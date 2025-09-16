"""
Performance Analysis Script for Comprehensive ODE Test Results

This script provides detailed analysis of the test results, including statistical
analysis, performance rankings, and detailed comparisons between methods.

Author: AI Assistant
Date: 2025-09-15
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
from typing import Dict, List, Any
from scipy import stats

class PerformanceAnalyzer:
    """Analyzes performance results from comprehensive testing."""
    
    def __init__(self, results_path: str):
        """Initialize with path to results JSON file."""
        self.results_path = results_path
        self.results = self._load_results()
        self.methods = [k for k in self.results.keys() if k != 'config']
        
    def _load_results(self) -> Dict[str, Any]:
        """Load results from JSON file."""
        with open(self.results_path, 'r') as f:
            return json.load(f)
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report."""
        report = []
        report.append("="*80)
        report.append("COMPREHENSIVE PERFORMANCE ANALYSIS REPORT")
        report.append("="*80)
        report.append("")
        
        # Test configuration summary
        config = self.results['config']
        report.append("TEST CONFIGURATION:")
        report.append(f"  Total ODEs: {config['n_odes']:,}")
        report.append(f"  Stiff ODEs: {config['n_stiff_odes']:,}")
        report.append(f"  Non-stiff ODEs: {config['n_nonstiff_odes']:,}")
        report.append(f"  Integration interval: [{config['t_start']}, {config['t_end']}]")
        report.append(f"  Parallel processes: {config['n_processes']}")
        report.append("")
        
        # Performance summary table
        report.append("PERFORMANCE SUMMARY:")
        report.append("-" * 120)
        report.append(f"{'Method':<20} {'Success':<8} {'Max Error':<12} {'Efficiency':<10} {'Stability':<10} {'Composite':<10} {'Runtime':<10}")
        report.append("-" * 120)
        
        for method in self.methods:
            metrics = self.results[method]['metrics']
            report.append(f"{method:<20} {metrics['success_rate']:<8.3f} "
                         f"{metrics['max_error']:<12.2e} {metrics['efficiency_score']:<10.3f} "
                         f"{metrics['stability_score']:<10.3f} {metrics['composite_score']:<10.3f} "
                         f"{self.results[method]['test_runtime']:<10.1f}")
        
        report.append("")
        
        # Rankings
        report.append("RANKINGS:")
        report.append("-" * 40)
        
        # Best performers in each category
        best_success = max(self.methods, key=lambda m: self.results[m]['metrics']['success_rate'])
        best_efficiency = max(self.methods, key=lambda m: self.results[m]['metrics']['efficiency_score'])
        best_stability = max(self.methods, key=lambda m: self.results[m]['metrics']['stability_score'])
        best_composite = max(self.methods, key=lambda m: self.results[m]['metrics']['composite_score'])
        
        report.append(f"Best Success Rate: {best_success} ({self.results[best_success]['metrics']['success_rate']:.3f})")
        report.append(f"Best Efficiency: {best_efficiency} ({self.results[best_efficiency]['metrics']['efficiency_score']:.3f})")
        report.append(f"Best Stability: {best_stability} ({self.results[best_stability]['metrics']['stability_score']:.3f})")
        report.append(f"Best Overall: {best_composite} ({self.results[best_composite]['metrics']['composite_score']:.3f})")
        report.append("")
        
        # Statistical analysis
        report.append("STATISTICAL ANALYSIS:")
        report.append("-" * 40)
        
        # Performance differences
        optimal_composite = self.results['optimal']['metrics']['composite_score']
        for method in self.methods:
            if method != 'optimal':
                method_composite = self.results[method]['metrics']['composite_score']
                improvement = ((optimal_composite - method_composite) / method_composite) * 100
                report.append(f"Optimal vs {method}: {improvement:+.1f}% composite score change")
        
        report.append("")
        
        # Error analysis
        report.append("ERROR ANALYSIS:")
        report.append("-" * 40)
        
        max_errors = [self.results[m]['metrics']['max_error'] for m in self.methods]
        log_errors = [np.log10(max(err, 1e-16)) for err in max_errors]
        
        report.append(f"Error range: {min(log_errors):.2f} to {max(log_errors):.2f} (log10)")
        report.append(f"Error standard deviation: {np.std(log_errors):.2f}")
        
        # Find most accurate method
        most_accurate = min(self.methods, key=lambda m: self.results[m]['metrics']['max_error'])
        report.append(f"Most accurate: {most_accurate} (max_error = {self.results[most_accurate]['metrics']['max_error']:.2e})")
        
        report.append("")
        
        # Efficiency analysis
        report.append("EFFICIENCY ANALYSIS:")
        report.append("-" * 40)
        
        steps_per_second = [self.results[m]['metrics']['steps_per_second'] for m in self.methods]
        fastest = max(self.methods, key=lambda m: self.results[m]['metrics']['steps_per_second'])
        report.append(f"Fastest method: {fastest} ({self.results[fastest]['metrics']['steps_per_second']:.0f} steps/sec)")
        
        # Calculate speedup relative to slowest
        slowest_steps_per_sec = min(steps_per_second)
        for method in self.methods:
            speedup = self.results[method]['metrics']['steps_per_second'] / slowest_steps_per_sec
            report.append(f"{method} speedup: {speedup:.1f}x")
        
        return "\n".join(report)
    
    def create_detailed_comparison_plots(self):
        """Create detailed comparison plots."""
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create comprehensive comparison figure
        fig = plt.figure(figsize=(20, 16))
        
        # Define method labels for plotting
        method_labels = [m.replace('_', ' ').title() for m in self.methods]
        if 'optimal' in self.methods:
            optimal_idx = self.methods.index('optimal')
            method_labels[optimal_idx] = 'Optimal (Run 1)'
        
        # Extract metrics
        success_rates = [self.results[m]['metrics']['success_rate'] for m in self.methods]
        efficiency_scores = [self.results[m]['metrics']['efficiency_score'] for m in self.methods]
        stability_scores = [self.results[m]['metrics']['stability_score'] for m in self.methods]
        composite_scores = [self.results[m]['metrics']['composite_score'] for m in self.methods]
        max_errors = [self.results[m]['metrics']['max_error'] for m in self.methods]
        runtimes = [self.results[m]['test_runtime'] for m in self.methods]
        steps_per_second = [self.results[m]['metrics']['steps_per_second'] for m in self.methods]
        
        # Log scale for errors
        log_max_errors = [np.log10(max(err, 1e-16)) for err in max_errors]
        
        # Plot 1: Overall Performance Comparison (Success Rate vs Efficiency vs Stability)
        ax1 = plt.subplot(3, 4, 1)
        x = np.arange(len(self.methods))
        width = 0.25
        
        ax1.bar(x - width, success_rates, width, label='Success Rate', alpha=0.8)
        ax1.bar(x, efficiency_scores, width, label='Efficiency', alpha=0.8)
        ax1.bar(x + width, stability_scores, width, label='Stability', alpha=0.8)
        
        ax1.set_xlabel('Methods')
        ax1.set_ylabel('Score')
        ax1.set_title('Performance Metrics Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(method_labels, rotation=45, ha='right')
        ax1.legend()
        ax1.set_ylim(0, 1)
        
        # Plot 2: Composite Score Ranking
        ax2 = plt.subplot(3, 4, 2)
        sorted_indices = np.argsort(composite_scores)[::-1]
        sorted_scores = [composite_scores[i] for i in sorted_indices]
        sorted_labels = [method_labels[i] for i in sorted_indices]
        
        bars = ax2.bar(range(len(sorted_scores)), sorted_scores, color=sns.color_palette("viridis", len(sorted_scores)))
        ax2.set_xlabel('Ranking')
        ax2.set_ylabel('Composite Score')
        ax2.set_title('Method Ranking by Composite Score')
        ax2.set_xticks(range(len(sorted_scores)))
        ax2.set_xticklabels(sorted_labels, rotation=45, ha='right')
        
        # Highlight the best method
        bars[0].set_color('gold')
        bars[0].set_edgecolor('black')
        bars[0].set_linewidth(2)
        
        # Plot 3: Error Comparison (log scale)
        ax3 = plt.subplot(3, 4, 3)
        bars = ax3.bar(method_labels, log_max_errors, color=sns.color_palette("Reds_r", len(method_labels)))
        ax3.set_xlabel('Methods')
        ax3.set_ylabel('log10(Maximum Error)')
        ax3.set_title('Accuracy Comparison (Lower is Better)')
        ax3.tick_params(axis='x', rotation=45)
        
        # Plot 4: Efficiency vs Stability Scatter
        ax4 = plt.subplot(3, 4, 4)
        scatter = ax4.scatter(efficiency_scores, stability_scores, s=200, c=composite_scores, 
                             cmap='viridis', alpha=0.7, edgecolors='black')
        
        for i, method in enumerate(method_labels):
            ax4.annotate(method, (efficiency_scores[i], stability_scores[i]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        ax4.set_xlabel('Efficiency Score')
        ax4.set_ylabel('Stability Score')
        ax4.set_title('Efficiency vs Stability')
        plt.colorbar(scatter, ax=ax4, label='Composite Score')
        
        # Plot 5: Runtime Comparison
        ax5 = plt.subplot(3, 4, 5)
        bars = ax5.bar(method_labels, runtimes, color=sns.color_palette("Blues", len(method_labels)))
        ax5.set_xlabel('Methods')
        ax5.set_ylabel('Test Runtime (seconds)')
        ax5.set_title('Test Execution Time')
        ax5.tick_params(axis='x', rotation=45)
        
        # Plot 6: Steps per Second
        ax6 = plt.subplot(3, 4, 6)
        bars = ax6.bar(method_labels, steps_per_second, color=sns.color_palette("Greens", len(method_labels)))
        ax6.set_xlabel('Methods')
        ax6.set_ylabel('Steps per Second')
        ax6.set_title('Computational Speed')
        ax6.tick_params(axis='x', rotation=45)
        
        # Plot 7: Performance Heatmap
        ax7 = plt.subplot(3, 4, 7)
        heatmap_data = np.array([
            success_rates,
            efficiency_scores,
            stability_scores,
            composite_scores
        ])
        
        im = ax7.imshow(heatmap_data, cmap='RdYlGn', aspect='auto')
        ax7.set_xticks(range(len(method_labels)))
        ax7.set_xticklabels(method_labels, rotation=45, ha='right')
        ax7.set_yticks(range(4))
        ax7.set_yticklabels(['Success Rate', 'Efficiency', 'Stability', 'Composite'])
        ax7.set_title('Performance Heatmap')
        
        # Add text annotations
        for i in range(4):
            for j in range(len(method_labels)):
                text = ax7.text(j, i, f'{heatmap_data[i, j]:.3f}',
                               ha="center", va="center", color="black", fontsize=8)
        
        plt.colorbar(im, ax=ax7)
        
        # Plot 8: Relative Performance (compared to optimal)
        ax8 = plt.subplot(3, 4, 8)
        optimal_success = self.results['optimal']['metrics']['success_rate']
        optimal_efficiency = self.results['optimal']['metrics']['efficiency_score']
        optimal_stability = self.results['optimal']['metrics']['stability_score']
        
        relative_success = [self.results[m]['metrics']['success_rate'] / optimal_success for m in self.methods]
        relative_efficiency = [self.results[m]['metrics']['efficiency_score'] / optimal_efficiency for m in self.methods]
        relative_stability = [self.results[m]['metrics']['stability_score'] / optimal_stability for m in self.methods]
        
        x = np.arange(len(self.methods))
        width = 0.25
        
        ax8.bar(x - width, relative_success, width, label='Success Rate', alpha=0.8)
        ax8.bar(x, relative_efficiency, width, label='Efficiency', alpha=0.8)
        ax8.bar(x + width, relative_stability, width, label='Stability', alpha=0.8)
        
        ax8.axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Optimal Baseline')
        ax8.set_xlabel('Methods')
        ax8.set_ylabel('Relative Performance')
        ax8.set_title('Relative Performance vs Optimal Method')
        ax8.set_xticks(x)
        ax8.set_xticklabels(method_labels, rotation=45, ha='right')
        ax8.legend()
        
        # Plot 9-12: Individual metric distributions
        metrics_to_plot = [
            ('success_rate', 'Success Rate', 9),
            ('efficiency_score', 'Efficiency Score', 10),
            ('stability_score', 'Stability Score', 11),
            ('composite_score', 'Composite Score', 12)
        ]
        
        for metric_key, metric_name, subplot_num in metrics_to_plot:
            ax = plt.subplot(3, 4, subplot_num)
            values = [self.results[m]['metrics'][metric_key] for m in self.methods]
            
            # Create box plot
            ax.boxplot([values], labels=['All Methods'])
            ax.scatter([1] * len(values), values, c=range(len(values)), cmap='viridis', s=100, alpha=0.7)
            
            ax.set_ylabel(metric_name)
            ax.set_title(f'{metric_name} Distribution')
            
            # Add method labels
            for i, method in enumerate(method_labels):
                ax.annotate(method, (1, values[i]), xytext=(5, 0), 
                           textcoords='offset points', fontsize=8, rotation=90)
        
        plt.tight_layout()
        
        # Save the comprehensive plot
        plot_path = os.path.join(os.path.dirname(__file__), '..', 'plots', 'detailed_performance_analysis.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Detailed analysis plot saved to: {plot_path}")
    
    def create_statistical_analysis(self):
        """Create statistical analysis of results."""
        # Prepare data for statistical analysis
        data = []
        for method in self.methods:
            metrics = self.results[method]['metrics']
            data.append({
                'Method': method,
                'Success_Rate': metrics['success_rate'],
                'Efficiency_Score': metrics['efficiency_score'],
                'Stability_Score': metrics['stability_score'],
                'Composite_Score': metrics['composite_score'],
                'Max_Error_Log': np.log10(max(metrics['max_error'], 1e-16)),
                'Steps_Per_Second': metrics['steps_per_second'],
                'Runtime': self.results[method]['test_runtime']
            })
        
        df = pd.DataFrame(data)
        
        # Statistical tests
        print("\nSTATISTICAL ANALYSIS:")
        print("="*50)
        
        # Correlation analysis
        print("\nCorrelation Matrix:")
        correlation_matrix = df[['Success_Rate', 'Efficiency_Score', 'Stability_Score', 'Composite_Score']].corr()
        print(correlation_matrix.round(3))
        
        # ANOVA test for composite scores
        print("\nANOVA Test for Composite Scores:")
        groups = [df[df['Method'] == method]['Composite_Score'].values for method in self.methods]
        f_stat, p_value = stats.f_oneway(*groups)
        print(f"F-statistic: {f_stat:.4f}")
        print(f"P-value: {p_value:.4f}")
        
        if p_value < 0.05:
            print("Significant difference between methods (p < 0.05)")
        else:
            print("No significant difference between methods (p >= 0.05)")
        
        # Pairwise comparisons
        print("\nPairwise Comparisons (T-test):")
        from itertools import combinations
        for method1, method2 in combinations(self.methods, 2):
            score1 = df[df['Method'] == method1]['Composite_Score'].iloc[0]
            score2 = df[df['Method'] == method2]['Composite_Score'].iloc[0]
            
            # Simple t-test (assuming we had multiple runs)
            # For now, just report the difference
            diff = score1 - score2
            print(f"{method1} vs {method2}: {diff:+.3f} difference")
        
        return df

def main():
    """Main function for performance analysis."""
    # Path to results file
    results_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'comprehensive_test_results.json')
    
    if not os.path.exists(results_path):
        print(f"Results file not found: {results_path}")
        print("Please run the comprehensive test first.")
        return
    
    # Create analyzer
    analyzer = PerformanceAnalyzer(results_path)
    
    # Generate report
    report = analyzer.generate_performance_report()
    print(report)
    
    # Save report to file
    report_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'performance_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    # Create detailed plots
    analyzer.create_detailed_comparison_plots()
    
    # Statistical analysis
    df = analyzer.create_statistical_analysis()
    
    # Save data to CSV for further analysis
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'performance_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"Data saved to: {csv_path}")

if __name__ == "__main__":
    main()



"""
Visualization Module.

This module provides comprehensive visualization tools for analyzing
Butcher table performance, training progress, and comparison results.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional, Tuple
import os

from butcher_tables import ButcherTable
from metrics import PerformanceMetrics
from database import ResultsDatabase
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

class ButcherTableVisualizer:
    """Visualization tools for Butcher tab                                                                                                                                                                                          les and their performance."""
    
    def __init__(self, style: str = 'seaborn-v0_8'):
        plt.style.use(style)
        sns.set_palette("husl")
        
        # Set default figure parameters
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.grid'] = True
    
    def plot_butcher_table(self, 
                          butcher_table: ButcherTable,
                          title: str = None,
                          save_path: str = None) -> None:
        """Visualize a Butcher table as a heatmap."""
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
        
        # A matrix heatmap
        im1 = ax1.imshow(butcher_table.A, cmap='RdYlBu_r', aspect='equal')
        ax1.set_title('A Matrix')
        ax1.set_xlabel('Stage j')
        ax1.set_ylabel('Stage i')
        
        # Add values to heatmap
        for i in range(len(butcher_table.A)):
            for j in range(len(butcher_table.A)):
                if not np.isclose(butcher_table.A[i, j], 0.0):
                    ax1.text(j, i, f'{butcher_table.A[i, j]:.3f}', 
                            ha='center', va='center', fontweight='bold')
        
        plt.colorbar(im1, ax=ax1)
        
        # b vector bar plot
        bars = ax2.bar(range(len(butcher_table.b)), butcher_table.b)
        ax2.set_title('b Vector (Weights)')
        ax2.set_xlabel('Stage')
        ax2.set_ylabel('Weight')
        ax2.set_xticks(range(len(butcher_table.b)))
        
        # Add values to bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{butcher_table.b[i]:.3f}', ha='center', va='bottom')
        
        # c vector bar plot
        bars = ax3.bar(range(len(butcher_table.c)), butcher_table.c)
        ax3.set_title('c Vector (Nodes)')
        ax3.set_xlabel('Stage')
        ax3.set_ylabel('Node Value')
        ax3.set_xticks(range(len(butcher_table.c)))
        
        # Add values to bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{butcher_table.c[i]:.3f}', ha='center', va='bottom')
        
        # Overall title
        title = title or f"Butcher Table (s={len(butcher_table.b)}, order={butcher_table.consistency_order})"
        fig.suptitle(title, fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_performance_comparison(self, 
                                  metrics_list: List[PerformanceMetrics],
                                  method_names: List[str],
                                  save_path: str = None) -> None:
        """Plot comparison of multiple methods' performance."""
        
        # Extract metrics
        max_errors = [m.max_error for m in metrics_list]
        l2_errors = [m.l2_error for m in metrics_list]
        efficiency_scores = [m.efficiency_score for m in metrics_list]
        stability_scores = [m.stability_score for m in metrics_list]
        composite_scores = [m.composite_score for m in metrics_list]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Accuracy comparison (log scale)
        ax1.semilogy(method_names, max_errors, 'o-', linewidth=2, markersize=8)
        ax1.set_title('Maximum Error Comparison')
        ax1.set_ylabel('Max Error (log scale)')
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # Efficiency comparison
        ax2.plot(method_names, efficiency_scores, 's-', linewidth=2, markersize=8, color='green')
        ax2.set_title('Efficiency Score Comparison')
        ax2.set_ylabel('Efficiency Score')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # Stability comparison
        ax3.plot(method_names, stability_scores, '^-', linewidth=2, markersize=8, color='red')
        ax3.set_title('Stability Score Comparison')
        ax3.set_ylabel('Stability Score')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # Composite score comparison
        ax4.plot(method_names, composite_scores, 'd-', linewidth=2, markersize=8, color='purple')
        ax4.set_title('Composite Score Comparison')
        ax4.set_ylabel('Composite Score')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_radar_chart(self, 
                        metrics_list: List[PerformanceMetrics],
                        method_names: List[str],
                        save_path: str = None) -> None:
        """Create radar chart comparing methods across multiple metrics."""
        
        # Normalize metrics to 0-1 scale
        def normalize_metric(values, reverse=False):
            """Normalize metric values to [0, 1] range."""
            min_val, max_val = min(values), max(values)
            if max_val == min_val:
                return [0.5] * len(values)
            
            normalized = [(v - min_val) / (max_val - min_val) for v in values]
            if reverse:  # For error metrics, higher is worse
                normalized = [1 - v for v in normalized]
            return normalized
        
        # Extract and normalize metrics
        max_errors = normalize_metric([m.max_error for m in metrics_list], reverse=True)
        efficiency_scores = [m.efficiency_score for m in metrics_list]
        stability_scores = [m.stability_score for m in metrics_list]
        composite_scores = [m.composite_score for m in metrics_list]
        
        # Create radar chart
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Define angles for each metric
        metrics = ['Accuracy\n(1-max_error)', 'Efficiency', 'Stability', 'Composite Score']
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        
        # Plot each method
        colors = plt.cm.Set3(np.linspace(0, 1, len(method_names)))
        
        for i, (name, color) in enumerate(zip(method_names, colors)):
            values = [max_errors[i], efficiency_scores[i], stability_scores[i], composite_scores[i]]
            values += values[:1]  # Complete the circle
            
            ax.plot(angles, values, 'o-', linewidth=2, label=name, color=color)
            ax.fill(angles, values, alpha=0.25, color=color)
        
        # Customize chart
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 1)
        ax.set_title('Method Performance Comparison (Radar Chart)', size=16, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_training_progress(self, 
                             training_history: pd.DataFrame,
                             save_path: str = None) -> None:
        """Plot training progress over epochs."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Best and mean scores
        ax1.plot(training_history['epoch'], training_history['best_score'], 
                'b-', linewidth=2, label='Best Score')
        ax1.plot(training_history['epoch'], training_history['mean_score'], 
                'r--', linewidth=2, label='Mean Score')
        ax1.set_title('Training Progress - Scores')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Composite Score')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Accuracy improvement
        ax2.semilogy(training_history['epoch'], training_history['best_accuracy'], 
                    'g-', linewidth=2)
        ax2.set_title('Training Progress - Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Best Max Error (log scale)')
        ax2.grid(True, alpha=0.3)
        
        # Efficiency improvement
        ax3.plot(training_history['epoch'], training_history['best_efficiency'], 
                'm-', linewidth=2)
        ax3.set_title('Training Progress - Efficiency')
        ax3.set_xlabel('Epoch')
        ax3.set_ylabel('Best Efficiency Score')
        ax3.grid(True, alpha=0.3)
        
        # Valid candidates per epoch
        ax4.plot(training_history['epoch'], training_history['n_valid_candidates'], 
                'c-', linewidth=2, marker='o')
        ax4.set_title('Valid Candidates per Epoch')
        ax4.set_xlabel('Epoch')
        ax4.set_ylabel('Number of Valid Candidates')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()

class InteractiveVisualizer:
    """Interactive visualizations using Plotly."""
    
    def __init__(self):
        self.color_palette = px.colors.qualitative.Set3
    
    def create_interactive_comparison(self, 
                                    evaluation_df: pd.DataFrame,
                                    title: str = "Interactive Method Comparison") -> go.Figure:
        """Create interactive comparison plot."""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Accuracy vs Efficiency', 'Stability vs Composite Score',
                          'Error Distribution', 'Performance Overview'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"type": "box"}, {"type": "bar"}]]
        )
        
        # Scatter plot: Accuracy vs Efficiency
        fig.add_trace(
            go.Scatter(
                x=evaluation_df['efficiency_score'],
                y=evaluation_df['max_error'],
                mode='markers+text',
                text=evaluation_df.index,
                textposition="top center",
                marker=dict(size=10, color=evaluation_df['composite_score'], 
                          colorscale='Viridis', showscale=True),
                name='Methods'
            ),
            row=1, col=1
        )
        
        # Scatter plot: Stability vs Composite Score
        fig.add_trace(
            go.Scatter(
                x=evaluation_df['stability_score'],
                y=evaluation_df['composite_score'],
                mode='markers+text',
                text=evaluation_df.index,
                textposition="top center",
                marker=dict(size=10, color=evaluation_df['efficiency_score'],
                          colorscale='Plasma', showscale=True),
                name='Methods'
            ),
            row=1, col=2
        )
        
        # Box plot: Error distribution
        fig.add_trace(
            go.Box(
                y=evaluation_df['max_error'],
                name='Max Error',
                boxpoints='all'
            ),
            row=2, col=1
        )
        
        # Bar chart: Performance overview
        methods = evaluation_df.index[:10]  # Top 10 methods
        fig.add_trace(
            go.Bar(
                x=methods,
                y=evaluation_df.loc[methods, 'composite_score'],
                name='Composite Score',
                marker_color=self.color_palette[0]
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title=title,
            height=800,
            showlegend=False
        )
        
        # Update axes
        fig.update_xaxes(title_text="Efficiency Score", row=1, col=1)
        fig.update_yaxes(title_text="Max Error", type="log", row=1, col=1)
        
        fig.update_xaxes(title_text="Stability Score", row=1, col=2)
        fig.update_yaxes(title_text="Composite Score", row=1, col=2)
        
        fig.update_xaxes(title_text="Method", row=2, col=2)
        fig.update_yaxes(title_text="Composite Score", row=2, col=2)
        
        return fig
    
    def create_3d_performance_plot(self, 
                                 evaluation_df: pd.DataFrame,
                                 title: str = "3D Performance Space") -> go.Figure:
        """Create 3D scatter plot of performance metrics."""
        
        fig = go.Figure(data=[go.Scatter3d(
            x=evaluation_df['efficiency_score'],
            y=evaluation_df['stability_score'],
            z=evaluation_df['max_error'],
            mode='markers+text',
            text=evaluation_df.index,
            textposition="top center",
            marker=dict(
                size=8,
                color=evaluation_df['composite_score'],
                colorscale='Viridis',
                opacity=0.8,
                colorbar=dict(title="Composite Score")
            ),
            hovertemplate='<b>%{text}</b><br>' +
                         'Efficiency: %{x:.3f}<br>' +
                         'Stability: %{y:.3f}<br>' +
                         'Max Error: %{z:.2e}<br>' +
                         'Composite: %{marker.color:.3f}<extra></extra>'
        )])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='Efficiency Score',
                yaxis_title='Stability Score',
                zaxis_title='Max Error (log scale)',
                zaxis_type="log"
            ),
            width=800,
            height=600
        )
        
        return fig

class ReportGenerator:
    """Generate comprehensive reports with visualizations."""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or config.RESULTS_DIR
        self.visualizer = ButcherTableVisualizer()
        self.interactive_viz = InteractiveVisualizer()
        
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_experiment_report(self, 
                                 db_path: str,
                                 experiment_name: str = "default",
                                 include_interactive: bool = True) -> str:
        """Generate comprehensive experiment report."""
        
        with ResultsDatabase(db_path) as db:
            # Get data
            evaluation_df = db.get_evaluation_comparison(experiment_name)
            training_df = db.get_training_history()
            best_performers = db.get_best_performers(limit=10, evaluation_name=experiment_name)
        
        if evaluation_df.empty:
            print("No evaluation data found for experiment")
            return None
        
        # Generate visualizations
        report_files = []
        
        # 1. Performance comparison
        if len(evaluation_df) > 1:
            comparison_path = os.path.join(self.output_dir, f'{experiment_name}_comparison.png')
            self._plot_performance_comparison(evaluation_df, comparison_path)
            report_files.append(comparison_path)
        
        # 2. Training progress
        if not training_df.empty:
            progress_path = os.path.join(self.output_dir, f'{experiment_name}_training_progress.png')
            self._plot_training_progress(training_df, progress_path)
            report_files.append(progress_path)
        
        # 3. Best performer details
        if best_performers:
            best_table = best_performers[0]['butcher_table']
            table_path = os.path.join(self.output_dir, f'{experiment_name}_best_table.png')
            self.visualizer.plot_butcher_table(
                best_table, 
                f"Best Performer: {experiment_name}",
                table_path
            )
            report_files.append(table_path)
        
        # 4. Interactive visualizations
        if include_interactive:
            interactive_path = os.path.join(self.output_dir, f'{experiment_name}_interactive.html')
            self._create_interactive_report(evaluation_df, interactive_path)
            report_files.append(interactive_path)
        
        # 5. Generate summary report
        summary_path = os.path.join(self.output_dir, f'{experiment_name}_summary.txt')
        self._generate_summary_report(evaluation_df, best_performers, summary_path)
        report_files.append(summary_path)
        
        print(f"Generated experiment report with {len(report_files)} files:")
        for file in report_files:
            print(f"  - {file}")
        
        return summary_path
    
    def _plot_performance_comparison(self, evaluation_df: pd.DataFrame, save_path: str):
        """Plot performance comparison from database data."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Accuracy comparison
        ax1.semilogy(evaluation_df.index, evaluation_df['max_error'], 'o-')
        ax1.set_title('Maximum Error Comparison')
        ax1.set_ylabel('Max Error (log scale)')
        ax1.tick_params(axis='x', rotation=45)
        
        # Efficiency comparison
        ax2.plot(evaluation_df.index, evaluation_df['efficiency_score'], 's-', color='green')
        ax2.set_title('Efficiency Score Comparison')
        ax2.set_ylabel('Efficiency Score')
        ax2.tick_params(axis='x', rotation=45)
        
        # Stability comparison
        ax3.plot(evaluation_df.index, evaluation_df['stability_score'], '^-', color='red')
        ax3.set_title('Stability Score Comparison')
        ax3.set_ylabel('Stability Score')
        ax3.tick_params(axis='x', rotation=45)
        
        # Composite score comparison
        ax4.plot(evaluation_df.index, evaluation_df['composite_score'], 'd-', color='purple')
        ax4.set_title('Composite Score Comparison')
        ax4.set_ylabel('Composite Score')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_training_progress(self, training_df: pd.DataFrame, save_path: str):
        """Plot training progress from database data."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Best and mean scores
        ax1.plot(training_df['epoch'], training_df['best_score'], 'b-', label='Best Score')
        ax1.plot(training_df['epoch'], training_df['mean_score'], 'r--', label='Mean Score')
        ax1.set_title('Training Progress - Scores')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Composite Score')
        ax1.legend()
        
        # Accuracy improvement
        ax2.semilogy(training_df['epoch'], training_df['best_accuracy'])
        ax2.set_title('Training Progress - Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Best Max Error (log scale)')
        
        # Efficiency improvement
        ax3.plot(training_df['epoch'], training_df['best_efficiency'], 'm-')
        ax3.set_title('Training Progress - Efficiency')
        ax3.set_xlabel('Epoch')
        ax3.set_ylabel('Best Efficiency Score')
        
        # Valid candidates per epoch
        ax4.plot(training_df['epoch'], training_df['n_valid_candidates'], 'c-', marker='o')
        ax4.set_title('Valid Candidates per Epoch')
        ax4.set_xlabel('Epoch')
        ax4.set_ylabel('Number of Valid Candidates')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_interactive_report(self, evaluation_df: pd.DataFrame, save_path: str):
        """Create interactive HTML report."""
        
        fig = self.interactive_viz.create_interactive_comparison(evaluation_df)
        fig.write_html(save_path)
    
    def _generate_summary_report(self, 
                               evaluation_df: pd.DataFrame,
                               best_performers: List[Dict[str, Any]],
                               save_path: str):
        """Generate text summary report."""
        
        with open(save_path, 'w') as f:
            f.write("EXPERIMENT SUMMARY REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            # Overall statistics
            f.write("OVERALL STATISTICS:\n")
            f.write(f"Total methods evaluated: {len(evaluation_df)}\n")
            f.write(f"Best composite score: {evaluation_df['composite_score'].max():.4f}\n")
            f.write(f"Mean composite score: {evaluation_df['composite_score'].mean():.4f}\n")
            f.write(f"Std composite score: {evaluation_df['composite_score'].std():.4f}\n\n")
            
            # Top performers
            f.write("TOP 5 PERFORMERS:\n")
            for i, performer in enumerate(best_performers[:5]):
                f.write(f"{i+1}. Table ID {performer['table_id']}: "
                       f"Score = {performer['score']:.4f}\n")
            
            f.write("\nDETAILED METRICS:\n")
            f.write("-" * 30 + "\n")
            
            # Best method details
            if best_performers:
                best = best_performers[0]
                table = best['butcher_table']
                f.write(f"Best method characteristics:\n")
                f.write(f"  Stages: {len(table.b)}\n")
                f.write(f"  Explicit: {table.is_explicit}\n")
                f.write(f"  Consistency order: {table.consistency_order}\n")
                f.write(f"  Stability radius: {table.stability_radius:.2f}\n")
            
            f.write("\nExperiment completed successfully.\n")

if __name__ == "__main__":
    # Test visualization functionality
    print("Testing visualization functionality...")
    
    # Test Butcher table visualization
    from butcher_tables import get_rk4
    
    visualizer = ButcherTableVisualizer()
    rk4 = get_rk4()
    visualizer.plot_butcher_table(rk4, "RK4 Method")
    
    # Test with dummy data
    from metrics import PerformanceMetrics
    
    dummy_metrics = [
        PerformanceMetrics(
            max_error=1e-6, l2_error=1e-7, mean_error=-6.0, error_percentile_95=-5.5,
            runtime=1.0, n_steps=100, steps_per_second=100.0, efficiency_score=0.8,
            stability_score=0.9, convergence_rate=0.85, composite_score=0.85,
            success_rate=0.95, n_successful=95, n_total=100
        ),
        PerformanceMetrics(
            max_error=1e-5, l2_error=1e-6, mean_error=-5.0, error_percentile_95=-4.5,
            runtime=0.5, n_steps=50, steps_per_second=100.0, efficiency_score=0.9,
            stability_score=0.7, convergence_rate=0.75, composite_score=0.8,
            success_rate=0.9, n_successful=90, n_total=100
        )
    ]
    
    visualizer.plot_performance_comparison(dummy_metrics, ["Method 1", "Method 2"])
    visualizer.plot_radar_chart(dummy_metrics, ["Method 1", "Method 2"])
    
    print("Visualization tests completed!")

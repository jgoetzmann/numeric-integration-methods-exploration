#!/usr/bin/env python3
"""
Main analysis script for comprehensive butcher table evaluation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from analysis.butcher_analyzer import ButcherTableAnalyzer
from analysis.comparison_runner import ComparisonRunner
from analysis.results_generator import ResultsGenerator

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
    
    # Create comparison runner
    runner = ComparisonRunner()
    
    # Create test dataset
    print("Creating test dataset...")
    test_odes = runner.create_test_dataset(10000)
    
    # Run comprehensive comparison
    print("Running comprehensive comparison...")
    results_df = runner.run_comprehensive_comparison(
        unique_tables, 
        analyzer.classical_methods, 
        test_odes
    )
    
    # Normalize results
    print("Normalizing results...")
    results_df = runner.normalize_results(results_df)
    
    # Create results generator
    generator = ResultsGenerator()
    
    # Save CSV
    print("Saving results to CSV...")
    generator.save_results_csv(results_df)
    
    # Save butcher tables
    print("Saving butcher tables...")
    generator.save_butcher_tables_json(unique_tables)
    
    # Create visualizations
    print("Creating visualizations...")
    generator.create_visualizations(results_df)
    
    # Generate conclusion report
    print("Generating conclusion report...")
    duplicate_analysis = analyzer.analyze_duplicates()
    generator.generate_conclusion_report(results_df, unique_tables, duplicate_analysis)
    
    print(f"Analysis complete! Results saved to {generator.output_dir}")
    print(f"Summary: {len(unique_tables)} unique methods analyzed")
    
    # Print summary
    discovered_methods = results_df[results_df['type'] == 'discovered']
    if not discovered_methods.empty:
        composite_col = discovered_methods['composite_normalized'].dropna()
        if not composite_col.empty:
            best_overall = discovered_methods.loc[composite_col.idxmax()]
            print(f"Best overall performer: {best_overall['method']} (Score: {best_overall['composite_normalized']:.3f}x RK45)")
        else:
            print("No valid composite scores found for discovered methods")
    
    return results_df, unique_tables

if __name__ == "__main__":
    main()

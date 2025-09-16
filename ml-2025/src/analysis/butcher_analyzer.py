"""
Core butcher table analysis functionality.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

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
    
    def analyze_duplicates(self) -> str:
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

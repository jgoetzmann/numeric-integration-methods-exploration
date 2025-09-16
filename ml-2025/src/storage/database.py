"""
Database and Logging Module.

This module provides database functionality for storing and retrieving
Butcher table results, metrics, and training progress.
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import os
from dataclasses import asdict

from butcher_tables import ButcherTable
from metrics import PerformanceMetrics
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

class ResultsDatabase:
    """SQLite database for storing integration results and metrics."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables."""
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        self._create_butcher_tables()
        self._create_evaluations_table()
        self._create_training_epochs_table()
        self._create_ode_results_table()
        
        self.conn.commit()
    
    def _create_butcher_tables(self):
        """Create butcher_tables table."""
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS butcher_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_hash TEXT UNIQUE NOT NULL,
            stages INTEGER NOT NULL,
            is_explicit BOOLEAN NOT NULL,
            consistency_order INTEGER,
            stability_radius REAL,
            A_matrix TEXT NOT NULL,  -- JSON string
            b_vector TEXT NOT NULL,  -- JSON string
            c_vector TEXT NOT NULL,  -- JSON string
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.conn.execute(create_table_sql)
    
    def _create_evaluations_table(self):
        """Create evaluations table for storing performance metrics."""
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            butcher_table_id INTEGER NOT NULL,
            evaluation_name TEXT NOT NULL,
            max_error REAL,
            l2_error REAL,
            mean_error REAL,
            error_percentile_95 REAL,
            runtime REAL,
            n_steps INTEGER,
            steps_per_second REAL,
            efficiency_score REAL,
            stability_score REAL,
            convergence_rate REAL,
            composite_score REAL,
            success_rate REAL,
            n_successful INTEGER,
            n_total INTEGER,
            evaluation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (butcher_table_id) REFERENCES butcher_tables (id)
        )
        """
        self.conn.execute(create_table_sql)
    
    def _create_training_epochs_table(self):
        """Create training_epochs table for storing training progress."""
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS training_epochs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epoch INTEGER NOT NULL,
            n_valid_candidates INTEGER,
            best_score REAL,
            mean_score REAL,
            best_accuracy REAL,
            best_efficiency REAL,
            best_stability REAL,
            surrogate_loss REAL,
            training_method TEXT,  -- 'neural_network' or 'evolutionary'
            epoch_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.conn.execute(create_table_sql)
    
    def _create_ode_results_table(self):
        """Create ode_results table for storing individual ODE evaluation results."""
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ode_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            butcher_table_id INTEGER NOT NULL,
            ode_id INTEGER NOT NULL,
            ode_type TEXT NOT NULL,
            is_stiff BOOLEAN NOT NULL,
            success BOOLEAN NOT NULL,
            max_error REAL,
            l2_error REAL,
            runtime REAL,
            n_steps INTEGER,
            error_message TEXT,
            evaluation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (butcher_table_id) REFERENCES butcher_tables (id)
        )
        """
        self.conn.execute(create_table_sql)
    
    def store_butcher_table(self, butcher_table: ButcherTable) -> int:
        """Store a Butcher table and return its ID."""
        
        # Create hash for uniqueness check
        table_hash = self._hash_butcher_table(butcher_table)
        
        # Check if already exists
        cursor = self.conn.execute(
            "SELECT id FROM butcher_tables WHERE table_hash = ?",
            (table_hash,)
        )
        existing = cursor.fetchone()
        if existing:
            return existing[0]
        
        # Store new table
        cursor = self.conn.execute(
            """INSERT INTO butcher_tables 
               (table_hash, stages, is_explicit, consistency_order, stability_radius, 
                A_matrix, b_vector, c_vector)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                table_hash,
                len(butcher_table.b),
                butcher_table.is_explicit,
                butcher_table.consistency_order,
                butcher_table.stability_radius,
                json.dumps(butcher_table.A.tolist()),
                json.dumps(butcher_table.b.tolist()),
                json.dumps(butcher_table.c.tolist())
            )
        )
        
        self.conn.commit()
        return cursor.lastrowid
    
    def store_evaluation(self, 
                        butcher_table_id: int,
                        metrics: PerformanceMetrics,
                        evaluation_name: str = "default") -> int:
        """Store evaluation metrics for a Butcher table."""
        
        cursor = self.conn.execute(
            """INSERT INTO evaluations 
               (butcher_table_id, evaluation_name, max_error, l2_error, mean_error,
                error_percentile_95, runtime, n_steps, steps_per_second,
                efficiency_score, stability_score, convergence_rate, composite_score,
                success_rate, n_successful, n_total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                butcher_table_id,
                evaluation_name,
                metrics.max_error,
                metrics.l2_error,
                metrics.mean_error,
                metrics.error_percentile_95,
                metrics.runtime,
                metrics.n_steps,
                metrics.steps_per_second,
                metrics.efficiency_score,
                metrics.stability_score,
                metrics.convergence_rate,
                metrics.composite_score,
                metrics.success_rate,
                metrics.n_successful,
                metrics.n_total
            )
        )
        
        self.conn.commit()
        return cursor.lastrowid
    
    def store_training_epoch(self, epoch_data: Dict[str, Any]) -> int:
        """Store training epoch data."""
        
        cursor = self.conn.execute(
            """INSERT INTO training_epochs 
               (epoch, n_valid_candidates, best_score, mean_score, best_accuracy,
                best_efficiency, best_stability, surrogate_loss, training_method)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                epoch_data.get('epoch'),
                epoch_data.get('n_valid_candidates'),
                epoch_data.get('best_score'),
                epoch_data.get('mean_score'),
                epoch_data.get('best_accuracy'),
                epoch_data.get('best_efficiency'),
                epoch_data.get('best_stability'),
                epoch_data.get('surrogate_loss'),
                epoch_data.get('training_method', 'neural_network')
            )
        )
        
        self.conn.commit()
        return cursor.lastrowid
    
    def store_ode_result(self, 
                        butcher_table_id: int,
                        ode_id: int,
                        ode_type: str,
                        is_stiff: bool,
                        success: bool,
                        max_error: float = None,
                        l2_error: float = None,
                        runtime: float = None,
                        n_steps: int = None,
                        error_message: str = None) -> int:
        """Store individual ODE evaluation result."""
        
        cursor = self.conn.execute(
            """INSERT INTO ode_results 
               (butcher_table_id, ode_id, ode_type, is_stiff, success,
                max_error, l2_error, runtime, n_steps, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                butcher_table_id,
                ode_id,
                ode_type,
                is_stiff,
                success,
                max_error,
                l2_error,
                runtime,
                n_steps,
                error_message
            )
        )
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_butcher_table(self, table_id: int) -> Optional[ButcherTable]:
        """Retrieve a Butcher table by ID."""
        
        cursor = self.conn.execute(
            "SELECT * FROM butcher_tables WHERE id = ?",
            (table_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Reconstruct ButcherTable
        A = np.array(json.loads(row[6]))
        b = np.array(json.loads(row[7]))
        c = np.array(json.loads(row[8]))
        
        table = ButcherTable(A=A, b=b, c=c)
        table.consistency_order = row[4]
        table.stability_radius = row[5]
        table.is_explicit = bool(row[3])
        
        return table
    
    def get_best_performers(self, 
                           metric: str = 'composite_score',
                           limit: int = 10,
                           evaluation_name: str = 'default') -> List[Dict[str, Any]]:
        """Get the best performing Butcher tables."""
        
        query = f"""
        SELECT bt.*, e.{metric}, e.evaluation_name, e.evaluation_timestamp
        FROM butcher_tables bt
        JOIN evaluations e ON bt.id = e.butcher_table_id
        WHERE e.evaluation_name = ?
        ORDER BY e.{metric} DESC
        LIMIT ?
        """
        
        cursor = self.conn.execute(query, (evaluation_name, limit))
        results = []
        
        for row in cursor.fetchall():
            # Reconstruct ButcherTable
            table = self.get_butcher_table(row[0])
            
            results.append({
                'table_id': row[0],
                'butcher_table': table,
                'score': row[13],  # The metric value
                'evaluation_name': row[14],
                'timestamp': row[15]
            })
        
        return results
    
    def get_training_history(self, training_method: str = None) -> pd.DataFrame:
        """Get training history as DataFrame."""
        
        query = "SELECT * FROM training_epochs"
        params = []
        
        if training_method:
            query += " WHERE training_method = ?"
            params.append(training_method)
        
        query += " ORDER BY epoch"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df
    
    def get_evaluation_comparison(self, evaluation_name: str = 'default') -> pd.DataFrame:
        """Get comparison of all evaluations."""
        
        query = """
        SELECT bt.id, bt.stages, bt.is_explicit, bt.consistency_order,
               e.max_error, e.l2_error, e.runtime, e.n_steps,
               e.efficiency_score, e.stability_score, e.composite_score,
               e.success_rate, e.evaluation_timestamp
        FROM butcher_tables bt
        JOIN evaluations e ON bt.id = e.butcher_table_id
        WHERE e.evaluation_name = ?
        ORDER BY e.composite_score DESC
        """
        
        df = pd.read_sql_query(query, self.conn, params=(evaluation_name,))
        return df
    
    def get_ode_results_summary(self, butcher_table_id: int) -> Dict[str, Any]:
        """Get summary of ODE results for a specific Butcher table."""
        
        # Overall statistics
        cursor = self.conn.execute(
            """SELECT 
                COUNT(*) as total_odes,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_odes,
                AVG(CASE WHEN success THEN max_error ELSE NULL END) as avg_max_error,
                AVG(CASE WHEN success THEN runtime ELSE NULL END) as avg_runtime,
                AVG(CASE WHEN success THEN n_steps ELSE NULL END) as avg_n_steps
               FROM ode_results 
               WHERE butcher_table_id = ?""",
            (butcher_table_id,)
        )
        
        overall_stats = cursor.fetchone()
        
        # Statistics by ODE type
        cursor = self.conn.execute(
            """SELECT 
                ode_type,
                COUNT(*) as count,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                AVG(CASE WHEN success THEN max_error ELSE NULL END) as avg_error
               FROM ode_results 
               WHERE butcher_table_id = ?
               GROUP BY ode_type""",
            (butcher_table_id,)
        )
        
        type_stats = cursor.fetchall()
        
        # Statistics by stiffness
        cursor = self.conn.execute(
            """SELECT 
                is_stiff,
                COUNT(*) as count,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                AVG(CASE WHEN success THEN max_error ELSE NULL END) as avg_error
               FROM ode_results 
               WHERE butcher_table_id = ?
               GROUP BY is_stiff""",
            (butcher_table_id,)
        )
        
        stiffness_stats = cursor.fetchall()
        
        return {
            'overall': {
                'total_odes': overall_stats[0],
                'successful_odes': overall_stats[1],
                'success_rate': overall_stats[1] / overall_stats[0] if overall_stats[0] > 0 else 0,
                'avg_max_error': overall_stats[2],
                'avg_runtime': overall_stats[3],
                'avg_n_steps': overall_stats[4]
            },
            'by_type': [
                {'type': row[0], 'count': row[1], 'successful': row[2], 'avg_error': row[3]}
                for row in type_stats
            ],
            'by_stiffness': [
                {'is_stiff': bool(row[0]), 'count': row[1], 'successful': row[2], 'avg_error': row[3]}
                for row in stiffness_stats
            ]
        }
    
    def _hash_butcher_table(self, butcher_table: ButcherTable) -> str:
        """Create hash for Butcher table uniqueness."""
        
        # Create string representation
        table_str = f"{butcher_table.A.tobytes()}{butcher_table.b.tobytes()}{butcher_table.c.tobytes()}"
        
        # Simple hash
        return str(hash(table_str))
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class ExperimentLogger:
    """High-level logger for experiments."""
    
    def __init__(self, db_path: str = None):
        self.db = ResultsDatabase(db_path)
        self.current_experiment = None
    
    def start_experiment(self, experiment_name: str, description: str = "") -> str:
        """Start a new experiment."""
        
        self.current_experiment = experiment_name
        self.experiment_description = description
        self.experiment_start_time = datetime.now()
        
        print(f"Started experiment: {experiment_name}")
        if description:
            print(f"Description: {description}")
        
        return experiment_name
    
    def log_butcher_table_evaluation(self, 
                                   butcher_table: ButcherTable,
                                   metrics: PerformanceMetrics,
                                   ode_results: List[Dict[str, Any]] = None) -> int:
        """Log evaluation of a Butcher table."""
        
        # Store Butcher table
        table_id = self.db.store_butcher_table(butcher_table)
        
        # Store evaluation metrics
        eval_id = self.db.store_evaluation(
            table_id, metrics, self.current_experiment or "default"
        )
        
        # Store individual ODE results if provided
        if ode_results:
            for ode_result in ode_results:
                self.db.store_ode_result(
                    table_id,
                    ode_result.get('ode_id', 0),
                    ode_result.get('ode_type', 'unknown'),
                    ode_result.get('is_stiff', False),
                    ode_result.get('success', False),
                    ode_result.get('max_error'),
                    ode_result.get('l2_error'),
                    ode_result.get('runtime'),
                    ode_result.get('n_steps'),
                    ode_result.get('error_message')
                )
        
        return table_id
    
    def log_training_epoch(self, epoch_data: Dict[str, Any]):
        """Log training epoch data."""
        
        epoch_data['training_method'] = epoch_data.get('training_method', 'neural_network')
        self.db.store_training_epoch(epoch_data)
    
    def get_experiment_summary(self, experiment_name: str = None) -> Dict[str, Any]:
        """Get summary of experiment results."""
        
        exp_name = experiment_name or self.current_experiment
        
        # Get best performers
        best_performers = self.db.get_best_performers(
            metric='composite_score',
            limit=5,
            evaluation_name=exp_name
        )
        
        # Get training history
        training_history = self.db.get_training_history()
        
        # Get evaluation comparison
        evaluation_comparison = self.db.get_evaluation_comparison(exp_name)
        
        return {
            'experiment_name': exp_name,
            'best_performers': best_performers,
            'training_history': training_history,
            'evaluation_comparison': evaluation_comparison,
            'n_evaluations': len(evaluation_comparison)
        }
    
    def export_results(self, export_dir: str = None):
        """Export all results to CSV files."""
        
        export_dir = export_dir or config.RESULTS_DIR
        os.makedirs(export_dir, exist_ok=True)
        
        # Export training history
        training_df = self.db.get_training_history()
        training_df.to_csv(os.path.join(export_dir, 'training_history.csv'), index=False)
        
        # Export evaluation comparison
        eval_df = self.db.get_evaluation_comparison()
        eval_df.to_csv(os.path.join(export_dir, 'evaluation_comparison.csv'), index=False)
        
        print(f"Results exported to {export_dir}")

if __name__ == "__main__":
    # Test database functionality
    print("Testing database functionality...")
    
    # Create test database
    with ResultsDatabase(":memory:") as db:
        # Test Butcher table storage
        from butcher_tables import get_rk4
        
        rk4 = get_rk4()
        table_id = db.store_butcher_table(rk4)
        print(f"Stored RK4 with ID: {table_id}")
        
        # Test retrieval
        retrieved_table = db.get_butcher_table(table_id)
        print(f"Retrieved table: {retrieved_table is not None}")
        
        # Test evaluation storage
        from metrics import PerformanceMetrics
        
        test_metrics = PerformanceMetrics(
            max_error=1e-6,
            l2_error=1e-7,
            mean_error=-6.0,
            error_percentile_95=-5.5,
            runtime=1.0,
            n_steps=100,
            steps_per_second=100.0,
            efficiency_score=0.8,
            stability_score=0.9,
            convergence_rate=0.85,
            composite_score=0.85,
            success_rate=0.95,
            n_successful=95,
            n_total=100
        )
        
        eval_id = db.store_evaluation(table_id, test_metrics, "test_evaluation")
        print(f"Stored evaluation with ID: {eval_id}")
        
        # Test best performers query
        best_performers = db.get_best_performers(limit=5)
        print(f"Found {len(best_performers)} best performers")
    
    print("Database test completed successfully!")

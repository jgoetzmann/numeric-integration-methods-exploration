"""
Machine Learning Models Module.

This module implements the generator and surrogate evaluator models for
discovering novel Butcher tables through machine learning.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import random
from butcher_tables import ButcherTable, ButcherTableGenerator
from metrics import PerformanceMetrics
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

@dataclass
class ModelConfig:
    """Configuration for ML models."""
    
    # Generator model parameters
    generator_input_size: int = 128  # Random noise input
    generator_hidden_size: int = 256
    generator_output_size: int = 24  # For 4-stage explicit method (4*4+4+4=24)
    
    # Surrogate model parameters
    surrogate_input_size: int = 24  # Butcher table representation (4-stage: 4*4+4+4=24)
    surrogate_hidden_size: int = 128
    surrogate_output_size: int = 4  # [accuracy, efficiency, stability, composite]
    
    # Training parameters
    learning_rate: float = 1e-3
    batch_size: int = 32
    n_epochs: int = 100
    weight_decay: float = 1e-5

class ButcherTableGenerator(nn.Module):
    """Neural network generator for creating Butcher tables."""
    
    def __init__(self, config_obj: ModelConfig, stages: int = 4):
        super().__init__()
        self.config = config_obj
        self.stages = stages
        self.output_size = stages * stages + stages + stages  # A + b + c
        
        # Generator network
        self.network = nn.Sequential(
            nn.Linear(config_obj.generator_input_size, config_obj.generator_hidden_size),
            nn.ReLU(),
            nn.BatchNorm1d(config_obj.generator_hidden_size),
            
            nn.Linear(config_obj.generator_hidden_size, config_obj.generator_hidden_size),
            nn.ReLU(),
            nn.BatchNorm1d(config_obj.generator_hidden_size),
            
            nn.Linear(config_obj.generator_hidden_size, config_obj.generator_hidden_size // 2),
            nn.ReLU(),
            nn.BatchNorm1d(config_obj.generator_hidden_size // 2),
            
            nn.Linear(config_obj.generator_hidden_size // 2, self.output_size),
            nn.Tanh()  # Output in [-1, 1]
        )
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize network weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_normal_(module.weight)
                nn.init.zeros_(module.bias)
    
    def forward(self, noise: torch.Tensor) -> torch.Tensor:
        """Generate Butcher table from noise."""
        return self.network(noise)
    
    def generate_tables(self, n_tables: int, device: str = 'cpu') -> List[ButcherTable]:
        """Generate multiple Butcher tables."""
        self.eval()
        with torch.no_grad():
            noise = torch.randn(n_tables, self.config.generator_input_size, device=device)
            outputs = self.forward(noise)
            
            tables = []
            for i in range(n_tables):
                try:
                    table = ButcherTable.from_tensor(outputs[i], self.stages)
                    # Ensure explicit structure
                    if table.is_explicit:
                        tables.append(table)
                except:
                    # Skip invalid tables
                    continue
            
            return tables
    
    def generate_valid_tables(self, n_tables: int, device: str = 'cpu') -> List[ButcherTable]:
        """Generate valid Butcher tables, ensuring we get the requested number."""
        tables = []
        attempts = 0
        max_attempts = n_tables * 10  # Allow multiple attempts
        
        while len(tables) < n_tables and attempts < max_attempts:
            batch_size = min(32, n_tables - len(tables))
            new_tables = self.generate_tables(batch_size, device)
            tables.extend(new_tables)
            attempts += 1
        
        return tables[:n_tables]

class SurrogateEvaluator(nn.Module):
    """Neural network surrogate for predicting Butcher table performance."""
    
    def __init__(self, config_obj: ModelConfig):
        super().__init__()
        self.config = config_obj
        
        # Surrogate network
        self.network = nn.Sequential(
            nn.Linear(config_obj.surrogate_input_size, config_obj.surrogate_hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(config_obj.surrogate_hidden_size, config_obj.surrogate_hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(config_obj.surrogate_hidden_size, config_obj.surrogate_hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            
            nn.Linear(config_obj.surrogate_hidden_size // 2, config_obj.surrogate_output_size)
        )
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize network weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_normal_(module.weight)
                nn.init.zeros_(module.bias)
    
    def forward(self, butcher_table_tensor: torch.Tensor) -> torch.Tensor:
        """Predict performance metrics from Butcher table."""
        return self.network(butcher_table_tensor)

class EvolutionaryGenerator:
    """Evolutionary algorithm for generating Butcher tables."""
    
    def __init__(self, population_size: int = 100, mutation_rate: float = 0.1, config_obj: ModelConfig = None):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.config = config_obj or ModelConfig()
        from butcher_tables import ButcherTableGenerator as RandomGenerator
        self.generator = RandomGenerator()
        
    def initialize_population(self, stages: int = 4) -> List[ButcherTable]:
        """Initialize random population of Butcher tables."""
        population = []
        
        # Add some baseline methods
        from butcher_tables import get_rk4, get_rk45_dormand_prince
        if stages == 4:
            population.append(get_rk4())
        
        # Fill remaining with random methods
        while len(population) < self.population_size:
            table = self.generator.generate_random_explicit(stages)
            population.append(table)
        
        return population[:self.population_size]
    
    def evolve(self, 
               population: List[ButcherTable],
               fitness_scores: List[float],
               n_generations: int = 1) -> List[ButcherTable]:
        """Evolve population based on fitness scores."""
        
        new_population = []
        
        # Elitism: keep top performers
        elite_size = self.population_size // 10
        elite_indices = np.argsort(fitness_scores)[-elite_size:]
        for idx in elite_indices:
            new_population.append(population[idx])
        
        # Generate offspring
        while len(new_population) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_selection(population, fitness_scores)
            parent2 = self._tournament_selection(population, fitness_scores)
            
            # Crossover
            offspring = self._crossover(parent1, parent2)
            
            # Mutation
            if random.random() < self.mutation_rate:
                offspring = self._mutate(offspring)
            
            new_population.append(offspring)
        
        return new_population[:self.population_size]
    
    def _tournament_selection(self, 
                             population: List[ButcherTable],
                             fitness_scores: List[float],
                             tournament_size: int = 3) -> ButcherTable:
        """Tournament selection for choosing parents."""
        tournament_indices = random.sample(range(len(population)), tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx]
    
    def _crossover(self, parent1: ButcherTable, parent2: ButcherTable) -> ButcherTable:
        """Crossover two Butcher tables."""
        # Simple uniform crossover
        s = len(parent1.b)
        
        # Crossover A matrix
        A_new = np.zeros_like(parent1.A)
        for i in range(s):
            for j in range(s):
                if random.random() < 0.5:
                    A_new[i, j] = parent1.A[i, j]
                else:
                    A_new[i, j] = parent2.A[i, j]
        
        # Crossover b vector
        b_new = np.where(random.random() < 0.5, parent1.b, parent2.b)
        b_new = b_new / np.sum(b_new)  # Renormalize
        
        # Compute new c
        c_new = np.sum(A_new, axis=1)
        
        return ButcherTable(A=A_new, b=b_new, c=c_new)
    
    def _mutate(self, table: ButcherTable, mutation_strength: float = 0.1) -> ButcherTable:
        """Mutate a Butcher table."""
        s = len(table.b)
        
        # Mutate A matrix
        A_new = table.A.copy()
        for i in range(s):
            for j in range(i):  # Only lower triangular for explicit methods
                if random.random() < self.mutation_rate:
                    A_new[i, j] += np.random.normal(0, mutation_strength)
        
        # Mutate b vector
        b_new = table.b.copy()
        for i in range(s):
            if random.random() < self.mutation_rate:
                b_new[i] += np.random.normal(0, mutation_strength)
        
        # Ensure positive weights and renormalize
        b_new = np.maximum(b_new, 0.01)
        b_new = b_new / np.sum(b_new)
        
        # Compute new c
        c_new = np.sum(A_new, axis=1)
        
        return ButcherTable(A=A_new, b=b_new, c=c_new)

class MLPipeline:
    """Complete ML pipeline for discovering Butcher tables."""
    
    def __init__(self, model_config: ModelConfig = None):
        self.config = model_config or ModelConfig()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize models
        self.generator = ButcherTableGenerator(self.config).to(self.device)
        self.surrogate = SurrogateEvaluator(self.config).to(self.device)
        
        # Optimizers
        self.generator_optimizer = optim.Adam(
            self.generator.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        self.surrogate_optimizer = optim.Adam(
            self.surrogate.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        # Evolutionary generator as backup
        self.evolutionary_generator = EvolutionaryGenerator(config_obj=self.config)
        
        # Training data storage
        self.training_data = []
        self.surrogate_losses = []
    
    def train_surrogate(self, 
                       butcher_tables: List[ButcherTable],
                       metrics: List[PerformanceMetrics],
                       n_epochs: int = None):
        """Train the surrogate evaluator on collected data."""
        
        if len(butcher_tables) < 10:
            return  # Need sufficient data
        
        n_epochs = n_epochs or self.config.n_epochs
        
        # Prepare training data
        X = torch.stack([table.to_tensor() for table in butcher_tables]).float()
        
        # Normalize accuracy for surrogate training
        accuracy_scores = []
        for i in range(len(metrics)):
            max_error = max(metrics[i].max_error, 1e-16)
            accuracy_score = 1.0 / (1.0 + np.log10(max_error))
            accuracy_score = max(0.0, min(1.0, accuracy_score))
            accuracy_scores.append(accuracy_score)
        
        y = torch.stack([torch.tensor([
            accuracy_scores[i],
            metrics[i].efficiency_score,
            metrics[i].stability_score,
            metrics[i].composite_score
        ], dtype=torch.float32) for i in range(len(metrics))])
        
        # Normalize targets
        y_mean = y.mean(dim=0)
        y_std = y.std(dim=0) + 1e-8
        y_normalized = (y - y_mean) / y_std
        
        # Create data loader
        dataset = torch.utils.data.TensorDataset(X, y_normalized)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=True
        )
        
        # Training loop
        self.surrogate.train()
        for epoch in range(n_epochs):
            epoch_loss = 0.0
            for batch_X, batch_y in dataloader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                self.surrogate_optimizer.zero_grad()
                predictions = self.surrogate(batch_X)
                loss = nn.MSELoss()(predictions, batch_y)
                loss.backward()
                self.surrogate_optimizer.step()
                
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(dataloader)
            self.surrogate_losses.append(avg_loss)
            
            if epoch % 10 == 0:
                print(f"Surrogate epoch {epoch}, loss: {avg_loss:.6f}")
    
    def predict_performance(self, butcher_tables: List[ButcherTable]) -> List[torch.Tensor]:
        """Predict performance using the surrogate model."""
        self.surrogate.eval()
        
        predictions = []
        with torch.no_grad():
            for table in butcher_tables:
                table_tensor = table.to_tensor().unsqueeze(0).to(self.device)
                pred = self.surrogate(table_tensor)
                predictions.append(pred.squeeze(0))
        
        return predictions
    
    def generate_candidates(self, 
                           n_candidates: int,
                           use_evolution: bool = False,
                           stages: int = 4) -> List[ButcherTable]:
        """Generate candidate Butcher tables."""
        
        if use_evolution:
            # Use evolutionary approach
            if not hasattr(self, 'evolutionary_population'):
                self.evolutionary_population = self.evolutionary_generator.initialize_population(stages)
            
            # Generate candidates through evolution
            candidates = self.evolutionary_population[:n_candidates]
        else:
            # Use neural network generator
            candidates = self.generator.generate_valid_tables(n_candidates, self.device)
            
            # Fill with random if not enough generated
            while len(candidates) < n_candidates:
                from butcher_tables import ButcherTableGenerator as RandomGenerator
                random_generator = RandomGenerator()
                random_table = random_generator.generate_random_explicit(stages)
                candidates.append(random_table)
        
        return candidates[:n_candidates]
    
    def update_training_data(self, 
                           butcher_tables: List[ButcherTable],
                           metrics: List[PerformanceMetrics]):
        """Update training data for surrogate model."""
        
        for table, metric in zip(butcher_tables, metrics):
            self.training_data.append({
                'table': table,
                'metrics': metric
            })
        
        # Keep only recent data to avoid memory issues
        max_data_size = 10000
        if len(self.training_data) > max_data_size:
            self.training_data = self.training_data[-max_data_size:]
    
    def save_models(self, checkpoint_dir: str):
        """Save model checkpoints."""
        import os
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        torch.save({
            'generator_state_dict': self.generator.state_dict(),
            'surrogate_state_dict': self.surrogate.state_dict(),
            'generator_optimizer': self.generator_optimizer.state_dict(),
            'surrogate_optimizer': self.surrogate_optimizer.state_dict(),
            'config': self.config
        }, os.path.join(checkpoint_dir, 'ml_pipeline.pth'))
        
        print(f"Saved models to {checkpoint_dir}")
    
    def load_models(self, checkpoint_path: str):
        """Load model checkpoints."""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        self.generator.load_state_dict(checkpoint['generator_state_dict'])
        self.surrogate.load_state_dict(checkpoint['surrogate_state_dict'])
        self.generator_optimizer.load_state_dict(checkpoint['generator_optimizer'])
        self.surrogate_optimizer.load_state_dict(checkpoint['surrogate_optimizer'])
        
        print(f"Loaded models from {checkpoint_path}")

if __name__ == "__main__":
    # Test the ML models
    print("Testing ML models...")
    
    # Test generator
    config_obj = ModelConfig()
    generator = ButcherTableGenerator(config_obj)
    
    # Generate some tables
    tables = generator.generate_valid_tables(5)
    print(f"Generated {len(tables)} Butcher tables")
    
    # Test surrogate
    surrogate = SurrogateEvaluator(config_obj)
    
    if len(tables) > 0:
        table_tensor = tables[0].to_tensor().unsqueeze(0)
        prediction = surrogate(table_tensor)
        print(f"Surrogate prediction shape: {prediction.shape}")
    
    # Test evolutionary generator
    evo_gen = EvolutionaryGenerator()
    population = evo_gen.initialize_population(4)
    print(f"Evolutionary population size: {len(population)}")
    
    # Test crossover and mutation
    if len(population) >= 2:
        offspring = evo_gen._crossover(population[0], population[1])
        mutated = evo_gen._mutate(offspring)
        print(f"Crossover and mutation successful")
    
    print("ML models test completed.")

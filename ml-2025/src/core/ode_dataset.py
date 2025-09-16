"""
ODE Dataset Generation and Management Module.

This module generates a collection of 10,000 static ODEs (mix of stiff and non-stiff)
and provides batching functionality for training.
"""

import numpy as np
import pickle
import os
from typing import List, Tuple, Dict, Any, Iterator
from dataclasses import dataclass
import random
import warnings
from tqdm import tqdm
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

# Suppress numerical warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', message='.*overflow.*')
warnings.filterwarnings('ignore', message='.*invalid value.*')
warnings.filterwarnings('ignore', message='.*Casting complex values.*')
warnings.filterwarnings('ignore', message='.*ComplexWarning.*')

@dataclass
class ODEParameters:
    """Parameters defining a specific ODE instance."""
    ode_id: int
    is_stiff: bool
    equation_type: str
    parameters: Dict[str, Any]
    initial_conditions: np.ndarray
    t_span: Tuple[float, float]

class ODEGenerator:
    """Generates various types of ODEs for testing integration methods."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)
        self.generated_odes = []  # Track generated ODEs
        
    def generate_linear_system(self, n: int, stiffness_ratio: float = 1.0) -> ODEParameters:
        """Generate a linear system of ODEs."""
        # Create matrix A with specified stiffness ratio
        A = np.random.randn(n, n)
        # Make eigenvalues more negative for stiffness
        eigenvals, eigenvecs = np.linalg.eig(A)
        if stiffness_ratio > 1:
            # Sort eigenvalues and make some very negative
            eigenvals = np.sort(eigenvals.real)
            n_stiff = max(1, n // 4)  # Make 1/4 of eigenvalues stiff
            eigenvals[:n_stiff] *= -stiffness_ratio * 10
            A = eigenvecs @ np.diag(eigenvals) @ np.linalg.inv(eigenvecs)
        
        x0 = np.random.randn(n)
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=stiffness_ratio > 10,
            equation_type="linear_system",
            parameters={"A": A, "n": n},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_van_der_pol(self, mu: float) -> ODEParameters:
        """Generate Van der Pol oscillator."""
        is_stiff = mu > 10
        x0 = np.array([2.0, 0.0])  # Standard initial conditions
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="van_der_pol",
            parameters={"mu": mu},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_lotka_volterra(self, alpha: float, beta: float, gamma: float, delta: float) -> ODEParameters:
        """Generate Lotka-Volterra predator-prey equations."""
        x0 = np.array([alpha / gamma, beta / delta])  # Equilibrium point
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=False,
            equation_type="lotka_volterra",
            parameters={"alpha": alpha, "beta": beta, "gamma": gamma, "delta": delta},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_brusselator(self, a: float, b: float) -> ODEParameters:
        """Generate Brusselator reaction-diffusion system."""
        is_stiff = b > 3.0  # Becomes stiff for large b
        x0 = np.array([a, b / a])  # Equilibrium point
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="brusselator",
            parameters={"a": a, "b": b},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_polynomial_ode(self, degree: int, stiffness: float = 1.0) -> ODEParameters:
        """Generate polynomial ODE: dy/dt = P(y)."""
        # Random polynomial coefficients
        coeffs = np.random.randn(degree + 1) * stiffness
        x0 = np.random.randn(1)
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=stiffness > 5.0,
            equation_type="polynomial",
            parameters={"coefficients": coeffs, "degree": degree},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )

class ODEDataset:
    """Manages the collection of ODEs and provides batching functionality."""
    
    def __init__(self, config_obj=None):
        self.config = config_obj or config
        self.generated_odes = []
        self.reference_solutions = {}
        self.dataset_file = os.path.join(self.config.DATA_DIR, "ode_dataset.pkl")
        
    def generate_dataset(self, force_regenerate: bool = False):
        """Generate the full dataset of ODEs."""
        if os.path.exists(self.dataset_file) and not force_regenerate:
            print("Loading existing ODE dataset...")
            self.load_dataset()
            return
            
        print(f"Generating {self.config.N_ODES} ODEs...")
        generator = ODEGenerator()
        
        # Generate stiff ODEs
        print(f"Generating {self.config.N_STIFF_ODES} stiff ODEs...")
        for i in tqdm(range(self.config.N_STIFF_ODES), desc="Generating stiff ODEs"):
            if i % 4 == 0:
                # Linear systems with high stiffness
                stiffness_ratio = np.random.uniform(10, 100)
                ode = generator.generate_linear_system(
                    n=np.random.randint(2, 6), 
                    stiffness_ratio=stiffness_ratio
                )
            elif i % 4 == 1:
                # Van der Pol with large mu
                mu = np.random.uniform(10, 50)
                ode = generator.generate_van_der_pol(mu)
            elif i % 4 == 2:
                # Brusselator with large b
                a = np.random.uniform(1, 3)
                b = np.random.uniform(3, 10)
                ode = generator.generate_brusselator(a, b)
            else:
                # High-degree polynomial with high stiffness
                degree = np.random.randint(3, 6)
                stiffness = np.random.uniform(5, 20)
                ode = generator.generate_polynomial_ode(degree, stiffness)
            
            self.generated_odes.append(ode)
        
        # Generate non-stiff ODEs
        print(f"Generating {self.config.N_NONSTIFF_ODES} non-stiff ODEs...")
        for i in tqdm(range(self.config.N_NONSTIFF_ODES), desc="Generating non-stiff ODEs"):
            if i % 5 == 0:
                # Linear systems with low stiffness
                stiffness_ratio = np.random.uniform(0.1, 2.0)
                ode = generator.generate_linear_system(
                    n=np.random.randint(2, 5), 
                    stiffness_ratio=stiffness_ratio
                )
            elif i % 5 == 1:
                # Van der Pol with small mu
                mu = np.random.uniform(0.1, 2.0)
                ode = generator.generate_van_der_pol(mu)
            elif i % 5 == 2:
                # Lotka-Volterra
                alpha = np.random.uniform(1, 3)
                beta = np.random.uniform(1, 3)
                gamma = np.random.uniform(1, 3)
                delta = np.random.uniform(1, 3)
                ode = generator.generate_lotka_volterra(alpha, beta, gamma, delta)
            elif i % 5 == 3:
                # Brusselator with small b
                a = np.random.uniform(1, 3)
                b = np.random.uniform(1, 3)
                ode = generator.generate_brusselator(a, b)
            else:
                # Low-degree polynomial with low stiffness
                degree = np.random.randint(2, 4)
                stiffness = np.random.uniform(0.1, 2.0)
                ode = generator.generate_polynomial_ode(degree, stiffness)
            
            self.generated_odes.append(ode)
        
        # Shuffle the dataset
        random.shuffle(self.generated_odes)
        
        # Reassign IDs
        for i, ode in enumerate(self.generated_odes):
            ode.ode_id = i
            
        print(f"Generated {len(self.generated_odes)} ODEs")
        self.save_dataset()
    
    def get_batch(self, batch_size: int = None) -> List[ODEParameters]:
        """Get a random batch of ODEs for training."""
        if batch_size is None:
            batch_size = self.config.BATCH_SIZE
            
        return random.sample(self.generated_odes, min(batch_size, len(self.generated_odes)))
    
    def get_stiff_batch(self, batch_size: int = None) -> List[ODEParameters]:
        """Get a batch of stiff ODEs."""
        if batch_size is None:
            batch_size = self.config.BATCH_SIZE // 3
            
        stiff_odes = [ode for ode in self.generated_odes if ode.is_stiff]
        return random.sample(stiff_odes, min(batch_size, len(stiff_odes)))
    
    def get_nonstiff_batch(self, batch_size: int = None) -> List[ODEParameters]:
        """Get a batch of non-stiff ODEs."""
        if batch_size is None:
            batch_size = self.config.BATCH_SIZE * 2 // 3
            
        nonstiff_odes = [ode for ode in self.generated_odes if not ode.is_stiff]
        return random.sample(nonstiff_odes, min(batch_size, len(nonstiff_odes)))
    
    def save_dataset(self):
        """Save the dataset to disk."""
        with open(self.dataset_file, 'wb') as f:
            pickle.dump(self.generated_odes, f)
        print(f"Saved dataset to {self.dataset_file}")
    
    def load_dataset(self):
        """Load the dataset from disk."""
        with open(self.dataset_file, 'rb') as f:
            self.generated_odes = pickle.load(f)
        print(f"Loaded {len(self.generated_odes)} ODEs from {self.dataset_file}")
    
    def __len__(self):
        return len(self.generated_odes)
    
    def __getitem__(self, idx):
        return self.generated_odes[idx]

# ODE function implementations
def linear_system_ode(t: float, y: np.ndarray, A: np.ndarray) -> np.ndarray:
    """Linear system: dy/dt = A*y."""
    return A @ y

def van_der_pol_ode(t: float, y: np.ndarray, mu: float) -> np.ndarray:
    """Van der Pol oscillator: d²x/dt² - μ(1-x²)dx/dt + x = 0."""
    x, v = y
    return np.array([v, mu * (1 - x**2) * v - x])

def lotka_volterra_ode(t: float, y: np.ndarray, alpha: float, beta: float, gamma: float, delta: float) -> np.ndarray:
    """Lotka-Volterra predator-prey equations."""
    x, y_pred = y
    dx_dt = alpha * x - beta * x * y_pred
    dy_dt = delta * x * y_pred - gamma * y_pred
    return np.array([dx_dt, dy_dt])

def brusselator_ode(t: float, y: np.ndarray, a: float, b: float) -> np.ndarray:
    """Brusselator reaction-diffusion system."""
    x, y_chem = y
    dx_dt = a - (b + 1) * x + x**2 * y_chem
    dy_dt = b * x - x**2 * y_chem
    return np.array([dx_dt, dy_dt])

def polynomial_ode(t: float, y: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    """Polynomial ODE: dy/dt = P(y)."""
    y_val = y[0]
    result = 0.0
    for i, coeff in enumerate(coefficients):
        result += coeff * (y_val ** i)
    return np.array([result])

# ODE function mapping
ODE_FUNCTIONS = {
    "linear_system": linear_system_ode,
    "van_der_pol": van_der_pol_ode,
    "lotka_volterra": lotka_volterra_ode,
    "brusselator": brusselator_ode,
    "polynomial": polynomial_ode
}

if __name__ == "__main__":
    # Test the dataset generation
    dataset = ODEDataset()
    dataset.generate_dataset(force_regenerate=True)
    
    # Test batching
    batch = dataset.get_batch(10)
    print(f"Got batch of {len(batch)} ODEs")
    
    stiff_batch = dataset.get_stiff_batch(5)
    print(f"Got {len(stiff_batch)} stiff ODEs")
    
    nonstiff_batch = dataset.get_nonstiff_batch(5)
    print(f"Got {len(nonstiff_batch)} non-stiff ODEs")

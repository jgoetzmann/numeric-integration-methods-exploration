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
    
    def __init__(self, seed: int = 42, complexity_level: int = 1):
        self.seed = seed
        self.complexity_level = complexity_level
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
    
    def generate_robertson_system(self, k1: float, k2: float, k3: float) -> ODEParameters:
        """Generate Robertson's chemical reaction system (extremely stiff)."""
        is_stiff = k1 > 1e4 or k2 > 1e7 or k3 > 1e4
        x0 = np.array([1.0, 0.0, 0.0])  # Standard initial conditions
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="robertson",
            parameters={"k1": k1, "k2": k2, "k3": k3},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_oregonator(self, alpha: float, beta: float, gamma: float) -> ODEParameters:
        """Generate Oregonator (Belousov-Zhabotinsky reaction) system."""
        is_stiff = alpha > 10 or beta > 10 or gamma > 10
        x0 = np.array([1.0, 1.0, 1.0])
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="oregonator",
            parameters={"alpha": alpha, "beta": beta, "gamma": gamma},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_hindmarsh_rose(self, a: float, b: float, c: float, d: float, r: float, s: float, xr: float) -> ODEParameters:
        """Generate Hindmarsh-Rose neuron model (chaotic dynamics)."""
        is_stiff = abs(a) > 5 or abs(b) > 5
        x0 = np.array([0.0, 0.0, 0.0])
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="hindmarsh_rose",
            parameters={"a": a, "b": b, "c": c, "d": d, "r": r, "s": s, "xr": xr},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_lorenz_system(self, sigma: float, rho: float, beta: float) -> ODEParameters:
        """Generate Lorenz system (chaotic attractor)."""
        is_stiff = abs(sigma) > 20 or abs(rho) > 50 or abs(beta) > 10
        x0 = np.array([1.0, 1.0, 1.0])
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="lorenz",
            parameters={"sigma": sigma, "rho": rho, "beta": beta},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_kuramoto_sivashinsky(self, n_modes: int, viscosity: float) -> ODEParameters:
        """Generate Kuramoto-Sivashinsky equation (PDE discretized)."""
        is_stiff = viscosity < 0.1
        # Initial condition as random Fourier modes
        x0 = np.random.randn(n_modes) * 0.1
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=is_stiff,
            equation_type="kuramoto_sivashinsky",
            parameters={"n_modes": n_modes, "viscosity": viscosity},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )
    
    def generate_enhanced_linear_system(self, n: int, stiffness_ratio: float = 1.0) -> ODEParameters:
        """Generate enhanced linear system with more complex dynamics."""
        # Create matrix A with specified stiffness ratio and complexity
        A = np.random.randn(n, n)
        
        # Add complexity based on complexity level
        if self.complexity_level > 1:
            # Add non-normal effects (non-commuting matrices)
            B = np.random.randn(n, n) * 0.1
            A = A + B
            
        if self.complexity_level > 2:
            # Add time-dependent terms
            A = A * (1 + 0.1 * np.random.randn())
        
        # Make eigenvalues more negative for stiffness
        eigenvals, eigenvecs = np.linalg.eig(A)
        if stiffness_ratio > 1:
            eigenvals = np.sort(eigenvals.real)
            n_stiff = max(1, n // 3)  # Make 1/3 of eigenvalues stiff
            eigenvals[:n_stiff] *= -stiffness_ratio * (10 ** self.complexity_level)
            A = eigenvecs @ np.diag(eigenvals) @ np.linalg.inv(eigenvecs)
        
        x0 = np.random.randn(n)
        
        return ODEParameters(
            ode_id=len(self.generated_odes),
            is_stiff=stiffness_ratio > 10,
            equation_type="enhanced_linear_system",
            parameters={"A": A, "n": n, "complexity_level": self.complexity_level},
            initial_conditions=x0,
            t_span=(config.T_START, config.T_END)
        )

class ODEDataset:
    """Manages the collection of ODEs and provides batching functionality."""
    
    def __init__(self, config_obj=None, complexity_level: int = 1, trial_id: str = "default"):
        self.config = config_obj or config
        self.complexity_level = complexity_level
        self.trial_id = trial_id
        self.generated_odes = []
        self.reference_solutions = {}
        # Create trial-specific dataset file
        self.dataset_file = os.path.join(self.config.DATA_DIR, f"ode_dataset_{trial_id}_complexity_{complexity_level}.pkl")
        
    def generate_dataset(self, force_regenerate: bool = False):
        """Generate the full dataset of ODEs with increasing complexity."""
        if os.path.exists(self.dataset_file) and not force_regenerate:
            print(f"Loading existing ODE dataset for trial {self.trial_id}, complexity {self.complexity_level}...")
            self.load_dataset()
            return
            
        print(f"Generating {self.config.N_ODES} ODEs for trial {self.trial_id} (complexity level {self.complexity_level})...")
        generator = ODEGenerator(seed=42 + self.complexity_level * 100 + hash(self.trial_id) % 1000, 
                               complexity_level=self.complexity_level)
        
        # Generate stiff ODEs with increasing complexity
        print(f"Generating {self.config.N_STIFF_ODES} stiff ODEs...")
        for i in tqdm(range(self.config.N_STIFF_ODES), desc="Generating stiff ODEs"):
            ode_type = i % 8  # More variety
            
            if ode_type == 0:
                # Enhanced linear systems with high stiffness
                stiffness_ratio = np.random.uniform(10 * self.complexity_level, 100 * self.complexity_level)
                ode = generator.generate_enhanced_linear_system(
                    n=np.random.randint(2, 4 + self.complexity_level), 
                    stiffness_ratio=stiffness_ratio
                )
            elif ode_type == 1:
                # Van der Pol with large mu
                mu = np.random.uniform(10 * self.complexity_level, 50 * self.complexity_level)
                ode = generator.generate_van_der_pol(mu)
            elif ode_type == 2:
                # Brusselator with large b
                a = np.random.uniform(1, 3)
                b = np.random.uniform(3 * self.complexity_level, 10 * self.complexity_level)
                ode = generator.generate_brusselator(a, b)
            elif ode_type == 3:
                # Robertson's chemical reaction system (extremely stiff)
                k1 = np.random.uniform(1e4, 1e6)
                k2 = np.random.uniform(1e7, 1e9)
                k3 = np.random.uniform(1e4, 1e6)
                ode = generator.generate_robertson_system(k1, k2, k3)
            elif ode_type == 4:
                # Oregonator (Belousov-Zhabotinsky reaction)
                alpha = np.random.uniform(10 * self.complexity_level, 50 * self.complexity_level)
                beta = np.random.uniform(10 * self.complexity_level, 50 * self.complexity_level)
                gamma = np.random.uniform(10 * self.complexity_level, 50 * self.complexity_level)
                ode = generator.generate_oregonator(alpha, beta, gamma)
            elif ode_type == 5:
                # High-degree polynomial with high stiffness
                degree = np.random.randint(3 + self.complexity_level, 6 + self.complexity_level)
                stiffness = np.random.uniform(5 * self.complexity_level, 20 * self.complexity_level)
                ode = generator.generate_polynomial_ode(degree, stiffness)
            elif ode_type == 6:
                # Lorenz system (chaotic)
                sigma = np.random.uniform(10, 20 * self.complexity_level)
                rho = np.random.uniform(20, 50 * self.complexity_level)
                beta = np.random.uniform(2, 10 * self.complexity_level)
                ode = generator.generate_lorenz_system(sigma, rho, beta)
            else:  # ode_type == 7
                # Kuramoto-Sivashinsky (PDE discretized)
                n_modes = np.random.randint(3, 5 + self.complexity_level)
                viscosity = np.random.uniform(0.01, 0.1 / self.complexity_level)
                ode = generator.generate_kuramoto_sivashinsky(n_modes, viscosity)
            
            self.generated_odes.append(ode)
        
        # Generate non-stiff ODEs with increasing complexity
        print(f"Generating {self.config.N_NONSTIFF_ODES} non-stiff ODEs...")
        for i in tqdm(range(self.config.N_NONSTIFF_ODES), desc="Generating non-stiff ODEs"):
            ode_type = i % 8  # More variety
            
            if ode_type == 0:
                # Enhanced linear systems with low stiffness
                stiffness_ratio = np.random.uniform(0.1, 2.0)
                ode = generator.generate_enhanced_linear_system(
                    n=np.random.randint(2, 4 + self.complexity_level), 
                    stiffness_ratio=stiffness_ratio
                )
            elif ode_type == 1:
                # Van der Pol with small mu
                mu = np.random.uniform(0.1, 2.0)
                ode = generator.generate_van_der_pol(mu)
            elif ode_type == 2:
                # Lotka-Volterra
                alpha = np.random.uniform(1, 3)
                beta = np.random.uniform(1, 3)
                gamma = np.random.uniform(1, 3)
                delta = np.random.uniform(1, 3)
                ode = generator.generate_lotka_volterra(alpha, beta, gamma, delta)
            elif ode_type == 3:
                # Brusselator with small b
                a = np.random.uniform(1, 3)
                b = np.random.uniform(1, 3)
                ode = generator.generate_brusselator(a, b)
            elif ode_type == 4:
                # Robertson's chemical reaction system (non-stiff version)
                k1 = np.random.uniform(1e2, 1e4)
                k2 = np.random.uniform(1e5, 1e7)
                k3 = np.random.uniform(1e2, 1e4)
                ode = generator.generate_robertson_system(k1, k2, k3)
            elif ode_type == 5:
                # Oregonator (non-stiff version)
                alpha = np.random.uniform(1, 10)
                beta = np.random.uniform(1, 10)
                gamma = np.random.uniform(1, 10)
                ode = generator.generate_oregonator(alpha, beta, gamma)
            elif ode_type == 6:
                # Low-degree polynomial with low stiffness
                degree = np.random.randint(2, 4)
                stiffness = np.random.uniform(0.1, 2.0)
                ode = generator.generate_polynomial_ode(degree, stiffness)
            else:  # ode_type == 7
                # Hindmarsh-Rose neuron model
                a = np.random.uniform(1, 5)
                b = np.random.uniform(1, 5)
                c = np.random.uniform(1, 5)
                d = np.random.uniform(1, 5)
                r = np.random.uniform(0.001, 0.01)
                s = np.random.uniform(1, 5)
                xr = np.random.uniform(-2, 2)
                ode = generator.generate_hindmarsh_rose(a, b, c, d, r, s, xr)
            
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

def robertson_ode(t: float, y: np.ndarray, k1: float, k2: float, k3: float) -> np.ndarray:
    """Robertson's chemical reaction system: dy1/dt = -k1*y1 + k3*y2*y3, dy2/dt = k1*y1 - k2*y2^2 - k3*y2*y3, dy3/dt = k2*y2^2."""
    y1, y2, y3 = y
    dy1_dt = -k1 * y1 + k3 * y2 * y3
    dy2_dt = k1 * y1 - k2 * y2**2 - k3 * y2 * y3
    dy3_dt = k2 * y2**2
    return np.array([dy1_dt, dy2_dt, dy3_dt])

def oregonator_ode(t: float, y: np.ndarray, alpha: float, beta: float, gamma: float) -> np.ndarray:
    """Oregonator (Belousov-Zhabotinsky reaction): dx/dt = alpha*(y - x*y + x - beta*x^2), dy/dt = (gamma*z - y - x*y)/alpha, dz/dt = x - z."""
    x, y, z = y
    dx_dt = alpha * (y - x * y + x - beta * x**2)
    dy_dt = (gamma * z - y - x * y) / alpha
    dz_dt = x - z
    return np.array([dx_dt, dy_dt, dz_dt])

def hindmarsh_rose_ode(t: float, y: np.ndarray, a: float, b: float, c: float, d: float, r: float, s: float, xr: float) -> np.ndarray:
    """Hindmarsh-Rose neuron model: dx/dt = y - a*x^3 + b*x^2 - z + I, dy/dt = c - d*x^2 - y, dz/dt = r*(s*(x - xr) - z)."""
    x, y, z = y
    I = 3.0  # External current
    dx_dt = y - a * x**3 + b * x**2 - z + I
    dy_dt = c - d * x**2 - y
    dz_dt = r * (s * (x - xr) - z)
    return np.array([dx_dt, dy_dt, dz_dt])

def lorenz_ode(t: float, y: np.ndarray, sigma: float, rho: float, beta: float) -> np.ndarray:
    """Lorenz system: dx/dt = sigma*(y - x), dy/dt = x*(rho - z) - y, dz/dt = x*y - beta*z."""
    x, y, z = y
    dx_dt = sigma * (y - x)
    dy_dt = x * (rho - z) - y
    dz_dt = x * y - beta * z
    return np.array([dx_dt, dy_dt, dz_dt])

def kuramoto_sivashinsky_ode(t: float, y: np.ndarray, n_modes: int, viscosity: float) -> np.ndarray:
    """Kuramoto-Sivashinsky equation (discretized): du/dt = -u*du/dx - d^2u/dx^2 - d^4u/dx^4."""
    # Simplified discretized version
    u = y
    n = len(u)
    dx = 2 * np.pi / n
    
    # Compute derivatives using finite differences
    du_dx = np.gradient(u, dx)
    d2u_dx2 = np.gradient(du_dx, dx)
    d4u_dx4 = np.gradient(np.gradient(d2u_dx2, dx), dx)
    
    # Kuramoto-Sivashinsky equation
    du_dt = -u * du_dx - d2u_dx2 - viscosity * d4u_dx4
    return du_dt

def enhanced_linear_system_ode(t: float, y: np.ndarray, A: np.ndarray, complexity_level: int = 1) -> np.ndarray:
    """Enhanced linear system: dy/dt = A*y + complexity_terms."""
    base_term = A @ y
    
    if complexity_level > 1:
        # Add non-linear terms
        nonlin_term = 0.1 * np.sin(y) * np.cos(y)
        base_term += nonlin_term
    
    if complexity_level > 2:
        # Add time-dependent terms
        time_term = 0.05 * np.sin(t) * y
        base_term += time_term
    
    return base_term

# ODE function mapping
ODE_FUNCTIONS = {
    "linear_system": linear_system_ode,
    "van_der_pol": van_der_pol_ode,
    "lotka_volterra": lotka_volterra_ode,
    "brusselator": brusselator_ode,
    "polynomial": polynomial_ode,
    "robertson": robertson_ode,
    "oregonator": oregonator_ode,
    "hindmarsh_rose": hindmarsh_rose_ode,
    "lorenz": lorenz_ode,
    "kuramoto_sivashinsky": kuramoto_sivashinsky_ode,
    "enhanced_linear_system": enhanced_linear_system_ode
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

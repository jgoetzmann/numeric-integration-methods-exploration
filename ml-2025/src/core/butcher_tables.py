"""
Butcher Table Representation and Management Module.

This module handles the representation, validation, and manipulation of Butcher tables
for Runge-Kutta integration schemes.
"""

import numpy as np
import torch
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from configs.base import config

@dataclass
class ButcherTable:
    """Represents a Butcher table for Runge-Kutta methods."""
    
    A: np.ndarray  # Coefficient matrix (s×s)
    b: np.ndarray  # Weight vector (s entries)
    c: np.ndarray  # Node vector (s entries)
    
    def __post_init__(self):
        """Validate the Butcher table after initialization."""
        self.validate()
        self.compute_consistency()
    
    def validate(self):
        """Validate the Butcher table structure."""
        s = len(self.b)
        
        # Check dimensions
        assert self.A.shape == (s, s), f"A matrix must be {s}×{s}, got {self.A.shape}"
        assert self.b.shape == (s,), f"b vector must have {s} elements, got {len(self.b)}"
        assert self.c.shape == (s,), f"c vector must have {s} elements, got {len(self.c)}"
        
        # Check if explicit (lower triangular with zero diagonal) or implicit
        self.is_explicit = self._is_explicit()
        
        # Basic consistency checks
        if not np.allclose(np.sum(self.b), 1.0, atol=1e-10):
            raise ValueError("Sum of weights b must equal 1.0")
    
    def _is_explicit(self) -> bool:
        """Check if this is an explicit method."""
        # Explicit methods have zero diagonal and upper triangular part
        upper_tri = np.triu(self.A, k=1)
        diagonal = np.diag(self.A)
        return np.allclose(upper_tri, 0.0) and np.allclose(diagonal, 0.0)
    
    def compute_consistency(self):
        """Compute consistency order and other properties."""
        s = len(self.b)
        
        # Compute c from A if not provided
        if not hasattr(self, 'c') or self.c is None:
            self.c = np.sum(self.A, axis=1)
        
        # No constraints - let the model learn naturally
        
        # Compute order of consistency
        self.consistency_order = self._compute_consistency_order()
        
        # Compute stability properties
        self._compute_stability_properties()
    
    def _compute_consistency_order(self) -> int:
        """Compute the order of consistency for this method."""
        s = len(self.b)
        
        # Check order conditions up to order 4
        order = 0
        
        # Order 1: sum(b) = 1
        if np.allclose(np.sum(self.b), 1.0, atol=1e-10):
            order = 1
        
        # Order 2: sum(b*c) = 1/2
        if order == 1 and np.allclose(np.sum(self.b * self.c), 0.5, atol=1e-10):
            order = 2
        
        # Order 3: sum(b*c²) = 1/3 and sum(b*A*c) = 1/6
        if order == 2:
            cond1 = np.allclose(np.sum(self.b * self.c**2), 1/3, atol=1e-10)
            cond2 = np.allclose(np.sum(self.b * (self.A @ self.c)), 1/6, atol=1e-10)
            if cond1 and cond2:
                order = 3
        
        # Order 4: Additional conditions
        if order == 3:
            cond1 = np.allclose(np.sum(self.b * self.c**3), 1/4, atol=1e-10)
            cond2 = np.allclose(np.sum(self.b * self.c * (self.A @ self.c)), 1/8, atol=1e-10)
            cond3 = np.allclose(np.sum(self.b * (self.A @ self.c)**2), 1/12, atol=1e-10)
            cond4 = np.allclose(np.sum(self.b * (self.A @ (self.A @ self.c))), 1/24, atol=1e-10)
            if cond1 and cond2 and cond3 and cond4:
                order = 4
        
        return order
    
    def _compute_stability_properties(self):
        """Compute stability region properties."""
        # For explicit methods, compute stability function
        if self.is_explicit:
            # Stability function: R(z) = 1 + z*b^T*(I - z*A)^(-1)*1
            # For small z, we can approximate
            self.stability_radius = self._estimate_stability_radius()
        else:
            # For implicit methods, stability is generally better
            self.stability_radius = float('inf')
    
    def _estimate_stability_radius(self) -> float:
        """Estimate the stability radius for explicit methods."""
        # Simple heuristic based on method order and structure
        s = len(self.b)
        
        # Higher order methods generally have smaller stability regions
        if self.consistency_order <= 2:
            return 2.0
        elif self.consistency_order == 3:
            return 1.5
        elif self.consistency_order == 4:
            return 1.0
        else:
            return 0.5
    
    def to_tensor(self, device: torch.device = None) -> torch.Tensor:
        """Convert to PyTorch tensor for ML models."""
        s = len(self.b)
        tensor = torch.zeros(s * s + s + s, device=device)  # A + b + c
        
        # Flatten A (lower triangular for explicit methods)
        A_flat = self.A.flatten()
        tensor[:s*s] = torch.tensor(A_flat, dtype=torch.float32, device=device)
        
        # Add b and c
        tensor[s*s:s*s+s] = torch.tensor(self.b, dtype=torch.float32, device=device)
        tensor[s*s+s:] = torch.tensor(self.c, dtype=torch.float32, device=device)
        
        return tensor
    
    @classmethod
    def from_tensor(cls, tensor: torch.Tensor, s: int) -> 'ButcherTable':
        """Create ButcherTable from PyTorch tensor."""
        tensor_np = tensor.detach().cpu().numpy()
        
        # Extract A, b, c
        A_flat = tensor_np[:s*s]
        A = A_flat.reshape(s, s)
        
        b = tensor_np[s*s:s*s+s]
        c_raw = tensor_np[s*s+s:]
        
        # Let the model learn naturally - no constraints
        # Just use the raw c values from the neural network
        c = c_raw
        
        return cls(A=A, b=b, c=c)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'A': self.A.tolist(),
            'b': self.b.tolist(),
            'c': self.c.tolist(),
            'is_explicit': self.is_explicit,
            'consistency_order': self.consistency_order,
            'stability_radius': self.stability_radius
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ButcherTable':
        """Create ButcherTable from dictionary."""
        table = cls(
            A=np.array(data['A']),
            b=np.array(data['b']),
            c=np.array(data['c'])
        )
        table.is_explicit = data.get('is_explicit', table.is_explicit)
        table.consistency_order = data.get('consistency_order', table.consistency_order)
        table.stability_radius = data.get('stability_radius', table.stability_radius)
        return table
    
    def __str__(self) -> str:
        """String representation of the Butcher table."""
        s = len(self.b)
        lines = []
        lines.append(f"Butcher Table (s={s}, order={self.consistency_order}, {'explicit' if self.is_explicit else 'implicit'}):")
        lines.append("A matrix:")
        for i in range(s):
            row_str = "  ".join([f"{self.A[i,j]:8.4f}" for j in range(s)])
            lines.append(f"  {row_str}")
        lines.append(f"b: {'  '.join([f'{bi:8.4f}' for bi in self.b])}")
        lines.append(f"c: {'  '.join([f'{ci:8.4f}' for ci in self.c])}")
        return "\n".join(lines)

class ButcherTableGenerator:
    """Generates random Butcher tables for ML training."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
    
    def generate_random_explicit(self, s: int = None) -> ButcherTable:
        """Generate a random explicit Butcher table."""
        if s is None:
            s = np.random.randint(config.MIN_STAGES, config.MAX_STAGES + 1)
        
        # Generate lower triangular A with zero diagonal
        A = np.zeros((s, s))
        for i in range(s):
            for j in range(i):  # Only lower triangular, excluding diagonal
                A[i, j] = np.random.uniform(-1, 1)
        
        # Generate weights b (must sum to 1)
        b = np.random.exponential(1.0, s)
        b = b / np.sum(b)  # Normalize to sum to 1
        
        # Generate c vector - let the model learn naturally
        c = np.random.uniform(-2, 2, s)  # Wider range for exploration
        
        return ButcherTable(A=A, b=b, c=c)
    
    def generate_random_implicit(self, s: int = None) -> ButcherTable:
        """Generate a random implicit Butcher table."""
        if s is None:
            s = np.random.randint(config.MIN_STAGES, config.MAX_STAGES + 1)
        
        # Generate full A matrix
        A = np.random.uniform(-0.5, 0.5, (s, s))
        
        # Ensure diagonal dominance for stability
        for i in range(s):
            A[i, i] = np.sum(np.abs(A[i, :])) + np.random.uniform(0.1, 0.5)
        
        # Generate weights b
        b = np.random.exponential(1.0, s)
        b = b / np.sum(b)
        
        # Generate c vector - let the model learn naturally
        c = np.random.uniform(-2, 2, s)  # Wider range for exploration
        
        return ButcherTable(A=A, b=b, c=c)
    
    def generate_perturbed_baseline(self, baseline: ButcherTable, noise_level: float = 0.1) -> ButcherTable:
        """Generate a perturbed version of a baseline method."""
        s = len(baseline.b)
        
        # Add noise to A matrix
        noise_A = np.random.normal(0, noise_level, (s, s))
        A_new = baseline.A + noise_A
        
        # For explicit methods, ensure lower triangular structure
        if baseline.is_explicit:
            A_new = np.tril(A_new, k=-1)
        
        # Add noise to weights and renormalize
        noise_b = np.random.normal(0, noise_level, s)
        b_new = baseline.b + noise_b
        b_new = np.maximum(b_new, 0.01)  # Ensure positive weights
        b_new = b_new / np.sum(b_new)
        
        # Add noise to c vector and constrain to [0,1]
        noise_c = np.random.normal(0, noise_level, s)
        c_new = baseline.c + noise_c
        # No constraints - let the model learn naturally
        
        return ButcherTable(A=A_new, b=b_new, c=c_new)

# Classic Butcher tables
def get_rk4() -> ButcherTable:
    """Classic 4th order Runge-Kutta method."""
    A = np.array([
        [0,   0,   0,   0],
        [0.5, 0,   0,   0],
        [0,   0.5, 0,   0],
        [0,   0,   1,   0]
    ])
    b = np.array([1/6, 1/3, 1/3, 1/6])
    c = np.array([0, 0.5, 0.5, 1])
    return ButcherTable(A=A, b=b, c=c)

def get_rk45_dormand_prince() -> ButcherTable:
    """Dormand-Prince 5th order method."""
    A = np.array([
        [0,             0,             0,             0,             0,             0,           0],
        [1/5,           0,             0,             0,             0,             0,           0],
        [3/40,          9/40,          0,             0,             0,             0,           0],
        [44/45,         -56/15,        32/9,          0,             0,             0,           0],
        [19372/6561,    -25360/2187,   64448/6561,    -212/729,      0,             0,           0],
        [9017/3168,     -355/33,       46732/5247,    49/176,        -5103/18656,   0,           0],
        [35/384,        0,             500/1113,      125/192,       -2187/6784,    11/84,       0]
    ])
    b = np.array([35/384, 0, 500/1113, 125/192, -2187/6784, 11/84, 0])
    c = np.array([0, 1/5, 3/10, 4/5, 8/9, 1, 1])
    return ButcherTable(A=A, b=b, c=c)

def get_gauss_legendre_2() -> ButcherTable:
    """2-stage Gauss-Legendre implicit method."""
    A = np.array([
        [1/4,          1/4 - np.sqrt(3)/6],
        [1/4 + np.sqrt(3)/6, 1/4]
    ])
    b = np.array([1/2, 1/2])
    c = np.array([1/2 - np.sqrt(3)/6, 1/2 + np.sqrt(3)/6])
    return ButcherTable(A=A, b=b, c=c)

def get_gauss_legendre_3() -> ButcherTable:
    """3-stage Gauss-Legendre implicit method."""
    sqrt15 = np.sqrt(15)
    A = np.array([
        [5/36,                 2/9 - sqrt15/15,      5/36 - sqrt15/30],
        [5/36 + sqrt15/24,     2/9,                  5/36 - sqrt15/24],
        [5/36 + sqrt15/30,     2/9 + sqrt15/15,      5/36]
    ])
    b = np.array([5/18, 4/9, 5/18])
    c = np.array([1/2 - sqrt15/10, 1/2, 1/2 + sqrt15/10])
    return ButcherTable(A=A, b=b, c=c)

def get_all_baseline_tables() -> Dict[str, ButcherTable]:
    """Get all baseline Butcher tables."""
    return {
        'rk4': get_rk4(),
        'rk45_dormand_prince': get_rk45_dormand_prince(),
        'gauss_legendre_2': get_gauss_legendre_2(),
        'gauss_legendre_3': get_gauss_legendre_3()
    }

if __name__ == "__main__":
    # Test Butcher table creation and validation
    print("Testing Butcher tables...")
    
    # Test RK4
    rk4 = get_rk4()
    print(rk4)
    print(f"RK4 tensor shape: {rk4.to_tensor().shape}")
    
    # Test random generation
    generator = ButcherTableGenerator()
    random_explicit = generator.generate_random_explicit(4)
    print(f"\nRandom explicit method:\n{random_explicit}")
    
    # Test perturbation
    perturbed_rk4 = generator.generate_perturbed_baseline(rk4, 0.1)
    print(f"\nPerturbed RK4:\n{perturbed_rk4}")
    
    # Test serialization
    rk4_dict = rk4.to_dict()
    rk4_reconstructed = ButcherTable.from_dict(rk4_dict)
    print(f"\nSerialization test: {np.allclose(rk4.A, rk4_reconstructed.A)}")

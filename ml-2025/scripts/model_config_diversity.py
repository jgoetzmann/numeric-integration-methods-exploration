"""
Dynamic model configuration for diversity-focused training.
Handles variable stage counts (5-8 stages).
"""

from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for ML models with variable stage support."""
    
    # Generator model parameters
    generator_input_size: int = 128  # Random noise input
    generator_hidden_size: int = 256
    generator_output_size: int = None  # Will be calculated dynamically
    
    # Surrogate model parameters
    surrogate_input_size: int = None  # Will be calculated dynamically
    surrogate_hidden_size: int = 128
    surrogate_output_size: int = 4  # [accuracy, efficiency, stability, composite]
    
    # Training parameters
    learning_rate: float = 1e-3
    batch_size: int = 32
    n_epochs: int = 100
    weight_decay: float = 1e-5
    
    def __post_init__(self):
        """Calculate dynamic sizes based on max stages."""
        # Calculate for 6-stage method (fixed in diversity config)
        max_stages = 6
        self.generator_output_size = max_stages * max_stages + max_stages + max_stages  # A + b + c
        self.surrogate_input_size = max_stages * max_stages + max_stages + max_stages  # A + b + c

# Create config instance
config = ModelConfig()

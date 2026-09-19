"""CPU fallback decision engine for Fly Brain."""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class DecisionEngineConfig:
    input_size: int = 100
    hidden_size: int = 64
    output_size: int = 4
    seed: int = 42


class CPUEngine:
    """CPU-based decision engine using numpy (fallback for Vulkan)."""

    def __init__(self, config: Optional[DecisionEngineConfig] = None):
        self.config = config or DecisionEngineConfig()
        np.random.seed(self.config.seed)

        # Xavier initialization
        scale1 = np.sqrt(2.0 / self.config.input_size)
        self.W1 = (
            np.random.randn(self.config.hidden_size, self.config.input_size)
            .astype(np.float32) * scale1
        )
        self.b1 = np.zeros(self.config.hidden_size, dtype=np.float32)
        scale2 = np.sqrt(2.0 / self.config.hidden_size)
        self.W2 = (
            np.random.randn(self.config.output_size, self.config.hidden_size)
            .astype(np.float32) * scale2
        )
        self.b2 = np.zeros(self.config.output_size, dtype=np.float32)

        self._initialized = True

    def compute(self, input_grid: np.ndarray) -> np.ndarray:
        """Forward pass: input -> hidden (ReLU) -> output."""
        if not self._initialized:
            raise RuntimeError("CPUEngine not initialized")

        # Flatten input if needed
        x = input_grid.flatten().astype(np.float32)

        # Hidden layer with ReLU
        hidden = np.maximum(0, self.W1 @ x + self.b1)

        # Output layer
        output = self.W2 @ hidden + self.b2

        return output.astype(np.float32)

    def cleanup(self):
        self._initialized = False


# Global singleton
_cpu_engine = None


def get_cpu_engine(config: Optional[DecisionEngineConfig] = None) -> CPUEngine:
    global _cpu_engine
    if _cpu_engine is None:
        _cpu_engine = CPUEngine(config)
    return _cpu_engine


def shutdown_cpu_engine():
    global _cpu_engine
    if _cpu_engine is not None:
        _cpu_engine.cleanup()
        _cpu_engine = None

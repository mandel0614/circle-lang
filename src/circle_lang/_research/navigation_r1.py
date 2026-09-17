"""Seed policy for LifeCompiler AlphaEvolve experiment v1."""

import numpy as np

# EVOLVE-BLOCK-START

def toward_gain(A, B):
    """Per-cell gain for migration toward target signal A."""
    A_safe = np.clip(A, 0.0, 1.0)
    B_safe = np.clip(B, 0.0, 1.0)
    
    # Adaptive attraction: when near the target (high A), we tolerate more inhibitor B.
    # When far (low A), we remain highly conservative to avoid entering forbidden regions.
    safety_limit = 0.34 + 0.66 * (A_safe ** 2.5)
    gain = 3.0 * np.clip(1.0 - (B_safe / safety_limit) ** 2, 0.0, 1.0)
    return gain


def away_gain(A, B):
    """Per-cell gain for migration away from inhibitor signal B."""
    A_safe = np.clip(A, 0.0, 1.0)
    B_safe = np.clip(B, 0.0, 1.0)
    
    # Adaptive avoidance: shift the threshold for pushing away from B based on target proximity A.
    # If we are close to the goal, we suppress the avoidance signal to prevent being pushed off the target.
    away_threshold = 0.018 + 0.42 * (A_safe ** 2.5)
    gain = 3.0 * np.clip((B_safe - away_threshold) / 0.18, 0.0, 1.0) ** 1.15
    return gain

# EVOLVE-BLOCK-END


def policy(A, B):
    """Stable public interface used by the locked evaluator."""
    toward = np.asarray(toward_gain(A, B), dtype=float)
    away = np.asarray(away_gain(A, B), dtype=float)
    return toward, away

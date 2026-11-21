"""Deterministic test signals. Plain module (not conftest) so tests can import it."""
import numpy as np

FS = 256.0
N = 128  # 0.5 s -> 2 Hz frequency resolution, so 24, 40 and 92 Hz fall exactly on FFT bins


def tone(freq_hz: float, amplitude: float = 1.0, n: int = N, fs: float = FS, phase: float = 0.3) -> np.ndarray:
    return amplitude * np.sin(2 * np.pi * freq_hz * np.arange(n) / fs + phase)

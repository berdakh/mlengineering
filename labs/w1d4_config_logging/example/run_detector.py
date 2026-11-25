"""Worked example for w1d4: one small experiment made reproducible and inspectable.

A rolling z-score spike detector on a SIMULATED sensor trace. The science is trivial
on purpose; look at how the run is parameterised, logged and recorded.

    python labs/w1d4_config_logging/example/run_detector.py
    python labs/w1d4_config_logging/example/run_detector.py --set detector.threshold=3.0
    python labs/w1d4_config_logging/example/run_detector.py --set detector.treshold=3.0   # typo -> error
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
logger = logging.getLogger("detector")


# --- 1. Configuration is data: typed, validated once, then immutable -------------------------

@dataclass(frozen=True)
class SignalConfig:
    n_samples: int = 5000
    n_spikes: int = 25
    spike_size: float = 6.0
    seed: int = 0


@dataclass(frozen=True)
class DetectorConfig:
    window: int = 50
    threshold: float = 4.0

    def __post_init__(self):
        # dataclasses do not check types or ranges; this is where our own checks go
        if self.window < 2:
            raise ValueError(f"detector.window must be >= 2, got {self.window}")
        if self.threshold <= 0:
            raise ValueError(f"detector.threshold must be > 0, got {self.threshold}")


@dataclass(frozen=True)
class Config:
    signal: SignalConfig
    detector: DetectorConfig
    log_level: str = "INFO"


def load_config(path: Path, overrides: list[str]) -> Config:
    with path.open("rb") as fh:                      # tomllib wants a binary file
        raw = tomllib.load(fh)
    for item in overrides:                           # CLI layer sits on top of the file layer
        dotted, _, value = item.partition("=")
        section, _, key = dotted.partition(".")
        raw.setdefault(section, {})[key] = tomllib.loads(f"v = {value}")["v"]
    try:
        # SignalConfig(**dict) raises TypeError on an unknown key: typos cannot pass silently.
        return Config(
            signal=SignalConfig(**raw.get("signal", {})),
            detector=DetectorConfig(**raw.get("detector", {})),
            log_level=raw.get("logging", {}).get("level", "INFO"),
        )
    except TypeError as exc:
        raise ValueError(f"bad configuration: {exc}") from None


# --- 2. The computation takes values, never reads files or globals ---------------------------

def simulate(cfg: SignalConfig) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(cfg.seed)            # a local generator; no global seeding
    x = rng.standard_normal(cfg.n_samples)
    spikes = np.sort(rng.choice(np.arange(200, cfg.n_samples), size=cfg.n_spikes, replace=False))
    x[spikes] += cfg.spike_size * rng.choice([-1.0, 1.0], size=cfg.n_spikes)
    logger.debug("simulated signal n=%d spikes=%d seed=%d", cfg.n_samples, cfg.n_spikes, cfg.seed)
    return x, spikes


def detect(x: np.ndarray, cfg: DetectorConfig) -> np.ndarray:
    """Indices where |x[t] - mean(previous window)| / std(previous window) > threshold."""
    windows = np.lib.stride_tricks.sliding_window_view(x, cfg.window)[:-1]   # strictly past samples
    z = (x[cfg.window:] - windows.mean(axis=1)) / windows.std(axis=1)
    return np.flatnonzero(np.abs(z) > cfg.threshold) + cfg.window


def score(detected: np.ndarray, truth: np.ndarray) -> dict:
    tp = int(np.isin(detected, truth).sum())
    return {
        "n_true": int(len(truth)),
        "n_detected": int(len(detected)),
        "precision": tp / len(detected) if len(detected) else 0.0,
        "recall": tp / len(truth),
    }


# --- 3. The entry point owns arguments, logging and output locations -------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rolling z-score spike detector (worked example).")
    parser.add_argument("--config", type=Path, default=HERE / "detector.toml")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="SECTION.KEY=VALUE")
    parser.add_argument("--run-dir", type=Path, default=Path("runs_example"))
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config, args.overrides)
    except ValueError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    run_dir = args.run_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True)

    # Logging is configured here, once. stderr for humans, a file for the record.
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(run_dir / "run.log")],
    )
    (run_dir / "config.json").write_text(json.dumps(dataclasses.asdict(cfg), indent=2))
    logger.info("run started run_dir=%s", run_dir)

    x, truth = simulate(cfg.signal)
    detected = detect(x, cfg.detector)
    metrics = score(detected, truth)
    logger.info("detection finished threshold=%g precision=%.3f recall=%.3f",
                cfg.detector.threshold, metrics["precision"], metrics["recall"])
    if metrics["precision"] < 0.5:
        logger.warning("more than half of the detections are false alarms n_detected=%d", metrics["n_detected"])

    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics))                       # the result, and only the result, on stdout
    return 0


if __name__ == "__main__":
    sys.exit(main())

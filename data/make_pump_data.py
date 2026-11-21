"""Generate the SYNTHETIC pump-vibration dataset used by the Week 1 engineering lessons.

This data is simulated. It exists so the packaging / configuration / testing labs
run offline and deterministically. Nothing learned about model quality on it says
anything about real equipment. See data/README.md for the schema.

Usage:
    python data/make_pump_data.py            # writes data/synthetic/pump_vibration.csv
    python data/make_pump_data.py --check    # verifies the committed file is reproducible
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd

FS_HZ = 256            # sampling rate of the simulated accelerometer
WINDOW_SAMPLES = 128   # 0.5 s windows
N_UNITS = 10
WINDOWS_PER_UNIT = 30
FAULT_FREQ_HZ = 90.0   # bearing-fault signature frequency
SEED = 20261121
OUT = Path(__file__).parent / "synthetic" / "pump_vibration.csv"


def simulate(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(WINDOW_SAMPLES) / FS_HZ
    frames = []
    faulty_units = set(rng.choice(N_UNITS, size=N_UNITS // 2, replace=False).tolist())
    for u in range(N_UNITS):
        unit_id = f"P{u + 1:02d}"
        gain = float(rng.lognormal(mean=0.0, sigma=0.35))      # unit-specific sensor gain
        shaft_hz = float(rng.uniform(22.0, 28.0))              # unit-specific shaft speed
        onset = int(rng.integers(12, 22)) if u in faulty_units else WINDOWS_PER_UNIT
        for w in range(WINDOWS_PER_UNIT):
            label = int(w >= onset)
            x = np.sin(2 * np.pi * shaft_hz * t + rng.uniform(0, 2 * np.pi))
            x += 0.5 * rng.standard_normal(WINDOW_SAMPLES)
            if label:
                severity = 0.25 + 0.03 * (w - onset)           # fault grows over time
                x += severity * np.sin(2 * np.pi * FAULT_FREQ_HZ * t + rng.uniform(0, 2 * np.pi))
                x += severity * rng.standard_normal(WINDOW_SAMPLES)
            x *= gain
            temp = 45.0 + 4.0 * gain + 0.05 * w + 1.5 * label + rng.normal(0, 0.4)
            frames.append(pd.DataFrame({
                "unit_id": unit_id,
                "window_id": w,
                "sample": np.arange(WINDOW_SAMPLES),
                "vibration": np.round(x, 5),
                "temperature_c": round(float(temp), 2),
                "label": label,
            }))
    df = pd.concat(frames, ignore_index=True)
    # A small number of dropped samples, as a real acquisition system would produce.
    missing = rng.choice(len(df), size=len(df) // 1000, replace=False)
    df.loc[missing, "vibration"] = np.nan
    return df


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue().encode()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="compare regenerated data to the file on disk")
    args = ap.parse_args()
    data = to_csv_bytes(simulate())
    digest = hashlib.sha256(data).hexdigest()
    if args.check:
        on_disk = hashlib.sha256(OUT.read_bytes()).hexdigest()
        print("regenerated:", digest)
        print("on disk:    ", on_disk)
        raise SystemExit(0 if digest == on_disk else 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data) / 1e6:.2f} MB, sha256 {digest[:16]}...)")


if __name__ == "__main__":
    main()

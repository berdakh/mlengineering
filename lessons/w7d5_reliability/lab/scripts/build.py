"""Build the model bundle and the data-derived service settings from DEVELOPMENT experiments only.

    python scripts/build.py --raw ../../../../data/raw/skab        # from the lab directory

Writes bundle/ (model.json + MANIFEST.json) and appends support_* and envelope_* to configs/service.toml.
Test experiments are never read.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.scoring import ZScoreModel  # noqa: E402
from flowguard.splits import dev_experiments, file_sha256, load_splits  # noqa: E402

ENVELOPE_Q = (0.005, 0.995)


def default_raw() -> str:
    """data/raw/skab of the repository this lab lives in (works for lessons/ and solutions/ copies)."""
    for parent in HERE.parents:
        if (parent / "data" / "raw" / "skab").is_dir():
            return str(parent / "data" / "raw" / "skab")
    return "data/raw/skab"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", default=default_raw())
    ap.add_argument("--splits", default=str(HERE / "splits" / "v2.json"))
    ap.add_argument("--config", default=str(HERE / "configs" / "model.toml"))
    ap.add_argument("--service", default=str(HERE / "configs" / "service.toml"))
    ap.add_argument("--out", default=str(HERE / "bundle"))
    args = ap.parse_args()

    config = tomllib.loads(Path(args.config).read_text())
    model = ZScoreModel(**config)
    manifest = load_splits(args.splits)
    tidy = load_raw(args.raw)
    dev = tidy[tidy["experiment_id"].isin(set(dev_experiments(manifest)))]
    x_all = dev[model.sensor].to_numpy(dtype=float)
    x_normal = dev.loc[dev["anomaly"] == 0, model.sensor].to_numpy(dtype=float)
    values = {"support_low": float(x_all.min()), "support_high": float(x_all.max()),
              "envelope_low": float(np.quantile(x_normal, ENVELOPE_Q[0])),
              "envelope_high": float(np.quantile(x_normal, ENVELOPE_Q[1]))}

    save_bundle(model, args.out, {"config": config, "config_sha256": file_sha256(args.config),
                                  "splits_sha256": file_sha256(args.splits),
                                  "dev_experiments": int(dev["experiment_id"].nunique())})
    service = Path(args.service)
    text = re.sub(r"(?m)^(support|envelope)_(low|high) = .*\n", "", service.read_text())
    text = text.rstrip("\n") + "\n" + "".join(f"{k} = {v!r}\n" for k, v in values.items())
    service.write_text(text)
    print(f"bundle {args.out}: {model.model_version}; {dev['experiment_id'].nunique()} development experiments")
    for k, v in values.items():
        print(f"  {k} = {v:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

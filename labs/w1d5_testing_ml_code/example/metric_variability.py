"""Why `assert auc > 0.95` is not a unit test.

Runs the SAME correct code on the SAME (synthetic) data with 20 different split
seeds and prints the held-out metrics. Nothing about the code changes between
rows; only which three pumps are held out.

    python labs/w1d5_testing_ml_code/example/metric_variability.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "labs" / "w1d5_testing_ml_code" / "lab" / "src"))

from pumpwatch.features import build_feature_table  # noqa: E402
from pumpwatch.io import load_windows  # noqa: E402
from pumpwatch.model import train_and_evaluate  # noqa: E402

table = build_feature_table(load_windows(ROOT / "data" / "synthetic" / "pump_vibration.csv"), fs=256.0)
aucs = []
print("seed  auc     f1     held-out units")
for seed in range(20):
    m = train_and_evaluate(table, seed=seed)
    aucs.append(m["auc"])
    print(f"{seed:>4}  {m['auc']:.4f}  {m['f1']:.3f}  {' '.join(m['test_units'])}")
print(f"\nAUC min {min(aucs):.4f}  max {max(aucs):.4f}  -> runs below 0.95: {sum(a <= 0.95 for a in aucs)} of {len(aucs)}")

"""Write the tidy table data/interim/skab.csv if you do not have it from w2d3.

    python project/get_skab.py                                   # once: download the raw files
    python lessons/w2d5_feature_pipeline/lab/make_tidy.py        # from the repository root
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent / "src"))
from flowguard.data import load_raw  # noqa: E402

raw, out = ROOT / "data" / "raw" / "skab", ROOT / "data" / "interim" / "skab.csv"
if not raw.is_dir():
    sys.exit("data/raw/skab is missing. Run:  python project/get_skab.py")
tidy = load_raw(raw)
out.parent.mkdir(parents=True, exist_ok=True)
tidy.to_csv(out, index=False, lineterminator="\n")
print(f"wrote {out.relative_to(ROOT)}: {len(tidy)} rows, {tidy['experiment_id'].nunique()} experiments")

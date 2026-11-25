from pumpwatch.features import build_feature_table
from pumpwatch.io import load_windows


def test_real_dataset_has_300_windows():
    table = build_feature_table(load_windows("data/synthetic/pump_vibration.csv"), 256.0)
    assert len(table) == 300

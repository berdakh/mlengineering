from pumpwatch.features import build_feature_table
from pumpwatch.model import train_and_evaluate


def test_model_is_good(make_frame):
    metrics = train_and_evaluate(build_feature_table(make_frame(), 256.0), test_fraction=0.34, seed=0)
    assert metrics["auc"] > 0.95
    assert metrics["acc"] > 0.9

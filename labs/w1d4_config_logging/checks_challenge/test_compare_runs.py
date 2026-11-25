import json

import pytest


def metrics(run_dir):
    return json.loads((run_dir / "metrics.json").read_text())


def test_config_diff_names_exactly_the_changed_dotted_keys(cli, runs):
    report = cli.compare(runs["base"], runs["tuned"])
    assert report["config_diff"] == {
        "split.seed": {"a": 7, "b": 3},
        "model.C": {"a": 1.0, "b": 0.1},
    }


def test_identical_configs_have_an_empty_config_diff(cli, runs):
    report = cli.compare(runs["base"], runs["base"])
    assert report["config_diff"] == {}
    assert all(entry["delta"] == 0 for entry in report["metric_diff"].values())


def test_metric_delta_is_b_minus_a(cli, runs):
    a, b = metrics(runs["base"]), metrics(runs["tuned"])
    assert a["f1"] != b["f1"], "fixture problem: the two runs should differ"
    report = cli.compare(runs["base"], runs["tuned"])
    for name in ("auc", "ap", "acc", "f1"):
        entry = report["metric_diff"][name]
        assert entry["a"] == a[name] and entry["b"] == b[name]
        assert entry["delta"] == pytest.approx(b[name] - a[name])


def test_swapping_the_arguments_negates_the_deltas(cli, runs):
    forward = cli.compare(runs["base"], runs["tuned"])["metric_diff"]
    backward = cli.compare(runs["tuned"], runs["base"])["metric_diff"]
    assert backward["f1"]["delta"] == pytest.approx(-forward["f1"]["delta"])


def test_non_numeric_metrics_are_not_differenced(cli, runs):
    assert "test_units" not in cli.compare(runs["base"], runs["tuned"])["metric_diff"]


def test_same_data_is_true_for_an_identical_copy_at_another_path(cli, runs):
    report = cli.compare(runs["base"], runs["copy"])
    assert report["same_data"] is True
    assert "data.path" in report["config_diff"]


def test_same_data_is_false_when_the_file_was_edited_in_place(cli, runs):
    report = cli.compare(runs["before_edit"], runs["after_edit"])
    assert report["same_data"] is False
    assert report["config_diff"] == {}, "nothing in the config changed - only the bytes on disk did"


@pytest.mark.parametrize("damage", ["missing_directory", "missing_metrics"])
def test_incomplete_run_directories_fail_cleanly(cli, runs, tmp_path, damage):
    if damage == "missing_directory":
        broken = tmp_path / "does_not_exist"
    else:
        broken = tmp_path / "partial"
        broken.mkdir()
        (broken / "config.json").write_text((runs["base"] / "config.json").read_text())
    proc = cli.run("compare-runs", runs["base"], broken)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr and proc.stderr.strip() != ""
    assert proc.stdout.strip() == ""

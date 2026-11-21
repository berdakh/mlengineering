"""validate_splits must reject every way a manifest can leak; save/load must round-trip and freeze."""
from __future__ import annotations

import copy
import json

import pytest

from conftest import assigned_ids


@pytest.fixture()
def good(splits, tidy):
    return splits.make_splits(tidy, seed=0)


def test_accepts_its_own_output(splits, tidy, good):
    splits.validate_splits(good, tidy)          # must not raise


def _broken(good, how):
    m = copy.deepcopy(good)
    if how == "test_dev_overlap":
        m["dev_folds"][0].append(m["test"][0])
    elif how == "fold_fold_overlap":
        m["dev_folds"][1].append(m["dev_folds"][0][0])
    elif how == "unknown_id":
        m["test"].append("valve9/99")
    elif how == "missing_experiment":
        m["dev_folds"][0] = m["dev_folds"][0][1:]
    elif how == "normal_in_test":
        m["test"].append("anomaly-free/anomaly-free")
    elif how == "labelled_as_normal":
        m["reference_normal"].append(m["test"][0])
    elif how == "row_unit":
        m["unit"] = "row"
    elif how == "row_indices":
        m["test"] = [0, 1, 2, 3]
    return m


@pytest.mark.parametrize("how", ["test_dev_overlap", "fold_fold_overlap", "unknown_id", "missing_experiment",
                                 "normal_in_test", "labelled_as_normal", "row_unit", "row_indices"])
def test_rejects_broken_manifests(splits, tidy, good, how):
    with pytest.raises(ValueError):
        splits.validate_splits(_broken(good, how), tidy)


def test_error_names_the_offending_experiment(splits, tidy, good):
    bad = _broken(good, "test_dev_overlap")
    with pytest.raises(ValueError) as err:
        splits.validate_splits(bad, tidy)
    assert good["test"][0] in str(err.value), "the message should say which experiment is on both sides"


def test_save_then_load_round_trips(splits, good, tmp_path):
    path = tmp_path / "splits" / "v1.json"
    splits.save_splits(good, path)
    assert splits.load_splits(path) == good
    assert json.loads(path.read_text()) == good, "the manifest must be plain JSON"


def test_saved_file_is_stable_text(splits, good, tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    splits.save_splits(good, a)
    splits.save_splits(copy.deepcopy(good), b)
    assert a.read_bytes() == b.read_bytes(), "saving the same manifest twice must give identical bytes"


def test_a_frozen_manifest_is_not_silently_replaced(splits, tidy, good, tmp_path):
    path = tmp_path / "v1.json"
    splits.save_splits(good, path)
    before = path.read_bytes()
    other = splits.make_splits(tidy, seed=1)
    with pytest.raises(FileExistsError):
        splits.save_splits(other, path)
    assert path.read_bytes() == before


def test_cli_creates_a_valid_manifest_and_refuses_to_overwrite(splits, tidy, run_cli, tmp_path):
    from conftest import write_raw
    raw = write_raw(tidy, tmp_path / "raw")
    out = tmp_path / "splits" / "v1.json"
    first = run_cli("split", "--raw-dir", raw, "--out", out, "--seed", 0, cwd=tmp_path)
    assert first.returncode == 0, first.stderr[-800:]
    manifest = json.loads(out.read_text())
    splits.validate_splits(manifest, tidy)
    assert len(assigned_ids(manifest)) == 16

    before = out.read_bytes()
    second = run_cli("split", "--raw-dir", raw, "--out", out, "--seed", 1, cwd=tmp_path)
    assert second.returncode != 0, "re-running `split` onto an existing manifest must fail without --force"
    assert out.read_bytes() == before, "the existing manifest was modified"
    assert "Traceback" not in second.stderr


def test_cli_reports_missing_data_without_a_traceback(run_cli, tmp_path):
    proc = run_cli("split", "--raw-dir", tmp_path / "nope", "--out", tmp_path / "v1.json", cwd=tmp_path)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr
    assert not (tmp_path / "v1.json").exists()

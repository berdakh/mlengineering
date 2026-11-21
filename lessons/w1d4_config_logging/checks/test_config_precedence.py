"""defaults < file < command-line overrides, and the snapshot records the RESOLVED values."""
import sys

import pytest

from conftest import DATA, write_config


def test_snapshot_contains_file_values(base_run):
    cfg = base_run.json("config.json")
    assert cfg["split"]["seed"] == 7
    assert cfg["data"]["fs"] == 256.0
    assert cfg["model"]["C"] == 1.0


def test_omitted_keys_take_documented_defaults(cli, workdir):
    minimal = write_config(workdir / "minimal.toml", f'[data]\npath = "{DATA}"\n')
    cfg = cli.train(workdir, minimal).json("config.json")
    assert cfg["split"] == {"test_fraction": 0.3, "seed": 7}
    assert cfg["model"]["C"] == 1.0
    assert cfg["data"]["fs"] == 256.0


def test_file_beats_default(cli, workdir):
    body = f'[data]\npath = "{DATA}"\n\n[split]\nseed = 5\n\n[model]\nC = 0.5\n'
    cfg = cli.train(workdir, write_config(workdir / "file_values.toml", body)).json("config.json")
    assert cfg["split"]["seed"] == 5
    assert cfg["model"]["C"] == 0.5
    assert cfg["split"]["test_fraction"] == 0.3


def test_command_line_beats_file_and_is_in_the_snapshot(cli, workdir, base_config):
    run = cli.train(workdir, base_config, "--set", "split.seed=11", "--set", "model.C=0.25")
    cfg = run.json("config.json")
    assert cfg["split"]["seed"] == 11, "config.json must record the value actually used, after overrides"
    assert cfg["model"]["C"] == 0.25
    assert cfg["split"]["test_fraction"] == 0.3


def test_load_config_api(target, base_config):
    sys.path.insert(0, str(target / "src"))
    try:
        from pumpwatch.config import load_config
        cfg = load_config(base_config)
        assert cfg.split.seed == 7 and cfg.model.C == 1.0 and cfg.data.fs == 256.0
        assert load_config(base_config, overrides=["split.seed=11"]).split.seed == 11
        assert load_config(base_config).split.seed == 7, "overrides must not leak between calls"
        with pytest.raises(Exception):
            cfg.split.seed = 99                        # configuration objects are immutable
        assert cfg.split.seed == 7
        with pytest.raises(ValueError):
            load_config(base_config, overrides=["split.test_fraction=2"])
    finally:
        sys.path.remove(str(target / "src"))
        for name in [m for m in sys.modules if m == "pumpwatch" or m.startswith("pumpwatch.")]:
            del sys.modules[name]

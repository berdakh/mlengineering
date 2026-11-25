"""Bad configuration fails fast, with an exit code and a message that names the key."""
import pytest

from conftest import DATA, write_config

GOOD = f'[data]\npath = "{DATA}"\n'

BAD_FILES = {
    "split.sed":            GOOD + "\n[split]\nsed = 7\n",                 # typo in a key
    "split.seed":           GOOD + '\n[split]\nseed = "seven"\n',          # wrong type
    "split.test_fraction":  GOOD + "\n[split]\ntest_fraction = 1.5\n",     # out of range
    "model.C":              GOOD + "\n[model]\nC = -1.0\n",                # out of range
    "data.path":            "[split]\nseed = 7\n",                          # required key missing
}


def assert_clean_failure(proc, key):
    assert proc.returncode != 0, f"a bad value for {key} must not exit 0"
    assert key in proc.stderr, f"the error message should name the key {key!r}; got:\n{proc.stderr[-600:]}"
    assert "Traceback" not in proc.stderr, "a user's config mistake should not produce a traceback"
    assert proc.stdout.strip() == "", "nothing should be printed to stdout on failure"


@pytest.mark.parametrize("key", sorted(BAD_FILES))
def test_bad_config_file_is_rejected(cli, workdir, key):
    config = write_config(workdir / f"bad_{key.replace('.', '_')}.toml", BAD_FILES[key])
    assert_clean_failure(cli.train(workdir, config).proc, key)


@pytest.mark.parametrize("override,key", [
    ("model.depth=3", "model.depth"),          # unknown key
    ("split.seed=1.5", "split.seed"),          # wrong type
    ("data.fs=0", "data.fs"),                  # out of range
])
def test_bad_override_is_rejected(cli, workdir, base_config, override, key):
    assert_clean_failure(cli.train(workdir, base_config, "--set", override).proc, key)

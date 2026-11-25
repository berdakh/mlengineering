"""Checks for lesson w6d6: rollback target selection, startup configuration, the debugging log."""
from __future__ import annotations

import random
import re

import pytest

from conftest import IMAGE, entry


# ------------------------------------------------------------------------------------- rollback
def test_rollback_skips_the_failed_current_and_picks_the_previous_good(rb):
    h = [entry("production", "aaaaaaa1", "a", 1), entry("production", "bbbbbbb2", "b", 2),
         entry("production", "ccccccc3", "c", 3, "failed")]
    assert rb.select_rollback_target(h, "production")["release"] == "bbbbbbb2"


def test_rollback_skips_failed_and_rolled_back_entries(rb):
    h = [entry("production", "aaaaaaa1", "a", 1), entry("production", "bbbbbbb2", "b", 2, "failed"),
         entry("production", "ccccccc3", "c", 3, "rolled_back"), entry("production", "ddddddd4", "d", 4, "failed")]
    assert rb.select_rollback_target(h, "production")["release"] == "aaaaaaa1"


def test_rollback_never_targets_the_image_that_is_already_running(rb):
    # Config incident: the current deployment failed with the same digest that was good before.
    h = [entry("production", "aaaaaaa1", "a", 1), entry("production", "bbbbbbb2", "b", 2),
         entry("production", "bbbbbbb2", "b", 3, "failed")]
    assert rb.select_rollback_target(h, "production")["release"] == "aaaaaaa1"


def test_rollback_looks_only_at_its_environment(rb):
    h = [entry("production", "aaaaaaa1", "a", 1), entry("staging", "bbbbbbb2", "b", 2),
         entry("production", "ccccccc3", "c", 3, "failed"), entry("staging", "ddddddd4", "d", 4)]
    assert rb.select_rollback_target(h, "production")["release"] == "aaaaaaa1"
    assert rb.select_rollback_target(h, "staging")["release"] == "bbbbbbb2"


def test_rollback_orders_by_time_not_by_list_position(rb):
    h = [entry("production", "aaaaaaa1", "a", 1), entry("production", "bbbbbbb2", "b", 2),
         entry("production", "ccccccc3", "c", 3, "failed")]
    for seed in range(5):
        shuffled = h[:]
        random.Random(seed).shuffle(shuffled)
        assert rb.select_rollback_target(shuffled, "production")["release"] == "bbbbbbb2"


@pytest.mark.parametrize("history", [
    [],
    [{"env": "staging", "release": "aaaaaaa1", "image": IMAGE, "digest": "sha256:" + "a" * 64,
      "deployed_at": "2026-11-22T10:00:00.000+00:00", "status": "good", "note": ""}],
    [entry("production", "aaaaaaa1", "a", 1, "failed"), entry("production", "bbbbbbb2", "b", 2, "failed")],
    [entry("production", "aaaaaaa1", "a", 1), entry("production", "aaaaaaa1", "a", 2, "failed")],
])
def test_no_target_is_an_error_not_a_guess(rb, history):
    with pytest.raises(rb.RollbackError):
        rb.select_rollback_target(history, "production")


def test_image_reference_pins_the_digest(rb):
    e = entry("production", "aaaaaaa1", "a", 1)
    ref = rb.image_reference(e)
    assert ref == f"{IMAGE}@sha256:{'a' * 64}"
    assert ":aaaaaaa1" not in ref, "a tag can be moved; deploy by digest"
    with pytest.raises(rb.RollbackError):
        rb.image_reference(dict(e, digest="aaaaaaa1"))


# ------------------------------------------------------------------------------------- settings
GOOD = {"FLOWGUARD_ENV": "production", "FLOWGUARD_MODEL_DIR": "/models/flowguard-z/1.0.0",
        "FLOWGUARD_RELEASE": "b7c8d9e0f1a2", "PATH": "/usr/bin", "HOME": "/home/app"}


def test_valid_environment_gives_settings_with_defaults(settings_mod):
    s = settings_mod.load_settings(GOOD)
    assert (s.environment, s.model_dir, s.release, s.log_level, s.port) == \
        ("production", "/models/flowguard-z/1.0.0", "b7c8d9e0f1a2", "INFO", 8000)
    s = settings_mod.load_settings({**GOOD, "FLOWGUARD_LOG_LEVEL": "debug", "FLOWGUARD_PORT": "9000"})
    assert s.log_level == "DEBUG" and s.port == 9000


@pytest.mark.parametrize("change, name", [
    ({"FLOWGUARD_ENV": None}, "FLOWGUARD_ENV"),
    ({"FLOWGUARD_ENV": "prod"}, "FLOWGUARD_ENV"),
    ({"FLOWGUARD_MODEL_DIR": ""}, "FLOWGUARD_MODEL_DIR"),
    ({"FLOWGUARD_MODEL_DIR": "models/flowguard-z/1.0.0"}, "FLOWGUARD_MODEL_DIR"),
    ({"FLOWGUARD_RELEASE": "latest"}, "FLOWGUARD_RELEASE"),
    ({"FLOWGUARD_RELEASE": "B7C8D9E0"}, "FLOWGUARD_RELEASE"),
    ({"FLOWGUARD_LOG_LEVEL": "VERBOSE"}, "FLOWGUARD_LOG_LEVEL"),
    ({"FLOWGUARD_PORT": "eighty"}, "FLOWGUARD_PORT"),
    ({"FLOWGUARD_PORT": "70000"}, "FLOWGUARD_PORT"),
    ({"FLOWGUARD_MODEL_DlR": "/models/x"}, "FLOWGUARD_MODEL_DlR"),
])
def test_bad_environment_is_rejected_with_the_variable_named(settings_mod, change, name):
    env = dict(GOOD)
    for k, v in change.items():
        if v is None:
            env.pop(k)
        else:
            env[k] = v
    with pytest.raises(settings_mod.SettingsError) as info:
        settings_mod.load_settings(env)
    assert name in str(info.value), f"the error must name {name}: {info.value}"


def test_unrelated_variables_are_ignored(settings_mod):
    settings_mod.load_settings({**GOOD, "PYTHONUNBUFFERED": "1", "OTHER_PORT": "x"})


# ------------------------------------------------------------------------------------- debug log
FIELDS = ["Symptom", "Evidence", "Hypotheses", "Test", "Root cause", "Fix", "Verification", "Prevention"]


def incidents(text: str) -> dict[str, str]:
    parts = re.split(r"^## (Incident \d+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def field(body: str, name: str) -> str:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*(.*?)(?=\n\*\*[A-Z][A-Za-z ]+:\*\*|\Z)", body, flags=re.S)
    return m.group(1).strip() if m else ""


def test_debug_log_has_three_complete_incidents(target):
    text = (target / "DEBUG_LOG.md").read_text()
    inc = incidents(text)
    assert len(inc) >= 3, "write up all three incidents (## Incident 1, 2, 3)"
    for title, body in inc.items():
        for name in FIELDS:
            value = re.sub(r"<!--.*?-->", "", field(body, name), flags=re.S)
            assert len(value) >= 15 and "TODO" not in value, f"{title}: **{name}:** is empty or still TODO"
        evidence = field(body, "Evidence")
        assert "```" in evidence, f"{title}: quote real output in a fenced code block under Evidence"


def test_debug_log_root_causes_match_the_incidents(target):
    """The three seeded incidents have three different causes; each must appear in some root cause."""
    inc = incidents((target / "DEBUG_LOG.md").read_text())
    causes = [field(b, "Root cause").lower() + " " + field(b, "Fix").lower() for b in inc.values()]
    joined = " || ".join(causes)
    assert re.search(r"checksum", joined), "one incident is a bundle whose checksums do not match"
    assert re.search(r"model_dir|model dir|model directory", joined), "one incident is a wrong model directory"
    assert re.search(r"memory|oom", joined), "one incident is a memory limit below the working set"
    rollback_fixes = [c for c in causes if "rollback" in c or "roll back" in c]
    assert rollback_fixes and any("checksum" in c for c in rollback_fixes), \
        "the checksum incident is fixed by rolling back the image"

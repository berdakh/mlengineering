"""Tasks 4-5: atomic, audited pointer moves; compatibility; rollback; reload through the API."""
from __future__ import annotations

import os

import pytest

from conftest import SERVING, make_run


def test_promote_moves_the_pointer_and_audits(fg, registry):
    u, reg = fg["update"], fg["registry"]
    u.promote(registry, "flowguard", "1.0.0", serving_columns=SERVING, actor="alice", reason="first")
    u.promote(registry, "flowguard", "1.1.0", serving_columns=SERVING, actor="bob", reason="gate passed")
    assert reg.current_version(registry, "flowguard") == "1.1.0"
    log = u.audit_log(registry, "flowguard")
    assert [(e["action"], e["from"], e["to"]) for e in log] == [("promote", None, "1.0.0"), ("promote", "1.0.0", "1.1.0")]
    assert log[1]["actor"] == "bob" and log[1]["reason"] == "gate passed" and log[1]["ts"]


def test_incompatible_or_unknown_versions_are_refused(fg, registry):
    u, reg = fg["update"], fg["registry"]
    u.promote(registry, "flowguard", "1.0.0", serving_columns=SERVING)
    with pytest.raises(reg.RegistryError, match="voltage"):
        u.promote(registry, "flowguard", "2.0.0", serving_columns=SERVING)
    with pytest.raises(reg.RegistryError):
        u.promote(registry, "flowguard", "3.0.0", serving_columns=SERVING)
    assert reg.current_version(registry, "flowguard") == "1.0.0"
    assert len(u.audit_log(registry, "flowguard")) == 1


def test_tampered_bundle_is_refused(fg, registry):
    u, reg = fg["update"], fg["registry"]
    model_json = registry / "flowguard" / "1.1.0" / "model.json"
    model_json.write_text(model_json.read_text().replace('"threshold": 4.0', '"threshold": 0.5'))
    with pytest.raises((reg.BundleError, reg.RegistryError)):
        u.promote(registry, "flowguard", "1.1.0", serving_columns=SERVING)
    assert reg.current_version(registry, "flowguard") is None


def test_pointer_move_is_atomic_and_audit_follows_success(fg, registry, monkeypatch):
    u, reg = fg["update"], fg["registry"]
    u.promote(registry, "flowguard", "1.0.0", serving_columns=SERVING)

    def broken_replace(src, dst, *a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError):
        u.promote(registry, "flowguard", "1.1.0", serving_columns=SERVING)
    monkeypatch.undo()
    assert reg.current_version(registry, "flowguard") == "1.0.0"
    assert [e["to"] for e in u.audit_log(registry, "flowguard")] == ["1.0.0"]


def test_rollback_undoes_promotions_in_order(fg, registry):
    u, reg = fg["update"], fg["registry"]
    with pytest.raises(reg.RegistryError):
        u.rollback(registry, "flowguard", serving_columns=SERVING)
    u.promote(registry, "flowguard", "1.0.0", serving_columns=SERVING)
    with pytest.raises(reg.RegistryError):
        u.rollback(registry, "flowguard", serving_columns=SERVING)     # nothing before the first promotion
    u.promote(registry, "flowguard", "1.1.0", serving_columns=SERVING)
    assert u.rollback(registry, "flowguard", serving_columns=SERVING, reason="alarm storm") == "1.0.0"
    assert reg.current_version(registry, "flowguard") == "1.0.0"
    log = u.audit_log(registry, "flowguard")
    assert (log[-1]["action"], log[-1]["from"], log[-1]["to"], log[-1]["reason"]) == ("rollback", "1.1.0", "1.0.0", "alarm storm")
    with pytest.raises(reg.RegistryError):                            # the 1.0.0 promotion has no predecessor
        u.rollback(registry, "flowguard", serving_columns=SERVING)


def test_rollback_through_the_api_restores_exact_scores(fg, registry, monkeypatch):
    from fastapi.testclient import TestClient
    u = fg["update"]
    u.promote(registry, "flowguard", "1.0.0", serving_columns=SERVING)
    run = make_run(4, drop=2.2)        # a fault that only the lower threshold of 1.1.0 catches
    body = {"run_id": "x", "datetime": run["datetime"].astype(str).tolist(),
            **{c: run[c].tolist() for c in SERVING if c != "datetime"}}
    monkeypatch.setenv("FLOWGUARD_ADMIN_TOKEN", "test-token-not-a-secret")
    with TestClient(fg["api"].create_app(registry, "flowguard", SERVING)) as client:
        before = client.post("/predict", json=body).json()
        assert before["model_version"] == "flowguard-1.0.0"
        u.promote(registry, "flowguard", "1.1.0", serving_columns=SERVING)
        assert client.post("/admin/reload", headers={"X-Admin-Token": "nope"}).status_code == 401
        assert client.post("/admin/reload", headers={"X-Admin-Token": "test-token-not-a-secret"}).status_code == 200
        after = client.post("/predict", json=body).json()
        assert after["model_version"] == "flowguard-1.1.0" and after["alarm_events"] != before["alarm_events"]
        u.rollback(registry, "flowguard", serving_columns=SERVING)
        client.post("/admin/reload", headers={"X-Admin-Token": "test-token-not-a-secret"})
        assert client.post("/predict", json=body).json() == before
    monkeypatch.delenv("FLOWGUARD_ADMIN_TOKEN")
    with TestClient(fg["api"].create_app(registry, "flowguard", SERVING)) as client:
        assert client.post("/admin/reload", headers={"X-Admin-Token": "anything"}).status_code == 403

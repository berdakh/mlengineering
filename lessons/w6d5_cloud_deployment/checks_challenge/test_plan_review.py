"""Checks for the w6d5 challenge: the corrected deployment plan and the review's structure."""
from __future__ import annotations

import ipaddress
import json
import re


def test_same_schema_as_the_original(plan, original):
    missing = sorted(set(original) - set(plan))
    assert not missing, f"keep every top-level key of the original plan; missing: {missing}"


def test_credentials_are_short_lived_and_not_admin(plan):
    cred = plan["credentials"]
    assert cred.get("mode") == "sso", "use IAM Identity Center (mode 'sso'), not access keys"
    text = json.dumps(cred).lower()
    assert "administratoraccess" not in text, "the deploying identity must not be an administrator"
    assert not any(k in cred for k in ("stored_at", "access_key_id", "secret_access_key", "iam_user")), \
        "no stored credential file, key material or deployment IAM user"
    assert cred.get("permission_set") or cred.get("role"), "name the permission set or role you deploy with"
    assert not any(r.get("type") == "iam_user" for r in plan["resources"]), "no IAM user for deployment"


def test_budget_exists_with_an_alert(plan):
    b = plan.get("budget")
    assert isinstance(b, dict), "add a budget before anything is created"
    assert float(b.get("limit_usd", 0)) > 0
    alerts = b.get("alerts") or b.get("alert_thresholds_percent") or []
    thresholds = [a["threshold_percent"] if isinstance(a, dict) else a for a in alerts]
    assert thresholds and min(float(t) for t in thresholds) <= 100, "at least one alert at or below 100 %"


def test_registry_immutable_scanned_and_tagged_by_sha(plan):
    reg = plan["registry"]
    assert reg.get("tag_mutability") == "IMMUTABLE"
    assert reg.get("scan_on_push") is True
    assert re.fullmatch(r"[0-9a-f]{7,40}", str(reg.get("image_tag", ""))), "image_tag must be a git SHA"


def test_model_artifacts_are_not_public(plan):
    art = plan.get("model_artifacts")
    buckets = [r for r in plan["resources"] if r.get("type") == "s3_bucket"]
    if art is None or art == {}:
        assert not buckets, "if the bucket is gone, remove it from resources too"
        return
    assert art.get("public_read") is False and art.get("block_public_access") is True
    assert "task role" in str(art.get("access", "")).lower(), "say how the task reads the bucket: its task role"


def test_no_ingress_wider_than_one_address(plan):
    for rule in plan["network"].get("ingress", []):
        net = ipaddress.ip_network(rule["cidr"], strict=False)
        assert net.prefixlen == net.max_prefixlen, f"{rule['cidr']} admits more than one address"


def test_log_retention(plan):
    days = plan["logs"].get("retention_days")
    assert isinstance(days, int) and 1 <= days <= 30


def test_teardown_covers_every_resource(plan):
    planned = {(r["type"], r["name"]) for r in plan["resources"]}
    torn = {(t["type"], t["name"]) for t in plan.get("teardown", [])}
    assert planned and planned <= torn, f"not torn down: {sorted(planned - torn)}"


HEADINGS = ["Summary", "Credentials", "Budget", "Registry", "Model artifacts", "Network", "Logs",
            "Teardown", "Decision"]


def sections(review: str) -> dict[str, str]:
    out, current = {}, None
    for line in review.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current:
            out[current] += line + "\n"
    return out


def test_review_has_every_section_filled_in(review):
    secs = sections(review)
    for h in HEADINGS:
        match = [k for k in secs if k.lower().startswith(h.lower())]
        assert match, f"REVIEW.md needs a '## {h}...' section"
        body = re.sub(r"<!--.*?-->", "", secs[match[0]], flags=re.S).strip()
        assert len(body) >= 40 and "TODO" not in body, f"section '{match[0]}' is not written yet"


def test_review_states_a_decision(review):
    secs = sections(review)
    decision = next(v for k, v in secs.items() if k.lower().startswith("decision")).lower()
    assert "todo" not in decision, "the decision section is not written yet"
    assert re.search(r"\bno-go\b|\bgo with changes\b|\bgo\b", decision), "state go, go with changes, or no-go"

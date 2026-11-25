"""Take two candidate models through gate -> shadow -> promote -> reload -> rollback on real data.

    python labs/w7d4_model_updates_rollback/lab/build_models.py      # first
    python labs/w7d4_model_updates_rollback/lab/update_report.py     # about 10 s
    python labs/w7d4_model_updates_rollback/lab/update_report.py --json results/update.json

Given complete; it works once you have implemented ``flowguard.update``.

Stated choices:
* Gate data: the 7 test experiments of the frozen manifest v2. Neither candidate was tuned on them,
  but every gate decision is one more look at the test set (w3d3); in production a gate runs on
  recent labelled data instead. Slices are the experiment families.
* Gate policy for 1.1.0: non-inferiority with margin 0.05 and a guardrail of 1 false alarm per hour
  (the newly agreed budget). The report also shows what a superiority policy would have decided.
* Serving contract (what the plant gateway sends): datetime and six process sensors, no accelerometers.
* Shadow: 1.0.0 serves, 1.1.0 is scored on the same runs (the 20 valve recordings, one per day,
  built with flowguard.replay).
* The admin token is a throwaway value set in this process's environment, never written to disk.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from flowguard.api import create_app  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.registry import RegistryError, current_version, load_bundle, register  # noqa: E402
from flowguard.replay import build_timeline  # noqa: E402
from flowguard.serving import respond  # noqa: E402
from flowguard.splits import load_splits  # noqa: E402
from flowguard.update import ShadowRunner, audit_log, disagreements, offline_gate, promote, rollback  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
SERVING_COLUMNS = ["datetime", "flow_rate", "pressure", "current", "voltage", "temperature", "thermocouple"]
NAME = "flowguard"


def per_experiment(model, df):
    out = {}
    for eid, g in df.groupby("experiment_id", sort=False):
        g = g.sort_values("t")
        r = evaluate_experiments(g, model.flags(model.score_run(g)), burn_in=model.n_burn,
                                 min_duration=model.min_duration, merge_gap=model.merge_gap)
        out[eid] = {k: r[k] for k in ("n_events", "n_detected", "n_false_alarms", "normal_hours")}
    return out


def run(raw_dir: Path, bundles: Path, workdir: Path) -> dict:
    tidy = load_raw(raw_dir)
    manifest = load_splits(HERE / "splits" / "v2.json")
    test = tidy[tidy["experiment_id"].isin(manifest["test"])].reset_index(drop=True)
    families = {e: e.split("/")[0] for e in manifest["test"]}

    registry = workdir / "registry"
    shutil.rmtree(registry, ignore_errors=True)
    models = {}
    for v in ("1.0.0", "1.1.0", "2.0.0"):
        register(registry, bundles / f"{NAME}-{v}")
        models[v], _ = load_bundle(registry / NAME / v)
    promote(registry, NAME, "1.0.0", serving_columns=SERVING_COLUMNS, actor="report", reason="initial deployment")
    out = {"models": {v: {"sensors": list(m.sensors), "threshold": m.threshold, "min_duration": m.min_duration,
                          "merge_gap": m.merge_gap, **{k: m.metadata.get(k) for k in
                          ("dev_events_detected", "dev_false_alarms", "dev_normal_hours")}}
                      for v, m in models.items()}}

    # 1. Offline gate on the frozen test experiments.
    results = {v: per_experiment(m, test) for v, m in models.items()}
    out["gate"] = {}
    for v, policy in (("1.1.0", "non_inferiority"), ("1.1.0", "superiority"), ("2.0.0", "non_inferiority")):
        g = offline_gate(results["1.0.0"], results[v], policy=policy, margin=0.05, max_false_alarms_per_hour=1.0,
                         slices=families, n_boot=4000, seed=0)
        out["gate"][f"{v} {policy}"] = {"decision": g["decision"], "reasons": g["reasons"],
                                        "recall_current": g["current"]["recall"], "recall_candidate": g["candidate"]["recall"],
                                        "far_candidate": g["candidate"]["false_alarms_per_hour"],
                                        "diff": [g["diff"]["estimate"], g["diff"]["low"], g["diff"]["high"]],
                                        "per_experiment": {e: (results["1.0.0"][e]["n_detected"], results[v][e]["n_detected"])
                                                           for e in manifest["test"]}}
    try:
        promote(registry, NAME, "2.0.0", serving_columns=SERVING_COLUMNS, actor="report", reason="try 2.0.0")
        out["promote_2.0.0"] = "promoted (unexpected)"
    except RegistryError as exc:
        out["promote_2.0.0"] = f"refused: {exc}"

    # 2. Shadow: 1.0.0 serves, 1.1.0 is scored on the same 20 valve recordings.
    valve = sorted((e for e in tidy["experiment_id"].unique() if e.startswith("valve")),
                   key=lambda e: (e.split("/")[0], int(e.split("/")[1])))
    timeline = build_timeline(tidy, valve)
    shadow = ShadowRunner(models["1.0.0"], models["1.1.0"])
    served_equal = True
    for run_id, g in timeline.groupby("run_id", sort=False):
        response = shadow.score(run_id, g)
        served_equal &= response == respond(models["1.0.0"], g)
    out["shadow"] = {**disagreements(shadow.log), "served_responses_identical_to_current": bool(served_equal)}

    # 3. Promote 1.1.0 (the gate said so under the agreed policy), reload the API, then roll back.
    token = secrets.token_hex(16)
    os.environ["FLOWGUARD_ADMIN_TOKEN"] = token
    probe = tidy[tidy["experiment_id"] == "valve1/8"].sort_values("t")
    body = {"run_id": "probe", "datetime": probe["datetime"].astype(str).tolist(),
            **{c: probe[c].tolist() for c in SERVING_COLUMNS if c != "datetime"}}
    steps = []
    with TestClient(create_app(registry, NAME, SERVING_COLUMNS)) as client:
        before = client.post("/predict", json=body).json()
        steps.append(("start", client.get("/version").json()["model_version"], len(before["alarm_events"])))
        promote(registry, NAME, "1.1.0", serving_columns=SERVING_COLUMNS, actor="report",
                reason="gate: non-inferior, guardrail met")
        r = client.post("/admin/reload", headers={"X-Admin-Token": token}).json()
        after = client.post("/predict", json=body).json()
        steps.append(("promote 1.1.0 + reload", r["model_version"], len(after["alarm_events"])))
        bad = client.post("/admin/reload", headers={"X-Admin-Token": "wrong"}).status_code
        restored = rollback(registry, NAME, serving_columns=SERVING_COLUMNS, actor="report", reason="demonstration")
        r = client.post("/admin/reload", headers={"X-Admin-Token": token}).json()
        again = client.post("/predict", json=body).json()
        steps.append((f"rollback to {restored} + reload", r["model_version"], len(again["alarm_events"])))
    del os.environ["FLOWGUARD_ADMIN_TOKEN"]
    out["api"] = {"steps": steps, "reload_with_wrong_token": bad,
                  "scores_after_rollback_identical": again == before,
                  "scores_changed_after_promote": after["scores"] != before["scores"]}
    out["audit"] = [{k: e[k] for k in ("action", "from", "to", "reason")} for e in audit_log(registry, NAME)]
    out["current"] = current_version(registry, NAME)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--bundles", default=str(HERE / "results" / "bundles"))
    ap.add_argument("--json", help="also write the results to this JSON file")
    args = ap.parse_args(argv)
    if not Path(args.raw_dir).is_dir() or not Path(args.bundles).is_dir():
        print("error: run python project/get_skab.py and build_models.py first", file=sys.stderr)
        return 2
    out = run(Path(args.raw_dir), Path(args.bundles), HERE / "results")
    for v, m in out["models"].items():
        print(f"model {v}: {m}")
    for k, g in out["gate"].items():
        d = g["diff"]
        print(f"gate {k}: {g['decision'].upper()}  recall {g['recall_current']:.3f} -> {g['recall_candidate']:.3f}, "
              f"diff {d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}], candidate FA/h {g['far_candidate']:.2f}; {g['reasons']}")
    print("promote 2.0.0:", out["promote_2.0.0"])
    print("shadow:", out["shadow"])
    for step in out["api"]["steps"]:
        print("api:", step)
    print("reload with a wrong token ->", out["api"]["reload_with_wrong_token"])
    print("scores after rollback identical to before:", out["api"]["scores_after_rollback_identical"])
    print("audit:", out["audit"])
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

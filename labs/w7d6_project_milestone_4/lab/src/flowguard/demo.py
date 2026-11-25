"""The monitoring demonstration (milestone 4): one command, a scripted scenario, a generated report.

    python -m flowguard monitor-demo --raw data/raw/skab --splits splits/v2.json \
        --scenario scenarios/demo.toml --out reports

What it does, in order:
1. Builds the shipped model bundle and a bad candidate (same detector, the scenario's too-low threshold),
   registers both in <out>/registry and promotes the shipped one.
2. Calibrates the drift monitor on DEVELOPMENT experiments only (reference = their normal rows; threshold =
   the given quantile of the PSI of each development experiment's normal rows).
3. Starts the service (uvicorn on 127.0.0.1, a free port) from the registry's CURRENT version, with JSON
   logs to <out>/service.log.
4. Plays the scenario's events in order; promote/rollback events switch CURRENT and restart the service.
5. Writes <out>/results.json (machine-readable; the source of every number) and <out>/monitoring_demo.md.
6. Stops the service, also when something fails. results.json records every server pid.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import tomllib
from dataclasses import replace
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from flowguard import __version__
from flowguard.bundle import save_bundle
from flowguard.data import load_raw
from flowguard.monitoring import DriftMonitor, alarm_rate_alert, delayed_label_report, extract_events
from flowguard.registry import Registry
from flowguard.scoring import ZScoreModel
from flowguard.settings import load_settings
from flowguard.splits import dev_experiments, load_splits

MAX_VALUES = 3600
SUMMARY_FORMAT = "{:.4f}"
DRIFT_THRESHOLD = 0.25          # PSI rule of thumb, from the first draft of this report


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Service:
    """One uvicorn process serving a registry version. Always stop() it."""

    def __init__(self, model_dir: Path, settings_path: Path, log_file: Path, src_dir: Path) -> None:
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        env = {**{k: v for k, v in os.environ.items() if k != "FLOWGUARD_FAULTS"},
               "PYTHONPATH": str(src_dir), "FLOWGUARD_MODEL_DIR": str(model_dir),
               "FLOWGUARD_SETTINGS": str(settings_path), "FLOWGUARD_LOG_FILE": str(log_file)}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "--factory", "flowguard.api:app_from_env", "--host", "127.0.0.1",
             "--port", str(self.port), "--log-level", "warning"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                if httpx.get(self.url + "/readyz", timeout=0.5).status_code == 200:
                    return
            except httpx.TransportError:
                pass
            if self.proc.poll() is not None:
                break
            time.sleep(0.1)
        self.stop()
        raise RuntimeError(f"service on port {self.port} did not become ready")

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

    def version(self) -> str:
        return httpx.get(self.url + "/version", timeout=5).json()["model_version"]


def _series(tidy: pd.DataFrame, experiment: str, sensor: str) -> pd.DataFrame:
    g = tidy[tidy["experiment_id"] == experiment].sort_values("t")
    if g.empty:
        raise ValueError(f"experiment {experiment!r} is not in the data")
    return g


def _replay(service: Service, x: np.ndarray, n_burn: int, start: int, end: int, machine: str) -> dict:
    burn = x[:n_burn].tolist()
    values = x[start:end]
    alarms: list[bool] = []
    oos = degraded = 0
    for i in range(0, len(values), MAX_VALUES):
        r = httpx.post(service.url + "/predict", timeout=30, headers={"X-Machine-ID": machine},
                       json={"burn_in": burn, "values": values[i:i + MAX_VALUES].tolist()})
        r.raise_for_status()
        d = r.json()
        alarms += d["above_threshold"]
        oos += len(d["out_of_support"])
        degraded += int(d["degraded"])
    return {"alarms": alarms, "oos": oos, "degraded_responses": degraded}


def _bundle(model: ZScoreModel, directory: Path) -> Path:
    return save_bundle(model, directory, {"built_by": "flowguard.demo", "package_version": __version__})


def run_demo(raw: str | Path, splits: str | Path, scenario_path: str | Path, out: str | Path,
             config: str | Path = "configs/model.toml", settings_path: str | Path = "configs/service.toml") -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scenario = tomllib.loads(Path(scenario_path).read_text())
    src_dir = Path(__file__).resolve().parents[1]
    settings_path = Path(settings_path).resolve()
    settings = load_settings(settings_path)
    good = ZScoreModel(**tomllib.loads(Path(config).read_text()))
    bad = replace(good, threshold=float(scenario["model"]["bad_threshold"]),
                  model_version=scenario["model"]["bad_version"])

    registry = Registry(out / "registry")
    for m in (good, bad):
        if m.model_version not in registry.versions():
            registry.register(_bundle(m, out / "staging" / m.model_version))
    shutil.rmtree(out / "staging", ignore_errors=True)
    registry.promote(good.model_version, "demo start: shipped model")

    tidy = load_raw(raw)
    manifest = load_splits(splits)
    dev = tidy[tidy["experiment_id"].isin(set(dev_experiments(manifest)))]
    normal_dev = dev[dev["anomaly"] == 0]
    windows = [g[good.sensor].to_numpy(dtype=float) for _, g in normal_dev.groupby("experiment_id")]
    drift = DriftMonitor.calibrate(normal_dev[good.sensor].to_numpy(dtype=float), windows,
                                   n_bins=int(scenario.get("drift_bins", 10)),
                                   quantile=float(scenario.get("drift_quantile", 1.0)))
    budget = float(scenario["alarm_rate_budget"])

    log_file = out / "service.log"
    log_file.write_text("")
    pids: list[int] = []
    results: dict = {"scenario": scenario.get("name", ""), "package_version": __version__,
                     "drift_threshold": drift.threshold, "alarm_rate_budget": budget, "events": []}
    service = Service(registry.path(), settings_path, log_file, src_dir)
    pids.append(service.proc.pid)
    labelled: list[dict] = []
    try:
        for ev in scenario["event"]:
            kind = ev["kind"]
            if kind in ("promote", "rollback"):
                if kind == "promote":
                    registry.promote(bad.model_version if ev["version"] == "bad" else good.model_version,
                                     ev.get("reason", ""))
                    service = Service(registry.path(), settings_path, log_file, src_dir)
                    pids.append(service.proc.pid)
                else:
                    registry.rollback(ev.get("reason", ""))
            record = {"id": ev["id"], "kind": kind, "expected": ev["expect"], "model_version": service.version()}
            signals: list[str] = []
            if kind == "labels":
                report = delayed_label_report([r for r in labelled if r["experiment"] in set(ev["experiments"])])
                record["observed"] = report
                if report["labelled_replays"]:
                    signals.append("delayed_eval")
            else:
                g = _series(tidy, ev["experiment"], good.sensor)
                x = g[good.sensor].to_numpy(dtype=float) * float(ev.get("scale", 1.0))
                start, end = ev.get("rows", [0, len(x)])
                rep = _replay(service, x, good.n_burn_in, start, end, ev["experiment"])
                flags = rep["alarms"]
                events = extract_events(flags, good.min_duration, good.merge_gap)
                rate, rate_alert = alarm_rate_alert(sum(flags), len(flags), budget)
                psi_value, drift_alert = drift.check(x[start:end])
                record["observed"] = {"values": len(flags), "alarm_values": int(sum(flags)), "alarm_rate": rate,
                                      "alarm_events": len(events), "out_of_support_values": rep["oos"],
                                      "degraded_responses": rep["degraded_responses"], "psi": psi_value}
                if rep["oos"]:
                    signals.append("out_of_support")
                if drift_alert:
                    signals.append("drift")
                if rate_alert:
                    signals.append("alarm_rate")
                if events:
                    signals.append("detector")
                if kind == "rollback" and record["model_version"] == good.model_version and not rate_alert:
                    signals.append("version_restored")
                labels = g["anomaly"].to_numpy(dtype=int)[start:end].tolist()
                if kind in ("normal", "fault") and record["model_version"] == good.model_version:
                    labelled.append({"experiment": ev["experiment"], "events": events, "labels": labels})
            record["signals"] = signals
            expected = ev["expect"]
            record["as_expected"] = (not signals) if expected == "no_alert" else (expected in signals)
            results["events"].append(record)
            print(f"{ev['id']:16s} {kind:9s} {record['model_version']:26s} signals={signals} "
                  f"{'as expected' if record['as_expected'] else 'NOT AS EXPECTED'}")
        metrics_text = httpx.get(service.url + "/metrics", timeout=5).text
    finally:
        service.stop()
    results["server"] = {"pids": pids, "restarts": len(pids) - 1,
                         "stopped": all(_pid_gone(p) for p in pids)}
    results["registry_history"] = registry.history()
    results["final_metrics"] = [ln for ln in metrics_text.splitlines() if not ln.startswith("flowguard_requests")]
    results["summary"] = _summary(results)
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    _figures(results, out)
    (out / "monitoring_demo.md").write_text(render_report(results, out))
    return results


def _pid_gone(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _summary(results: dict) -> dict:
    evs = results["events"]
    replays = [e for e in evs if "values" in e.get("observed", {})]
    labels = [e for e in evs if e["kind"] == "labels"]
    last = labels[-1]["observed"] if labels else {}
    return {"events": len(evs), "events_as_expected": sum(e["as_expected"] for e in evs),
            "drift_threshold": results["drift_threshold"], "alarm_rate_budget": results["alarm_rate_budget"],
            "values_scored": sum(e["observed"]["values"] for e in replays),
            "out_of_support_values": sum(e["observed"]["out_of_support_values"] for e in replays),
            "faults_labelled": last.get("faults", 0), "faults_detected": last.get("faults_detected", 0),
            "false_alarm_events_labelled": last.get("false_alarm_events", 0),
            "server_restarts": results["server"]["restarts"]}


def _fmt(v) -> str:
    if isinstance(v, float):
        return SUMMARY_FORMAT.format(v)
    return str(v)


def render_report(results: dict, out: Path) -> str:
    """Markdown generated from results ONLY: every number in it is in results.json."""
    lines = [f"# Monitoring demonstration: {results['scenario']}", "",
             f"Generated by `python -m flowguard monitor-demo` (flowguard {results['package_version']}). "
             "Do not edit by hand: re-run the command.", "", "## Timeline", "",
             "| # | Event | Kind | Model version | Expected | Signals fired | Result |",
             "|---|---|---|---|---|---|---|"]
    for i, e in enumerate(results["events"], 1):
        fired = ", ".join(e["signals"]) or "none"
        if e["as_expected"]:
            verdict = "as expected"
        elif e["expected"] == "no_alert":
            verdict = "UNEXPECTED ALERT"
        else:
            verdict = f"not detected (expected {e['expected']})"
        lines.append(f"| {i} | {e['id']} | {e['kind']} | {e['model_version']} | {e['expected']} | {fired} | {verdict} |")
    lines += ["", "## Per-event observations", "",
              "| Event | Values | Alarm rate | Alarm events | Out-of-support values | PSI | Degraded responses |",
              "|---|---|---|---|---|---|---|"]
    for e in results["events"]:
        o = e["observed"]
        if "values" in o:
            lines.append(f"| {e['id']} | {o['values']} | {_fmt(o['alarm_rate'])} | {o['alarm_events']} | "
                         f"{o['out_of_support_values']} | {_fmt(o['psi'])} | {o['degraded_responses']} |")
    labels = [e for e in results["events"] if e["kind"] == "labels"]
    for e in labels:
        o = e["observed"]
        recall = "n/a" if o["event_recall"] is None else _fmt(o["event_recall"])
        lines += ["", f"Delayed labels ({e['id']}): {o['labelled_replays']} labelled replays, {o['faults']} labelled "
                  f"faults, {o['faults_detected']} detected, {o['false_alarm_events']} false alarm events, "
                  f"event recall {recall}. Covers labelled traffic only."]
    lines += ["", "## Summary", "", "| Quantity | Value |", "|---|---|"]
    summary = {**results["summary"], "drift_threshold": DRIFT_THRESHOLD}
    lines += [f"| {k} | {_fmt(v)} |" for k, v in summary.items()]
    if (out / "figures" / "timeline.svg").is_file():
        lines += ["", "![Per-event alarm rate, drift PSI and out-of-support share](figures/timeline.svg)"]
    lines += ["", "## Registry history", ""]
    lines += [f"* {h['action']} -> `{h['version']}`: {h['reason']}" for h in results["registry_history"]]
    lines += ["", f"Service processes started: {len(results['server']['pids'])}; all stopped: "
              f"{results['server']['stopped']}.", ""]
    return "\n".join(lines)


def _figures(results: dict, out: Path) -> None:
    """Optional: a timeline figure if matplotlib is installed (the report is complete without it)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    evs = [e for e in results["events"] if "values" in e["observed"]]
    if not evs:
        return
    names = [e["id"] for e in evs]
    panels = [("alarm rate", [e["observed"]["alarm_rate"] for e in evs], results["alarm_rate_budget"]),
              ("drift PSI", [e["observed"]["psi"] for e in evs], results["drift_threshold"]),
              ("out-of-support share", [e["observed"]["out_of_support_values"] / max(e["observed"]["values"], 1)
                                        for e in evs], None)]
    fig, axes = plt.subplots(len(panels), 1, figsize=(7.5, 6.0), sharex=True)
    for ax, (title, vals, limit) in zip(axes, panels):
        ax.bar(range(len(vals)), vals, color="#2a78d6")
        if limit is not None:
            ax.axhline(limit, color="#d03b3b", lw=1, ls="--")
            ax.text(len(vals) - 0.5, limit, " alert above", color="#d03b3b", fontsize=8, va="bottom", ha="right")
        ax.set_ylabel(title, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xticks(range(len(names)), names, rotation=20, ha="right", fontsize=8)
    fig.suptitle("Monitoring signals per scenario event", x=0.02, ha="left", fontweight="bold", fontsize=11)
    (out / "figures").mkdir(exist_ok=True)
    fig.savefig(out / "figures" / "timeline.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)

# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/44_project_m3_monitoring.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 44 · Project milestone 3: monitoring demo
#
# **Week 11 · lab (project milestone) · about 120 minutes**
#
# In milestone 2 (notebook 36) the SKAB fault detector went behind `POST /score`. This milestone treats the 34
# SKAB experiments as if they had arrived one after another in production, and builds the monitoring an operator
# would want: a log record per experiment, an input-drift table, an operations table with alerts, one dashboard,
# and a short operations note.
#
# **What you will build** (each exercise uses the previous ones):
#
# 1. a monitoring record for one experiment (detector output, model version, latency);
# 2. a run over all experiments that writes a JSON Lines log and survives experiments it cannot score;
# 3. a drift table: PSI of each experiment's normal operation against a reference;
# 4. an operations table that joins the log and the drift table and raises drift alerts;
# 5. a two-panel dashboard;
# 6. an operations note: what is monitored, what you found, and its limits.
#
# **What you need:** notebooks 36 (milestone 2), 42 (logging, metrics, alerts) and 43 (PSI). No new concepts.
#
# **How grading works:** each exercise has a grader cell. Grading uses small synthetic sensor frames, so it
# works offline; the real SKAB data is used for the demo itself.
#
# SKAB is a public research dataset from a laboratory testbed. This project is an educational prototype, not a
# monitoring system for real equipment.

# %%
# --- Setup: works in Google Colab AND on your own computer. Safe to re-run. ---
# In Colab this downloads the course (about 30 s) and installs what it needs (about a minute, once
# per session). On your computer it just finds the course folder.
import os, sys, subprocess
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/mlengineering").exists():
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/berdakh/mlengineering.git", "/content/mlengineering"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                    "/content/mlengineering/requirements.txt"], check=True)
REPO_ROOT = Path("/content/mlengineering") if "google.colab" in sys.modules else next(
    p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
from mlcourse.grader import grade, quiz
print("Ready. Course folder:", REPO_ROOT)

# %% [markdown]
# ## The data and the detector
#
# SKAB is licensed under GPL-3.0, so the course does not copy it into its repository: `project/get_skab.py`
# downloads it (about 4 MB, pinned to one version, with a checksum per file) into `data/raw/skab/`. The next cell
# runs it only if the data is not there yet, then loads the 34 experiments: 16 in `valve1`, 4 in `valve2` and 14
# in `other`, one row per second, eight sensor columns plus the labels.

# %%
import json
import shutil
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mlcourse.graders.w11 import FLOW, detect, psi, use

SKAB = REPO_ROOT / "data" / "raw" / "skab"
if not (SKAB / "MANIFEST.json").is_file():
    subprocess.run([sys.executable, "project/get_skab.py"], check=True)

experiments = {}
for group in ["valve1", "valve2", "other"]:
    for path in sorted((SKAB / group).glob("*.csv"), key=lambda p: int(p.stem)):
        experiments[f"{group}/{path.stem}"] = pd.read_csv(path, sep=";")
print(len(experiments), "experiments; columns:", list(experiments["valve1/0"].columns))

WORK = REPO_ROOT / "runs" / "week11" / "monitoring"   # Git ignores runs/
shutil.rmtree(WORK, ignore_errors=True)                # start clean on every run of the notebook

# %% [markdown]
# **The detector** is milestone 2's, provided here as `detect(values, burn_in=100, threshold=3.0, min_run=5)`: it
# uses the first 100 readings of the flow rate as the baseline, computes $|z|$ for every reading, and raises an
# alarm at a reading once the last 5 readings after the burn-in all had $|z| > 3$. It returns `(alarms, z)`, the
# list of alarm positions and the array of $|z|$, and raises `ValueError` for a series shorter than the burn-in or
# a constant burn-in.

# %%
alarms, z = detect(experiments["valve1/10"][FLOW].to_numpy())
print(len(alarms), "alarm readings; first at", alarms[0], "| largest |z|:", round(float(z.max()), 2))

# %% [markdown]
# ## Exercise 1 · a monitoring record
#
# Write `monitor_record(name, df, model_version, column=FLOW)` returning a dict with:
# `"experiment"` (the name), `"model_version"`, `"n_readings"` (rows), `"n_alarms"`, `"first_alarm"` (position of
# the first alarm, or `None`), `"max_z"` (largest $|z|$, rounded to 2 decimals), `"flow_mean"` (mean of the
# column) and `"latency_ms"` (how long `detect` took, measured with `time.perf_counter()` before and after, in
# milliseconds). Convert NumPy numbers to plain `int`/`float` so the record can be written as JSON.

# %%
def monitor_record(name, df, model_version, column=FLOW):
    ### BEGIN SOLUTION
    start = time.perf_counter()
    alarms, z = detect(df[column].to_numpy())
    latency_ms = (time.perf_counter() - start) * 1000
    return {"experiment": name, "model_version": model_version, "n_readings": int(len(df)),
            "n_alarms": len(alarms), "first_alarm": int(alarms[0]) if alarms else None,
            "max_z": round(float(np.max(z)), 2), "flow_mean": float(df[column].mean()),
            "latency_ms": latency_ms}
    ### END SOLUTION


use(monitor_record, "valve1/10", experiments["valve1/10"], "zscore_v1")

# %%
grade("w11.monitor_record", monitor_record)

# %% [markdown]
# ## Exercise 2 · run the monitor over every experiment
#
# Write `run_monitoring(experiments, log_path, model_version)`: for each `(name, df)` in the dict, build the
# record with `monitor_record`; if that raises `ValueError` (the detector cannot score the series), build instead
# `{"experiment": name, "model_version": model_version, "error": str(err)}`. Append **every** record to
# `log_path` as one JSON line (create the folder; append mode), and return a DataFrame of the records.
#
# Logging the failure instead of crashing or silently skipping is what makes the log trustworthy: every input
# appears in it, scored or not.

# %%
def run_monitoring(experiments, log_path, model_version):
    ### BEGIN SOLUTION
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for name, df in experiments.items():
        try:
            record = use(monitor_record, name, df, model_version)
        except ValueError as err:
            record = {"experiment": name, "model_version": model_version, "error": str(err)}
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        records.append(record)
    return pd.DataFrame(records)
    ### END SOLUTION


log_df = use(run_monitoring, experiments, WORK / "skab_log.jsonl", "zscore_v1")
print(len(log_df), "records;", "errors:", int(log_df["error"].notna().sum()) if "error" in log_df else 0)
print("experiments with at least one alarm:", int((log_df["n_alarms"] > 0).sum()))
log_df[["experiment", "n_readings", "n_alarms", "first_alarm", "max_z"]].head(8)

# %%
grade("w11.run_monitoring", run_monitoring)

# %% [markdown]
# All 34 experiments were scored (no errors) and 28 raised at least one alarm. The graders also feed your function
# a too-short and a constant series, to check that those are logged as errors.
#
# ## Exercise 3 · a drift table
#
# Which **reference** should today's inputs be compared with? SKAB ships an `anomaly-free` recording, the obvious
# candidate. But it was recorded at a different operating point (its flow rate averages about 125 L/min; the
# valve experiments about 31), so against it **every** experiment drifts on almost every sensor, and the monitor
# says nothing useful. A better reference is the data the detector was developed on: the **normal operation** of
# the `valve1` experiments, i.e. their first 400 readings (in every `valve1` file the labelled anomaly starts
# after reading 565).
#
# To check experiments' inputs, not their faults, compare each experiment's own first 400 readings with that
# reference. (One exception to keep in mind: in `other/2` the anomaly starts at reading 104, so its first 400
# readings include part of the fault.)
#
# Write `drift_table(reference, experiments, features, bins=10)` returning a DataFrame with one row per experiment
# (index = the names, in order) and one column per feature (in order), each cell the `psi` of that feature against
# the reference. `psi` is notebook 43's function, imported above.

# %%
def drift_table(reference, experiments, features, bins=10):
    ### BEGIN SOLUTION
    rows = {name: {f: psi(reference[f], df[f], bins) for f in features} for name, df in experiments.items()}
    table = pd.DataFrame.from_dict(rows, orient="index")[list(features)]
    table.index.name = "experiment"
    return table
    ### END SOLUTION


reference = pd.concat([df.iloc[:400] for name, df in experiments.items() if name.startswith("valve1/")])
normal_operation = {name: df.iloc[:400] for name, df in experiments.items()}
DRIFT_FEATURES = ["Current", "Pressure", "Voltage"]
drift = use(drift_table, reference, normal_operation, DRIFT_FEATURES)
drift.round(2).iloc[[0, 5, 16, 20, 24, 30]]

# %%
grade("w11.drift_table", drift_table)

# %% [markdown]
# **Try it.** Add `"Temperature"` and `"Accelerometer1RMS"` to `DRIFT_FEATURES` and look at the table again.

# %%
try_features = ["Temperature", "Accelerometer1RMS"]
use(drift_table, reference, normal_operation, try_features).round(2).groupby(lambda n: n.split("/")[0]).median()

# %% [markdown]
# Even within `valve1`, whose own data is the reference, the median PSI is 5.99 for temperature and 0.90 for the
# accelerometer: their levels differ from one recording to the next. A drift alert on them would fire for almost
# every experiment. That is why the demo watches current, pressure and voltage, and why
# the detector itself uses each experiment's own burn-in instead of a fixed baseline. Write this down for the
# note: it is a finding, not a failure.
#
# ## Exercise 4 · the operations table
#
# Write `ops_table(log_df, drift_df, psi_threshold=0.25)` returning a DataFrame indexed like `drift_df` (one row per
# experiment, same order) with the columns:
#
# * `n_alarms`: from the log (NaN for an experiment whose record has no `n_alarms`, e.g. an error);
# * `max_psi`: the largest PSI in that experiment's row of `drift_df`;
# * `drift_alert`: `max_psi > psi_threshold`;
# * `error`: `True` if the experiment's log record has an `error` message.
#
# Hint: `log_df.set_index("experiment")`, then `.reindex(drift_df.index)` on the columns you need; the log may
# have no `error` column at all if nothing failed.

# %%
def ops_table(log_df, drift_df, psi_threshold=0.25):
    ### BEGIN SOLUTION
    log = log_df.set_index("experiment")
    table = pd.DataFrame(index=drift_df.index)
    table["n_alarms"] = log["n_alarms"].reindex(table.index) if "n_alarms" in log else np.nan
    table["max_psi"] = drift_df.max(axis=1)
    table["drift_alert"] = table["max_psi"] > psi_threshold
    errors = log["error"].reindex(table.index) if "error" in log else pd.Series(np.nan, index=table.index)
    table["error"] = errors.notna()
    return table
    ### END SOLUTION


ops = use(ops_table, log_df, drift)
summary = ops.groupby(lambda n: n.split("/")[0]).agg(experiments=("max_psi", "size"),
                                                    drift_alerts=("drift_alert", "sum"),
                                                    median_alarms=("n_alarms", "median"))
summary

# %%
grade("w11.ops_table", ops_table)

# %% [markdown]
# No `valve1` or `valve2` experiment raises a drift alert; all 14 `other` experiments do, through the motor
# current. The `other` experiments were recorded with a different setup, so their inputs really do differ from
# the reference: before trusting the detector on them, you would want to know why.
#
# ## Exercise 5 · a dashboard
#
# Write `make_dashboard(table, psi_threshold)` returning a Figure with **two** bar panels (one bar per experiment):
# the `max_psi` per experiment with the threshold drawn as a horizontal line (`ax.axhline`), and the `n_alarms`
# per experiment (use `table["n_alarms"].fillna(0)` so failed experiments show as 0). Give both panels a title.
# A log scale (`ax.set_yscale("log")`) helps for PSI.

# %%
def make_dashboard(table, psi_threshold):
    ### BEGIN SOLUTION
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    colours = ["tab:red" if alert else "tab:blue" for alert in table["drift_alert"]]
    top.bar(table.index, table["max_psi"], color=colours)
    top.axhline(psi_threshold, color="black", ls="--", lw=1)
    top.set_yscale("log")
    top.set_title(f"Largest input PSI per experiment (red: above {psi_threshold})", fontsize=10)
    bottom.bar(table.index, table["n_alarms"].fillna(0), color="tab:grey")
    bottom.set_title("Detector alarm readings per experiment", fontsize=10)
    bottom.tick_params(axis="x", rotation=90, labelsize=7)
    fig.tight_layout()
    return fig
    ### END SOLUTION


try:
    fig = make_dashboard(ops, 0.25)
    fig.savefig(WORK / "dashboard.png", dpi=120)
    plt.show()
except NotImplementedError:
    print("(finish Exercise 5 to see the dashboard)")

# %%
grade("w11.make_dashboard", make_dashboard)

# %% [markdown]
# ## Exercise 6 · the operations note
#
# Write `ops_note`, a short Markdown text (120-400 words) for the person who will run this monitor, with exactly
# these three headings:
#
# * `## What is monitored`: what the log records, which inputs are checked for drift and against which reference,
#   and the alert rule;
# * `## What we found`: how many experiments were monitored, how many raised a drift alert, how many failed to be
#   scored, and what that means. Quote the numbers from your tables;
# * `## Limits`: what this monitoring cannot tell you (think: labels, the choice of reference, the sensors left
#   out, the size of the dataset).
#
# The grader checks the headings, the length, and that the number of experiments and of drift alerts appear.

# %%
### BEGIN SOLUTION
n_exp, n_alerts = len(ops), int(ops["drift_alert"].sum())
n_errors = int(ops["error"].sum())
ops_note = f"""## What is monitored

Every scored experiment writes one JSON line: experiment, model version (zscore_v1), number of readings, number
of alarm readings, first alarm, largest |z|, mean flow and scoring latency. Experiments that cannot be scored are
logged with an error message instead of being skipped. Input drift is the PSI of each experiment's first 400
readings (normal operation) against the first 400 readings of the 16 valve1 experiments, for motor current,
pressure and voltage. A drift alert fires when the largest PSI is above 0.25.

## What we found

{n_exp} experiments were monitored and {n_errors} failed to be scored. {n_alerts} raised a drift alert: all of
them in the "other" group, through the motor current, which runs at a different level there. No valve1 or valve2
experiment raised one. Temperature and vibration differ between almost all recordings, even within valve1, so
they are not used for alerting; the detector is unaffected because it uses each experiment's own burn-in.

## Limits

Drift says the inputs differ, not that the detector is wrong: whether it still finds faults needs labels, which
a real deployment would get late or not at all. The reference is the data the detector was developed on, so
valve1 compares partly with itself. Sensors left out of the drift check can change unnoticed. 34 experiments
from one testbed are far too few to set thresholds with confidence; 0.25 is a starting point, not a calibrated
value.
"""
### STARTER
ops_note = """## What is monitored

YOUR TEXT HERE

## What we found

YOUR TEXT HERE

## Limits

YOUR TEXT HERE
"""
### END SOLUTION
print(ops_note)

# %%
grade("w11.ops_note", (ops_note, ops))

# %%
(WORK / "OPERATIONS_NOTE.md").write_text(ops_note)
print("saved:", (WORK / "OPERATIONS_NOTE.md").relative_to(REPO_ROOT), "and", (WORK / "dashboard.png").relative_to(REPO_ROOT))

# %% [markdown]
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c44-01.svg" alt="34 SKAB experiments go through the detector into a monitoring log, and into a drift table of normal operation against a reference; the log and the drift table are joined into an ops table, which feeds the dashboard and the operations note" style="max-width:100%">
#
# ## Quiz
#
# **Q1.** Against SKAB's `anomaly-free` recording, every experiment drifts on almost every sensor. What is the
# right conclusion?
#
# - a) PSI is broken.
# - b) The reference was recorded at a different operating point; drift monitoring needs a reference that matches
#   how the system normally runs.
# - c) The anomalies cause the drift.
# - d) More bins would fix it.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.44_q1", answer)

# %% [markdown]
# **Q2.** Why keep the detector's alarms separate from the operations alerts (errors, drift)?
#
# - a) Alarms are the product's output; ops alerts are about the system. Mixing them would page the on-call
#   engineer for every fault the detector correctly found.
# - b) Alarms should not be logged.
# - c) Alarms are always wrong.
# - d) Because of latency.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.44_q2", answer)

# %% [markdown]
# **Q3.** An experiment's burn-in is constant, so the detector raises `ValueError`. What should the monitor do?
#
# - a) Crash, so someone notices.
# - b) Skip it silently.
# - c) Log a score of 0.
# - d) Log a record with the error message, so the failure is counted and visible.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.44_q3", answer)

# %% [markdown]
# **Q4.** In a real deployment of this detector, what can you monitor immediately, and what only later?
#
# - a) Recall immediately, inputs later.
# - b) Only input drift, ever.
# - c) Inputs, errors and alarm rates immediately; recall only when labels exist.
# - d) Only latency.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.44_q4", answer)

# %% [markdown]
# ## Reflection
#
# Write three or four sentences for yourself: which alert would you trust enough to be woken up by? Which would you
# turn into a weekly report instead? What would you need (data, labels, time) to set the threshold properly?
#
# ## What to show in your portfolio
#
# - `runs/week11/monitoring/OPERATIONS_NOTE.md` and `dashboard.png`, copied into your project repository's `docs/`.
# - The monitoring functions (record, run, drift table, ops table) as a module with the tests from this notebook's
#   ideas: a too-short series, a constant series, a shifted sensor.
# - One paragraph in your README: what is monitored, the reference, the alert rule, and its limits.
#
# Next week (notebook 45) you put the three milestones together into one finished project.

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("44", "reading")
# mark("44", "guided")

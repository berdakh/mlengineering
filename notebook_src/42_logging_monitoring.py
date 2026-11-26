# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/42_logging_monitoring.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 42 · Logging and monitoring a model service
#
# **Week 11 · lesson · about 90 minutes**
#
# Once a model service is deployed, nobody watches it by hand. Instead it writes a **log** of what it does, the
# logs are turned into **metrics**, metrics are shown on a **dashboard**, and **alerts** call a person only when
# something needs them. This notebook builds each step for the churn service from Week 9, on a simulated two-day
# log, entirely in Colab.
#
# **What you will learn in this notebook**
#
# - Structured logging: one JSON object per request, with the fields you will need later and no personal data.
# - Python's `logging` module, and a JSON formatter for it.
# - Service metrics per time window: request count, error rate, latency percentiles, share of positive predictions.
# - A three-panel dashboard with matplotlib.
# - Alert rules that fire when a person must act, and not on every blip.
#
# **What you need:** Week 9 (the prediction API), Week 3 (pandas `groupby`). No monitoring experience is assumed.
#
# **How grading works:** after each exercise there is a grader cell. Run it and it tells you immediately
# whether your answer works, and if not, what to look at.

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

# %%
import json
import logging
import shutil
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mlcourse.graders.w11 import FEATURES, simulate_requests, use

WORK = REPO_ROOT / "runs" / "week11"          # Git ignores runs/
shutil.rmtree(WORK / "logs", ignore_errors=True)  # start clean on every run of the notebook
print("features the churn model uses:", FEATURES)

# %% [markdown]
# ## 1. Why print() is not enough: structured logs
#
# **Why.** At 3 a.m. someone asks: "how slow was model v3 between 06:00 and 09:00, and how many requests failed?"
# If your service printed sentences like `predicted 1 for customer in 35ms`, answering means writing fragile text
# searches. If it wrote **structured** records, it is one line of pandas.
#
# **Idea.** A **structured log** writes one **JSON object per line** (the format is called **JSON Lines**,
# `.jsonl`). Every record has the same fields, so machines can filter and aggregate them:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c42-01.svg" alt="The service answers each request and writes one JSON line per request to a log; the log is turned into metrics per window (requests, error rate, p95 latency, positive rate) which feed a dashboard for looking and alert rules for acting; a sustained breach notifies a person" style="max-width:100%">
#
# What a prediction record should contain:
#
# | Field | Why |
# |---|---|
# | `time` (UTC, ISO 8601) | order events; join with other systems. Always UTC: time zones cause bugs |
# | `request_id` | follow one request through several services |
# | `model_version` | which model answered (essential after an update) |
# | `latency_ms` | how long it took |
# | `prediction` | what the model said (to compare with labels later) |
# | `inputs` | only the model's features, to debug and to detect drift |
#
# What it must **not** contain: personal data the model does not need (names, emails, phone numbers, addresses),
# secrets, or whole request bodies "just in case". Logs are read by many people and kept for a long time; data
# protection law (such as the EU's GDPR) applies to them too. The safe pattern is an **allow-list**: copy the fields
# you need, rather than deleting the fields you remember to delete.
#
# **See it.**

# %%
record = {"time": datetime.now(timezone.utc).isoformat(), "request_id": "req-0001", "model_version": "churn_v3",
          "latency_ms": 31.4, "prediction": 1, "inputs": {"recency_days": 40, "segment": "consumer"}}
line = json.dumps(record)
print(line)
print(json.loads(line)["model_version"])

# %% [markdown]
# **Try it.** Change `datetime.now(timezone.utc)` to `datetime.now()` and print `.isoformat()`. What is missing
# from the end of the string, and why would that hurt when two servers are in different countries?
#
# ### Exercise 1 · a safe prediction record
#
# Write `log_record(request_id, model_version, features, prediction, latency_ms, allowed=FEATURES)` returning a
# dict with exactly these keys:
#
# * `"time"`: `datetime.now(timezone.utc).isoformat()`;
# * `"request_id"`, `"model_version"`, `"prediction"`: as given;
# * `"latency_ms"`: as a float rounded to 1 decimal;
# * `"inputs"`: a dict with only the keys of `allowed` that are present in `features` (loop over `allowed`);
# * `"n_missing"`: how many names in `allowed` are absent from `features`.

# %%
def log_record(request_id, model_version, features, prediction, latency_ms, allowed=FEATURES):
    ### BEGIN SOLUTION
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "model_version": model_version,
        "latency_ms": round(float(latency_ms), 1),
        "prediction": prediction,
        "inputs": {name: features[name] for name in allowed if name in features},
        "n_missing": sum(1 for name in allowed if name not in features),
    }
    ### END SOLUTION


incoming = {"recency_days": 12, "orders_90d": 3, "spend_90d": 81.5, "tenure_days": 400, "segment": "consumer",
            "email": "someone@example.com"}
use(log_record, "req-0002", "churn_v3", incoming, 1, 28.04)

# %%
grade("w11.log_record", log_record)

# %% [markdown]
# ### Exercise 2 · append a record to a log file
#
# Write `append_jsonl(path, record)`: create the parent folder if needed (`Path(path).parent.mkdir(parents=True,
# exist_ok=True)`), open the file in **append** mode (`"a"`), write `json.dumps(record)` and a newline. Return the
# path.

# %%
def append_jsonl(path, record):
    ### BEGIN SOLUTION
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return path
    ### END SOLUTION


# %%
grade("w11.append_jsonl", append_jsonl)

# %% [markdown]
# ### Exercise 3 · read a log, surviving broken lines
#
# Real logs contain the odd broken line (a process killed mid-write, a stray message). Write `read_jsonl(path)`
# returning `(DataFrame of the good records, number of bad lines)`. Skip blank lines silently. A line that is not
# valid JSON (`json.JSONDecodeError`), or valid JSON that is not an object (dict), counts as bad.

# %%
def read_jsonl(path):
    ### BEGIN SOLUTION
    rows, bad = [], 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(obj, dict):
            rows.append(obj)
        else:
            bad += 1
    return pd.DataFrame(rows), bad
    ### END SOLUTION


# %% [markdown]
# **See it.** Write three records and one broken line, then read them back.

# %%
log_path = WORK / "logs" / "service.jsonl"
for i, latency in enumerate([31.0, 45.2, 29.9]):
    use(append_jsonl, log_path, use(log_record, f"req-{i}", "churn_v3", incoming, int(latency > 40), latency))
with open(log_path, "a") as fh:
    fh.write('{"time": "2026-03-02T10:00:00+00:00", "request_id": "req-3", "lat\n')   # cut off mid-write
frame, n_bad = use(read_jsonl, log_path)
print("bad lines:", n_bad)
frame[["request_id", "model_version", "latency_ms", "prediction"]]

# %%
grade("w11.read_jsonl", read_jsonl)

# %% [markdown]
# ## 2. The logging module, with a JSON formatter
#
# **Why.** Real services do not open files themselves for every record. They use Python's **`logging`** module:
# one call (`log.info(...)`) and the configuration decides where it goes (the console, a file, a log service),
# which **levels** are kept, and how each line is **formatted**.
#
# **Idea.** Levels, from least to most serious: `DEBUG` (details for developers), `INFO` (normal events, e.g.
# "prediction served"), `WARNING` (something odd but handled, e.g. a slow request), `ERROR` (a request failed),
# `CRITICAL` (the service cannot work). A **logger** creates records; a **handler** sends them somewhere; a
# **formatter** turns a record into text. Extra structured fields travel in `extra={...}`.
#
# **See it.** The default formatter writes plain text.

# %%
demo = logging.getLogger("demo_service")
demo.handlers[:] = [logging.StreamHandler(sys.stdout)]
demo.handlers[0].setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
demo.setLevel(logging.INFO)
demo.propagate = False
demo.info("prediction served in %d ms", 31)
demo.debug("this DEBUG line is dropped, because the level is INFO")
demo.warning("slow request: %d ms", 812)

# %% [markdown]
# **Try it.** Change `demo.setLevel(logging.INFO)` to `logging.WARNING` and re-run: which lines disappear?
#
# ### Exercise 4 · a JSON formatter
#
# Complete the class below. `format(self, record)` must return **one line of JSON** with:
# `"time"` (use `self.formatTime(record)`), `"level"` (`record.levelname`), `"logger"` (`record.name`),
# `"message"` (`record.getMessage()`, which fills in `%d`-style arguments), plus every key of the dict passed as
# `extra={"fields": {...}}`, which arrives as `getattr(record, "fields", {})`. Use `json.dumps(..., default=str)` so
# unusual values do not crash logging.

# %%
class JsonFormatter(logging.Formatter):
    def format(self, record):
        ### BEGIN SOLUTION
        out = {"time": self.formatTime(record), "level": record.levelname, "logger": record.name,
               "message": record.getMessage()}
        out.update(getattr(record, "fields", {}) or {})
        return json.dumps(out, default=str)
        ### END SOLUTION


# %%
grade("w11.json_formatter", JsonFormatter)

# %% [markdown]
# Once it passes, this is how a service would use it:

# %%
try:
    JsonFormatter().format(logging.makeLogRecord({"msg": "check"}))   # does the formatter work yet?
    demo.handlers[0].setFormatter(JsonFormatter())
    demo.info("prediction served", extra={"fields": {"request_id": "req-9", "latency_ms": 31.2}})
    demo.warning("slow request: %d ms", 812)
except NotImplementedError:
    print("(finish Exercise 4 to see JSON lines here)")

# %% [markdown]
# ## 3. From logs to metrics
#
# **Why.** Nobody reads two thousand log lines. You read a few **metrics**, computed per time window, that say
# whether the service is healthy.
#
# **Idea.** The four signals most teams start with (sometimes called the "golden signals"):
#
# * **traffic**: requests per window;
# * **errors**: the share of requests that failed *because of the service*: status 500 and above. A 422 means the
#   caller sent bad input, which the service handled correctly; count it separately;
# * **latency**: not the average but **percentiles**. The p95 is the time within which 95 % of requests finished.
#   Latency is skewed (most requests are fast, a few are very slow), and the mean hides the slow tail;
# * **saturation** (how full the machine is: CPU, memory), which the platform measures for you.
#
# For a *model* service add one model signal you can compute without labels: the **share of positive predictions**
# per window. A sudden jump often means the inputs changed (notebook 43).
#
# **See it.** A simulated two-day log of the churn service (SYNTHETIC: generated by the course, with an incident
# hidden in it).

# %%
log = simulate_requests()
print(len(log), "requests;", log["time"].min(), "to", log["time"].max())
print(log["status"].value_counts().to_dict())
log.head()

# %% [markdown]
# The log has 1,866 requests: 1,790 answered (200), 65 rejected as bad input (422) and 11 server errors (500).
#
# ### Exercise 5 · latency percentiles
#
# Write `latency_percentiles(latencies)` returning `{"p50": ..., "p95": ..., "p99": ...}` as floats, using
# `np.percentile`. Drop `NaN` first (rejected requests have no latency). If nothing is left, raise `ValueError`.

# %%
def latency_percentiles(latencies):
    ### BEGIN SOLUTION
    values = np.asarray(latencies, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        raise ValueError("no latencies to summarise")
    p50, p95, p99 = np.percentile(values, [50, 95, 99])
    return {"p50": float(p50), "p95": float(p95), "p99": float(p99)}
    ### END SOLUTION


print({k: round(v, 1) for k, v in use(latency_percentiles, log["latency_ms"]).items()},
      "| mean:", round(log["latency_ms"].mean(), 1))

# %%
grade("w11.latency_percentiles", latency_percentiles)

# %% [markdown]
# Over the two days: median 36.0 ms, p95 94.3 ms, p99 156.4 ms, while the mean is 43.0 ms. The mean says
# "about 40 ms"; the p99 says one request in a hundred took over 150 ms.
#
# ### Exercise 6 · metrics per window
#
# Write `window_metrics(log, freq="1h")` returning a DataFrame with one row per time window (the index is the
# window start) and the columns:
#
# * `requests`: rows in the window; `errors`: rows with `status >= 500`; `error_rate`: errors / requests;
# * `p95_latency_ms`: the 95th percentile of `latency_ms` in the window, ignoring NaN (NaN if none);
# * `positive_rate`: mean `prediction` over the **status-200** rows (NaN if none).
#
# Make the window with `pd.to_datetime(log["time"]).dt.floor(freq)`, then `groupby`. Windows with no requests do
# not appear.

# %%
def window_metrics(log, freq="1h"):
    ### BEGIN SOLUTION
    df = log.copy()
    df["window"] = pd.to_datetime(df["time"]).dt.floor(freq)
    rows = []
    for window, g in df.groupby("window"):
        answered = g[g["status"] == 200]
        latency = g["latency_ms"].dropna()
        rows.append({"window": window, "requests": len(g), "errors": int((g["status"] >= 500).sum()),
                     "error_rate": float((g["status"] >= 500).mean()),
                     "p95_latency_ms": float(np.percentile(latency, 95)) if len(latency) else np.nan,
                     "positive_rate": float(answered["prediction"].mean()) if len(answered) else np.nan})
    return pd.DataFrame(rows).set_index("window")
    ### END SOLUTION


metrics = use(window_metrics, log)
metrics.iloc[28:35].round(3)

# %%
grade("w11.window_metrics", window_metrics)

# %% [markdown]
# Something happened on the second day between 06:00 and 10:00 UTC: p95 latency jumped from about 60 ms to
# 166-209 ms and 5-12 % of requests failed, then everything went back to normal.
#
# ## 4. A dashboard
#
# **Why.** A dashboard lets a person see the shape of the last day in five seconds: when it went wrong, what went
# wrong together, and whether it is over.
#
# **Idea.** One panel per metric, stacked, **sharing the time axis** so that events line up vertically. Keep it
# to the few metrics that matter; a dashboard with forty panels is not read.
#
# ### Exercise 7 · three panels
#
# Write `plot_dashboard(metrics)` that makes `fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)` and
# plots `requests`, `error_rate` and `p95_latency_ms` against `metrics.index`, one per panel, each with a title.
# Return `fig` (do not call `plt.show()` inside the function).

# %%
def plot_dashboard(metrics):
    ### BEGIN SOLUTION
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    for ax, column, title in zip(axes, ["requests", "error_rate", "p95_latency_ms"],
                                 ["Requests per hour", "Server error rate (status >= 500)", "p95 latency (ms)"]):
        ax.plot(metrics.index, metrics[column], marker=".", lw=1)
        ax.set_title(title, fontsize=10)
    axes[-1].set_xlabel("time (UTC)")
    fig.tight_layout()
    return fig
    ### END SOLUTION


try:
    fig = plot_dashboard(metrics)
    plt.show()
except NotImplementedError:
    print("(finish Exercise 7 to see the dashboard)")

# %%
grade("w11.plot_dashboard", plot_dashboard)

# %% [markdown]
# ## 5. Alerts that are worth waking up for
#
# **Why.** A dashboard needs someone looking at it. An **alert** looks for you and notifies a person (a message,
# a phone call) when a rule is broken. Bad alerts are worse than none: if an alert fires every day for nothing,
# people learn to ignore it, including on the day it matters.
#
# **Idea.** Three decisions make an alert rule:
#
# 1. **what** to watch (one metric) and **which direction** is bad (`>` for errors and latency, `<` for traffic);
# 2. the **threshold**. Two common sources: a target agreed with users (a **service level objective**, SLO, such
#    as "fewer than 2 % errors"), or the metric's normal behaviour (for example mean + 3 standard deviations of a
#    quiet baseline period);
# 3. **how long** it must be broken before anyone is called: requiring 2-3 bad windows in a row filters out one-off
#    blips, at the price of a slightly later alert.
#
# ### Exercise 8 · a threshold from a baseline
#
# Write `alert_threshold(values, k=3.0)` returning `mean + k * std` of the values (NumPy's default std), ignoring
# NaN. With fewer than 5 usable values, raise `ValueError`.

# %%
def alert_threshold(values, k=3.0):
    ### BEGIN SOLUTION
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size < 5:
        raise ValueError("need at least 5 baseline values to set a threshold")
    return float(v.mean() + k * v.std())
    ### END SOLUTION


baseline = metrics.iloc[:24]   # the first day, which was quiet
latency_threshold = use(alert_threshold, baseline["p95_latency_ms"])
print("p95 latency threshold:", round(latency_threshold, 1), "ms")
print("error-rate threshold from the same formula:", use(alert_threshold, baseline["error_rate"]))

# %%
grade("w11.alert_threshold", alert_threshold)

# %% [markdown]
# The latency threshold comes out at 83.7 ms. The error-rate threshold comes out at **0.0**: the first day had no
# server errors at all, so its standard deviation is 0 and *any* single error would fire the alert. That is why
# error alerts usually use an agreed target (an SLO) rather than a formula.
#
# ### Exercise 9 · evaluate the rules for one window
#
# Write `evaluate_alerts(row, rules)`. `row` is one window's metrics (a dict or a pandas row); `rules` is a list of
# dicts `{"name", "metric", "op", "threshold"}` with `op` either `">"` or `"<"`. Return the names of the rules that
# fire, in the rules' order. A value equal to the threshold does not fire; a NaN value never fires; a rule whose
# metric is not in `row` raises `KeyError`.

# %%
def evaluate_alerts(row, rules):
    ### BEGIN SOLUTION
    fired = []
    for rule in rules:
        if rule["metric"] not in row:
            raise KeyError(f"no metric called {rule['metric']!r}")
        value = row[rule["metric"]]
        if value is None or value != value:   # NaN is the only value not equal to itself
            continue
        if (rule["op"] == ">" and value > rule["threshold"]) or (rule["op"] == "<" and value < rule["threshold"]):
            fired.append(rule["name"])
    return fired
    ### END SOLUTION


rules = [{"name": "server errors above 2 %", "metric": "error_rate", "op": ">", "threshold": 0.02},
         {"name": "p95 latency high", "metric": "p95_latency_ms", "op": ">", "threshold": round(latency_threshold, 1)},
         {"name": "traffic dropped", "metric": "requests", "op": "<", "threshold": 10}]
for window, row in metrics.iloc[29:35].iterrows():
    print(window.strftime("%d %b %H:%M"), use(evaluate_alerts, row, rules))

# %%
grade("w11.evaluate_alerts", evaluate_alerts)

# %% [markdown]
# ### Exercise 10 · only alert when it lasts
#
# Write `sustained_alerts(values, threshold, n)` returning the positions at which an alert fires: when the
# value has been **above** `threshold` for `n` windows in a row. Fire once per run (when the run reaches exactly
# `n`), not again until the value drops back. A NaN breaks a run.

# %%
def sustained_alerts(values, threshold, n):
    ### BEGIN SOLUTION
    fired, run = [], 0
    for i, value in enumerate(values):
        run = run + 1 if (value == value and value > threshold) else 0
        if run == n:
            fired.append(i)
    return fired
    ### END SOLUTION


p95 = metrics["p95_latency_ms"].tolist()
for n in [1, 2, 3]:
    at = use(sustained_alerts, p95, latency_threshold, n)
    print(f"n={n}: fires at", [metrics.index[i].strftime("%d %b %H:%M") for i in at])

# %%
grade("w11.sustained_alerts", sustained_alerts)

# %% [markdown]
# With `n=1` the alert fires at 06:00 on the second day, with `n=2` at 07:00: one hour later, in exchange for
# never firing on a single slow hour. Which trade-off is right depends on what a late alert costs.
#
# ## Quiz
#
# Put the letter of your answer between the quotes and run the cell. Each answer explains itself.
#
# **Q1.** What is the main advantage of logging one JSON object per line over printing sentences?
#
# - a) The files are smaller.
# - b) Machines can filter and aggregate the records by field, without fragile text searches.
# - c) JSON logs cannot contain personal data.
# - d) print() does not work on servers.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.42_q1", answer)

# %% [markdown]
# **Q2.** Why do dashboards show p95 latency rather than the average?
#
# - a) Percentiles are cheaper to compute.
# - b) The average of latencies is not defined.
# - c) Latency is skewed; the mean hides the slow tail that some users actually experience.
# - d) The p95 uses more of the data.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.42_q2", answer)

# %% [markdown]
# **Q3.** Why are 422 responses not counted in the server error rate?
#
# - a) The caller sent invalid input and the service handled it correctly; it is not the service's failure.
# - b) 422s never matter.
# - c) 422s show the model is accurate.
# - d) 422 only happens for GET requests.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.42_q3", answer)

# %% [markdown]
# **Q4.** What does requiring three bad windows in a row before alerting buy you?
#
# - a) Earlier alerts.
# - b) A different metric.
# - c) It makes thresholds unnecessary.
# - d) Fewer alerts on one-off blips, at the cost of a slightly later alert.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.42_q4", answer)

# %% [markdown]
# **Q5.** Your team's latency alert fires every afternoon and is always ignored. What is the problem?
#
# - a) There are not enough alerts.
# - b) An alert should mean a person must act; one that fires for nothing trains people to ignore all alerts.
# - c) Alerts should be replaced by dashboards.
# - d) The threshold should be lowered.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w11.42_q5", answer)

# %% [markdown]
# ## Recap
#
# - Log one JSON object per request: time (UTC), request id, model version, latency, prediction, allowed inputs.
# - Build the inputs from an allow-list, so personal data never reaches the logs.
# - Python's `logging`: levels, loggers, handlers, formatters; a JSON formatter turns records into JSON lines.
# - Read logs defensively: count broken lines instead of crashing on them.
# - Metrics per window: traffic, server error rate (status >= 500), p95 latency, share of positive predictions.
# - A dashboard: few panels, shared time axis.
# - Alerts: a metric, a direction, a threshold (SLO or baseline), and a duration; alert only when a person must act.
#
# ## On the job
#
# In practice the log lines go to a log service (on AWS, CloudWatch Logs), and metrics and alerts are configured
# there or in tools such as Prometheus and Grafana. The ideas do not change: what to log, which few metrics, which
# thresholds, and who is called. An ML engineer is usually the one who adds the model-specific parts: the model
# version in every record, the prediction distribution, and the input features for drift checks.
#
# ## Going further
#
# - Tool guide: [Logging and monitoring](../docs/tools/monitoring.md).
# - Handbook: [15. Logging, monitoring and updates](../docs/handbook/ch15_logging_monitoring_updates/index.md).
# - Advanced track: notebooks 37 (service logging and metrics) and 41 (reliability) in `advanced/notebooks/`.
# - Next: [43 · Drift, degradation and model updates](43_drift_and_updates.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("42", "reading")
# mark("42", "guided")

# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/34_latency_resources.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 34 · Latency, throughput and resource use
#
# **Week 6 · day 4 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w6d4_latency_resources/`](../labs/w6d4_latency_resources/)
#
# **Objective.** Measure p50/p95/p99 latency and memory under load, find the bottleneck, and tune workers/batching against a stated budget.

# %%
# --- Setup: works on your laptop AND in Google Colab ----------------------------
# In Colab this clones the course repository and installs the requirements (about a
# minute, first run only). On your own machine it just finds the repository. Every
# command in this notebook runs from the repository root. Safe to re-run.
import os
import subprocess
import sys
from pathlib import Path

if "google.colab" in sys.modules:
    if not Path("/content/mlengineering").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/berdakh/mlengineering.git",
                        "/content/mlengineering"], check=True)
    os.chdir("/content/mlengineering")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "-r", "requirements.txt"], check=True)

REPO_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
print("repo root:", REPO_ROOT)

# %% [markdown]
# Unit id `w6d4_latency_resources` · Week 6, day 4 · Handbook:
# [H10.4 Latency and throughput](../docs/handbook/ch10_batch_online_inference/h10_4_latency_and_throughput.md)
# · Content status: see [STATUS.md](../docs/guides/status.md)

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Measure the `flowguard` API's latency percentiles, throughput and memory under
# controlled load, find what limits it, change one thing on the evidence, and show the effect with the
# same method, against a stated budget.
#
# **Why an applied ML engineer needs it.** "How fast is the model?" is rarely the question that matters.
# The questions are: how many requests per second can this deployment serve while keeping p95 under the
# budget, what happens when traffic exceeds that, and what does it cost in machines. They are answered by
# measurement, and measurement of latency is easy to get wrong in ways that produce confident, optimistic
# numbers. In this lesson the model's own computation turns out to be a small part of each request, and
# the two real bottlenecks found are a single Python process and a 40 ms TCP interaction that nobody
# would find by reading the model code.
#
# **Deliverables.**
# * `lab/loadtest.py`: an open-loop load generator and latency statistics (five functions).
# * `lab/results/*.json` and `lab/LATENCY_REPORT.md`: your measurements, the bottleneck, the fix, the
#   before/after, and what the measurement does not show.
# * `challenge/capacity.py` and `challenge/CAPACITY.md`: a capacity plan for a fleet (section 5).
#
# **Completion criteria.**
# * `python wb.py check w6d4` passes (the generator and statistics, tested with fake servers).
# * Your `LATENCY_REPORT.md` reports measurements you made, with the method, at three or more rates for
#   at least two configurations, and names a bottleneck with evidence.
# * `python wb.py check w6d4 --challenge` passes.
# * You can explain without notes why a closed-loop benchmark under-reports tail latency, and what
#   Little's law says about a service that is falling behind.
#
# **Prerequisites.** [w5d4](28_fastapi_validation.ipynb) (the service),
# [w5d5](29_api_testing.ipynb) (concurrency in FastAPI), [w6d3](33_ci.ipynb) (why timing
# checks are not CI gates). Linux for the memory readings (`/proc`). No new packages: `httpx` and
# `uvicorn` are already installed. Optional, for the real request bodies: `python project/get_skab.py`.
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2 | 25 |
# | Worked example: closed vs open loop | 10 |
# | Guided lab: tasks 1-5 (generator and statistics) | 35 |
# | Guided lab: tasks 6-9 (measure, profile, fix, report) | 35 |
# | Challenge: start `capacity.py` | 5 |
# | Assessment and reflection | 10 |
# | *Optional extension: finish the capacity plan; add a concurrency limit and measure overload behaviour; repeat with 4 workers* | *up to 60* |
#
# Each measurement in tasks 6-8 takes about a minute. Close other heavy programs while measuring.

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Latency, throughput, budgets
#
# * **Latency** of a request: time from when it should have been sent to when its response is complete.
# * **Throughput**: completed requests per second. Offered load is what clients send; served load is
#   what comes back successfully. Below capacity they are equal; past it they diverge.
# * A **latency budget** (or service-level objective, SLO) is a statement such as "p95 <= 100 ms and
#   p99 <= 250 ms with error rate <= 0.1 %, at up to N requests/s". It is stated before measuring, by
#   working backwards from the user's need (an operator dashboard that must update within 2 s leaves the
#   model service a fraction of that after queues, network and rendering).
#
# The lab's budget is in `lab/budget.toml`: p95 <= 100 ms, p99 <= 250 ms, error rate <= 0.1 %.
#
# ### 2.2 Percentiles, not means
#
# Latency distributions are skewed: most requests are fast, a few are very slow, and the slow ones are
# what users remember and what time-outs hit. The mean mixes the two and describes nobody. Report
# **p50** (typical), **p95** and **p99** (the tail), and the maximum with care (it is one request).
#
# The p-th percentile of n sorted values, with linear interpolation (numpy's default):
# $$h = \frac{(n-1)\,p}{100},\qquad P_p = x_{\lfloor h\rfloor} + (h-\lfloor h\rfloor)\,\bigl(x_{\lceil h\rceil} - x_{\lfloor h\rfloor}\bigr).$$
# Two consequences. A p99 from 200 requests is decided by 2 of them; collect enough requests for the
# percentile you report (thousands for p99). And percentiles do not average: the mean of five p95s is not
# the p95 of the combined traffic. Aggregate the raw latencies (or histograms), not the percentiles.
#
# ### 2.3 Open loop, closed loop and coordinated omission
#
# A **closed-loop** generator has a fixed number of virtual users; each sends a request, waits for the
# response, then sends the next. When the server stalls, the users stall with it and *stop sending*:
# the requests that real clients would have sent during the stall never exist, so their delays are never
# measured. An **open-loop** generator schedules request i at $t_0 + i/\lambda$ regardless of responses,
# as independent clients do, and measures each request **from its scheduled time**. This error of the
# closed loop is called **coordinated omission**: the generator coordinates with the server and omits
# exactly the bad measurements.
#
# A parallel from real-time systems: a control loop (a robot controller, a brain-computer interface) is
# closed, because the next decision waits for the last, so per-cycle latency is the right measure. A
# prediction service with thousands of independent machines is open: a stalled server does not stop the
# machines from sending.
#
# ### 2.4 Little's law and queues
#
# For any stable system, averaged over a long period,
# $$L = \lambda\,W,$$
# the average number of requests in the system equals the arrival rate times the average time each spends
# in it. No distributional assumptions. Two uses:
#
# * **Sizing.** A worker that serves one request at a time for $S$ seconds is busy a fraction
#   $\rho = \lambda S$ of the time (utilisation). $n$ workers have utilisation $\lambda S/n$; to keep it
#   below a target $\rho^\*$ you need $n = \lceil \lambda S / \rho^\* \rceil$ workers.
# * **Diagnosis.** If $\lambda$ stays the same and $W$ grows from 10 ms to 2 s, $L$ grows 200-fold: the
#   extra requests are sitting in queues, in memory. Past capacity ($\rho \ge 1$) the queue grows without
#   bound until something gives: memory, time-outs, or the client.
#
# Why not run at $\rho = 0.95$? Queueing delay grows like $\rho/(1-\rho)$ for simple queues: at 0.5 a
# request waits about one service time on average, at 0.7 about 2.3, at 0.9 about 9, before even
# considering the tail. Capacity plans therefore target 0.6-0.75.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-34-01.svg" alt="Diagram 1 of notebook 34" style="max-width:100%">
#
# ### 2.5 Where the time goes inside one request
#
# A request to `/predict` is more than the model: HTTP parsing, JSON decoding, pydantic validation of
# every sample, building a DataFrame, scoring, building per-sample response objects, re-validating the
# response model and encoding JSON, plus the hand-off from the event loop to a thread for a `def`
# endpoint. `lab/profile_predict.py` re-enacts the path with `time.perf_counter` spans and runs
# `cProfile` over complete requests. Measured for a 600-sample real request on the authoring machine:
#
# ```text
# span medians over 50 runs:
#   parse + validate request        0.62 ms
#   build frame + score             2.26 ms
#   build response objects          0.69 ms
#   serialise response              0.26 ms
#   sum of spans                    3.84 ms
#
# end-to-end through TestClient (median, profiler on): 11.02 ms
# ```
#
# The detector itself is inside "build frame + score". About two thirds of the request is framework and
# transport work. Optimising the model would barely move the service.
#
# ### 2.6 Processes, threads and the GIL
#
# FastAPI runs a `def` endpoint in a thread pool. Threads let a process wait on many slow I/O operations
# at once, but CPU-bound Python code holds the global interpreter lock (GIL), so one process executes
# Python bytecode on one core at a time. NumPy and pandas release the GIL inside some vectorised
# operations, but per-sample pydantic work and JSON handling do not. So, for this service:
#
# * more **threads** in one process: more requests *in progress*, not more completed per second;
# * more **worker processes** (`uvicorn --workers N`): N independent interpreters, up to N cores of
#   Python work, at the cost of N copies of the model and libraries in memory (measured: 90 MB idle for
#   1 worker, 220 MB for 2, about 395 MB for 4).
#
# A related trap from w4d5: numerical libraries that start their own thread pools (OpenMP, BLAS) inside
# several worker processes oversubscribe the cores; that course measured 8,153 ms with default threading
# versus 3.5 ms with one thread for the same scoring. `OMP_NUM_THREADS=1` per worker is the usual setting.
#
# ### 2.7 Memory under load
#
# Resident set size (RSS, `VmRSS` in `/proc/<pid>/status`) is the memory a process occupies. It grows
# with what is held: loaded libraries and the model (fixed), and requests in flight (proportional to $L$).
# In this lab a single worker pushed past capacity grew from 90 MB to **2.1-2.8 GB** in under a minute,
# holding queued 138 KiB request bodies and their parsed forms. In a container with a memory limit that
# is an out-of-memory kill: overload becomes an outage. Bounded queues and concurrency limits that reject
# excess work early (HTTP 503 with `Retry-After`) turn it back into graceful degradation; that is w7d5.
#
# ### 2.8 An industry example (illustrative composite, not a documented case)
#
# A team load-tested its scoring API with a closed-loop tool and 10 virtual users, reported "p99 = 45 ms
# at 200 requests/s", and sized production for it. In production, a nightly batch client sent 3,000
# requests in a burst; the service queued them, p99 for interactive users went to 9 s, and pods were
# killed for memory. Re-measured open loop, the same deployment kept p99 under budget only up to
# 120 requests/s. Nothing about the model had changed.
#
# ### 2.9 Limitations and misconceptions
#
# * **"The benchmark says 10 ms, so the service is fast."** At which rate? Latency without offered load
#   is half a number.
# * **"Average latency is fine."** The mean hid the bimodal 2-worker distribution in this lab (some
#   requests at 10 ms, many at 52 ms).
# * **"More workers is always better."** It raised capacity here, and also exposed a 40 ms floor;
#   with 4 cores, 4 workers plus the load generator compete for CPU.
# * **"The load generator is neutral."** It uses CPU and has its own queues; on one machine it competes
#   with the server. Watch its `late_starts` count: if the generator falls behind its schedule, the
#   measurement is of the generator.
# * **"Numbers from my laptop transfer."** Different CPUs, network, TLS, payloads. Re-measure on the
#   target hosts; use laptop numbers to find mechanisms, not capacity.

# %% [markdown]
# ## 3. Worked example: the same server, measured two ways (SYNTHETIC)
#
# `example/coordinated_omission.py` simulates a single first-in-first-out server that takes exactly
# 10 ms per request but freezes for 1 s once, at t = 30 s. It "load-tests" it for 60 s at about
# 50 requests/s, first with one closed-loop virtual user (10 ms think time), then open loop. It is a
# discrete-event simulation (no sleeping), so the output is exact and repeatable:

# %%
!python labs/w6d4_latency_resources/example/coordinated_omission.py

# %% [markdown]
# ```text
# closed loop  n= 2951 (49.2/s)  p50=  10.0  p95=  10.0  p99=   10.0  p99.9=   10.0  max= 1010.0 ms  >100 ms: 0.03%
# open loop    n= 3000 (50.0/s)  p50=  10.0  p95=  10.0  p99=  710.1  p99.9=  980.0  max= 1010.0 ms  >100 ms: 3.07%
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d4_latency_resources/figures/coordinated_omission.svg" alt="Grouped bars: closed loop reports 10 ms at every percentile; open loop reports p99 710 ms and p99.9 980 ms." width="100%">
#
# *Figure 1. SYNTHETIC simulation. Same server, same stall.*
#
# **Interpretation.** The closed-loop user was stuck behind the stall for one request, so exactly one
# latency of 1,010 ms was recorded (0.03 % of requests) and p99 is 10 ms. The open-loop schedule kept
# sending: the 50 requests due during the stall all waited, and the 3 % of requests over 100 ms move
# p99 to 710 ms. Real clients behave like the open loop. **Decisions in the code:** the server and the
# stall are simulated in time arithmetic, so the result is not affected by the machine; latency in the
# open loop is `finish - scheduled`, never `finish - actually_sent`.

# %% [markdown]
# ## 4. Guided lab
#
# `lab/` holds the week-5 service (`src/`, `models/`, `splits/`), the budget (`budget.toml`), three given
# scripts (`measure_service.py`, `profile_predict.py`, `serve.py`), the report template
# (`LATENCY_REPORT.md`) and your file, `loadtest.py`.
#
# **Tasks 1-5 (35 min): implement `loadtest.py`.** The docstrings are the specification.
#
# 1. `percentile(values, q)`: linear interpolation, without numpy. *Checkpoint:* matches `numpy.percentile`.
# 2. `intended_schedule(rate, duration)`.
# 3. `run_open_loop(send, rate, duration)`: sleep until each scheduled time, *start* a task for the request,
#    move on; gather at the end. Latency from the intended start. Exceptions become records with
#    `status=None`.
# 4. `summarise(records, warmup_s, late_threshold_s)`: warm-up by intended time; percentiles over 2xx only;
#    error rate over everything; throughput over the measured window; late starts.
# 5. `compare_to_budget(summary, budget)`.

# %%
!python wb.py check w6d4

# %% [markdown]
# The checks use fake `send` functions (a 200 ms server, a stall that blocks the event loop, failures),
# not the network. *Debugging:* "requests were sent late" means your loop awaits each response;
# "latency must be finished - intended start" means you measured from the actual send.
#
# **Task 6 (10 min): find the knee with one worker.**
#
# ```bash
# python labs/w6d4_latency_resources/lab/measure_service.py --workers 1 --rates 20 60 90 120 \
#     --duration 10 --out labs/w6d4_latency_resources/lab/results/workers1.json
# ```
#
# Read p95 against the budget, served throughput against offered, and the RSS line. Real output on the
# authoring machine (first repetition, `--duration 15`):
#
# ```text
# workers=1 rate=   20/s  sent=  300  p50=   11.0  p95=   15.7  p99=   20.5 ms  errors=0.000  thr=  20.0/s  late=0  budget=OK
# workers=1 rate=   60/s  sent=  900  p50=   10.4  p95=   24.4  p99=   81.0 ms  errors=0.000  thr=  60.0/s  late=1  budget=OK
# workers=1 rate=   90/s  sent= 1350  p50= 1219.3  p95= 2993.0  p99= 3376.5 ms  errors=0.000  thr=  80.5/s  late=1  budget=MISSED
# workers=1 rate=  120/s  sent= 1800  p50= 6843.1  p95=10072.6  p99=10324.2 ms  errors=0.974  thr=   1.8/s  late=639  budget=MISSED
# server RSS 90 MB idle, 2494 MB after load (1 worker(s)); real SKAB valve1/13, first 600 samples
# ```
#
# One worker serves about 83 requests/s at most. At 90/s the queue grows for the whole run; at 120/s
# nearly every request times out at 10 s, the server completes only a handful per second, and its memory
# reaches gigabytes. (The `late=639` at 120/s is the *generator* falling behind; that row measures an
# overloaded machine as much as the service.)
#
# **Task 7 (5 min): where does a request's time go?**

# %%
!python labs/w6d4_latency_resources/lab/profile_predict.py

# %% [markdown]
# Compare with section 2.5. Decide whether a faster model would move the knee.
#
# **Task 8 (10 min): add workers, and look carefully.** Repeat task 6 with `--workers 2` (and `4` if you
# have the time). The knee disappears below 120/s. Now compare p50 at 20/s and 60/s with the one-worker
# run. Real means of two repetitions on the authoring machine:
#
# | Configuration | 20/s p50 / p95 | 60/s p50 / p95 | 120/s p50 / p95 |
# |---|---|---|---|
# | `--workers 1` | 10.8 / 15.9 | 10.5 / 32.6 | 6767 / 10029 (95 % errors) |
# | `--workers 2` | 11.6 / 54.9 | 52.8 / 60.1 | 54.7 / 85.5 |
# | `--workers 4` | 11.8 / 54.4 | 52.5 / 60.3 | 55.7 / 87.8 |
#
# A latency that does not depend on load is not queueing. Before reading on, write down a hypothesis.
#
# *The answer.* About 52 - 11 = 41 ms is added to many requests whatever the rate, which matches the Linux
# delayed-ACK timer: TCP's Nagle algorithm is holding back the last piece of the response until the
# client acknowledges the previous one, and the client delays its acknowledgement. Servers normally
# disable Nagle with `TCP_NODELAY`; asyncio does so automatically, but only for sockets whose protocol
# number is `IPPROTO_TCP`. With `--workers N > 1`, uvicorn 0.54 creates the shared listening socket as
# `socket.socket(family=AF_INET)`, protocol number 0, so asyncio skips it (both read in the installed
# source). With one worker uvicorn lets asyncio create the socket and the problem does not occur.
# Forcing `TCP_NODELAY` in the workers (a verification-only experiment) cut p50 at 60/s from 52 to 9.5 ms.
#
# **Task 9 (10 min): apply the fix and report.** `lab/serve.py` starts the same app with N workers on a
# listening socket created with `IPPROTO_TCP`. Measure with it:
#
# ```bash
# python labs/w6d4_latency_resources/lab/measure_service.py --launcher serve --workers 2 \
#     --rates 20 60 90 120 --duration 10 --out labs/w6d4_latency_resources/lab/results/serve2.json
# ```
#
# Authoring machine, means of two repetitions: p95 14.8, 11.7, 14.1 and 13.7 ms at 20, 60, 90 and
# 120/s; p99 at most 43.9 ms; no errors; 239 MB. Fill in `lab/LATENCY_REPORT.md` from **your** numbers.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d4_latency_resources/figures/latency_vs_rate.svg" alt="Two panels, p50 and p95 against offered load on a log scale: one worker rises above 1 s past 90 req/s; two and four workers sit near 52 ms p50; two workers with TCP_NODELAY stay near 10 ms." width="100%">
#
# *Figure 2. Real measurements on the authoring machine (dots: two repetitions; lines: their mean).*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d4_latency_resources/figures/throughput.svg" alt="Served against offered load: two workers with TCP_NODELAY follow the diagonal to 120/s; one worker peaks near 83/s and falls to 3.5/s at 120/s." width="100%">
#
# *Figure 3. Past saturation, served throughput falls: the queue fills, requests time out, and work
# done on requests that will time out is wasted. Real measurements.*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w6d4_latency_resources/figures/latency_cdf.svg" alt="Cumulative distribution on a log axis: one worker at 60/s has p99 near 90 ms; at 95/s the whole curve sits between 1 and 10 seconds." width="100%">
#
# *Figure 4. One worker, 30 s at 60/s and at 95/s (real; 532 of 2,850 requests at 95/s succeeded).*

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w6d4")

# %% [markdown]
# ## 5. Independent challenge: a capacity plan you can defend
#
# Read [challenge/README.md](../labs/w6d4_latency_resources/challenge/README.md). You size the service for 120,000 machines from the
# single-worker curve you measured (`challenge/measured_curve.csv` holds the authoring machine's), with
# Little's law, a utilisation target and a sensitivity analysis, and write a one-page plan.
#
# Acceptance: `python wb.py check w6d4 --challenge` (numbers and memo structure), and the rubric in the
# assessment for the reasoning.
#
#
# ### The challenge brief
#
#
# **Scenario.** The plant operator wants `flowguard` for its whole fleet: **120,000 machines**, each
# sending one 600-sample request every 10 minutes. Requests are not evenly spread: after a shift change
# many machines flush at once, and the operator's data team estimates the peak at **3 times the average**.
# The service-level objective (SLO) for `/predict`: **p95 latency <= 100 ms and error rate <= 0.1 %**,
# measured at the service. Hosts have 4 vCPUs.
#
# You have one real measurement: `measured_curve.csv`, the single-worker service on the authoring
# machine (means of two repetitions of `lab/measure_service.py --workers 1`, 600-sample requests,
# open-loop load from the same 4-core machine). Columns: offered rate, p50/p95/p99/mean latency (ms),
# error rate, achieved throughput.
#
# #### Tasks
#
# 1. Implement the four functions in `capacity.py` (`load_curve` is given). Their docstrings are the spec.
# 2. Write `CAPACITY.md`, a one-page capacity plan with these sections (headings must contain the words):
#    * `## Assumptions`: traffic model (average and peak rates you derived, and how), the service time you
#      used and where it comes from in the curve, the utilisation target and why, what the measurement
#      setup over- or under-states.
#    * `## Calculation`: Little's law at peak, workers needed, hosts needed; show the numbers.
#    * `## Sensitivity`: how the answer moves if traffic is 0.5x / 1.5x / 2x your estimate and if you use a
#      tail latency instead of the mean as service time; which assumption matters most.
#    * `## Risks`: at least three, with what you would measure to retire each.
#    State your recommendation as a number of workers (for example "11 workers").
#
# #### Acceptance criteria (`python wb.py check w6d4 --challenge`)
#
# * `littles_law_concurrency`, `workers_needed`, `max_rate_within_slo` and `sensitivity` give the right
#   numbers on test cases (including units, rounding, and rates that pass after a failure).
# * `load_curve("measured_curve.csv")` works with your `max_rate_within_slo`.
# * `CAPACITY.md` has the four sections, states a number of workers and is at least 250 words.
#
# The numbers are checked automatically; the reasoning is graded with the rubric in the assessment.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w6d4", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# [Hint 1: concepts](../labs/w6d4_latency_resources/hints/hint1_concept.md) · [Hint 2: approach](../labs/w6d4_latency_resources/hints/hint2_approach.md) ·
# [Hint 3: partial implementation](../labs/w6d4_latency_resources/hints/hint3_partial.md)
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# * **Open loop.** The generator decides *when* each request is sent (t0 + i / rate) before the test
#   starts. It never waits for a response before sending the next request. Requests overlap.
# * **Latency is measured from the intended start.** If the generator or the server stalls, the requests
#   that should have gone out during the stall still count from when they *should* have been sent.
#   Measuring from the actual send hides the stall ("coordinated omission").
# * **Percentiles.** Sort, compute the fractional position h = (n - 1) q / 100, interpolate between the
#   two neighbouring values. That is numpy's default ("linear") definition.
# * **Errors are not latencies.** A fast 503 or a 10 s timeout tells you about failure, not about how
#   long successful service takes. Count them in the error rate; keep them out of the percentiles.
# * **Warm-up.** The first seconds include connection set-up and cold code paths. Exclude them by
#   intended start time, not by count.
# * **Capacity (challenge).** A Python worker serving CPU-bound requests handles about one at a time.
#   Little's law: average number busy = arrival rate x time each takes.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **`run_open_loop`.** Record `t0 = clock()`. For each offset in `intended_schedule(rate, duration)`:
# `await asyncio.sleep(...)` until `t0 + offset`, then *start a task* for the request
# (`asyncio.create_task(one(intended))`) and move on without awaiting it. At the end,
# `await asyncio.gather(*tasks)`. Inside `one`: record `started`, `await send()` in a `try` (an exception
# means status None and an `error` string), record `finished`, set `latency = finished - intended`.
# `gather` returns results in the order the tasks were given, which is schedule order.
#
# **`summarise`.** Filter by `intended >= first_intended + warmup_s`. Split successful (2xx) from the rest.
# Percentiles over successful latencies in milliseconds. Window = last `finished` - first `intended` of the
# kept records. Late starts: `started - intended > late_threshold_s`.
#
# **`compare_to_budget`.** Loop over the budget's keys; treat missing and NaN as failing; `<=` passes.
#
# **Measuring.** Run `measure_service.py` with `--workers 1` at a low, medium and high rate, then with 2
# workers. Read where p95 leaves the budget and what the throughput column does at the same time.
#
# **Challenge.** `workers_needed`: offered load in busy workers is rate x service time (in seconds);
# divide by the target utilisation and round *up*. `max_rate_within_slo`: sort rows by rate and stop at
# the first row that violates the SLO.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ```python
# def percentile(values, q):
#     if not 0 <= q <= 100:
#         raise ValueError(...)
#     xs = sorted(values)
#     if not xs:
#         raise ValueError(...)
#     h = (len(xs) - 1) * q / 100.0
#     lo, hi = math.floor(h), math.ceil(h)
#     return float(xs[lo] + (h - lo) * (xs[hi] - xs[lo]))
#
#
# async def run_open_loop(send, rate, duration, clock=time.perf_counter):
#     t0 = clock()
#
#     async def one(intended):
#         rec = {"intended": intended, "started": clock(), "status": None, "error": None}
#         ...                                   # await send() inside try/except
#         rec["finished"] = clock()
#         rec["latency"] = ...                  # from which time?
#         return rec
#
#     tasks = []
#     for offset in intended_schedule(rate, duration):
#         delay = (t0 + offset) - clock()
#         if delay > 0:
#             await asyncio.sleep(delay)
#         tasks.append(...)                     # start it, do not await it here
#     return list(await asyncio.gather(*tasks))
# ```
#
# `summarise` (sketch): `kept` by warm-up; `ok` = 2xx; `lat_ms` from `ok`; fill NaN for the latency keys
# when `ok` is empty.
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): reasoning questions, a design-choice explanation, the rubric and a
# system-design interview rep on latency budgets.
#
#
# ### Assessment questions
#
#
# Write your answers before opening `solutions/labs/w6d4_latency_resources/assessment_answers.md`.
#
# #### Reasoning questions
#
# 1. A dashboard shows "mean latency 35 ms". Give two distributions of request latency with that mean,
#    one of which meets "p99 <= 100 ms" and one of which badly misses it. What should the dashboard show?
# 2. A closed-loop load test with 8 virtual users reports p99 = 40 ms against a server that, for 2 s
#    every minute, stops answering (a garbage-collection pause, say). Explain why the reported p99 is far
#    too optimistic, and estimate the fraction of requests that an open-loop test at the same average rate
#    would see delayed by the pause.
# 3. Little's law: a service receives 120 requests/s and the mean time in system is 50 ms. How many
#    requests are in the system on average? If the arrival rate stays the same and the mean time rises to
#    2 s because of queueing, how many? What happens to memory, and why does that matter?
# 4. Your service is CPU-bound Python. Explain what adding uvicorn *threads* (a larger thread pool for sync
#    endpoints) buys you versus adding *worker processes*, and when each helps.
# 5. Two reasons why "p95 latency measured in a unit test" belongs in a scheduled job rather than in CI
#    (lesson w6d3), and one deterministic proxy that may stay in CI.
# 6. You measured on a 4-core laptop with the load generator on the same machine. List what this setup
#    over- or under-states compared with production, and one change that removes the biggest bias.
#
# #### Design-choice explanation (150-250 words)
#
# The lab found the single-worker service collapses beyond its capacity: latency rose to seconds and
# memory to gigabytes. Propose how the service should behave when offered more load than it can serve
# (think: bounded queues, concurrency limits, `503` with `Retry-After`, timeouts, autoscaling), and argue
# which response is better for the reliability engineer who consumes the alerts.
#
# #### Rubric (open answers)
#
# | Criterion | Strong | Adequate | Weak |
# |---|---|---|---|
# | Distribution thinking | reasons with percentiles and tails, gives numbers | mentions tails | reasons with means |
# | Measurement validity | names coordinated omission, warm-up, co-located generator, noisy host | one of these | trusts any number |
# | Queueing | uses L = lambda W and utilisation correctly, links queues to memory | one link | none |
# | Concurrency model | separates GIL-bound threads from processes | partly | "more threads = faster" |
# | Evidence | cites the lab's own measurements | general | none |
#
# #### Interview rep (10-15 minutes, system design: latency budget; reduced assistance)
#
# > "The product team wants anomaly scores shown on the operator dashboard 'in real time'. Each of 2,000
# > machines sends a 60-sample window every minute. The dashboard must update within 2 seconds of a window
# > arriving, 99% of the time. Walk me through how you would turn that into a latency budget for the model
# > service, how you would size it, and how you would know you are meeting it in production."
#
# Answer aloud or in writing in 12 minutes, then score yourself with the rubric in the answers file.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** write an open-loop generator that does not hide stalls;
# report percentiles with enough samples; locate a service's knee and explain it with Little's law; tell
# queueing from a fixed delay by how latency depends on load; choose between threads and processes for
# CPU-bound Python; and size a deployment with a stated utilisation target.
#
# **Reflection prompt.** Think of a latency number you have seen reported (in a paper, a benchmark, or a
# system you have built or used). Was it measured closed loop, and would the conclusion change if it had
# been measured open loop?
#
# **Later retrieval question (for the w6d7 review).** A service's p50 is 50 ms at 5 requests/s and
# 50 ms at 100 requests/s, while one request's server-side processing takes 10 ms. List three hypotheses
# and the measurement that separates them.
#
# **Next.** [w6d5](35_cloud_deployment.ipynb) deploys the container to one cloud route, behind an
# authorisation gate.

# %% [markdown]
# ## Verification record
#
# Executed on the authoring machine (4-core shared Linux container), 2026-11-22: Python 3.13, FastAPI
# 0.165.0, uvicorn 0.54.0, httpx 0.28.1, pydantic 2.13.5.
# * `python tools/verify_checks.py labs/w6d4_latency_resources`: reference passes both parts; 5 lab
#   and 4 challenge mutants rejected, each by its intended check. The starter fails all 19 lab checks and
#   every challenge check.
# * All measurements quoted come from `figures/measure.py` (two interleaved repetitions of 1, 2 and 4
#   workers with the uvicorn command line and 2 workers with `serve.py`, plus one 30 s distribution run),
#   plotted by `figures/make_figures.py`. `pgrep` confirmed no server was left running after each run.
# * The TCP_NODELAY cause was confirmed by reading `asyncio.base_events._set_nodelay` and uvicorn's
#   `Config.bind_socket` in the installed versions, and by a verification-only run that forced
#   TCP_NODELAY in the workers (p50 52.3 -> 9.5 ms at 60/s).
# * The worked example's output above is exact (deterministic simulation).
# * **Not verified:** other uvicorn versions (the floor may be absent or fixed in yours: measure);
#   `httptools`/`uvloop` (not installed); multi-machine load; behaviour beyond 120/s for 2 workers.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w6d4", "reading")
# mark("w6d4", "guided")
# mark("w6d4", "independent")
# note("w6d4", "what tripped me up today")


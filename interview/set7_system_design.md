# Interview set 7 - ML system design rep 2 (operating a model); a retry wrapper in code

**Use on:** the Week 7 review day (`w7d7`). **Total time: 45 minutes, timer on.**
**Conditions (Weeks 6-8 level):** timed; the design is **spoken aloud and recorded** (a phone voice memo
is enough; sketch boxes on paper while you talk); no hints, no solutions, no AI assistance. **Score your
recording against the rubric (`solutions/interview/set7.md`, part A) before reading anything else in that
file.** Part B, the worked answer, stays closed until you have re-recorded every rubric area you scored
below "Demonstrated".

| # | Type | Time |
|---|---|---|
| D1 | System design: operating a prohibited-listing classifier with delayed, selective human labels | 30 min |
| C2 | Coding: `retry_call` with capped exponential backoff, full jitter, Retry-After and a deadline | 15 min |

On a short day: D1 alone (30 minutes).

**What is different from set 5.** Set 5 asked you to design a model into existence. Here the model
already exists and works offline; the question is how it is *operated*: what you watch, which signals
mean what, where the labels come from and what they are biased by, how a new version reaches production
safely and leaves it quickly, and what the service does when a dependency fails. Interviewers for
applied ML roles ask this second question more often than the first, because it is where deployed
models actually fail. Spend at most a few minutes on the model itself.

The scenario and every number in it are **constructed for practice**; they are assumptions, not facts
about any real company.

---

## D1 - "Keep the bad listings out" (30 minutes)

You join the trust-and-safety engineering team of an online **second-hand marketplace**. When a seller
publishes a listing (title, description, category, price, up to 8 photos), a classifier scores it for
**prohibited items** (weapons, counterfeit goods, recalled products, regulated substances, and so on).
The classifier exists: a text model plus an image-embedding model, combined into one score per policy
category. Today it runs as a batch job every 6 hours over new listings; leadership wants it in the
publish path, and the data science team has a new version (v4, with a new image encoder) ready to ship.

What the interviewer tells you when asked (anything else, make and state an assumption):

* **Volume:** about 1.2 million new listings a day; peak 60 per second on Sunday evenings.
* **Decision and latency:** at publish time each listing is **published**, **held for human review**,
  or **blocked**. The seller's app waits for the answer; the publish call must answer within **800 ms
  at p99** and otherwise shows "something went wrong".
* **Image embeddings** come from a separate GPU service owned by another team (median 120 ms, p99
  400 ms on a normal day).
* **Human review:** a moderation team can review about **6,000 listings a day**; a held listing waits
  for review (median 3 hours, up to 24 hours on weekends). Reviewer verdicts are the main label source.
* **Other labels:** buyers can report published listings; reports arrive hours to weeks after
  publication and cover an unknown fraction of bad listings. Today there is **no random audit** of
  published listings.
* **Policy changes:** the policy team adds or changes a prohibited category about once a quarter,
  sometimes with immediate legal effect.
* **Sellers adapt:** some sellers who are blocked rewrite titles or crop photos and try again.
* **Current numbers (batch job, v3):** about 2.1 % of new listings are held; reviewers confirm about
  62 % of held listings as prohibited.

**Design how this model is operated.** Cover what you judge important, in an order you choose. Keep
about 5 minutes for these follow-ups:

1. *"Two weeks after v4 went live, the hold rate fell from 2.1 % to 1.4 % and reviewers now confirm
   78 % of held listings instead of 62 %. The product manager says v4 is clearly better. Is it?"*
2. *"During a Sunday sale the image-embedding service times out on 30 % of calls. What does the
   publish path do, and what do the moderators see?"*
3. *"Legal adds a new prohibited category, effective tomorrow. You have no labelled examples. What do
   you do this week, and what do you not do?"*

---

## C2 - A retry wrapper with backoff, jitter, Retry-After and a deadline (15 minutes)

Implement `retry_call` in `interview/set7_work/c2.py`. Standard library only. Keep the names
`TransientError` and `retry_call` (the stub defines `TransientError` for you). This is the client side of
w7d5: what your service should do when *it* calls the image-embedding service.

```python
def retry_call(fn, *, max_attempts=5, base=0.1, cap=5.0, deadline=None,
               is_retryable=None, sleep=time.sleep, now=time.monotonic, rand=random.random): ...
```

**Behaviour.**

1. Call `fn()` (no arguments). If it returns, return its value.
2. If it raises an `Exception` for which `is_retryable(exc)` is false, re-raise it immediately. With
   `is_retryable=None`, only `TransientError` (and subclasses) is retryable. A `BaseException` that is not
   an `Exception` (`KeyboardInterrupt`, `SystemExit`) is never caught.
3. `max_attempts` counts **calls**, including the first. After the last allowed call fails, re-raise
   **that** exception object, unchanged (not a wrapper).
4. Before retry number *n* (n = 1 after the first failure, 2 after the second, ...) sleep for:
   * `min(retry_after, cap)` if the exception has a `retry_after` attribute that is not `None`
     (seconds; the server's hint wins over your formula);
   * otherwise **full jitter**: `rand() * min(cap, base * 2 ** (n - 1))`, where `rand()` returns a
     uniform number in [0, 1).
5. **Deadline.** If `deadline` is not `None`, it is a budget in seconds measured with `now()` from just
   before the first call. Time spent inside `fn` counts. If sleeping the next delay would end after
   `start + deadline`, do not sleep: re-raise the last exception at once.
6. Use only the injected `sleep`, `now` and `rand` (the tests pass a fake clock; nothing really waits).
7. `max_attempts < 1`, a negative `base` or a negative `cap` raise `ValueError` before anything is called.

Before coding, say which HTTP responses your service should treat as retryable when calling the
embedding service, and which never (w7d5, 2.5). After coding, say what happens to the embedding service
if 2,000 publish requests fail at the same instant and every client uses your function with
`rand = lambda: 1.0`, and why a deadline does not by itself free the embedding service's resources.

```bash
python -m pytest interview/set7_tests -q
```

The harness loads your file as a module named `set7_c2`. A worked check: `base=0.1, cap=5.0`, three
transient failures and `rand()` returning 0.5, 0.25, 0.75 give sleeps of 0.05, 0.05 and 0.3 seconds.

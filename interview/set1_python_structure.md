# Interview set 1 - Python and project structure

**Use on:** the Week 1 review day (`w1d7`). **Total time: 40 minutes, timer on.**
**Conditions (Weeks 1-2 level):** first attempt untimed-help-free; no hints, no solutions, no AI
assistance. Language reference and the standard-library documentation are allowed. Rubrics and
worked answers are in `solutions/interview/set1.md`: open them only after you have written all
four answers.

| # | Type | Time |
|---|---|---|
| P1 | Coding: a data structure | 15 min |
| P2 | Coding: refactor for testability | 15 min |
| E3 | Spoken/written explanation | 5 min |
| E4 | Spoken/written explanation | 5 min |

Write code in `interview/work/set1/` (stub files are there). Run the tests only when you believe you
are done with a prompt, as you would hand in an answer:

```bash
python -m pytest interview/set1_tests -q                 # both coding prompts
python -m pytest interview/set1_tests/test_p1_rolling.py -q
```

The tests are an aid to self-scoring. Passing them is not the whole rubric: an interviewer also
scores how you clarified the problem, stated complexity and chose tests.

---

## P1 - Rolling statistics over a stream (15 min)

A monitoring service receives one sensor value at a time and must report statistics over the most
recent `window` values.

Implement in `interview/work/set1/p1.py`:

```python
class RollingStats:
    def __init__(self, window: int): ...      # window >= 1, else ValueError
    def push(self, x: float) -> None: ...     # add one value; the oldest leaves once more than `window` are held
    def mean(self) -> float: ...              # mean of the values currently held
    def max(self) -> float: ...               # maximum of the values currently held
    def __len__(self) -> int: ...             # number of values currently held (<= window)
```

Requirements

* `mean()` and `max()` raise `ValueError` when nothing has been pushed.
* Before the window is full, statistics cover the values pushed so far.
* `push`, `mean` and `max` must each be **O(1) amortised**. A solution that scans the window on
  every call is not accepted (the tests include a stream of 300,000 values with `window=20,000`).
* Standard library only.

Before coding, say (write down) in two sentences: which structure gives you an O(1) maximum, and
why its amortised cost is O(1). After coding, state one numerical caveat of your `mean()`.

---

## P2 - Refactor for testability (15 min)

`interview/set1_legacy/report_legacy.py` is a script that works but cannot be tested: it reads a
hard-coded path, asks the clock for the time, and prints. Read it first (it is 30 lines).

Rewrite it as `interview/work/set1/p2.py` exposing:

```python
def parse_line(line: str) -> dict | None:
    """'2026-11-20T09:15:00 ERROR disk full' -> {'ts': datetime, 'level': 'ERROR', 'message': 'disk full'}.
    Returns None for blank or malformed lines (never raises)."""

def summarize(events: list[dict], now: datetime) -> dict:
    """Summary of events with  now - 24h < ts <= now.
    Returns {'counts': {level: n, ...}, 'last_error': str | None}
    'counts' contains only levels that occur in the window.
    'last_error' is the message of the most recent ERROR in the window, or None."""

def main(argv: list[str] | None = None) -> int:
    """`main([path])` prints the summary as one JSON line and returns 0.
    Returns 2 (and prints nothing to stdout) if the file does not exist."""
```

Requirements

* `summarize` is a pure function: it must not read the clock, files or environment.
* Importing the module does nothing observable (no file access, no output).
* Behaviour for the well-formed cases is the legacy script's, with the window boundary exactly as
  specified above (the legacy script is ambiguous about it; decide from the docstring).
* Timestamps are naive ISO-8601 (`datetime.fromisoformat`).

Then list, in comments at the bottom of your file, the **five test cases** you consider most
valuable, one line each, in priority order.

---

## E3 - Explanation (5 min, aloud or in writing, at most 150 words)

A teammate says: "Packaging is overkill for our research repo. I just put
`sys.path.insert(0, os.path.dirname(__file__) + '/..')` at the top of every script and everything
imports fine." Respond as a colleague: what specifically breaks or becomes unreliable, what is the
smallest alternative, and when would you agree their approach is good enough?

## E4 - Explanation (5 min, at most 150 words)

You are handed a training script with fourteen module-level constants, `print` statements, and
`np.random.seed(0)` at the top. You have one afternoon. In order, what three changes do you make so
that a result produced next month can be traced and regenerated, and what do you deliberately leave
for later?

---

## Log it

```bash
python wb.py note w1d7 "set1: P1 <time> <pass/fail>, P2 <time> <pass/fail>; error pattern: ..."
```

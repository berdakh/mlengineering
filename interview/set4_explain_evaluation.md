# Interview set 4 - explain your evaluation; time-series fundamentals

**Use on:** the Week 4 review day (`w4d7`). **Total time: 45 minutes, timer on.**
**Conditions (Weeks 3-5 level):** timed; spoken and **recorded** (phone or laptop audio is enough);
no hints, no solutions, no AI assistance. After the first attempt open the **rubrics only**
(`solutions/interview/set4.md`, part A). Worked answers (part B) stay closed until a second attempt
at everything scored below "Demonstrated".

| # | Type | Time |
|---|---|---|
| E1 | Explain the `flowguard` evaluation, recorded, one take | 5 min + 5 min self-scoring |
| E2 | Follow-up questions, spoken | 12 min (pick 6 of 10, about 2 min each) |
| T1, T2 | Time-series fundamentals, spoken | 4 min each |
| C3 | Coding: statistics over a time-based window | 15 min |

On a short day: E1, three follow-ups, T1 (about 25 minutes).

---

## E1 - "Walk me through how you evaluated this" (5 minutes, recorded)

**Setup.** Imagine a hiring manager with an ML background who has not seen your project. They say:
*"You built an anomaly detector on sensor data. Walk me through how you evaluated it and how much I
should trust the numbers."*

**Protocol**

1. Two minutes of preparation with a blank page. No repository, no report. You may write at most
   six words per bullet.
2. Record **one take** of five minutes. Do not restart. If you finish early, stop.
3. Use your own project's numbers if you have them by heart. If you have not yet produced a number,
   say so in the answer ("I have not measured X yet") rather than leaving it out. The course's
   reference numbers (frozen split v2: 7 test, 27 development experiments) are in the Week 3-4
   lessons and in `docs/guides/project.md`; quoting those is acceptable, as long as you say they are the
   reference runs and not yours.
4. Listen to the recording once, with the rubric in `solutions/interview/set4.md` (part A, E1) in
   front of you, and tick what you actually said. Score what is on the recording, not what you meant.
5. Note the two most important things you left out. Record a second take tomorrow or on `w5d7`;
   do not re-record today.

The answer is judged on whether a listener could **reconstruct the protocol and its weak points**,
not on how good the numbers are.

## E2 - Follow-up questions (12 minutes)

Pick six, alternating between ones you expect to answer well and ones you do not. Answer each
aloud in at most two minutes. They are the questions a careful interviewer asks next.

1. Why did you split by experiment instead of by row? What would the number have been otherwise?
2. Your supervised model beats the one-sensor z-score by 0.016 PR-AUC on the test set. Is it better?
3. Your positive class is about 35 % of samples. Is this really anomaly detection? What happens to
   your precision in a plant where faults are rare?
4. Your gradient-boosted trees had the best test score. Why are they not the model you chose?
5. Could your model just be learning when the fault is scheduled to happen? How would you know?
6. Did you find anything wrong with the dataset itself? What did you do about it?
7. How did you choose the threshold? At that threshold, would an operator be happy?
8. You tried a neural network. What happened, and is that a fair verdict on neural models?
9. How do you know your features do not use future information? Could you prove it to me?
10. Which of your conclusions would you expect *not* to hold on a real plant, and why?

## T1 - How much data is that, really? (4 minutes)

A sensor is sampled at 1 Hz for 600 s. Successive samples are strongly correlated: the series is
well described as AR(1) with coefficient 0.9. You compute the mean of the 600 samples.

Roughly how many *independent* samples is this worth for estimating the mean, and where does the
formula come from? Give two consequences for an anomaly-detection project, one for training and one
for evaluation.

## T2 - A forecaster as a detector (4 minutes)

You build an anomaly score as the absolute residual of a naive last-value forecast,
`|x[t] - x[t-1]|`, thresholded at a multiple of its normal standard deviation.

Describe what this score does on (a) a sudden step in the sensor level, (b) a slow linear drift,
(c) a stuck sensor. Which faults can it never flag, and for how long does it flag a step? Propose
one change that fixes the main weakness and say what it costs.

---

## C3 - Statistics over a time-based window (15 minutes)

Row-count windows are wrong when sampling is irregular: in the project data, six files contain
gaps of up to 247 s, so "the last 60 rows" is not "the last 60 seconds".

Implement in `interview/set4_work/c3.py`, standard library only, no pandas or NumPy:

```python
class TimeWindowStats:
    def __init__(self, horizon_s: float): ...   # horizon_s > 0, else ValueError
    def push(self, t: float, x: float) -> None: ...
        # t in seconds, non-decreasing (ValueError if it goes backwards; equal is allowed).
        # After the push the window holds exactly the values with  t_now - horizon_s < t_i <= t_now.
    def mean(self) -> float: ...                # ValueError if empty
    def std(self) -> float: ...                 # SAMPLE standard deviation (n - 1);
                                                # float('nan') when one value is held; ValueError if empty
    def __len__(self) -> int: ...               # number of values currently held
```

Requirements

* `push`, `mean` and `std` are **O(1) amortised**; the tests include a window holding 20,000 values.
* `std()` must never fail or return `nan` because of rounding on a nearly constant signal with a
  large offset (for example values near 1,000,000.1).
* Before coding, say which running quantities you keep, and what is numerically dangerous about the
  textbook formula `E[x²] − E[x]²`.
* After coding, say what your class does after a long gap, and whether that is what a detector
  should want.

```bash
python -m pytest interview/set4_tests -q
```

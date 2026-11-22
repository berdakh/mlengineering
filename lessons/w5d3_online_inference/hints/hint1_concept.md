# Hint 1 - concept (w5d3)

**Lab.** Ask, for every rule, "what would `score_batch` have known at this row?". During the burn-in
it knows the values so far and nothing else; after it, only `mu` and `sigma`. Your state is exactly
that, plus what you need to recognise a retry (the last timestamp, value and result). If you find
yourself appending to a list, ask which batch quantity the list stands for and keep a running version
of it instead.

Rejections are safe only if they happen before you touch the state. Write every check first and
every assignment last.

**Challenge.** Hysteresis is a two-counter state machine: the length of the current run of `True`
and the length of the current run of `False`. A `None` is "no evidence": it breaks both runs and
decides nothing. `hysteresis_batch` is not a second algorithm; it is the streaming one applied in a
loop. If you write it differently, you have to prove the two agree, and the point of the exercise is
that an offline formulation tends to look back.

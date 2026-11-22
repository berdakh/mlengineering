"""C2: behaviour from the specification in interview/set7_system_design.md (not one implementation)."""
import random

import pytest


def fixed(*values):
    """A rand() that returns the given values in order, then repeats the last one."""
    seq = list(values)

    def rand():
        return seq.pop(0) if len(seq) > 1 else seq[0]
    return rand


class Script:
    """fn() that raises the scripted exceptions in order, then returns 'ok'. Optionally costs time."""

    def __init__(self, outcomes, clock=None, cost=0.0):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.clock, self.cost = clock, cost

    def __call__(self):
        self.calls += 1
        if self.clock is not None:
            self.clock.t += self.cost
        if self.outcomes:
            exc = self.outcomes.pop(0)
            if exc is not None:
                raise exc
        return "ok"


def call(c2, fn, clock, **kw):
    kw.setdefault("rand", fixed(1.0))
    return c2.retry_call(fn, sleep=clock.sleep, now=clock.now, **kw)


def test_success_on_first_attempt_does_not_sleep(c2, clock):
    fn = Script([])
    assert call(c2, fn, clock) == "ok"
    assert fn.calls == 1 and clock.sleeps == []


def test_delays_are_full_jitter_of_capped_exponential(c2, clock):
    T = c2.TransientError
    fn = Script([T(), T(), T(), None])
    out = call(c2, fn, clock, base=0.1, cap=5.0, rand=fixed(0.5, 0.25, 0.75))
    assert out == "ok" and fn.calls == 4
    assert clock.sleeps == pytest.approx([0.5 * 0.1, 0.25 * 0.2, 0.75 * 0.4])


def test_cap_limits_the_exponential(c2, clock):
    T = c2.TransientError
    fn = Script([T()] * 5 + [None])
    call(c2, fn, clock, base=1.0, cap=3.0, max_attempts=6, rand=fixed(1.0))
    assert clock.sleeps == pytest.approx([1.0, 2.0, 3.0, 3.0, 3.0])


def test_jitter_can_be_zero(c2, clock):
    """Full jitter draws from [0, bound]: rand() = 0 means no wait (equal jitter or no jitter would wait)."""
    T = c2.TransientError
    fn = Script([T(), T(), None])
    call(c2, fn, clock, base=1.0, cap=10.0, rand=fixed(0.0))
    assert clock.sleeps == pytest.approx([0.0, 0.0])


def test_random_delays_stay_within_bounds(c2, clock):
    T = c2.TransientError
    fn = Script([T()] * 9 + [None])
    rng = random.Random(7)
    call(c2, fn, clock, base=0.2, cap=6.0, max_attempts=10, rand=rng.random)
    assert len(clock.sleeps) == 9
    for n, d in enumerate(clock.sleeps, start=1):
        assert 0.0 <= d <= min(6.0, 0.2 * 2 ** (n - 1)) + 1e-12
    assert len(set(clock.sleeps)) > 1           # actually random, not a fixed schedule


def test_gives_up_after_max_attempts_and_reraises_the_last_error(c2, clock):
    T = c2.TransientError
    errors = [T(f"fail {i}") for i in range(3)]
    fn = Script(list(errors) + [None])
    with pytest.raises(T) as info:
        call(c2, fn, clock, max_attempts=3)
    assert info.value is errors[2]               # the original object, not a wrapper
    assert fn.calls == 3 and len(clock.sleeps) == 2


def test_max_attempts_one_means_no_retry(c2, clock):
    T = c2.TransientError
    fn = Script([T(), None])
    with pytest.raises(T):
        call(c2, fn, clock, max_attempts=1)
    assert fn.calls == 1 and clock.sleeps == []


def test_non_retryable_errors_are_raised_immediately(c2, clock):
    err = ValueError("bad request")
    fn = Script([err, None])
    with pytest.raises(ValueError) as info:
        call(c2, fn, clock)
    assert info.value is err and fn.calls == 1 and clock.sleeps == []


def test_custom_retry_predicate(c2, clock):
    fn = Script([ConnectionError(), ConnectionError(), None])
    out = call(c2, fn, clock, is_retryable=lambda e: isinstance(e, ConnectionError))
    assert out == "ok" and fn.calls == 3


def test_retry_after_wins_over_jitter_and_is_capped(c2, clock):
    T = c2.TransientError
    fn = Script([T(retry_after=2.5), T(retry_after=100.0), T(retry_after=0.0), None])
    call(c2, fn, clock, base=0.1, cap=5.0, rand=fixed(0.1))
    assert clock.sleeps == pytest.approx([2.5, 5.0, 0.0])


def test_deadline_stops_before_a_sleep_that_would_exceed_it(c2, clock):
    T = c2.TransientError
    fn = Script([T(), T(), T(), None])
    with pytest.raises(T):
        call(c2, fn, clock, base=1.0, cap=10.0, deadline=2.5, rand=fixed(1.0))
    # t=0 fail, sleep 1 -> t=1 fail, next sleep 2 would end at t=3 > 2.5: give up without sleeping
    assert clock.sleeps == pytest.approx([1.0])
    assert fn.calls == 2


def test_deadline_counts_time_spent_inside_fn(c2, clock):
    T = c2.TransientError
    fn = Script([T(), T(), None], clock=clock, cost=1.0)        # each call takes 1 s
    with pytest.raises(T):
        call(c2, fn, clock, base=0.5, cap=10.0, deadline=2.0, rand=fixed(1.0))
    # call 1 ends at 1.0, sleep 0.5 -> 1.5; call 2 ends at 2.5 >= deadline: no third attempt
    assert fn.calls == 2 and clock.sleeps == pytest.approx([0.5])


def test_keyboard_interrupt_is_never_retried(c2, clock):
    fn = Script([KeyboardInterrupt(), None])
    with pytest.raises(KeyboardInterrupt):
        call(c2, fn, clock, is_retryable=lambda e: True)
    assert fn.calls == 1


@pytest.mark.parametrize("kw", [{"max_attempts": 0}, {"base": -1.0}, {"cap": -0.5}])
def test_invalid_arguments_are_rejected(c2, clock, kw):
    with pytest.raises(ValueError):
        call(c2, Script([]), clock, **kw)

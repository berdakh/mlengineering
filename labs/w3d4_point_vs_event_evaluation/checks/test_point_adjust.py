"""point_adjust: any flagged row inside a true event marks the whole event; nothing else changes."""
import numpy as np


def f1(y, pred):
    tp = int(np.sum((pred == 1) & (y == 1)))
    if tp == 0:
        return 0.0
    precision, recall = tp / pred.sum(), tp / y.sum()
    return 2 * precision * recall / (precision + recall)


def test_known_answer(ev):
    y = [0, 1, 1, 1, 0, 1, 1, 0]
    pred = [1, 0, 1, 0, 0, 0, 0, 1]
    assert list(ev.point_adjust(y, pred)) == [1, 1, 1, 1, 0, 0, 0, 1]


def test_rows_outside_true_events_are_untouched_and_input_is_not_modified(ev):
    rng = np.random.default_rng(0)
    y = np.zeros(400, dtype=int)
    y[100:180] = 1
    y[300:320] = 1
    pred = (rng.random(400) < 0.1).astype(int)
    before = pred.copy()
    out = np.asarray(ev.point_adjust(y, pred))
    assert np.array_equal(pred, before), "point_adjust must not modify its input"
    assert np.array_equal(out[y == 0], pred[y == 0])
    assert (out >= pred).all()


def test_no_flag_in_an_event_leaves_it_missed(ev):
    y = np.array([0, 1, 1, 0, 1, 1])
    assert list(ev.point_adjust(y, np.zeros(6, dtype=int))) == [0] * 6
    assert list(ev.point_adjust(y, np.array([0, 0, 0, 1, 0, 0]))) == [0, 0, 0, 1, 0, 0]


def test_is_idempotent(ev):
    rng = np.random.default_rng(3)
    y = (np.arange(600) % 200 >= 150).astype(int)
    pred = (rng.random(600) < 0.05).astype(int)
    once = np.asarray(ev.point_adjust(y, pred))
    assert np.array_equal(np.asarray(ev.point_adjust(y, once)), once)


def test_point_adjust_turns_a_random_scorer_into_a_near_perfect_one(ev):
    """The property that makes the protocol unusable: SYNTHETIC labels with five 300-row events."""
    rng = np.random.default_rng(0)
    y = np.zeros(5000, dtype=int)
    for start in range(500, 5000, 1000):
        y[start:start + 300] = 1
    pred = (rng.random(5000) < 0.02).astype(int)          # knows nothing
    raw = f1(y, pred)
    adjusted = f1(y, np.asarray(ev.point_adjust(y, pred)))
    assert raw < 0.1
    assert adjusted > 0.9

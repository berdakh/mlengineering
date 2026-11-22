"""SYNTHETIC e-commerce feature stream for the w7d2 challenge.

    python lessons/w7d2_input_monitoring_drift/challenge/data/make_stream.py --seed 0 --out stream.csv

70 days x 400 sessions. Columns: ``day``, ``price`` (EUR, mean basket item price), ``basket_size``
(items, may be missing), ``session_length_s``, ``page_views``. Weekends (day % 7 in {5, 6}) have slightly
larger baskets and longer sessions: real, harmless variation a monitor must not page on.

Events (``EVENTS``; the calendar file lists ONLY the planned one, as a real change calendar would):

* day 30: planned price increase of 12 % (in calendar.csv).
* day 42: session_length_s logged ~1.8x too long from now on (a tracking bug; unplanned).
* day 50: price 10 % lower from now on (a currency-conversion bug; unplanned).
* days 56-59: 30 % of basket_size values missing (an upstream outage; unplanned).

Nothing here is real data; it exists to grade a monitoring design, not to say anything about shops.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DAYS, SESSIONS = 70, 400
EVENTS = {
    "planned_price_change": {"day": 30, "feature": "price", "factor": 1.12},
    "session_length_bug": {"day": 42, "feature": "session_length_s", "factor": 1.8},
    "price_currency_bug": {"day": 50, "feature": "price", "factor": 0.90},
    "basket_missing": {"day": 56, "end_day": 60, "feature": "basket_size", "share": 0.30},
}
CALENDAR = pd.DataFrame([{"day": 30, "features": "price", "note": "planned price increase (+12 %)"}])


def generate(seed: int = 0, days: int = DAYS, sessions: int = SESSIONS) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for d in range(days):
        weekend = d % 7 in (5, 6)
        n = sessions
        price = rng.lognormal(np.log(24.0), 0.35, n)
        basket = rng.poisson(2.6 + (0.3 if weekend else 0.0), n) + 1.0
        length = rng.gamma(2.0, 160.0 * (1.08 if weekend else 1.0), n)
        views = rng.poisson(6.0 + 0.004 * length) + 1
        if d >= EVENTS["planned_price_change"]["day"]:
            price = price * EVENTS["planned_price_change"]["factor"]
        if d >= EVENTS["price_currency_bug"]["day"]:
            price = price * EVENTS["price_currency_bug"]["factor"]
        if d >= EVENTS["session_length_bug"]["day"]:
            length = length * EVENTS["session_length_bug"]["factor"]
        if EVENTS["basket_missing"]["day"] <= d < EVENTS["basket_missing"]["end_day"]:
            basket[rng.random(n) < EVENTS["basket_missing"]["share"]] = np.nan
        frames.append(pd.DataFrame({"day": d, "price": np.round(price, 2), "basket_size": basket,
                                    "session_length_s": np.round(length, 1), "page_views": views}))
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    df = generate(args.seed)
    df.to_csv(args.out, index=False)
    print(f"wrote {args.out}: {len(df)} rows, days 0-{df['day'].max()}")


if __name__ == "__main__":
    main()

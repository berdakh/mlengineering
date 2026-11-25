# TableTop no-show evaluation (reference report; SYNTHETIC data; numbers from `lab/evaluate.py`, 2026-11-22)

| Conditions | |
|---|---|
| Start / stop time | reference written outside the time box |
| Looked up | scikit-learn and pandas docs |
| Finished? | yes |

## 1. Framing
Unit: one reservation, scored on the evening before its service day. Label: `no_show`. Action: the
team phones the top 10 % (rounded up) of the next day's reservations. Decision metric: share of
calls that reach a would-be no-show, pooled over the test days (daily top-10 % precision).

## 2. Leak audit
| Column | Known the evening before? | Reason | Used? |
|---|---|---|---|
| restaurant_id, slot, channel, party_size, lead_days, deposit_paid | yes | set at booking | yes |
| booked_at, service_date | yes | booking record | only via derived `weekend` |
| prior_visits, prior_no_shows | yes | counts over *earlier* service dates (checked: increase with time per customer) | yes, plus their ratio |
| customer_no_show_rate | **no** | mean over the guest's whole history, including this and later reservations | no |
| table_released_at | **no** | filled exactly for no-shows: it *is* the outcome | no |
| reminder_reply | **no** | reply to the reminder sent on the service day, after the call list is made | no |
| reservation_id, customer_id | - | identifiers | no |

## 3. Split
Train: reservations served before 2024-10-01 (6,529; outcomes known that evening). Test: all
reservations served from 2024-10-01 (2,223 over 92 days), **including 189 booked in September**, whose
outcome was not known at training time. Splitting by `booked_at` would put those in training.

## 4. Baseline and model
| Approach | Daily top-10 % precision | Interval |
|---|---|---|
| random calls (prevalence) | 0.173 | - |
| rule: no deposit first, then longest lead time | 0.322 | - |
| logistic regression on booking-time features | 0.371 | [0.313, 0.425] |
| generator's own probabilities (checks only; not available in practice) | 0.409 | - |

264 calls in the test period: about 98 reach a would-be no-show with the model, 85 with the rule.

## 5. Interval
Bootstrap over the 92 service days (2,000 resamples), training held fixed. Days are the unit the call
list is made for; reservations of one day share conditions. It covers test-set sampling only, not
retraining variance or a change in the guest population. The rule's interval was not computed, so
"model beats rule" is not established: the difference (0.05) is about the half-width of the model's interval.

## 6. One slice
By booking channel among the called reservations: partner 58 calls, precision 0.43; web 104, 0.38;
phone 55, 0.36; app 47, 0.30. Small slices; next check whether partner bookings are over-called
because of lead time.

## 7. Limitations
Synthetic data (no conclusion about real diners). One test period (October-December, includes the
pre-holiday season). The interval ignores model retraining. Calls change behaviour: once deployed,
called guests who would not have come cancel, so future labels are affected by the policy.

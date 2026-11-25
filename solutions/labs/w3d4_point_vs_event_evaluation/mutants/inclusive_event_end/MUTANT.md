# Mutant: inclusive event end

`extract_events` returns `(start, last_row)` instead of `(start, end)` with `end` exclusive.

**Why it is plausible.** "The event runs from row 573 to row 973" is how one says it aloud, and an
inclusive end survives a quick look at the output.

**What goes wrong.** Every length is one row short, a one-row event has length 0,
`binary[start:end]` no longer selects the event, and an alarm starting on the last row of a true
event is scored as a false alarm.

**Caught by.** `test_extract_events.py` (known answers, reconstruction property).

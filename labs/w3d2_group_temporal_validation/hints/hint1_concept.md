# Hint 1 - read the deployment sentence word by word

Each phrase of a deployment sentence withholds something:

| Phrase | What validation must withhold |
|---|---|
| "new pumps / new stores / new patients" | every row of the validation units from training (grouping) |
| "next month / the following eight weeks" | everything after the cut-off from training (time) |
| "retrained at the end of the quarter" | labels not yet *observed* at the cut-off, even if the row's own date is earlier |
| "a fault type it never saw" | a whole category of units (leave-one-category-out) |

For the lab: the project's deployment question is about new experiments (new pumps or runs) of known
fault families, with a stress test for an unseen family. Rows from one experiment share its operating
point and sensor offsets, so they are not independent.

For buffers: a row's information comes from a span of raw samples, $[i-w+1, i+h]$. Two rows are
dependent through shared samples when their spans intersect. Count the rows you must drop so that no
training span touches a validation span.

For the challenge: a "known" store is one the *model* has seen, not one the *business* considers old.

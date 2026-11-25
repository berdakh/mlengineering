# f3_cleaning - reviewer notes (parallel form of a3)

Planted defects mirror a3 one for one: duplicates with stale versions, three date formats incl.
offsets (UTC date is the definition), categorical noise with missing codes, a unit column that
changes the meaning of the number (annual vs monthly instead of cents vs dollars), sentinel and
impossible values. The reference `lab/NOTES.md` has the measured counts.

## Common incorrect answers and why they fail

* `pd.to_datetime(..., dayfirst=True)` on the mixed column: guesses per value; the offset rows are
  either left tz-aware or converted to local dates. Parse each format explicitly.
* Keeping the *first* row per account, or `drop_duplicates()` only: stale tiers survive.
* Dividing every fee by 12, or none: unit column ignored.
* Filling missing employees with 0 or the median: the contract says missing.

## Rubric (assign per aspect)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Finding defects | NOTES lists every defect with counts found by inspection | most defects, counts missing | defects inferred from check names only |
| pandas fluency | vectorised, explicit formats, no row loops needed | works but via apply/loops or trial and error | does not pass |
| Time zones | UTC date from offset timestamps, stated why | correct by accident (e.g. via a parser default) | local date kept |
| Judgment | each decision justified (what is "missing", which version wins) | decisions made silently | arbitrary fills |

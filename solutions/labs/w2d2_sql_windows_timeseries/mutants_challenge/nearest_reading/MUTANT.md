# Mutant: nearest_reading

`last_temperature` takes the reading *nearest in time* to the label rather than the latest reading
at or before it. Roughly half the time the nearest reading is a few minutes after the label. The
leak is subtle: values look plausible and usually differ only slightly from the correct ones.
pandas equivalent: `merge_asof(..., direction="nearest")`.

Changed file: `features.sql`

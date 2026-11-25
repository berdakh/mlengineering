# Challenge notes (reference answer to acceptance criterion 6)

Altering later values only proves that later *values* are not read. On irregular data the
*presence and timing* of later rows can also leak: a centred or bidirectional time window, a
"next reading" interval feature, or interpolation onto a regular grid all change when a future
row is removed even if no value is altered. Truncation reproduces what the device has actually
seen at that moment, so it is the stronger statement of point-in-time correctness.

A fixed row-count window (for example "the last 6 readings" as a stand-in for 30 s) reads only
the past and passes every look-ahead and truncation test. It is still wrong: the time it covers
varies with the sampling rate, so the feature's meaning and variance change from row to row.
Causality tests cannot catch a feature that is causal and mis-specified; only a test against
the definition (reference comparison, the seconds-not-rows test) does.

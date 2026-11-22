# Hint 1: concepts

* Two empirical CDFs are step functions that only change at sample points. Evaluate both on the sorted
  union of the samples and you have them exactly; KS is the largest vertical gap, W1 the area between them.
* A share of 0 in a PSI bin is common (small windows, a shift past the reference range). Floor shares,
  do not drop bins.
* A row with -9999 is not "drifted data"; it is not data. Decide what a violation is before computing
  any statistic.
* With m sensors tested in every window, ask what the chance is that at least one exceeds its threshold.
* Challenge: a calendar tells you WHEN to expect change on WHICH feature. After the change settles, what
  should "normal" mean for that feature?

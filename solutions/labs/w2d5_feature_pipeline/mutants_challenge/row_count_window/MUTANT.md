# Mutant: row_count_window

The window is a fixed number of rows chosen from the average sampling interval (about 4.75 s) instead of a span of time. It is causal and passes every look-ahead test, which is why it is a tempting shortcut, but on irregular data a '30 s' feature then covers anything from a few seconds to minutes. Caught by the reference comparison, the seconds-not-rows test and the boundary test.

Changed file: `timefeatures.py`

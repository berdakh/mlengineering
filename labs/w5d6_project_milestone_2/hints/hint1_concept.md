# Hint 1 (concept)

Ask of every number the API returns: *which function computed it, and does the evaluation report's
number come from the same function?* If the answer is "a copy", that copy is the bug, even if it is
right today. The release is ready when (a) the score formula exists once, (b) a test compares the three
paths on the same input, (c) the artifact names the config and manifest it came from, and (d) the
version is written once. Everything else on the checklist follows from these four.

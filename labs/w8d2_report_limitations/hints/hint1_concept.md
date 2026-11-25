# Hint 1 (concept)

The checker is a linter for claims. Each rule turns a reviewer's habit into a test:

* "Where does this number come from?" → every number must equal some value in the results file *at the precision
  written*. Rounding is the point: the report says 0.884, the file says 0.8842514; they agree to three decimals.
* "Bootstrap over what?" → an interval and its method live in the same block of text, so the reader never has to
  search for them.
* "Which test?" → the word "significant" carries a test name or p value with it.
* "So what?" → each limitation says its impact and its mitigation.

Work line by line for numbers and block by block (text between blank lines) for intervals and significance.

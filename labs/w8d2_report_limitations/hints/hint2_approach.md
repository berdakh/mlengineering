# Hint 2 (approach)

* `strip_markup(line)`: a few `re.sub` calls in order: inline code (text between backticks), link targets (the parenthesised part after a closing bracket), URLs,
  dates `\d{4}-\d{2}-\d{2}`, version strings `\d+(\.\d+){2,}`, and a leading list marker. Replace with a space,
  not with nothing, so neighbouring tokens do not merge.
* `traced(token, percent, leaves)`: parse the token (drop thousands commas), count the decimals written, and look
  for any leaf with `round(leaf * (100 if percent else 1), d) == round(value, d)`.
* `check`:
  1. `sections(lines)` gives titles; each required name must start one of them (case-insensitive).
  2. For each line outside code blocks that is not a heading or an image: `NUMBER.finditer(strip_markup(line))`;
     group 1 is the number, group 2 the optional `%`.
  3. For each `blocks(lines)` block: `INTERVAL` without `METHOD` → `interval_without_unit`; `SIGNIFICANT` without
     `TEST_REF` → `significance_without_test`.
  4. Limitations: collect list items (a line starting with `*`, `-` or `1.`, plus indented continuation lines);
     count them and the ones containing both `Impact:` and `Mitigation:`.

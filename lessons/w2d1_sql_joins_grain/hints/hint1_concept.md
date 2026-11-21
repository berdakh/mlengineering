# Hint 1 — concept

Ask one question of every join before you write it:

> **For one row on the left, how many rows on the right can match: at most one, or many?**

If the answer is "many", the result is now at the child's grain. From that point on you may only
aggregate measures that are defined at that grain. A measure that came from the parent, or from a
*different* child, is repeated and must not be summed, counted or averaged there.

Second question, for every condition that mentions a table reached through a `LEFT JOIN`:

> **Should entities with no matching child still appear?** If yes, the condition cannot be in `WHERE`.

Third, for every anti-join ("never", "without", "no …"):

> **Can the column I compare against be NULL?** If yes, `NOT IN` will return nothing.

For the challenge: the phrase "for every X" fixes the driving table (X) and the grain (one row per X).
"Distinct parts ever used on a machine" is a statement about a set across several work orders, not
about part lines.

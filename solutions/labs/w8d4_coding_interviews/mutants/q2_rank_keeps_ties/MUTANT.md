# q2_rank_keeps_ties
RANK() gives tied drivers the same rank, so a city can return three or more rows. Caught by:
test_q2_ties_give_exactly_two_rows (and the oracle tests when ties exist).

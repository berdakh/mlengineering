# Mutant: recommend = leaderboard

`recommend` returns the eligible candidate with the highest primary metric, ignoring the practical
difference and the complexity ranking. Caught by `test_recommend_prefers_simple_when_nothing_is_better`.

# threshold_ignores_success_rate

The break-even probability is computed as cost / customer value, as if every customer who receives the offer and would have churned were saved.

Why it is plausible: `p >= C / B` is the textbook rule; the benefit `B` silently has to include the probability that the action works.

Why it is wrong: with a 25% success rate the true break-even probability is four times higher. The policy offers to customers whose expected value is negative.

Caught by: `test_offer_threshold_is_the_break_even_probability`.

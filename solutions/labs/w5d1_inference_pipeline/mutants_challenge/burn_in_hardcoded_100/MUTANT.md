# Mutant: burn-in "fixed" by changing the constant to 100

Matches today's model, so every comparison with the shipped model passes; the next model with a
different burn-in would silently skew. Caught by `test_serving_takes_the_burn_in_from_the_model`.

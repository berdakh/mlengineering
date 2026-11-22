# Mutant: teardown_forgets_bucket

The teardown removes the compute but not the bucket. Its storage keeps costing, and a forgotten
bucket with a model in it is exactly what later gets made public 'for a quick test'.

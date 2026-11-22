# Mutant: size from sys.getsizeof

Measures the Python object header with `sys.getsizeof` instead of serialising the model, so a model
holding a 1.6 MB array reports a few hundred bytes. Caught by `test_size_counts_contents_not_the_wrapper`.

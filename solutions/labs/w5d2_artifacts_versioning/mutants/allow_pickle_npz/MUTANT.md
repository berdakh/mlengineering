# Mutant: numpy.load with allow_pickle=True

Object arrays in an `.npz` file are stored as pickles; `allow_pickle=True` unpickles them on load. With
the checksums rewritten, a crafted `reference.npz` then runs code when the model loads. Caught by
`test_pickled_array_is_not_loaded`.

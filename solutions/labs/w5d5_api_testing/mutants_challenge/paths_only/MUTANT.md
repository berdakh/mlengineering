# Mutant: paths only

Compares the sets of (method, path) and nothing else. It catches a removed endpoint and misses every
change inside a request or response body, which is where most real breaks happen. Its own contract
test on v1/v2 fails too, because v2 keeps all v1 paths.

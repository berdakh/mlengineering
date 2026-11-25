# Mutant: the image job has no `needs`
Jobs run in parallel by default, so the image is built and smoke-tested even when the tests fail.
Caught by: test_image_is_built_after_tests_and_smoke_tested.

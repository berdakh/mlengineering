# Mutant: unquoted Python versions in the matrix
`python-version: [3.10, 3.11, 3.12]` - YAML reads 3.10 as the float 3.1, so that matrix entry asks for
Python 3.1. Caught by: test_tests_run_on_a_quoted_python_matrix.

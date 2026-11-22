# Mutant: versions sorted as strings

`list_versions` sorts lexically, so 1.10.0 comes before 1.9.0 and "the latest version" is wrong as soon
as a minor version reaches 10. Caught by `test_versions_are_listed_in_semantic_order`.

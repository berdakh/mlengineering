# Mutant: query tool assumes every line is JSON

Real log files contain uvicorn text lines, truncated writes and crash dumps. A tool that dies on the first one is useless during an incident. Caught by `test_find_request_keeps_order_and_skips_junk`.

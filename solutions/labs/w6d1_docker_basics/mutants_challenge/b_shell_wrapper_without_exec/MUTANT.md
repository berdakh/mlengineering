# b_shell_wrapper_without_exec
Plausible mistake: rewriting the CMD as a JSON array that starts sh -c with the same && chain. That is exec form for the shell, not for uvicorn: the shell stays PID 1 and still swallows SIGTERM. Expected to fail: test_b_server_receives_sigterm (the script would need `exec uvicorn ...`).

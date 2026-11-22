# shell_form_cmd
Plausible mistake: CMD written as a plain string. /bin/sh becomes PID 1 and does not pass SIGTERM on; `docker stop` waits the 10 s grace period and kills the server (measured: 10.2-10.4 s, exit 137). Expected to fail: test_the_command_is_exec_form_uvicorn_on_all_container_interfaces.

# binds_container_loopback
Plausible mistake: --host 127.0.0.1 inside the container (uvicorn's default, or copied from a local run). The healthcheck inside the container still passes, but the published port reaches nothing (measured: curl: (56) Connection reset by peer). Expected to fail: test_the_command_is_exec_form_uvicorn_on_all_container_interfaces.

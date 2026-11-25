# runs_as_root
Plausible mistake: the Dockerfile works, but it never creates or switches to an unprivileged user, so uvicorn runs as root (UID 0) inside the container. Expected to fail: test_the_container_runs_as_an_unprivileged_user.

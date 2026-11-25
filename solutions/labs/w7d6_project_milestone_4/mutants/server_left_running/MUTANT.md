# Mutant: server_left_running

A promotion or rollback starts a new service process without stopping the old one. The demo looks fine, but two processes now share the log file and one keeps serving the old model until someone notices a port still bound.

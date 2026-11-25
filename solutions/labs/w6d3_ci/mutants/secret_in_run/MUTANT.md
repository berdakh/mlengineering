# Mutant: a secret interpolated into a run script
`echo "${{ secrets.REGISTRY_TOKEN }}" | docker login ...` puts the secret into the generated script text
(and invites someone to drop the pipe and print it). Caught by: test_no_secret_is_interpolated_into_a_shell_command.

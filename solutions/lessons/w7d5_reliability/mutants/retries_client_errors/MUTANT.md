# Mutant: retries_client_errors

The client retries every error status, including 400/404/422. A malformed request fails identically every time; retrying it multiplies load and delays the real error.

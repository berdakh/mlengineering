# Mutant: default_validation_body

No handler for `RequestValidationError`: FastAPI's default 422 body `{"detail": [...]}` is returned,
so clients must parse two error formats and the 422 carries no request id.

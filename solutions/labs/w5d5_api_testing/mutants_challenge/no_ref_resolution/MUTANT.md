# Mutant: no $ref resolution

Compares the request and response schemas exactly as they appear under `paths`. FastAPI writes every
pydantic body as `{"$ref": "#/components/schemas/Name"}`, so the compared objects are identical
pointers and all field-level changes are invisible. A classic OpenAPI-diff bug.

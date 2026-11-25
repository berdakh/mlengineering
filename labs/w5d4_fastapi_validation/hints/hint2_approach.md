# Hint 2 - approach (w5d4)

**Lab, inside `create_app`:**

```text
lifespan:   try load_bundle -> app.state.detector; except BundleError -> None (log it); yield
middleware: read/validate X-Request-ID or generate; request.state.request_id; set response header
class ApiError(Exception): status_code, code, message, details
handlers:   ApiError -> its status; RequestValidationError -> 422 + details from exc.errors();
            starlette HTTPException -> 404/405 codes; Exception -> 500 generic, logger.exception
endpoints:  /healthz, /readyz (raise ApiError 503 if no detector), /version, /predict (def, not async)
/predict:   detector or 503 -> timestamps strictly increasing (and same tz-awareness) or 400
            -> DataFrame (rename timestamp -> datetime) -> score_batch -> results
```

Build the error body in exactly one function and call it from every handler, so the shape cannot drift.

**Challenge.** Create the `StreamRegistry` in the lifespan (only when the model loaded). One endpoint
per row of the contract table. Map `UnknownMachineError` to 404, `OutOfOrderError` and
`ConflictingDuplicateError` to 409 with different codes. For `PUT`, take `response: Response` as a
parameter and set `response.status_code` to 201 or 200. Constrain the path parameter with
`fastapi.Path(pattern=...)`.

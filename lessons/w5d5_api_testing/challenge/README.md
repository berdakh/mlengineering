# Challenge: catch the breaking change before release (independent)

`apps/v1.py` builds the released API (schema `flowguard-api/1`). `apps/v2.py` builds a colleague's
proposal, described in the pull request as "fully backwards compatible". Only the OpenAPI documents
matter: `v1.create_app().openapi()` and `v2.create_app().openapi()`.

## Tasks

1. **`compat.py`**: implement `breaking_changes(old: dict, new: dict) -> list[str]`. Return one message
   per breaking change; each message contains the HTTP method and path (`"POST /predict: ..."`).
   An empty list means a client written against `old` keeps working against `new`.
2. **`test_contract.py`**: contract tests that would block the release of v2 (assert the specific
   breaking changes you expect, not just "some change"), and that pass for v1 against itself.
3. **`COMPATIBILITY.md`**: replace every TODO. The policy must say how versions are named, what you
   change without notice, how breaking changes are shipped, how the rule is enforced, and give a
   verdict on v2 that names each breaking change and how to ship the useful parts without breaking v1.

## What counts as breaking

Think from the client's side. Compare every (method, path) of `old` with `new`; for each, compare the
JSON request body and every 2xx JSON response body. Bodies are usually `{"$ref": "#/components/schemas/..."}`.

| Change | Breaking? |
|---|---|
| (method, path) removed, or a 2xx status removed | yes |
| request: a field becomes required | yes |
| request: a field removed while unknown fields are rejected (`additionalProperties: false`) | yes |
| request: a field's type changes so that old values are no longer accepted | yes |
| request: `maxItems`/`maxLength`/`maximum` decreased, `minItems`/`minLength`/`minimum` increased, or newly added | yes |
| response: a field removed | yes |
| response: a field no longer in `required` | yes |
| response: a field may now have a type it could not have before (including `null`) | yes |
| new endpoint; new optional request field; new response field; relaxed request constraint; changed titles or descriptions | no |

Types: compare *type signatures*. `{"type": "number"}` -> `{number}`; `anyOf`/`oneOf` -> the union of
the members; arrays -> `array<items>`, e.g. `array<number>`.

## Acceptance criteria

`python wb.py check w5d5 --challenge` passes. The checks build pairs of small FastAPI apps that differ
in exactly one way: 8 breaking pairs must be reported (with the path in the message), 6 compatible
pairs must not; your `test_contract.py` must pass; `COMPATIBILITY.md` must be complete.

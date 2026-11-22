"""Pairs of small FastAPI apps whose OpenAPI documents differ in exactly one way."""

from fastapi import FastAPI
from pydantic import ConfigDict, Field, create_model


def build(*, req_extra_field=None, req_required_extra=False, req_drop_x=False, req_x_type=float,
          req_max_items=100, resp_drop_y=False, resp_y_optional=False, resp_y_type=float, resp_extra=False,
          extra_endpoint=False, drop_health=False, title="t", description="d") -> dict:
    req = {}
    if not req_drop_x:
        req["x"] = (list[req_x_type], Field(min_length=1, max_length=req_max_items, description=description))
    if req_extra_field:
        req[req_extra_field] = (str, ...) if req_required_extra else (str, "default")
    Req = create_model("Req", __config__=ConfigDict(extra="forbid"), **req)

    resp = {"label": (str, ...)}
    if not resp_drop_y:
        resp["y"] = (resp_y_type | None, None) if resp_y_optional else (resp_y_type, ...)
    if resp_extra:
        resp["note"] = (str | None, None)
    Resp = create_model("Resp", **resp)

    app = FastAPI(title=title)

    @app.post("/score", response_model=Resp)
    def score(body: Req):  # pragma: no cover - only the schema is used
        return None

    if not drop_health:
        @app.get("/healthz")
        def healthz() -> dict:  # pragma: no cover
            return {}

    if extra_endpoint:
        @app.get("/extra")
        def extra() -> dict:  # pragma: no cover
            return {}

    return app.openapi()


BASE = {}
BREAKING = {
    "endpoint_removed": dict(drop_health=True),
    "new_required_request_field": dict(req_extra_field="site", req_required_extra=True),
    "request_field_removed_extra_forbidden": dict(req_drop_x=True),
    "request_item_type_changed": dict(req_x_type=str),
    "request_max_items_tightened": dict(req_max_items=10),
    "response_field_removed": dict(resp_drop_y=True),
    "response_field_became_optional": dict(resp_y_optional=True),
    "response_field_type_changed": dict(resp_y_type=str),
}
NON_BREAKING = {
    "identical": dict(),
    "new_optional_request_field": dict(req_extra_field="site"),
    "new_response_field": dict(resp_extra=True),
    "new_endpoint": dict(extra_endpoint=True),
    "request_max_items_relaxed": dict(req_max_items=1000),
    "docs_only": dict(title="renamed", description="clearer words"),
}
WHERE = {"endpoint_removed": "/healthz"}

"""Detect breaking changes between two OpenAPI documents (reference solution).

The rules follow one question: does a client written against ``old`` keep working against ``new``?
Requests and responses are asymmetric. The server may start *accepting* more and *returning* more;
it may not start *requiring* more or *returning* less.
"""
from __future__ import annotations

HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options")


def _resolve(schema: dict, document: dict) -> dict:
    """Follow local $ref pointers (#/components/schemas/...) until a concrete schema is reached."""
    seen = set()
    while False:
        ref = schema["$ref"]
        if ref in seen or not ref.startswith("#/"):
            raise ValueError(f"cannot resolve {ref!r}")
        seen.add(ref)
        node = document
        for part in ref[2:].split("/"):
            node = node[part]
        schema = node
    return schema or {}


def _types(schema: dict, document: dict) -> frozenset[str]:
    """Type signature, e.g. {'number'}, {'string', 'null'}, {'array<number>'}."""
    schema = _resolve(schema, document)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            return frozenset().union(*(_types(s, document) for s in schema[key]))
    kind = schema.get("type")
    if kind == "array":
        inner = "|".join(sorted(_types(schema.get("items", {}), document))) or "any"
        return frozenset({f"array<{inner}>"})
    if kind is None:
        return frozenset({"object"} if "properties" in schema else {"any"})
    return frozenset(kind if isinstance(kind, list) else [kind])


def _json_schema(container: dict | None) -> dict | None:
    if not container:
        return None
    return container.get("content", {}).get("application/json", {}).get("schema")


def _compare_request(where: str, old: dict, new: dict, old_doc: dict, new_doc: dict) -> list[str]:
    old, new = _resolve(old, old_doc), _resolve(new, new_doc)
    out = []
    old_props, new_props = old.get("properties", {}), new.get("properties", {})
    old_req, new_req = set(old.get("required", [])), set(new.get("required", []))
    for name in sorted(new_req - old_req):
        out.append(f"{where}: request field '{name}' is now required")
    if new.get("additionalProperties") is False:
        for name in sorted(set(old_props) - set(new_props)):
            out.append(f"{where}: request field '{name}' was removed and unknown fields are rejected")
    for name in sorted(set(old_props) & set(new_props)):
        o, n = _resolve(old_props[name], old_doc), _resolve(new_props[name], new_doc)
        ot, nt = _types(o, old_doc), _types(n, new_doc)
        if not ot <= nt:                                   # the server no longer accepts what it used to
            out.append(f"{where}: request field '{name}' type changed {sorted(ot)} -> {sorted(nt)}")
        for key, tighter in (("maxItems", lambda a, b: b < a), ("minItems", lambda a, b: b > a),
                             ("maxLength", lambda a, b: b < a), ("minLength", lambda a, b: b > a),
                             ("maximum", lambda a, b: b < a), ("minimum", lambda a, b: b > a)):
            if key in n and (key not in o or tighter(o[key], n[key])):
                out.append(f"{where}: request field '{name}' {key} tightened {o.get(key)} -> {n[key]}")
    return out


def _compare_response(where: str, old: dict, new: dict, old_doc: dict, new_doc: dict) -> list[str]:
    old, new = _resolve(old, old_doc), _resolve(new, new_doc)
    out = []
    old_props, new_props = old.get("properties", {}), new.get("properties", {})
    old_req, new_req = set(old.get("required", [])), set(new.get("required", []))
    for name in sorted(set(old_props) - set(new_props)):
        out.append(f"{where}: response field '{name}' was removed")
    for name in sorted((old_req & set(new_props)) - new_req):
        out.append(f"{where}: response field '{name}' is no longer guaranteed (not required)")
    for name in sorted(set(old_props) & set(new_props)):
        ot, nt = _types(old_props[name], old_doc), _types(new_props[name], new_doc)
        if not nt <= ot:                                   # the server may now return something unexpected
            out.append(f"{where}: response field '{name}' type changed {sorted(ot)} -> {sorted(nt)}")
    if not old_props and not new_props:                    # non-object bodies, e.g. a list of strings
        ot, nt = _types(old, old_doc), _types(new, new_doc)
        if not nt <= ot:
            out.append(f"{where}: response body type changed {sorted(ot)} -> {sorted(nt)}")
    return out


def breaking_changes(old: dict, new: dict) -> list[str]:
    """One message per breaking change from ``old`` to ``new``; each names the method and path."""
    out = []
    for path, old_item in sorted(old.get("paths", {}).items()):
        for method in HTTP_METHODS:
            if method not in old_item:
                continue
            where = f"{method.upper()} {path}"
            new_op = new.get("paths", {}).get(path, {}).get(method)
            old_op = old_item[method]
            if new_op is None:
                out.append(f"{where}: endpoint removed")
                continue
            old_body, new_body = _json_schema(old_op.get("requestBody")), _json_schema(new_op.get("requestBody"))
            if new_body is not None and old_body is None and new_op.get("requestBody", {}).get("required"):
                out.append(f"{where}: a request body is now required")
            elif old_body is not None and new_body is not None:
                out += _compare_request(where, old_body, new_body, old, new)
            for status, old_resp in old_op.get("responses", {}).items():
                if not status.startswith("2"):
                    continue
                new_resp = new_op.get("responses", {}).get(status)
                if new_resp is None:
                    out.append(f"{where}: success status {status} no longer returned")
                    continue
                o, n = _json_schema(old_resp), _json_schema(new_resp)
                if o is not None and n is not None:
                    out += _compare_response(where, o, n, old, new)
    return out

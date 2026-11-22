HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options")


def breaking_changes(old: dict, new: dict) -> list[str]:
    out = []
    for path, item in old.get("paths", {}).items():
        for method in HTTP_METHODS:
            if method in item and method not in new.get("paths", {}).get(path, {}):
                out.append(f"{method.upper()} {path}: endpoint removed")
    return out

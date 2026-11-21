"""Packaging contract: what pip and a colleague's machine depend on."""
import re


def _names(requirements):
    return {re.split(r"[\s<>=!~;\[(]", r.strip(), maxsplit=1)[0].lower().replace("_", "-") for r in requirements}


def test_build_system_declared(pyproject):
    build = pyproject.get("build-system", {})
    assert build.get("requires"), "[build-system] requires is missing: pip cannot know which backend to fetch"
    assert build.get("build-backend"), "[build-system] build-backend is missing"


def test_project_metadata(pyproject):
    project = pyproject.get("project", {})
    assert project.get("name") == "pumpwatch"
    assert project.get("version") or "version" in project.get("dynamic", []), "version must be static or dynamic"
    assert project.get("requires-python"), "declare requires-python so an old interpreter fails at install time"


def test_runtime_dependencies_declared(pyproject):
    declared = _names(pyproject.get("project", {}).get("dependencies", []))
    for needed in ("numpy", "pandas", "scikit-learn"):
        assert needed in declared, f"{needed} is imported by the package but not declared in [project] dependencies"


def test_src_layout(target, src):
    assert not (target / "pumpwatch" / "__init__.py").exists(), (
        "found a top-level pumpwatch/ package: with a flat layout the code is importable "
        "from the project root without being installed, which hides packaging mistakes"
    )


def test_no_import_path_hacks(src):
    offenders = [p.name for p in src.rglob("*.py") if re.search(r"sys\.path\.(insert|append)", p.read_text())]
    assert not offenders, f"sys.path manipulation in {offenders}: the installed package must not need it"


def test_entry_point_resolves_to_a_callable(src, entry_point, pkg):
    import importlib

    module, func = entry_point
    obj = getattr(importlib.import_module(module), func, None)
    assert callable(obj), f"[project.scripts] points at {module}:{func}, which is not a callable"

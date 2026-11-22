"""A small static reader for Dockerfiles and .dockerignore files, used by the w6d1 checks.

Why static: the checks must run on machines without a Docker daemon (CI, many laptops). Nothing
here builds an image. What it can establish: the instructions say what the contract requires, and
the files the image needs are actually in the build context. What it cannot: that the build
succeeds or the container starts. The optional live test (WB_DOCKER=1) covers that.

Pieces:
* ``parse_dockerfile`` - instructions with line continuations, comments, flags, exec/shell form,
  stages and global-ARG substitution in FROM. Heredocs are not supported (not needed here).
* ``DockerIgnore`` - a port of moby/patternmatcher's ``MatchesOrParentMatches`` with the
  ``ignorefile.ReadAll`` preprocessing: patterns are anchored at the context root, ``**`` matches
  any number of directories, a matching parent directory excludes everything below it, ``!``
  re-includes, the last matching pattern wins.
* ``image_path_to_context`` - follows WORKDIR and COPY in one stage to answer "which file of the
  build context ends up at this path in the image?".
"""
from __future__ import annotations

import json
import posixpath
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path


# --------------------------------------------------------------------------- Dockerfile parsing

@dataclass
class Instruction:
    name: str                  # upper case, e.g. "COPY"
    raw: str                   # arguments as written (continuations joined), flags included
    lineno: int                # first line, 1-based
    stage: int                 # index of the FROM this belongs to (-1 before the first FROM)
    flags: dict = field(default_factory=dict)   # --from=builder -> {"from": "builder"}
    args: str = ""             # raw arguments with the leading --flags removed

    @property
    def exec_form(self) -> list[str] | None:
        """The JSON array of an exec-form instruction, else None (shell form)."""
        text = self.args.strip()
        if not text.startswith("["):
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, list) and all(isinstance(v, str) for v in value) else None


@dataclass
class Stage:
    index: int
    image: str                 # after ARG substitution, e.g. "python:3.12-slim@sha256:..."
    name: str | None           # the "AS name", lower case
    instructions: list[Instruction]


@dataclass
class Dockerfile:
    instructions: list[Instruction]
    stages: list[Stage]
    global_args: dict

    def stage_named(self, name: str) -> Stage | None:
        return next((s for s in self.stages if s.name == name.lower()), None)

    @property
    def final(self) -> Stage:
        if not self.stages:
            raise ValueError("the Dockerfile has no FROM instruction")
        return self.stages[-1]


_FLAG = re.compile(r"^--([A-Za-z-]+)(?:=(\S*))?\s+")


def _split_flags(text: str) -> tuple[dict, str]:
    flags = {}
    rest = text.lstrip()
    while True:
        match = _FLAG.match(rest)
        if not match:
            return flags, rest
        flags[match.group(1).lower()] = match.group(2) if match.group(2) is not None else True
        rest = rest[match.end():]


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Join backslash continuations; drop comments and blank lines. Returns (first line no, text)."""
    out, buffer, start = [], [], None
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not buffer and (not stripped or stripped.startswith("#")):
            continue
        if buffer and stripped.startswith("#"):          # comment lines inside a continuation are skipped
            continue
        if start is None:
            start = number
        if stripped.endswith("\\"):
            buffer.append(stripped[:-1])
            continue
        buffer.append(stripped)
        out.append((start, " ".join(part.strip() for part in buffer if part.strip())))
        buffer, start = [], None
    if buffer:
        out.append((start, " ".join(buffer)))
    return out


def _substitute(text: str, variables: dict) -> str:
    def repl(match):
        name = match.group(1) or match.group(2)
        return variables.get(name, "")
    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", repl, text)


def parse_dockerfile(text: str) -> Dockerfile:
    instructions, stages, global_args = [], [], {}
    stage_index = -1
    for lineno, line in _logical_lines(text):
        name, _, rest = line.partition(" ")
        name = name.upper()
        flags, args = _split_flags(rest)
        if name == "FROM":
            stage_index += 1
        ins = Instruction(name=name, raw=rest.strip(), lineno=lineno, stage=stage_index, flags=flags, args=args)
        instructions.append(ins)
        if name == "ARG" and stage_index == -1:
            key, eq, value = args.strip().partition("=")
            global_args[key.strip()] = value.strip().strip('"').strip("'") if eq else ""
        if name == "FROM":
            words = _substitute(args, global_args).split()
            image = words[0] if words else ""
            alias = words[2].lower() if len(words) >= 3 and words[1].upper() == "AS" else None
            stages.append(Stage(index=stage_index, image=image, name=alias, instructions=[ins]))
        elif stage_index >= 0:
            stages[stage_index].instructions.append(ins)
    return Dockerfile(instructions=instructions, stages=stages, global_args=global_args)


def load_dockerfile(path: str | Path) -> Dockerfile:
    return parse_dockerfile(Path(path).read_text())


def parse_env(ins: Instruction) -> dict:
    """ENV key=value [key=value ...] (or the legacy ENV key value)."""
    text = ins.args.strip()
    if not text:
        return {}
    try:
        words = shlex.split(text)
    except ValueError:
        words = text.split()
    if "=" not in words[0]:
        return {words[0]: " ".join(words[1:])}
    out = {}
    for word in words:
        key, _, value = word.partition("=")
        out[key] = value
    return out


def stage_env(stage: Stage) -> dict:
    """ENV values in effect at the end of a stage (later ENV wins; $VAR references expanded)."""
    env: dict = {}
    for ins in stage.instructions:
        if ins.name == "ENV":
            for key, value in parse_env(ins).items():
                env[key] = _substitute(value, env)
    return env


def effective_command(stage: Stage) -> tuple[list[str] | None, list[Instruction]]:
    """The command the container runs (ENTRYPOINT + CMD, last of each), and the instructions used.

    Returns (argv, [instructions]) where argv is None if any part is in shell form.
    For a shell-form part the returned list still contains the instruction.
    """
    entry = next((i for i in reversed(stage.instructions) if i.name == "ENTRYPOINT"), None)
    cmd = next((i for i in reversed(stage.instructions) if i.name == "CMD"), None)
    used = [i for i in (entry, cmd) if i is not None]
    argv: list[str] = []
    for part in used:
        form = part.exec_form
        if form is None:
            return None, used
        argv.extend(form)
    return argv, used


def option_value(argv: list[str], option: str) -> str | None:
    """Value of ``--host 0.0.0.0`` or ``--host=0.0.0.0`` in an argv list."""
    for i, word in enumerate(argv):
        if word == option and i + 1 < len(argv):
            return argv[i + 1]
        if word.startswith(option + "="):
            return word.split("=", 1)[1]
    return None


# --------------------------------------------------------------------------- .dockerignore

class DockerIgnore:
    """Exclusion rules of a .dockerignore file, with Docker's semantics (see the module docstring)."""

    def __init__(self, text: str = ""):
        self.patterns: list[tuple[bool, str, str, re.Pattern | None]] = []
        for line in text.splitlines():
            if line.startswith("#"):
                continue
            pattern = line.strip()
            if not pattern:
                continue
            invert = pattern.startswith("!")
            if invert:
                pattern = pattern[1:].strip()
            if not pattern:
                continue
            pattern = posixpath.normpath(pattern)
            if len(pattern) > 1 and pattern.startswith("/"):
                pattern = pattern[1:]
            kind, regex = self._compile(pattern)
            self.patterns.append((invert, pattern, kind, regex))

    @classmethod
    def from_file(cls, path: str | Path) -> "DockerIgnore":
        path = Path(path)
        return cls(path.read_text() if path.is_file() else "")

    @staticmethod
    def _compile(pattern: str) -> tuple[str, re.Pattern | None]:
        """Translate one pattern exactly as patternmatcher's Pattern.compile does."""
        kind, regex, pos, step = "exact", "^", 0, 0
        escape = set(".+()|{}$")
        n = len(pattern)
        while pos < n:
            ch = pattern[pos]
            pos += 1
            if ch == "*":
                if pos < n and pattern[pos] == "*":            # some flavour of "**"
                    pos += 1
                    if pos < n and pattern[pos] == "/":        # treat "**/" as "**"
                        pos += 1
                    if pos >= n:                               # "**" at the end
                        if kind == "exact":
                            kind = "prefix"
                        else:
                            regex += ".*"
                            kind = "regex"
                    else:
                        regex += "(.*/)?"
                        kind = "regex"
                    if step == 0:
                        kind = "suffix"
                else:
                    regex += "[^/]*"
                    kind = "regex"
            elif ch == "?":
                regex += "[^/]"
                kind = "regex"
            elif ch in escape:
                regex += "\\" + ch
            elif ch == "\\":
                if pos < n:
                    regex += "\\" + pattern[pos]
                    pos += 1
                    kind = "regex"
                else:
                    regex += "\\\\"
            elif ch in "[]":
                regex += ch
                kind = "regex"
            else:
                regex += ch
            step += 1
        if kind == "regex":
            return kind, re.compile(regex + "$")
        return kind, None

    @staticmethod
    def _match_one(pattern: str, kind: str, regex: re.Pattern | None, path: str) -> bool:
        if kind == "exact":
            return path == pattern
        if kind == "prefix":
            return path.startswith(pattern[:-2])
        if kind == "suffix":
            suffix = pattern[2:]
            return path.endswith(suffix) or (suffix.startswith("/") and path == suffix[1:])
        return bool(regex.match(path))

    def excluded(self, path: str) -> bool:
        """True if the context-relative ``path`` (slash separated) is excluded from the context."""
        path = posixpath.normpath(path.strip("/"))
        parents = path.split("/")[:-1]
        matched = False
        for invert, pattern, kind, regex in self.patterns:
            if invert != matched:                      # same skip rule as patternmatcher
                continue
            hit = self._match_one(pattern, kind, regex, path)
            if not hit and parents:
                for depth in range(1, len(parents) + 1):
                    if self._match_one(pattern, kind, regex, "/".join(parents[:depth])):
                        hit = True
                        break
            if hit:
                matched = not invert
        return matched


# --------------------------------------------------------------------------- image layout

def _copy_sources_dest(ins: Instruction) -> tuple[list[str], str] | None:
    form = ins.exec_form
    words = form if form is not None else shlex.split(ins.args)
    if len(words) < 2:
        return None
    return words[:-1], words[-1]


def image_path_to_context(stage: Stage, image_path: str, context: Path,
                          ignore: DockerIgnore | None = None) -> Path | None:
    """Context file or directory that a COPY in ``stage`` places at ``image_path``, or None.

    Follows WORKDIR (relative WORKDIRs and COPY destinations are resolved against it). Only COPY
    from the build context counts (``COPY --from`` copies from another stage or image). Later
    COPYs win. A path excluded by .dockerignore is not in the context, so it resolves to None.
    """
    image_path = posixpath.normpath(image_path)
    workdir = "/"
    result = None
    for ins in stage.instructions:
        if ins.name == "WORKDIR":
            target = ins.args.strip()
            workdir = posixpath.normpath(posixpath.join(workdir, target))
        if ins.name not in ("COPY", "ADD") or "from" in ins.flags:
            continue
        parsed = _copy_sources_dest(ins)
        if parsed is None:
            continue
        sources, dest = parsed
        dest_is_dir = dest.endswith("/") or dest in (".", "./") or len(sources) > 1
        dest_abs = posixpath.normpath(posixpath.join(workdir, dest))
        for src in sources:
            src_rel = posixpath.normpath(src.lstrip("/"))
            src_path = context / src_rel if src_rel != "." else context
            if src_path.is_dir():
                base = dest_abs                       # directory: its CONTENTS go into dest
                if image_path == base or image_path.startswith(base.rstrip("/") + "/"):
                    rel = posixpath.relpath(image_path, base)
                    candidate = src_path / rel if rel != "." else src_path
                    rel_ctx = posixpath.normpath(posixpath.join(src_rel, rel)) if rel != "." else src_rel
                    if candidate.exists() and not (ignore and rel_ctx != "." and ignore.excluded(rel_ctx)):
                        result = candidate
            elif src_path.is_file():
                target = posixpath.join(dest_abs, posixpath.basename(src_rel)) if dest_is_dir else dest_abs
                if image_path == target and not (ignore and ignore.excluded(src_rel)):
                    result = src_path
    return result


def context_files(context: Path) -> list[str]:
    """All files under ``context`` as slash-separated relative paths."""
    return sorted(p.relative_to(context).as_posix() for p in context.rglob("*") if p.is_file())

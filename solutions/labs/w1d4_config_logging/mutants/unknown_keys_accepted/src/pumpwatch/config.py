"""Typed, validated run configuration.

Precedence (lowest to highest): dataclass defaults < TOML file < ``--set`` overrides.
Everything that can vary between runs lives here; nothing else in the package
reads files or the command line to decide *what* to compute.
"""
from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(ValueError):
    """A configuration problem the user can fix. The message names the dotted key."""


@dataclass(frozen=True)
class DataConfig:
    path: str
    fs: float = 256.0


@dataclass(frozen=True)
class SplitConfig:
    test_fraction: float = 0.3
    seed: int = 7


@dataclass(frozen=True)
class ModelConfig:
    C: float = 1.0


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True)
class Config:
    data: DataConfig
    split: SplitConfig = field(default_factory=SplitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Plain nested dict, suitable for ``json.dump`` (the run snapshot)."""
        return dataclasses.asdict(self)


_SECTIONS = {"data": DataConfig, "split": SplitConfig, "model": ModelConfig, "logging": LoggingConfig}


def parse_override(text: str) -> tuple[str, str, Any]:
    """``"split.seed=11"`` -> ``("split", "seed", 11)``.

    The value is parsed as a TOML value so that types match the file
    (``11`` is an int, ``0.2`` a float, ``"x"`` a string); anything that is not
    valid TOML is kept as a plain string, so ``data.path=some/file.csv`` works
    without shell-quoting gymnastics.
    """
    key, sep, raw = text.partition("=")
    section, dot, name = key.strip().partition(".")
    if not sep or not dot or not section or not name:
        raise ConfigError(f"override {text!r} must look like section.key=value")
    try:
        value = tomllib.loads(f"v = {raw}")["v"]
    except tomllib.TOMLDecodeError:
        value = raw.strip()
    return section, name, value


def _coerce(dotted: str, value: Any, expected: type) -> Any:
    """Check ``value`` against the annotated field type; never guess silently."""
    if expected is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{dotted} must be a number, got {value!r}")
        return float(value)
    if expected is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{dotted} must be an integer, got {value!r}")
        return value
    if expected is str:
        if not isinstance(value, str):
            raise ConfigError(f"{dotted} must be a string, got {value!r}")
        return value
    raise AssertionError(f"unsupported field type for {dotted}: {expected}")  # pragma: no cover


def _build_section(name: str, cls: type, values: dict[str, Any]) -> Any:
    fields = {f.name: f for f in dataclasses.fields(cls)}
    unknown = sorted(set(values) - set(fields))
    values = {k: v for k, v in values.items() if k in fields}  # quietly drop anything unrecognised
    kwargs = {}
    for key, value in values.items():
        expected = {"float": float, "int": int, "str": str}[fields[key].type]
        kwargs[key] = _coerce(f"{name}.{key}", value, expected)
    try:
        return cls(**kwargs)
    except TypeError:
        missing = [k for k, f in fields.items()
                   if k not in kwargs and f.default is dataclasses.MISSING]
        raise ConfigError(f"missing required configuration key: {name}.{missing[0]}") from None


def _validate(cfg: Config) -> None:
    if cfg.data.fs <= 0:
        raise ConfigError(f"data.fs must be > 0, got {cfg.data.fs}")
    if not 0.0 < cfg.split.test_fraction < 1.0:
        raise ConfigError(f"split.test_fraction must be in (0, 1), got {cfg.split.test_fraction}")
    if not 0 <= cfg.split.seed <= 2**32 - 1:
        raise ConfigError(f"split.seed must be in [0, 2**32 - 1], got {cfg.split.seed}")
    if cfg.model.C <= 0:
        raise ConfigError(f"model.C must be > 0, got {cfg.model.C}")
    if cfg.logging.level not in LOG_LEVELS:
        raise ConfigError(f"logging.level must be one of {LOG_LEVELS}, got {cfg.logging.level!r}")


def load_config(path: str | Path, overrides: Sequence[str] | None = None) -> Config:
    """Load ``path`` (TOML), apply ``section.key=value`` overrides, validate, freeze."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        with path.open("rb") as fh:  # tomllib requires a binary file object
            raw = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from None

    for section, value in raw.items():
        if section not in _SECTIONS:
            raise ConfigError(f"unknown configuration section: {section}")
        if not isinstance(value, dict):
            raise ConfigError(f"{section} must be a table ([{section}]), got {value!r}")
    merged = {section: dict(raw.get(section, {})) for section in _SECTIONS}

    for text in overrides or ():
        section, name, value = parse_override(text)
        if section not in _SECTIONS:
            raise ConfigError(f"unknown configuration key: {section}.{name}")
        merged[section][name] = value

    cfg = Config(**{name: _build_section(name, cls, merged[name]) for name, cls in _SECTIONS.items()})
    _validate(cfg)
    return cfg

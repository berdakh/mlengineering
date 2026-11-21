"""Logging is configured by the application entry point only, and never pollutes stdout."""
import json
import subprocess
import sys

HYGIENE = """
import importlib, logging, pkgutil
import pumpwatch
for mod in pkgutil.walk_packages(pumpwatch.__path__, "pumpwatch."):
    importlib.import_module(mod.name)
handlers = logging.getLogger().handlers
assert not handlers, f"importing the library configured the root logger: {handlers}"
"""


def test_importing_the_library_does_not_configure_logging(cli, workdir):
    proc = subprocess.run([sys.executable, "-c", HYGIENE], cwd=workdir, env=cli.env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert proc.stdout == "" and proc.stderr == "", "importing the library should produce no output"


def test_console_verbosity_follows_the_configured_level(cli, workdir, base_config):
    quiet = cli.train(workdir, base_config, "--set", 'logging.level="ERROR"')
    loud = cli.train(workdir, base_config, "--set", 'logging.level="DEBUG"')
    assert quiet.dir and quiet.proc.stderr.strip() == "", "at ERROR level a healthy run prints no diagnostics"
    assert loud.dir and loud.proc.stderr.strip() != "", "at DEBUG level diagnostics should appear on stderr"
    json.loads(loud.proc.stdout)                      # stdout stays machine-readable at any level


def test_log_file_keeps_detail_even_when_the_console_is_quiet(cli, workdir, base_config):
    quiet = cli.train(workdir, base_config, "--set", 'logging.level="ERROR"')
    text = "".join(p.read_text() for p in quiet.dir.glob("*.log"))
    assert len(text.splitlines()) >= 3, "the log file should record the run's steps regardless of console level"

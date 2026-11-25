"""pytest plugin loaded by the harness: unit tests must not open network connections."""
import socket


def _blocked(*args, **kwargs):
    raise RuntimeError("network access attempted inside the unit-test suite")


def pytest_configure(config):
    socket.socket.connect = _blocked
    socket.socket.connect_ex = _blocked

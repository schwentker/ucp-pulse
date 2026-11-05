"""Deny network for the entire pytest session, including child Python processes."""
import os
import socket
import sys
from pathlib import Path
import pytest


def blocked(*args, **kwargs):
    raise AssertionError("network disabled in tests")


socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
os.environ["PYTHONPATH"] = os.pathsep.join([str(Path(__file__).parent / "offline"), str(Path(__file__).parents[1] / "src"), os.environ.get("PYTHONPATH", "")])
os.environ["GIT_ALLOW_PROTOCOL"] = "file"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)

"""Shared fixtures.

tracker.py reads config.json when it is imported, so each test imports a fresh copy
from its own temporary folder. Nmap, SMTP, the vendor API and desktop notifications
are always mocked: the suite never scans a network or sends a message.
"""
import copy
import importlib.util
import itertools
import json
import shutil
import smtplib
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent

# Documentation-range IPs (RFC 5737) and obviously fake MAC addresses only.
FAKE_NMAP_OUTPUT = """Starting Nmap 7.95 ( https://nmap.org )
Nmap scan report for router.test (192.0.2.1)
Host is up (0.0010s latency).
MAC Address: AA:BB:CC:00:00:01 (Example Vendor)
Nmap scan report for 192.0.2.50
Host is up (0.0020s latency).
MAC Address: AA:BB:CC:00:00:02 (Unknown)
Nmap scan report for 192.0.2.60
Host is up (0.0030s latency).
MAC Address: AA:BB:CC:00:00:03
Nmap done: 256 IP addresses (3 hosts up) scanned in 2.00 seconds
"""

TEST_PASSWORD = "test-app-password-not-real"

_module_ids = itertools.count()


@pytest.fixture(autouse=True)
def block_external_calls(monkeypatch):
    """Fail loudly if a test reaches Nmap, SMTP or the vendor API without mocking it."""
    def blocked(name):
        def _raise(*args, **kwargs):
            raise AssertionError(f"Unmocked call to {name}")
        return _raise

    monkeypatch.setattr(subprocess, "check_output", blocked("nmap"))
    monkeypatch.setattr(smtplib, "SMTP", blocked("SMTP"))
    monkeypatch.setattr(requests, "get", blocked("vendor API"))


@pytest.fixture
def desktop_notifications(monkeypatch):
    """Replace plyer with a stub that records notifications instead of showing them."""
    calls = []
    stub = types.ModuleType("plyer")
    stub.notification = types.SimpleNamespace(notify=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setitem(sys.modules, "plyer", stub)
    return calls


@pytest.fixture
def example_config():
    with open(REPO_ROOT / "config.example.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def base_config(example_config):
    """A runnable config: example values, test IP range, every notification off."""
    config = copy.deepcopy(example_config)
    config.update(ip_range="192.0.2.0/24", enable_desktop_notifications=False, enable_email_notifications=False)
    return config


@pytest.fixture
def email_config(base_config):
    config = copy.deepcopy(base_config)
    config["enable_email_notifications"] = True
    config["smtp_settings"].update(enabled=True, app_password=TEST_PASSWORD)
    return config


@pytest.fixture
def load_tracker(tmp_path, desktop_notifications):
    """Copy tracker.py into a temporary folder with the given config and import it.

    Pass config=None to leave config.json missing, or a str to write raw file contents.
    """
    def _load(config=None, install_dir=None):
        folder = Path(install_dir or tmp_path / "app")
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / "tracker.py", folder / "tracker.py")
        if config is not None:
            text = config if isinstance(config, str) else json.dumps(config)
            (folder / "config.json").write_text(text, encoding="utf-8")
        name = f"tracker_under_test_{next(_module_ids)}"
        spec = importlib.util.spec_from_file_location(name, folder / "tracker.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return _load


@pytest.fixture
def fake_nmap(monkeypatch):
    """Make Nmap return canned output; returns the list of commands it was called with."""
    commands = []

    def _install(output=FAKE_NMAP_OUTPUT):
        def check_output(cmd, text=True):
            commands.append(cmd)
            return output
        monkeypatch.setattr(subprocess, "check_output", check_output)
        return commands

    return _install


@pytest.fixture
def fake_vendor_api(monkeypatch):
    """Answer vendor lookups locally; returns the list of (url, timeout) requested."""
    requested = []

    def get(url, timeout=None):
        requested.append((url, timeout))
        return mock.Mock(status_code=200, text="Example Corp\n")

    monkeypatch.setattr(requests, "get", get)
    return requested


@pytest.fixture
def fake_smtp(monkeypatch):
    """Replace smtplib.SMTP with a MagicMock usable as a context manager."""
    server = mock.MagicMock()
    server.__enter__.return_value = server
    factory = mock.Mock(return_value=server)
    monkeypatch.setattr(smtplib, "SMTP", factory)
    return types.SimpleNamespace(factory=factory, server=server)

import subprocess
from unittest import mock

import pytest
import requests

from conftest import FAKE_NMAP_OUTPUT


@pytest.fixture
def tracker(load_tracker, base_config):
    return load_tracker(config=base_config)


def test_runs_host_discovery_on_configured_range(tracker, fake_nmap):
    commands = fake_nmap()
    lines = tracker.run_nmap_scan()
    assert commands == [["nmap", "-sn", "192.0.2.0/24"]]
    assert lines == FAKE_NMAP_OUTPUT.splitlines()


def test_parses_multiple_devices(tracker, fake_vendor_api):
    devices = tracker.parse_nmap_output(FAKE_NMAP_OUTPUT.splitlines())
    assert devices == [
        {"Hostname": "router.test", "IP": "192.0.2.1", "MAC": "AA:BB:CC:00:00:01", "Manufacturer": "Example Vendor"},
        {"Hostname": "192.0.2.50", "IP": "192.0.2.50", "MAC": "AA:BB:CC:00:00:02", "Manufacturer": "Unknown"},
        {"Hostname": "192.0.2.60", "IP": "192.0.2.60", "MAC": "AA:BB:CC:00:00:03", "Manufacturer": "Example Corp"},
    ]


def test_parses_scan_with_no_devices(tracker):
    output = "Starting Nmap 7.95\nNmap done: 256 IP addresses (0 hosts up) scanned in 2.00 seconds\n"
    assert tracker.parse_nmap_output(output.splitlines()) == []


def test_host_without_mac_is_still_listed(tracker):
    output = "Nmap scan report for 192.0.2.10\nHost is up.\n"
    assert tracker.parse_nmap_output(output.splitlines()) == [{"Hostname": "192.0.2.10", "IP": "192.0.2.10"}]


def test_missing_nmap_gives_install_guidance(tracker, monkeypatch):
    monkeypatch.setattr(subprocess, "check_output", mock.Mock(side_effect=FileNotFoundError("nmap")))
    with pytest.raises(SystemExit) as exc:
        tracker.run_nmap_scan()
    assert "Nmap was not found" in str(exc.value.code)


def test_nmap_error_exit_is_reported(tracker, monkeypatch):
    error = subprocess.CalledProcessError(1, ["nmap", "-sn", "192.0.2.0/24"])
    monkeypatch.setattr(subprocess, "check_output", mock.Mock(side_effect=error))
    with pytest.raises(SystemExit) as exc:
        tracker.run_nmap_scan()
    assert "Nmap exited with an error (code 1)" in str(exc.value.code)


def test_vendor_lookup_sends_only_manufacturer_prefix(tracker, fake_vendor_api):
    assert tracker.get_vendor("AA:BB:CC:00:00:03") == "Example Corp"
    assert fake_vendor_api == [("https://api.macvendors.com/AA:BB:CC", 5)]


def test_vendor_lookup_unknown_on_non_200(tracker, monkeypatch):
    monkeypatch.setattr(requests, "get", mock.Mock(return_value=mock.Mock(status_code=404, text="Not Found")))
    assert tracker.get_vendor("AA:BB:CC:00:00:03") == "Unknown"


def test_vendor_lookup_failure_is_handled(tracker, monkeypatch):
    monkeypatch.setattr(requests, "get", mock.Mock(side_effect=requests.Timeout("timed out")))
    assert tracker.get_vendor("AA:BB:CC:00:00:03") == "Error"

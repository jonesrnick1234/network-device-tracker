import csv

import pytest

from conftest import FAKE_NMAP_OUTPUT

CSV_COLUMNS = ["Timestamp", "IP", "Hostname", "MAC", "Manufacturer", "Notes"]
NEW_HOST = "Nmap scan report for 192.0.2.70\nHost is up.\nMAC Address: AA:BB:CC:00:00:04 (Example Vendor)\n"


@pytest.fixture
def tracker(load_tracker, base_config, fake_nmap, fake_vendor_api):
    fake_nmap()
    return load_tracker(config=base_config)


def read_log(tracker):
    with open(tracker.output_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def test_first_scan_logs_every_device(tracker, capsys):
    tracker.main()
    columns, rows = read_log(tracker)
    assert columns == CSV_COLUMNS
    assert [(r["IP"], r["MAC"]) for r in rows] == [
        ("192.0.2.1", "AA:BB:CC:00:00:01"),
        ("192.0.2.50", "AA:BB:CC:00:00:02"),
        ("192.0.2.60", "AA:BB:CC:00:00:03"),
    ]
    assert all(r["Timestamp"] for r in rows)
    out = capsys.readouterr().out
    assert "Scanning 192.0.2.0/24..." in out
    assert "3 devices found" in out
    assert "3 new device(s) logged" in out


def test_second_identical_scan_reports_nothing_new(tracker, capsys):
    tracker.main()
    capsys.readouterr()
    tracker.main()
    assert "No new devices since last scan" in capsys.readouterr().out
    assert len(read_log(tracker)[1]) == 3


def test_only_newly_seen_device_is_logged(tracker, fake_nmap, capsys):
    tracker.main()
    capsys.readouterr()
    fake_nmap(FAKE_NMAP_OUTPUT + NEW_HOST)
    tracker.main()
    out = capsys.readouterr().out
    assert "1 new device(s) logged" in out
    assert "192.0.2.70 (AA:BB:CC:00:00:04) - Example Vendor" in out
    assert [r["IP"] for r in read_log(tracker)[1]][-1] == "192.0.2.70"


def test_log_is_written_beside_tracker_only(tracker, tmp_path):
    tracker.main()
    assert tracker.output_file.exists()
    assert list(tmp_path.rglob("*.csv")) == [tracker.output_file]

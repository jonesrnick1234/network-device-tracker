import copy
import io
import smtplib
import sys
import types

import pytest

from conftest import TEST_PASSWORD

SMS_GATEWAY = "1234567890@vtext.com"


@pytest.fixture
def run_scan(load_tracker, fake_nmap, fake_vendor_api, capsys):
    """Run one full scan with the given config and return (tracker, printed output)."""
    fake_nmap()

    def _run(config):
        tracker = load_tracker(config=config)
        tracker.main()
        return tracker, capsys.readouterr().out

    return _run


def test_no_notifications_when_disabled(run_scan, base_config, desktop_notifications, fake_smtp):
    run_scan(base_config)
    assert desktop_notifications == []
    fake_smtp.factory.assert_not_called()


def test_desktop_notification_when_enabled(run_scan, base_config, desktop_notifications):
    config = dict(base_config, enable_desktop_notifications=True)
    run_scan(config)
    assert len(desktop_notifications) == 1
    assert desktop_notifications[0]["title"] == "New Device Detected"
    assert "192.0.2.1 (AA:BB:CC:00:00:01) - Example Vendor" in desktop_notifications[0]["message"]


def test_desktop_notification_failure_does_not_stop_scan(run_scan, base_config, monkeypatch):
    def broken_notify(**kwargs):
        raise RuntimeError("no notification backend")

    monkeypatch.setitem(sys.modules, "plyer", types.SimpleNamespace(notification=types.SimpleNamespace(notify=broken_notify)))
    config = dict(base_config, enable_desktop_notifications=True)
    _, out = run_scan(config)
    assert "Desktop notification failed" in out
    assert "3 new device(s) logged" in out


def test_email_only(run_scan, email_config, fake_smtp):
    _, out = run_scan(email_config)
    smtp = email_config["smtp_settings"]
    fake_smtp.factory.assert_called_once_with(smtp["server"], smtp["port"], timeout=30)
    fake_smtp.server.starttls.assert_called_once()
    fake_smtp.server.login.assert_called_once_with(smtp["sender_email"], TEST_PASSWORD)
    sender, recipients, _ = fake_smtp.server.sendmail.call_args.args
    assert recipients == [smtp["receiver_email"]]
    assert "Email notification sent." in out


def test_email_and_sms(run_scan, email_config, fake_smtp):
    config = copy.deepcopy(email_config)
    config["smtp_settings"]["sms_gateway"] = SMS_GATEWAY
    _, out = run_scan(config)
    _, recipients, message = fake_smtp.server.sendmail.call_args.args
    assert recipients == [config["smtp_settings"]["receiver_email"], SMS_GATEWAY]
    assert "Subject: New Device(s) on Your Network" in message
    assert "Email and SMS notifications sent." in out


def test_email_requires_both_switches(run_scan, email_config, fake_smtp):
    config = copy.deepcopy(email_config)
    config["smtp_settings"]["enabled"] = False
    run_scan(config)
    fake_smtp.factory.assert_not_called()


def test_incomplete_smtp_settings_are_named_not_printed(run_scan, email_config, fake_smtp):
    config = copy.deepcopy(email_config)
    config["smtp_settings"]["server"] = ""
    _, out = run_scan(config)
    fake_smtp.factory.assert_not_called()
    assert "smtp_settings is missing server" in out
    assert TEST_PASSWORD not in out


@pytest.mark.parametrize("error", [
    smtplib.SMTPAuthenticationError(535, b"5.7.8 authentication failed"),
    ConnectionRefusedError("connection refused"),
])
def test_delivery_failure_is_reported_without_credentials(run_scan, email_config, fake_smtp, error):
    fake_smtp.server.login.side_effect = error
    _, out = run_scan(email_config)
    assert "Failed to send email/SMS" in out
    assert "3 new device(s) logged" in out
    assert TEST_PASSWORD not in out


def test_redirected_output_with_legacy_windows_encoding(load_tracker, base_config, fake_nmap, fake_vendor_api, monkeypatch):
    fake_nmap()
    tracker = load_tracker(config=base_config)
    buffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buffer, encoding="cp1252"))
    tracker.main()
    sys.stdout.flush()
    output = buffer.getvalue().decode("cp1252")
    assert "3 devices found" in output
    assert "192.0.2.1 (AA:BB:CC:00:00:01)" in output

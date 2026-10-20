import copy
import json

import pytest

from conftest import REPO_ROOT

REQUIRED_TOP_LEVEL = {"ip_range", "output_file", "enable_desktop_notifications", "enable_email_notifications", "smtp_settings"}
REQUIRED_SMTP = {"enabled", "server", "port", "sender_email", "receiver_email", "sms_gateway", "app_password"}


def test_example_config_has_all_settings(example_config):
    assert REQUIRED_TOP_LEVEL <= set(example_config)
    assert REQUIRED_SMTP <= set(example_config["smtp_settings"])


def test_example_config_is_safe_to_publish(example_config):
    smtp = example_config["smtp_settings"]
    assert example_config["enable_email_notifications"] is False
    assert smtp["enabled"] is False
    assert smtp["sender_email"].endswith("@example.com")
    assert smtp["receiver_email"].endswith("@example.com")
    assert smtp["app_password"].startswith("your_")
    assert smtp["sms_gateway"] == ""


def test_missing_config_explains_how_to_create_it(load_tracker):
    with pytest.raises(SystemExit) as exc:
        load_tracker(config=None)
    message = str(exc.value.code)
    assert "config.json not found" in message
    assert "Copy config.example.json to config.json" in message


def test_invalid_json_is_reported_without_echoing_contents(load_tracker):
    raw = '{"ip_range": "192.0.2.0/24", "app_password": "secret-should-not-appear",, }'
    with pytest.raises(SystemExit) as exc:
        load_tracker(config=raw)
    message = str(exc.value.code)
    assert "not valid JSON" in message
    assert "secret-should-not-appear" not in message


@pytest.mark.parametrize("key", ["ip_range", "output_file"])
def test_missing_required_setting_is_named(load_tracker, base_config, key):
    config = copy.deepcopy(base_config)
    del config[key]
    with pytest.raises(SystemExit) as exc:
        load_tracker(config=config)
    assert key in str(exc.value.code)


def test_notification_settings_default_to_off(load_tracker):
    tracker = load_tracker(config={"ip_range": "192.0.2.0/24", "output_file": "devices.csv"})
    assert tracker.enable_desktop_notifications is False
    assert tracker.enable_email_notifications is False
    assert tracker.smtp_config == {}


def test_config_and_output_are_relative_to_tracker_not_cwd(load_tracker, base_config, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    install_dir = tmp_path / "install"
    tracker = load_tracker(config=base_config, install_dir=install_dir)
    assert tracker.CONFIG_PATH == install_dir / "config.json"
    assert tracker.output_file == install_dir / base_config["output_file"]


def test_repository_does_not_track_a_real_config():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "config.json" in gitignore
    json.loads((REPO_ROOT / "config.example.json").read_text(encoding="utf-8"))

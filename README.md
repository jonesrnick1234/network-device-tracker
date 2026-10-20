# Network Device Tracker

A Python and Nmap tool that monitors a local network for new devices, logs discoveries to CSV, and can optionally send desktop, email, or SMS alerts.

A personal Python and network-monitoring project by Nicolas Jones.

## Why it exists

Home and small-office networks rarely offer an easy way to notice when an unfamiliar device joins. This tool runs a lightweight Nmap discovery scan, compares the results with devices it has already seen, and tells you when something new appears.

## What it does

- Runs an Nmap host-discovery scan (`nmap -sn`) of the IP range you configure
- Records each device's IP address, hostname, MAC address, and manufacturer
- Detects devices whose IP/MAC combination has not been logged before
- Appends newly seen devices to a local CSV file
- Optionally shows a desktop notification
- Optionally sends an email alert over SMTP, and an SMS alert through a carrier email-to-SMS gateway

## Requirements

- Python 3.8 or newer
- [Nmap](https://nmap.org/download.html) installed and available on your `PATH`
- Python packages listed in `requirements.txt` (`requests`, `plyer`)
- Developed for Windows: desktop notifications and the scheduling steps below assume Windows

## Installation

```powershell
git clone https://github.com/jonesrnick1234/network-device-tracker.git
cd network-device-tracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## Configuration

1. Copy the example configuration:

   ```powershell
   Copy-Item config.example.json config.json
   ```

   On macOS or Linux: `cp config.example.json config.json`

2. Edit `config.json` and set `ip_range` to your own network, for example `192.168.1.0/24`.
3. Leave email and SMS alerts disabled unless you need them. No credentials are required when they are off.
4. Never commit `config.json`.

| Setting | Purpose |
|---|---|
| `ip_range` | Network range passed to `nmap -sn` |
| `output_file` | CSV log file, relative to the project folder |
| `enable_desktop_notifications` | `true` to show a desktop notification for new devices |
| `enable_email_notifications` | `true` to send email/SMS alerts (also requires `smtp_settings.enabled`) |
| `smtp_settings` | SMTP server, port, sender and receiver addresses, optional `sms_gateway`, and `app_password` |

> **Security note:** `config.json` can contain an email app password and a phone-based SMS address. It is listed in `.gitignore` so it stays on your machine. Never commit credentials, and use an app-specific password rather than your main account password.

### Email and SMS alerts (optional)

1. In `config.json`, set `enable_email_notifications` and `smtp_settings.enabled` to `true`.
2. Fill in `server`, `port`, `sender_email`, `receiver_email`, and `app_password`.
3. Create an app password with your email provider:
   - **Yahoo Mail:** turn on 2-step verification at [Yahoo account security](https://login.yahoo.com/account/security), then generate an app password.
   - **Gmail:** turn on 2-Step Verification at [Google account security](https://myaccount.google.com/security), then create one under [App passwords](https://myaccount.google.com/apppasswords).
4. For SMS, set `sms_gateway` to your carrier's email-to-SMS address. Replace `1234567890` with your 10-digit number:

   | Carrier | Gateway format |
   |---|---|
   | Verizon | `1234567890@vtext.com` |
   | T-Mobile | `1234567890@tmomail.net` |
   | US Cellular | `1234567890@email.uscc.net` |

   Carrier support for email-to-SMS gateways varies, and some carriers have discontinued them. Check with your carrier if texts do not arrive.

Example `smtp_settings` (placeholder values):

```json
"smtp_settings": {
  "enabled": true,
  "server": "smtp.mail.yahoo.com",
  "port": 587,
  "sender_email": "you@example.com",
  "receiver_email": "you@example.com",
  "sms_gateway": "1234567890@vtext.com",
  "app_password": "your_app_password_here"
}
```

## Usage

```powershell
python tracker.py
```

Run from an elevated terminal (Administrator on Windows, `sudo` on macOS/Linux) so Nmap can report MAC addresses and manufacturers.

Example output (example values):

```
Scanning 192.168.1.0/24...

✅ Scan complete. 7 devices found.
🆕 1 new device(s) logged:
- 192.168.1.50 (AA:BB:CC:00:00:01) - Example Vendor
```

### Run automatically (Windows Task Scheduler)

1. Open **Task Scheduler** and choose **Create Task**.
2. **General:** name it `Network Device Tracker` and check **Run with highest privileges**.
3. **Triggers:** add a daily trigger and, optionally, an **At log on** trigger.
4. **Actions:** start a program.
   - **Program/script:** `python` (or the full path to `.venv\Scripts\python.exe`)
   - **Add arguments:** `tracker.py`
   - **Start in:** the project folder
5. Save, then right-click the task and choose **Run** to test it.

The computer must be on and connected to the network for scheduled scans to run.

## Output

- New devices are appended to `network_devices_log.csv` (or the `output_file` you configure) in the project folder.
- Columns: `Timestamp`, `IP`, `Hostname`, `MAC`, `Manufacturer`, `Notes`.
- The log describes devices on your network, so `*.csv` files are ignored by Git.
- Delete the CSV to reset the list of known devices.

When Nmap does not report a manufacturer, the tool looks up the MAC address prefix (first three octets only) at [api.macvendors.com](https://macvendors.com/).

## Testing

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

The tests mock Nmap, email/SMS delivery, desktop notifications, and the vendor lookup, so they never scan a network or send a message. Each test runs in a temporary folder and leaves no log or config files behind.

## Limitations

- Only devices that respond to Nmap host discovery from the scanning machine are found; firewalled or sleeping devices may be missed.
- MAC addresses and manufacturers are only available for devices on the same local subnet, and usually require elevated privileges.
- A device counts as new when its IP/MAC pair has not been logged before, so a known device that gets a new IP address or uses a randomized MAC address (common on phones) is reported again.
- Manufacturer lookups need internet access and may return `Unknown`; randomized MAC addresses have no registered manufacturer.
- Results vary with network configuration, and each run performs a single scan.
- This is an awareness tool for networks you own or are authorized to monitor. It is not an intrusion detection system or a replacement for enterprise security controls.

## License

Free to use and share.

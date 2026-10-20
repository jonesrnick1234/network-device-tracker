import subprocess
import csv
import requests
import datetime
import os
import smtplib
import json
import sys
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from plyer import notification

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    """Load config.json from the script folder, exiting with a clear message if it is missing or invalid."""
    if not CONFIG_PATH.exists():
        sys.exit(
            f"config.json not found in {BASE_DIR}.\n"
            "Copy config.example.json to config.json, then set your ip_range.\n"
            "Email/SMS settings are only needed if you enable those notifications."
        )
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            loaded = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"config.json is not valid JSON (line {e.lineno}, column {e.colno}).")
    missing = [key for key in ("ip_range", "output_file") if not loaded.get(key)]
    if missing:
        sys.exit(f"config.json is missing required setting(s): {', '.join(missing)}. See config.example.json.")
    return loaded


# Load config
config = load_config()

ip_range = config["ip_range"]
output_file = Path(config["output_file"])
if not output_file.is_absolute():
    output_file = BASE_DIR / output_file
mac_vendor_url = "https://api.macvendors.com/"

smtp_config = config.get("smtp_settings", {})
enable_desktop_notifications = config.get("enable_desktop_notifications", False)
enable_email_notifications = config.get("enable_email_notifications", False)

def get_vendor(mac):
    # Only the manufacturer prefix (first three octets) is sent to the lookup service.
    try:
        response = requests.get(mac_vendor_url + mac[:8], timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return "Unknown"
    except requests.RequestException:
        return "Error"

def run_nmap_scan():
    try:
        result = subprocess.check_output(["nmap", "-sn", ip_range], text=True)
    except FileNotFoundError:
        sys.exit("Nmap was not found. Install it from https://nmap.org/download.html and make sure it is on your PATH.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Nmap exited with an error (code {e.returncode}). Check the ip_range setting in config.json.")
    return result.splitlines()

def parse_nmap_output(lines):
    devices = []
    current = {}
    for line in lines:
        line = line.strip()
        if line.startswith("Nmap scan report for"):
            if current:
                devices.append(current)
                current = {}
            parts = line.split()
            current["Hostname"] = parts[4] if len(parts) > 4 else "Unknown"
            current["IP"] = parts[-1].replace("(", "").replace(")", "")
        elif line.startswith("MAC Address:"):
            parts = line.split(" ", 3)
            current["MAC"] = parts[2]
            current["Manufacturer"] = parts[3].strip("()") if len(parts) > 3 else get_vendor(parts[2])
    if current:
        devices.append(current)
    return devices

def load_existing_log():
    if not os.path.exists(output_file):
        return set()
    with open(output_file, newline='') as f:
        reader = csv.DictReader(f)
        return {(row["IP"], row["MAC"]) for row in reader}

def send_notifications(new_devices):
    required = ("server", "port", "sender_email", "receiver_email", "app_password")
    missing = [key for key in required if not smtp_config.get(key)]
    if missing:
        print(f"❌ Email/SMS not sent: smtp_settings is missing {', '.join(missing)}.")
        return

    subject = "New Device(s) on Your Network"
    body_lines = []
    for d in new_devices:
        body_lines.append(f"{d['IP']} ({d.get('MAC', 'Unknown')}) - {d.get('Manufacturer', 'Unknown')}")
    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = smtp_config["sender_email"]
    msg["To"] = smtp_config["receiver_email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    recipients = [smtp_config["receiver_email"]]
    if smtp_config.get("sms_gateway"):
        recipients.append(smtp_config["sms_gateway"])

    try:
        with smtplib.SMTP(smtp_config["server"], smtp_config["port"], timeout=30) as server:
            server.starttls()
            server.login(smtp_config["sender_email"], smtp_config["app_password"])
            server.sendmail(smtp_config["sender_email"], recipients, msg.as_string())
        print("📤 Email and SMS notifications sent." if len(recipients) > 1 else "📤 Email notification sent.")
    except (smtplib.SMTPException, OSError) as e:
        print(f"❌ Failed to send email/SMS: {e}")

def save_new_devices(devices, existing_devices):
    new_entries = []
    with open(output_file, 'a', newline='') as f:
        fieldnames = ["Timestamp", "IP", "Hostname", "MAC", "Manufacturer", "Notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if os.stat(output_file).st_size == 0:
            writer.writeheader()
        for device in devices:
            ip = device.get("IP", "Unknown")
            mac = device.get("MAC", "Unknown")
            manufacturer = device.get("Manufacturer", "Unknown")
            hostname = device.get("Hostname", "Unknown")
            notes = ""
            key = (ip, mac)
            if key not in existing_devices:
                writer.writerow({
                    "Timestamp": datetime.datetime.now().isoformat(),
                    "IP": ip,
                    "Hostname": hostname,
                    "MAC": mac,
                    "Manufacturer": manufacturer,
                    "Notes": notes
                })
                new_entries.append(device)
    return new_entries

def notify_desktop(message):
    if enable_desktop_notifications:
        try:
            notification.notify(
                title="New Device Detected",
                message=message,
                timeout=8
            )
        except Exception as e:
            print(f"⚠️ Desktop notification failed: {e}")

def main():
    # Avoid crashing on emoji output when stdout is redirected with a legacy Windows encoding.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    print(f"Scanning {ip_range}...")
    lines = run_nmap_scan()
    devices = parse_nmap_output(lines)
    existing = load_existing_log()
    new_devices = save_new_devices(devices, existing)

    print(f"\n✅ Scan complete. {len(devices)} devices found.")
    if new_devices:
        print(f"🆕 {len(new_devices)} new device(s) logged:")
        msg_text = ""
        for d in new_devices:
            ip = d.get("IP", "Unknown")
            mac = d.get("MAC", "Unknown")
            vendor = d.get("Manufacturer", "Unknown")
            print(f"- {ip} ({mac}) - {vendor}")
            msg_text += f"{ip} ({mac}) - {vendor}\n"

        notify_desktop(msg_text.strip())
        if enable_email_notifications and smtp_config.get("enabled"):
            send_notifications(new_devices)
    else:
        print("📋 No new devices since last scan.")

if __name__ == "__main__":
    main()

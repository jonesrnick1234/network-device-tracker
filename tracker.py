import subprocess
import csv
import requests
import datetime
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from plyer import notification

# Load config
with open("config.json") as f:
    config = json.load(f)

ip_range = config["ip_range"]
output_file = config["output_file"]
mac_vendor_url = "https://api.macvendors.com/"

smtp_config = config["smtp_settings"]
enable_desktop_notifications = config["enable_desktop_notifications"]
enable_email_notifications = config["enable_email_notifications"]

def get_vendor(mac):
    try:
        response = requests.get(mac_vendor_url + mac)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return "Unknown"
    except:
        return "Error"

def run_nmap_scan():
    result = subprocess.check_output(["nmap", "-sn", ip_range], text=True)
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

    try:
        server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
        server.starttls()
        server.login(smtp_config["sender_email"], smtp_config["app_password"])
        recipients = [smtp_config["receiver_email"]]
        if smtp_config["sms_gateway"]:
            recipients.append(smtp_config["sms_gateway"])
        server.sendmail(smtp_config["sender_email"], recipients, msg.as_string())
        server.quit()
        print("📤 Email and SMS notifications sent.")
    except Exception as e:
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
        if enable_email_notifications and smtp_config["enabled"]:
            send_notifications(new_devices)
    else:
        print("📋 No new devices since last scan.")

if __name__ == "__main__":
    main()

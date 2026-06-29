# Network Device Tracker

A lightweight Python tool to monitor devices on your local network. It uses `nmap` to scan for active hosts, logs new devices to a CSV file, and can optionally send desktop, email, and SMS alerts.

## Features

- Scans your local network for connected devices
- Logs new devices (IP, MAC, manufacturer) to a CSV file
- Optional email, SMS, and desktop notifications
- Configurable via `config.json`

## Requirements

- Python 3.7+
- [nmap](https://nmap.org/download.html) installed and in your system PATH
- Python packages (install via pip):

```bash
pip install -r requirements.txt
```

## Setup

1. Clone or download the repo.
2. Edit `config.json` with your IP range and preferences.
3. Run the script:

```bash
python tracker.py
```

4. (Optional) Schedule it via Windows Task Scheduler to run on startup or daily.

## Enabling Notifications

- **Desktop alerts:** Works out of the box on Windows.
- **Email/SMS:** Set `enable_email_notifications` to `true` and configure your SMTP settings in `config.json`.

> ⚠️ Use app-specific passwords if required by your email provider (e.g., Yahoo, Gmail).

## Example

```
Scanning 192.168.1.0/24...
✅ Scan complete. 7 devices found.
🆕 1 new device(s) logged:
- 192.168.1.94 (F6:82:09:FF:29:D7) - Unknown
📤 Email and SMS notifications sent.
```

## License

Free to use and share.

## 🔔 Enabling Notifications (Email & SMS)

You can configure the script to send **email and/or SMS alerts** when a new device joins your network.

### ✅ Step 1: Enable Email Notifications

In `config.json`, set:
```json
"enable_email_notifications": true,
"smtp_settings": {
  "enabled": true,
  ...
}
```

---

### ✉️ Step 2: Set Up Your Email Provider

#### 📧 **Yahoo Mail:**
1. Go to: [https://login.yahoo.com/account/security](https://login.yahoo.com/account/security)
2. Enable **2-step verification**
3. Click **“Generate app password”**
4. Choose "Other App" → Name it something like `Network Tracker`
5. Paste the generated password into:
```json
"app_password": "your_generated_app_password"
```

#### 📧 **Gmail:**
1. Go to: [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create a new password for "Mail" + "Other" app
5. Paste it into:
```json
"app_password": "your_generated_app_password"
```

---

### 📱 Step 3: Add Your Phone Number (Optional SMS Alerts)

Most carriers allow sending texts via email-to-SMS gateways.

| Carrier       | SMS Gateway Format              |
|---------------|---------------------------------|
| Verizon       | `1234567890@vtext.com`          |
| AT&T          | `1234567890@txt.att.net`        |
| T-Mobile      | `1234567890@tmomail.net`        |
| Sprint        | `1234567890@messaging.sprintpcs.com` |
| US Cellular   | `1234567890@email.uscc.net`     |

> Replace `1234567890` with your 10-digit phone number (no spaces or dashes)

In `config.json`:
```json
"sms_gateway": "5555555555@tmomail.net"
```

---

### ✅ Final Config Example (`config.json`)
```json
"enable_email_notifications": true,
"smtp_settings": {
  "enabled": true,
  "server": "smtp.mail.yahoo.com",
  "port": 587,
  "sender_email": "your_email@yahoo.com",
  "receiver_email": "your_email@yahoo.com",
  "sms_gateway": "5555555555@tmomail.net",
  "app_password": "your_yahoo_app_password"
}
```

## 🕒 Running Automatically (Optional: Task Scheduler)

To get alerts **without manually running the script**, you can use **Windows Task Scheduler** to:

- ✅ Run the script daily (e.g., every day at noon)
- ✅ Run it at system startup or user login

### ✅ Step-by-Step Setup (Windows)

1. Open **Task Scheduler** (`Win + S` → search “Task Scheduler”)
2. Click **Create Task** (not Basic Task)
3. In the **General** tab:
   - Name: `Network Device Tracker`
   - Check ✅ "Run with highest privileges"
4. In the **Triggers** tab:
   - Add new → Choose **Daily** at 12:00 PM
   - Add another trigger → **At log on**
5. In the **Actions** tab:
   - Action: Start a program
   - **Program/script:** `python`
   - **Add arguments:**  
     ```
     "C:\Path\To\tracker.py"
     ```
   - **Start in:**  
     ```
     C:\Path\To\Your\Project\Folder
     ```
6. Save and test by right-clicking the task → **Run**

---

### ⚠️ Important Notes
- Your computer **must be powered on and connected to your network** for the scan to run.
- If it’s asleep or shut down, no scan or alerts will occur.
- For best results, run on a desktop PC or a small home server that stays on.

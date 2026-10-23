import os
import sys
import time
import shutil
import sqlite3
import tempfile
import subprocess
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE_DIR = os.path.abspath("storage/bot_browser_profile")

def kill_zombie_bot_chrome():
    ps_cmd = "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | Where-Object { $_.CommandLine -like '*bot_browser_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1)

def check_is_google_authenticated() -> bool:
    cookies_path = os.path.join(PROFILE_DIR, "Default", "Network", "Cookies")
    if not os.path.exists(cookies_path):
        return False
    tmp_path = os.path.join(tempfile.gettempdir(), f"cookie_auth_chk_{int(time.time()*1000)}.db")
    try:
        shutil.copy2(cookies_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM cookies WHERE name IN ('SID', 'SSID', 'SAPISID') AND host_key LIKE '%google.com%' LIMIT 1")
        row = cur.fetchone()
        conn.close()
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return row is not None
    except PermissionError:
        return False
    except Exception:
        return False

def main():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    kill_zombie_bot_chrome()

    if check_is_google_authenticated():
        print("=" * 65)
        print("SUCCESS: The AI Bot is ALREADY authenticated with a Google Account!")
        print(f"Profile: {PROFILE_DIR}")
        print("=" * 65)
        return

    print("=" * 65)
    print("AUTHENTIC GOOGLE CHROME SIGN-IN LAUNCHER")
    print("=" * 65)
    print("Opening authentic Google Chrome WITHOUT automation hooks,")
    print("so Google will NOT show 'This browser or app may not be secure'.")
    print("")
    print("1. In the Chrome window that opens, enter your Google email & password.")
    print("2. Complete 2FA on your phone if prompted.")
    print("3. When you see your account or Google Meet, CLOSE the Chrome window.")
    print("=" * 65)

    cmd = [
        CHROME_PATH,
        f"--user-data-dir={PROFILE_DIR}",
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
        "https://accounts.google.com"
    ]
    subprocess.Popen(cmd)
    
    print("\nChrome window opened on your screen.")
    print("Please complete sign-in in Chrome, then CLOSE the Chrome window.")
    input("\nPress ENTER here once you have signed in and closed Chrome: ")

    time.sleep(2)
    if check_is_google_authenticated():
        print("\n" + "=" * 65)
        print("GOOGLE ACCOUNT AUTHENTICATION CONFIRMED!")
        print("Session tokens are permanently saved in storage/bot_browser_profile.")
        print("The AI Bot can now join Google Meet calls without any security blocks!")
        print("=" * 65)
    else:
        print("\n" + "!" * 65)
        print("Notice: No Google session cookies were detected.")
        print("Make sure you completed sign-in and closed the Chrome window.")
        print("!" * 65)

if __name__ == "__main__":
    main()

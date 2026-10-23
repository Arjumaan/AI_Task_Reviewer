import os
import shutil
import tempfile
import sqlite3

local_app_data = os.environ.get("LOCALAPPDATA", "")
user_cookies = os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default", "Network", "Cookies")
print("User default Chrome cookies path:", user_cookies)
print("Exists:", os.path.exists(user_cookies))
if os.path.exists(user_cookies):
    tmp = os.path.join(tempfile.gettempdir(), "user_check.db")
    try:
        shutil.copy2(user_cookies, tmp)
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM cookies WHERE name IN ('SID', 'SSID') AND host_key LIKE '%google.com%' LIMIT 1")
        row = cur.fetchone()
        print("User is ALREADY LOGGED IN to Google in daily Chrome:", row is not None)
        conn.close()
        os.remove(tmp)
    except Exception as e:
        print("Error:", e)

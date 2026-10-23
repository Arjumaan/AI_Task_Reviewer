import os, sqlite3, shutil, tempfile

user_chrome_cookies = os.path.expanduser(r'~\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies')
print('User Chrome cookies path:', user_chrome_cookies)
print('Exists:', os.path.exists(user_chrome_cookies))
if os.path.exists(user_chrome_cookies):
    tmp = os.path.join(tempfile.gettempdir(), 'user_cookie_chk.db')
    try:
        shutil.copy2(user_chrome_cookies, tmp)
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com%'")
        count = cur.fetchone()[0]
        print(f"Total Google cookies in user's default Chrome profile: {count}")
        cur.execute("SELECT name FROM cookies WHERE host_key LIKE '%google.com%' AND name IN ('SID', 'SSID')")
        names = [r[0] for r in cur.fetchall()]
        print(f"Authenticated session tokens found: {names}")
        conn.close()
        os.remove(tmp)
    except Exception as e:
        print(f"Error reading user Chrome cookies: {e}")

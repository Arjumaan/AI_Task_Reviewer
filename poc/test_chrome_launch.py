import subprocess, time

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
profile_dir = r"D:\My Projects\AI-Task_Reviewer\storage\bot_browser_profile"

cmd = [
    CHROME_PATH,
    f"--user-data-dir={profile_dir}",
    "--enable-logging=stderr",
    "--v=1",
    "https://accounts.google.com"
]

print("Executing:", cmd)
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(3)
poll = proc.poll()
print("Process Poll after 3s:", poll)
if poll is not None:
    stdout, stderr = proc.communicate()
    print("STDOUT:\n", stdout)
    print("STDERR:\n", stderr)
else:
    print("Chrome is running! PID:", proc.pid)

import subprocess

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--incognito",
    "https://meet.google.com/sbk-bcoj-veq"
]
subprocess.run(cmd)
print("Incognito opened")

import subprocess

ps_code = """
Get-CimInstance Win32_Process -Filter "name = 'chrome.exe'" | ForEach-Object {
    if ($_.CommandLine -like '*bot_browser_profile*') {
        Write-Host "FOUND BOT CHROME PID: $($_.ProcessId)"
        Write-Host "CommandLine: $($_.CommandLine)"
    }
}
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)

import sys
import subprocess


def windows_toast(title: str, message: str) -> None:
    """Cross-platform desktop notification. Silent no-op on failure."""
    try:
        if sys.platform == "win32":
            _win(title, message)
        elif sys.platform == "darwin":
            _mac(title, message)
        else:
            _linux(title, message)
    except Exception:
        pass


def _win(title: str, message: str) -> None:
    t = title.replace("'", "")
    m = message.replace("'", "")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$n=New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon=[System.Drawing.SystemIcons]::Application;"
        "$n.BalloonTipIcon='Info';"
        f"$n.BalloonTipTitle='{t}';"
        f"$n.BalloonTipText='{m}';"
        "$n.Visible=$true;"
        "$n.ShowBalloonTip(8000);"
        "Start-Sleep 9;$n.Dispose()"
    )
    subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive",
         "-Command", script],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _mac(title: str, message: str) -> None:
    t = title.replace('"', "").replace("'", "")
    m = message.replace('"', "").replace("'", "")
    subprocess.Popen(
        ["osascript", "-e", f'display notification "{m}" with title "{t}"'])


def _linux(title: str, message: str) -> None:
    subprocess.Popen(["notify-send", "--expire-time=8000", title, message])

import os
import sys
from pathlib import Path

APP_ID = "foklumi"
APP_NAME = "Foklumi"
LINUX_AUTOSTART = Path(
    os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
) / "autostart" / f"{APP_ID}.desktop"


def supported() -> bool:
    return sys.platform in ("linux", "win32", "darwin")


def is_enabled() -> bool:
    try:
        if sys.platform == "linux":
            return LINUX_AUTOSTART.exists()
        if sys.platform == "win32":
            import winreg
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_READ) as key:
                try:
                    winreg.QueryValueEx(key, APP_NAME)
                    return True
                except FileNotFoundError:
                    return False
        if sys.platform == "darwin":
            return _mac_plist_path().exists()
    except OSError:
        return False
    return False


def set_enabled(enabled: bool) -> str:
    """Enable or disable login autostart. Returns an empty string on success,
    or an error message."""
    try:
        if sys.platform == "linux":
            return _set_linux(enabled)
        if sys.platform == "win32":
            return _set_windows(enabled)
        if sys.platform == "darwin":
            return _set_mac(enabled)
    except OSError as e:
        return str(e)
    return "Autostart is not supported on this platform."


def exec_command() -> list:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    main = Path(__file__).resolve().parent.parent / "main.py"
    return [sys.executable, str(main), "--background"]


def _quote_arg(arg: str) -> str:
    if not any(c in arg for c in (" ", "\t", '"', "'", "\\", "$")):
        return arg
    return '"' + arg.replace("\\", "\\\\").replace('"', '\\"') + '"'


def linux_desktop_contents(command=None) -> str:
    cmd = " ".join(_quote_arg(a) for a in (command or exec_command()))
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Pomodoro timer with German vocabulary breaks\n"
        f"Exec={cmd}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def _set_linux(enabled: bool) -> str:
    path = LINUX_AUTOSTART
    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(linux_desktop_contents(), encoding="utf-8")
    return ""


def _set_windows(enabled: bool) -> str:
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                        winreg.KEY_SET_VALUE | winreg.KEY_READ) as key:
        if enabled:
            cmd = " ".join(f'"{a}"' if " " in a else a for a in exec_command())
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    return ""


def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"


def _set_mac(enabled: bool) -> str:
    path = _mac_plist_path()
    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return ""
    args = "".join(f"    <string>{a}</string>\n" for a in exec_command())
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f'  <key>Label</key><string>{APP_ID}</string>\n'
        '  <key>ProgramArguments</key><array>\n'
        f'{args}'
        '  </array>\n'
        '  <key>RunAtLoad</key><true/>\n'
        '</dict></plist>\n')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")
    return ""

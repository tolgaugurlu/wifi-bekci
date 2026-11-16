import ctypes
import subprocess
import sys
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_handles = []


def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return -1, "zaman aşımı"
    except OSError as e:
        return -2, str(e)
    out = (p.stdout or b"") + (p.stderr or b"")
    try:
        text = out.decode("utf-8")
    except UnicodeDecodeError:
        text = out.decode("oem", errors="replace")
    return p.returncode, text.strip()


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def pid_alive(pid):
    try:
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return code.value == 259
    except Exception:
        return False


def keep_awake():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    except Exception:
        pass


def lower_priority():
    try:
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)
    except Exception:
        pass


def enable_vt():
    try:
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass


def single_instance(name):
    try:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = k.CreateMutexW(None, False, name)
        if ctypes.get_last_error() == 183:
            return False
        _handles.append(handle)
    except Exception:
        pass
    return True


def pythonw():
    p = Path(sys.executable).with_name("pythonw.exe")
    return str(p) if p.exists() else sys.executable

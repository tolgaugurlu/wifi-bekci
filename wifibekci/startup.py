import os
from pathlib import Path

from . import store, system

NAME = "TolgaWifiBekci.vbs"


def path():
    folder = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return folder / NAME


def content():
    script = store.ROOT / "bekci.py"
    return f'CreateObject("WScript.Shell").Run """{system.pythonw()}"" ""{script}"" servis", 0, False\r\n'


def enabled():
    return path().exists()


def enable():
    path().write_text(content(), encoding="utf-16")


def disable():
    path().unlink(missing_ok=True)

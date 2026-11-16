import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from .system import run

PROBES = [("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443)]
PROBE_TIMEOUT = 1.5

_pool = ThreadPoolExecutor(max_workers=len(PROBES))


def _probe(addr):
    socket.create_connection(addr, timeout=PROBE_TIMEOUT).close()
    return True


def internet_ok():
    futures = [_pool.submit(_probe, a) for a in PROBES]
    try:
        for f in as_completed(futures, timeout=PROBE_TIMEOUT + 1):
            if f.exception() is None:
                return True
    except Exception:
        pass
    return False


def _pairs(text):
    for line in text.splitlines():
        key, sep, val = line.partition(":")
        if sep:
            yield key.strip(), val.strip()


def current_ssid():
    _, out = run(["netsh", "wlan", "show", "interfaces"], timeout=10)
    for key, val in _pairs(out):
        if key.upper() == "SSID" and val:
            return val
    return None


def profiles():
    _, out = run(["netsh", "wlan", "show", "profiles"], timeout=10)
    names = []
    for _, val in _pairs(out):
        if val and not val.startswith("<") and val not in names:
            names.append(val)
    return names


def connect(name):
    rc, out = run(["netsh", "wlan", "connect", f"name={name}"], timeout=15)
    return rc == 0, " ".join(out.split())[:160]


def set_auto(name):
    run(["netsh", "wlan", "set", "profileparameter", f"name={name}", "connectionmode=auto"], timeout=10)


def restart_adapter():
    script = (
        "Get-NetAdapter | Where-Object {$_.PhysicalMediaType -like '*802.11*' -or "
        "$_.Name -like '*Wi-Fi*' -or $_.Name -like '*Wireless*'} | "
        "Restart-NetAdapter -Confirm:$false"
    )
    return run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout=60)


def restart_service():
    run(["net", "stop", "wlansvc", "/y"], timeout=40)
    return run(["net", "start", "wlansvc"], timeout=40)

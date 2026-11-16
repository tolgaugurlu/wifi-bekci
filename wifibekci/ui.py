import sys
import time

RESET = "\x1b[0m"
DIM = "\x1b[2m"
GREEN = "\x1b[92m"
RED = "\x1b[91m"
YELLOW = "\x1b[93m"
CYAN = "\x1b[96m"

STATES = {
    "bagli": ("● Bağlı", GREEN),
    "kopuk": ("● Kopuk", RED),
    "baglaniyor": ("● Yeniden bağlanıyor", YELLOW),
}


def paint(text, color):
    return f"{color}{text}{RESET}"


def duration(seconds):
    seconds = int(max(0, seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def span(seconds):
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} sn"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} dk {s} sn"
    h, m = divmod(m, 60)
    return f"{h} sa {m} dk"


def clock(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))


def status_lines(s):
    now = time.time()
    label, color = STATES.get(s["state"], STATES["kopuk"])
    rows = [
        ("Durum", paint(label, color)),
        ("Hedef ağ", s["target"]),
        ("Bağlı ağ", s.get("ssid") or "yok"),
        ("Çalışma süresi", duration(now - s["started"])),
        ("Kesinti", f"{s['outages']} kez, toplam {span(s['downtime'])}"),
    ]
    if s.get("last_outage_at"):
        text = clock(s["last_outage_at"])
        if s.get("last_outage_len") is not None:
            text += f", {span(s['last_outage_len'])} sürdü"
        rows.append(("Son kesinti", text))
    if s["state"] != "bagli" and s.get("attempt"):
        rows.append(("Deneme", str(s["attempt"])))
    if s.get("last_check"):
        rows.append(("Son kontrol", f"{int(now - s['last_check'])} sn önce"))
    return ["  " + paint(k.ljust(16), DIM) + v for k, v in rows]


class Live:
    def __init__(self):
        self.height = 0
        self.drawn = False

    def draw(self, lines):
        out = sys.stdout
        self.height = max(self.height, len(lines))
        lines = lines + [""] * (self.height - len(lines))
        if self.drawn:
            out.write(f"\x1b[{self.height}A")
        for line in lines:
            out.write("\x1b[2K" + line + "\n")
        out.flush()
        self.drawn = True


def cursor(visible):
    sys.stdout.write("\x1b[?25h" if visible else "\x1b[?25l")
    sys.stdout.flush()

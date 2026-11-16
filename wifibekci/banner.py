import random
import sys
import time

from . import ui

GLYPHS = [
    [
        "████████╗",
        "╚══██╔══╝",
        "   ██║   ",
        "   ██║   ",
        "   ██║   ",
        "   ╚═╝   ",
    ],
    [
        " ██████╗ ",
        "██╔═══██╗",
        "██║   ██║",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    [
        "██╗     ",
        "██║     ",
        "██║     ",
        "██║     ",
        "███████╗",
        "╚══════╝",
    ],
    [
        " ██████╗ ",
        "██╔════╝ ",
        "██║  ███╗",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
]

NOISE = "01#$%&*+<>"
SUBTITLE = "Wi-Fi Bekçisi  1.0"


def rows():
    return ["".join(g[i] for g in GLYPHS) for i in range(6)]


def show():
    if not sys.stdout or not sys.stdout.isatty():
        return
    art = rows()
    width = max(len(r) for r in art)
    out = sys.stdout
    frames = 14
    try:
        ui.cursor(False)
        out.write("\n")
        for f in range(frames + 1):
            cut = int(width * f / frames)
            if f:
                out.write(f"\x1b[{len(art)}A")
            for row in art:
                shown = "".join(
                    ch if ch == " " or x < cut else random.choice(NOISE)
                    for x, ch in enumerate(row)
                )
                out.write(f"\x1b[2K{ui.GREEN}{shown}{ui.RESET}\n")
            out.flush()
            time.sleep(0.04)
        out.write("\n  ")
        for ch in SUBTITLE:
            out.write(f"{ui.DIM}{ch}{ui.RESET}")
            out.flush()
            time.sleep(0.02)
        out.write("\n\n")
    except UnicodeError:
        out.write("\nTOLGA\n\n")
    finally:
        ui.cursor(True)

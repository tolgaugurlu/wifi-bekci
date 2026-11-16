import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "veri"
CONFIG = DATA / "ayar.json"
STATUS = DATA / "durum.json"
LOG = DATA / "bekci.log"

DEFAULTS = {"ag": "", "aralik": 4.5}


def ensure():
    DATA.mkdir(exist_ok=True)


def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_config():
    cfg = dict(DEFAULTS)
    cfg.update(read_json(CONFIG) or {})
    return cfg


def save_config(cfg):
    ensure()
    write_json(CONFIG, cfg)


def read_status():
    return read_json(STATUS)

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from . import store, system, wifi

UP, DOWN, CONNECTING = "bagli", "kopuk", "baglaniyor"


class AlreadyRunning(Exception):
    pass


def logger():
    log = logging.getLogger("bekci")
    if not log.handlers:
        store.ensure()
        handler = RotatingFileHandler(store.LOG, maxBytes=500_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log


class Guard:
    def __init__(self, target, interval, on_tick=None):
        self.target = target
        self.interval = max(2.0, float(interval))
        self.on_tick = on_tick
        self.log = logger()
        self.admin = system.is_admin()
        self.state = UP
        self.started = time.time()
        self.outages = 0
        self.downtime = 0.0
        self.down_at = None
        self.last_outage_at = None
        self.last_outage_len = None
        self.last_check = None
        self.attempt = 0
        self.ssid = None
        self._written = 0.0
        self._warned = False

    def snapshot(self):
        now = time.time()
        downtime = self.downtime + (now - self.down_at if self.down_at else 0)
        return {
            "pid": os.getpid(),
            "updated": now,
            "started": self.started,
            "state": self.state,
            "target": self.target,
            "ssid": self.ssid,
            "outages": self.outages,
            "downtime": downtime,
            "last_outage_at": self.last_outage_at,
            "last_outage_len": self.last_outage_len,
            "last_check": self.last_check,
            "attempt": self.attempt,
        }

    def _emit(self, force=False):
        now = time.time()
        if force or now - self._written >= 4:
            store.write_json(store.STATUS, self.snapshot())
            self._written = now
        if self.on_tick:
            self.on_tick(self.snapshot())

    def _pause(self, seconds):
        end = time.monotonic() + seconds
        while True:
            left = end - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(1.0, left) if self.on_tick else left)
            self._emit()

    def _wait_up(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if wifi.internet_ok():
                return True
            self._emit()
            time.sleep(0.3)
        return False

    def _went_down(self):
        now = time.time()
        self.down_at = now
        self.last_outage_at = now
        self.outages += 1
        self.attempt = 0
        self.state = DOWN
        self.ssid = wifi.current_ssid()
        self.log.info("kesinti başladı, bağlı ağ: %s", self.ssid)
        self._emit(True)

    def _recovered(self):
        length = time.time() - self.down_at
        self.downtime += length
        self.last_outage_len = length
        self.log.info("bağlantı geri geldi, kesinti %.1f sn, %d deneme", length, self.attempt)
        self.down_at = None
        self.attempt = 0
        self.state = UP
        self.ssid = wifi.current_ssid()
        self._emit(True)

    def _recover_step(self):
        self.attempt += 1
        self.state = CONNECTING
        self._emit(True)
        step = self.attempt % 12
        if step in (5, 9):
            if self.admin:
                if step == 5:
                    self.log.info("deneme %d: adaptör yenileniyor", self.attempt)
                    wifi.restart_adapter()
                else:
                    self.log.info("deneme %d: WLAN servisi yenileniyor", self.attempt)
                    wifi.restart_service()
                time.sleep(3)
            elif not self._warned:
                self._warned = True
                self.log.info("yönetici yetkisi yok, adaptör ve servis yenileme atlanıyor")
        ok, msg = wifi.connect(self.target)
        self.log.info("deneme %d: bağlan komutu %s %s", self.attempt, "tamam" if ok else "hata", msg)
        if self._wait_up(8):
            return
        self.state = DOWN
        self._emit(True)
        self._pause(min(1 + self.attempt * 0.5, 10))

    def _cycle(self):
        system.keep_awake()
        ok = wifi.internet_ok()
        self.last_check = time.time()
        if ok:
            if self.down_at is not None:
                self._recovered()
            self._emit()
            self._pause(self.interval)
            return
        if self.down_at is None:
            self._pause(1.0)
            if wifi.internet_ok():
                return
            self._went_down()
        self._recover_step()

    def run(self):
        if not system.single_instance("Global\\TolgaWifiBekci"):
            raise AlreadyRunning
        system.lower_priority()
        wifi.set_auto(self.target)
        self.ssid = wifi.current_ssid()
        self.log.info("başladı, hedef ağ: %s, aralık: %.1f sn", self.target, self.interval)
        self._emit(True)
        while True:
            try:
                self._cycle()
            except KeyboardInterrupt:
                raise
            except Exception:
                self.log.exception("beklenmeyen hata")
                time.sleep(2)

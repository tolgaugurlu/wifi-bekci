import argparse
import subprocess
import sys
import time

from . import banner, startup, store, system, ui, wifi
from .guard import AlreadyRunning, Guard, logger

STALE = 180


def service_status():
    st = store.read_status()
    if not st or time.time() - st.get("updated", 0) > STALE:
        return None
    return st if system.pid_alive(st.get("pid", 0)) else None


def spawn_service():
    script = str(store.ROOT / "bekci.py")
    exe = system.pythonw()
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [exe, script, "servis"],
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=str(store.ROOT),
    )


def need_target():
    cfg = store.load_config()
    if not cfg["ag"]:
        print("Önce hedef ağı seç: bekci kur")
        return None
    return cfg


def cmd_durum(args):
    st = service_status()
    if not st:
        print("Servis çalışmıyor. Başlatmak için: bekci baslat")
        return 1
    print()
    print("\n".join(ui.status_lines(st)))
    print()
    return 0


def cmd_baslat(args):
    cfg = need_target()
    if not cfg:
        return 1
    if service_status():
        print("Servis zaten arka planda çalışıyor.")
        return 0
    spawn_service()
    for _ in range(20):
        time.sleep(0.3)
        if service_status():
            print(f"Arka planda başladı. Hedef ağ: {cfg['ag']}")
            return 0
    print("Servis başlatılamadı. Ayrıntı için: bekci log")
    return 1


def cmd_durdur(args):
    st = service_status()
    if not st:
        print("Servis zaten çalışmıyor.")
        return 0
    system.run(["taskkill", "/PID", str(st["pid"]), "/F"], timeout=10)
    for _ in range(20):
        if not system.pid_alive(st["pid"]):
            break
        time.sleep(0.2)
    store.STATUS.unlink(missing_ok=True)
    print("Servis durduruldu.")
    return 0


def cmd_canli(args):
    banner.show()
    live = ui.Live()
    ui.cursor(False)
    try:
        if service_status():
            print("Arka plandaki servis izleniyor. Ctrl+C ile çık, servis çalışmaya devam eder.\n")
            while True:
                st = service_status()
                if not st:
                    print("\nServis durdu.")
                    return 1
                live.draw(ui.status_lines(st))
                time.sleep(1)
        cfg = need_target()
        if not cfg:
            return 1
        print("Servis kapalı, bu pencerede çalışıyor. Ctrl+C ile durdur.\n")
        Guard(cfg["ag"], cfg["aralik"], lambda s: live.draw(ui.status_lines(s))).run()
    except KeyboardInterrupt:
        print("\nKapatıldı.")
    except AlreadyRunning:
        print("Başka bir kopya zaten çalışıyor.")
        return 1
    finally:
        ui.cursor(True)
    return 0


def cmd_kur(args):
    names = wifi.profiles()
    if args.ag:
        chosen = args.ag
    else:
        if not names:
            print("Kayıtlı Wi-Fi profili bulunamadı. Ağa bir kez bağlandıktan sonra tekrar dene.")
            return 1
        current = wifi.current_ssid()
        print()
        for i, name in enumerate(names, 1):
            mark = ui.paint("  bağlı", ui.GREEN) if name == current else ""
            print(f"  {ui.paint(str(i), ui.CYAN)}  {name}{mark}")
        try:
            raw = input("\nSeçim numarası: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if not raw.isdigit() or not 1 <= int(raw) <= len(names):
            print("Geçersiz seçim.")
            return 1
        chosen = names[int(raw) - 1]
    if chosen not in names:
        print("Bu isimde kayıtlı bir profil yok. Liste için: bekci ag")
        return 1
    cfg = store.load_config()
    cfg["ag"] = chosen
    store.save_config(cfg)
    print(f"Hedef ağ kaydedildi: {chosen}")
    if service_status():
        cmd_durdur(args)
        cmd_baslat(args)
    return 0


def cmd_ag(args):
    names = wifi.profiles()
    if not names:
        print("Kayıtlı Wi-Fi profili bulunamadı.")
        return 1
    current = wifi.current_ssid()
    target = store.load_config()["ag"]
    print()
    for name in names:
        tags = []
        if name == current:
            tags.append("bağlı")
        if name == target:
            tags.append("hedef")
        extra = ui.paint("  " + ", ".join(tags), ui.GREEN) if tags else ""
        print(f"  {name}{extra}")
    print()
    return 0


def cmd_log(args):
    try:
        lines = store.LOG.read_text(encoding="utf-8").splitlines()
    except OSError:
        print("Henüz kayıt yok.")
        return 0
    print("\n".join(lines[-args.n:]))
    return 0


def cmd_otostart(args):
    if args.islem == "ac":
        startup.enable()
        print("Windows açılışında otomatik başlayacak.")
    elif args.islem == "kapat":
        startup.disable()
        print("Otomatik başlatma kapatıldı.")
    else:
        print("Otomatik başlatma: " + ("açık" if startup.enabled() else "kapalı"))
    return 0


def cmd_servis(args):
    cfg = store.load_config()
    if not cfg["ag"]:
        return 1
    try:
        Guard(cfg["ag"], cfg["aralik"]).run()
    except (AlreadyRunning, KeyboardInterrupt):
        return 0
    except Exception:
        logger().exception("servis düştü")
        return 1


def toggle_startup(args):
    args.islem = "kapat" if startup.enabled() else "ac"
    return cmd_otostart(args)


def menu():
    banner.show()
    while True:
        auto = "açık" if startup.enabled() else "kapalı"
        items = [
            ("1", "Durum", cmd_durum),
            ("2", "Canlı izle", cmd_canli),
            ("3", "Arka planda başlat", cmd_baslat),
            ("4", "Durdur", cmd_durdur),
            ("5", "Ağ seç", cmd_kur),
            ("6", f"Windows açılışında otomatik başlat ({auto})", toggle_startup),
            ("7", "Son kayıtlar", cmd_log),
            ("0", "Çık", None),
        ]
        for key, label, _ in items:
            print(f"  {ui.paint(key, ui.CYAN)}  {label}")
        try:
            choice = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        action = next((fn for key, _, fn in items if key == choice), False)
        if choice == "0":
            return 0
        if action is False:
            print("Geçersiz seçim.\n")
            continue
        args = argparse.Namespace(ag=None, n=25, islem="durum")
        action(args)
        print()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="bekci",
        description="Wi-Fi bağlantısını izler, koparsa seçilen ağa otomatik yeniden bağlanır.",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="komut")

    def add(name, func, help_text):
        sp = sub.add_parser(name, help=help_text)
        sp.set_defaults(func=func)
        return sp

    add("durum", cmd_durum, "Servisin anlık durumunu göster")
    add("canli", cmd_canli, "Canlı durum ekranı")
    add("baslat", cmd_baslat, "Servisi arka planda başlat")
    add("durdur", cmd_durdur, "Arka plandaki servisi durdur")
    add("kur", cmd_kur, "Hedef ağı seç").add_argument("ag", nargs="?", help="ağ adı, boşsa listeden seçilir")
    add("ag", cmd_ag, "Kayıtlı ağları listele")
    add("log", cmd_log, "Son kayıtları göster").add_argument("n", nargs="?", type=int, default=25)
    add("otostart", cmd_otostart, "Windows açılışında otomatik başlatma").add_argument(
        "islem", nargs="?", choices=["ac", "kapat", "durum"], default="durum"
    )
    sub.add_parser("servis").set_defaults(func=cmd_servis)
    return parser


def main(argv=None):
    if sys.stdout:
        system.enable_vt()
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    store.ensure()
    if not args.cmd:
        return menu()
    return args.func(args)

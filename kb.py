#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Color del teclado. Un frame de luces se queda en el aparato hasta que se cambia.

Nunca manda configuración ni el probe que lo dejó mudo.
"""

import json
import math
import os
import select
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from presets import CATALOG, IDS, preset_frame
VID_PID = "258A:00000049"
HERE = Path(__file__).resolve()
STATE = Path.home() / ".config" / "teclado-color.json"
SOCK = Path("/tmp/teclado-color.sock")
WIN = sys.platform == "win32"
PORT = 47631
WHEEL = 240
FRAME = 0.016


class NoKeyboard(Exception):
    pass


class NeedPermission(Exception):
    pass


def hsv_rgb(h, s, v=1.0):
    h %= 1.0
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i % 6]
    return int(r * 255), int(g * 255), int(b * 255)


def led_packet(rgb=None, slots=None):
    pkt = bytearray(382)
    pkt[0:4] = bytes((0x08, 0x0A, 0x7A, 0x01))
    if slots is None:
        color = bytes(max(0, min(255, int(c))) for c in rgb)
        for i in range(126):
            pkt[4 + i * 3:7 + i * 3] = color
    else:
        for i, col in enumerate(slots[:126]):
            pkt[4 + i * 3:7 + i * 3] = bytes(max(0, min(255, int(c))) for c in col)
    if pkt[0] != 0x08 or pkt[1:4] != b"\x0a\x7a\x01":
        raise RuntimeError("paquete rechazado")
    return pkt


def scale(rgb, brightness, extra=1.0):
    level = max(0, min(4, int(brightness))) / 4 * extra
    return tuple(max(0, min(255, int(c * level))) for c in rgb)


def find_node():
    hits = []
    for sysfs in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        try:
            uevent = (sysfs / "device" / "uevent").read_text()
        except OSError:
            continue
        if VID_PID not in uevent.upper():
            continue
        iface, d = "", sysfs.resolve()
        for _ in range(6):
            f = d / "bInterfaceNumber"
            if f.exists():
                iface = f.read_text().strip()
                break
            d = d.parent
        hits.append((iface, Path("/dev") / sysfs.name))
    for iface, node in hits:
        if iface == "01":
            return node
    if hits:
        return hits[-1][1]
    raise NoKeyboard()
def _guard(pkt):
    if pkt[0] != 0x08 or len(pkt) != 382 or pkt[1:4] != b"\x0a\x7a\x01" or b"\x05\x83\xb6" in pkt[:6]:
        raise RuntimeError("solo se puede enviar el color")


def close_fd(fd):
    if not fd:
        return
    if WIN:
        import win_hid
        win_hid.close(fd)
        return
    try:
        os.close(fd)
    except OSError:
        pass


def ioctl_send(fd, pkt):
    _guard(pkt)
    if WIN:
        import win_hid
        win_hid.send(fd, pkt)
        return
    import fcntl
    fcntl.ioctl(fd, (3 << 30) | (382 << 16) | (ord("H") << 8) | 0x06, bytearray(pkt))


def load_state():
    base = {"color": (255, 255, 255), "brightness": 4, "mode": "solid", "fresh": True}
    try:
        data = json.loads(STATE.read_text())
        rgb = tuple(int(x) for x in data["color"])
        if len(rgb) != 3 or any(c < 0 or c > 255 for c in rgb):
            raise ValueError
        mode = data.get("mode", "solid")
        if mode not in IDS and mode not in ("solid", "off"):
            mode = "solid"
        base.update(color=rgb, brightness=min(4, max(1, int(data.get("brightness", 4)))), mode=mode, fresh=False)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return base


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({
        "color": list(state["color"]),
        "brightness": state["brightness"],
        "mode": state["mode"],
    }))
    tmp.replace(STATE)




def frame_rgb(state, now):
    mode = state["mode"]
    if mode == "off":
        return (0, 0, 0)
    if mode == "rainbow":
        hue = (state.get("hue0", 0.0) + now * 0.25) % 1
        return scale(hsv_rgb(hue, 1), state["brightness"])
    if mode == "breath":
        wave = 0.22 + 0.78 * (0.5 + 0.5 * math.sin(now * 2.4))
        return scale(state["color"], state["brightness"], wave)
    if mode == "latido":
        t = now % 0.86
        def hit(center, width):
            d = abs(t - center)
            return 0 if d > width else math.cos(d / width * math.pi / 2) ** 2
        amp = max(hit(0.08, 0.09), hit(0.24, 0.07) * 0.72)
        return scale((210, 24, 32), state["brightness"], 0.1 + 0.9 * amp)
    if mode == "aurora":
        hue = 0.42 + 0.2 * math.sin(now * 0.28)
        glow = 0.45 + 0.4 * (0.5 + 0.5 * math.sin(now * 0.9))
        return scale(hsv_rgb(hue, 0.7), state["brightness"], glow)

    return scale(state["color"], state["brightness"])


def frame_slots(state, now):
    mode = state["mode"]
    br = state["brightness"]
    if mode == "ola":
        colors = []
        for i in range(126):
            col = i // 6
            amp = 0.12 + 0.88 * (0.5 + 0.5 * math.sin(now * 2.4 - col * 0.42))
            hue = (now * 0.06 + col / 22) % 1
            colors.append(scale(hsv_rgb(hue, 0.9), br, amp))
        return colors
    if mode == "fuego":
        colors = []
        for i in range(126):
            heat = (5 - (i % 6)) / 5
            flick = 0.55 + 0.45 * math.sin(now * 13 + i * 1.9) * math.sin(now * 7 + i * 0.7)
            flick = max(0.3, min(1.0, flick))
            if heat > 0.7:
                rgb = (255, 210, 60)
            elif heat > 0.35:
                rgb = (255, 90, 0)
            else:
                rgb = (140, 12, 0)
            colors.append(scale(rgb, br, flick * (0.3 + 0.7 * heat)))
        return colors
    if mode == "policia":
        left_on = int(now / 0.16) % 2 == 0
        colors = []
        for i in range(126):
            left = (i // 6) < 11
            if left:
                rgb = (255, 0, 0) if left_on else (12, 0, 0)
            else:
                rgb = (0, 30, 255) if not left_on else (0, 0, 16)
            colors.append(scale(rgb, br))
        return colors
    if mode == "cometa":
        # slot = columna*6 + fila (arriba→abajo). La cabeza cruza y vuelve; la estela queda detrás.
        t = (now * 0.42) % 2
        phase = t if t < 1 else 2 - t
        head_x = -1.4 + phase * 23.5
        head_y = 2.6
        colors = []
        for i in range(126):
            col, row = divmod(i, 6)
            x = col + row * 0.18
            y = row
            dx = head_x - x
            dy = y - head_y
            if dx < -0.7:
                colors.append(scale((0, 4, 18), br, 0.22))
                continue
            behind = math.hypot(max(dx, 0) * 0.42, dy * 0.85)
            tail = math.exp(-behind * 0.72)
            head = math.exp(-math.hypot(dx, dy * 0.9) * 2.1)
            amp = max(tail * 0.9, head)
            r = int(30 * tail + 255 * head)
            g = int(70 * tail + 245 * head)
            b = int(210 * tail + 255 * head)
            colors.append(scale((min(255, r), min(255, g), min(255, b)), br, min(1, amp)))
        return colors
def open_fd():
    if WIN:
        import win_hid
        try:
            return win_hid.open_led()
        except win_hid.Missing:
            raise NoKeyboard()
        except win_hid.Denied:
            raise PermissionError("hid")
    return os.open(find_node(), os.O_RDWR)


def push(fd, rgb=None, slots=None):
    pkt = led_packet(rgb, slots)
    try:
        ioctl_send(fd, pkt)
        return fd
    except OSError:
        close_fd(fd)
        fd = open_fd()
        ioctl_send(fd, led_packet(rgb, slots))
        return fd


def apply_cmd(state, cmd):
    if cmd[0] == "solid" and len(cmd) == 5:
        state.update(mode="solid", color=tuple(int(x) for x in cmd[1:4]), brightness=int(cmd[4]))
    elif cmd[0] == "rainbow" and len(cmd) == 2:
        state.update(mode="rainbow", brightness=int(cmd[1]), hue0=time.monotonic() * -0.25)
    elif cmd[0] in IDS and len(cmd) == 5:
        state.update(mode=cmd[0], color=tuple(int(x) for x in cmd[1:4]), brightness=int(cmd[4]))
    elif cmd[0] == "off":
        state["mode"] = "off"
    else:
        return False
    return True


def arm_windows():
    if not WIN:
        return
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return
    base = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)

    def vbs(args):
        extra = f" {args}" if args else ""
        return f'Set sh = CreateObject("Wscript.Shell")\r\nsh.Run """{exe}"" ""{HERE}""{extra}", 0, False\r\n'

    try:
        (base / "Startup").mkdir(parents=True, exist_ok=True)
        (base / "Startup" / "Teclado.vbs").write_text(vbs("--render"), encoding="utf-8")
        (base / "Teclado.vbs").write_text(vbs(""), encoding="utf-8")
    except OSError:
        pass


def render():
    arm_windows()
    if WIN:
        try:
            s = _connect()
            s.close()
            return
        except OSError:
            pass
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("127.0.0.1", PORT))
        except OSError:
            raise SystemExit(1)
    else:
        if SOCK.exists():
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.2)
                s.connect(str(SOCK))
                s.close()
                return
            except OSError:
                try:
                    SOCK.unlink()
                except OSError:
                    raise SystemExit(1)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(SOCK))
        os.chmod(SOCK, 0o666)
    srv.listen(64)
    srv.setblocking(False)
    lock = threading.Lock()
    state = load_state()
    state["hue0"] = 0.0
    wake = threading.Event()

    def painter():
        fd = None
        last = None
        moving = IDS
        while True:
            now = time.monotonic()
            with lock:
                mode = state["mode"]
                snap = dict(state)
            slots, rgb = preset_frame(snap, now)
            if slots is None and rgb is None:
                slots = frame_slots(snap, now)
                rgb = None if slots else frame_rgb(snap, now)
            current = tuple(map(tuple, slots)) if slots else rgb
            if mode in moving or current != last:
                try:
                    if fd is None:
                        fd = open_fd()
                    fd = push(fd, rgb, slots)
                    last = current
                except (NoKeyboard, OSError):
                    if fd is not None:
                        close_fd(fd)
                    fd = None
                    time.sleep(0.2)
                    continue
            if mode in moving:
                time.sleep(FRAME)
            else:
                wake.wait(0.5)
                wake.clear()

    threading.Thread(target=painter, daemon=True).start()


    clients, bufs = [], {}
    while True:
        readable, _, _ = select.select([srv, *clients], [], [], 0.5)
        changed = False
        for sock in readable:
            if sock is srv:
                conn, _ = srv.accept()
                conn.setblocking(False)
                clients.append(conn)
                bufs[conn] = ""
                continue
            try:
                chunk = sock.recv(4096)
            except OSError:
                chunk = b""
            if not chunk:
                clients.remove(sock)
                bufs.pop(sock, None)
                sock.close()
                continue
            bufs[sock] += chunk.decode(errors="ignore")
            while "\n" in bufs[sock]:
                line, bufs[sock] = bufs[sock].split("\n", 1)
                cmd = line.split()
                if not cmd:
                    continue
                with lock:
                    if apply_cmd(state, cmd):
                        save_state(state)
                        changed = True
        if changed:
            wake.set()


def _connect():
    if WIN:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        s.connect(("127.0.0.1", PORT))
    else:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.4)
        s.connect(str(SOCK))
    s.settimeout(None)
    return s


def _is_root():
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)


def _spawn_render():
    if WIN:
        exe = Path(sys.executable)
        pyw = exe.with_name("pythonw.exe")
        if pyw.exists():
            exe = pyw
        subprocess.Popen(
            [str(exe), str(HERE), "--render"],
            creationflags=0x08000000 | 0x00000008 | 0x00000200,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    subprocess.Popen(
        [sys.executable, str(HERE), "--render"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_render():
    for _ in range(30):
        try:
            s = _connect()
            s.close()
            return
        except OSError:
            time.sleep(0.05)
    if not _is_root() and not _can_open():
        raise NeedPermission()
    _spawn_render()
    for _ in range(40):
        try:
            s = _connect()
            s.close()
            return
        except OSError:
            time.sleep(0.05)
    raise NeedPermission()


def _can_open():
    try:
        close_fd(open_fd())
        return True
    except NoKeyboard:
        raise
    except (PermissionError, OSError):
        return False


class Bus:
    def __init__(self):
        self.sock = None

    def send(self, line):
        last = None
        for _ in range(6):
            try:
                if self.sock is None:
                    ensure_render()
                    self.sock = _connect()
                self.sock.sendall((line + "\n").encode())
                return
            except OSError as exc:
                last = exc
                self.close()
                time.sleep(0.05)
        raise last

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None


def self_check():
    pkt = led_packet((255, 255, 255))
    assert pkt[:4] == b"\x08\x0a\x7a\x01" and len(pkt) == 382
    assert pkt[4:7] == b"\xff\xff\xff" and b"\x05\x83\xb6" not in pkt
    assert frame_rgb({"mode": "off", "color": (255, 0, 0), "brightness": 4}, 0) == (0, 0, 0)
    assert frame_rgb({"mode": "solid", "color": (255, 0, 0), "brightness": 4}, 0) == (255, 0, 0)
    st = {"color": (1, 2, 3), "brightness": 4, "mode": "solid"}
    assert apply_cmd(st, ["off"]) and st["mode"] == "off"
    import win_hid
    win_hid.guard(pkt)
    try:
        win_hid.guard(b"\x05\x83\xb6" + bytes(376))
        raise AssertionError("el comando mudo no puede pasar")
    except RuntimeError:
        pass
    print("check ok")


def plain_error(exc):
    if isinstance(exc, NoKeyboard):
        return "No encuentro el teclado. Enchúfalo y prueba otra vez."
    return "No se pudo cambiar el color."


def wheel_ppm(size=WHEEL):
    cx = cy = (size - 1) / 2
    radius = size / 2 - 1
    raw = bytearray()
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = math.hypot(dx, dy)
            if dist > radius:
                raw += b"\xf3\xf3\xf4"
                continue
            raw += bytes(hsv_rgb((math.atan2(dy, dx) / (2 * math.pi)) % 1, dist / radius))
    return f"P6 {size} {size} 255\n".encode() + raw


def gui():
    import tkinter as tk
    from tkinter import messagebox
    arm_windows()
    root = tk.Tk()
    root.title("Teclado")
    root.configure(bg="#f3f3f4")
    root.resizable(False, False)
    state = load_state()
    buttons = {}
    bus = Bus()
    warned = {"t": 0.0}

    def brightness():
        return int(bright.get())

    def remember():
        state["brightness"] = brightness()
        save_state(state)

    def style():
        hold["v"] = True
        listing.selection_clear(0, "end")
        for i, (pid, _name) in enumerate(CATALOG):
            if pid == state["mode"]:
                listing.selection_set(i)
                listing.see(i)
        hold["v"] = False

    def line():
        if state["mode"] == "off":
            return "off"
        r, g, b = state["color"]
        if state["mode"] in IDS:
            return f"{state['mode']} {r} {g} {b} {brightness()}"
        return f"solid {r} {g} {b} {brightness()}"

    def commit(quiet=False):
        remember()
        try:
            bus.send(line())
        except (NoKeyboard, NeedPermission, OSError) as exc:
            if quiet:
                return
            now = time.monotonic()
            if now - warned["t"] < 2:
                return
            warned["t"] = now
            messagebox.showinfo("Teclado", plain_error(exc))

    def set_mode(mode, toggle=False):
        if toggle and mode in ("rainbow", "breath", "latido", "ola", "fuego", "policia", "cometa", "aurora") and state["mode"] == mode:
            mode = "solid"
        state["mode"] = mode
        style()
        commit()

    def color_at(x, y):
        cx = cy = (WHEEL - 1) / 2
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        radius = WHEEL / 2 - 1
        if dist > radius:
            return None
        return hsv_rgb((math.atan2(dy, dx) / (2 * math.pi)) % 1, dist / radius)

    def pick(event, force=False):
        rgb = color_at(event.x, event.y)
        if rgb is None:
            return
        state["mode"] = "solid"
        state["color"] = rgb
        style()
        mark.place(x=event.x - 7, y=event.y - 7)
        now = time.monotonic()
        if force or now - state.get("drag", 0) > 0.03:
            state["drag"] = now
            commit(quiet=not force)

    def animate():
        now = time.monotonic()
        mode = state["mode"]
        if mode == "rainbow":
            ang = (now * 0.25) % 1 * 2 * math.pi
            cx = cy = WHEEL / 2
            mark.place(x=cx + math.cos(ang) * WHEEL * 0.36 - 7, y=cy + math.sin(ang) * WHEEL * 0.36 - 7)
            preview.configure(bg="#%02x%02x%02x" % hsv_rgb((now * 0.25) % 1, 1))
        elif mode == "breath":
            wave = 0.22 + 0.78 * (0.5 + 0.5 * math.sin(now * 2.4))
            preview.configure(bg="#%02x%02x%02x" % scale(state["color"], 4, wave))
        elif mode == "latido":
            t = now % 0.86
            def hit(center, width):
                d = abs(t - center)
                return 0 if d > width else math.cos(d / width * math.pi / 2) ** 2
            amp = 0.1 + 0.9 * max(hit(0.08, 0.09), hit(0.24, 0.07) * 0.72)
            preview.configure(bg="#%02x%02x%02x" % scale((210, 24, 32), 4, amp))
        elif mode == "ola":
            preview.configure(bg="#%02x%02x%02x" % hsv_rgb((now * 0.06) % 1, 0.9))
        elif mode == "fuego":
            preview.configure(bg="#%02x%02x%02x" % ((255, 90 + int(40 * abs(math.sin(now * 9))), 0)))
        elif mode == "policia":
            preview.configure(bg="#ff0000" if int(now / 0.16) % 2 == 0 else "#0020ff")
        elif mode == "cometa":
            preview.configure(bg="#d2ebff" if (now % 2.6) < 1.8 else "#111111")
        elif mode == "aurora":
            hue = 0.42 + 0.2 * math.sin(now * 0.28)
            glow = 0.45 + 0.4 * (0.5 + 0.5 * math.sin(now * 0.9))
            preview.configure(bg="#%02x%02x%02x" % scale(hsv_rgb(hue, 0.7), 4, glow))
        elif mode == "off":
            preview.configure(bg="#111111")
        else:
            preview.configure(bg="#%02x%02x%02x" % state["color"])
        root.after(16, animate)

    tk.Label(root, text="Elige un color", bg="#f3f3f4", fg="#222", font=("sans-serif", 13, "bold")).pack(pady=(14, 6))
    img = tk.PhotoImage(data=wheel_ppm())
    canvas = tk.Canvas(root, width=WHEEL, height=WHEEL, bg="#f3f3f4", highlightthickness=0)
    canvas.pack()
    canvas.create_image(0, 0, image=img, anchor="nw")
    canvas.image = img
    mark = tk.Frame(canvas, width=14, height=14, bg="#fff", highlightbackground="#111", highlightthickness=2)
    preview = tk.Frame(root, width=72, height=22, bg="#%02x%02x%02x" % state["color"])
    preview.pack(pady=(8, 0))
    canvas.bind("<Button-1>", lambda e: pick(e, True))
    canvas.bind("<B1-Motion>", pick)
    canvas.bind("<ButtonRelease-1>", lambda e: pick(e, True))
    tk.Label(root, text="Brillo", bg="#f3f3f4", fg="#222", font=("sans-serif", 13, "bold")).pack(pady=(10, 0))
    bright = tk.Scale(root, from_=1, to=4, orient="horizontal", showvalue=False, length=WHEEL, bg="#f3f3f4", highlightthickness=0, troughcolor="#ddd")
    bright.set(state["brightness"])
    bright.pack()
    bright.bind("<ButtonRelease-1>", lambda _e: set_mode(state["mode"]))
    tk.Label(root, text="Efectos", bg="#f3f3f4", fg="#222", font=("sans-serif", 13, "bold")).pack(pady=(8, 0))
    hold = {"v": False}
    listing = tk.Listbox(root, height=9, font=("sans-serif", 12), activestyle="none", selectbackground="#1d4ed8", selectforeground="#fff", bg="#fff", relief="flat", highlightthickness=0)
    for n, (_pid, name) in enumerate(CATALOG, 1):
        listing.insert("end", f"{n}. {name}")
    listing.pack(fill="x", padx=14, pady=(4, 0))
    def on_list(_event=None):
        if hold["v"]:
            return
        sel = listing.curselection()
        if not sel:
            return
        pid = CATALOG[sel[0]][0]
        if pid != state["mode"]:
            set_mode(pid)
    listing.bind("<<ListboxSelect>>", on_list)
    tk.Button(
        root, text="Apagar", font=("sans-serif", 12), width=26, height=2, relief="flat",
        bg="#2b2b2b", fg="#fff", activebackground="#111", activeforeground="#fff",
        command=lambda: set_mode("off"),
    ).pack(pady=(8, 16))
    style()
    animate()
    if not state.get("fresh"):
        root.after(80, commit)
    root.protocol("WM_DELETE_WINDOW", lambda: (bus.close(), root.destroy()))
    root.mainloop()


def main():
    if "--check" in sys.argv:
        self_check()
        return 0
    if "--render" in sys.argv:
        render()
        return 0
    gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())

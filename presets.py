"""Efectos de luz. Orden: lo más habitual en los programas de teclado, luego lo más de exhibición."""

import math

# id, nombre visible. El color fijo va en la rueda, no aquí.
CATALOG = [
    ("rainbow", "Arcoíris"),
    ("ola", "Ola"),
    ("breath", "Respirar"),
    ("stars", "Estrellas"),
    ("colorwave", "Ola de color"),
    ("fuego", "Fuego"),
    ("rain", "Lluvia"),
    ("ocean", "Océano"),
    ("sunset", "Atardecer"),
    ("neon", "Neón"),
    ("aurora", "Aurora"),
    ("pulse", "Pulso"),
    ("gradient", "Gradiente"),
    ("latido", "Latido"),
    ("cometa", "Cometa"),
    ("scanner", "Escáner"),
    ("lava", "Lava"),
    ("matrix", "Matrix"),
    ("forest", "Bosque"),
    ("ice", "Hielo"),
    ("dawn", "Amanecer"),
    ("violet", "Violeta"),
    ("gold", "Oro"),
    ("mint", "Menta"),
    ("rose", "Rosa"),
    ("crimson", "Carmesí"),
    ("indigo", "Índigo"),
    ("coral", "Coral"),
    ("lemon", "Limón"),
    ("cloud", "Nube"),
    ("storm", "Tormenta"),
    ("glacier", "Glaciar"),
    ("ember", "Brasa"),
    ("jungle", "Selva"),
    ("twilight", "Crepúsculo"),
    ("radar", "Radar"),
    ("spiral", "Espiral"),
    ("policia", "Policía"),
    ("alert", "Alerta"),
    ("disco", "Disco"),
    ("night", "Noche"),
    ("candy", "Chuche"),
    ("sakura", "Cerezo"),
    ("deep", "Abismo"),
    ("copper", "Cobre"),
    ("pearl", "Perla"),
    ("toxic", "Tóxico"),
    ("royal", "Real"),
    ("sand", "Arena"),
    ("blood", "Sangre"),
]
IDS = {item[0] for item in CATALOG}


def hsv(h, s=1.0, v=1.0):
    h %= 1.0
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i % 6]
    return int(r * 255), int(g * 255), int(b * 255)


def shade(rgb, brightness, extra=1.0):
    level = max(0, min(4, int(brightness))) / 4 * extra
    return tuple(max(0, min(255, int(c * level))) for c in rgb)


def _slots(paint):
    return [paint(i) for i in range(126)]


def preset_frame(state, now):
    """Devuelve (slots o None, color único o None)."""
    mode = state["mode"]
    br = state["brightness"]
    color = state.get("color", (255, 255, 255))
    if mode not in IDS:
        return None, None
    if mode == "rainbow":
        hue = (state.get("hue0", 0.0) + now * 0.25) % 1
        return None, shade(hsv(hue), br)
    if mode == "breath":
        wave = 0.22 + 0.78 * (0.5 + 0.5 * math.sin(now * 2.4))
        return None, shade(color, br, wave)
    if mode == "latido":
        t = now % 0.86
        def hit(center, width):
            d = abs(t - center)
            return 0 if d > width else math.cos(d / width * math.pi / 2) ** 2
        amp = max(hit(0.08, 0.09), hit(0.24, 0.07) * 0.72)
        return None, shade((210, 24, 32), br, 0.1 + 0.9 * amp)
    if mode == "aurora":
        hue = 0.42 + 0.2 * math.sin(now * 0.28)
        glow = 0.45 + 0.4 * (0.5 + 0.5 * math.sin(now * 0.9))
        return None, shade(hsv(hue, 0.7), br, glow)
    if mode == "neon":
        return None, shade(hsv(now * 0.55), br)
    if mode == "sunset":
        return None, shade(hsv(0.02 + 0.1 * (0.5 + 0.5 * math.sin(now * 0.2))), br)
    if mode == "dawn":
        return None, shade(hsv(0.08 + 0.06 * (0.5 + 0.5 * math.sin(now * 0.12)), 0.55), br, 0.7)
    if mode == "pulse":
        return None, shade(color, br, 0.15 + 0.85 * abs(math.sin(now * 3.2)))
    if mode == "alert":
        return None, shade((255, 30, 0), br, 1 if int(now * 4) % 2 == 0 else 0.08)
    if mode == "disco":
        return None, shade(hsv(int(now * 6) / 8), br, 1 if int(now * 8) % 2 == 0 else 0.15)
    if mode in ("violet", "gold", "mint", "rose", "crimson", "indigo", "coral", "lemon", "cloud", "sakura", "deep", "copper", "pearl", "toxic", "royal", "sand", "blood", "candy"):
        hues = {
            "violet": 0.78, "gold": 0.12, "mint": 0.45, "rose": 0.94, "crimson": 0.0,
            "indigo": 0.72, "coral": 0.04, "lemon": 0.16, "cloud": 0.58, "sakura": 0.93,
            "deep": 0.66, "copper": 0.07, "pearl": 0.1, "toxic": 0.3, "royal": 0.75,
            "sand": 0.1, "blood": 0.0, "candy": 0.88,
        }
        sats = {"cloud": 0.15, "pearl": 0.25, "sand": 0.45, "deep": 0.9}
        wave = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(now * 1.6))
        return None, shade(hsv(hues[mode], sats.get(mode, 0.85)), br, wave)
    return _slots(lambda i, mode=mode, now=now, br=br, color=color: _slot(mode, i, now, br, color)), None


def _slot(mode, i, now, br, color):
    col, row = divmod(i, 6)
    if mode == "ola":
        amp = 0.12 + 0.88 * (0.5 + 0.5 * math.sin(now * 2.4 - col * 0.42))
        return shade(hsv((now * 0.06 + col / 22) % 1, 0.9), br, amp)
    if mode == "colorwave":
        amp = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(now * 2.2 - col * 0.5))
        return shade(color, br, amp)
    if mode == "gradient":
        return shade(hsv((col / 21 + now * 0.04) % 1), br)
    if mode == "spiral":
        amp = 0.1 + 0.9 * (0.5 + 0.5 * math.sin(now * 3 - col * 0.35 - row * 0.5))
        return shade(hsv((now * 0.1 + col / 22) % 1), br, amp)
    if mode == "fuego":
        heat = (5 - row) / 5
        flick = max(0.3, min(1.0, 0.55 + 0.45 * math.sin(now * 13 + i * 1.9)))
        rgb = (255, 210, 60) if heat > 0.7 else (255, 90, 0) if heat > 0.35 else (140, 12, 0)
        return shade(rgb, br, flick * (0.3 + 0.7 * heat))
    if mode == "ember":
        heat = (5 - row) / 5
        flick = 0.4 + 0.3 * math.sin(now * 4 + i)
        return shade((180, 40, 0), br, flick * (0.25 + 0.75 * heat))
    if mode == "rain":
        drop = int(now * 8 + col * 3) % 8
        on = drop == row
        return shade((140, 190, 255) if on else (0, 8, 28), br, 1 if on else 0.25)
    if mode == "storm":
        drop = int(now * 14 + col * 2) % 7
        flash = int(now * 3) % 11 == 0
        if flash:
            return shade((220, 230, 255), br, 0.7)
        on = drop == row
        return shade((80, 110, 180) if on else (0, 4, 16), br, 1 if on else 0.2)
    if mode == "ocean":
        amp = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(now * 1.1 - col * 0.35 + row * 0.15))
        return shade((0, 40 + int(80 * amp), 90 + int(80 * amp)), br, amp)
    if mode == "glacier":
        amp = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(now * 0.8 - col * 0.3))
        return shade((180, 220, 255), br, amp)
    if mode == "ice":
        amp = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(now * 1.4 - col * 0.25))
        return shade(hsv(0.55, 0.35), br, amp)
    if mode == "forest":
        amp = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(now * 0.9 - row * 0.4))
        return shade((20, 140, 40), br, amp)
    if mode == "jungle":
        on = (int(now * 6) + col + row) % 9 == 0
        return shade((0, 255, 70) if on else (0, 30, 8), br, 1 if on else 0.35)
    if mode == "matrix":
        fall = int(now * 10 + col * 4) % 10
        on = fall == row or fall == (row + 1) % 6
        return shade((0, 255, 70) if on else (0, 18, 6), br, 1 if on else 0.2)
    if mode == "lava":
        amp = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(now * 0.7 - col * 0.2 + row * 0.3))
        return shade((255, int(40 + 80 * amp), 0), br, amp)
    if mode == "stars" or mode == "night":
        tick = int(now * (2.2 if mode == "stars" else 0.8))
        spark = ((i * 17 + tick * 13) % 23) == 0
        return shade((255, 255, 255) if spark else (8, 10, 28), br, 1 if spark else 0.2)
    if mode == "scanner" or mode == "radar":
        speed = 6 if mode == "radar" else 3
        span = 21
        pos = (now * speed) % (span * 2)
        pos = pos if pos < span else span * 2 - pos
        dist = abs(col - pos)
        amp = max(0, 1 - dist / (1.2 if mode == "radar" else 2.2))
        return shade((255, 255, 255), br, amp if amp else 0.05)
    if mode == "policia":
        left_on = int(now / 0.16) % 2 == 0
        left = col < 11
        if left:
            rgb = (255, 0, 0) if left_on else (12, 0, 0)
        else:
            rgb = (0, 30, 255) if not left_on else (0, 0, 16)
        return shade(rgb, br)
    if mode == "cometa":
        t = (now * 0.42) % 2
        phase = t if t < 1 else 2 - t
        head_x = -1.4 + phase * 23.5
        x = col + row * 0.18
        y = row
        dx = head_x - x
        dy = y - 2.6
        if dx < -0.7:
            return shade((0, 4, 18), br, 0.22)
        behind = math.hypot(max(dx, 0) * 0.42, dy * 0.85)
        tail = math.exp(-behind * 0.72)
        head = math.exp(-math.hypot(dx, dy * 0.9) * 2.1)
        amp = max(tail * 0.9, head)
        rgb = (min(255, int(30 * tail + 255 * head)), min(255, int(70 * tail + 245 * head)), min(255, int(210 * tail + 255 * head)))
        return shade(rgb, br, min(1, amp))
    if mode == "fuego":
        heat = (5 - row) / 5
        flick = max(0.3, min(1.0, 0.55 + 0.45 * math.sin(now * 13 + i * 1.9)))
        rgb = (255, 210, 60) if heat > 0.7 else (255, 90, 0) if heat > 0.35 else (140, 12, 0)
        return shade(rgb, br, flick * (0.3 + 0.7 * heat))
    return shade(color, br)

# -*- coding: utf-8 -*-
"""
KOZMOGENİS // PROSEDÜREL SANAT
Roket (gövde + motor + elektrik + anten + yük, gövdede ajans adı),
fırlatma aracı, gölgelendirilmiş gezegenler, asteroitler, uydular,
yakıt istasyonu, astronotlar ve koloni bayrağı.
"""
import math
import random

import pygame

from . import data as D
from .config import C, CREW_COLORS
from .fx import draw_glow, lerp_color, scale_color, HAS_NUMPY, glow_sprite
from .ui import render_text, draw_text

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

_CACHE = {}


def _cine_on():
    from . import i18n
    return i18n.PREFS.get("cinematic", True)


def _styl(img, **kw):
    from . import cinema
    return cinema.stylize_sprite(img, **kw)


def _cache(key, fn):
    s = _CACHE.get(key)
    if s is None:
        s = fn()
        if len(_CACHE) > 400:
            _CACHE.clear()
        _CACHE[key] = s
    return s


def metal_gradient(w, h, base, horizontal=True, k=0.55):
    """Silindirik metal gölgelendirme."""
    s = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
    n = w if horizontal else h
    for i in range(n):
        t = i / max(1, n - 1)
        light = 0.55 + 0.75 * math.sin(math.pi * (t * 0.85 + 0.08)) ** 0.8
        if t > 0.72:
            light *= 0.75
        c = scale_color(base, light * k + (1 - k))
        if horizontal:
            pygame.draw.line(s, c, (i, 0), (i, h))
        else:
            pygame.draw.line(s, c, (0, i), (w, i))
    return s


# ===========================================================================
# ROKET (yukarı bakan)
# ===========================================================================
def render_spacecraft(hull, engine, power, antenna, payloads, agency, color, scale=1.0, t=0.0):
    """
    Uzay aracını yukarı bakacak şekilde çizer.
    Dönüş: (surface, nozzle_offset(x,y), center_offset)
    """
    hk = hull or "orbiter"
    ek = engine or "liquid"
    pk = power or "solar"
    ak = antenna or "low"
    pls = tuple(payloads or ())
    key = ("craft", hk, ek, pk, ak, pls, agency, tuple(color), round(scale, 2))
    def build():
        W0, H0 = int(260 * scale), int(300 * scale)
        s = pygame.Surface((W0, H0), pygame.SRCALPHA)
        cx = W0 // 2
        sc = scale
        hull_d = D.PART["hull"].get(hk, D.HULLS[1])
        base = hull_d["color"]
        # boyutlar
        dims = {"probe": (40, 60), "orbiter": (56, 86), "capsule": (64, 80), "lander": (70, 84),
                "station": (60, 150), "cargo": (84, 126), "armored": (72, 110)}
        bw, bh = dims.get(hk, (56, 86))
        bw, bh = int(bw * sc), int(bh * sc)
        top = int(70 * sc)
        body = pygame.Rect(cx - bw // 2, top, bw, bh)
        # --- elektrik (arkada) ----------------------------------------------
        if pk in ("solar", "big_solar"):
            wings = 2 if pk == "solar" else 4
            pw, ph = int(78 * sc) if pk == "solar" else int(96 * sc), int(30 * sc)
            frame = (70, 140, 255) if pk == "solar" else (255, 206, 84)
            ys = [body.y + bh * 0.35] if wings == 2 else [body.y + bh * 0.22, body.y + bh * 0.58]
            for yy in ys:
                for side in (-1, 1):
                    r = pygame.Rect(0, 0, pw, ph)
                    r.centery = int(yy)
                    r.x = body.centerx + side * (bw // 2 + 6) - (pw if side < 0 else 0)
                    pygame.draw.line(s, (150, 160, 180), (body.centerx + side * bw // 2, r.centery),
                                     (r.right if side < 0 else r.x, r.centery), max(1, int(3 * sc)))
                    pygame.draw.rect(s, (16, 30, 80), r)
                    cells = 5 if pk == "solar" else 7
                    for i in range(cells):
                        cr = pygame.Rect(r.x + 2 + i * (r.w - 4) / cells, r.y + 2, (r.w - 4) / cells - 2, r.h - 4)
                        pygame.draw.rect(s, (40, 90, 200), cr)
                        pygame.draw.line(s, (120, 180, 255), cr.topleft, (cr.right, cr.y), 1)
                    pygame.draw.rect(s, frame, r, max(1, int(2 * sc)))
        elif pk == "rtg":
            for side in (-1, 1):
                rx = body.centerx + side * (bw // 2 + int(16 * sc))
                rr = pygame.Rect(0, 0, int(16 * sc), int(40 * sc))
                rr.center = (rx, body.y + bh * 0.6)
                pygame.draw.line(s, (150, 160, 180), (body.centerx + side * bw // 2, rr.centery), rr.center, 2)
                pygame.draw.rect(s, (40, 40, 48), rr, border_radius=4)
                for i in range(4):
                    yy = rr.y + 6 + i * rr.h / 4
                    pygame.draw.line(s, (90, 90, 100), (rr.x - 5, yy), (rr.right + 5, yy), 2)
                pygame.draw.circle(s, (255, 120, 60), rr.center, max(2, int(3 * sc)))
        elif pk == "battery":
            br = pygame.Rect(0, 0, int(26 * sc), int(18 * sc))
            br.midleft = (body.right - 2, body.y + bh * 0.55)
            pygame.draw.rect(s, (60, 70, 90), br, border_radius=3)
            pygame.draw.rect(s, (70, 255, 160), br.inflate(-8, -8))
        elif pk == "fuelcell":
            for side in (-1, 1):
                tr = pygame.Rect(0, 0, int(18 * sc), int(46 * sc))
                tr.center = (body.centerx + side * (bw // 2 + int(10 * sc)), body.y + bh * 0.55)
                s.blit(metal_gradient(tr.w, tr.h, (220, 225, 235)), tr)
                pygame.draw.rect(s, (120, 130, 150), tr, 1, border_radius=6)
                pygame.draw.circle(s, (120, 200, 255), (tr.centerx, tr.y + 6), 3)
        # --- gövde -----------------------------------------------------------
        if hk == "probe":
            pygame.draw.circle(s, (230, 200, 90), body.center, bw // 2)
            pygame.draw.circle(s, (255, 240, 170), (body.centerx - bw // 6, body.centery - bw // 6), bw // 6)
            pygame.draw.circle(s, (150, 120, 40), body.center, bw // 2, 2)
            nose_y = body.y
        elif hk == "capsule" or hk == "lander":
            pts = [(body.centerx - bw * 0.22, body.y), (body.centerx + bw * 0.22, body.y),
                   (body.right, body.bottom), (body.x, body.bottom)]
            g = metal_gradient(bw, bh, base)
            m = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.polygon(m, (255, 255, 255, 255), [(p[0] - body.x, p[1] - body.y) for p in pts])
            g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            s.blit(g, body)
            pygame.draw.polygon(s, scale_color(base, 0.5), pts, 2)
            pygame.draw.rect(s, scale_color(base, 0.45), (body.x, body.bottom - 8 * sc, bw, 8 * sc))
            for i in range(2):
                wr = pygame.Rect(0, 0, int(12 * sc), int(12 * sc))
                wr.center = (body.centerx - 10 * sc + i * 20 * sc, body.y + bh * 0.42)
                pygame.draw.ellipse(s, (30, 50, 90), wr)
                pygame.draw.ellipse(s, (150, 220, 255), wr.inflate(-6, -6))
            nose_y = body.y
            if hk == "lander":
                for side in (-1, 1):
                    fx0 = body.centerx + side * bw * 0.4
                    fy0 = body.bottom - 4
                    fx1 = body.centerx + side * bw * 0.75
                    fy1 = body.bottom + 34 * sc
                    pygame.draw.line(s, (200, 200, 210), (fx0, fy0), (fx1, fy1), max(2, int(3 * sc)))
                    pygame.draw.line(s, (230, 200, 120), (fx1 - 8 * sc, fy1), (fx1 + 8 * sc, fy1), max(2, int(4 * sc)))
        else:
            g = metal_gradient(bw, bh, base)
            m = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, bw, bh), border_radius=int(10 * sc))
            g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            s.blit(g, body)
            pygame.draw.rect(s, scale_color(base, 0.45), body, 2, border_radius=int(10 * sc))
            # burun
            nose = [(body.x + 4, body.y + 6), (body.centerx, body.y - bw * 0.7), (body.right - 4, body.y + 6)]
            if hk in ("cargo",):
                nose = [(body.x, body.y + 4), (body.x + bw * 0.25, body.y - bw * 0.35),
                        (body.right - bw * 0.25, body.y - bw * 0.35), (body.right, body.y + 4)]
            pygame.draw.polygon(s, scale_color(base, 0.9), nose)
            pygame.draw.polygon(s, scale_color(base, 0.5), nose, 2)
            nose_y = int(min(p[1] for p in nose))
            if hk == "station":
                for i in range(5):
                    wy = body.y + 16 * sc + i * (bh - 30 * sc) / 5
                    pygame.draw.rect(s, (30, 50, 90), (body.centerx - 6 * sc, wy, 12 * sc, 9 * sc), border_radius=3)
                    pygame.draw.rect(s, (170, 230, 255), (body.centerx - 4 * sc, wy + 2, 8 * sc, 5 * sc), border_radius=2)
                pygame.draw.rect(s, (90, 100, 120), (body.x - 6 * sc, body.y + bh * 0.48, bw + 12 * sc, 8 * sc))
            elif hk == "cargo":
                for i in range(3):
                    cy = body.y + 14 * sc + i * bh / 3.2
                    pygame.draw.rect(s, (180, 120, 50), (body.x + 8 * sc, cy, bw - 16 * sc, bh / 4.2), 2, border_radius=4)
                    pygame.draw.line(s, (200, 150, 70), (body.x + 8 * sc, cy), (body.right - 8 * sc, cy + bh / 4.2), 1)
            elif hk == "armored":
                for i in range(6):
                    py = body.y + 6 + i * bh / 6
                    pygame.draw.line(s, (90, 100, 115), (body.x + 3, py), (body.right - 3, py), 2)
                    for j in range(3):
                        pygame.draw.circle(s, (200, 205, 215), (int(body.x + 8 + j * (bw - 16) / 2), int(py + 4)), 2)
            elif hk == "orbiter":
                pygame.draw.rect(s, (255, 206, 84), (body.x + 4, body.y + bh * 0.55, bw - 8, bh * 0.3), border_radius=3)
                for i in range(4):
                    pygame.draw.line(s, (200, 150, 40), (body.x + 6 + i * (bw - 12) / 3, body.y + bh * 0.56),
                                     (body.x + 6 + i * (bw - 12) / 3, body.y + bh * 0.84), 1)
            # ajans adı (dikey)
            if bh > 70 * sc and agency:
                name = agency.upper()[:14]
                fs = max(9, int(13 * sc))
                txt = render_text(name, fs, tuple(color), True)
                txt = pygame.transform.rotate(txt, 90)
                if txt.get_height() > bh - 20:
                    txt = pygame.transform.smoothscale(txt, (txt.get_width(), int(bh - 20)))
                s.blit(txt, (body.x + 6 * sc, body.centery - txt.get_height() // 2))
        # --- yükler -------------------------------------------------------
        for i, pk2 in enumerate(pls):
            py = body.y + bh * (0.2 + 0.22 * i)
            pr = pygame.Rect(0, 0, int(14 * sc), int(14 * sc))
            pr.center = (body.right - int(8 * sc), int(py))
            colp = {"camera": (40, 40, 50), "spectro": (150, 100, 255), "magneto": (230, 230, 240),
                    "biolab": (70, 220, 120)}[pk2]
            pygame.draw.rect(s, colp, pr, border_radius=3)
            if pk2 == "camera":
                pygame.draw.circle(s, (120, 200, 255), pr.center, max(2, pr.w // 3))
            elif pk2 == "spectro":
                for j, cc in enumerate(((255, 80, 80), (255, 220, 80), (80, 255, 140), (80, 160, 255))):
                    pygame.draw.line(s, cc, (pr.x + 2, pr.y + 3 + j * 3), (pr.right - 2, pr.y + 3 + j * 3), 1)
            elif pk2 == "magneto":
                pygame.draw.line(s, (255, 64, 84), pr.center, (pr.centerx + 5 * math.cos(t * 4), pr.centery - 5), 2)
            elif pk2 == "biolab":
                pygame.draw.circle(s, (200, 255, 220), pr.center, max(2, pr.w // 3), 1)
        # --- anten --------------------------------------------------------
        ax, ay = body.centerx, nose_y
        if ak == "low":
            pygame.draw.line(s, (210, 210, 220), (ax, ay), (ax, ay - 26 * sc), 2)
            pygame.draw.circle(s, (255, 90, 90), (ax, int(ay - 26 * sc)), 3)
        elif ak == "high":
            pygame.draw.line(s, (200, 200, 210), (ax, ay), (ax, ay - 14 * sc), 3)
            dish = pygame.Rect(0, 0, int(44 * sc), int(18 * sc))
            dish.center = (ax, int(ay - 20 * sc))
            pygame.draw.arc(s, (230, 235, 245), dish, 0, math.pi, max(2, int(4 * sc)))
            pygame.draw.line(s, (200, 200, 210), dish.center, (ax, dish.y - 6 * sc), 2)
        elif ak == "laser":
            pygame.draw.line(s, (180, 180, 190), (ax, ay), (ax, ay - 18 * sc), 4)
            pygame.draw.circle(s, (255, 60, 60), (ax, int(ay - 20 * sc)), max(3, int(6 * sc)))
            pygame.draw.circle(s, (255, 200, 200), (ax, int(ay - 20 * sc)), max(1, int(2 * sc)))
        elif ak == "dsn":
            for k in (-1, 0, 1):
                dx = ax + k * 18 * sc
                pygame.draw.line(s, (200, 200, 210), (ax, ay), (dx, ay - 18 * sc), 2)
                d2 = pygame.Rect(0, 0, int(20 * sc), int(10 * sc))
                d2.center = (int(dx), int(ay - 22 * sc))
                pygame.draw.arc(s, (230, 235, 245), d2, 0, math.pi, 3)
            pygame.draw.circle(s, (62, 200, 255), (ax, int(ay - 20 * sc)), int(26 * sc), 2)
        # --- motor --------------------------------------------------------
        ny = body.bottom + (2 if hk not in ("capsule", "lander") else 0)
        if ek == "sail":
            pygame.draw.line(s, (200, 200, 210), (body.centerx, body.y + bh * 0.3), (body.centerx, body.y - 40 * sc), 2)
            sail = [(body.centerx - 110 * sc, body.y - 30 * sc), (body.centerx + 110 * sc, body.y - 30 * sc),
                    (body.centerx + 80 * sc, body.y + bh * 0.9), (body.centerx - 80 * sc, body.y + bh * 0.9)]
            ss = pygame.Surface((W0, H0), pygame.SRCALPHA)
            pygame.draw.polygon(ss, (210, 220, 235, 120), sail)
            pygame.draw.polygon(ss, (240, 245, 255, 220), sail, 2)
            for i in range(1, 5):
                pygame.draw.line(ss, (255, 255, 255, 90), sail[0], (sail[3][0] + (sail[2][0] - sail[3][0]) * i / 5, sail[3][1]), 1)
            s.blit(ss, (0, 0), special_flags=0)
            nozzle = (body.centerx, ny)
        else:
            nw = {"solid": 30, "liquid": 26, "ion": 22, "nuclear": 32, "plasma": 30}.get(ek, 26)
            nh = {"solid": 26, "liquid": 24, "ion": 14, "nuclear": 30, "plasma": 22}.get(ek, 24)
            nw, nh = int(nw * sc), int(nh * sc)
            ncol = {"solid": (120, 110, 100), "liquid": (170, 175, 190), "ion": (80, 120, 200),
                    "nuclear": (110, 90, 140), "plasma": (130, 110, 200)}.get(ek, (160, 160, 170))
            pts = [(body.centerx - nw * 0.35, ny), (body.centerx + nw * 0.35, ny),
                   (body.centerx + nw * 0.5, ny + nh), (body.centerx - nw * 0.5, ny + nh)]
            pygame.draw.polygon(s, ncol, pts)
            pygame.draw.polygon(s, scale_color(ncol, 0.5), pts, 2)
            pygame.draw.line(s, scale_color(ncol, 1.4), pts[0], pts[3], 2)
            if ek == "nuclear":
                pygame.draw.circle(s, (255, 220, 60), (body.centerx, int(ny + nh * 0.4)), max(3, int(5 * sc)))
                pygame.draw.circle(s, (40, 30, 10), (body.centerx, int(ny + nh * 0.4)), max(1, int(2 * sc)))
            if ek == "ion":
                pygame.draw.ellipse(s, (120, 200, 255), (body.centerx - nw * 0.45, ny + nh - 5, nw * 0.9, 8))
            nozzle = (body.centerx, ny + nh)
        return _styl(s), nozzle
    return _cache(key + (_cine_on(),), build)


def render_booster(size, agency, color, scale=1.0):
    """Fırlatma aracı (Rampa A/B/C)."""
    key = ("boost", size, agency, tuple(color), round(scale, 2))

    def build():
        bw = int({1: 54, 2: 70, 3: 92}[size] * scale)
        bh = int({1: 190, 2: 260, 3: 340}[size] * scale)
        W0, H0 = bw + int(120 * scale), bh + int(40 * scale)
        s = pygame.Surface((W0, H0), pygame.SRCALPHA)
        cx = W0 // 2
        body = pygame.Rect(cx - bw // 2, 0, bw, bh)
        s.blit(metal_gradient(bw, bh, (224, 226, 228)), body)
        # bantlar
        for yy in (0.18, 0.6):
            pygame.draw.rect(s, (30, 32, 40), (body.x, body.y + bh * yy, bw, 10 * scale))
        pygame.draw.rect(s, tuple(color), (body.x, body.y + bh * 0.85, bw, 8 * scale))
        # yan güçlendiriciler (dev roket)
        if size >= 2:
            for side in (-1, 1):
                sw, sh = int(bw * 0.38), int(bh * 0.62)
                r = pygame.Rect(0, 0, sw, sh)
                r.bottom = bh
                r.centerx = cx + side * (bw // 2 + sw // 2 - 2)
                s.blit(metal_gradient(sw, sh, (225, 228, 236)), r)
                pygame.draw.polygon(s, (200, 200, 210), [(r.x, r.y), (r.centerx, r.y - sw), (r.right, r.y)])
                pygame.draw.rect(s, (120, 125, 140), r, 1)
        # kanatçıklar
        for side in (-1, 1):
            fin = [(cx + side * bw // 2, bh - 60 * scale), (cx + side * (bw // 2 + 34 * scale), bh + 8 * scale),
                   (cx + side * bw // 2, bh)]
            pygame.draw.polygon(s, scale_color(tuple(color), 0.85), fin)
            pygame.draw.polygon(s, scale_color(tuple(color), 0.5), fin, 2)
        # ajans adı (kanadın üstünde dikey)
        fs = max(12, int({1: 16, 2: 20, 3: 26}[size] * scale))
        txt = render_text(agency.upper()[:16], fs, (20, 26, 44), True)
        txt = pygame.transform.rotate(txt, 90)
        if txt.get_height() > bh * 0.5:
            txt = pygame.transform.smoothscale(txt, (txt.get_width(), int(bh * 0.5)))
        s.blit(txt, (cx - txt.get_width() // 2, bh * 0.24))
        # nozul
        nz = [(cx - bw * 0.3, bh), (cx + bw * 0.3, bh), (cx + bw * 0.4, bh + 26 * scale), (cx - bw * 0.4, bh + 26 * scale)]
        pygame.draw.polygon(s, (90, 90, 100), nz)
        pygame.draw.rect(s, (120, 125, 140), body, 1)
        return _styl(s), (cx, bh + int(26 * scale))
    return _cache(key + (_cine_on(),), build)


# ===========================================================================
# MOTOR ALEVİ (parçacık yayımı)
# ===========================================================================
def emit_flame(ps, x, y, engine_key, direction, power=1.0, scale=1.0):
    """direction: radyan, alevin akış yönü."""
    if power <= 0.02:
        return
    sp = 0.35
    if engine_key == "solid":
        ps.fire(x, y, n=int(5 * power) + 1, angle=direction, spread=0.28, speed=(260 * scale, 520 * scale),
                size=(9 * scale, 20 * scale), life=(0.25, 0.6), ramp="fire", drag=1.4)
        if random.random() < 0.5 * power:
            ps.smoke(x, y, n=1, angle=direction, spread=0.5, speed=(60, 160), size=(10 * scale, 22 * scale),
                     life=(0.8, 1.8), alpha=90, grow=30)
    elif engine_key == "liquid":
        ps.fire(x, y, n=int(4 * power) + 1, angle=direction, spread=0.16, speed=(300 * scale, 520 * scale),
                size=(6 * scale, 14 * scale), life=(0.2, 0.45), ramp="blue", drag=1.6)
    elif engine_key == "ion":
        ps.fire(x, y, n=int(2 * power) + 1, angle=direction, spread=0.05, speed=(380 * scale, 520 * scale),
                size=(3 * scale, 6 * scale), life=(0.25, 0.55), ramp="blue", drag=0.4)
    elif engine_key == "nuclear":
        ps.fire(x, y, n=int(4 * power) + 1, angle=direction, spread=0.18, speed=(320 * scale, 560 * scale),
                size=(7 * scale, 16 * scale), life=(0.2, 0.5), ramp="purple", drag=1.4)
    elif engine_key == "plasma":
        ps.fire(x, y, n=int(4 * power) + 1, angle=direction, spread=0.1, speed=(380 * scale, 640 * scale),
                size=(8 * scale, 16 * scale), life=(0.2, 0.5), ramp="plasma", drag=1.2)
        if random.random() < 0.35 * power:
            ps.sparks(x, y, n=2, color=(190, 160, 255), speed=(80, 260), life=(0.15, 0.35), grav=0)
    elif engine_key == "sail":
        if random.random() < 0.3:
            ps.glow(x + random.uniform(-60, 60) * scale, y, n=1, color=(220, 230, 255), speed=(5, 30), size=(1, 3),
                    life=(0.4, 1.0))


def draw_flame_core(surf, x, y, engine_key, direction, power, scale=1.0, t=0.0):
    """Nozul çıkışında parlak çekirdek (parçacıkların altında)."""
    if power <= 0.02 or engine_key == "sail":
        return
    col = {"solid": (255, 180, 80), "liquid": (150, 210, 255), "ion": (110, 180, 255),
           "nuclear": (200, 120, 255), "plasma": (180, 150, 255)}.get(engine_key, (255, 200, 120))
    length = {"solid": 70, "liquid": 60, "ion": 46, "nuclear": 70, "plasma": 80}.get(engine_key, 60) * scale * power
    length *= 0.85 + 0.15 * math.sin(t * 40)
    for i in range(6):
        k = i / 6
        px = x + math.cos(direction) * length * k
        py = y + math.sin(direction) * length * k
        draw_glow(surf, (px, py), (22 - 14 * k) * scale * (0.6 + power * 0.4), col, 1.0 - k * 0.7)
    draw_glow(surf, (x, y), 34 * scale * power, col, 0.9)


# ===========================================================================
# GEZEGENLER
# ===========================================================================
def planet_surface(key, radius, light=(-0.6, -0.45)):
    radius = int(radius)
    ck = ("planet", key, radius, light)
    if radius > 640:
        def build_big():
            base = planet_surface(key, 640, light)
            k = radius / 640
            return pygame.transform.smoothscale(base, (int(base.get_width() * k), int(base.get_height() * k)))
        return _cache(ck, build_big)

    def build():
        if key == "earth":
            col1, col2 = (40, 110, 220), (20, 50, 120)
            glow = (120, 190, 255)
        else:
            p = D.PLANET[key]
            col1, col2, glow = p["color"], p["color2"], p["glow"]
        size = radius * 2 + 40
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        if HAS_NUMPY:
            rng = np.random.default_rng(abs(hash(key)) % 1000)
            ys, xs = np.mgrid[-radius:radius, -radius:radius].astype(np.float32)
            xs = (xs + 0.5) / radius
            ys = (ys + 0.5) / radius
            rr = xs * xs + ys * ys
            inside = rr <= 1.0
            z = np.sqrt(np.clip(1 - rr, 0, 1))
            lx, ly = light
            lz = math.sqrt(max(0.0, 1 - lx * lx - ly * ly))
            lam = np.clip(xs * lx + ys * ly + z * lz, 0, 1)
            shade = 0.12 + 0.95 * lam ** 0.9
            # doku
            lat = ys
            lon = np.arctan2(xs, z + 1e-6)
            tex = np.zeros_like(xs)
            if key == "jupiter":
                tex = 0.5 + 0.5 * np.sin(lat * 18 + np.sin(lon * 3) * 0.6) * 0.8
                tex += 0.15 * np.sin(lat * 47 + lon * 2)
                spot = np.exp(-(((lon - 0.5) * 3.2) ** 2 + ((lat - 0.32) * 9) ** 2))
            elif key == "earth":
                tex = (np.sin(lon * 3.1 + 0.4) * np.cos(lat * 4.2) + np.sin(lon * 7 + lat * 5) * 0.4) > 0.35
                tex = tex.astype(np.float32)
                spot = None
            else:
                g = rng.random((24, 24)).astype(np.float32)
                ix = np.clip(((xs + 1) * 11.5).astype(int), 0, 23)
                iy = np.clip(((ys + 1) * 11.5).astype(int), 0, 23)
                tex = g[ix, iy]
                tex = 0.6 * tex + 0.4 * (0.5 + 0.5 * np.sin(lon * 5 + lat * 7))
                spot = None
            c1 = np.array(col1, dtype=np.float32)
            c2 = np.array(col2, dtype=np.float32)
            if key == "earth":
                land = np.array((60, 150, 80), dtype=np.float32)
                rgb = c1[None, None, :] * (1 - tex[..., None]) + land[None, None, :] * tex[..., None]
                cloud = (np.sin(lon * 9 + lat * 13) * np.sin(lat * 6) > 0.55).astype(np.float32) * 0.6
                rgb = rgb * (1 - cloud[..., None]) + 255 * cloud[..., None]
            else:
                rgb = c2[None, None, :] + (c1 - c2)[None, None, :] * tex[..., None]
                if key == "jupiter" and spot is not None:
                    rgb = rgb * (1 - spot[..., None] * 0.6) + np.array((200, 90, 60))[None, None, :] * spot[..., None] * 0.6
            if key == "moon":
                for _ in range(26):
                    cx2, cy2 = rng.uniform(-0.9, 0.9, 2)
                    cr = rng.uniform(0.04, 0.16)
                    d = np.sqrt((xs - cx2) ** 2 + (ys - cy2) ** 2)
                    rim = np.exp(-((d - cr) / (cr * 0.25)) ** 2) * 0.25
                    bowl = (d < cr) * 0.22
                    rgb = rgb * (1 - bowl[..., None]) + rgb * rim[..., None]
            if key == "mars":
                cap = np.clip((np.abs(ys) - 0.82) * 8, 0, 1)
                rgb = rgb * (1 - cap[..., None]) + 240 * cap[..., None]
            if key == "venus":
                swirl = 0.5 + 0.5 * np.sin(lon * 4 + lat * 9 + np.sin(lat * 4) * 2)
                rgb = rgb * (0.8 + 0.25 * swirl[..., None])
            rgb = rgb * shade[..., None]
            rim = np.clip((rr - 0.82) / 0.18, 0, 1) ** 2 * inside
            gcol = np.array(glow, dtype=np.float32)
            rgb = rgb * (1 - rim[..., None] * 0.5) + gcol[None, None, :] * rim[..., None] * 0.5 * (0.3 + lam[..., None])
            rgb = np.clip(rgb, 0, 255).astype(np.uint8)
            alpha = (inside * 255).astype(np.uint8)
            # kenar yumuşatma
            edge = np.clip((1.0 - np.sqrt(rr)) * radius * 1.2, 0, 1)
            alpha = (edge * 255 * inside).astype(np.uint8)
            ps = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.surfarray.blit_array(ps, np.ascontiguousarray(rgb.transpose(1, 0, 2)))
            a = pygame.surfarray.pixels_alpha(ps)
            a[:, :] = alpha.T
            del a
        else:
            ps = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for i in range(radius, 0, -1):
                k = i / radius
                pygame.draw.circle(ps, lerp_color(col1, col2, k), (int(radius * 0.8 + (1 - k) * 0.2 * radius),
                                                                    int(radius * 0.8)), i)
        # atmosfer
        for i in range(14, 0, -1):
            a = int(60 * (1 - i / 15) ** 2)
            pygame.draw.circle(s, (*glow, a), (c, c), radius + i, 2)
        s.blit(ps, (c - radius, c - radius))
        if key == "jupiter":
            pass
        return s
    return _cache(ck, build)


_P3D = {}


def planet3d_surface(key, radius, light=(-0.6, -0.45)):
    """Atlas çizicisiyle (space3d) ışıklı, dokulu küre; boyut kovalarında önbelleklenir.
    Çok büyük yarıçaplar en fazla 520 px'de çizilip yumuşakça büyütülür."""
    try:
        from . import space3d as S3
        from . import i18n
        import math as _m
    except Exception:
        return None
    radius = max(2, int(radius))
    rr = min(radius, 520)
    step = 1 if rr < 40 else (4 if rr < 160 else 16)
    rb = max(2, int(round(rr / step) * step))
    lk = (round(light[0], 1), round(light[1], 1))
    key3 = (key, rb, lk, i18n.PREFS.get("cinematic", True))
    img = _P3D.get(key3)
    if img is None:
        try:
            lx, ly = lk
            lz = _m.sqrt(max(0.05, 1 - lx * lx - ly * ly))
            Lv = S3.norm3(np.array((lx, -ly, lz), dtype=np.float32))
            M = S3.rot_z(_m.radians(-12)) @ S3.rot_x(0.25)
            th = 256 if rb < 60 else (512 if rb < 200 else S3.safe_tex(key, max(512, i18n.quality()["tex"])))
            img = S3.to_surface(S3.render_body(key, rb, M, Lv, 0.9, 0.0, th))
        except Exception:
            img = False
        if len(_P3D) > 80:
            _P3D.clear()
        _P3D[key3] = img
    if not img:
        return None
    if rb != radius:
        img = pygame.transform.smoothscale(img, (radius * 2, radius * 2))
    return img


def draw_planet(surf, key, center, radius, light=(-0.6, -0.45), glow=True):
    ps = planet3d_surface(key, radius, light) if HAS_NUMPY else None
    if ps is None:
        ps = planet_surface(key, radius, light)
    if glow:
        col = (120, 190, 255) if key == "earth" else D.PLANET[key]["glow"]
        draw_glow(surf, center, radius * 1.5, scale_color(col, 0.35), 0.6)
    surf.blit(ps, (center[0] - ps.get_width() // 2, center[1] - ps.get_height() // 2))


# ===========================================================================
# ASTEROİTLER
# ===========================================================================
AST_COLORS = {
    "rock": ((120, 108, 98), (70, 62, 58)),
    "big": ((110, 100, 92), (60, 54, 50)),
    "gold": ((240, 190, 70), (150, 100, 30)),
    "ice": ((180, 225, 255), (90, 140, 200)),
    "ore": ((125, 110, 100), (72, 64, 60)),
    "debris": ((170, 175, 185), (90, 95, 110)),
    "ring": ((226, 214, 190), (140, 128, 110)),
    "ringice": ((240, 244, 250), (150, 165, 190)),
}


def asteroid_sprite(kind, radius, seed):
    radius = int(radius)
    key = ("ast", kind, radius, seed % 12)

    def build():
        r = random.Random(seed % 12 * 977 + radius)
        size = radius * 2 + 6
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        c1, c2 = AST_COLORS.get(kind, AST_COLORS["rock"])
        if kind == "debris":
            pts = [(c - radius, c - radius * 0.3), (c + radius * 0.6, c - radius * 0.7), (c + radius, c + radius * 0.2),
                   (c - radius * 0.2, c + radius * 0.6)]
            pygame.draw.polygon(s, c1, pts)
            pygame.draw.polygon(s, c2, pts, 2)
            pygame.draw.line(s, (255, 206, 84), pts[0], pts[2], 1)
            return s
        n = 11
        pts = []
        for i in range(n):
            a = i / n * math.tau
            rr = radius * r.uniform(0.72, 1.0)
            pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
        pygame.draw.polygon(s, c2, pts)
        inner = [(c + (x - c) * 0.86 - radius * 0.08, c + (y - c) * 0.86 - radius * 0.1) for x, y in pts]
        pygame.draw.polygon(s, c1, inner)
        for _ in range(max(2, radius // 7)):
            cx = c + r.uniform(-0.5, 0.5) * radius
            cy = c + r.uniform(-0.5, 0.5) * radius
            cr = r.uniform(0.08, 0.2) * radius
            pygame.draw.circle(s, c2, (int(cx), int(cy)), int(cr))
            pygame.draw.circle(s, scale_color(c1, 1.15), (int(cx - cr * 0.3), int(cy - cr * 0.3)), max(1, int(cr * 0.4)))
        if kind == "gold":
            for _ in range(5):
                gx = c + r.uniform(-0.5, 0.5) * radius
                gy = c + r.uniform(-0.5, 0.5) * radius
                pygame.draw.circle(s, (255, 250, 200), (int(gx), int(gy)), 2)
        if kind == "ice":
            pygame.draw.polygon(s, (230, 250, 255), inner, 2)
        pygame.draw.polygon(s, scale_color(c2, 0.6), pts, 2)
        return _styl(s, rim=(255, 200, 150) if kind != "ice" else (170, 230, 255), brushk=radius > 10)
    return _cache(key + (_cine_on(),), build)


def draw_satellite(surf, x, y, t, scale=1.0, color=(220, 225, 235)):
    a = t * 0.8
    body = pygame.Rect(0, 0, int(22 * scale), int(22 * scale))
    body.center = (int(x), int(y))
    for side in (-1, 1):
        pr = pygame.Rect(0, 0, int(34 * scale), int(14 * scale))
        pr.center = (int(x + side * 30 * scale), int(y))
        pygame.draw.rect(surf, (30, 60, 160), pr)
        pygame.draw.rect(surf, (120, 170, 255), pr, 1)
        pygame.draw.line(surf, (160, 160, 170), body.center, pr.center, 2)
    pygame.draw.rect(surf, color, body, border_radius=4)
    pygame.draw.rect(surf, (255, 206, 84), body.inflate(-8, -8), border_radius=2)
    blink = (t * 2) % 1 < 0.5
    if blink:
        draw_glow(surf, (x, y - 14 * scale), 12, (255, 80, 80), 1.0)


def draw_fuel_station(surf, x, y, t, scale=1.0):
    ring = int(46 * scale)
    pygame.draw.circle(surf, (120, 130, 150), (int(x), int(y)), ring, 6)
    for i in range(6):
        a = t * 0.4 + i * math.tau / 6
        px, py = x + math.cos(a) * ring, y + math.sin(a) * ring
        pygame.draw.circle(surf, (230, 230, 240), (int(px), int(py)), int(8 * scale))
        draw_glow(surf, (px, py), 10, (255, 160, 60), 0.6)
    core = pygame.Rect(0, 0, int(36 * scale), int(36 * scale))
    core.center = (int(x), int(y))
    pygame.draw.rect(surf, (240, 140, 50), core, border_radius=8)
    pygame.draw.rect(surf, (255, 220, 160), core, 2, border_radius=8)
    draw_text(surf, "F", core.center, int(20 * scale), (40, 20, 10), True, anchor="center", shadow=False)


# ===========================================================================
# ASTRONOT
# ===========================================================================
SUIT_STYLE = "balanced"        # ajansın seçtiği kıyafet tipi (app tarafından ayarlanır)


def draw_astronaut(surf, x, y, ctype, scale=1.0, t=0.0, tired=False, sick=False, wave=False, suit=None):
    col = CREW_COLORS.get(ctype, (200, 200, 200))
    st = suit or SUIT_STYLE
    w = {"armored": 1.22, "agile": 0.86}.get(st, 1.0)          # zırhlı: iri ve hantal · çevik: ince ve hızlı
    s = scale
    y = y + math.sin(t * {"armored": 2.2, "agile": 3.8}.get(st, 3.0) + x * 0.1) * 2 * s
    bw = 11 * s * w
    lw = max(1, int(2 * s))
    pygame.draw.rect(surf, scale_color(col, 0.55), (x - bw - 2 * s, y - 6 * s, bw * 2 + 4 * s, 30 * s), border_radius=int(6 * s))
    pygame.draw.rect(surf, col, (x - bw, y - 4 * s, bw * 2, 30 * s), border_radius=int(8 * s))
    pygame.draw.rect(surf, scale_color(col, 0.6), (x - bw, y - 4 * s, bw * 2, 30 * s), lw, border_radius=int(8 * s))
    pygame.draw.rect(surf, (230, 235, 245), (x - 6 * s, y + 4 * s, 12 * s, 8 * s), border_radius=2)
    if st == "armored":
        plate = scale_color(col, 0.42)
        pygame.draw.rect(surf, plate, (x - bw - 3 * s, y - 5 * s, 9 * s, 9 * s), border_radius=int(3 * s))
        pygame.draw.rect(surf, plate, (x + bw - 6 * s, y - 5 * s, 9 * s, 9 * s), border_radius=int(3 * s))
        pygame.draw.rect(surf, plate, (x - bw + 2 * s, y + 15 * s, bw * 2 - 4 * s, 5 * s), border_radius=2)
    elif st == "agile":
        pygame.draw.line(surf, (255, 255, 255), (x - bw + 2 * s, y + 17 * s), (x + bw - 2 * s, y + 17 * s), lw)
    pygame.draw.rect(surf, scale_color(col, 0.85), (x - bw + s, y + 24 * s, 8 * s * w, 12 * s), border_radius=3)
    pygame.draw.rect(surf, scale_color(col, 0.85), (x + bw - s - 8 * s * w, y + 24 * s, 8 * s * w, 12 * s), border_radius=3)
    arm = math.sin(t * 6) * 8 * s if wave else 0
    aw = max(2, int(6 * s * w))
    pygame.draw.line(surf, col, (x - bw, y + 2 * s), (x - bw - 6 * s, y + 16 * s), aw)
    pygame.draw.line(surf, col, (x + bw, y + 2 * s), (x + bw + 7 * s, y + 14 * s - arm), aw)
    hr = 13 * s * {"armored": 1.08, "agile": 0.95}.get(st, 1.0)
    pygame.draw.circle(surf, (240, 244, 255), (int(x), int(y - 14 * s)), int(hr))
    if st == "armored":
        pygame.draw.circle(surf, scale_color(col, 0.5), (int(x), int(y - 14 * s)), int(hr), lw)
    visor = pygame.Rect(0, 0, int(18 * s), int(12 * s))
    visor.center = (int(x + 2 * s), int(y - 14 * s))
    pygame.draw.ellipse(surf, (40, 80, 160) if not sick else (120, 160, 80), visor)
    pygame.draw.ellipse(surf, (180, 220, 255), (visor.x + 3 * s, visor.y + 2 * s, 6 * s, 4 * s))
    if tired:
        draw_text(surf, "z", (x + 14 * s, y - 34 * s - (t * 10) % 8), int(14 * s), C["text_dim"], True, shadow=False, raw=True)
    if sick:
        pygame.draw.circle(surf, C["red"], (int(x + 14 * s), int(y - 26 * s)), int(6 * s))
        pygame.draw.line(surf, C["white"], (x + 14 * s, y - 29 * s), (x + 14 * s, y - 23 * s), 2)
        pygame.draw.line(surf, C["white"], (x + 11 * s, y - 26 * s), (x + 17 * s, y - 26 * s), 2)


def draw_flag(surf, x, y, agency, color, t, scale=1.0):
    pole_h = 90 * scale
    pygame.draw.line(surf, (200, 205, 215), (x, y), (x, y - pole_h), max(2, int(3 * scale)))
    w, h = 110 * scale, 54 * scale
    pts_top, pts_bot = [], []
    for i in range(12):
        k = i / 11
        wave = math.sin(t * 4 + k * 5) * 6 * scale * k
        pts_top.append((x + k * w, y - pole_h + wave))
        pts_bot.append((x + k * w, y - pole_h + h + wave))
    poly = pts_top + pts_bot[::-1]
    pygame.draw.polygon(surf, tuple(color), poly)
    pygame.draw.polygon(surf, scale_color(tuple(color), 0.6), poly, 2)
    txt = render_text(agency.upper()[:12], max(10, int(13 * scale)), (10, 14, 30), True)
    surf.blit(txt, (x + w / 2 - txt.get_width() / 2, y - pole_h + h / 2 - txt.get_height() / 2 + math.sin(t * 4 + 2.5) * 3 * scale))

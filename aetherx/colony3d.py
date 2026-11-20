# -*- coding: utf-8 -*-
"""
KOZMOGENİS // 3B KOLONİ GÖRÜNÜMÜ
2B koloni sahnesinin yerini alan, yazılımla çizilen (numpy + pygame) 3B sahne.

Sahne hiyerarşisi (Unity/Godot karşılığı):
  Colony3D (yönetici)
   ├─ CameraRig        hedef pivotu + bom kolu + kamera: yakınlaştırma, 360° yörünge, eğim, kaydırma, odak/takip
   ├─ Terrain          yükseklik haritası (bina tabanlarında düzleştirilir), gezegene göre renk ve sis
   ├─ BuildingsContainer
   │    └─ Building    modüler 3B model + inşaat aşamaları (plan -> temel/iskele -> çerçeve -> tamam)
   ├─ ColonistsContainer
   │    └─ ColonistAgent   görsel ajan: A* yol bulma, kaçınma, yumuşak dönüş, animasyon durum makinesi
   ├─ Lighting         gece/gündüz güneşi, yarımküre ortam ışığı, gece pencere ve fener ışıkları
   └─ WorldUI          seçim halkası, kameraya dönük durum simgeleri ve can çubukları

Görsel katman simülasyondan ayrıdır: oyun mantığı (nüfus, binalar, mutluluk) game.py'de
kalır; bu modül yalnızca o veriyi okur ve kendi görsel durumunu (yerleşim, inşaat ilerlemesi)
koloni kaydının "layout3d" alanında tutar.

Geçiş planı: 1) kamera, 2) arazi + binalar, 3) kolonistler; 2B görünüm hâlâ bir düğmeyle açılabilir.
"""
import heapq
import math
import random

import numpy as np
import pygame

from . import cinema
from . import data as D
from . import i18n
from .config import C, CREW_COLORS
from .fx import draw_glow
from .ui import draw_bar, draw_text

F32 = np.float32
N = 20                       # ızgara boyutu (hücre)
HALF = N / 2
MIN_DIST, MAX_DIST = 7.0, 30.0

# bina ayak izi (genişlik x derinlik, hücre)
FOOT = {"house": (2, 2), "mine": (2, 2), "hut": (2, 2), "gym": (3, 2), "hospital": (3, 2), "school": (3, 2),
        "park": (3, 3)}

PALETTE = {  # zemin, zemin2, sis, gök ortamı, yer ortamı
    "moon": ((132, 130, 126), (98, 96, 94), (12, 12, 18), (70, 74, 90), (40, 38, 36)),
    "mars": ((178, 102, 62), (140, 76, 46), (196, 150, 108), (150, 120, 100), (90, 50, 30)),
    "venus": ((150, 104, 56), (112, 74, 40), (214, 160, 84), (170, 130, 80), (80, 54, 30)),
    "jupiter": ((188, 196, 204), (150, 160, 172), (30, 36, 52), (90, 100, 130), (60, 66, 80)),
}


# =========================================================================== yardımcılar
def _v(x, y, z):
    return np.array((x, y, z), F32)


def _norm(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else v


def _smooth(cur, target, k, dt):
    return cur + (target - cur) * (1 - math.exp(-k * dt))


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


class Mesh:
    """Yüz listesi: her yüz 3-4 köşe, renk, iç nokta (normal yönü için), çift yüz ve ışıma bayrakları."""

    def __init__(self):
        self.faces = []

    def quad(self, pts, col, inner, two=False, emit=0.0):
        self.faces.append((pts, col, inner, two, emit))

    def extend(self, other):
        self.faces.extend(other.faces)
        return self

    # ---- ilkel şekiller
    def box(self, cx, cz, y0, w, d, h, col, top=True, side_col=None):
        x0, x1, z0, z1, y1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2, y0 + h
        c = _v(cx, y0 + h / 2, cz)
        sc = side_col or col
        P = [_v(x0, y0, z0), _v(x1, y0, z0), _v(x1, y0, z1), _v(x0, y0, z1),
             _v(x0, y1, z0), _v(x1, y1, z0), _v(x1, y1, z1), _v(x0, y1, z1)]
        if top:
            self.quad([P[4], P[5], P[6], P[7]], col, c)
        self.quad([P[0], P[1], P[5], P[4]], sc, c)
        self.quad([P[1], P[2], P[6], P[5]], sc, c)
        self.quad([P[2], P[3], P[7], P[6]], sc, c)
        self.quad([P[3], P[0], P[4], P[7]], sc, c)
        return self

    def gable(self, cx, cz, y0, w, d, rise, col, along_x=True):
        x0, x1, z0, z1 = cx - w / 2, cx + w / 2, cz - d / 2, cz + d / 2
        c = _v(cx, y0, cz)
        if along_x:
            r0, r1 = _v(x0, y0 + rise, cz), _v(x1, y0 + rise, cz)
            self.quad([_v(x0, y0, z0), _v(x1, y0, z0), r1, r0], col, c)
            self.quad([_v(x1, y0, z1), _v(x0, y0, z1), r0, r1], col, c)
            self.quad([_v(x0, y0, z0), r0, _v(x0, y0, z1)], col, c)
            self.quad([_v(x1, y0, z1), r1, _v(x1, y0, z0)], col, c)
        else:
            r0, r1 = _v(cx, y0 + rise, z0), _v(cx, y0 + rise, z1)
            self.quad([_v(x0, y0, z0), _v(x0, y0, z1), r1, r0], col, c)
            self.quad([_v(x1, y0, z1), _v(x1, y0, z0), r0, r1], col, c)
            self.quad([_v(x0, y0, z0), r0, _v(x1, y0, z0)], col, c)
            self.quad([_v(x1, y0, z1), r1, _v(x0, y0, z1)], col, c)
        return self

    def dome(self, cx, cz, y0, r, col, seg=10, rings=4, window_ring=None, emit_col=None):
        c = _v(cx, y0 + r * 0.3, cz)
        for i in range(rings):
            a0, a1 = math.pi / 2 * i / rings, math.pi / 2 * (i + 1) / rings
            for j in range(seg):
                b0, b1 = math.tau * j / seg, math.tau * (j + 1) / seg
                p = lambda a, b: _v(cx + r * math.cos(a) * math.cos(b), y0 + r * math.sin(a), cz + r * math.cos(a) * math.sin(b))
                if i == rings - 1:
                    self.quad([p(a0, b0), p(a0, b1), _v(cx, y0 + r, cz)], col, c)
                else:
                    win = window_ring is not None and i == window_ring and j % 2 == 0
                    self.quad([p(a0, b0), p(a0, b1), p(a1, b1), p(a1, b0)], (60, 90, 130) if win else col, c,
                              emit=1.0 if win else 0.0)
        return self

    def cyl(self, cx, cz, y0, r, h, col, seg=8, cap=True):
        c = _v(cx, y0 + h / 2, cz)
        top = []
        for j in range(seg):
            b0, b1 = math.tau * j / seg, math.tau * (j + 1) / seg
            p0 = (cx + r * math.cos(b0), cz + r * math.sin(b0))
            p1 = (cx + r * math.cos(b1), cz + r * math.sin(b1))
            self.quad([_v(p0[0], y0, p0[1]), _v(p1[0], y0, p1[1]), _v(p1[0], y0 + h, p1[1]), _v(p0[0], y0 + h, p0[1])], col, c)
            top.append(_v(p0[0], y0 + h, p0[1]))
        if cap:
            for j in range(0, seg - 2, 2):
                self.quad([top[0], top[j + 1], top[j + 2], top[min(seg - 1, j + 3)]], col, c)
        return self

    def cone(self, cx, cz, y0, r, h, col, seg=7):
        c = _v(cx, y0 + h * 0.3, cz)
        tip = _v(cx, y0 + h, cz)
        for j in range(seg):
            b0, b1 = math.tau * j / seg, math.tau * (j + 1) / seg
            self.quad([_v(cx + r * math.cos(b0), y0, cz + r * math.sin(b0)), _v(cx + r * math.cos(b1), y0, cz + r * math.sin(b1)), tip],
                      col, c)
        return self

    def panel(self, pts, col, emit=0.0):
        """İnce düzlem (pencere, tabela, bayrak): çift yüzlü."""
        c = sum(pts) / len(pts)
        self.quad(pts, col, c - _v(0, 0.001, 0), two=True, emit=emit)
        return self

    def transformed(self, cx, cz, rot, y_off=0.0):
        """Merkez etrafında 90° adımlarla döndür."""
        a = rot * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)

        def tf(p):
            x, z = p[0] - cx, p[2] - cz
            return _v(cx + x * ca - z * sa, p[1] + y_off, cz + x * sa + z * ca)
        m = Mesh()
        for pts, col, inner, two, emit in self.faces:
            m.faces.append(([tf(p) for p in pts], col, tf(inner), two, emit))
        return m


# =========================================================================== modüler binalar
def building_mesh(key, cx, cz, y, w, d, planet, seed=0):
    """Modüler parçalardan bina: gövde + çatı varyantı + baca/anten + pencereler + çevre eşyaları."""
    r = random.Random(seed)
    m = Mesh()
    lights = []                      # (x, y, z, renk) gece ışığı
    wall = {"moon": (210, 214, 222), "mars": (226, 220, 210), "venus": (200, 196, 186), "jupiter": (220, 226, 236)}[planet]
    trim = (70, 80, 96)
    # temel plaka (araziye oturtma)
    m.box(cx, cz, y - 0.25, w * 0.96, d * 0.96, 0.3, (110, 112, 118), side_col=(88, 90, 96))
    yb = y + 0.05
    if key == "house":               # yaşam kubbesi + giriş tüneli
        m.dome(cx, cz, yb, min(w, d) * 0.42, wall, seg=12, rings=4, window_ring=1)
        m.box(cx, cz + d * 0.42, yb, 0.5, 0.5, 0.45, wall, side_col=(196, 200, 208))
        m.panel([_v(cx - 0.16, yb, cz + d * 0.67 + 0.01), _v(cx + 0.16, yb, cz + d * 0.67 + 0.01),
                 _v(cx + 0.16, yb + 0.34, cz + d * 0.67 + 0.01), _v(cx - 0.16, yb + 0.34, cz + d * 0.67 + 0.01)], (60, 90, 130), emit=1.0)
        lights.append((cx, yb + 0.3, cz + d * 0.7, (255, 200, 130)))
        m.cyl(cx + w * 0.3, cz - d * 0.3, yb, 0.06, 0.9, (150, 150, 160), seg=5)        # anten
    elif key == "mine":              # madencilik kulesi + konveyör
        m.box(cx, cz, yb, w * 0.7, d * 0.7, 0.7, (170, 150, 120), side_col=(150, 130, 104))
        for sx in (-1, 1):
            for sz in (-1, 1):
                m.box(cx + sx * 0.32, cz + sz * 0.32, yb + 0.7, 0.07, 0.07, 1.3, (90, 90, 96))
        m.gable(cx, cz, yb + 2.0, 0.85, 0.85, 0.35, (200, 120, 50))
        m.box(cx + w * 0.35, cz, yb, 0.9, 0.22, 0.18, (80, 80, 86))                       # konveyör
        for i in range(3):
            m.box(cx - w * 0.38, cz - d * 0.2 + i * 0.25, yb, 0.2, 0.2, 0.2 + i * 0.06, (140, 96, 60))  # cevher yığını
        lights.append((cx, yb + 2.2, cz, (255, 170, 80)))
    elif key == "hut":               # araştırma kulübesi + çanak anten
        m.box(cx, cz, yb, w * 0.72, d * 0.6, 0.75, wall, side_col=(200, 206, 214))
        m.gable(cx, cz, yb + 0.75, w * 0.78, d * 0.66, 0.35, (70, 120, 190))
        for i in (-1, 1):
            m.panel([_v(cx + i * 0.3 - 0.13, yb + 0.3, cz + d * 0.3 + 0.01), _v(cx + i * 0.3 + 0.13, yb + 0.3, cz + d * 0.3 + 0.01),
                     _v(cx + i * 0.3 + 0.13, yb + 0.55, cz + d * 0.3 + 0.01), _v(cx + i * 0.3 - 0.13, yb + 0.55, cz + d * 0.3 + 0.01)],
                    (60, 90, 130), emit=1.0)
        m.cyl(cx - w * 0.3, cz - d * 0.3, yb, 0.05, 0.9, (150, 150, 160), seg=5)
        m.dome(cx - w * 0.3, cz - d * 0.3, yb + 0.9, 0.28, (212, 214, 218), seg=8, rings=2)
        lights.append((cx, yb + 0.5, cz + d * 0.36, (150, 210, 255)))
    elif key == "hospital":          # beyaz blok + kırmızı haç
        m.box(cx, cz, yb, w * 0.8, d * 0.72, 0.95, (240, 242, 246), side_col=(224, 228, 234))
        m.box(cx, cz, yb + 0.95, w * 0.82, d * 0.74, 0.08, (180, 186, 196))
        fz = cz + d * 0.36 + 0.01
        m.panel([_v(cx - 0.08, yb + 0.35, fz), _v(cx + 0.08, yb + 0.35, fz), _v(cx + 0.08, yb + 0.8, fz), _v(cx - 0.08, yb + 0.8, fz)],
                (220, 40, 50))
        m.panel([_v(cx - 0.23, yb + 0.5, fz), _v(cx + 0.23, yb + 0.5, fz), _v(cx + 0.23, yb + 0.65, fz), _v(cx - 0.23, yb + 0.65, fz)],
                (220, 40, 50))
        for i in (-2, -1, 1, 2):
            m.panel([_v(cx + i * 0.38 - 0.1, yb + 0.45, fz), _v(cx + i * 0.38 + 0.1, yb + 0.45, fz),
                     _v(cx + i * 0.38 + 0.1, yb + 0.7, fz), _v(cx + i * 0.38 - 0.1, yb + 0.7, fz)], (60, 90, 130), emit=1.0)
        lights.append((cx, yb + 1.0, cz + d * 0.4, (255, 230, 220)))
    elif key == "school":            # beşik çatılı okul + bayrak direği
        m.box(cx, cz, yb, w * 0.8, d * 0.66, 0.8, (236, 214, 170), side_col=(220, 196, 150))
        m.gable(cx, cz, yb + 0.8, w * 0.86, d * 0.72, 0.5, (180, 70, 60))
        m.box(cx + w * 0.25, cz - d * 0.1, yb + 0.9, 0.16, 0.16, 0.55, (150, 80, 70))     # baca
        fz = cz + d * 0.33 + 0.01
        for i in (-1, 0, 1):
            m.panel([_v(cx + i * 0.5 - 0.13, yb + 0.3, fz), _v(cx + i * 0.5 + 0.13, yb + 0.3, fz),
                     _v(cx + i * 0.5 + 0.13, yb + 0.6, fz), _v(cx + i * 0.5 - 0.13, yb + 0.6, fz)], (60, 90, 130), emit=1.0)
        m.cyl(cx - w * 0.45, cz + d * 0.4, yb, 0.03, 1.6, (200, 200, 210), seg=4, cap=False)
        m.panel([_v(cx - w * 0.45, yb + 1.3, cz + d * 0.4), _v(cx - w * 0.45 + 0.5, yb + 1.33, cz + d * 0.4),
                 _v(cx - w * 0.45 + 0.5, yb + 1.6, cz + d * 0.4), _v(cx - w * 0.45, yb + 1.6, cz + d * 0.4)], (70, 200, 230))
        lights.append((cx, yb + 0.5, cz + d * 0.38, (255, 210, 140)))
    elif key == "gym":               # cam çatılı uzun salon
        m.box(cx, cz, yb, w * 0.84, d * 0.62, 0.7, (200, 206, 220), side_col=(180, 188, 204))
        m.gable(cx, cz, yb + 0.7, w * 0.88, d * 0.66, 0.3, (110, 170, 220))
        fz = cz + d * 0.31 + 0.01
        m.panel([_v(cx - w * 0.36, yb + 0.25, fz), _v(cx + w * 0.36, yb + 0.25, fz), _v(cx + w * 0.36, yb + 0.55, fz),
                 _v(cx - w * 0.36, yb + 0.55, fz)], (60, 90, 130), emit=1.0)
        lights.append((cx, yb + 0.6, cz + d * 0.34, (255, 140, 180)))
    elif key == "park":              # basınçlı sera parkı: çim, ağaçlar, bank
        m.box(cx, cz, yb, w * 0.92, d * 0.92, 0.06, (70, 150, 80), side_col=(60, 120, 64))
        for i in range(6):
            tx, tz = cx + r.uniform(-w * 0.35, w * 0.35), cz + r.uniform(-d * 0.35, d * 0.35)
            m.cyl(tx, tz, yb + 0.06, 0.05, 0.3, (110, 80, 50), seg=4, cap=False)
            m.cone(tx, tz, yb + 0.3, r.uniform(0.22, 0.32), r.uniform(0.6, 0.9), (50 + r.randint(0, 30), 140 + r.randint(0, 40), 70))
        m.box(cx, cz + d * 0.3, yb + 0.06, 0.6, 0.15, 0.14, (140, 100, 60))
        lights.append((cx + w * 0.4, yb + 0.7, cz + d * 0.4, (255, 220, 150)))
        m.cyl(cx + w * 0.4, cz + d * 0.4, yb, 0.03, 0.7, (60, 60, 70), seg=4, cap=False)       # fener direği
    # çevre eşyaları: varil, sandık, fener
    for _ in range(2):
        side = r.choice((-1, 1))
        px, pz = cx + side * (w * 0.5 + 0.15), cz + r.uniform(-d * 0.35, d * 0.35)
        if r.random() < 0.5:
            m.cyl(px, pz, y, 0.1, 0.24, (70 + r.randint(0, 40), 90, 120), seg=6)
        else:
            m.box(px, pz, y, 0.22, 0.22, 0.22, (150, 110, 70), side_col=(130, 94, 58))
    return m, lights


def colonist_mesh(x, y, z, heading, col, phase, state, carry):
    """Basit insan modeli; durum makinesine göre bacak/kol salınımı ve taşıma."""
    swing = 0.0
    arm = 0.0
    if state in ("walk", "carry"):
        swing = math.sin(phase * 9) * 0.5
        arm = -swing
    elif state == "work":
        arm = -1.1 + math.sin(phase * 7) * 0.9
    if carry:
        arm = -1.3
    parts = _colonist_local(swing, arm, col, carry)
    m = Mesh()
    ca, sa = math.cos(heading), math.sin(heading)
    for pts, cc, inner, two, emit in parts.faces:
        def tf(p):
            return _v(x + p[0] * ca + p[2] * sa, y + p[1], z - p[0] * sa + p[2] * ca)
        m.faces.append(([tf(p) for p in pts], cc, tf(inner), two, emit))
    return m


def _colonist_local(swing, arm, col, carry):
    """Kolonist modeli yerel uzayda (orijinde, yönsüz)."""
    s = 0.34
    suit = (236, 238, 244)

    def limb(ox, oy, oz, w, h, d, ang, c):
        # pivot (ox, oy+h, oz) etrafında x ekseninde dönen uzuv
        mm = Mesh().box(ox, oz, oy, w, d, h, c)
        ca, sa = math.cos(ang), math.sin(ang)
        py, pz = oy + h, oz
        out = Mesh()
        for pts, cc, inner, two, emit in mm.faces:
            def rt(p):
                yy, zz = p[1] - py, p[2] - pz
                return _v(p[0], py + yy * ca - zz * sa, pz + yy * sa + zz * ca)
            out.faces.append(([rt(p) for p in pts], cc, rt(inner), two, emit))
        return out
    parts = Mesh()
    parts.extend(limb(-0.07 * s * 3, 0, 0, 0.1 * s * 3, 0.32 * s * 3, 0.1 * s * 3, swing, suit))
    parts.extend(limb(0.07 * s * 3, 0, 0, 0.1 * s * 3, 0.32 * s * 3, 0.1 * s * 3, -swing, suit))
    parts.box(0, 0, 0.32 * s * 3, 0.3 * s * 3, 0.18 * s * 3, 0.34 * s * 3, col)                     # gövde (rol rengi)
    parts.box(0, -0.13 * s * 3, 0.36 * s * 3, 0.22 * s * 3, 0.1 * s * 3, 0.26 * s * 3, (180, 184, 196))   # sırt çantası
    parts.box(0, 0, 0.68 * s * 3, 0.24 * s * 3, 0.24 * s * 3, 0.22 * s * 3, suit)                    # kask
    parts.panel([_v(-0.09 * s * 3, 0.72 * s * 3, 0.125 * s * 3), _v(0.09 * s * 3, 0.72 * s * 3, 0.125 * s * 3),
                 _v(0.09 * s * 3, 0.85 * s * 3, 0.125 * s * 3), _v(-0.09 * s * 3, 0.85 * s * 3, 0.125 * s * 3)], (40, 70, 140))
    parts.extend(limb(-0.2 * s * 3, 0.36 * s * 3, 0, 0.08 * s * 3, 0.3 * s * 3, 0.08 * s * 3, arm, suit))
    parts.extend(limb(0.2 * s * 3, 0.36 * s * 3, 0, 0.08 * s * 3, 0.3 * s * 3, 0.08 * s * 3, arm if carry else -arm, suit))
    if carry:
        parts.box(0, 0.26 * s * 3, 0.62 * s * 3, 0.3 * s * 3, 0.22 * s * 3, 0.22 * s * 3, (160, 112, 66), side_col=(140, 96, 56))
    return parts


# =========================================================================== paketleme (optimizasyon)
_PACK = {}


def pack_faces(faces):
    """Yüz listesini numpy dizilerine çevirir ve normal/merkezleri bir kez hesaplar.
    Döngüsüz tek dönüşüm: eskiden her karede her yüz için ayrı ayrı atama yapılıyordu."""
    nv = 4
    n_f = len(faces)
    if n_f == 0:
        return None
    padded, cols, inner, two, emit, cnt = [], [], [], [], [], []
    for pts, col, inn, tw, em in faces:
        k = len(pts)
        cnt.append(k)
        padded.append(list(pts) + [pts[-1]] * (nv - k) if k < nv else pts)
        cols.append(col)
        inner.append(inn)
        two.append(tw)
        emit.append(em)
    P = np.array(padded, F32)
    pk = {"P": P, "cols": np.array(cols, F32), "inner": np.array(inner, F32), "two": np.array(two, bool),
          "emit": np.array(emit, F32), "cnt": np.array(cnt, np.int32)}
    _normals(pk)
    return pk


def _normals(pk):
    P = pk["P"]
    cen = P.mean(1)
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ln = np.linalg.norm(n, axis=1)
    n = n / np.maximum(ln, 1e-9)[:, None]
    n[((cen - pk["inner"]) * n).sum(1) < 0] *= -1
    pk["cen"], pk["n"], pk["ln"] = cen, n, ln


def pack_cached(faces):
    """Durağan yüz listeleri (arazi, binalar) için paket önbelleği: liste kimliğiyle."""
    hit = _PACK.get(id(faces))
    if hit is not None and hit[0] is faces:
        return hit[1]
    pk = pack_faces(faces)
    if len(_PACK) > 24:
        _PACK.clear()
    _PACK[id(faces)] = (faces, pk)
    return pk


def concat_packs(packs):
    packs = [p for p in packs if p is not None]
    if not packs:
        return None
    if len(packs) == 1:
        return packs[0]
    return {k: np.concatenate([p[k] for p in packs]) for k in packs[0]}


_COLONIST = {}


def colonist_packed(x, y, z, heading, col, phase, state, carry):
    """colonist_mesh ile aynı model; poz (uzuv açıları ~0,04 rad adımla) başına bir kez kurulur,
    sonra yalnızca vektörel döndürme + öteleme yapılır."""
    swing = arm = 0.0
    if state in ("walk", "carry"):
        swing = math.sin(phase * 9) * 0.5
        arm = -swing
    elif state == "work":
        arm = -1.1 + math.sin(phase * 7) * 0.9
    if carry:
        arm = -1.3
    q = 0.04
    key = (tuple(col), round(swing / q), round(arm / q), bool(carry))
    loc = _COLONIST.get(key)
    if loc is None:
        loc = pack_faces(_colonist_local(round(swing / q) * q, round(arm / q) * q, col, carry).faces)
        if len(_COLONIST) > 800:
            _COLONIST.clear()
        _COLONIST[key] = loc
    ca, sa = math.cos(heading), math.sin(heading)
    R = np.array(((ca, 0, -sa), (0, 1, 0), (sa, 0, ca)), F32)      # satır vektörü @ R
    t = np.array((x, y, z), F32)
    out = dict(loc)
    out["P"] = loc["P"] @ R + t
    out["inner"] = loc["inner"] @ R + t
    out["cen"] = loc["cen"] @ R + t
    out["n"] = loc["n"] @ R
    return out


# =========================================================================== kamera
class CameraRig:
    """Hedef pivotu + bom kolu + kamera; tüm değerler yumuşak sönümle izlenir."""

    def __init__(self):
        self.tx, self.tz = 0.0, 0.0
        self.yaw, self.pitch_base, self.dist = 0.6, 33.0, 15.0
        self.g = {"tx": 0.0, "tz": 0.0, "yaw": 0.6, "pitch_base": 33.0, "dist": 15.0}
        self.follow = None
        self.drag = None
        self.edge_pan = True

    @property
    def pitch(self):
        # yakınlaştıkça kamera ufka doğru eğilir (otomatik eğim), 20°–80° arasında sınırlı
        zn = (self.dist - MIN_DIST) / (MAX_DIST - MIN_DIST)
        return max(20.0, min(80.0, self.pitch_base + (zn - 0.5) * 22))

    def zoom(self, steps):
        self.g["dist"] = max(MIN_DIST, min(MAX_DIST, self.g["dist"] * (0.88 ** steps)))

    def orbit(self, dx, dy):
        self.g["yaw"] += dx * 0.006
        self.g["pitch_base"] = max(20.0, min(80.0, self.g["pitch_base"] - dy * 0.25))

    def pan(self, fwd, right, dt):
        if fwd or right:
            self.follow = None                         # elle kaydırınca takip biter
            spd = self.dist * 0.85 * dt               # yüksekliğe göre ölçeklenen hız
            sy, cy = math.sin(self.yaw), math.cos(self.yaw)
            self.g["tx"] += (-sy * fwd + cy * right) * spd
            self.g["tz"] += (-cy * fwd - sy * right) * spd
            self.clamp()

    def focus(self, x, z, dist=None):
        self.g["tx"], self.g["tz"] = x, z
        if dist:
            self.g["dist"] = dist
        self.clamp()

    def clamp(self):
        self.g["tx"] = max(-HALF, min(HALF, self.g["tx"]))
        self.g["tz"] = max(-HALF, min(HALF, self.g["tz"]))

    def update(self, dt):
        if self.follow is not None:
            self.g["tx"], self.g["tz"] = self.follow.x, self.follow.z
        for k, rate in (("tx", 9), ("tz", 9), ("yaw", 10), ("pitch_base", 10), ("dist", 8)):
            setattr(self, k, _smooth(getattr(self, k), self.g[k], rate, dt))

    def basis(self, ty):
        p, y = math.radians(self.pitch), self.yaw
        T = _v(self.tx, ty, self.tz)
        eye = T + _v(math.cos(p) * math.sin(y), math.sin(p), math.cos(p) * math.cos(y)) * self.dist
        f = _norm(T - eye)
        r = _norm(np.cross(f, _v(0, 1, 0)))
        u = np.cross(r, f)
        return eye, f, r, u


# =========================================================================== kolonist ajanı
class ColonistAgent:
    """Görsel ajan (simülasyondan bağımsız): görev döngüsü, A* yol, kaçınma, yumuşak dönüş."""

    def __init__(self, world, idx, role):
        self.w = world
        self.idx = idx
        self.role = role
        self.col = CREW_COLORS.get(role, (200, 200, 210))
        cell = world.random_free_cell()
        self.x, self.z = world.cell_center(*cell)
        self.heading = random.uniform(0, math.tau)
        self.state = "idle"
        self.timer = random.uniform(0.5, 2.5)
        self.path = []
        self.phase = random.uniform(0, 9)
        self.carry = False
        self.goal = None
        self.hidden = False
        self.screen = None

    def plan(self, target_cell):
        start = self.w.world_to_cell(self.x, self.z)
        self.path = self.w.astar(start, target_cell)
        return bool(self.path)

    def update(self, dt, night):
        self.phase += dt
        if night and self.state not in ("sleep", "walk_home"):
            home = self.w.door_of("house")
            if home and self.plan(home):
                self.state, self.carry = "walk_home", False
            else:
                self.state, self.hidden = "sleep", False
        if not night and self.state == "sleep":
            self.state, self.hidden, self.timer = "idle", False, random.uniform(0.3, 1.5)
        if self.state in ("walk", "carry", "walk_home"):
            if not self.path:
                if self.state == "walk_home":
                    self.state, self.hidden = "sleep", True
                elif self.state == "walk":
                    self.state, self.timer = "work", random.uniform(3.0, 5.0)
                else:
                    self.state, self.carry, self.timer = "idle", False, random.uniform(1.0, 2.5)
                return
            tx, tz = self.w.cell_center(*self.path[0])
            dx, dz = tx - self.x, tz - self.z
            dist = math.hypot(dx, dz)
            if dist < 0.12:
                self.path.pop(0)
                return
            vx, vz = dx / dist, dz / dist
            # basit kaçınma: diğer ajanlardan uzaklaş
            for o in self.w.agents:
                if o is self or o.hidden:
                    continue
                ox, oz = self.x - o.x, self.z - o.z
                d2 = ox * ox + oz * oz
                if 1e-6 < d2 < 0.16:
                    vx += ox / d2 * 0.04
                    vz += oz / d2 * 0.04
            n = math.hypot(vx, vz) or 1.0
            spd = 1.25 if self.state != "carry" else 0.95
            self.x += vx / n * spd * dt
            self.z += vz / n * spd * dt
            want = math.atan2(vx, vz)
            diff = (want - self.heading + math.pi) % math.tau - math.pi
            self.heading += max(-6.0 * dt, min(6.0 * dt, diff))           # RotateTowards
        elif self.state in ("idle", "work"):
            self.timer -= dt
            if self.timer <= 0:
                if self.state == "work":
                    dest = self.w.door_of(random.choice(("house", "hut")))
                    if dest and self.plan(dest):
                        self.state, self.carry = "carry", True
                    else:
                        self.state, self.timer = "idle", 1.0
                else:
                    dest = self.w.door_of(random.choice(("mine", "mine", "hut", "park", "gym")))
                    if dest and self.plan(dest):
                        self.state = "walk"
                    else:
                        cell = self.w.random_free_cell()
                        if self.plan(cell):
                            self.state = "walk"
                        else:
                            self.timer = 1.0

    def label(self):
        return {"idle": "Boşta", "walk": "Yürüyor", "walk_home": "Yürüyor", "work": "Çalışıyor", "carry": "Taşıyor",
                "sleep": "Uyuyor"}[self.state]


# =========================================================================== dünya
class Colony3D:
    def __init__(self, scene):
        self.scene = scene
        self.cam = CameraRig()
        self.planet = None
        self.colony = None
        self.agents = []
        self.selected = None
        self.place = None            # yerleştirme modu: {"key", "rot", "cell", "valid"}
        self.t = 0.0
        self.static = None
        self.static_sig = None
        self.lights = []
        self.blocked = set()
        self.doors = {}
        self.heights = None
        self.view = None
        self.mouse_world = None
        self._layer = None

    # ---------------------------------------------------------------- kurulum
    def setup(self, planet, colony, game):
        self.planet, self.colony, self.game = planet, colony, game
        rng = np.random.default_rng(sum(map(ord, planet)) * 7)
        base = rng.random((6, 6)).astype(F32)
        xs = np.linspace(0, 5, N + 1)
        hm = np.array([[np.interp(x, np.arange(6), base[int(min(5, y))]) for x in xs] for y in xs], F32)
        fine = rng.random((N + 1, N + 1)).astype(F32)
        self.base_heights = (hm - 0.5) * 1.1 + (fine - 0.5) * 0.12
        self.sync_layout()
        self.spawn_agents()
        if self.selected not in self.agents:
            self.selected = None
        self.cam.follow = None

    def layout(self):
        return self.colony.setdefault("layout3d", [])

    def sync_layout(self):
        """Simülasyondaki bina sayılarıyla görsel yerleşimi eşleştir (eksikleri otomatik yerleştir)."""
        lay = self.layout()
        counts = {}
        for e in lay:
            counts[e["key"]] = counts.get(e["key"], 0) + 1
        self.rebuild_grid()
        for b in D.COLONY_BUILDINGS:
            k = b["key"]
            need = self.colony["buildings"].get(k, 0) - counts.get(k, 0)
            for _ in range(max(0, need)):
                spot = self.auto_spot(k)
                if spot is None:
                    break
                lay.append({"key": k, "gx": spot[0], "gz": spot[1], "rot": spot[2], "prog": 1.0})
                self.rebuild_grid()
        # fazla kayıt (ör. kayıt dosyası değiştiyse) temizle
        for b in D.COLONY_BUILDINGS:
            k = b["key"]
            have = [e for e in lay if e["key"] == k]
            while len(have) > self.colony["buildings"].get(k, 0):
                lay.remove(have.pop())
        self.rebuild_grid()
        self.static_sig = None

    def foot(self, key, rot):
        w, d = FOOT[key]
        return (d, w) if rot % 2 else (w, d)

    def cells_of(self, key, gx, gz, rot):
        w, d = self.foot(key, rot)
        return [(gx + i, gz + j) for i in range(w) for j in range(d)]

    def rebuild_grid(self):
        self.blocked = set()
        self.doors = {}
        h = self.base_heights.copy()
        for e in self.layout():
            cells = self.cells_of(e["key"], e["gx"], e["gz"], e["rot"])
            self.blocked.update(cells)
            w, d = self.foot(e["key"], e["rot"])
            # araziye hizalama: ayak izi köşelerinin ortalamasına düzleştir
            xs, zs = range(e["gx"], e["gx"] + w + 1), range(e["gz"], e["gz"] + d + 1)
            pad = float(np.mean([h[z, x] for x in xs for z in zs]))
            e["pad"] = pad
            for x in xs:
                for z in zs:
                    h[z, x] = pad
            door = (e["gx"] + w // 2, e["gz"] + d)            # ön kapı hücresi
            self.doors.setdefault(e["key"], []).append(door)
        self.heights = h

    def free(self, cells, margin=True):
        for (x, z) in cells:
            if not (1 <= x < N - 1 and 1 <= z < N - 1) or (x, z) in self.blocked:
                return False
        if margin:
            for (x, z) in cells:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (x + dx, z + dz) in self.blocked:
                        return False
        return True

    def auto_spot(self, key):
        order = sorted(((x, z) for x in range(2, N - 3) for z in range(2, N - 3)),
                       key=lambda c: (abs(c[0] - HALF + 1) + abs(c[1] - HALF + 1), c))
        for (x, z) in order:
            for rot in (0, 1):
                if self.free(self.cells_of(key, x, z, rot)):
                    return (x, z, rot)
        return None

    def spawn_agents(self):
        n = max(1, min(12, int(self.colony["pop"])))
        roles = list(CREW_COLORS.keys())
        while len(self.agents) > n:
            self.agents.pop()
        for i in range(len(self.agents), n):
            self.agents.append(ColonistAgent(self, i, roles[i % len(roles)]))
        for a in self.agents:
            a.w = self

    # ---------------------------------------------------------------- ızgara yardımcıları
    def cell_center(self, x, z):
        return x - HALF + 0.5, z - HALF + 0.5

    def world_to_cell(self, x, z):
        return int(max(0, min(N - 1, math.floor(x + HALF)))), int(max(0, min(N - 1, math.floor(z + HALF))))

    def height(self, x, z):
        fx, fz = max(0.0, min(N - 0.001, x + HALF)), max(0.0, min(N - 0.001, z + HALF))
        i, j = int(fx), int(fz)
        ax, az = fx - i, fz - j
        h = self.heights
        return float((h[j, i] * (1 - ax) + h[j, i + 1] * ax) * (1 - az) + (h[j + 1, i] * (1 - ax) + h[j + 1, i + 1] * ax) * az)

    def heights_at(self, x, z):
        fx = np.clip(x + HALF, 0, N - 0.001)
        fz = np.clip(z + HALF, 0, N - 0.001)
        i, j = fx.astype(np.int32), fz.astype(np.int32)
        ax, az = fx - i, fz - j
        h = self.heights
        return (h[j, i] * (1 - ax) + h[j, i + 1] * ax) * (1 - az) + (h[j + 1, i] * (1 - ax) + h[j + 1, i + 1] * ax) * az

    def random_free_cell(self):
        for _ in range(60):
            c = (random.randint(1, N - 2), random.randint(1, N - 2))
            if c not in self.blocked:
                return c
        return (1, 1)

    def door_of(self, key):
        ds = self.doors.get(key)
        if not ds:
            return None
        d = random.choice(ds)
        return (min(N - 1, d[0]), min(N - 1, d[1]))

    def astar(self, start, goal):
        """4 komşulu A* (bina hücreleri engel)."""
        if goal in self.blocked:
            return []
        openh = [(0, start)]
        came, gs = {start: None}, {start: 0}
        while openh:
            _, cur = heapq.heappop(openh)
            if cur == goal:
                path = []
                while cur is not None and cur != start:
                    path.append(cur)
                    cur = came[cur]
                return path[::-1]
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (cur[0] + dx, cur[1] + dz)
                if not (0 <= nb[0] < N and 0 <= nb[1] < N) or nb in self.blocked:
                    continue
                ng = gs[cur] + 1
                if ng < gs.get(nb, 1e9):
                    gs[nb] = ng
                    came[nb] = cur
                    heapq.heappush(openh, (ng + abs(nb[0] - goal[0]) + abs(nb[1] - goal[1]), nb))
            if len(gs) > 600:
                break
        return []

    # ---------------------------------------------------------------- zaman / ışık
    def hour(self):
        return (self.game.s["clock"]["minutes"] / 60.0) % 24

    def lighting(self):
        h = self.hour()
        ang = (h - 6) / 12 * math.pi                      # 6:00 doğuş, 18:00 batış
        elev = math.sin(ang)
        day = max(0.0, min(1.0, elev * 3 + 0.15))
        sun = _norm(_v(math.cos(ang) * 0.8, max(0.08, elev), 0.45))
        warm = max(0.0, 1 - abs(elev) * 3)                # şafak/gün batımı
        sun_col = np.array((1.0, 0.96 - 0.25 * warm, 0.9 - 0.45 * warm), F32) * (1.15 * day)
        pal = PALETTE[self.planet]
        night_amb = np.array((0.10, 0.12, 0.2), F32)
        sky = np.array(pal[3], F32) / 255 * (0.35 + 0.5 * day) + night_amb * (1 - day)
        gnd = np.array(pal[4], F32) / 255 * (0.3 + 0.4 * day) + night_amb * 0.5 * (1 - day)
        return sun, sun_col, sky, gnd, day

    # ---------------------------------------------------------------- girdi
    def handle(self, e, rect):
        inside = rect.collidepoint(e.pos) if hasattr(e, "pos") else True
        if e.type == pygame.MOUSEWHEEL and rect.collidepoint(pygame.mouse.get_pos()):
            self.cam.zoom(e.y)
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and inside:
            if e.button in (2, 3):
                if self.place and e.button == 3:
                    self.place = None
                    return True
                self.cam.drag = e.pos
                return True
            if e.button == 1:
                if self.place:
                    return self.confirm_place()
                self.pick(e.pos)
                return True
        if e.type == pygame.MOUSEBUTTONUP and e.button in (2, 3):
            self.cam.drag = None
        if e.type == pygame.MOUSEMOTION and self.cam.drag:
            dx, dy = e.pos[0] - self.cam.drag[0], e.pos[1] - self.cam.drag[1]
            self.cam.orbit(dx, dy)
            self.cam.drag = e.pos
            return True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r and self.place:
                self.place["rot"] = (self.place["rot"] + 1) % 4
                return True
            if e.key == pygame.K_ESCAPE and self.place:
                self.place = None
                return True
            if e.key == pygame.K_f:
                if self.selected:
                    self.cam.follow = self.selected
                    self.cam.g["dist"] = min(self.cam.g["dist"], 11.0)
                else:
                    self.cam.focus(0.0, 0.0)
                return True
        return False

    def start_place(self, key):
        self.place = {"key": key, "rot": 0, "cell": None, "valid": False}

    def confirm_place(self):
        p = self.place
        if not p or not p["valid"]:
            self.scene.app.audio.play("deny")
            return True
        key, (gx, gz), rot = p["key"], p["cell"], p["rot"]
        ok = self.scene.act(self.game.colony_build, self.planet, key, ok_sound="clunk")
        if ok:
            self.layout().append({"key": key, "gx": gx, "gz": gz, "rot": rot, "prog": 0.0})
            self.rebuild_grid()
            self.static_sig = None
            self.place = None
            self.scene.rebuild()
        return True

    def pick(self, pos):
        best, bd = None, 26.0
        for a in self.agents:
            if a.hidden or a.screen is None:
                continue
            d = math.hypot(a.screen[0] - pos[0], a.screen[1] - pos[1])
            if d < bd:
                best, bd = a, d
        self.selected = best
        if best:
            self.cam.follow = best
            self.scene.app.audio.play("tick")
        elif self.mouse_world:
            cx, cz = self.world_to_cell(*self.mouse_world)
            for e in self.layout():
                if (cx, cz) in self.cells_of(e["key"], e["gx"], e["gz"], e["rot"]):
                    w, d = self.foot(e["key"], e["rot"])
                    self.cam.focus(e["gx"] - HALF + w / 2, e["gz"] - HALF + d / 2, min(self.cam.g["dist"], 12.0))
                    self.scene.app.audio.play("tick")
                    break

    # ---------------------------------------------------------------- güncelleme
    def update(self, dt, rect):
        self.t += dt
        keys = pygame.key.get_pressed()
        fwd = (1 if keys[pygame.K_w] or keys[pygame.K_UP] else 0) - (1 if keys[pygame.K_s] or keys[pygame.K_DOWN] else 0)
        right = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
        mx, my = pygame.mouse.get_pos()
        if self.cam.edge_pan and rect.collidepoint((mx, my)) and not self.cam.drag:
            if mx < rect.x + 10:
                right -= 1
            elif mx > rect.right - 10:
                right += 1
            if my < rect.y + 10:
                fwd += 1
            elif my > rect.bottom - 10:
                fwd -= 1
        self.cam.pan(fwd, right, dt)
        if keys[pygame.K_q]:
            self.cam.g["yaw"] -= 1.6 * dt
        if keys[pygame.K_e]:
            self.cam.g["yaw"] += 1.6 * dt
        self.cam.update(dt)
        # inşaat ilerlemesi (görsel)
        changed = False
        for e in self.layout():
            if e.get("prog", 1.0) < 1.0:
                e["prog"] = min(1.0, e.get("prog", 0.0) + dt / 9.0)
                changed = True
        if changed:
            self.static_sig = None
        night = self.lighting()[4] < 0.25
        for a in self.agents:
            a.update(dt, night)

    # ---------------------------------------------------------------- geometri
    def static_mesh(self):
        """Arazi + tamamlanmış binalar (önbellekli)."""
        sig = tuple((e["key"], e["gx"], e["gz"], e["rot"], round(e.get("prog", 1.0), 2)) for e in self.layout())
        if sig == self.static_sig and self.static is not None:
            return self.static
        terrain, objects, lights, construct = Mesh(), Mesh(), [], []
        pal = PALETTE[self.planet]
        rng = random.Random(7)
        h = self.heights
        for z in range(N):
            for x in range(N):
                x0, z0 = x - HALF, z - HALF
                k = rng.random()
                base = np.array(pal[0], F32) * (1 - k * 0.25) + np.array(pal[1], F32) * k * 0.25
                if (x, z) in self.blocked:
                    base = base * 0.9
                col = tuple(int(c) for c in np.clip(base, 0, 255))
                pts = [_v(x0, h[z, x], z0), _v(x0 + 1, h[z, x + 1], z0), _v(x0 + 1, h[z + 1, x + 1], z0 + 1), _v(x0, h[z + 1, x], z0 + 1)]
                terrain.quad(pts, col, _v(x0 + 0.5, -50, z0 + 0.5))
        # yollar: kapılar arasında koyu toprak şeritler
        for e in self.layout():
            w, d = self.foot(e["key"], e["rot"])
            cx, cz = e["gx"] - HALF + w / 2, e["gz"] - HALF + d / 2
            prog = e.get("prog", 1.0)
            if prog >= 1.0:
                mesh, lts = building_mesh(e["key"], cx, cz, e["pad"], w, d, self.planet,
                                          seed=e["gx"] * 31 + e["gz"] * 7)
                objects.extend(mesh)
                lights.extend(lts)
            else:
                construct.append((e, cx, cz, w, d))
        self.static = (terrain, objects, lights, construct)
        self.static_sig = sig
        return self.static

    # ---------------------------------------------------------------- çizim
    def project(self, P, eye, f, r, u, fpx, cx, cy):
        rel = P - eye
        x = rel @ r
        y = rel @ u
        z = rel @ f
        return x, y, z, cx + fpx * x / np.maximum(z, 1e-3), cy - fpx * y / np.maximum(z, 1e-3)

    def shade_and_draw(self, surf, faces, eye, f, r, u, fpx, cx, cy, L, sun_col, sky, gnd, day, fog_col, alpha=None,
                       cull=True, objects=False, cached=False):
        """faces: yüz listesi ya da pack_faces/concat_packs çıktısı; cached=True durağan listeyi önbellekler."""
        nv = 4
        if isinstance(faces, dict):
            pk = faces
        elif cached:
            pk = pack_cached(faces)
        else:
            pk = pack_faces(faces)
        if pk is None:
            return
        P, cols, two, emit, cnt = pk["P"], pk["cols"], pk["two"], pk["emit"], pk["cnt"]
        cen, ln = pk["cen"], pk["ln"][:, None]
        n = pk["n"].copy()
        view = cen - eye
        facing = (view * n).sum(1) < 0
        keep = (facing | two | (not cull)) & (ln[:, 0] > 1e-8)          # not cull: bool (~True = -2 olurdu)
        # kamera arkası
        x, y, z, sx, sy = self.project(P.reshape(-1, 3), eye, f, r, u, fpx, cx, cy)
        z = z.reshape(-1, nv)
        keep &= (z.min(1) > 0.25)
        sx, sy = sx.reshape(-1, nv), sy.reshape(-1, nv)
        if two.any():
            n[two & ~facing] *= -1
        # ışık: yarımküre ortamı + güneş + ışıma + sis + ACES
        lin = (cols / 255.0) ** 2.2
        ny = n[:, 1:2]
        amb = sky[None, :] * (0.5 + 0.5 * ny) + gnd[None, :] * (0.5 - 0.5 * ny)
        dif = np.clip(n @ L, 0, 1)[:, None] * sun_col[None, :]
        cine = cinema.enabled() and alpha is None
        vdir = view / np.maximum(np.linalg.norm(view, axis=1, keepdims=True), 1e-6)
        if cine and objects:
            # yumuşak sıçrayan ışık (zemin rengi), doymuş temas gölgesi (AO), yarı saydam yaprakta SSS
            gh = self.heights_at(cen[:, 0], cen[:, 2])
            ao = 0.42 + 0.58 * np.clip((cen[:, 1] - gh) / 0.75, 0, 1)
            amb = amb * ao[:, None] + gnd[None, :] * 0.25 * np.clip(-ny, 0, 1)
            leaf = (cols[:, 1] > cols[:, 0] * 1.25) & (cols[:, 1] > cols[:, 2] * 1.25)
            sss = np.clip(-(n @ L), 0, 1) * 0.45 + 0.12
            out = lin * (amb + dif)
            out[leaf] += lin[leaf] * sss[leaf, None] * np.array((1.0, 1.15, 0.6), F32) * sun_col
            out = out * (0.86 + 0.14 * ao[:, None]) + (1 - ao[:, None]) * np.array((0.012, 0.0, 0.03), F32)
        else:
            out = lin * (amb + dif)
        if cine:
            # güçlü, renkli kenar ışığı: güneşin tamamlayıcısı (gündüz camgöbeği, akşam macenta)
            rim = np.clip(1 - np.abs((n * vdir).sum(1)), 0, 1) ** 3
            rim_col = np.array((0.25, 0.55, 1.0), F32) * day + np.array((0.9, 0.3, 0.8), F32) * (1 - day)
            out += rim[:, None] * rim_col[None, :] * (0.35 if objects else 0.08)
        night = 1 - day
        out += (emit[:, None] * np.array((1.0, 0.72, 0.4), F32)[None, :] * (0.12 + 1.4 * night))
        dist = np.linalg.norm(view, axis=1)[:, None]
        fogk = np.clip((dist - 12) / 30, 0, 0.75)
        out = out * (1 - fogk) + ((np.array(fog_col, F32) / 255) ** 2.2)[None, :] * fogk
        a, b, c2, d2, e2 = 2.51, 0.03, 2.43, 0.59, 0.14
        out = np.clip((out * (a * out + b)) / (out * (c2 * out + d2) + e2), 0, 1) ** (1 / 2.2)
        if cine:
            # tamamlayıcı renk uyumu: ışıklar sıcak, gölgeler camgöbeği-mor
            lum = (out @ np.array((0.299, 0.587, 0.114), F32))[:, None]
            out = out + (np.array((0.06, 0.02, -0.04), F32) * lum + np.array((-0.03, 0.0, 0.05), F32) * (1 - lum))
            lum2 = (out @ np.array((0.299, 0.587, 0.114), F32))[:, None]
            out = np.clip(lum2 + (out - lum2) * 1.12, 0, 1)
        rgb = (out * 255).astype(np.int32)
        ink = cine and objects
        lw = max(1, int(round(fpx / 560)))
        order = np.argsort(-z.mean(1))
        order = order[keep[order]]
        # numpy -> Python listesi tek seferde (öğe öğe float() çağrısı yerine)
        SX, SY, RGB = sx[order].tolist(), sy[order].tolist(), rgb[order].tolist()
        CNT, TWO = cnt[order].tolist(), two[order].tolist()
        if ink:
            ICS = (rgb[order] * np.array((0.38, 0.34, 0.42)) + np.array((8, 4, 16))).astype(np.int32).tolist()
        poly, lines = pygame.draw.polygon, pygame.draw.lines
        a_ = int(alpha) if alpha is not None else None
        for j in range(len(SX)):
            k = CNT[j]
            pts = list(zip(SX[j][:k], SY[j][:k]))
            col = RGB[j]
            poly(surf, col if a_ is None else (col[0], col[1], col[2], a_), pts)
            if ink and not TWO[j]:
                # Arcane tarzı mürekkep çizgisi: koyu, hafif mor kontur (kenar yumuşatma süper örneklemeden gelir)
                lines(surf, ICS[j], True, pts, lw)

    def draw(self, surf, rect, bg=None):
        if self.heights is None:
            return
        import time as _time
        t_start = _time.perf_counter()
        # süper örnekleme: pürüzsüz siluetler; bilgisayar yavaşsa kendiliğinden kapanır (uyarlanır kalite)
        ss = i18n.quality().get("ss", 1.35) if (cinema.enabled() and not getattr(self, "low_perf", False)) else 1.0
        self.ss = ss
        w, h = int(rect.w * ss), int(rect.h * ss)
        if self.view is None or self.view.get_size() != (w, h):
            self.view = pygame.Surface((w, h))
            self._layer = pygame.Surface((w, h), pygame.SRCALPHA)
        v = self.view
        if bg is not None and bg.get_size() != (w, h):
            key = (id(bg), w, h)
            if getattr(self, "_bgkey", None) != key:
                self._bgkey, self._bgs = key, pygame.transform.smoothscale(bg, (w, h))
            bg = self._bgs
        sun, sun_col, sky, gnd, day = self.lighting()
        pal = PALETTE[self.planet]
        # arka plan: boyalı manzara, geceye göre karartılmış
        if bg is not None:
            v.blit(bg, (0, 0))
            k = int(255 * (0.35 + 0.65 * day))
            v.fill((k, k, min(255, k + 20)), special_flags=pygame.BLEND_MULT)
        else:
            v.fill(pal[2])
        ty = self.height(self.cam.tx, self.cam.tz)
        eye, f, r, u = self.cam.basis(ty)
        fpx = h * 1.25
        cx, cy = w / 2, h / 2
        fog = tuple(int(c * (0.4 + 0.6 * day)) for c in pal[2])
        terrain, objects, lights, construct = self.static_mesh()
        # 1) arazi
        self.shade_and_draw(v, terrain.faces, eye, f, r, u, fpx, cx, cy, sun, sun_col, sky, gnd, day, fog, cull=False,
                            cached=True)
        # 2) gölgeler (güneş yönünde izdüşüm)
        lay = self._layer
        sh_a = int(110 * day)
        if sh_a > 8 and sun[1] > 0.1:
            lay.fill((0, 0, 0, 0))
            for e in self.layout():
                if e.get("prog", 1.0) < 0.45:
                    continue
                fw, fd = self.foot(e["key"], e["rot"])
                x0, z0 = e["gx"] - HALF + 0.1, e["gz"] - HALF + 0.1
                x1, z1 = x0 + fw - 0.2, z0 + fd - 0.2
                hh = {"mine": 2.3, "park": 0.6, "house": 0.8}.get(e["key"], 1.2)
                base = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
                pts3 = [_v(x, e["pad"], z) for x, z in base]
                pts3 += [_v(x - sun[0] * hh / sun[1], e["pad"], z - sun[2] * hh / sun[1]) for x, z in base]
                X = np.array(pts3)
                _, _, zz, sx, sy = self.project(X, eye, f, r, u, fpx, cx, cy)
                if (zz > 0.3).all():
                    hull = _hull([(float(a), float(b)) for a, b in zip(sx, sy)])
                    if len(hull) >= 3:
                        pygame.draw.polygon(lay, (0, 0, 0, sh_a), hull)
            for a in self.agents:
                if a.hidden:
                    continue
                gy = self.height(a.x, a.z)
                c3 = np.array([_v(a.x - sun[0] * 0.25, gy, a.z - sun[2] * 0.25)])
                _, _, zz, sx, sy = self.project(c3, eye, f, r, u, fpx, cx, cy)
                if zz[0] > 0.3:
                    s = fpx * 0.22 / zz[0]
                    pygame.draw.ellipse(lay, (0, 0, 0, sh_a), (int(sx[0] - s), int(sy[0] - s * 0.45), int(s * 2) + 1,
                                                               int(s * 0.9) + 1))
            v.blit(lay, (0, 0))
        # 3) seçim halkası
        if self.selected and not self.selected.hidden:
            a = self.selected
            gy = self.height(a.x, a.z) + 0.03
            ring = np.array([_v(a.x + math.cos(t) * 0.38, gy, a.z + math.sin(t) * 0.38) for t in np.linspace(0, math.tau, 24)])
            _, _, zz, sx, sy = self.project(ring, eye, f, r, u, fpx, cx, cy)
            if (zz > 0.3).all():
                pts = [(float(a1), float(b1)) for a1, b1 in zip(sx, sy)]
                pygame.draw.lines(v, C["gold"], True, pts, 3)
        # 4) nesneler: binalar + inşaatlar + kolonistler (birlikte derinlik sıralı)
        faces = []                            # her karede değişen yüzler (inşaatlar); binalar önbellekli paketten
        scaffolds = []
        for e, bx, bz, fw, fd in construct:
            p = e.get("prog", 0.0)
            mesh, lts = building_mesh(e["key"], bx, bz, e["pad"], fw, fd, self.planet, seed=e["gx"] * 31 + e["gz"] * 7)
            if p < 0.2:
                continue                      # plan aşaması: yalnızca hayalet çizilir (aşağıda)
            if p < 0.45:                      # temel + iskele
                faces.extend(Mesh().box(bx, bz, e["pad"] - 0.25, fw * 0.96, fd * 0.96, 0.3, (110, 112, 118)).faces)
            else:                             # çerçeve: aşağıdan yukarı dolan yüzler
                top = max(pp[1] for ff in mesh.faces for pp in ff[0])
                lim = e["pad"] + (top - e["pad"]) * (p - 0.45) / 0.55
                faces.extend(ff for ff in mesh.faces if min(pp[1] for pp in ff[0]) <= lim)
            scaffolds.append((e, bx, bz, fw, fd, p))
        packs = [pack_cached(objects.faces), pack_faces(faces)]
        for a in self.agents:
            a.screen = None
            if a.hidden:
                continue
            gy = self.height(a.x, a.z)
            packs.append(colonist_packed(a.x, gy, a.z, a.heading, a.col, a.phase, a.state, a.carry))
        allp = concat_packs(packs)
        if allp is not None:
            self.shade_and_draw(v, allp, eye, f, r, u, fpx, cx, cy, sun, sun_col, sky, gnd, day, fog, objects=True)
        # 5) iskeleler, hayaletler ve yerleştirme önizlemesi (yarı saydam)
        need_layer = bool(scaffolds) or bool(construct) or bool(self.place)
        if need_layer:
            lay.fill((0, 0, 0, 0))
        for e, bx, bz, fw, fd, p in scaffolds:
            if p < 0.85:
                hh = 1.4 if e["key"] != "mine" else 2.4
                for (px, pz) in ((bx - fw / 2, bz - fd / 2), (bx + fw / 2, bz - fd / 2), (bx + fw / 2, bz + fd / 2), (bx - fw / 2, bz + fd / 2)):
                    seg = np.array([_v(px, e["pad"], pz), _v(px, e["pad"] + hh, pz)])
                    _, _, zz, sx, sy = self.project(seg, eye, f, r, u, fpx, cx, cy)
                    if (zz > 0.3).all():
                        pygame.draw.line(lay, (210, 170, 90, 220), (float(sx[0]), float(sy[0])), (float(sx[1]), float(sy[1])), 2)
                for yy in (0.5, 1.0):
                    ring = np.array([_v(bx - fw / 2, e["pad"] + yy, bz - fd / 2), _v(bx + fw / 2, e["pad"] + yy, bz - fd / 2),
                                     _v(bx + fw / 2, e["pad"] + yy, bz + fd / 2), _v(bx - fw / 2, e["pad"] + yy, bz + fd / 2)])
                    _, _, zz, sx, sy = self.project(ring, eye, f, r, u, fpx, cx, cy)
                    if (zz > 0.3).all():
                        pygame.draw.lines(lay, (210, 170, 90, 200), True, [(float(a1), float(b1)) for a1, b1 in zip(sx, sy)], 2)
        for e, bx, bz, fw, fd in construct:
            if e.get("prog", 0.0) < 0.2:
                mesh, _ = building_mesh(e["key"], bx, bz, e["pad"], fw, fd, self.planet, seed=1)
                self.shade_and_draw(lay, mesh.faces, eye, f, r, u, fpx, cx, cy, sun, np.ones(3, F32), np.ones(3, F32) * 0.5,
                                    np.ones(3, F32) * 0.3, 1.0, fog, alpha=90)
        # yerleştirme hayaleti
        self.mouse_world = None
        mx, my = pygame.mouse.get_pos()
        if rect.collidepoint((mx, my)):
            d = _norm(f + r * (((mx - rect.x) * ss - cx) / fpx) + u * ((cy - (my - rect.y) * ss) / fpx))
            if d[1] < -1e-3:
                tt = (ty - eye[1]) / d[1]
                hit = eye + d * tt
                self.mouse_world = (float(hit[0]), float(hit[2]))
        if self.place and self.mouse_world:
            p = self.place
            fw, fd = self.foot(p["key"], p["rot"])
            gx = int(round(self.mouse_world[0] + HALF - fw / 2))
            gz = int(round(self.mouse_world[1] + HALF - fd / 2))
            p["cell"] = (gx, gz)
            cells = self.cells_of(p["key"], gx, gz, p["rot"])
            p["valid"] = self.free(cells, margin=False)
            if p["valid"]:
                hs = [self.base_heights[z, x] for (x, z) in cells if 0 <= x < N and 0 <= z < N]
                p["valid"] = (max(hs) - min(hs)) < 0.9 if hs else False      # çok dik zemine kurulmaz
            col = (60, 230, 120) if p["valid"] else (240, 70, 70)
            bx, bz = gx - HALF + fw / 2, gz - HALF + fd / 2
            pad = self.height(bx, bz)
            mesh, _ = building_mesh(p["key"], bx, bz, pad, fw, fd, self.planet, seed=1)
            ghost = Mesh()
            for pts, _c, inner, two, em in mesh.faces:
                ghost.faces.append((pts, col, inner, two, 0.0))
            self.shade_and_draw(lay, ghost.faces, eye, f, r, u, fpx, cx, cy, sun, np.ones(3, F32), np.ones(3, F32) * 0.6,
                                np.ones(3, F32) * 0.4, 1.0, fog, alpha=110)
            fp = np.array([_v(bx - fw / 2, pad + 0.02, bz - fd / 2), _v(bx + fw / 2, pad + 0.02, bz - fd / 2),
                           _v(bx + fw / 2, pad + 0.02, bz + fd / 2), _v(bx - fw / 2, pad + 0.02, bz + fd / 2)])
            _, _, zz, sx, sy = self.project(fp, eye, f, r, u, fpx, cx, cy)
            if (zz > 0.3).all():
                pygame.draw.lines(lay, col + (255,), True, [(float(a1), float(b1)) for a1, b1 in zip(sx, sy)], 2)
        if need_layer:
            v.blit(lay, (0, 0))
        # 6) gece ışıkları (bloom)
        night = 1 - day
        if night > 0.15:
            pts = np.array([_v(x, y, z) for x, y, z, _ in lights]) if lights else np.zeros((0, 3), F32)
            if len(pts):
                _, _, zz, sx, sy = self.project(pts, eye, f, r, u, fpx, cx, cy)
                for i, (_, _, _, col) in enumerate(lights):
                    if zz[i] > 0.3:
                        draw_glow(v, (float(sx[i]), float(sy[i])), float(min(70.0, fpx * 0.9 / zz[i])), col, 0.5 * night)
        # 7) küçült (kenar yumuşatma) + sinematik geçiş + tilt-shift alan derinliği
        out = pygame.transform.smoothscale(v, rect.size) if ss != 1.0 else v
        if cinema.enabled():
            sp = eye + sun * 200
            _, _, sz, ssx, ssy = self.project(np.array([sp]), eye, f, r, u, fpx, cx, cy)
            sunpos = (float(ssx[0]) / ss, float(ssy[0]) / ss) if sz[0] > 0 else (rect.w * 0.8, -rect.h * 0.4)
            warm_sun = tuple(int(c) for c in np.clip(sun_col / max(1e-3, sun_col.max()) * 255, 0, 255))
            cinema.full_pass(out, out.get_rect(), self.t, sun=sunpos, sun_col=warm_sun, rays=0.42 * day,
                             mote_col=(255, 226, 180) if day > 0.3 else (150, 190, 255), n_motes=55,
                             haze_col=pal[2], haze_k=round(0.22 + 0.1 * day, 1))
        self.tilt_shift(out)
        surf.blit(out, rect.topleft)
        dt_draw = _time.perf_counter() - t_start
        self.perf_ema = dt_draw if not hasattr(self, "perf_ema") else self.perf_ema * 0.95 + dt_draw * 0.05
        self.perf_n = getattr(self, "perf_n", 0) + 1
        if self.perf_n > 90 and self.perf_ema > 0.05 and not getattr(self, "low_perf", False):
            self.low_perf = True                     # ~20 FPS altı: süper örneklemeyi kapat
            self.view = None
        # 8) dünya arayüzü: kameraya dönük durum simgeleri, can çubukları, inşaat etiketleri
        happy = self.colony.get("happiness", 70) / 100.0
        for a in self.agents:
            if a.hidden:
                continue
            gy = self.height(a.x, a.z)
            hp = np.array([_v(a.x, gy + 1.2, a.z), _v(a.x, gy + 0.5, a.z)])
            _, _, zz, sx, sy = self.project(hp, eye, f, r, u, fpx, cx, cy)
            if zz[0] <= 0.3:
                continue
            a.screen = (rect.x + float(sx[1]) / ss, rect.y + float(sy[1]) / ss)
            if a is self.selected or zz[0] < 11:
                X, Y = rect.x + float(sx[0]) / ss, rect.y + float(sy[0]) / ss
                if rect.collidepoint((X, Y)):
                    draw_bar(surf, (int(X - 22), int(Y - 6), 44, 5), happy, C["green"] if happy > 0.4 else C["red"])
                    if a is self.selected:
                        draw_text(surf, a.label(), (X, Y - 24), 12, C["white"], bold=True, anchor="midtop")
        for e, bx, bz, fw, fd in construct:
            p = np.array([_v(bx, e["pad"] + 1.9, bz)])
            _, _, zz, sx, sy = self.project(p, eye, f, r, u, fpx, cx, cy)
            if zz[0] > 0.3:
                X, Y = rect.x + float(sx[0]) / ss, rect.y + float(sy[0]) / ss
                if rect.collidepoint((X, Y)):
                    pr = e.get("prog", 0.0)
                    phase = "Plan" if pr < 0.2 else "Temel ve iskele" if pr < 0.45 else "Çerçeve" if pr < 0.85 else "Son dokunuşlar"
                    draw_text(surf, phase, (X, Y - 18), 12, C["gold"], bold=True, anchor="midtop")
                    draw_bar(surf, (int(X - 40), int(Y), 80, 6), pr, C["gold"])
        if night > 0.6:
            for d in self.doors.get("house", []):
                p = np.array([_v(d[0] - HALF + 0.5, self.height(d[0] - HALF + 0.5, d[1] - HALF - 1) + 1.6, d[1] - HALF - 0.5)])
                _, _, zz, sx, sy = self.project(p, eye, f, r, u, fpx, cx, cy)
                if zz[0] > 0.3 and any(a.hidden for a in self.agents):
                    X, Y = rect.x + float(sx[0]) / ss, rect.y + float(sy[0]) / ss + math.sin(self.t * 2) * 4
                    if rect.collidepoint((X, Y)):
                        draw_text(surf, "Z z", (X, Y), 16, C["cyan"], bold=True, anchor="center", raw=True)

    def tilt_shift(self, v):
        w, h = v.get_size()
        small = pygame.transform.smoothscale(v, (max(1, w // 5), max(1, h // 5)))
        big = pygame.transform.smoothscale(small, (w, h))
        bands = 6
        top_h, bot_h = int(h * 0.2), int(h * 0.16)
        for i in range(bands):
            a = int(210 * (1 - i / bands))
            big.set_alpha(a)
            y0 = int(top_h * i / bands)
            v.blit(big, (0, y0), area=pygame.Rect(0, y0, w, max(1, top_h // bands + 1)))
            y1 = h - int(bot_h * (i + 1) / bands)
            v.blit(big, (0, y1), area=pygame.Rect(0, y1, w, max(1, bot_h // bands + 1)))
        big.set_alpha(None)

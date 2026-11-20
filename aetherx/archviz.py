# -*- coding: utf-8 -*-
"""
AETHER-X // MİMARİ GÖRSELLEŞTİRME (fırlatma üssü binaları)

Üs haritasındaki her bina, üç çeyrek eğik (oblique) bakışta gerçekçi bir 3B model olarak bir kez
üretilir ve önbelleğe alınır:
  * eğik izdüşüm: (x, y, z) -> (x - z*KX, y - z*KZ)  — çatı, batı cephesi ve güney cephesi görünür
  * güneş sol üstten: çatı en aydınlık, batı cephesi aydınlık, güney cephesi yarı gölgede
  * yere düşen yumuşak gölge (güneydoğuya), zemine yakın ortam gölgesi (AO), çatı kenarı pahı
  * malzemeler uyumlu palette: sıcak açık gri beton (saf beyaz yok), çelik, koyu cam, oksitli metal
  * cephede panel derzleri, pencere bantları; gece pencereler sıcak ışıkla yanar
  * kilitli bina: temel + iskele (inşaat alanı)

Hareketli ve oyun durumuna bağlı ayrıntılar (rampadaki roketler, ilerleme halkaları, görev panosu
yazıları vb.) sahne tarafından bu modelin üstüne çizilir.
"""
import math
import random

import numpy as np
import pygame

KX, KZ = 0.32, 0.82            # eğik izdüşüm katsayıları (yükseklik sola-yukarı kayar)
SUN_SHADOW = (0.42, 0.24)      # 1 birim yükseklik için gölgenin yerdeki kayması (güneydoğuya)

# ---------------------------------------------------------------- malzeme paleti
# Bilinçli olarak doygunluğu ve parlaklığı sınırlı, birbiriyle uyumlu tonlar (saf beyaz yok).
MAT = {
    "concrete":  (176, 178, 180),
    "concrete2": (138, 140, 142),
    "apron":     (112, 114, 116),       # rampa/beton saha
    "panel":     (198, 198, 194),       # boyalı cephe paneli: kırık beyaz (saf beyaz değil)
    "steel":     (132, 140, 150),
    "steel_d":   (84, 90, 100),
    "glass":     (46, 62, 82),
    "glass_l":   (96, 124, 150),
    "roof":      (118, 120, 122),       # çakıl çatı: cepheden koyu (biçim okunur, parlamaz)
    "roof_d":    (98, 100, 104),
    "asphalt":   (62, 64, 70),
    "rust":      (150, 92, 64),
    "tower":     (176, 74, 56),          # fırlatma kulesi: oksit kırmızısı
    "grass":     (74, 112, 72),
    "grass_d":   (52, 86, 56),
    "water":     (64, 128, 158),
    "copper":    (176, 132, 92),
    "dark":      (34, 38, 46),
}
WARM_WIN = (255, 214, 150)
COOL_WIN = (150, 200, 235)

_CACHE = {}


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _mul(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


class Arch:
    """Tek bir bina modelini oluşturan küçük sahne: kutu, silindir, küre, kubbe, kafes kule..."""

    def __init__(self, w, h, max_z, night, seed=1):
        self.w, self.h = w, h
        self.night = night
        self.mx = int(max_z * KX) + 10                      # sola taşma payı
        self.my = int(max_z * KZ) + 10                      # yukarı taşma payı
        self.rx = int(max_z * SUN_SHADOW[0]) + 14           # gölge payı (sağ)
        self.ry = int(max_z * SUN_SHADOW[1]) + 14           # gölge payı (alt)
        size = (w + self.mx + self.rx, h + self.my + self.ry)
        self.surf = pygame.Surface(size, pygame.SRCALPHA)
        self.shadow = pygame.Surface(size, pygame.SRCALPHA)
        self.rng = random.Random(seed)
        # ışık: gündüz nötr-sıcak, gece soğuk ve kısık
        self.L = 1.0 - 0.62 * night
        self.tint = _mix((255, 250, 242), (150, 170, 220), night)

    # --- yardımcılar ----------------------------------------------------------------
    def P(self, x, y, z=0.0):
        return (self.mx + x - z * KX, self.my + y - z * KZ)

    def lit(self, col, k):
        """Malzeme rengi x ışık şiddeti x ortam rengi."""
        k *= self.L
        return tuple(max(0, min(255, int(col[i] * k * self.tint[i] / 255))) for i in range(3))

    def poly(self, col, pts, width=0):
        pygame.draw.polygon(self.surf, col, [(round(px), round(py)) for px, py in pts], width)

    def cast(self, pts_ground, z, alpha=110):
        """Taban çokgeninin z yükseklikteki gölgesi (taban + kaydırılmış taban dışbükey zarfı)."""
        sx, sy = SUN_SHADOW[0] * z, SUN_SHADOW[1] * z
        pts = [self.P(x, y) for x, y in pts_ground] + [self.P(x + sx, y + sy) for x, y in pts_ground]
        hull = _hull(pts)
        if len(hull) >= 3:
            pygame.draw.polygon(self.shadow, (8, 10, 20, alpha), [(round(a), round(b)) for a, b in hull])

    def face_grad(self, quad, top_col, bot_col, steps=10):
        """Dörtgen yüzü dikey gradyanla boyar (quad: alt-sol, alt-sağ, üst-sağ, üst-sol)."""
        (ax, ay), (bx, by), (cx, cy), (dx, dy) = quad
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            p0 = (ax + (dx - ax) * t0, ay + (dy - ay) * t0)
            p1 = (bx + (cx - bx) * t0, by + (cy - by) * t0)
            p2 = (bx + (cx - bx) * t1, by + (cy - by) * t1)
            p3 = (ax + (dx - ax) * t1, ay + (dy - ay) * t1)
            self.poly(_mix(bot_col, top_col, (t0 + t1) / 2), [p0, p1, p2, p3])

    # --- ilkel şekiller -------------------------------------------------------------
    def box(self, x, y, w, d, hgt, mat="concrete", roof=None, z0=0.0, windows=None, seams=0, door=None,
            band=None, parapet=True, shadow=True, roof_units=0, south_mat=None, joints=0):
        """Eksen hizalı kutu. windows: (sıra, sütun, renk_seed) güney cephesine; seams: dikey derz aralığı (px).
        door: (u0, u1, yükseklik) güney cephesinde koyu kapı oyuğu (oran). band: (z_oran, kalınlık, renk)."""
        base = MAT.get(mat, mat) if isinstance(mat, str) else mat
        rcol = MAT.get(roof, roof) if isinstance(roof, str) else (roof or _mul(base, 0.92))
        scol = MAT.get(south_mat, south_mat) if isinstance(south_mat, str) else (south_mat or base)
        z1 = z0 + hgt
        if shadow and z0 <= 0.01:
            self.cast([(x, y), (x + w, y), (x + w, y + d), (x, y + d)], z1)
        # batı cephesi (aydınlık)
        west = [self.P(x, y + d, z0), self.P(x, y, z0), self.P(x, y, z1), self.P(x, y + d, z1)]
        self.face_grad(west, self.lit(base, 1.08), self.lit(base, 0.78))
        # güney cephesi (yarı gölge) + ortam gölgesi
        south = [self.P(x, y + d, z0), self.P(x + w, y + d, z0), self.P(x + w, y + d, z1), self.P(x, y + d, z1)]
        self.face_grad(south, self.lit(scol, 0.78), self.lit(scol, 0.46))
        if seams:
            n = max(1, int(w / seams))
            for i in range(1, n):
                u = x + w * i / n
                self.poly_line(self.lit(scol, 0.58), self.P(u, y + d, z0 + 1), self.P(u, y + d, z1 - 1))
        if band:
            bz, bt, bc = band
            zz = z0 + hgt * bz
            q = [self.P(x, y + d, zz), self.P(x + w, y + d, zz), self.P(x + w, y + d, zz + bt), self.P(x, y + d, zz + bt)]
            self.poly(self.lit(MAT.get(bc, bc) if isinstance(bc, str) else bc, 0.78), q)
        if windows:
            self.windows(x, y + d, w, z0, hgt, *windows)
        if door:
            u0, u1, dh = door
            q = [self.P(x + w * u0, y + d, z0), self.P(x + w * u1, y + d, z0),
                 self.P(x + w * u1, y + d, z0 + hgt * dh), self.P(x + w * u0, y + d, z0 + hgt * dh)]
            self.poly(self.lit(MAT["dark"], 1.0), q)
            # kapı panelleri (dikey çizgiler)
            for i in range(1, 6):
                u = x + w * (u0 + (u1 - u0) * i / 6)
                self.poly_line(self.lit(MAT["steel_d"], 0.9), self.P(u, y + d, z0), self.P(u, y + d, z0 + hgt * dh))
            if self.night > 0.4:
                self.glow_quad(q, WARM_WIN, 0.35 * self.night)
        # çatı
        roofq = [self.P(x, y, z1), self.P(x + w, y, z1), self.P(x + w, y + d, z1), self.P(x, y + d, z1)]
        self.poly(self.lit(rcol, 1.16), roofq)
        # çatı kenarı pahı (parapet) — ince açık ve koyu çizgiler
        if parapet:
            self.poly_line(self.lit(rcol, 1.22), self.P(x, y + d, z1), self.P(x, y, z1))
            self.poly_line(self.lit(rcol, 1.22), self.P(x, y, z1), self.P(x + w, y, z1))
            self.poly_line(self.lit(rcol, 0.72), self.P(x, y + d, z1), self.P(x + w, y + d, z1))
            inset = 3
            q2 = [self.P(x + inset, y + inset, z1), self.P(x + w - inset, y + inset, z1),
                  self.P(x + w - inset, y + d - inset, z1), self.P(x + inset, y + d - inset, z1)]
            self.poly(self.lit(rcol, 1.08), q2)
        if joints:                                   # beton saha genleşme derzleri
            jc = self.lit(rcol, 0.86)
            for u in np.arange(x + joints, x + w - 2, joints):
                self.poly_line(jc, self.P(u, y, z1), self.P(u, y + d, z1))
            for v in np.arange(y + joints, y + d - 2, joints):
                self.poly_line(jc, self.P(x, v, z1), self.P(x + w, v, z1))
        for i in range(roof_units):
            uw, ud = min(18, w * 0.18), min(12, d * 0.2)
            ux = x + 6 + self.rng.random() * max(1, w - uw - 12)
            uy = y + 6 + self.rng.random() * max(1, d - ud - 12)
            self.box(ux, uy, uw, ud, 5, "steel", z0=z1, parapet=False, shadow=False)

    def poly_line(self, col, a, b, w=1):
        pygame.draw.line(self.surf, col, (round(a[0]), round(a[1])), (round(b[0]), round(b[1])), w)

    def glow_quad(self, quad, col, k):
        g = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(g, (*col, int(110 * k)), [(round(a), round(b)) for a, b in quad])
        self.surf.blit(g, (0, 0))

    def windows(self, x, y_face, w, z0, hgt, rows, cols, seed=0, glass="glass", margin=0.12, ribbon=False):
        rng = random.Random(seed)
        gcol = MAT[glass]
        for j in range(rows):
            zb = z0 + hgt * (0.18 + j * (0.72 / rows))
            zt = zb + hgt * (0.72 / rows) * 0.55
            if ribbon:
                spans = [(x + w * margin, x + w * (1 - margin))]
            else:
                cw = w * (1 - 2 * margin) / cols
                spans = [(x + w * margin + i * cw + cw * 0.14, x + w * margin + (i + 1) * cw - cw * 0.14) for i in range(cols)]
            for (u0, u1) in spans:
                q = [self.P(u0, y_face, zb), self.P(u1, y_face, zb), self.P(u1, y_face, zt), self.P(u0, y_face, zt)]
                on = self.night > 0.35 and rng.random() < 0.72
                if on:
                    c = _mix(WARM_WIN, COOL_WIN, rng.random() * 0.35)
                    self.poly(_mix(self.lit(gcol, 1.0), c, 0.55 + 0.4 * self.night), q)
                else:
                    # gökyüzü yansıması: üstte açık, altta koyu cam
                    self.face_grad([q[0], q[1], q[2], q[3]], self.lit(MAT["glass_l"], 1.05), self.lit(gcol, 0.95), 3)
                self.poly(self.lit(MAT["steel_d"], 0.9), q, 1)

    def cylinder(self, cx, cy, r, hgt, mat="steel", z0=0.0, cap=None, rings=0, shadow=True):
        base = MAT.get(mat, mat) if isinstance(mat, str) else mat
        z1 = z0 + hgt
        if shadow and z0 <= 0.01:
            pts = [(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.9) for a in np.linspace(0, math.tau, 18)]
            self.cast(pts, z1)
        # gövde: soldan sağa ışık geçişi (sol taraf aydınlık)
        n = max(8, int(r))
        for i in range(n):
            a0 = math.pi * (i / n)
            a1 = math.pi * ((i + 1) / n)
            # ön yarım daire: açı 0 (doğu) .. pi (batı) — güney yüzü görünür
            x0, x1 = cx + math.cos(a0) * r, cx + math.cos(a1) * r
            y0, y1 = cy + math.sin(a0) * r * 0.9, cy + math.sin(a1) * r * 0.9
            lamb = 0.55 + 0.45 * max(0.0, -math.cos((a0 + a1) / 2) * 0.8 + 0.35)
            q = [self.P(x0, y0, z0), self.P(x1, y1, z0), self.P(x1, y1, z1), self.P(x0, y0, z1)]
            self.face_grad(q, self.lit(base, lamb * 1.02), self.lit(base, lamb * 0.72), 4)
        for k in range(1, rings + 1):
            zz = z0 + hgt * k / (rings + 1)
            pts = [self.P(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.9, zz) for a in np.linspace(0, math.pi, 12)]
            pygame.draw.lines(self.surf, self.lit(base, 0.6), False, [(round(a), round(b)) for a, b in pts], 1)
        top = [self.P(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.9, z1) for a in np.linspace(0, math.tau, 24)]
        self.poly(self.lit(MAT.get(cap, cap) if isinstance(cap, str) else (cap or base), 1.05), top)

    def sphere(self, cx, cy, r, z_center, mat="panel"):
        """Küre: numpy ile Lambert + yumuşak yansıma, sol üstten ışık."""
        base = np.array(MAT.get(mat, mat) if isinstance(mat, str) else mat, np.float32)
        self.cast([(cx + math.cos(a) * r, cy + math.sin(a) * r) for a in np.linspace(0, math.tau, 16)], z_center + r * 0.6, 95)
        sx, sy = self.P(cx, cy, z_center)
        R = int(r)
        yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        d2 = (xx * xx + yy * yy) / (R * R)
        inside = d2 <= 1.0
        nz = np.sqrt(np.clip(1 - d2, 0, 1))
        nx, ny = xx / R, yy / R
        L = np.array((-0.55, -0.6, 0.58), np.float32)
        L /= np.linalg.norm(L)
        lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
        spec = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1) ** 24 * 0.35
        k = (0.36 + 0.78 * lam) * self.L
        tint = np.array(self.tint, np.float32) / 255
        rgb = base[None, None, :] * k[..., None] * tint[None, None, :] + spec[..., None] * 255 * self.L
        rim = np.clip(1 - nz, 0, 1) ** 3 * 0.18                     # kenarda gökyüzü yansıması
        rgb = rgb * (1 - rim[..., None]) + np.array((120, 150, 190), np.float32) * rim[..., None] * self.L
        a = np.clip((1 - np.sqrt(d2)) * R * 1.5, 0, 1) * 255 * inside
        arr = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), a.astype(np.uint8)])
        spr = pygame.image.frombuffer(np.ascontiguousarray(arr).tobytes(), (2 * R + 1, 2 * R + 1), "RGBA")
        self.surf.blit(spr, (round(sx - R), round(sy - R)))

    def dome(self, cx, cy, r, z0, mat="glass_l", ribs=8):
        """Yarım küre kubbe (cam/metal kaburgalı)."""
        base = np.array(MAT.get(mat, mat) if isinstance(mat, str) else mat, np.float32)
        sx, sy = self.P(cx, cy, z0)
        R = int(r)
        Ry = int(r * 0.9)
        yy, xx = np.mgrid[-R:1, -R:R + 1].astype(np.float32)    # yalnızca üst yarı (kubbe)
        nx, ny = xx / R, yy / R
        d2 = nx * nx + ny * ny
        inside = d2 <= 1
        nz = np.sqrt(np.clip(1 - d2, 0, 1))
        L = np.array((-0.55, -0.62, 0.56), np.float32)
        L /= np.linalg.norm(L)
        lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
        k = (0.35 + 0.7 * lam) * self.L
        tint = np.array(self.tint, np.float32) / 255
        rgb = base[None, None, :] * k[..., None] * tint[None, None, :]
        spec = lam ** 30 * 120 * self.L
        rgb += spec[..., None]
        # kaburgalar
        ang = np.arctan2(ny, nx + 1e-6)
        rib = (np.abs(((ang / math.pi * ribs) % 1.0) - 0.5) > 0.46) & inside
        rgb[rib] *= 0.7
        if self.night > 0.35:
            rgb = rgb * 0.7 + np.array(COOL_WIN, np.float32) * 0.35 * self.night * nz[..., None]
        a = np.clip((1 - np.sqrt(d2)) * R * 1.5, 0, 1) * 255 * inside
        arr = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), a.astype(np.uint8)])
        spr = pygame.image.frombuffer(np.ascontiguousarray(arr).tobytes(), (2 * R + 1, R + 1), "RGBA")
        spr = pygame.transform.smoothscale(spr, (2 * R + 1, Ry + 1))
        self.surf.blit(spr, (round(sx - R), round(sy - Ry)))

    def lattice(self, x, y, w, hgt, mat="tower", z0=0.0):
        """Kafes kule (fırlatma kulesi / anten direği): ön yüzde çapraz örgü."""
        base = MAT.get(mat, mat) if isinstance(mat, str) else mat
        self.cast([(x, y), (x + w, y), (x + w, y + w), (x, y + w)], z0 + hgt, 90)
        col = self.lit(base, 0.92)
        dcol = self.lit(base, 0.62)
        for u in (x, x + w):
            self.poly_line(col, self.P(u, y + w, z0), self.P(u, y + w, z0 + hgt), 2)
            self.poly_line(dcol, self.P(u, y, z0), self.P(u, y, z0 + hgt), 1)
        step = max(6, w * 0.9)
        z = z0
        while z < z0 + hgt - 1:
            z2 = min(z0 + hgt, z + step)
            self.poly_line(col, self.P(x, y + w, z), self.P(x + w, y + w, z2))
            self.poly_line(dcol, self.P(x + w, y + w, z), self.P(x, y + w, z2))
            self.poly_line(col, self.P(x, y + w, z2), self.P(x + w, y + w, z2))
            z = z2
        self.box(x - 2, y - 2, w + 4, w + 4, 3, mat, z0=z0 + hgt, parapet=False, shadow=False)

    def tree(self, cx, cy, r, h):
        self.cylinder(cx, cy, max(1.5, r * 0.16), h * 0.45, (96, 74, 58), shadow=False)
        self.cast([(cx + math.cos(a) * r, cy + math.sin(a) * r) for a in np.linspace(0, math.tau, 12)], h, 85)
        c = _mix(MAT["grass"], (96, 128, 70), self.rng.random() * 0.5)
        self.sphere(cx, cy, r, h * 0.45 + r * 0.7, c)

    def slab(self, x, y, w, d, mat="concrete2", hgt=3):
        self.box(x, y, w, d, hgt, mat, parapet=False, shadow=False)

    def scaffold(self, x, y, w, d, hgt):
        """Kilitli bina: temel + iskele çerçevesi (inşaat alanı)."""
        self.slab(x, y, w, d, "concrete2", 4)
        col = self.lit((196, 160, 70), 0.95)
        dcol = self.lit((150, 120, 60), 0.8)
        for u in np.linspace(x, x + w, max(3, int(w / 26)) + 1):
            self.poly_line(col, self.P(u, y + d, 4), self.P(u, y + d, hgt))
            self.poly_line(dcol, self.P(u, y, 4), self.P(u, y, hgt))
        for zz in np.linspace(10, hgt, 4):
            self.poly_line(col, self.P(x, y + d, zz), self.P(x + w, y + d, zz))
            self.poly_line(dcol, self.P(x, y, zz), self.P(x, y + d, zz))
        # vinç
        mx = x + w * 0.8
        self.lattice(mx, y + d * 0.3, 6, hgt * 1.5, (200, 170, 70))
        jib0, jib1 = self.P(mx - w * 0.7, y + d * 0.3, hgt * 1.5), self.P(mx + 30, y + d * 0.3, hgt * 1.5)
        self.poly_line(col, jib0, jib1, 2)

    # --- son rötuş ------------------------------------------------------------------
    def finish(self, grain=True):
        out = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)
        out.blit(self.shadow, (0, 0))
        out.blit(self.surf, (0, 0))
        if grain:
            # malzeme dokusu: çok ince beton/boya grenli çarpma (alfa korunur)
            w, h = out.get_size()
            rng = np.random.default_rng(7)
            n = (rng.random((h // 2 + 1, w // 2 + 1)).astype(np.float32) - 0.5) * 22
            n = np.repeat(np.repeat(n, 2, 0), 2, 1)[:h, :w]
            v = np.clip(246 + n, 0, 255).astype(np.uint8)
            g = pygame.image.frombuffer(np.ascontiguousarray(np.dstack([v, v, v])).tobytes(), (w, h), "RGB")
            out.blit(g, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        try:
            if pygame.display.get_surface() is not None:
                out = out.convert_alpha()
        except pygame.error:
            pass
        return out, (self.mx, self.my)


def _hull(points):
    pts = sorted(set((round(x, 1), round(y, 1)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


# =================================================================================
# BİNALAR (footprint: w x h piksel; modeller bu alanın içine oturur)
# =================================================================================
def _hangar(A, w, h, lv, acc):
    """Araç Montaj Binası tarzı: dev blok, yüksek dikey kapılar, alçak yan kanat, ajans amblemi."""
    hh = 104 + 22 * lv
    A.box(w * 0.04, h * 0.42, w * 0.92, h * 0.5, 34, "panel", "roof", seams=22,
          windows=(1, 9, 3, "glass", 0.06), roof_units=3)                       # alçak kanat
    A.box(w * 0.18, h * 0.04, w * 0.5, h * 0.62, hh, "panel", "roof_d", seams=14, roof_units=4,
          door=(0.14, 0.42, 0.86), band=(0.92, 4, "concrete2"))
    # ikinci kapı çifti
    x, y, ww, d = w * 0.18, h * 0.04, w * 0.5, h * 0.62
    q = [A.P(x + ww * 0.58, y + d, 0), A.P(x + ww * 0.86, y + d, 0), A.P(x + ww * 0.86, y + d, hh * 0.86),
         A.P(x + ww * 0.58, y + d, hh * 0.86)]
    A.poly(A.lit(MAT["dark"], 1.0), q)
    for i in range(1, 6):
        u = x + ww * (0.58 + 0.28 * i / 6)
        A.poly_line(A.lit(MAT["steel_d"], 0.9), A.P(u, y + d, 0), A.P(u, y + d, hh * 0.86))
    # ajans amblemi (yuvarlak, kendi rengi) ve renk bantları — batı cephesinde
    ex, ey = A.P(x, y + d * 0.5, hh * 0.62)
    pygame.draw.circle(A.surf, A.lit(acc, 0.9), (round(ex - 2), round(ey)), max(5, int(d * 0.11)))
    pygame.draw.circle(A.surf, A.lit((236, 236, 232), 0.85), (round(ex - 2), round(ey)), max(5, int(d * 0.11)), 2)
    for i in range(3):
        c = acc if i != 1 else (220, 220, 214)
        z0 = hh * (0.2 + i * 0.07)
        q = [A.P(x, y + d * 0.28, z0), A.P(x, y + d * 0.72, z0), A.P(x, y + d * 0.72, z0 + hh * 0.05),
             A.P(x, y + d * 0.28, z0 + hh * 0.05)]
        A.poly(A.lit(c, 0.82), q)
    # yan servis kulesi
    A.box(w * 0.72, h * 0.12, w * 0.18, h * 0.26, hh * 0.55, "concrete", "roof", windows=(3, 2, 7))


def _research(A, w, h, lv, acc):
    A.box(w * 0.05, h * 0.3, w * 0.9, h * 0.6, 30 + 6 * lv, "concrete", "roof",
          windows=(2, 1, 11, "glass", 0.05, True), roof_units=2)
    A.dome(w * 0.5, h * 0.5, min(w, h) * 0.28, 30 + 6 * lv, "glass_l", ribs=9)
    A.box(w * 0.08, h * 0.06, w * 0.22, h * 0.28, 18, "steel", "roof_d", seams=8)


def _astro(A, w, h, lv, acc):
    A.box(w * 0.04, h * 0.18, w * 0.6, h * 0.74, 36 + 4 * lv, "panel", "roof", seams=18,
          windows=(3, 6, 21), roof_units=2)
    # santrifüj eğitim salonu (silindir)
    A.cylinder(w * 0.8, h * 0.55, min(w, h) * 0.17, 26, "concrete2", cap="roof", rings=2)


def _depot(A, w, h, lv, acc):
    A.box(w * 0.03, h * 0.08, w * 0.94, h * 0.78, 30, (150, 140, 120), "roof_d", seams=9, roof_units=1)
    # sarmal kepenkler
    x, y, ww, d = w * 0.03, h * 0.08, w * 0.94, h * 0.78
    for i in range(3):
        u0 = 0.12 + i * 0.28
        q = [A.P(x + ww * u0, y + d, 0), A.P(x + ww * (u0 + 0.18), y + d, 0),
             A.P(x + ww * (u0 + 0.18), y + d, 20), A.P(x + ww * u0, y + d, 20)]
        A.face_grad(q, A.lit((120, 124, 130), 0.9), A.lit((90, 94, 100), 0.8), 6)
        for k in range(1, 6):
            A.poly_line(A.lit((70, 74, 80), 0.9), A.P(x + ww * u0, y + d, 20 * k / 6), A.P(x + ww * (u0 + 0.18), y + d, 20 * k / 6))


def _board(A, w, h, lv, acc):
    A.box(w * 0.04, h * 0.12, w * 0.92, h * 0.74, 22, "concrete2", "roof", parapet=True)


def _nova(A, w, h, lv, acc):
    A.box(w * 0.06, h * 0.08, w * 0.88, h * 0.82, 40 + 8 * lv, (40, 46, 58), (58, 64, 76),
          windows=(4, 1, 5, "glass", 0.04, True), seams=0)
    # çatıda ışıklı halka (yapay zekâ çekirdeği)
    cx, cy = w * 0.5, h * 0.48
    pts = [A.P(cx + math.cos(a) * w * 0.26, cy + math.sin(a) * h * 0.26, 40 + 8 * lv + 1) for a in np.linspace(0, math.tau, 32)]
    pygame.draw.lines(A.surf, A.lit(_mix(acc, (220, 240, 250), 0.3), 1.1), True, [(round(a), round(b)) for a, b in pts], 2)


def _control(A, w, h, lv, acc):
    A.box(w * 0.03, h * 0.22, w * 0.94, h * 0.7, 28 + 3 * lv, "panel", "roof", windows=(2, 1, 31, "glass", 0.04, True),
          roof_units=2, band=(0.08, 3, "concrete2"))
    for i in range(2 + lv // 2):
        A.lattice(w * (0.12 + i * 0.2), h * 0.1, 4, 26 + i * 6, "steel")


def _fuel(A, w, h, lv, acc, n=3):
    rad = min(h * 0.3, (w - 30) / (2.25 * max(1, n)))
    for i in range(n):
        cx = w * 0.12 + rad + i * (w - w * 0.24 - 2 * rad) / max(1, n - 1)
        for lx in (-0.55, 0.55):                                  # ayaklar
            A.cylinder(cx + lx * rad, h * 0.55, 2, rad * 0.9, "steel_d", shadow=False)
        A.sphere(cx, h * 0.55, rad, rad * 1.5, (204, 202, 196))
    # boru hattı
    y = h * 0.86
    A.box(w * 0.06, y, w * 0.88, 5, 5, "steel", parapet=False)


def _comms(A, w, h, lv, acc):
    A.box(w * 0.2, h * 0.62, w * 0.6, h * 0.3, 18, "concrete", "roof", windows=(1, 3, 41))
    A.lattice(w * 0.44, h * 0.42, 8, 44 + 8 * lv, "steel")


def _medical(A, w, h, lv, acc):
    A.box(w * 0.04, h * 0.14, w * 0.92, h * 0.76, 34 + 4 * lv, "panel", "roof", seams=16,
          windows=(3, 7, 51), roof_units=2)
    # çatıda helikopter pisti
    cx, cy, z = w * 0.62, h * 0.5, 34 + 4 * lv
    pts = [A.P(cx + math.cos(a) * h * 0.22, cy + math.sin(a) * h * 0.22, z + 0.5) for a in np.linspace(0, math.tau, 24)]
    pygame.draw.polygon(A.surf, A.lit((92, 96, 102), 1.0), [(round(a), round(b)) for a, b in pts])
    hx, hy = A.P(cx, cy, z + 0.5)
    font = pygame.font.Font(None, max(12, int(h * 0.26)))
    t = font.render("H", True, A.lit((220, 218, 210), 1.0))
    A.surf.blit(t, (round(hx - t.get_width() / 2), round(hy - t.get_height() / 2)))
    # kırmızı haç (soluk, uyumlu)
    x, yb = w * 0.04, h * 0.14 + h * 0.76
    ex, ey = A.P(x + w * 0.2, yb, (34 + 4 * lv) * 0.62)
    s = max(4, int(h * 0.07))
    red = A.lit((196, 64, 70), 1.0)
    pygame.draw.rect(A.surf, red, (round(ex - s * 0.35), round(ey - s), round(s * 0.7), s * 2))
    pygame.draw.rect(A.surf, red, (round(ex - s), round(ey - s * 0.35), s * 2, round(s * 0.7)))


def _rec(A, w, h, lv, acc):
    A.box(0, 0, w, h, 1.5, "grass", "grass", parapet=False, shadow=False)
    A.box(w * 0.55, h * 0.1, w * 0.38, h * 0.36, 1.2, "water", "water", parapet=False, shadow=False)
    A.box(w * 0.06, h * 0.62, w * 0.42, h * 0.3, 14, "panel", "roof", windows=(1, 4, 61))
    rng = random.Random(8)
    for i in range(8):
        A.tree(w * (0.08 + rng.random() * 0.45), h * (0.1 + rng.random() * 0.45), 7 + rng.random() * 4, 16 + rng.random() * 6)


def _pads(A, w, h, lv, acc, centers=()):
    A.box(0, 0, w, h, 2, "apron", "apron", parapet=False, shadow=False, joints=36)
    for i, (cx, cy, size) in enumerate(centers):
        open_ = lv >= i + 1
        s = size
        A.box(cx - s / 2, cy - s / 2, s, s, 5, "concrete2" if open_ else "apron", parapet=True, shadow=False)
        # alev çukuru
        q = [A.P(cx - s * 0.22, cy - s * 0.1, 5.2), A.P(cx + s * 0.22, cy - s * 0.1, 5.2),
             A.P(cx + s * 0.22, cy + s * 0.38, 5.2), A.P(cx - s * 0.22, cy + s * 0.38, 5.2)]
        A.poly(A.lit(MAT["dark"], 1.0), q)
        if open_:
            A.lattice(cx + s / 2 + 2, cy - s * 0.3, max(7, s * 0.14), 40 + 18 * i, "tower")
            # ışık direkleri
            for lx in (-0.5, 0.5):
                A.lattice(cx + lx * s, cy + s * 0.6, 2, 22, "steel_d")
        else:
            A.scaffold(cx - s * 0.3, cy - s * 0.3, s * 0.6, s * 0.6, 14)


BUILDERS = {"hangar": (_hangar, 150), "research": (_research, 90), "astro": (_astro, 60), "depot": (_depot, 40),
            "board": (_board, 30), "nova": (_nova, 80), "control": (_control, 60), "fuel": (_fuel, 70),
            "comms": (_comms, 90), "medical": (_medical, 50), "rec": (_rec, 30), "pads": (_pads, 100)}


def building(key, size, lv, night, accent, **extra):
    """Önbellekli bina modeli. Dönüş: (yüzey, (ox, oy)) — yüzey, ayak izi sol-üstü (r.x-ox, r.y-oy)'ye basılır."""
    w, h = int(size[0]), int(size[1])
    nb = round(night * 4) / 4
    ek = tuple(sorted((k, tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in extra.items()))
    ck = (key, w, h, lv, nb, tuple(accent), ek)
    hit = _CACHE.get(ck)
    if hit is not None:
        return hit
    fn, maxz = BUILDERS.get(key, (None, 40))
    A = Arch(w, h, maxz + 60, nb, seed=hash(key) % 997)
    if lv <= 0 and key not in ("pads",):
        A.scaffold(w * 0.12, h * 0.15, w * 0.76, h * 0.7, 26)
    elif fn is not None:
        if key == "pads":
            fn(A, w, h, lv, accent, centers=extra.get("centers", ()))
        elif key == "fuel":
            fn(A, w, h, lv, accent, n=extra.get("n", 3))
        else:
            fn(A, w, h, lv, accent)
    res = A.finish()
    if len(_CACHE) > 160:
        _CACHE.clear()
    _CACHE[ck] = res
    return res

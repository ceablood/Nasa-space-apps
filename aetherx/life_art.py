# -*- coding: utf-8 -*-
"""
AETHER-X // YAŞAM GÖRSELLERİ
Yaşam Motorunun verisinden çizilen görseller (hepsi prosedürel; dış görsel dosyası yok):
  * species_art  : türün figürü, genomundan türetilir — alem (bitki/mantar/mikrop/hayvan), yaşam alanı (kara/su/hava/
                   yeraltı/buzaltı), beden boyu (log10 m), beslenme (etçil: kırmızı vurgu), sosyallik. Gerçek gruplar
                   doğal renklerde, kurgusal türler farklı renk ailesinde.
  * Diorama      : seçili biyomun canlı kesiti — gökyüzü gezegenin atmosferinden, zemin biyomdan; canlılar sayısı
                   biyokütleyle orantılı olarak hareket eder; gün-gece döngüsü; fırtına ve olay canlandırmaları.
  * timeline_icon, event_icon: zaman şeridi ve olay düğmesi simgeleri.
Bu görseller temsilîdir (ölçeksiz çizim); bilgi panellerindeki sayılar Yaşam Motorundan gelir.
"""
import math
import random

import pygame

from .fx import clamp, draw_glow, lerp, scale_color


def _hash(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _hsv(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s, 0, 1), clamp(v, 0, 1))
    return int(r * 255), int(g * 255), int(b * 255)


def species_color(sp):
    """Doğal renk ailesi: gerçek gruplar Dünya renklerinde, kurgusal türler mor/turkuaz/altın ailesinde."""
    h = _hash(sp.name)
    j = (h % 1000) / 1000.0
    k = sp.kingdom
    if not sp.real:
        base = {"bitki": 0.47, "mantar": 0.83, "mikrop": 0.52, "hayvan": 0.75}.get(k, 0.6)
        return _hsv(base + (j - 0.5) * 0.25, 0.55, 0.85)
    base = {"bitki": 0.30, "mantar": 0.08, "mikrop": 0.15, "hayvan": 0.07}.get(k, 0.1)
    if k == "hayvan":
        return _hsv(base + (j - 0.5) * 0.12, 0.45 + j * 0.2, 0.55 + j * 0.3)
    return _hsv(base + (j - 0.5) * 0.08, 0.6, 0.6 + j * 0.25)


# ======================================================================== figürler
def species_art(surf, sp, cx, cy, size, t=0.0, alive=True, facing=1, phase=0.0):
    """Türün figürünü (cx, cy) alt-ortası (zemin) olacak şekilde çizer. size: piksel yükseklik."""
    g = sp.genome
    col = species_color(sp)
    if not alive:
        col = (90, 90, 96)
    dark = scale_color(col, 0.55)
    lite = tuple(min(255, int(c * 1.25 + 20)) for c in col)
    s = max(4.0, size)
    k = sp.kingdom
    ph = t * (1.0 + g.speed * 2) + phase
    if k == "bitki":
        if g.habitat in ("su", "buzaltı"):                          # yosun / deniz çayırı / plankton
            if g.size < -3:
                for i in range(5):
                    a = ph * 0.8 + i * 1.3
                    pygame.draw.circle(surf, lite, (int(cx + math.cos(a) * s * 0.25), int(cy - s * 0.5 + math.sin(a * 1.3) * s * 0.25)),
                                       max(1, int(s * 0.08)))
                return
            for i in range(3):
                x0 = cx + (i - 1) * s * 0.18
                pts = [(x0 + math.sin(ph * 1.4 + j * 0.7 + i) * s * 0.06 * j, cy - j * s * 0.24) for j in range(5)]
                pygame.draw.lines(surf, col, False, pts, max(2, int(s * 0.07)))
            return
        if g.size > 0.4:                                            # ağaç: gölgeli, katmanlı taç
            sway = math.sin(ph * 0.9) * s * 0.03
            shd = pygame.Surface((int(s * 0.9) + 2, int(s * 0.14) + 2), pygame.SRCALPHA)
            pygame.draw.ellipse(shd, (0, 0, 0, 70), shd.get_rect())
            surf.blit(shd, (cx - s * 0.45 + s * 0.12, cy - s * 0.06))
            tw = max(2, int(s * 0.09))
            pygame.draw.line(surf, (70, 50, 34) if alive else dark, (cx + tw * 0.3, cy), (cx + sway + tw * 0.3, cy - s * 0.55), tw)
            pygame.draw.line(surf, (112, 82, 56) if alive else dark, (cx - tw * 0.2, cy), (cx + sway - tw * 0.2, cy - s * 0.55), max(1, tw // 2))
            rng_ = random.Random(_hash(sp.name))
            clumps = [(0, -0.74, 0.28), (-0.22, -0.6, 0.21), (0.22, -0.62, 0.21), (0, -0.94, 0.19), (-0.12, -0.86, 0.17),
                      (0.14, -0.84, 0.17), (rng_.uniform(-0.25, 0.25), -0.68, 0.16)]
            deep = scale_color(col, 0.42)
            for dx, dy, r in clumps:                                       # gölge katmanı
                pygame.draw.circle(surf, deep, (int(cx + sway + dx * s + s * 0.03), int(cy + dy * s + s * 0.04)), max(2, int(r * s)))
            for dx, dy, r in clumps:                                       # orta ton
                pygame.draw.circle(surf, col, (int(cx + sway + dx * s), int(cy + dy * s)), max(2, int(r * s * 0.88)))
            for dx, dy, r in clumps:                                       # güneş tarafı (sol-üst) parlak
                pygame.draw.circle(surf, lite, (int(cx + sway + dx * s - r * s * 0.3), int(cy + dy * s - r * s * 0.3)), max(1, int(r * s * 0.42)))
            return
        if g.size > -2:                                             # çalı / ot
            for i in range(5):
                a = -math.pi / 2 + (i - 2) * 0.35 + math.sin(ph + i) * 0.08
                pygame.draw.line(surf, col, (cx, cy), (cx + math.cos(a) * s * 0.6, cy + math.sin(a) * s * 0.6), max(1, int(s * 0.06)))
            pygame.draw.circle(surf, lite, (int(cx), int(cy - s * 0.55)), max(1, int(s * 0.07)))
            return
        # mikroskobik üretici (siyanobakteri, alg): yeşil hücre kümesi
        for i in range(4):
            pygame.draw.circle(surf, col, (int(cx + (i - 1.5) * s * 0.2), int(cy - s * 0.25 - (i % 2) * s * 0.1)), max(2, int(s * 0.12)))
        return
    if k == "mantar":
        pygame.draw.rect(surf, (226, 214, 196) if alive else dark, (cx - s * 0.08, cy - s * 0.45, s * 0.16, s * 0.45))
        pygame.draw.ellipse(surf, col, (cx - s * 0.35, cy - s * 0.7, s * 0.7, s * 0.34))
        for i in range(3):
            pygame.draw.circle(surf, lite, (int(cx - s * 0.15 + i * s * 0.15), int(cy - s * 0.58)), max(1, int(s * 0.04)))
        return
    if k == "mikrop":                                               # hücre + kamçı
        r = s * 0.28
        y0 = cy - s * 0.4 + math.sin(ph * 2 + phase) * s * 0.08
        pts = [(cx - facing * (r + j * s * 0.07), y0 + math.sin(ph * 6 + j) * s * 0.06) for j in range(6)]
        pygame.draw.lines(surf, dark, False, pts, max(1, int(s * 0.04)))
        pygame.draw.ellipse(surf, col, (cx - r, y0 - r * 0.7, r * 2, r * 1.4))
        pygame.draw.ellipse(surf, lite, (cx - r * 0.75, y0 - r * 0.5, r * 1.5, r * 1.0), max(1, int(s * 0.03)))
        pygame.draw.circle(surf, dark, (int(cx + r * 0.2), int(y0)), max(1, int(r * 0.32)))
        return
    # ---------------- hayvanlar
    carn = g.diet == "etçil"
    eye = (250, 250, 240)
    if g.habitat in ("su", "buzaltı"):                              # balık / deniz canlısı
        L = s * 1.1
        y0 = cy - s * 0.5
        tail = math.sin(ph * 6) * L * 0.12
        pygame.draw.polygon(surf, dark, [(cx - facing * L * 0.42, y0), (cx - facing * L * 0.7, y0 - L * 0.2 + tail),
                                         (cx - facing * L * 0.7, y0 + L * 0.2 + tail)])
        pygame.draw.ellipse(surf, col, (cx - L * 0.45, y0 - L * 0.18, L * 0.9, L * 0.36))
        pygame.draw.polygon(surf, dark, [(cx - facing * L * 0.05, y0 - L * 0.16), (cx + facing * L * 0.12, y0 - L * 0.3),
                                         (cx + facing * L * 0.2, y0 - L * 0.14)])
        pygame.draw.circle(surf, eye, (int(cx + facing * L * 0.28), int(y0 - L * 0.04)), max(1, int(L * 0.05)))
        if carn:
            pygame.draw.line(surf, (230, 70, 70), (cx + facing * L * 0.36, y0 + L * 0.06), (cx + facing * L * 0.45, y0 + L * 0.04), 2)
        return
    if g.habitat == "hava":                                         # kuş / uçan canlı
        y0 = cy - s * 0.5
        flap = math.sin(ph * 8)
        w = s * 0.7
        pygame.draw.lines(surf, dark, False, [(cx - w, y0 - flap * w * 0.5), (cx - w * 0.3, y0 - w * 0.08), (cx, y0)], max(2, int(s * 0.08)))
        pygame.draw.lines(surf, dark, False, [(cx + w, y0 - flap * w * 0.5), (cx + w * 0.3, y0 - w * 0.08), (cx, y0)], max(2, int(s * 0.08)))
        pygame.draw.ellipse(surf, col, (cx - s * 0.22, y0 - s * 0.1, s * 0.44, s * 0.22))
        pygame.draw.polygon(surf, (240, 190, 60), [(cx + facing * s * 0.22, y0 - s * 0.03), (cx + facing * s * 0.34, y0),
                                                   (cx + facing * s * 0.22, y0 + s * 0.04)])
        return
    if g.size < -1.8:                                               # böcek / küçük eklem bacaklı
        y0 = cy - s * 0.3
        for i in range(3):
            lx = cx + (i - 1) * s * 0.18
            off = math.sin(ph * 12 + i * 2) * s * 0.06
            pygame.draw.line(surf, dark, (lx, y0), (lx - s * 0.12 + off, cy), max(1, int(s * 0.04)))
            pygame.draw.line(surf, dark, (lx, y0), (lx + s * 0.12 - off, cy), max(1, int(s * 0.04)))
        pygame.draw.ellipse(surf, col, (cx - s * 0.35, y0 - s * 0.14, s * 0.55, s * 0.28))
        pygame.draw.circle(surf, dark, (int(cx + facing * s * 0.28), int(y0)), max(2, int(s * 0.11)))
        return
    if g.habitat == "yeraltı" or g.size < -0.5:                      # küçük memeli / sürüngen / solucan
        y0 = cy - s * 0.28
        hop = abs(math.sin(ph * 6)) * s * 0.06
        pygame.draw.ellipse(surf, col, (cx - s * 0.4, y0 - s * 0.2 - hop, s * 0.8, s * 0.4))
        pygame.draw.circle(surf, col, (int(cx + facing * s * 0.4), int(y0 - s * 0.12 - hop)), max(2, int(s * 0.17)))
        pygame.draw.circle(surf, eye, (int(cx + facing * s * 0.46), int(y0 - s * 0.16 - hop)), max(1, int(s * 0.04)))
        pygame.draw.line(surf, dark, (cx - facing * s * 0.4, y0 - hop), (cx - facing * s * 0.62, y0 - s * 0.12 - hop), max(1, int(s * 0.05)))
        return
    # büyük kara hayvanı (dört ayaklı)
    y0 = cy - s * 0.5
    stride = math.sin(ph * 5) * s * 0.12
    for i, lx in enumerate((-0.3, -0.18, 0.2, 0.32)):
        sw = stride if i % 2 == 0 else -stride
        pygame.draw.line(surf, dark, (cx + lx * s, y0 + s * 0.1), (cx + lx * s + sw * facing, cy), max(2, int(s * 0.09)))
    pygame.draw.ellipse(surf, col, (cx - s * 0.45, y0 - s * 0.18, s * 0.9, s * 0.38))
    hx, hy = cx + facing * s * 0.5, y0 - s * 0.22
    pygame.draw.line(surf, col, (cx + facing * s * 0.32, y0 - s * 0.05), (hx, hy), max(3, int(s * 0.16)))
    pygame.draw.circle(surf, col, (int(hx), int(hy)), max(2, int(s * 0.15)))
    pygame.draw.circle(surf, eye, (int(hx + facing * s * 0.05), int(hy - s * 0.04)), max(1, int(s * 0.035)))
    pygame.draw.line(surf, dark, (cx - facing * s * 0.45, y0 - s * 0.05), (cx - facing * s * 0.62, y0 + s * 0.1), max(1, int(s * 0.05)))
    if carn:
        pygame.draw.line(surf, (230, 70, 70), (hx + facing * s * 0.08, hy + s * 0.06), (hx + facing * s * 0.16, hy + s * 0.06), 2)
    if g.social > 0.6:
        pygame.draw.circle(surf, lite, (int(cx), int(y0 - s * 0.3)), max(1, int(s * 0.04)))


def species_portrait(surf, sp, rect, t, figure=True):
    """Detay panelinde büyük figür: yaşam alanına uygun küçük arka plan + figür."""
    r = pygame.Rect(rect)
    g = sp.genome
    top, bot = {"su": ((20, 60, 110), (8, 24, 54)), "buzaltı": ((40, 70, 110), (10, 20, 40)), "hava": ((90, 150, 220), (190, 210, 240)),
                "yeraltı": ((50, 38, 30), (24, 18, 14))}.get(g.habitat, ((70, 120, 190), (150, 180, 200)))
    sub = pygame.Surface(r.size)
    for y in range(r.h):
        k = y / max(1, r.h - 1)
        pygame.draw.line(sub, tuple(int(lerp(a, b, k)) for a, b in zip(top, bot)), (0, y), (r.w, y))
    if g.habitat == "kara":
        pygame.draw.rect(sub, (70, 96, 60), (0, int(r.h * 0.78), r.w, r.h))
    elif g.habitat == "yeraltı":
        pygame.draw.rect(sub, (40, 30, 24), (0, int(r.h * 0.78), r.w, r.h))
    surf.blit(sub, r.topleft)
    gy = r.y + int(r.h * (0.8 if g.habitat in ("kara", "yeraltı") else 0.72))
    if figure:
        species_art(surf, sp, r.centerx, gy, r.h * 0.62, t, sp.alive)
    pygame.draw.rect(surf, (90, 120, 150), r, 1, border_radius=6)


# ======================================================================== diorama
SKY = {"earth": ((70, 130, 210), (170, 205, 235)), "mars": ((150, 110, 80), (214, 170, 120)), "venus": ((150, 120, 50), (226, 196, 120)),
       "moon": ((2, 3, 8), (10, 12, 20)), "jupiter": ((150, 110, 80), (220, 190, 150))}
WATER_BIOMES = ("okyanus", "resif", "buz altı okyanusu")
GROUND = {"tropikal orman": ((40, 96, 46), (22, 60, 30)), "çöl": ((214, 180, 120), (180, 140, 90)), "buzul": ((226, 236, 246), (180, 200, 220)),
          "volkanik bölge": ((50, 40, 40), (26, 20, 20)), "regolit ovası": ((130, 128, 124), (90, 88, 86)),
          "kalıcı gölgeli krater": ((50, 52, 58), (24, 24, 30)), "toz ovası": ((180, 110, 70), (130, 74, 46)),
          "kutup buzulu": ((230, 224, 220), (190, 180, 176)), "kanyon": ((170, 90, 60), (110, 56, 38)),
          "volkanik ova": ((120, 90, 60), (70, 50, 34)), "tessera yayla": ((140, 110, 76), (90, 70, 50)),
          "sıcak su kaynakları": ((150, 130, 100), (100, 86, 64)), "tuz ovası": ((236, 232, 222), (200, 196, 186)),
          "çorak ova": ((110, 100, 90), (70, 64, 58)), "yer altı mağaraları": ((60, 50, 44), (30, 24, 22)), "bulut kuşağı": None}


def sky_colors(env, key):
    if key in SKY:
        return SKY[key]
    a = env.atmosphere
    if not env.pressure_bar or env.pressure_bar < 0.01:
        return (4, 6, 14), (14, 16, 26)
    if a.get("SO2", 0) > 0.01:
        return (150, 130, 50), (220, 200, 110)
    if a.get("CH4", 0) > 0.02:
        return (60, 120, 130), (150, 200, 200)
    if a.get("CO2", 0) > 0.4:
        return (150, 100, 70), (220, 170, 120)
    return (60, 120, 200), (160, 200, 235)


# --------------------------------------------------------------------- 3B sprite bütçesi
BUDGET = {"n": 0}          # karede en çok bir yeni 3B çizim (akıcılık); hazır olana kadar 2B figür kullanılır


def new_frame():
    BUDGET["n"] = 1


def sprite3d(sp, size, facing=1):
    """Biyom kesiti için küçük 3B hayvan (sağa ya da sola dönük)."""
    from . import creature3d as C3
    px = int(max(40, min(120, size * 2.8)) // 8 * 8)
    step = 0 if facing >= 0 else 12
    if C3.is_cached(sp, px, step, 24, -0.25, 2):
        return C3.surface(sp, px, step, 24, -0.25, 2)
    if BUDGET["n"] > 0:
        BUDGET["n"] -= 1
        return C3.surface(sp, px, step, 24, -0.25, 2)
    return None


def card3d(sp, px):
    """Kart görseli: 2x süper örneklemeli tek açı."""
    from . import creature3d as C3
    if C3.is_cached(sp, px, 1, 24, -0.3, 2) or BUDGET["n"] > 0:
        if not C3.is_cached(sp, px, 1, 24, -0.3, 2):
            BUDGET["n"] -= 1
        return C3.surface(sp, px, 1, 24, -0.3, 2)
    return None


def portrait3d(sp, size, t, ss=1, steps=24):
    """Dönen 3B portre: açı adımı zamana göre; yeni açı bütçe varsa çizilir, yoksa en son hazır açı gösterilir."""
    from . import creature3d as C3
    want = int(t * 6) % steps
    for k in range(steps):
        st = (want - k) % steps
        if C3.is_cached(sp, size, st, steps, -0.32, ss):
            if k and BUDGET["n"] > 0:
                BUDGET["n"] -= 1
                return C3.surface(sp, size, want, steps, -0.32, ss)
            return C3.surface(sp, size, st, steps, -0.32, ss)
    BUDGET["n"] -= 1
    return C3.surface(sp, size, want, steps, -0.32, ss)


class Diorama:
    """Biyomun canlı kesiti. Statik katman önbellekte; canlılar her karede hareket eder."""

    def __init__(self):
        self.key = None
        self.bg = None
        self.agents = []
        self.sig = None
        self.rng = random.Random(1)
        self.stars = []

    # -------------------------------------------------------------- statik katman
    def _build_bg(self, world, biome, w, h):
        env = world.env
        surf = pygame.Surface((w, h))
        top, bot = sky_colors(env, world.key)
        water = biome in WATER_BIOMES
        if water:
            top, bot = (30, 110, 160), (6, 26, 60)
            if biome == "buz altı okyanusu":
                top, bot = (60, 90, 120), (6, 14, 30)
        for y in range(h):
            k = y / max(1, h - 1)
            pygame.draw.line(surf, tuple(int(lerp(a, b, k)) for a, b in zip(top, bot)), (0, y), (w, y))
        rng = random.Random(_hash(f"{world.key}{biome}"))
        self.stars = [(rng.randrange(w), rng.randrange(int(h * 0.6)), rng.random()) for _ in range(70)] \
            if (not env.pressure_bar or env.pressure_bar < 0.01) else []
        self.ground_y = int(h * 0.74)
        gy = self.ground_y
        if biome == "bulut kuşağı":                                  # Jüpiter: zemin yok, bulut bantları
            for i in range(7):
                yy = int(h * (0.15 + i * 0.13))
                col = [(230, 200, 160), (200, 150, 110), (240, 226, 200), (180, 120, 90)][i % 4]
                pts = [(x, yy + math.sin(x * 0.02 + i) * 8) for x in range(0, w + 20, 20)]
                pygame.draw.lines(surf, col, False, pts, 14)
            self.ground_y = h - 6
            return surf
        if water:
            for i in range(9):                                       # ışık huzmeleri
                x = rng.randrange(w)
                pygame.draw.polygon(surf, (40, 130, 180) if biome != "buz altı okyanusu" else (60, 90, 120),
                                    [(x, 0), (x + 30, 0), (x + 90, gy), (x + 50, gy)])
            sand = (194, 170, 120) if biome != "buz altı okyanusu" else (60, 64, 70)
            pts = [(0, h)] + [(x, gy + 10 + math.sin(x * 0.03) * 5) for x in range(0, w + 10, 10)] + [(w, h)]
            pygame.draw.polygon(surf, sand, pts)
            if biome == "resif":
                for _ in range(14):
                    x = rng.randrange(w)
                    c = rng.choice([(240, 110, 120), (250, 170, 90), (180, 120, 230), (120, 220, 200)])
                    for j in range(5):
                        pygame.draw.circle(surf, c, (x + rng.randint(-12, 12), gy + 6 - j * 6 - rng.randint(0, 8)), rng.randint(3, 7))
            if biome == "buz altı okyanusu":
                pygame.draw.rect(surf, (200, 220, 236), (0, 0, w, 18))
                for x in range(0, w, 24):
                    pygame.draw.polygon(surf, (170, 196, 220), [(x, 18), (x + 12, 18 + rng.randint(6, 26)), (x + 24, 18)])
            return surf
        g1, g2 = GROUND.get(biome) or ((110, 100, 90), (70, 64, 58))
        # gerçekçi katmanlı arazi: uzaktan yakına 3 sırt; hava perspektifi (uzak = gökyüzüne karışır), eğime göre gölge
        self._layers(surf, world, biome, w, h, gy, g1, top, bot, rng)
        if biome == "kanyon":
            for i in range(5):
                c = scale_color(g1, 0.8 + 0.1 * (i % 2))
                pygame.draw.rect(surf, c, (0, gy - 80 + i * 16, int(w * 0.3), 16))
                pygame.draw.rect(surf, c, (int(w * 0.72), gy - 80 + i * 16, w, 16))
        if biome in ("volkanik bölge", "volkanik ova"):
            vx = int(w * 0.7)
            pygame.draw.polygon(surf, (44, 34, 34), [(vx - 120, gy), (vx - 20, gy - 110), (vx + 20, gy - 110), (vx + 130, gy)])
            pygame.draw.line(surf, (255, 120, 40), (vx, gy - 108), (vx - 30, gy - 40), 3)
            pygame.draw.line(surf, (255, 160, 60), (vx + 6, gy - 108), (vx + 40, gy - 30), 2)
        self._ground(surf, w, h, gy, g1, g2, bot, rng)
        if biome in ("regolit ovası", "kalıcı gölgeli krater", "toz ovası"):
            for _ in range(8):
                cx, cy, r = rng.randrange(w), rng.randint(gy + 8, h - 8), rng.randint(6, 22)
                pygame.draw.ellipse(surf, scale_color(g1, 0.7), (cx - r, cy - r * 0.3, r * 2, r * 0.6))
                pygame.draw.ellipse(surf, scale_color(g1, 1.15), (cx - r, cy - r * 0.3, r * 2, r * 0.6), 1)
        if biome == "çöl":
            for i in range(3):
                pts = [(x, gy + 10 + i * 14 + math.sin(x * 0.02 + i * 2) * 5) for x in range(0, w + 10, 10)]
                pygame.draw.lines(surf, scale_color(g1, 1.08), False, pts, 2)
        if biome == "sıcak su kaynakları":
            for _ in range(3):
                cx = rng.randrange(60, w - 60)
                pygame.draw.ellipse(surf, (60, 170, 200), (cx - 40, gy + 14, 80, 18))
                pygame.draw.ellipse(surf, (240, 180, 60), (cx - 46, gy + 11, 92, 24), 3)
        if biome == "tuz ovası":
            for _ in range(30):
                x, y = rng.randrange(w), rng.randint(gy + 4, h - 4)
                pygame.draw.polygon(surf, (210, 204, 192), [(x, y), (x + 14, y + 3), (x + 4, y + 6)], 1)
        if biome in ("buzul", "kutup buzulu"):
            for _ in range(6):
                x = rng.randrange(w)
                pygame.draw.polygon(surf, (200, 220, 240), [(x, gy), (x + 18, gy - rng.randint(18, 40)), (x + 36, gy)])
        if biome == "yer altı mağaraları":
            pygame.draw.rect(surf, (24, 20, 18), (0, 0, w, 26))
            for x in range(0, w, 30):
                pygame.draw.polygon(surf, (30, 24, 22), [(x, 26), (x + 15, 26 + rng.randint(10, 46)), (x + 30, 26)])
        return surf

    # -------------------------------------------------------------- gerçekçi arka plan yardımcıları
    @staticmethod
    def _noise2(w, h, cell, seed):
        """Yumuşak 2B gürültü (0..1): küçük rastgele ızgara büyütülerek (çift doğrusal)."""
        import numpy as np
        rng = np.random.default_rng(seed)
        gw, gh = max(2, w // cell + 2), max(2, h // cell + 2)
        g = (rng.random((gw, gh)) * 255).astype(np.uint8)
        sm = pygame.surfarray.make_surface(np.stack([g] * 3, -1))
        big = pygame.transform.smoothscale(sm, (w, h))
        return pygame.surfarray.array3d(big)[..., 0].astype(np.float32) / 255.0

    def _layers(self, surf, world, biome, w, h, gy, g1, top, bot, rng):
        import numpy as np
        env = world.env
        thick = 0.0 if (not env.pressure_bar or env.pressure_bar < 0.01) else min(1.0, 0.3 + 0.25 * math.log10(1 + env.pressure_bar * 10))
        # bulutlar (atmosferli gezegenler): yumuşak gürültü eşiği
        if thick > 0.2:
            n = self._noise2(w, int(gy * 0.75), 40, rng.randrange(10 ** 6)) * 0.6 + self._noise2(w, int(gy * 0.75), 14, rng.randrange(10 ** 6)) * 0.4
            a = np.clip((n - 0.55) * 3.2, 0, 1) * 150 * thick
            cl = pygame.Surface((w, int(gy * 0.75)), pygame.SRCALPHA)
            px = pygame.surfarray.pixels3d(cl)
            cc = np.array((250, 250, 255) if world.key != "mars" else (230, 200, 170), np.float32)
            px[...] = (cc * (0.85 + 0.15 * n[..., None])).astype(np.uint8)
            del px
            pa = pygame.surfarray.pixels_alpha(cl)
            pa[...] = a.astype(np.uint8)
            del pa
            surf.blit(cl, (0, 0))
        xs = np.arange(w + 1)
        for li, (base, amp, haze, freq) in enumerate(((gy - 70, 46, 0.62, 0.006), (gy - 38, 30, 0.38, 0.011), (gy - 14, 16, 0.16, 0.02))):
            ph = [rng.uniform(0, 6.28) for _ in range(4)]
            ridge = base - amp * (0.55 * np.sin(xs * freq + ph[0]) + 0.3 * np.sin(xs * freq * 2.3 + ph[1])
                                  + 0.15 * np.abs(np.sin(xs * freq * 5.1 + ph[2])) + 0.1 * np.sin(xs * freq * 11 + ph[3]))
            slope = np.gradient(ridge)
            col = np.array(g1, np.float32) * (0.75 + 0.1 * li)
            sky = np.array(bot, np.float32)
            for x in range(0, w, 2):
                y0 = int(ridge[x])
                if y0 >= gy:
                    continue
                shade = float(np.clip(1.0 - slope[x] * 0.06, 0.7, 1.25))       # güneş solda: sola bakan yamaç aydınlık
                c = col * shade
                c = c + (sky - c) * (haze * (0.6 + 0.4 * thick) if thick > 0 else haze * 0.25)
                pygame.draw.line(surf, tuple(int(v) for v in np.clip(c, 0, 255)), (x, y0), (x, gy), 2)
        # ufuk pusu
        if thick > 0:
            hz = pygame.Surface((w, 40), pygame.SRCALPHA)
            for i in range(40):
                pygame.draw.line(hz, (*bot, int(90 * thick * (1 - abs(i - 20) / 20))), (0, i), (w, i))
            surf.blit(hz, (0, gy - 34))

    def _ground(self, surf, w, h, gy, g1, g2, bot, rng):
        """Dokulu zemin: renk geçişi + iki ölçekli gürültü + çakıl."""
        import numpy as np
        gh = h - gy
        if gh <= 0:
            return
        yy = np.linspace(0, 1, gh, dtype=np.float32)[None, :, None]
        base = np.array(g1, np.float32)[None, None, :] * (1 - yy) + np.array(g2, np.float32)[None, None, :] * yy
        n = self._noise2(w, gh, 22, rng.randrange(10 ** 6)) * 0.6 + self._noise2(w, gh, 5, rng.randrange(10 ** 6)) * 0.4
        img = base * (0.82 + 0.36 * n[..., None])
        top_haze = np.clip(1 - yy * 6, 0, 1) * 0.25                               # uzak zemin gökyüzüne karışır
        img = img + (np.array(bot, np.float32)[None, None, :] - img) * top_haze
        gs = pygame.surfarray.make_surface(np.clip(img, 0, 255).astype(np.uint8))
        surf.blit(gs, (0, gy))
        for _ in range(60):                                                         # çakıllar (yakında büyük)
            y = rng.randint(gy + 4, h - 2)
            k = (y - gy) / max(1, gh)
            r = 1 + int(k * 4 * rng.random())
            x = rng.randrange(w)
            pygame.draw.ellipse(surf, scale_color(g2, 0.55), (x - r, y - r * 0.4 + 1, r * 2, r * 0.9))
            pygame.draw.ellipse(surf, scale_color(g1, 1.15), (x - r, y - r * 0.5, r * 2 - 1, r * 0.7))

    # -------------------------------------------------------------- canlı ajanlar
    def _agents(self, world, biome, w, h):
        rng = random.Random(_hash(f"{world.key}{biome}") + 3)
        out = []
        sp = [s for s in world.species if s.biome == biome and s.alive]
        water = biome in WATER_BIOMES
        for s in sp:
            n = int(clamp(1 + math.log10(1 + s.biomass) * 2.4, 1, 9))
            g = s.genome
            for i in range(n):
                kind = "sabit"
                if s.kingdom == "hayvan":
                    kind = "yüz" if (g.habitat in ("su", "buzaltı") or water) else ("uç" if g.habitat == "hava" else "yürü")
                elif s.kingdom == "mikrop":
                    kind = "süzül"
                size = clamp(12 + (g.size + 3) * 6, 9, 46)
                if s.kingdom == "bitki" and g.size > 0.4:
                    size = clamp(40 + g.size * 14, 40, 84)
                if s.kingdom == "mikrop" or (s.kingdom == "bitki" and g.size < -2):
                    size = rng.uniform(8, 12)
                x = rng.uniform(10, w - 10)
                if kind == "uç":
                    y = rng.uniform(h * 0.12, h * 0.5)
                elif kind in ("yüz", "süzül") and water:
                    y = rng.uniform(h * 0.2, self.ground_y)
                elif kind == "süzül":
                    y = self.ground_y + rng.uniform(4, (h - self.ground_y) * 0.8)
                else:
                    y = self.ground_y + rng.uniform(2, (h - self.ground_y) * 0.55)
                out.append({"sp": s, "x": x, "y": y, "vx": rng.choice((-1, 1)) * (10 + g.speed * 40) * (0.6 + rng.random() * 0.6),
                            "kind": kind, "size": size, "ph": rng.random() * 6})
        out.sort(key=lambda a: (a["kind"] != "sabit", a["y"]))
        return out

    def draw(self, surf, rect, world, biome, t, dt=1 / 30, event=None, storm=0.0, night=None):
        r = pygame.Rect(rect)
        w, h = r.size
        key = (world.key, biome, w, h, id(world))
        if key != self.key:
            self.key = key
            self.bg = self._build_bg(world, biome, w, h)
            self.sig = None
        sig = tuple((s.sid, round(math.log10(1 + s.biomass), 1), s.alive) for s in world.species if s.biome == biome)
        if sig != self.sig:
            self.sig = sig
            self.agents = self._agents(world, biome, w, h)
        canvas = self.bg.copy()
        # gün-gece: güneş/yıldız ve karartma
        day = 0.5 + 0.5 * math.sin(t * 0.08) if night is None else (0.0 if night else 1.0)
        if not self.stars:
            sx = int(w * (0.1 + 0.8 * ((t * 0.08 / math.pi) % 1.0)))
            draw_glow(canvas, (sx, int(h * 0.18)), 40, (255, 240, 200), 0.5 * day)
            pygame.draw.circle(canvas, (255, 246, 220), (sx, int(h * 0.18)), 9)
        for x, y, b in self.stars:
            c = int(120 + 120 * b * (0.7 + 0.3 * math.sin(t * 2 + x)))
            canvas.set_at((x, y), (c, c, c))
        water = biome in WATER_BIOMES
        for a in self.agents:
            s = a["sp"]
            if a["kind"] != "sabit":
                a["x"] += a["vx"] * dt
                if a["x"] < 6 or a["x"] > w - 6:
                    a["vx"] = -a["vx"]
                    a["x"] = clamp(a["x"], 6, w - 6)
            yy = a["y"]
            if a["kind"] == "uç":
                yy += math.sin(t * 1.5 + a["ph"]) * 10
            elif a["kind"] in ("yüz", "süzül"):
                yy += math.sin(t * 1.1 + a["ph"]) * 5
            img = sprite3d(s, a["size"], 1 if a["vx"] >= 0 else -1) if s.kingdom == "hayvan" else None
            if img is not None:                                       # gerçekçi 3B hayvan (önbellekli)
                bob = abs(math.sin(t * 6 + a["ph"])) * 1.5 if a["kind"] == "yürü" else 0
                canvas.blit(img, (int(a["x"] - img.get_width() / 2), int(yy - img.get_height() * 0.78 - bob)))
            else:
                species_art(canvas, s, a["x"], yy, a["size"], t, True, 1 if a["vx"] >= 0 else -1, a["ph"])
            if s.kingdom == "mikrop" and water:
                draw_glow(canvas, (int(a["x"]), int(yy - a["size"] * 0.4)), 8, (120, 255, 200), 0.25)
        if storm > 0.05:                                             # yağmur / toz fırtınası
            rng = random.Random(int(t * 20))
            dust = world.key == "mars" or (world.env.pressure_bar or 0) < 0.05
            col = (210, 150, 100) if dust else (180, 200, 230)
            for _ in range(int(80 * storm)):
                x, y = rng.randrange(w), rng.randrange(h)
                pygame.draw.line(canvas, col, (x, y), (x - 6, y + (4 if dust else 14)), 1)
        if event:
            self._event_fx(canvas, event, w, h, t)
        shade = int(150 * (1 - day)) if not water else int(60 * (1 - day))
        if shade > 4:
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((6, 10, 30, shade))
            canvas.blit(ov, (0, 0))
        surf.blit(canvas, r.topleft)
        pygame.draw.rect(surf, (80, 110, 140), r, 1, border_radius=4)

    # -------------------------------------------------------------- olay efektleri
    def _event_fx(self, c, ev, w, h, t):
        kind, age = ev            # age: olaydan bu yana sn (0..6)
        k = clamp(1 - age / 6.0, 0, 1)
        gy = self.ground_y
        if kind == "meteor":
            if age < 1.2:
                p = age / 1.2
                x0, y0 = w * 0.1, -20
                x1, y1 = w * 0.62, gy
                x, y = lerp(x0, x1, p), lerp(y0, y1, p)
                for i in range(10):
                    q = max(0.0, p - i * 0.02)
                    pygame.draw.circle(c, (255, 200 - i * 12, 120 - i * 10), (int(lerp(x0, x1, q)), int(lerp(y0, y1, q))), max(1, 7 - i // 2))
                draw_glow(c, (int(x), int(y)), 30, (255, 220, 150), 0.8)
            else:
                draw_glow(c, (int(w * 0.62), gy), int(60 + 140 * (age - 1.2)), (255, 180, 100), 0.9 * k)
                pygame.draw.ellipse(c, (40, 30, 26), (w * 0.62 - 50, gy - 6, 100, 18))
                fl = pygame.Surface((w, h), pygame.SRCALPHA)
                fl.fill((255, 240, 220, int(160 * max(0.0, 1 - (age - 1.2) * 2))))
                c.blit(fl, (0, 0))
        elif kind == "volkan":
            vx = int(w * 0.7)
            for i in range(26):
                a = -math.pi / 2 + math.sin(i * 1.7) * 0.5
                d = (age * 60 + i * 9) % 140
                pygame.draw.circle(c, (90 + i * 3, 80, 76), (int(vx + math.cos(a) * d), int(gy - 110 + math.sin(a) * d)), int(6 + d * 0.12))
            for i in range(12):
                d = (age * 120 + i * 17) % 90
                pygame.draw.circle(c, (255, 140 - i * 5, 40), (int(vx + (i - 6) * d * 0.08), int(gy - 110 - d + d * d * 0.01)), 3)
            draw_glow(c, (vx, gy - 110), 60, (255, 120, 40), 0.7 * k)
        elif kind == "buzul":
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((210, 230, 255, int(110 * k)))
            c.blit(ov, (0, 0))
            rng = random.Random(int(t * 10))
            for _ in range(60):
                pygame.draw.circle(c, (250, 250, 255), (rng.randrange(w), rng.randrange(h)), 2)
        elif kind in ("kuraklik", "sicak"):
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((255, 160, 60, int(90 * k)))
            c.blit(ov, (0, 0))
            if kind == "kuraklik":
                rng = random.Random(4)
                for _ in range(14):
                    x, y = rng.randrange(w), rng.randint(gy + 6, h - 6)
                    pygame.draw.lines(c, (80, 60, 40), False, [(x, y), (x + 10, y + 4), (x + 18, y - 2), (x + 26, y + 5)], 1)
        elif kind == "atmosfer":
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((170, 150, 110, int(100 * k)))
            c.blit(ov, (0, 0))
        elif kind == "deniz":
            lvl = int(gy - 30 * min(1.0, age / 2))
            ov = pygame.Surface((w, h - lvl), pygame.SRCALPHA)
            ov.fill((40, 110, 170, int(120 * k)))
            c.blit(ov, (0, lvl))
        elif kind in ("radyasyon", "yildiz"):
            fl = pygame.Surface((w, h), pygame.SRCALPHA)
            a = int((140 if kind == "yildiz" else 70) * k * (0.6 + 0.4 * math.sin(t * 20)))
            fl.fill((255, 250, 210, a) if kind == "yildiz" else (120, 255, 140, a))
            c.blit(fl, (0, 0))
            rng = random.Random(int(t * 15))
            for _ in range(30):
                x, y = rng.randrange(w), rng.randrange(h)
                pygame.draw.line(c, (180, 255, 180), (x, y), (x + 3, y + 8), 1)
        elif kind == "firtina":
            if int(t * 3) % 5 == 0:
                x = int(w * 0.3 + math.sin(t) * w * 0.3)
                pts, y = [(x, 0)], 0
                rng = random.Random(int(t))
                while y < gy:
                    y += rng.randint(14, 30)
                    x += rng.randint(-18, 18)
                    pts.append((x, y))
                pygame.draw.lines(c, (240, 240, 255), False, pts, 2)


# ======================================================================== simgeler
def event_icon(surf, kind, center, size, color):
    x, y = center
    s = size
    if kind == "volkan":
        pygame.draw.polygon(surf, color, [(x - s * 0.5, y + s * 0.4), (x - s * 0.12, y - s * 0.2), (x + s * 0.12, y - s * 0.2), (x + s * 0.5, y + s * 0.4)], 2)
        for i in range(3):
            pygame.draw.circle(surf, color, (int(x - s * 0.1 + i * s * 0.1), int(y - s * 0.35 - i * s * 0.08)), max(2, int(s * 0.08)))
    elif kind == "meteor":
        pygame.draw.circle(surf, color, (int(x + s * 0.2), int(y + s * 0.2)), max(3, int(s * 0.2)), 2)
        for i in range(3):
            pygame.draw.line(surf, color, (x + s * 0.05 - i * s * 0.1, y + s * 0.05 - i * s * 0.05), (x - s * 0.45 - i * s * 0.05, y - s * 0.45 + i * s * 0.1), 2)
    elif kind == "kuraklik":
        pygame.draw.circle(surf, color, (int(x), int(y - s * 0.1)), max(3, int(s * 0.22)), 2)
        pygame.draw.lines(surf, color, False, [(x - s * 0.45, y + s * 0.4), (x - s * 0.15, y + s * 0.3), (x, y + s * 0.42), (x + s * 0.2, y + s * 0.3), (x + s * 0.45, y + s * 0.4)], 2)
    elif kind == "buzul":
        for i in range(3):
            a = i * math.pi / 3
            pygame.draw.line(surf, color, (x - math.cos(a) * s * 0.42, y - math.sin(a) * s * 0.42), (x + math.cos(a) * s * 0.42, y + math.sin(a) * s * 0.42), 2)
    elif kind == "sicak":
        pygame.draw.line(surf, color, (x, y - s * 0.4), (x, y + s * 0.2), 3)
        pygame.draw.circle(surf, color, (int(x), int(y + s * 0.28)), max(3, int(s * 0.14)))
    elif kind == "atmosfer":
        for i in range(3):
            pygame.draw.arc(surf, color, (x - s * 0.45, y - s * 0.3 + i * s * 0.2, s * 0.9, s * 0.3), 0.2, 2.9, 2)
    elif kind == "deniz":
        for i in range(2):
            pts = [(x - s * 0.45 + j * s * 0.15, y + i * s * 0.25 + math.sin(j * 1.6) * s * 0.06) for j in range(7)]
            pygame.draw.lines(surf, color, False, pts, 2)
    elif kind == "radyasyon":
        pygame.draw.circle(surf, color, (int(x), int(y)), max(2, int(s * 0.08)))
        for i in range(3):
            a = i * 2 * math.pi / 3 - math.pi / 2
            pygame.draw.arc(surf, color, (x - s * 0.42, y - s * 0.42, s * 0.84, s * 0.84), a - 0.45, a + 0.45, 4)
    elif kind == "yildiz":
        for i in range(8):
            a = i * math.pi / 4
            r0 = s * (0.45 if i % 2 == 0 else 0.28)
            pygame.draw.line(surf, color, (x, y), (x + math.cos(a) * r0, y + math.sin(a) * r0), 2)
    elif kind == "firtina":
        pygame.draw.ellipse(surf, color, (x - s * 0.45, y - s * 0.4, s * 0.9, s * 0.4), 2)
        pygame.draw.lines(surf, color, False, [(x + s * 0.05, y), (x - s * 0.1, y + s * 0.22), (x + s * 0.06, y + s * 0.22), (x - s * 0.08, y + s * 0.45)], 2)


ERAS = [  # (milyar yıl önce, simge, kısa ad) — Dünya: yayımlanmış tarihler (NASA / jeolojik zaman ölçeği)
    (4.54, "planet", "Dünya oluştu"), (3.7, "cell", "İlk yaşam izleri"), (2.4, "o2", "Büyük Oksijenlenme"),
    (1.6, "multi", "Çok hücreli"), (0.538, "cambrian", "Kambriyen patlaması"), (0.47, "plant", "Karaya bitkiler"),
    (0.252, "extinct", "Permiyen yok oluşu"), (0.066, "meteor", "K-Pg çarpması"), (0.0003, "human", "Homo sapiens")]


def era_icon(surf, kind, center, s, color):
    x, y = center
    if kind == "planet":
        pygame.draw.circle(surf, color, (int(x), int(y)), int(s * 0.4), 2)
        pygame.draw.arc(surf, color, (x - s * 0.55, y - s * 0.15, s * 1.1, s * 0.3), 3.3, 6.1, 1)
    elif kind == "cell":
        pygame.draw.ellipse(surf, color, (x - s * 0.4, y - s * 0.25, s * 0.8, s * 0.5), 2)
        pygame.draw.circle(surf, color, (int(x + s * 0.08), int(y)), max(2, int(s * 0.1)))
    elif kind == "o2":
        pygame.draw.circle(surf, color, (int(x - s * 0.16), int(y)), int(s * 0.22), 2)
        pygame.draw.circle(surf, color, (int(x + s * 0.16), int(y)), int(s * 0.22), 2)
    elif kind == "multi":
        for dx, dy in ((-0.15, -0.12), (0.15, -0.12), (0, 0.14)):
            pygame.draw.circle(surf, color, (int(x + dx * s), int(y + dy * s)), int(s * 0.16), 2)
    elif kind == "cambrian":
        pygame.draw.ellipse(surf, color, (x - s * 0.4, y - s * 0.16, s * 0.8, s * 0.32), 2)
        for i in range(5):
            pygame.draw.line(surf, color, (x - s * 0.3 + i * s * 0.15, y - s * 0.16), (x - s * 0.3 + i * s * 0.15, y + s * 0.16), 1)
    elif kind == "plant":
        pygame.draw.line(surf, color, (x, y + s * 0.4), (x, y - s * 0.2), 2)
        pygame.draw.ellipse(surf, color, (x - s * 0.35, y - s * 0.3, s * 0.35, s * 0.2), 2)
        pygame.draw.ellipse(surf, color, (x, y - s * 0.12, s * 0.35, s * 0.2), 2)
    elif kind == "extinct":
        pygame.draw.line(surf, color, (x - s * 0.3, y - s * 0.3), (x + s * 0.3, y + s * 0.3), 2)
        pygame.draw.line(surf, color, (x + s * 0.3, y - s * 0.3), (x - s * 0.3, y + s * 0.3), 2)
    elif kind == "meteor":
        event_icon(surf, "meteor", center, s, color)
    elif kind == "human":
        pygame.draw.circle(surf, color, (int(x), int(y - s * 0.28)), max(2, int(s * 0.12)))
        pygame.draw.line(surf, color, (x, y - s * 0.15), (x, y + s * 0.15), 2)
        pygame.draw.line(surf, color, (x, y + s * 0.15), (x - s * 0.15, y + s * 0.4), 2)
        pygame.draw.line(surf, color, (x, y + s * 0.15), (x + s * 0.15, y + s * 0.4), 2)
        pygame.draw.line(surf, color, (x - s * 0.2, y - s * 0.05), (x + s * 0.2, y - s * 0.05), 2)

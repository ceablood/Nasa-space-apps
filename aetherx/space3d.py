# -*- coding: utf-8 -*-
"""
AETHER-X // 3B GÖK CİSİMLERİ (numpy yazılım çizici)

- Prosedürel eş-dikdörtgen dokular (3B gürültü küre üzerinde: dikişsiz)
- Dünya: kıta çokgenlerinden harita, okyanus parlaması, bulut katmanı,
  gece yarım küresinde şehir ışıkları
- Mars: zaman zaman kabarıp sönen, hareket eden toz bulutları
- Gaz devleri: türbülanslı kuşaklar, Büyük Kırmızı Leke, Büyük Karanlık Leke
- Tek ışık kaynağı Güneş: gündüz / alacakaranlık / gece
- Satürn halkaları: C, B, Cassini Bölümü, A, Encke Boşluğu, F halkası,
  gezegenin halkaya ve halkanın gezegene düşen gölgesi, Kepler hızıyla dönen
  buz ve kaya parçaları
"""
import math
import random

import numpy as np

TAU = math.tau
F32 = np.float32


# ===========================================================================
# MATEMATİK
# ===========================================================================
def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=F32)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=F32)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=F32)


def norm3(v):
    v = np.asarray(v, dtype=F32)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([0, 0, 1], dtype=F32)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    """a, b: renk (3,) ; t: (...,)  ->  (...,3)"""
    a = np.asarray(a, dtype=F32)
    b = np.asarray(b, dtype=F32)
    return a + (b - a) * t[..., None]


def mixa(arr, col, t):
    """arr: (...,3) dizi, col: renk"""
    return arr + (np.asarray(col, dtype=F32) - arr) * t[..., None]


# ---------------------------------------------------------------- gürültü
_P = np.tile(np.random.default_rng(1234).permutation(256), 2).astype(np.int32)
_V = np.random.default_rng(99).random(256).astype(F32)


def noise3(x, y, z, seed=0):
    xi = np.floor(x).astype(np.int32)
    yi = np.floor(y).astype(np.int32)
    zi = np.floor(z).astype(np.int32)
    xf = (x - xi).astype(F32)
    yf = (y - yi).astype(F32)
    zf = (z - zi).astype(F32)
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    w = zf * zf * (3 - 2 * zf)
    x0 = (xi + seed * 37) & 255
    y0 = yi & 255
    z0 = zi & 255
    x1 = (x0 + 1) & 255
    y1 = (y0 + 1) & 255
    z1 = (z0 + 1) & 255

    def h(a, b, c):
        return _V[_P[_P[_P[a] + b] + c]]
    c00 = h(x0, y0, z0) * (1 - u) + h(x1, y0, z0) * u
    c10 = h(x0, y1, z0) * (1 - u) + h(x1, y1, z0) * u
    c01 = h(x0, y0, z1) * (1 - u) + h(x1, y0, z1) * u
    c11 = h(x0, y1, z1) * (1 - u) + h(x1, y1, z1) * u
    return (c00 * (1 - v) + c10 * v) * (1 - w) + (c01 * (1 - v) + c11 * v) * w


def fbm(x, y, z, octaves=5, seed=0, gain=0.5, lac=2.0):
    out = np.zeros_like(x, dtype=F32)
    amp, tot, f = 1.0, 0.0, 1.0
    for o in range(octaves):
        out += noise3(x * f, y * f, z * f, seed + o) * amp
        tot += amp
        amp *= gain
        f *= lac
    return out / tot


_GRID = {}


def grid(th):
    g = _GRID.get(th)
    if g is None:
        tw = th * 2
        lon = ((np.arange(tw, dtype=F32) + 0.5) / tw * TAU - math.pi)[None, :].repeat(th, 0)
        lat = (math.pi / 2 - (np.arange(th, dtype=F32) + 0.5) / th * math.pi)[:, None].repeat(tw, 1)
        cl = np.cos(lat)
        g = (cl * np.sin(lon), np.sin(lat), cl * np.cos(lon), lat, lon)
        _GRID.clear()
        _GRID[th] = g
    return g


def blur(a, n=1):
    for _ in range(n):
        a = (a + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 3
        a = (a + np.vstack([a[:1], a[:-1]]) + np.vstack([a[1:], a[-1:]])) / 3
    return a


# ===========================================================================
# DÜNYA HARİTASI (boylam, enlem çokgenleri)
# ===========================================================================
LAND = [
    # Kuzey ve Orta Amerika
    [(-168, 66), (-162, 70), (-156, 71), (-141, 70), (-128, 70), (-115, 69), (-105, 69), (-95, 69), (-90, 69),
     (-87, 67), (-90, 64), (-94, 60), (-92, 57), (-85, 55), (-82, 52), (-79, 51), (-79, 55), (-77, 57), (-78, 61),
     (-73, 62), (-70, 61), (-66, 59), (-64, 60), (-62, 57), (-58, 54), (-56, 51), (-55, 48), (-61, 45), (-66, 44),
     (-70, 43), (-71, 41), (-74, 40), (-76, 36), (-78, 34), (-81, 31), (-80, 26), (-81, 25), (-83, 29), (-85, 30),
     (-89, 30), (-91, 29), (-94, 29), (-97, 27), (-98, 22), (-96, 19), (-92, 18), (-90, 21), (-87, 21), (-88, 16),
     (-84, 15), (-83, 11), (-82, 9), (-79, 9), (-77, 8), (-80, 7), (-83, 8), (-86, 11), (-88, 13), (-92, 14),
     (-95, 16), (-100, 17), (-105, 20), (-106, 23), (-109, 26), (-112, 30), (-114, 31), (-117, 33), (-120, 34),
     (-122, 37), (-124, 40), (-124, 46), (-123, 48), (-128, 51), (-131, 54), (-135, 58), (-140, 60), (-147, 61),
     (-152, 59), (-158, 57), (-163, 55), (-160, 58), (-162, 60), (-166, 62), (-165, 65)],
    [(-80, 73), (-70, 71), (-62, 66), (-66, 62), (-74, 65), (-80, 68)],
    [(-117, 70), (-105, 69.5), (-102, 72), (-112, 73)],
    [(-90, 77), (-70, 78), (-62, 82), (-85, 82)],
    # Grönland
    [(-45, 60), (-41, 63), (-36, 66), (-25, 69), (-20, 73), (-18, 77), (-20, 81), (-32, 83), (-48, 82), (-62, 81),
     (-68, 78), (-60, 75), (-55, 71), (-53, 67), (-50, 63)],
    # Güney Amerika
    [(-77, 8), (-72, 12), (-68, 11), (-62, 10), (-58, 7), (-52, 5), (-50, 1), (-48, -1), (-42, -3), (-37, -5),
     (-35, -8), (-38, -13), (-39, -18), (-41, -22), (-46, -24), (-48, -27), (-51, -31), (-54, -34), (-57, -36),
     (-58, -38), (-62, -39), (-65, -42), (-66, -46), (-68, -50), (-69, -52), (-72, -54), (-74, -52), (-75, -47),
     (-73, -42), (-73, -37), (-71, -30), (-70, -24), (-70, -18), (-73, -16), (-76, -13), (-79, -8), (-81, -5),
     (-80, -2), (-80, 1), (-78, 3), (-77, 6)],
    # Afrika
    [(-6, 35), (-2, 35), (3, 37), (10, 37), (11, 34), (15, 32), (20, 31), (25, 32), (30, 31), (33, 31), (34, 28),
     (36, 24), (37, 20), (39, 16), (42, 12), (44, 11), (51, 12), (49, 7), (46, 3), (42, -1), (40, -5), (39, -9),
     (40, -14), (37, -18), (35, -22), (35, -25), (33, -27), (31, -30), (28, -33), (25, -34), (20, -35), (18, -33),
     (17, -29), (15, -25), (12, -18), (13, -12), (12, -6), (9, -2), (9, 4), (7, 4), (3, 6), (-3, 5), (-8, 4),
     (-11, 7), (-14, 10), (-17, 13), (-17, 18), (-16, 22), (-14, 26), (-10, 29), (-9, 32)],
    # Avrasya
    [(-9, 37), (-9, 43), (-2, 43.5), (-1, 46), (-4, 48), (-1, 49), (2, 51), (4, 52), (7, 54), (8, 57), (7, 58),
     (5, 60), (5, 62), (8, 64), (12, 66), (15, 69), (20, 70), (25, 71), (30, 70), (33, 69), (40, 68), (41, 66),
     (35, 65), (38, 64), (44, 66), (47, 67), (53, 68), (60, 69), (67, 69), (68, 72), (73, 73), (80, 73), (87, 75),
     (98, 76), (104, 78), (112, 76), (113, 74), (125, 73), (130, 71), (140, 72), (150, 71), (160, 70), (170, 70),
     (180, 69), (180, 65), (178, 63), (172, 61), (165, 60), (163, 58), (162, 55), (160, 52), (157, 51), (156, 54),
     (156, 57), (159, 60), (155, 59), (148, 59), (142, 59), (138, 56), (135, 54), (141, 53), (140, 49), (138, 46),
     (133, 43), (130, 42), (128, 40), (129, 37), (127, 35), (126, 37), (125, 39), (122, 40), (118, 39), (120, 37),
     (122, 37), (119, 35), (121, 32), (122, 30), (120, 27), (118, 24), (114, 22), (110, 21), (108, 21), (106, 19),
     (108, 16), (109, 12), (107, 10), (105, 9), (102, 12), (100, 13), (99, 10), (101, 7), (103, 4), (104, 1.5),
     (101, 3), (100, 6), (98, 8), (98, 13), (97, 17), (94, 16), (94, 19), (91, 22), (88, 22), (86, 20), (82, 16),
     (80, 14), (80, 10), (78, 8), (76, 10), (74, 15), (73, 20), (70, 21), (67, 24), (62, 25), (58, 25), (57, 27),
     (52, 27), (50, 30), (48, 30), (48, 28), (51, 25), (54, 24), (56, 26), (57, 24), (59, 22), (57, 18), (53, 16),
     (48, 14), (44, 12.5), (42, 15), (40, 19), (38, 23), (35, 28), (34, 30), (35, 33), (36, 36), (33, 36.5),
     (30, 36.5), (27, 37), (26, 39), (27, 40.5), (29, 41), (32, 42), (36, 41.5), (41, 41.5), (41, 43), (38, 45),
     (39, 47), (36, 46), (33, 46), (31, 46.5), (29, 45), (28, 43), (28, 41.5), (26, 41), (24, 41), (23, 40),
     (24, 38), (22, 37), (21, 39), (19.5, 41), (19, 42), (16, 43.5), (14, 45), (13, 45.5), (12.5, 44), (14, 42),
     (16, 41.5), (18, 40), (16, 39), (15.5, 38), (16, 40), (14, 41), (12, 42), (10, 44), (8, 44), (6, 43),
     (4, 43.5), (3, 42), (0, 40), (0, 38.5), (-2, 37), (-5, 36), (-6, 37)],
    # Adalar
    [(-5, 50), (-1, 50.7), (1, 51.2), (1.7, 52.7), (0, 53.5), (-1.5, 55), (-2, 57.6), (-4, 58.6), (-6, 58),
     (-5.5, 56), (-3, 54), (-4.5, 53), (-5, 51.7), (-4, 51)],
    [(-10, 52), (-6, 52), (-6, 54), (-7.5, 55.3), (-10, 54)],
    [(-24, 65.5), (-22, 66.4), (-16, 66.5), (-13.5, 65), (-16, 63.5), (-21, 63.4)],
    [(130, 31), (131, 34), (133, 34.5), (136, 34), (139, 35), (141, 36), (142, 39), (141, 41.5), (140, 40),
     (139, 38), (137, 37), (136, 36), (133, 35.5), (131, 34.5)],
    [(140, 42), (141, 45.5), (145, 44), (144, 43), (141, 42)],
    [(120, 18.5), (122.5, 18), (122, 14), (124, 12.5), (126, 9), (126, 6.5), (122, 7), (120, 10), (120, 14)],
    [(109, 1.5), (111, 2), (113, 3.5), (115, 5), (117, 7), (119, 5), (118, 1), (116, -3.5), (114, -4), (111, -3),
     (110, -1)],
    [(95, 5.5), (98, 3.5), (101, 2), (104, -1), (106, -3), (106, -6), (104, -5.5), (101, -3), (98, 1), (96, 3)],
    [(105, -6.5), (108, -6.5), (111, -6.5), (114.5, -7.5), (114, -8.5), (108, -7.8), (105.5, -7)],
    [(119, 1), (121, 1), (125, 1.5), (123, -1), (122.5, -4.5), (120.5, -5.5), (119.5, -3)],
    [(131, -1), (134, -1), (138, -1.5), (141, -2.5), (145, -4), (147.5, -6), (150.5, -10), (147, -9.5), (143, -8.5),
     (140, -8), (138, -7), (135, -4), (132, -3)],
    [(113.5, -22), (114, -26), (115, -31), (115.5, -34), (118, -35), (123.5, -34), (129, -31.5), (133, -32),
     (135.5, -35), (139.5, -37), (143, -38.7), (146.5, -39), (150, -37.5), (151.5, -33), (153.5, -28), (153, -25),
     (149.5, -22), (146, -19), (145.5, -15), (143, -12), (142, -10.8), (141, -17), (139, -17.5), (136, -15),
     (136.5, -12), (132, -11.5), (130, -13), (128, -15), (125, -15), (122, -17.5), (119, -20)],
    [(145, -41), (148, -41), (148, -43), (146, -43.5)],
    [(173, -35), (175, -37), (178, -38), (177, -39.5), (175, -41.5), (174, -39)],
    [(172.5, -41), (174, -42), (171, -44.5), (169, -46.5), (167, -45.5), (169, -44)],
    [(44, -16), (47, -15), (49.5, -12.5), (50, -16), (48, -22), (47, -25), (44, -25), (43.5, -21)],
    [(80, 9.5), (82, 7.5), (81, 6), (80, 7)],
    [(-85, 22), (-82, 23), (-78, 22.5), (-74, 20), (-77, 20), (-80, 22)],
    [(-74, 20), (-71, 20), (-68.5, 18.5), (-71, 17.8), (-74, 18.5)],
    [(52, 71), (56, 73), (60, 76), (68, 77), (60, 74), (55, 71)],
]
WATER = [
    [(47, 45), (51, 46.5), (54, 42), (53.5, 37), (49, 37), (49, 41), (47, 43)],                 # Hazar
    [(-92, 47), (-84, 46.5), (-79, 43.5), (-82, 42), (-87, 42), (-88, 45)],                     # Büyük Göller
    [(11, 54.5), (14, 55), (19, 55.5), (21, 57.5), (23, 59.5), (29, 60), (23, 60.5), (21, 62), (22, 64.5),
     (24, 65.5), (22, 65.5), (18, 62.5), (17, 60), (18, 58.5), (16, 56.5), (13, 55.5)],          # Baltık
]


def _fill_poly(mask, pts, val=1.0):
    th, tw = mask.shape
    P = [((lo + 180) / 360 * tw, (90 - la) / 180 * th) for lo, la in pts]
    ys = [p[1] for p in P]
    n = len(P)
    for y in range(max(0, int(min(ys))), min(th - 1, int(max(ys)) + 1) + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            xa, ya = P[i]
            xb, yb = P[(i + 1) % n]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(xa + (yc - ya) / (yb - ya) * (xb - xa))
        xs.sort()
        for j in range(0, len(xs) - 1, 2):
            a, b = max(0, int(round(xs[j]))), min(tw, int(round(xs[j + 1])))
            if b > a:
                mask[y, a:b] = val


_WORLD = {}


def world_mask(th):
    """Kara = 1, deniz = 0 (th x 2th)."""
    m = _WORLD.get(th)
    if m is None:
        hb = 2 * th                                   # 2x süper örnekleme: kıyılar kenar yumuşatmalı
        base = np.zeros((hb, hb * 2), dtype=F32)
        for poly in LAND:
            _fill_poly(base, poly, 1.0)
        for poly in WATER:
            _fill_poly(base, poly, 0.0)
        lon = (np.arange(hb * 2) + 0.5) / (hb * 2) * 360 - 180
        lat = 90 - (np.arange(hb) + 0.5) / hb * 180
        edge = -69 - 3.5 * np.sin(np.radians(lon) * 3) - 2 * np.cos(np.radians(lon) * 5)      # Antarktika kıyısı
        base[lat[:, None] < edge[None, :]] = 1.0
        pen = (np.abs(lon[None, :] + 60) < 5) & (lat[:, None] < -63) & (lat[:, None] > -72)   # yarımada
        base[pen] = 1.0
        m = base.reshape(th, 2, th * 2, 2).mean(axis=(1, 3)).astype(F32)
        _WORLD.clear()
        _WORLD[th] = m
    return m


# ===========================================================================
# DOKULAR
# ===========================================================================
def _palette(stops):
    pos = np.array([p for p, _ in stops], dtype=F32)
    cols = np.array([c for _, c in stops], dtype=F32)
    xs = np.linspace(-1, 1, 512, dtype=F32)
    return np.stack([np.interp(xs, pos, cols[:, i]) for i in range(3)], axis=1).astype(F32)


def _craters(rgb, th, n, seed, rmin=0.03, rmax=0.16, rays=0.0):
    x, y, z, lat, lon = grid(th)
    rng = random.Random(seed)
    for k in range(n):
        u, v = rng.uniform(-1, 1), rng.uniform(0, TAU)
        s = math.sqrt(1 - u * u)
        cx, cy, cz = s * math.sin(v), u, s * math.cos(v)
        rad = rmin + (rmax - rmin) * rng.random() ** 2.5
        d = np.arccos(np.clip(x * cx + y * cy + z * cz, -1, 1))
        floor = (d < rad * 0.9).astype(F32) * 0.16
        rim = np.exp(-((d - rad) / (rad * 0.2)) ** 2) * 0.22
        ray = np.exp(-(d / (rad * 2.6)) ** 2) * rays * (rng.random() < 0.25)
        rgb *= (1 - floor + rim + ray)[..., None]
    return rgb


def tex_earth(th):
    x, y, z, lat, lon = grid(th)
    alat = np.abs(lat)
    m = world_mask(th)
    prox = blur(m, max(2, th // 60))
    n = fbm(x * 3, y * 3, z * 3, 5, 3)
    land = smoothstep(0.46, 0.54, blur(m, 1) + (n - 0.5) * 0.3)
    elev = fbm(x * 5 + 7, y * 5, z * 5, 5, 8)
    arid = np.exp(-((alat - 0.42) / 0.17) ** 2) * smoothstep(0.38, 0.62, fbm(x * 2.2, y * 2.2, z * 2.2, 3, 21))
    veg = mix((34, 88, 44), (92, 126, 62), smoothstep(0.12, 0.7, alat + (elev - 0.5) * 0.3))
    lc = mixa(veg, (198, 170, 114), np.clip(arid * 1.25, 0, 1))
    lc = mixa(lc, (112, 120, 92), smoothstep(0.92, 1.1, alat))
    lc = mixa(lc, (128, 114, 100), smoothstep(0.6, 0.78, elev) * 0.8)
    ice = smoothstep(1.1, 1.2, alat + (elev - 0.5) * 0.25) * land
    green = ((lat > 1.03) & (lon > -1.3) & (lon < -0.3) & (land > 0.5)).astype(F32)      # Grönland buzulu
    ice = np.maximum(ice, np.maximum(green, (lat < -1.1) * land))
    lc = mixa(lc, (244, 247, 251), ice)
    lc *= (0.86 + 0.28 * elev)[..., None]
    oc = mix((7, 30, 88), (34, 108, 166), smoothstep(0.02, 0.5, prox))
    seaice = smoothstep(1.33, 1.42, lat + (n - 0.5) * 0.2) * (1 - land)
    oc = mixa(oc, (226, 236, 244), seaice)
    rgb = oc * (1 - land[..., None]) + lc * land[..., None]
    pop = land * (1 - np.clip(arid * 1.1, 0, 1)) * (1 - ice) * smoothstep(0.46, 0.68, fbm(x * 7, y * 7, z * 7, 3, 31))
    pop *= 1 - smoothstep(0.95, 1.2, alat)
    lights = pop * smoothstep(0.5, 0.78, noise3(x * 95, y * 95, z * 95, 32))
    cw = fbm(x * 2, y * 2, z * 2, 3, 40)
    cl = fbm(x * 4 + cw * 1.6, y * 6.5, z * 4 + cw * 1.6, 5, 41)
    cloud = smoothstep(0.5, 0.7, cl) * 0.92
    return {"rgb": rgb, "spec": (1 - land) * (1 - seaice), "lights": lights, "cloud": cloud,
            "cloud_rgb": (250, 252, 255), "cloud_speed": 0.35}


def tex_mars(th):
    x, y, z, lat, lon = grid(th)
    n1 = fbm(x * 2.2, y * 2.2, z * 2.2, 5, 50)
    n2 = fbm(x * 9, y * 9, z * 9, 4, 51)
    rgb = mix((126, 62, 44), (206, 112, 66), smoothstep(0.34, 0.66, n1))
    rgb = mixa(rgb, (232, 168, 116), smoothstep(0.62, 0.8, n1) * 0.7)
    rgb *= (0.82 + 0.34 * n2)[..., None]
    vm = np.exp(-((lat + 0.17) / 0.045) ** 2) * smoothstep(-1.9, -1.5, lon) * (1 - smoothstep(-0.9, -0.5, lon))
    rgb = mixa(rgb, (70, 34, 28), np.clip(vm * (0.6 + 0.8 * n2), 0, 1) * 0.85)                 # Valles Marineris
    om = np.exp(-(((lon + 2.33) / 0.11) ** 2 + ((lat - 0.32) / 0.09) ** 2))
    rgb = mixa(rgb, (236, 180, 132), om * 0.8)                                               # Olympus Mons
    cap = smoothstep(1.36, 1.44, lat + (n2 - 0.5) * 0.12) + smoothstep(1.42, 1.48, -lat + (n2 - 0.5) * 0.1)
    rgb = mixa(rgb, (246, 244, 240), np.clip(cap, 0, 1))
    rgb = _craters(rgb, th, 26, 52, 0.02, 0.09)
    dw = fbm(x * 1.6, y * 1.6, z * 1.6, 3, 55)
    dust = smoothstep(0.52, 0.74, fbm(x * 3 + dw * 2.2, y * 3.5, z * 3 + dw * 2.2, 5, 56)) * 0.95
    return {"rgb": rgb, "cloud": dust, "cloud_rgb": (232, 176, 118), "cloud_speed": 0.9, "storm": True}


def _banded(th, stops, turb, seed, streak=0.08):
    x, y, z, lat, lon = grid(th)
    w = fbm(x * 1.4, y * 7, z * 1.4, 4, seed)
    w2 = fbm(x * 6, y * 22, z * 6, 3, seed + 5)
    s = np.clip((lat + (w - 0.5) * turb + (w2 - 0.5) * turb * 0.35) / (math.pi / 2), -1, 1)
    pal = _palette(stops)
    rgb = pal[((s + 1) * 255.5).astype(np.int32)]
    fine = fbm(x * 5, y * 46, z * 5, 3, seed + 9)
    rgb = rgb * (1 - streak + 2 * streak * fine)[..., None]
    return rgb


def _spot(rgb, th, lon0, lat0, rl, rb, col, k=1.0):
    x, y, z, lat, lon = grid(th)
    dl = (lon - lon0 + math.pi) % TAU - math.pi
    d = (dl / rl) ** 2 + ((lat - lat0) / rb) ** 2
    core = np.exp(-d * 1.4) * k
    ring = np.exp(-((np.sqrt(d) - 1.05) / 0.22) ** 2) * 0.35 * k
    rgb = mixa(rgb, col, np.clip(core, 0, 1))
    return rgb * (1 - ring)[..., None]


def tex_jupiter(th):
    rgb = _banded(th, [(-1, (126, 116, 112)), (-0.75, (166, 140, 120)), (-0.6, (226, 210, 186)),
                       (-0.45, (190, 140, 100)), (-0.33, (233, 219, 191)), (-0.22, (164, 104, 70)),
                       (-0.1, (236, 223, 199)), (0.08, (241, 229, 206)), (0.18, (156, 94, 60)),
                       (0.3, (229, 213, 187)), (0.42, (186, 136, 98)), (0.55, (223, 206, 181)),
                       (0.75, (160, 138, 120)), (1, (124, 118, 116))], 0.085, 60)
    rgb = _spot(rgb, th, 0.7, -0.385, 0.2, 0.085, (198, 84, 50))
    for i, lo in enumerate((-2.2, -1.2, 2.3)):
        rgb = _spot(rgb, th, lo, -0.58, 0.05, 0.03, (244, 238, 226), 0.8)
    return {"rgb": rgb, "limb": 0.42}


def tex_saturn(th):
    rgb = _banded(th, [(-1, (150, 142, 124)), (-0.6, (212, 188, 138)), (-0.3, (230, 208, 158)),
                       (0, (239, 221, 174)), (0.25, (222, 198, 148)), (0.5, (206, 184, 140)),
                       (0.8, (172, 166, 150)), (1, (140, 152, 164))], 0.05, 70, 0.045)
    return {"rgb": rgb, "limb": 0.42}


def tex_uranus(th):
    rgb = _banded(th, [(-1, (188, 234, 238)), (-0.5, (160, 222, 228)), (0, (150, 216, 224)),
                       (0.5, (162, 224, 230)), (1, (176, 230, 234))], 0.03, 80, 0.02)
    return {"rgb": rgb, "limb": 0.5}


def tex_neptune(th):
    x, y, z, lat, lon = grid(th)
    rgb = _banded(th, [(-1, (38, 66, 164)), (-0.5, (52, 98, 208)), (-0.2, (40, 80, 192)), (0.1, (62, 112, 218)),
                       (0.5, (48, 92, 202)), (1, (36, 64, 160))], 0.06, 90, 0.05)
    rgb = _spot(rgb, th, -0.6, -0.36, 0.22, 0.1, (22, 38, 118))
    cw = fbm(x * 3, y * 30, z * 3, 4, 95)
    streak = smoothstep(0.66, 0.8, cw) * np.exp(-((np.abs(lat) - 0.5) / 0.18) ** 2)
    rgb = mixa(rgb, (236, 244, 255), streak * 0.85)
    return {"rgb": rgb, "limb": 0.5}


def tex_venus(th):
    x, y, z, lat, lon = grid(th)
    w = fbm(x * 1.2, y * 1.2, z * 1.2, 3, 100)
    c = fbm(x * 2 + w * 3, y * 5 + np.abs(x) * 1.5, z * 2 + w * 3, 5, 101)
    rgb = mix((196, 160, 96), (248, 232, 184), smoothstep(0.3, 0.72, c))
    return {"rgb": rgb, "limb": 0.35}


def tex_rocky(th, dark, base, seed, craters=40, f=2.4, rays=0.0, rmax=0.15):
    x, y, z, lat, lon = grid(th)
    n1 = fbm(x * f, y * f, z * f, 5, seed)
    n2 = fbm(x * 10, y * 10, z * 10, 4, seed + 3)
    rgb = mix(dark, base, smoothstep(0.36, 0.64, n1)) * (0.8 + 0.4 * n2)[..., None]
    return {"rgb": _craters(rgb, th, craters, seed + 7, 0.02, rmax, rays)}


def tex_sun(th):
    x, y, z, lat, lon = grid(th)
    g = fbm(x * 16, y * 16, z * 16, 4, 120)
    big = fbm(x * 3, y * 3, z * 3, 3, 121)
    rgb = mix((246, 150, 46), (255, 226, 150), smoothstep(0.3, 0.7, g * 0.6 + big * 0.4))
    spots = smoothstep(0.7, 0.78, fbm(x * 5, y * 5, z * 5, 3, 122)) * np.exp(-(lat / 0.5) ** 2)
    return {"rgb": mixa(rgb, (120, 58, 20), spots * 0.8)}


def _tex_special(key, th):
    x, y, z, lat, lon = grid(th)
    if key == "io":
        t = tex_rocky(th, (196, 150, 60), (232, 214, 110), 130, 0)
        v = smoothstep(0.7, 0.8, fbm(x * 7, y * 7, z * 7, 3, 131))
        t["rgb"] = mixa(mixa(t["rgb"], (238, 236, 220), smoothstep(0.6, 0.75, fbm(x * 3, y * 3, z * 3, 3, 132)) * 0.6),
                        (60, 30, 20), v)
        return t
    if key == "europa":
        t = tex_rocky(th, (206, 196, 180), (238, 232, 222), 140, 4)
        w = fbm(x * 2, y * 2, z * 2, 3, 141)
        lines = 1 - smoothstep(0.0, 0.06, np.abs(np.sin((x * 3 + y * 5 + w * 4) * 4)))
        lines2 = 1 - smoothstep(0.0, 0.05, np.abs(np.sin((z * 4 - y * 3 + w * 5) * 3.5)))
        t["rgb"] = mixa(t["rgb"], (150, 96, 70), np.clip(lines + lines2, 0, 1) * 0.6)
        return t
    if key == "titan":
        n = fbm(x * 2.5, y * 4, z * 2.5, 4, 150)
        return {"rgb": mix((190, 122, 52), (232, 172, 84), n), "limb": 0.3}
    if key == "enceladus":
        t = tex_rocky(th, (226, 232, 240), (250, 252, 255), 160, 10, rmax=0.08)
        st = (1 - smoothstep(0.0, 0.05, np.abs(np.sin(lon * 4 + x * 2)))) * smoothstep(-0.9, -1.2, lat)
        t["rgb"] = mixa(t["rgb"], (120, 190, 230), st * 0.8)                                   # kaplan çizgileri
        return t
    if key == "iapetus":
        t = tex_rocky(th, (200, 196, 188), (236, 232, 224), 170, 30)
        lead = smoothstep(-0.25, 0.35, np.sin(lon)) * (1 - smoothstep(0.7, 1.1, np.abs(lat)))
        t["rgb"] = mixa(t["rgb"], (46, 34, 28), lead * 0.92)
        ridge = np.exp(-(lat / 0.03) ** 2) * 0.25
        t["rgb"] = t["rgb"] * (1 + ridge)[..., None]
        return t
    if key == "mimas":
        t = tex_rocky(th, (150, 150, 152), (206, 206, 208), 180, 45, rmax=0.1)
        d = np.arccos(np.clip(z, -1, 1))                                                       # Herschel krateri
        t["rgb"] *= (1 - (d < 0.42) * 0.22 + np.exp(-((d - 0.44) / 0.07) ** 2) * 0.3 + np.exp(-(d / 0.06) ** 2) * 0.3)[..., None]
        return t
    if key == "triton":
        t = tex_rocky(th, (150, 140, 136), (214, 196, 190), 190, 8)
        t["rgb"] = mixa(t["rgb"], (236, 204, 200), smoothstep(-0.2, -0.7, lat) * 0.7)
        return t
    if key == "callisto":
        return tex_rocky(th, (58, 50, 44), (112, 98, 84), 200, 70, rays=0.5, rmax=0.07)
    if key == "ganymede":
        return tex_rocky(th, (92, 84, 76), (176, 168, 156), 210, 36, f=1.8, rays=0.3)
    return None


ROCKY = {
    "mercury": ((98, 94, 90), (168, 162, 156), 220, 80, 0.4),
    "moon": ((84, 84, 90), (186, 184, 180), 230, 60, 0.35),
    "ceres": ((88, 86, 84), (140, 138, 134), 240, 40, 0.3),
    "rock": ((92, 84, 76), (150, 140, 128), 250, 30, 0.0),
    "ice": ((178, 184, 192), (232, 236, 242), 260, 34, 0.0),
    "dark": ((40, 36, 34), (86, 78, 72), 270, 30, 0.0),
    "rust": ((96, 62, 48), (150, 104, 80), 280, 26, 0.0),
}
TEXFN = {"earth": tex_earth, "mars": tex_mars, "jupiter": tex_jupiter, "saturn": tex_saturn, "uranus": tex_uranus,
         "neptune": tex_neptune, "venus": tex_venus, "sun": tex_sun}
ATMO = {"earth": ((110, 170, 255), 0.9), "venus": ((255, 222, 150), 0.7), "mars": ((255, 170, 120), 0.3),
        "titan": ((255, 176, 90), 0.8), "jupiter": ((255, 226, 190), 0.25), "saturn": ((255, 232, 180), 0.25),
        "uranus": ((170, 240, 250), 0.5), "neptune": ((100, 150, 255), 0.6)}
_TEX = {}


TEX_VERSION = 3
_DISK = None


def _disk_dir():
    global _DISK
    if _DISK is None:
        import os
        from pathlib import Path
        _DISK = Path(os.path.expanduser("~")) / ".aetherx" / "tex"
    return _DISK


def _disk_load(key, th):
    try:
        f = _disk_dir() / f"{key}_{th}_v{TEX_VERSION}.npz"
        if not f.exists():
            return None
        z = np.load(f, allow_pickle=False)
        t = {"rgb": z["rgb"]}
        for q in ("spec", "lights", "cloud"):
            if q in z.files:
                t[q] = z[q].astype(F32) / 255.0
        meta = z["meta"].tolist() if "meta" in z.files else ""
        for kv in meta.split(";") if meta else ():
            name, val = kv.split("=", 1)
            t[name] = (float(val) if name in ("limb", "cloud_speed") else
                       (val == "1") if name == "storm" else tuple(int(c) for c in val.split(",")))
        return t
    except Exception:
        return None


def disk_has(key, th):
    try:
        return (_disk_dir() / f"{key}_{th}_v{TEX_VERSION}.npz").exists()
    except Exception:
        return False


def _disk_save(key, th, t):
    try:
        d = _disk_dir()
        d.mkdir(parents=True, exist_ok=True)
        arrs = {"rgb": t["rgb"]}
        for q in ("spec", "lights", "cloud"):
            if q in t:
                arrs[q] = np.clip(t[q] * 255 + 0.5, 0, 255).astype(np.uint8)
        meta = []
        for name in ("limb", "cloud_speed", "storm", "cloud_rgb"):
            if name in t:
                v = t[name]
                meta.append(f"{name}=" + (",".join(str(int(c)) for c in v) if isinstance(v, (tuple, list)) else
                                          ("1" if v is True else "0" if v is False else str(v))))
        np.savez_compressed(d / f"{key}_{th}_v{TEX_VERSION}.npz", meta=np.array(";".join(meta)), **arrs)
    except Exception:
        pass


def texture(key, th=256):
    k = (key, th)
    t = _TEX.get(k)
    if t is None and th >= 1024:
        t = _disk_load(key, th)                    # büyük dokular bir kez üretilip diske yazılır
        if t is not None:
            t["th"] = th
            _TEX[k] = t
            return t
    if t is None:
        if key in TEXFN:
            t = TEXFN[key](th)
        else:
            t = _tex_special(key, th)
            if t is None:
                d, b, seed, cr, rays = ROCKY.get(key, ROCKY["rock"])
                t = tex_rocky(th, d, b, seed, cr, rays=rays)
        t["rgb"] = np.clip(t["rgb"], 0, 255).astype(np.uint8)
        for q in ("spec", "lights", "cloud"):
            if q in t:
                t[q] = np.clip(t[q], 0, 1).astype(F32)
        t["th"] = th
        _TEX[k] = t
        if th >= 1024:
            _disk_save(key, th, t)
    return t


def has_texture(key, th=256):
    return (key, th) in _TEX


# ===========================================================================
# KÜRE ÇİZİCİ
# ===========================================================================
_GEO = {}


def _geometry(R, M, obl):
    key = (R, tuple(np.round(M.flatten(), 2)), obl)
    g = _GEO.get(key)
    if g is not None:
        return g
    n = R * 2
    c = (np.arange(n, dtype=F32) + 0.5 - R) / R
    nx = c[None, :].repeat(n, 0)
    ny = (-c[:, None] / obl).repeat(n, 1)
    rr = nx * nx + ny * ny
    idx = np.flatnonzero(rr.ravel() <= 1.0)
    vx, vy = nx.ravel()[idx], ny.ravel()[idx]
    vz = np.sqrt(np.clip(1 - rr.ravel()[idx], 0, 1))
    Mt = M.T
    px = Mt[0, 0] * vx + Mt[0, 1] * vy + Mt[0, 2] * vz
    py = Mt[1, 0] * vx + Mt[1, 1] * vy + Mt[1, 2] * vz
    pz = Mt[2, 0] * vx + Mt[2, 1] * vy + Mt[2, 2] * vz
    u = (np.arctan2(px, pz) / TAU + 0.5).astype(F32)
    v = (0.5 - np.arcsin(np.clip(py, -1, 1)) / math.pi).astype(F32)
    aa = np.clip((1 - np.sqrt(rr.ravel()[idx])) * R * obl, 0, 1)
    g = (idx, vx, vy, vz, u, v, (aa * 255).astype(np.uint8))
    if len(_GEO) > 48:
        _GEO.clear()
    _GEO[key] = g
    return g


def _sample(tex, u, v, bilinear):
    th = tex["th"]
    tw = th * 2
    rgb = tex["rgb"]
    if not bilinear:
        cols = (u * tw).astype(np.int32) % tw
        rows = np.clip((v * th).astype(np.int32), 0, th - 1)
        return rgb[rows, cols].astype(F32), rows, cols
    cf = u * tw - 0.5
    rf = np.clip(v * th - 0.5, 0, th - 1.001)
    c0 = np.floor(cf).astype(np.int32)
    r0 = rf.astype(np.int32)
    fx = (cf - c0)[:, None]
    fy = (rf - r0)[:, None]
    c0 %= tw
    c1 = (c0 + 1) % tw
    r1 = r0 + 1
    top = rgb[r0, c0] * (1 - fx) + rgb[r0, c1] * fx
    bot = rgb[r1, c0] * (1 - fx) + rgb[r1, c1] * fx
    return (top * (1 - fy) + bot * fy).astype(F32), r0, c0


def _grade(out):
    """Film tonu eşleme (ACES yaklaşımı): parlak noktalar patlamaz, gölgelerde ayrıntı kalır,
    renkler doğal; hafif doygunluk ve kontrast. Girdi/çıktı 0-255 sRGB benzeri."""
    x = np.maximum(out, 0) / 255.0
    lin = x ** 2.2 * 1.18                                   # pozlama
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    tm = np.clip((lin * (a * lin + b)) / (lin * (c * lin + d) + e), 0, 1)
    g = tm ** (1 / 2.2)
    lum = (g @ np.array((0.2126, 0.7152, 0.0722), dtype=F32))[:, None]
    g = lum + (g - lum) * 1.08                              # doğal doygunluk
    return np.clip(g, 0, 1) * 255.0


def render_body(key, R, M, L, spin=0.0, t=0.0, th=256, ring=None, obl=1.0, emissive=False):
    """RGBA uint8 (2R, 2R, 4). M: gezegen->görüş (y yukarı), L: Güneş yönü (görüş uzayı)."""
    R = max(2, int(R))
    # mip seviyesi: küçük çizimde yüksek doku "kumlanma"/titreşme yapar -> uygun çözünürlüğe in
    while th > 128 and R < th * 0.16 and not (key, th // 2) in _TEX and R < 40:
        th //= 2
    while th > 128 and R < th * 0.16 and (key, th // 2) in _TEX:
        th //= 2
    tex = texture(key, th)
    idx, vx, vy, vz, u, v, aa = _geometry(R, M, obl)
    bil = R > th * 0.2
    uu = (u - spin / TAU) % 1.0
    rgb, rows, cols = _sample(tex, uu, v, bil)
    tw = th * 2
    if emissive:
        out = rgb * (0.5 + 0.5 * vz ** 0.55)[:, None]
    else:
        ndl = vx * L[0] + vy * L[1] + vz * L[2]
        day = smoothstep(-0.06, 0.28, ndl)
        ca = None
        if "cloud" in tex:
            op = 1.0
            if tex.get("storm"):
                op = max(0.0, math.sin(t * 0.11) * 1.5 - 0.35) ** 0.8          # zaman zaman kabaran toz fırtınası
                op = min(1.0, op)
            if op > 0.01:
                cc = ((uu + t * 0.004 * tex["cloud_speed"]) % 1.0 * tw).astype(np.int32) % tw
                ca = tex["cloud"][rows, cc] * op
                rgb = rgb + (np.asarray(tex["cloud_rgb"], dtype=F32) - rgb) * ca[:, None]
        # stüdyo ışığı: yumuşak gün/gece geçişi + çok hafif mavi ortam dolgusu (gece tarafı simsiyah olmaz)
        lam = np.clip(ndl, 0, 1)
        lit = 0.05 + day * (0.22 + 0.78 * lam ** 0.85)
        if "limb" in tex:
            lit = lit * (1 - tex["limb"] + tex["limb"] * vz ** 0.5)
        if ring is not None:
            lit = lit * _ring_shadow_on_body(ring, R, M, L, vx, vy, vz)
        out = rgb * lit[:, None]
        if "spec" in tex:
            h = norm3((L[0], L[1], L[2] + 1.0))
            sp = np.clip(vx * h[0] + vy * h[1] + vz * h[2], 0, 1) ** 70 * tex["spec"][rows, cols] * day
            if ca is not None:
                sp = sp * (1 - ca)
            out += (sp * 210)[:, None]
        if "lights" in tex:
            night = 1 - smoothstep(-0.22, 0.02, ndl)
            lg = tex["lights"][rows, cols] * night
            if ca is not None:
                lg = lg * (1 - ca * 0.7)
            out += lg[:, None] * np.array((255, 196, 116), dtype=F32)
        at = ATMO.get(key)
        if at:
            fres = (1 - vz) ** 2.6 * smoothstep(-0.25, 0.4, ndl) * at[1]
            out += fres[:, None] * np.asarray(at[0], dtype=F32)
        try:
            from . import i18n as _i18n
            cine = _i18n.PREFS.get("cinematic", True)
        except Exception:
            cine = False
        if cine:
            # stilize kenar ışığı: gece tarafında da silueti ayıran soğuk ışık, gündüz kenarında sıcak sızıntı
            rimk = (1 - vz) ** 3.5
            out += (rimk * (1 - day) * 34)[:, None] * np.array((0.45, 0.65, 1.0), dtype=F32)
            out += (rimk * day * 22)[:, None] * np.array((1.0, 0.8, 0.6), dtype=F32)
        out = _grade(out)
    img = np.zeros((R * 2 * R * 2, 4), dtype=np.uint8)
    img[idx, :3] = np.clip(out, 0, 255).astype(np.uint8)
    img[idx, 3] = aa
    return img.reshape(R * 2, R * 2, 4)


# ===========================================================================
# HALKALAR
# ===========================================================================
def _ring_profile(kind):
    """(iç, dış, opaklık[n], renk[n,3]) - yarıçap gezegen yarıçapı biriminde."""
    n = 1024
    rng = np.random.default_rng({"saturn": 5, "uranus": 6, "neptune": 7}.get(kind, 8))
    fine = np.clip(0.72 + 0.28 * np.interp(np.arange(n), np.arange(0, n, 6), rng.random(len(range(0, n, 6)))), 0, 1)
    micro = 0.85 + 0.15 * rng.random(n)
    if kind == "saturn":
        inner, outer = 1.11, 2.34
        r = np.linspace(inner, outer, n)
        op = np.zeros(n, dtype=F32)
        col = np.zeros((n, 3), dtype=F32)

        def band(a, b, o, c):
            mk = (r >= a) & (r < b)
            op[mk] = o
            col[mk] = c
        band(1.11, 1.24, 0.05, (120, 112, 100))          # D
        band(1.24, 1.53, 0.26, (132, 120, 104))          # C
        band(1.53, 1.95, 0.92, (226, 208, 172))          # B
        band(1.95, 2.03, 0.06, (120, 110, 96))           # Cassini Bölümü
        band(2.03, 2.27, 0.62, (204, 190, 160))          # A
        band(2.212, 2.218, 0.03, (90, 84, 76))           # Encke Boşluğu
        band(2.262, 2.266, 0.04, (90, 84, 76))           # Keeler Boşluğu
        band(2.318, 2.332, 0.42, (220, 214, 200))        # F
        op *= fine * micro
        op[(r >= 1.53) & (r < 1.95)] *= np.linspace(0.8, 1.0, int(((r >= 1.53) & (r < 1.95)).sum()))
        return inner, outer, op.astype(F32), col
    if kind == "uranus":
        inner, outer = 1.6, 2.05
        r = np.linspace(inner, outer, n)
        op = np.zeros(n, dtype=F32)
        for rr, w, o in ((1.64, 0.004, 0.3), (1.65, 0.004, 0.3), (1.67, 0.004, 0.3), (1.75, 0.005, 0.4), (1.79, 0.005, 0.4),
                         (1.83, 0.004, 0.35), (1.86, 0.005, 0.4), (1.89, 0.005, 0.4), (2.0, 0.012, 0.7)):
            op = np.maximum(op, np.exp(-((r - rr) / w) ** 2) * o)
        return inner, outer, op.astype(F32), np.tile(np.array((120, 130, 140), dtype=F32), (n, 1))
    inner, outer = 1.7, 2.6
    r = np.linspace(inner, outer, n)
    op = np.maximum(np.exp(-((r - 2.15) / 0.012) ** 2) * 0.25, np.exp(-((r - 2.54) / 0.01) ** 2) * 0.4)
    return inner, outer, op.astype(F32), np.tile(np.array((150, 160, 190), dtype=F32), (n, 1))


_PROFILES = {}


def ring_profile(kind):
    p = _PROFILES.get(kind)
    if p is None:
        p = _PROFILES[kind] = _ring_profile(kind)
    return p


def _ring_shadow_on_body(kind, R, M, L, vx, vy, vz):
    inner, outer, op, _ = ring_profile(kind)
    N = M[:, 1]
    ln = float(L[0] * N[0] + L[1] * N[1] + L[2] * N[2])
    if abs(ln) < 0.02:
        return 1.0
    t = -(vx * N[0] + vy * N[1] + vz * N[2]) / ln
    hx, hy, hz = vx + t * L[0], vy + t * L[1], vz + t * L[2]
    rr = np.sqrt(hx * hx + hy * hy + hz * hz)
    i = np.clip(((rr - inner) / (outer - inner) * (len(op) - 1)).astype(np.int32), 0, len(op) - 1)
    o = np.where((t > 0) & (rr > inner) & (rr < outer), op[i], 0.0)
    return 1 - 0.78 * o


def render_ring(kind, R, M, L, obl=1.0):
    """(arka RGBA, ön RGBA, yarı_genişlik). Arka yarı gezegenden önce, ön yarı sonra çizilir."""
    inner, outer, op, col = ring_profile(kind)
    U, Wv, N = M[:, 0], M[:, 2], M[:, 1]
    det = float(U[0] * Wv[1] - Wv[0] * U[1])
    if abs(det) < 0.03:
        return None
    half = int(outer * R) + 2
    c = np.arange(-half, half, dtype=F32) + 0.5
    x = c[None, :].repeat(half * 2, 0)
    y = (-c[:, None]).repeat(half * 2, 1)
    u = (x * Wv[1] - y * Wv[0]) / det
    w = (-x * U[1] + y * U[0]) / det
    rr = np.sqrt(u * u + w * w) / R
    fi = (rr - inner) / (outer - inner) * (len(op) - 1)
    i = np.clip(fi.astype(np.int32), 0, len(op) - 1)
    inside = (rr > inner) & (rr < outer)
    a = np.where(inside, op[i], 0.0)
    px, py, pz = u * U[0] + w * Wv[0], u * U[1] + w * Wv[1], u * U[2] + w * Wv[2]
    pl = px * L[0] + py * L[1] + pz * L[2]
    perp2 = px * px + py * py + pz * pz - pl * pl
    shadow = (pl < 0) & (perp2 < (R * 0.985) ** 2)
    nl = abs(float(N[0] * L[0] + N[1] * L[1] + N[2] * L[2]))
    bright = (0.5 + 0.5 * min(1.0, nl * 2.2)) * np.where(shadow, 0.07, 1.0)
    grain = 0.9 + 0.1 * np.random.default_rng(3).random(a.shape)
    rgb = col[i] * (bright * grain)[..., None]
    img = np.zeros((half * 2, half * 2, 4), dtype=np.uint8)
    img[..., :3] = np.clip(rgb, 0, 255)
    alpha = np.clip(a * 255, 0, 255)
    back = img.copy()
    back[..., 3] = np.where(pz <= 0, alpha, 0)
    img[..., 3] = np.where(pz > 0, alpha, 0)
    return back, img, half


class RingRocks:
    """Halkada Kepler hızıyla dönen buz ve kaya parçaları."""

    def __init__(self, kind="saturn", n=520, seed=4242):
        rng = np.random.default_rng(seed)
        inner, outer, op, col = ring_profile(kind)
        r = np.linspace(inner, outer, len(op))
        p = op / op.sum()
        i = rng.choice(len(op), size=n, p=p)
        self.r = (r[i] + rng.normal(0, 0.004, n)).astype(F32)
        self.th = rng.uniform(0, TAU, n).astype(F32)
        self.size = (1.0 + rng.random(n) ** 3 * 4.2).astype(F32)
        self.h = rng.normal(0, 0.012, n).astype(F32)
        self.shade = (0.7 + 0.3 * rng.random(n)).astype(F32)
        self.col = col[i] * self.shade[:, None]
        self.kind = rng.integers(0, 6, n)
        self.spin = rng.uniform(-2, 2, n).astype(F32)
        self.n = n

    def update(self, dt, rate=0.5):
        self.th = (self.th + dt * rate * self.r ** -1.5) % TAU

    def project(self, R, M, L, yaw=0.0, obl=1.0):
        """Ekran konumları (y aşağı), derinlik, görünürlük ve parlaklık."""
        a = self.th + yaw
        u, w = np.sin(a) * self.r * R, np.cos(a) * self.r * R
        U, Wv, N = M[:, 0], M[:, 2], M[:, 1]
        hh = self.h * R
        px = u * U[0] + w * Wv[0] + hh * N[0]
        py = u * U[1] + w * Wv[1] + hh * N[1]
        pz = u * U[2] + w * Wv[2] + hh * N[2]
        vis = ~((pz < 0) & (px * px + (py / obl) ** 2 < R * R))
        pl = px * L[0] + py * L[1] + pz * L[2]
        dark = (pl < 0) & (px * px + py * py + pz * pz - pl * pl < (R * 0.985) ** 2)
        return px, -py, pz, vis, np.where(dark, 0.1, 1.0)


# ===========================================================================
# PYGAME YÜZEYLERİ
# ===========================================================================
def to_surface(arr):
    import pygame
    h, w = arr.shape[:2]
    return pygame.image.frombuffer(np.ascontiguousarray(arr).tobytes(), (w, h), "RGBA")

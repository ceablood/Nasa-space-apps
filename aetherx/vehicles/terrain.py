# -*- coding: utf-8 -*-
"""
AETHER-X // SÜRÜŞ ARAZİSİ
Yükseklik haritası (m), zemin türü haritası, kayalar (çarpışma), gölgeli renk haritası.
  Ay   : kraterler (çanak + kenar; derinlik/çap ~0,2 genç basit kraterlerde), regolit, kaya alanları.
  Mars : kum tepeleri, kraterler, kayalık alanlar (kaya boyu-sıklığı üstel dağılımı, Golombek & Rapp 1997 yaklaşımı).
  Titan: buz kaya tepeleri, organik kum düzlükleri, metan gölü (deniz seviyesi altındaki alan sıvı) ve ıslak kıyı.
Harita kenar uzunluğu 1024 m (2 m hücre). Değerler deterministik (tohumlu).
"""
import math

import numpy as np

from .planets import PLANETS, SURFACES, SURFACE_IDS

F32 = np.float32


def _noise(n, scale, rng):
    """Döngüsel (kenarları birleşik) yumuşak gürültü: FFT ile bant sınırlı."""
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    k = np.sqrt(fx ** 2 + fy ** 2) + 1e-9
    spec = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / k ** 1.0
    spec *= np.exp(-(k * n / scale) ** 2)
    x = np.real(np.fft.ifft2(spec))
    return (x / (np.abs(x).max() + 1e-9)).astype(F32)


class Terrain:
    def __init__(self, planet, seed=7, n=512, cell=2.0):
        self.planet = planet
        self.p = PLANETS[planet]
        self.n, self.cell = n, cell
        self.size = n * cell
        rng = np.random.default_rng(seed)
        h = _noise(n, 6, rng) * 34 + _noise(n, 24, rng) * 9 + _noise(n, 90, rng) * 1.2
        surf = np.zeros((n, n), dtype=np.int8)
        ids = {s: i for i, s in enumerate(SURFACE_IDS)}
        yy, xx = np.mgrid[0:n, 0:n].astype(F32)
        self.craters = []
        if planet in ("moon", "mars"):
            for _ in range(70 if planet == "moon" else 26):
                cx, cy = rng.uniform(0, n), rng.uniform(0, n)
                r = float(rng.pareto(2.2) * 6 + 5)                      # hücre; küçük krater çok, büyük az
                r = min(r, 70)
                if math.hypot(cx - n / 2, cy - n / 2) < r + 12:
                    continue
                dx = (xx - cx + n / 2) % n - n / 2
                dy = (yy - cy + n / 2) % n - n / 2
                d = np.sqrt(dx * dx + dy * dy) / r
                depth = 0.2 * r * cell                                 # derinlik/çap ~0,1 (çap = 2r)
                bowl = np.where(d < 1, -depth * (1 - d * d), 0)
                rim = np.where((d >= 1) & (d < 1.6), depth * 0.35 * np.cos((d - 1) / 0.6 * np.pi / 2) ** 2, 0)
                h += (bowl + rim).astype(F32)
                if r > 14:
                    surf[d < 0.85] = ids["krater tabanı"] if planet == "moon" else ids["toz"]
                self.craters.append((cx * cell, cy * cell, r * cell, depth))
        if planet == "mars":
            dunes = np.sin((xx * 0.9 + yy * 0.35) / 7.0 + _noise(n, 12, rng) * 3) * 1.6
            mask = _noise(n, 5, rng) > 0.1
            h += np.where(mask, dunes, 0).astype(F32)
            surf[(surf == 0) & mask] = ids["gevşek kum"]
            surf[(surf == 0)] = ids["regolit"]
        elif planet == "moon":
            surf[surf == 0] = ids["regolit"]
        else:   # titan
            h += _noise(n, 10, rng) * 6
            surf[:] = ids["organik kum"]
            surf[_noise(n, 8, rng) > 0.35] = ids["buz kaya"]
        # başlangıç alanını (harita merkezi) düzleştir: koloni / iniş alanı
        c = n // 2
        dist = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
        k = np.clip((dist - 7) / 14, 0, 1)        # yalnız ~14 m'lik iniş/koloni alanı düz
        h = h * k + h[c, c] * (1 - k)
        h -= h[c, c]
        self.lake_level = None
        if planet == "titan":
            # göl: başlangıçtan uzak bir çukur, seviyenin altı metan gölü, kıyısı ıslak
            lx, ly = int(n * 0.78), int(n * 0.3)
            dd = np.sqrt(((xx - lx + n / 2) % n - n / 2) ** 2 + ((yy - ly + n / 2) % n - n / 2) ** 2)
            h -= (np.clip(1 - dd / 70, 0, 1) ** 1.5 * 14).astype(F32)
            basin = dd < 80
            self.lake_level = min(float(np.percentile(h[basin], 35)), -2.0)
            surf[basin & (h < self.lake_level + 0.6)] = ids["ıslak kıyı"]
            surf[basin & (h < self.lake_level)] = ids["metan gölü"]
            self.lake = basin & (h < self.lake_level)
        # kayalar: kaya alanlarında yoğun; başlangıç çevresi temiz
        rocks = []
        rock_field = _noise(n, 9, rng)
        cnt = {"moon": 260, "mars": 380, "titan": 220}[planet]
        tries = 0
        while len(rocks) < cnt and tries < cnt * 20:
            tries += 1
            x, y = rng.uniform(0, n), rng.uniform(0, n)
            if math.hypot(x - c, y - c) < 20:
                continue
            if rock_field[int(y), int(x)] < -0.1 and rng.random() < 0.8:
                continue
            if self.lake_level is not None and self.lake[int(y), int(x)]:
                continue
            r = float(min(1.6, 0.18 + rng.pareto(3.0) * 0.25))       # m; çoğu küçük
            rocks.append((x * cell, y * cell, r))
            if r > 0.4:
                surf[int(y), int(x)] = ids["kaya"] if planet != "titan" else ids["buz kaya"]
        self.rocks = np.array(rocks, dtype=F32).reshape(-1, 3)
        self.h = h.astype(F32)
        self.surf = surf
        self._shade()

    # ---------------------------------------------------------------- örnekleme
    def height(self, x, y):
        """Çift doğrusal yükseklik (m); x, y metre (harita döngüsel)."""
        n, c = self.n, self.cell
        fx, fy = (x / c) % n, (y / c) % n
        i0, j0 = int(fx), int(fy)
        tx, ty = fx - i0, fy - j0
        i1, j1 = (i0 + 1) % n, (j0 + 1) % n
        h = self.h
        return float(h[j0, i0] * (1 - tx) * (1 - ty) + h[j0, i1] * tx * (1 - ty) + h[j1, i0] * (1 - tx) * ty + h[j1, i1] * tx * ty)

    def heights(self, xs, ys):
        n, c = self.n, self.cell
        fx, fy = np.mod(xs / c, n), np.mod(ys / c, n)
        i0, j0 = fx.astype(np.int32), fy.astype(np.int32)
        tx, ty = fx - i0, fy - j0
        i1, j1 = (i0 + 1) % n, (j0 + 1) % n
        h = self.h
        return h[j0, i0] * (1 - tx) * (1 - ty) + h[j0, i1] * tx * (1 - ty) + h[j1, i0] * (1 - tx) * ty + h[j1, i1] * tx * ty

    def gradient(self, x, y, d=0.5):
        return ((self.height(x + d, y) - self.height(x - d, y)) / (2 * d),
                (self.height(x, y + d) - self.height(x, y - d)) / (2 * d))

    def surface_at(self, x, y):
        n, c = self.n, self.cell
        return SURFACE_IDS[self.surf[int(y / c) % n, int(x / c) % n]]

    def slope_deg(self, x, y):
        gx, gy = self.gradient(x, y)
        return math.degrees(math.atan(math.hypot(gx, gy)))

    def rocks_near(self, x, y, r):
        if not len(self.rocks):
            return self.rocks
        d = np.hypot(self.rocks[:, 0] - x, self.rocks[:, 1] - y)
        return self.rocks[d < r + self.rocks[:, 2]]

    # ------------------------------------------------------------------- renk
    def _shade(self):
        sun = np.array(self.p["sun"], dtype=F32)
        sun /= np.linalg.norm(sun)
        gy, gx = np.gradient(self.h, self.cell)
        nz = 1 / np.sqrt(1 + gx * gx + gy * gy)
        nx, ny = -gx * nz, -gy * nz
        lam = np.clip(nx * sun[0] + ny * sun[1] + nz * sun[2], 0, 1)
        ambient = 0.10 if self.planet == "moon" else 0.30
        lam = lam ** 1.4                        # sert güneş: eğimler belirgin (Ay'da gölge kenarları keskin)
        light = ambient + (1 - ambient) * lam * 1.25
        base = np.array([SURFACES[s]["color"] for s in SURFACE_IDS], dtype=F32)[self.surf]
        rng = np.random.default_rng(3)
        grain = (1 + rng.uniform(-0.06, 0.06, self.h.shape)).astype(F32)
        col = base * (light * grain)[..., None]
        tint = {"mars": (1.30, 0.80, 0.56), "titan": (1.10, 0.90, 0.66)}.get(self.planet)   # Mars: demir oksit tozu (HiRISE renkleri)
        if tint:
            col *= np.array(tint, dtype=F32)
        if self.lake_level is not None:
            wet = self.lake
            col[wet] = np.array((30, 26, 24), dtype=F32) + 12 * lam[wet][:, None]       # koyu, yansımalı sıvı
        self.color = np.clip(col, 0, 255).astype(np.uint8)

# -*- coding: utf-8 -*-
"""
KOZMOGENİS // GÖRSEL EFEKTLER
Derin uzay gradyanı, nefes alan nebula, yanıp sönen yıldızlar, kayan yıldızlar,
parçacık sistemi (alev, duman, kıvılcım, plazma), ekran sarsıntısı, yumuşak
geçişler ve ışıma (glow) yardımcıları.
"""
import math
import sys
import random

import pygame

from .config import W, H, C

try:
    import numpy as np
    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None
    HAS_NUMPY = False


# ===========================================================================
# MATEMATİK / YUMUŞATMA
# ===========================================================================
def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def scale_color(c, k):
    return (clamp(int(c[0] * k), 0, 255), clamp(int(c[1] * k), 0, 255), clamp(int(c[2] * k), 0, 255))


def with_alpha(c, a):
    return (c[0], c[1], c[2], clamp(int(a), 0, 255))


def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t, s=1.70158):
    t = clamp(t, 0.0, 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_elastic(t):
    t = clamp(t, 0.0, 1.0)
    if t in (0.0, 1.0):
        return t
    return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1


def approach(value, target, speed, dt):
    """Üstel yaklaşma: kare hızından bağımsız yumuşak hareket."""
    return target + (value - target) * math.exp(-speed * dt)


class Spring:
    """Kritik sönümlü yay: hover büyümesi, panel kaydırma vb."""

    def __init__(self, value=0.0, stiffness=180.0, damping=22.0):
        self.value = value
        self.target = value
        self.vel = 0.0
        self.k = stiffness
        self.d = damping

    def update(self, dt):
        dt = min(dt, 1 / 30)
        f = (self.target - self.value) * self.k - self.vel * self.d
        self.vel += f * dt
        self.value += self.vel * dt
        return self.value

    def snap(self, v):
        self.value = self.target = v
        self.vel = 0.0


class Tween:
    """Zaman tabanlı tek seferlik geçiş."""

    def __init__(self, start, end, duration, ease=ease_out_cubic, delay=0.0):
        self.start, self.end = start, end
        self.duration = max(1e-4, duration)
        self.ease = ease
        self.t = -delay

    def update(self, dt):
        self.t += dt
        return self.value

    @property
    def value(self):
        if self.t <= 0:
            return self.start
        return lerp(self.start, self.end, self.ease(self.t / self.duration))

    @property
    def done(self):
        return self.t >= self.duration


# ===========================================================================
# IŞIMA SPRITE'LARI (önbellekli)
# ===========================================================================
_GLOW_CACHE = {}
_SOFT_CACHE = {}
_RING_CACHE = {}


def _to_display(s, alpha):
    """Sprite'ı ekran piksel formatına çevirir (hızlı karıştırma yolu); ekran yoksa olduğu gibi."""
    try:
        if pygame.display.get_surface() is not None:
            return s.convert_alpha() if alpha else s.convert()
    except pygame.error:
        pass
    return s


def glow_sprite(radius, color, intensity=1.0):
    """BLEND_ADD ile basılacak, siyah zeminli radyal ışıma."""
    radius = max(2, int(radius))
    if radius > 24:
        radius = radius // 4 * 4
    color = (int(color[0]) // 12 * 12, int(color[1]) // 12 * 12, int(color[2]) // 12 * 12)
    intensity = round(clamp(intensity, 0.0, 1.5) * 10) / 10.0
    key = (radius, color, intensity)
    s = _GLOW_CACHE.get(key)
    if s is not None:
        return s
    size = radius * 2
    s = pygame.Surface((size, size))
    s.fill((0, 0, 0))
    steps = min(radius, 28)
    for i in range(steps, 0, -1):
        r = radius * i / steps
        k = (1 - i / steps)
        k = (k ** 1.8) * intensity
        pygame.draw.circle(s, scale_color(color, k), (radius, radius), max(1, int(r)))
    s = _to_display(s, False)
    _GLOW_CACHE[key] = s
    if len(_GLOW_CACHE) > 900:
        _GLOW_CACHE.clear()
    return s


def soft_circle(radius, color, alpha=255):
    """Normal alfa ile basılan yumuşak kenarlı daire (duman, bulut)."""
    radius = max(2, int(radius))
    if radius > 16:                       # büyüyen duman her karede yeni yarıçap üretiyordu: önbellek ıskası
        radius = radius // 4 * 4 if radius < 64 else radius // 8 * 8
    alpha = int(clamp(alpha, 0, 255) // 8 * 8)
    key = (radius, color, alpha)
    s = _SOFT_CACHE.get(key)
    if s is not None:
        return s
    size = radius * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = min(radius, 18)
    for i in range(steps, 0, -1):
        r = radius * i / steps
        k = (1 - i / steps) ** 1.3
        pygame.draw.circle(s, (color[0], color[1], color[2], int(alpha * k)), (radius, radius), max(1, int(r)))
    s = _to_display(s, True)
    _SOFT_CACHE[key] = s
    if len(_SOFT_CACHE) > 900:
        _SOFT_CACHE.clear()
    return s


def draw_glow(surf, pos, radius, color, intensity=1.0):
    g = glow_sprite(radius, color, intensity)
    surf.blit(g, (int(pos[0] - g.get_width() / 2), int(pos[1] - g.get_height() / 2)),
              special_flags=pygame.BLEND_ADD)


def neon_ring(radius, color, width=3):
    key = (int(radius), color, width)
    s = _RING_CACHE.get(key)
    if s is not None:
        return s
    pad = 14
    size = int(radius * 2 + pad * 2)
    s = pygame.Surface((size, size))
    s.fill((0, 0, 0))
    c = size // 2
    for i, k in enumerate((0.12, 0.22, 0.4, 0.7)):
        pygame.draw.circle(s, scale_color(color, k), (c, c), int(radius), width + (3 - i) * 3)
    pygame.draw.circle(s, color, (c, c), int(radius), width)
    _RING_CACHE[key] = s
    return s


# ===========================================================================
# GRADYANLAR
# ===========================================================================
def vertical_gradient(size, top, bottom, mid=None):
    w, h = size
    surf = pygame.Surface((w, h))
    if HAS_NUMPY:
        t = np.linspace(0.0, 1.0, h, dtype=np.float32)[None, :, None]
        a = np.array(top, dtype=np.float32)[None, None, :]
        b = np.array(bottom, dtype=np.float32)[None, None, :]
        if mid is not None:
            m = np.array(mid, dtype=np.float32)[None, None, :]
            arr = np.where(t < 0.5, a + (m - a) * (t * 2), m + (b - m) * ((t - 0.5) * 2))
        else:
            arr = a + (b - a) * t
        arr = np.repeat(arr, w, axis=0).astype(np.uint8)
        pygame.surfarray.blit_array(surf, arr)
    else:
        for y in range(h):
            t = y / max(1, h - 1)
            if mid is not None:
                c = lerp_color(top, mid, t * 2) if t < 0.5 else lerp_color(mid, bottom, (t - 0.5) * 2)
            else:
                c = lerp_color(top, bottom, t)
            pygame.draw.line(surf, c, (0, y), (w, y))
    return surf


def vignette(size, strength=0.85):
    """Kenarları karartan SRCALPHA katman."""
    w, h = size
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    if HAS_NUMPY:
        xs = np.linspace(-1, 1, w, dtype=np.float32)[:, None]
        ys = np.linspace(-1, 1, h, dtype=np.float32)[None, :]
        d = np.sqrt(xs * xs * 0.9 + ys * ys * 1.1)
        a = np.clip((d - 0.55) / 0.85, 0, 1) ** 1.6 * 255 * strength
        s.fill((0, 0, 0, 0))
        px = pygame.surfarray.pixels_alpha(s)
        px[:, :] = a.astype(np.uint8)
        del px
    else:
        for i in range(24):
            k = i / 24
            pygame.draw.rect(s, (0, 0, 0, int(10 * strength)), (int(k * w * 0.25), int(k * h * 0.25),
                                                                 int(w - k * w * 0.5), int(h - k * h * 0.5)), 18)
    return s


# ===========================================================================
# NEBULA (değer gürültüsü, nefes alan katmanlar)
# ===========================================================================
def _value_noise(w, h, scale, rng):
    gw, gh = int(w / scale) + 3, int(h / scale) + 3
    grid = rng.random((gw, gh)).astype(np.float32)
    xs = np.linspace(0, gw - 2.001, w, dtype=np.float32)
    ys = np.linspace(0, gh - 2.001, h, dtype=np.float32)
    xi = xs.astype(np.int32)
    yi = ys.astype(np.int32)
    xf = xs - xi
    yf = ys - yi
    xf = xf * xf * (3 - 2 * xf)
    yf = yf * yf * (3 - 2 * yf)
    a = grid[xi][:, yi]
    b = grid[xi + 1][:, yi]
    c = grid[xi][:, yi + 1]
    d = grid[xi + 1][:, yi + 1]
    xf = xf[:, None]
    yf = yf[None, :]
    return (a * (1 - xf) + b * xf) * (1 - yf) + (c * (1 - xf) + d * xf) * yf


def make_nebula(w, h, colors, seed=1, density=1.0, lowres=4):
    """Renkli nebula katmanı (SRCALPHA)."""
    lw, lh = max(8, w // lowres), max(8, h // lowres)
    if HAS_NUMPY:
        rng = np.random.default_rng(seed)
        n = np.zeros((lw, lh), dtype=np.float32)
        amp, tot = 1.0, 0.0
        for sc in (90, 45, 22, 11, 6):
            n += _value_noise(lw, lh, sc / lowres * 4, rng) * amp
            tot += amp
            amp *= 0.55
        n /= tot
        warp = _value_noise(lw, lh, 30 / lowres * 4, rng)
        n = np.clip((n * 0.7 + warp * 0.3 - 0.42) * 2.6 * density, 0, 1)
        n = n ** 1.5
        hue = _value_noise(lw, lh, 70 / lowres * 4, rng)
        c0 = np.array(colors[0], dtype=np.float32)
        c1 = np.array(colors[1], dtype=np.float32)
        c2 = np.array(colors[2 % len(colors)], dtype=np.float32)
        h3 = hue[:, :, None]
        rgb = np.where(h3 < 0.5, c0 + (c1 - c0) * (h3 * 2), c1 + (c2 - c1) * ((h3 - 0.5) * 2))
        core = (n ** 3)[:, :, None]
        rgb = rgb * (0.65 + 0.35 * n[:, :, None]) + 255 * core * 0.35
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        small = pygame.Surface((lw, lh), pygame.SRCALPHA)
        pygame.surfarray.blit_array(small, rgb)
        alpha = pygame.surfarray.pixels_alpha(small)
        alpha[:, :] = np.clip(n * 210, 0, 255).astype(np.uint8)
        del alpha
        return pygame.transform.smoothscale(small, (w, h))
    # numpy yoksa: yumuşak bulutlar
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    r = random.Random(seed)
    for _ in range(int(60 * density)):
        col = colors[r.randrange(len(colors))]
        rad = r.randint(60, 220)
        s.blit(soft_circle(rad, col, r.randint(20, 60)), (r.randint(-rad, w), r.randint(-rad, h)))
    return s


class Nebula:
    """İki katmanlı, yavaşça kayan ve nefes alan nebula."""

    PALETTES = {
        "deep":   [(40, 60, 190), (130, 50, 200), (20, 160, 220)],
        "violet": [(110, 40, 190), (220, 60, 160), (60, 80, 220)],
        "ember":  [(200, 70, 40), (230, 140, 60), (120, 40, 120)],
        "teal":   [(20, 140, 160), (40, 90, 200), (90, 220, 200)],
        "storm":  [(220, 170, 40), (240, 110, 30), (200, 200, 90)],
    }

    def __init__(self, w=W, h=H, palette="deep", seed=7, density=1.0):
        cols = self.PALETTES.get(palette, self.PALETTES["deep"])
        self.w, self.h = w, h
        self.a = make_nebula(w + 160, h + 120, cols, seed, density)
        self.b = make_nebula(w + 160, h + 120, cols[::-1], seed + 31, density * 0.8)
        self.t = random.random() * 10

    def update(self, dt):
        self.t += dt

    def params(self, alpha=1.0, drift=(0, 0)):
        """Bu karenin tamsayı konum/alfa değerleri. Bulutsu çok yavaş hareket ettiğinden bunlar
        çoğu karede aynı kalır; arka plan bu anahtarla önbelleklenir (alfa 3'lük adımlarla, fark edilmez)."""
        t = self.t
        ka = 0.55 + 0.25 * math.sin(t * 0.35)
        kb = 0.45 + 0.25 * math.sin(t * 0.27 + 1.7)
        return (int(-80 + math.sin(t * 0.05) * 60 + drift[0]), int(-60 + math.cos(t * 0.04) * 40 + drift[1]),
                int(255 * ka * alpha) // 3 * 3,
                int(-80 - math.sin(t * 0.03) * 70 - drift[0] * 0.6), int(-60 + math.sin(t * 0.06) * 35),
                int(255 * kb * alpha) // 3 * 3)

    def draw_params(self, surf, p):
        ax, ay, aa, bx, by, ba = p
        self.a.set_alpha(aa)
        surf.blit(self.a, (ax, ay))
        self.b.set_alpha(ba)
        surf.blit(self.b, (bx, by))

    def draw(self, surf, alpha=1.0, drift=(0, 0)):
        self.draw_params(surf, self.params(alpha, drift))


# ===========================================================================
# YILDIZ ALANI
# ===========================================================================
STAR_COLORS = [(255, 255, 255), (200, 220, 255), (255, 240, 220), (170, 200, 255), (255, 220, 200)]


class Starfield:
    """Paralaks katmanlı, yanıp sönen yıldızlar. vx ile yatay kayar."""

    def __init__(self, w=W, h=H, count=420, seed=3):
        r = random.Random(seed)
        self.w, self.h = w, h
        self.stars = []
        for _ in range(count):
            layer = r.choice((0, 0, 0, 1, 1, 2))
            self.stars.append([
                r.uniform(0, w), r.uniform(0, h), layer,
                r.uniform(0, math.tau), r.uniform(0.6, 3.2),
                r.choice(STAR_COLORS), r.uniform(0.35, 1.0)
            ])
        self.t = 0.0

    def update(self, dt, vx=0.0, vy=0.0):
        self.t += dt
        if vx or vy:
            for s in self.stars:
                k = (0.15, 0.45, 1.0)[s[2]]
                s[0] -= vx * k * dt
                s[1] -= vy * k * dt
                if s[0] < -4:
                    s[0] += self.w + 8
                    s[1] = random.uniform(0, self.h)
                elif s[0] > self.w + 4:
                    s[0] -= self.w + 8
                if s[1] < -4:
                    s[1] += self.h + 8
                elif s[1] > self.h + 4:
                    s[1] -= self.h + 8

    def draw(self, surf, alpha=1.0, streak=0.0):
        t = self.t
        for x, y, layer, ph, sp, col, base in self.stars:
            tw = 0.55 + 0.45 * math.sin(t * sp + ph)
            k = base * tw * alpha
            if layer == 0:
                surf.set_at((int(x), int(y)), scale_color(col, k * 0.8))
            elif layer == 1:
                c = scale_color(col, k)
                if streak > 0:
                    pygame.draw.line(surf, c, (x, y), (x + streak * 0.4, y))
                else:
                    pygame.draw.circle(surf, c, (int(x), int(y)), 1)
            else:
                c = scale_color(col, k)
                if streak > 0:
                    pygame.draw.line(surf, c, (x, y), (x + streak, y), 2)
                else:
                    pygame.draw.circle(surf, c, (int(x), int(y)), 2)
                    if tw > 0.8:
                        draw_glow(surf, (x, y), 7, col, 0.55 * k)


class ShootingStars:
    def __init__(self):
        self.items = []
        self.timer = random.uniform(2, 5)

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(3, 9)
            a = random.uniform(0.25, 0.6)
            sp = random.uniform(700, 1100)
            self.items.append([random.uniform(100, W), random.uniform(-40, H * 0.4),
                               -math.cos(a) * sp, math.sin(a) * sp, 0.0, random.uniform(0.6, 1.0)])
        for s in self.items:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] += dt
        self.items = [s for s in self.items if s[4] < s[5]]

    def draw(self, surf):
        for x, y, vx, vy, t, life in self.items:
            k = math.sin(math.pi * t / life)
            tail = 0.11
            pygame.draw.line(surf, scale_color((200, 230, 255), k), (x, y), (x - vx * tail, y - vy * tail), 2)
            draw_glow(surf, (x, y), 9, (180, 220, 255), k)


# ===========================================================================
# TAM ARKA PLAN
# ===========================================================================
class SpaceBackground:
    """Derin uzay gradyanı + nefes alan nebula + yıldızlar + kayan yıldızlar + vinyet."""

    _BASE_CACHE = {}

    def __init__(self, palette="deep", seed=11, stars=420, density=1.0, tint=None):
        key = (palette, seed, density)
        cached = SpaceBackground._BASE_CACHE.get(key)
        if cached is None:
            grad = vertical_gradient((W, H), (2, 3, 12), (8, 6, 26), (5, 8, 24))
            neb = Nebula(W, H, palette, seed, density)
            vig = vignette((W, H), 0.9)
            cached = (grad, neb, vig)
            SpaceBackground._BASE_CACHE[key] = cached
        self.grad, self.nebula, self.vig = cached
        self.stars = Starfield(W, H, stars, seed + 5)
        self.shooting = ShootingStars()
        self.tint = tint
        self.pulse = 0.0
        self.palette = palette
        self._comp = None             # gradyan + bulutsu birleşik katmanı (yalnızca değişince yeniden çizilir)
        self._comp_key = None
        self._comp_t = 0.0
        self._tint_s = None

    def update(self, dt, vx=0.0, vy=0.0):
        self.nebula.update(dt)
        self.stars.update(dt, vx, vy)
        self.shooting.update(dt)
        self.pulse += dt

    def draw(self, surf, nebula_alpha=1.0, streak=0.0, drift=(0, 0)):
        from . import cinema
        strength = 0.6 if streak > 0 else 1.0
        layers = cinema.space_layers(self.palette, self.vig, strength)     # (pus+sıcak ışık, fırça×vinyet) ya da None
        p = (self.nebula.params(nebula_alpha, drift), id(layers[0]) if layers else 0)
        if WEB and self._comp is not None and self._comp_key[1] == p[1] and self.pulse - self._comp_t < 0.4:
            p = self._comp_key           # tarayıcıda bulutsu en fazla 0,4 sn'de bir yenilenir (hareketi saniyede ~3 px)
        if self._comp is None or self._comp_key != p:
            self._comp_t = self.pulse
            # gradyan + bulutsu (+ sinematik pus) birleşik katmanı: yalnızca görünür bir değişiklikte yeniden çizilir
            if self._comp is None:
                self._comp = pygame.Surface((W, H))
                try:
                    self._comp = self._comp.convert()
                except pygame.error:
                    pass
            self._comp.blit(self.grad, (0, 0))
            self.nebula.draw_params(self._comp, p[0])
            if layers:
                self._comp.blit(layers[0], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            self._comp_key = p
        surf.blit(self._comp, (0, 0))
        self.stars.draw(surf, 1.0, streak)
        if streak <= 0:
            self.shooting.draw(surf)
        if self.tint:
            if self._tint_s is None:
                if WEB:
                    self._tint_s = pygame.Surface((W, H))
                    self._tint_s.fill(self.tint[:3])
                    self._tint_s.set_alpha(self.tint[3] if len(self.tint) > 3 else 255)
                else:
                    self._tint_s = pygame.Surface((W, H), pygame.SRCALPHA)
                    self._tint_s.fill(self.tint)
            surf.blit(self._tint_s, (0, 0))
        if layers:
            cinema.space_dynamic(surf, self.palette, self.pulse, strength)    # huzmeler + toz zerreleri
            surf.blit(layers[1], (0, 0), special_flags=pygame.BLEND_RGB_MULT)  # fırça dokusu × vinyet × soğuk gölge
        else:
            surf.blit(self.vig, (0, 0))


# ===========================================================================
# PARÇACIK SİSTEMİ
# ===========================================================================
FIRE_RAMP = [(255, 255, 240), (255, 230, 120), (255, 160, 50), (230, 70, 30), (90, 20, 20)]
BLUE_RAMP = [(240, 255, 255), (160, 230, 255), (70, 160, 255), (40, 70, 200), (10, 20, 60)]
PURPLE_RAMP = [(255, 240, 255), (220, 150, 255), (160, 80, 255), (90, 40, 200), (30, 10, 60)]
PLASMA_RAMP = [(255, 255, 255), (200, 160, 255), (110, 140, 255), (150, 60, 255), (30, 10, 80)]
GOLD_RAMP = [(255, 255, 230), (255, 230, 120), (255, 190, 60), (200, 120, 30), (60, 30, 10)]
GREEN_RAMP = [(240, 255, 240), (160, 255, 200), (70, 230, 140), (30, 140, 80), (10, 40, 20)]


def ramp_color(ramp, t):
    t = clamp(t, 0.0, 0.999) * (len(ramp) - 1)
    i = int(t)
    return lerp_color(ramp[i], ramp[i + 1], t - i)


RAMPS = {
    "fire": FIRE_RAMP, "blue": BLUE_RAMP, "purple": PURPLE_RAMP, "plasma": PLASMA_RAMP,
    "gold": GOLD_RAMP, "green": GREEN_RAMP,
}


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "size", "grow", "kind",
                 "ramp", "drag", "grav", "color", "alpha", "spin", "add")

    def __init__(self):
        self.x = self.y = self.vx = self.vy = 0.0
        self.life = self.max = 1.0
        self.size = 4.0
        self.grow = 0.0
        self.kind = "glow"
        self.ramp = FIRE_RAMP
        self.drag = 0.0
        self.grav = 0.0
        self.color = (255, 255, 255)
        self.alpha = 255
        self.spin = 0.0
        self.add = True


class ParticleSystem:
    """
    Türler:
      fire   - additive alev, renk rampası
      smoke  - alfa duman, büyür ve söner
      spark  - çizgi kıvılcım
      glow   - tek renk additive nokta
      shard  - dönen kaya parçası
      ring   - genişleyen şok halkası
    """

    def __init__(self, cap=2600):
        self.p = []
        self.cap = cap
        self.rings = []
        self._smoke = None

    def clear(self):
        self.p.clear()
        self.rings.clear()

    def _new(self):
        if len(self.p) >= self.cap:
            self.p.pop(0)
        q = Particle()
        self.p.append(q)
        return q

    # --- yayıcılar ---------------------------------------------------------
    def fire(self, x, y, n=6, angle=math.pi / 2, spread=0.35, speed=(160, 320), size=(6, 14),
             life=(0.35, 0.8), ramp="fire", drag=1.2, grav=0.0):
        rp = RAMPS.get(ramp, FIRE_RAMP)
        for _ in range(n):
            q = self._new()
            a = angle + random.uniform(-spread, spread)
            s = random.uniform(*speed)
            q.x, q.y = x + random.uniform(-2, 2), y + random.uniform(-2, 2)
            q.vx, q.vy = math.cos(a) * s, math.sin(a) * s
            q.life = q.max = random.uniform(*life)
            q.size = random.uniform(*size)
            q.grow = q.size * 0.9
            q.kind = "fire"
            q.ramp = rp
            q.drag = drag
            q.grav = grav

    def smoke(self, x, y, n=3, angle=math.pi / 2, spread=0.8, speed=(30, 110), size=(14, 30),
              life=(1.6, 3.2), color=(150, 150, 160), alpha=150, grow=40, grav=-12):
        for _ in range(n):
            q = self._new()
            a = angle + random.uniform(-spread, spread)
            s = random.uniform(*speed)
            q.x, q.y = x + random.uniform(-6, 6), y + random.uniform(-6, 6)
            q.vx, q.vy = math.cos(a) * s, math.sin(a) * s
            q.life = q.max = random.uniform(*life)
            q.size = random.uniform(*size)
            q.grow = grow
            q.kind = "smoke"
            q.color = color
            q.alpha = alpha
            q.drag = 0.9
            q.grav = grav
            q.add = False

    def sparks(self, x, y, n=16, color=(255, 220, 140), speed=(120, 420), life=(0.25, 0.7), grav=220):
        for _ in range(n):
            q = self._new()
            a = random.uniform(0, math.tau)
            s = random.uniform(*speed)
            q.x, q.y = x, y
            q.vx, q.vy = math.cos(a) * s, math.sin(a) * s
            q.life = q.max = random.uniform(*life)
            q.size = 2
            q.kind = "spark"
            q.color = color
            q.drag = 1.6
            q.grav = grav

    def glow(self, x, y, n=8, color=(120, 220, 255), speed=(10, 80), size=(3, 8), life=(0.4, 1.2), drag=1.0, grav=0.0):
        for _ in range(n):
            q = self._new()
            a = random.uniform(0, math.tau)
            s = random.uniform(*speed)
            q.x, q.y = x, y
            q.vx, q.vy = math.cos(a) * s, math.sin(a) * s
            q.life = q.max = random.uniform(*life)
            q.size = random.uniform(*size)
            q.kind = "glow"
            q.color = color
            q.drag = drag
            q.grav = grav

    def shards(self, x, y, n=10, color=(140, 120, 110), speed=(60, 260), life=(0.6, 1.4)):
        for _ in range(n):
            q = self._new()
            a = random.uniform(0, math.tau)
            s = random.uniform(*speed)
            q.x, q.y = x, y
            q.vx, q.vy = math.cos(a) * s, math.sin(a) * s
            q.life = q.max = random.uniform(*life)
            q.size = random.uniform(2, 6)
            q.kind = "shard"
            q.color = color
            q.spin = random.uniform(-8, 8)
            q.drag = 0.6
            q.add = False

    def explosion(self, x, y, scale=1.0, ramp="fire"):
        self.fire(x, y, n=int(40 * scale), angle=0, spread=math.pi, speed=(60, 420 * scale),
                  size=(8 * scale, 20 * scale), life=(0.3, 0.9), ramp=ramp, drag=2.4)
        self.smoke(x, y, n=int(14 * scale), spread=math.pi, speed=(20, 120 * scale),
                   size=(16 * scale, 34 * scale), life=(1.2, 2.6), alpha=130, grav=-6)
        self.sparks(x, y, n=int(30 * scale))
        self.ring(x, y, 220 * scale, (255, 200, 120))

    def ring(self, x, y, radius, color, life=0.55, width=4):
        self.rings.append([x, y, radius, color, 0.0, life, width])

    # --- güncelle / çiz ----------------------------------------------------
    def update(self, dt, wind=0.0):
        keep = []
        for q in self.p:
            q.life -= dt
            if q.life <= 0:
                continue
            k = math.exp(-q.drag * dt)
            q.vx = q.vx * k + wind * dt
            q.vy = q.vy * k + q.grav * dt
            q.x += q.vx * dt
            q.y += q.vy * dt
            q.size += q.grow * dt * (q.life / q.max)
            keep.append(q)
        self.p = keep
        for r in self.rings:
            r[4] += dt
        self.rings = [r for r in self.rings if r[4] < r[5]]

    def draw(self, surf, ox=0, oy=0):
        add = pygame.BLEND_RGB_ADD
        smoke_layer = None
        if WEB and len(self.p) > 120:
            # tarayıcıda çok sayıda büyük alfa duman pahalı (piksel başı ~13 ns): duman çeyrek çözünürlükte
            # ayrı bir katmana çizilip yumuşak büyütülür (duman zaten çok yumuşak; fark edilmez)
            sz = (max(1, int(surf.get_width() * SMOKE_K)), max(1, int(surf.get_height() * SMOKE_K)))
            smoke_layer = self._smoke
            if smoke_layer is None or smoke_layer.get_size() != sz:
                smoke_layer = self._smoke = pygame.Surface(sz, pygame.SRCALPHA)
            smoke_layer.fill((0, 0, 0, 0))
            self._smoke_used = False
        self._draw_parts(surf, ox, oy, add, smoke_layer)
        if smoke_layer is not None:
            surf.blit(pygame.transform.smoothscale(smoke_layer, surf.get_size()), (0, 0))

    def _draw_parts(self, surf, ox, oy, add, smoke_layer):
        for q in self.p:
            t = 1 - q.life / q.max
            x, y = q.x + ox, q.y + oy
            if q.kind == "fire":
                col = ramp_color(q.ramp, t)
                g = glow_sprite(max(2, int(q.size)), col, 1.0 - t * 0.5)
                surf.blit(g, (x - g.get_width() / 2, y - g.get_height() / 2), special_flags=add)
            elif q.kind == "smoke":
                a = q.alpha * (1 - t) * min(1.0, t * 6 + 0.2)
                if a < 6:
                    continue                      # görünmez kuyruk
                if smoke_layer is not None:
                    g = soft_circle(max(3, int(q.size * SMOKE_K)), q.color, a)
                    smoke_layer.blit(g, (x * SMOKE_K - g.get_width() / 2, y * SMOKE_K - g.get_height() / 2))
                    continue
                g = soft_circle(max(3, int(q.size)), q.color, a)
                surf.blit(g, (x - g.get_width() / 2, y - g.get_height() / 2))
            elif q.kind == "spark":
                col = scale_color(q.color, 1 - t)
                pygame.draw.line(surf, col, (x, y), (x - q.vx * 0.03, y - q.vy * 0.03), 2)
            elif q.kind == "glow":
                g = glow_sprite(max(2, int(q.size * 2)), q.color, 1 - t)
                surf.blit(g, (x - g.get_width() / 2, y - g.get_height() / 2), special_flags=add)
            elif q.kind == "shard":
                ang = q.spin * (q.max - q.life)
                s = q.size
                pts = [(x + math.cos(ang + i * 2.1) * s, y + math.sin(ang + i * 2.1) * s) for i in range(3)]
                pygame.draw.polygon(surf, scale_color(q.color, 1 - t * 0.6), pts)
        for x, y, rad, col, t, life, wdt in self.rings:
            k = t / life
            r = max(2, int(rad * ease_out_cubic(k)))
            pygame.draw.circle(surf, scale_color(col, 1 - k), (int(x + ox), int(y + oy)), r, max(1, int(wdt * (1 - k)) + 1))


# ===========================================================================
# EKRAN SARSINTISI
# ===========================================================================
class Shake:
    def __init__(self):
        self.trauma = 0.0
        self.t = 0.0

    def add(self, amount):
        self.trauma = clamp(self.trauma + amount, 0.0, 1.0)

    def set_min(self, amount):
        self.trauma = max(self.trauma, amount)

    def update(self, dt):
        self.t += dt
        self.trauma = max(0.0, self.trauma - dt * 0.9)

    def offset(self, max_px=22):
        s = self.trauma * self.trauma
        if s <= 0.001:
            return 0, 0
        return (int(max_px * s * math.sin(self.t * 47.3) * random.uniform(0.7, 1.0)),
                int(max_px * s * math.cos(self.t * 39.1) * random.uniform(0.7, 1.0)))


# ===========================================================================
# GEÇİŞ (sahne arası radyal karartma)
# ===========================================================================
class Transition:
    def __init__(self):
        self.active = False
        self.t = 0.0
        self.dur = 0.45
        self.callback = None
        self.phase = 0  # 0 kapanıyor, 1 açılıyor
        self.overlay = pygame.Surface((W, H), pygame.SRCALPHA)

    def start(self, callback, dur=0.45):
        self.active = True
        self.t = 0.0
        self.dur = dur
        self.callback = callback
        self.phase = 0

    def update(self, dt):
        if not self.active:
            return
        self.t += dt
        if self.phase == 0 and self.t >= self.dur:
            if self.callback:
                cb, self.callback = self.callback, None
                cb()
            self.phase = 1
            self.t = 0.0
        elif self.phase == 1 and self.t >= self.dur:
            self.active = False

    def draw(self, surf):
        if not self.active:
            return
        k = self.t / self.dur
        k = ease_in_out(k) if self.phase == 0 else 1 - ease_in_out(k)
        self.overlay.fill((2, 4, 12, int(255 * k)))
        surf.blit(self.overlay, (0, 0))
        if 0.05 < k < 0.98:
            r = int(40 + 900 * (1 - k))
            pygame.draw.circle(surf, scale_color(C["cyan"], k * 0.8), (W // 2, H // 2), r, 2)


# ===========================================================================
# TAM EKRAN RENK KATMANI (önbellekli)
# ===========================================================================
_OVERLAY = {}
# tarayıcıda (WebAssembly, SIMD yok) piksel başı alfa tam ekran ~19 ms; opak yüzey + yüzey alfası ~2 ms.
# Masaüstünde (SIMD) tam tersi: piksel başı alfa daha hızlı. Yol platforma göre seçilir.
WEB = sys.platform == "emscripten"
SMOKE_K = 0.25                 # tarayıcıda duman katmanı ölçeği


def overlay(surf, rgba, size=None):
    """Ekranın üstüne yarı saydam renk basar; her karede yeni yüzey ayırmaz."""
    size = size or surf.get_size()
    ov = _OVERLAY.get(size)
    if ov is None:
        if WEB:
            ov = pygame.Surface(size)
            try:
                ov = ov.convert()
            except pygame.error:
                pass
        else:
            ov = pygame.Surface(size, pygame.SRCALPHA)
        _OVERLAY[size] = ov
    r, g, b, a = rgba
    a = int(max(0, min(255, a)))
    if a <= 0:
        return
    if WEB:
        ov.fill((int(r), int(g), int(b)))
        ov.set_alpha(a)
    else:
        ov.fill((int(r), int(g), int(b), a))
    surf.blit(ov, (0, 0))


# ===========================================================================
# TARAMA ÇİZGİLERİ / HOLOGRAM
# ===========================================================================
_SCAN = {}


def scanlines(size, alpha=22, gap=3):
    key = (size, alpha, gap)
    s = _SCAN.get(key)
    if s is None:
        s = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(0, size[1], gap):
            pygame.draw.line(s, (0, 0, 0, alpha), (0, y), (size[0], y))
        _SCAN[key] = s
    return s


def draw_grid(surf, rect, color, step=40, alpha_k=0.18, t=0.0):
    x0, y0, w, h = rect
    col = scale_color(color, alpha_k)
    off = int(t * 20) % step
    for x in range(x0 - off, x0 + w, step):
        if x >= x0:
            pygame.draw.line(surf, col, (x, y0), (x, y0 + h))
    for y in range(y0 - off, y0 + h, step):
        if y >= y0:
            pygame.draw.line(surf, col, (x0, y), (x0 + w, y))


# ===========================================================================
# MARS TOZ FIRTINASI (zaman zaman kabaran, rüzgârla sürüklenen renkli toz)
# ===========================================================================
class DustStorm:
    COLORS = [(214, 128, 70), (232, 164, 104), (196, 100, 64), (240, 186, 140), (204, 116, 96)]

    def __init__(self, rect, seed=3, n=46):
        self.rect = pygame.Rect(rect)
        r = random.Random(seed)
        self.puffs = [[r.uniform(0, self.rect.w), r.uniform(0.15, 1.0) * self.rect.h, r.uniform(50, 170),
                       r.choice(self.COLORS), r.uniform(0.6, 1.4), r.uniform(0, 6)] for _ in range(n)]
        self.t = r.uniform(0, 30)
        self.wind = 1.0

    def intensity(self):
        """0..1 - fırtına yaklaşık 50 sn'lik döngülerle gelir ve dağılır."""
        a = math.sin(self.t * 0.12)
        return clamp(a * 1.6 - 0.2, 0.0, 1.0)

    def update(self, dt):
        self.t += dt
        k = self.intensity()
        self.wind = 40 + 260 * k
        for p in self.puffs:
            p[0] += self.wind * p[4] * dt
            p[1] += math.sin(self.t * 0.7 + p[5]) * 12 * dt
            if p[0] - p[2] > self.rect.w:
                p[0] = -p[2]

    def draw(self, surf):
        k = self.intensity()
        if k <= 0.02:
            return
        old = surf.get_clip()
        surf.set_clip(self.rect)
        overlay(surf, (190, 104, 60, int(110 * k)))
        for x, y, rad, col, sp, ph in self.puffs:
            a = int(clamp(150 * k * (0.6 + 0.4 * math.sin(self.t + ph)), 0, 255))
            s = soft_circle(int(rad), col, a)
            surf.blit(s, (self.rect.x + x - rad, self.rect.y + y - rad))
        # ince taneler
        rr = random.Random(int(self.t * 20))
        for _ in range(int(160 * k)):
            px = self.rect.x + rr.uniform(0, self.rect.w)
            py = self.rect.y + rr.uniform(0, self.rect.h)
            pygame.draw.line(surf, (246, 196, 150), (px, py), (px + 6 + self.wind * 0.03, py), 1)
        surf.set_clip(old)

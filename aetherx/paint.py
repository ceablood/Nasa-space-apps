# -*- coding: utf-8 -*-
"""
KOZMOGENİS // BOYALI ARKA PLANLAR (matte painting)
Fotogerçekçi ama elle boyanmış gibi görünen arka planlar: bilimsel olarak doğru
gökyüzü ve gök cisimleri, katmanlı (paralaks) kompozisyon, ardından boya
filtresi (Kuwahara fırça yumuşatması + yönlü fırça darbesi dokusu + tuval
dokusu + sıcak/soğuk renk sırlaması). Arka planlarda yazı yoktur; altı dilde
de aynı kalır. Üretilen görüntüler ~/.aetherx/paint klasörüne kaydedilir.

Türler:
  menu   – yörüngeden şafak: Dünya'nın ufku, Rayleigh atmosfer kuşağı, Ay, Samanyolu
  moon   – kapkara gök, gri regolit, gökyüzünde Dünya
  mars   – karamela rengi tozlu gök, Güneş çevresinde mavimsi hale (Mars gün batımı), mesalar
  venus  – kükürtlü turuncu pus, volkanik ova, doğrudan görünmeyen Güneş
  jupiter– Europa benzeri çatlak buz ova ve gökyüzünü dolduran Jüpiter
"""
import math
import os
from pathlib import Path

import numpy as np
import pygame

from . import space3d as S3

F32 = np.float32
VERSION = 6
_MEM = {}


# ------------------------------------------------------------------ yardımcılar
def _h(s):
    return sum((i + 1) * ord(c) for i, c in enumerate(s))


def _dir():
    return Path(os.path.expanduser("~")) / ".aetherx" / "paint"


def _rng(seed):
    return np.random.default_rng(seed)


def _fbm1(n, seed, octaves=6, base=4, rough=0.5):
    """0..1 arası 1B fraktal gürültü (n örnek)."""
    r = _rng(seed)
    out = np.zeros(n, F32)
    amp, tot = 1.0, 0.0
    x = np.linspace(0, 1, n, dtype=F32)
    for o in range(octaves):
        k = base * 2 ** o
        pts = r.random(k + 2).astype(F32)
        out += np.interp(x * k, np.arange(k + 2), pts).astype(F32) * amp
        tot += amp
        amp *= rough
    return out / tot


def _upsample(g, h, w):
    """Çift doğrusal büyütme (saf numpy)."""
    gh, gw = g.shape
    ys = np.linspace(0, gh - 1.001, h, dtype=F32)
    xs = np.linspace(0, gw - 1.001, w, dtype=F32)
    y0, x0 = ys.astype(np.int32), xs.astype(np.int32)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _noise2(h, w, seed, scale=64, octaves=4):
    """Değer gürültüsü (2B), 0..1."""
    r = _rng(seed)
    out = np.zeros((h, w), F32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale / 2 ** o))
        g = r.random((h // s + 3, w // s + 3)).astype(F32)
        g = g * g * (3 - 2 * g) * 0.5 + g * 0.5
        out += _upsample(g, h, w) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def _mix(a, b, t):
    t = np.asarray(t, F32)
    if t.ndim and t.shape[-1] != 1:
        t = t[..., None]
    return a + (np.asarray(b, F32) - a) * t


def _vgrad(h, w, stops):
    """Dikey renk gradyanı. stops: [(0..1, (r,g,b)), ...]"""
    y = np.linspace(0, 1, h, dtype=F32)
    cols = np.stack([np.interp(y, [s for s, _ in stops], [c[i] for _, c in stops]) for i in range(3)], 1).astype(F32)
    return np.repeat(cols[:, None, :], w, 1)


def _glow(img, cx, cy, rad, col, k, power=2.0):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rad
    g = np.clip(1 - d, 0, 1) ** power * k
    img += g[..., None] * np.asarray(col, F32)
    return img


def _stars(img, seed, n, ymax=None, bright=1.0):
    h, w, _ = img.shape
    r = _rng(seed)
    ymax = h if ymax is None else ymax
    xs = r.integers(0, w, n)
    ys = r.integers(0, max(1, ymax), n)
    b = (r.random(n) ** 3 * 200 + 30) * bright
    tint = r.random(n)
    for x, y, v, tt in zip(xs, ys, b, tint):
        col = np.array((v, v * (0.92 + 0.08 * tt), v * (0.9 + 0.2 * tt)), F32)
        img[y, x] = np.maximum(img[y, x], col)
        if v > 170 and 0 < x < w - 1 and 0 < y < h - 1:
            img[y, x - 1:x + 2] = np.maximum(img[y, x - 1:x + 2], col * 0.35)
            img[y - 1:y + 2, x] = np.maximum(img[y - 1:y + 2, x], col * 0.35)
    return img


def _paste_body(img, key, cx, cy, R, L=(-0.55, 0.25, 0.8), roll=-10, pitch=0.25, th=1024, spin=0.6, ring=None):
    M = S3.rot_z(math.radians(roll)) @ S3.rot_x(pitch)
    Lv = S3.norm3(np.array(L, F32))
    arr = S3.render_body(key, R, M, Lv, spin, 0.0, th, ring=ring).astype(F32)
    rgb, a = arr[..., :3], arr[..., 3:] / 255
    h, w, _ = img.shape
    x0, y0 = int(cx - R), int(cy - R)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + 2 * R), min(h, y0 + 2 * R)
    if xb <= xa or yb <= ya:
        return img
    sub = img[ya:yb, xa:xb]
    rs, as_ = rgb[ya - y0:yb - y0, xa - x0:xb - x0], a[ya - y0:yb - y0, xa - x0:xb - x0]
    img[ya:yb, xa:xb] = sub * (1 - as_) + rs * as_
    return img


def _ridge_layer(img, horizon, amp, seed, color, shade, haze_col, haze, rough=0.55, base=3, sharp=False,
                 light_dir=-1.0):
    """Bir dağ/tepe katmanı: profil + eğime göre ışık + atmosfer perspektifi."""
    h, w, _ = img.shape
    prof = _fbm1(w, seed, 7, base, rough)
    if sharp:
        prof = 1 - np.abs(prof * 2 - 1)
    top = horizon - prof * amp
    k = np.ones(15, F32) / 15
    slope = np.convolve(np.gradient(top), k, mode="same") * light_dir      # yumuşatılmış eğim (dikey çizgi olmaz)
    yy = np.arange(h, dtype=F32)[:, None]
    mask = yy >= top[None, :]
    depth = np.clip((yy - top[None, :]) / max(8.0, amp), 0, 1)
    warp = _noise2(h, w, seed + 9, 40, 3)
    facet = _noise2(h, w, seed + 11, 14, 3)
    lit = 0.78 + np.clip(slope[None, :], -1.2, 1.2) * 0.45 * (0.6 + 0.8 * warp) + (facet - 0.5) * 0.35 - depth * 0.22
    if sharp:                                                            # tortul katmanlar (Mars mesaları)
        lit = lit + np.sin((yy - top[None, :]) * 0.22 + warp * 7) * 0.07
    lit = np.clip(lit, 0.25, 1.3)
    tex = _noise2(h, w, seed + 5, 24, 3) * 0.6 + _noise2(h, w, seed + 6, 6, 2) * 0.4
    col = np.asarray(color, F32) * (lit * (0.86 + 0.28 * tex))[..., None]
    col = _mix(col, np.asarray(shade, F32), (depth * 0.35)[..., None])
    col = _mix(col, np.asarray(haze_col, F32), haze)
    img[mask] = col[mask]
    return img, top


# ------------------------------------------------------------------ boya filtresi
def _box(a, r):
    """Kutu ortalaması (kümülatif toplamla, kenarlar kırpılarak)."""
    p = np.pad(a, ((r + 1, r), (r + 1, r)) + ((0, 0),) * (a.ndim - 2), mode="edge")
    c = p.cumsum(0).cumsum(1)
    n = 2 * r + 1
    s = c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]
    return s / (n * n)


def _kuwahara(img, r=3):
    """Kuwahara: dört alt bölgeden en düşük varyanslının ortalaması -> fırça lekesi hissi, kenarlar korunur."""
    h, w, _ = img.shape
    lum = img @ np.array((0.299, 0.587, 0.114), F32)
    m = _box(img, r // 2 + 1)
    ml = _box(lum, r // 2 + 1)
    v = _box(lum * lum, r // 2 + 1) - ml * ml
    k = r // 2 + 1
    best = np.full((h, w), np.inf, F32)
    out = np.zeros_like(img)
    for dy, dx in ((-k, -k), (-k, k), (k, -k), (k, k)):
        vs = np.roll(np.roll(v, dy, 0), dx, 1)
        ms = np.roll(np.roll(m, dy, 0), dx, 1)
        sel = vs < best
        best = np.where(sel, vs, best)
        out[sel] = ms[sel]
    return out


def _brush_texture(h, w, seed):
    """Yönlü fırça darbeleri: yatayda uzatılmış ve hafif eğik gürültü."""
    r = _rng(seed)
    g = r.random((h // 2 + 4, w // 7 + 4)).astype(F32)
    a = _upsample(g, h, w)
    shift = (np.arange(h) * 0.16).astype(np.int32)        # ~9° eğim
    a = a[np.arange(h)[:, None], (np.arange(w)[None, :] + shift[:, None]) % w]
    fine = r.random((h, w)).astype(F32)
    return (a - 0.5) * 0.9 + (fine - 0.5) * 0.25


def _canvas(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    return (np.sin(xx * 1.9) * np.sin(yy * 1.7)) * 0.5


def painterly(img, seed=1, strength=1.0, r=4):
    """Fotogerçekçi görüntüyü yağlı boya mat resmine çevirir (aşırı yumuşatmadan)."""
    h, w, _ = img.shape
    k1 = _kuwahara(img, r)
    k2 = _box(_kuwahara(k1, 2), 1)                       # kare lekeleri yumuşat
    out = img * 0.42 + k2 * 0.58                         # ayrıntı kaybolmasın, plastik görünmesin
    br = _brush_texture(h, w, seed)
    lum = (out @ np.array((0.299, 0.587, 0.114), F32))[..., None] / 255
    out = out * (1 + br[..., None] * 0.07 * strength)
    out = out + _canvas(h, w)[..., None] * 3.0 * strength
    warm = np.array((1.04, 1.0, 0.94), F32)              # sıcak ışık, soğuk gölge sırlaması
    cool = np.array((0.94, 0.98, 1.06), F32)
    out = out * (cool + (warm - cool) * np.clip(lum * 1.4, 0, 1))
    # hafif vinyet
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    out *= (1 - np.clip(d - 0.55, 0, 1) * 0.35)[..., None]
    return np.clip(out, 0, 255)


# ------------------------------------------------------------------ sahneler
def _menu(w, h):
    img = _vgrad(h, w, [(0, (2, 3, 10)), (0.55, (4, 7, 20)), (1, (8, 14, 34))])
    # Samanyolu: çapraz, boyalı bulut bandı
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    band = np.exp(-(((yy - (h * 0.15 + xx * 0.32)) / (h * 0.16)) ** 2))
    neb = _noise2(h, w, 21, 140, 5)
    img += (band * neb ** 1.6 * 70)[..., None] * np.array((0.75, 0.68, 1.0), F32)
    img += (band * _noise2(h, w, 22, 40, 3) ** 3 * 50)[..., None] * np.array((1.0, 0.85, 0.7), F32)
    img = _stars(img, 23, 1600, bright=1.0)
    # Ay (sağ üst)
    img = _paste_body(img, "moon", int(w * 0.84), int(h * 0.2), int(h * 0.07), L=(-0.85, 0.15, 0.5), th=512)
    # Dünya ufku: gerçek doku, eğrilik, şafak
    R = int(w * 1.05)
    cx, cy = w * 0.5, h + R - h * 0.30
    tex = S3.texture("earth", 1024)
    th_, tw_ = tex["rgb"].shape[:2]
    X, Y = xx - cx, yy - cy
    d = np.sqrt(X * X + Y * Y) / R
    inside = d < 1
    edge = (1 - d) * R
    lon = 0.55 + X / w * 0.95
    lat = 0.80 - np.clip((Y + R) / (h * 0.30 + 1), 0, 1) * 0.55
    fx = (lon / (2 * math.pi) + 0.5) % 1 * tw_
    fy = np.clip((0.5 - lat / math.pi) * th_, 0, th_ - 1)
    x0, y0 = fx.astype(np.int32) % tw_, fy.astype(np.int32)
    ax, ay = (fx - np.floor(fx))[..., None], (fy - y0)[..., None]
    x1, y1 = (x0 + 1) % tw_, np.minimum(y0 + 1, th_ - 1)
    def samp(arr):
        a = arr.astype(F32)
        if a.ndim == 2:
            a = a[..., None]
        return (a[y0, x0] * (1 - ax) + a[y0, x1] * ax) * (1 - ay) + (a[y1, x0] * (1 - ax) + a[y1, x1] * ax) * ay
    e = samp(tex["rgb"])
    oc = np.clip(samp(tex["spec"]), 0, 1)                # kıyıyı pürüzsüz yeniden keskinleştir
    ocean = tex["rgb"][tex["spec"] > 0.97].reshape(-1, 3).mean(0).astype(F32)
    land = np.clip((e - oc * ocean) / np.maximum(1 - oc, 0.08), 0, 255)
    # pürüzsüz kıyı: maske önce bulanıklaştırılır (doku pikseli basamakları kaybolur), sonra ekran
    # çözünürlüğünde ince gürültüyle doğal, kenar yumuşatılmış bir kıyı çizgisi çıkarılır
    ocs = np.clip(samp(S3.blur(tex["spec"], 3)), 0, 1)[..., 0]
    ocs = ocs + (_noise2(h, w, 29, 7, 3) - 0.5) * 0.16
    wv = np.clip((ocs - 0.42) / 0.16, 0, 1)[..., None]
    wv = wv * wv * (3 - 2 * wv)
    e = land * (1 - wv) + ocean * wv
    cl = samp(tex["cloud"])
    e = e * (1 - cl) + 245 * cl
    # şafak: sol taraf aydınlık, sağa doğru gece (şehir ışıkları)
    day = np.clip((w * 0.86 - xx) / (w * 0.42), 0, 1)[..., None]
    speck = _noise2(h, w, 27, 3, 2)[..., None] ** 5 * 6           # şehir ışıkları: ince benekler
    lights = samp(tex["lights"]) * speck * np.array((255, 196, 120), F32) * (1 - day)
    shade = 0.06 + 0.94 * day ** 1.3
    e = e * shade + lights
    limb = np.clip(1 - edge / 34, 0, 1)[..., None] ** 1.5
    e = e * (1 - limb * 0.7) + np.array((120, 185, 255), F32) * limb * (0.35 + 0.65 * day)
    img = np.where(inside[..., None], e, img)
    # ince atmosfer kuşağı (Rayleigh mavisi, şafakta turuncu)
    out = np.clip(1 + edge / 26, 0, 1) * (edge < 0)
    atm = _mix(np.array((80, 150, 255), F32), np.array((255, 150, 70), F32), np.clip((w * 0.3 - xx) / (w * 0.3), 0, 1)[..., None])
    img += out[..., None] * atm * (0.25 + 0.75 * day)
    # doğan Güneş: ufukta parlama
    sx, sy = w * 0.16, h - h * 0.30 + 6
    img = _glow(img, sx, sy, w * 0.5, (255, 170, 90), 0.55, 2.4)
    img = _glow(img, sx, sy, w * 0.12, (255, 235, 200), 1.0, 2.0)
    img = _glow(img, sx, sy, w * 0.02, (255, 255, 255), 2.0, 1.4)
    return img


def _surface_scene(w, h, kind):
    ground_y = int(h * 0.75)                          # koloni sahnesindeki zemin çizgisiyle aynı
    if kind == "moon":
        img = _vgrad(h, w, [(0, (1, 1, 4)), (1, (3, 3, 8))])
        img = _stars(img, 31, 900, ymax=ground_y, bright=1.1)
        img = _paste_body(img, "earth", int(w * 0.8), int(h * 0.22), int(h * 0.11), L=(-0.7, 0.3, 0.6), th=1024, spin=2.2)
        sun = None
        layers = [((156, 154, 150), (66, 66, 70), 0.12, 130, 3), ((132, 130, 126), (56, 56, 60), 0.0, 60, 5)]
        ground = ((112, 110, 106), (64, 63, 62))
        haze_col = (20, 20, 24)
    elif kind == "mars":
        img = _vgrad(h, w, [(0, (122, 88, 64)), (0.45, (190, 140, 96)), (0.62, (214, 168, 120)), (1, (214, 168, 120))])
        sx, sy = w * 0.72, h * 0.30
        img = _glow(img, sx, sy, w * 0.22, (90, 140, 210), 0.55, 1.6)     # Mars'ta Güneş çevresi mavimsi
        img = _glow(img, sx, sy, w * 0.03, (240, 248, 255), 1.6, 1.5)
        img = _paste_body(img, "moon", int(w * 0.18), int(h * 0.16),
                          max(6, int(h * 0.018)), L=(0.6, 0.3, 0.7), th=256)
        layers = [((176, 112, 72), (120, 70, 46), 0.45, 120, 2), ((160, 94, 58), (104, 58, 38), 0.25, 70, 4),
                  ((150, 84, 50), (96, 52, 34), 0.08, 36, 6)]
        ground = ((168, 96, 58), (110, 60, 38))
        haze_col = (205, 156, 112)
    elif kind == "venus":
        img = _vgrad(h, w, [(0, (120, 82, 40)), (0.4, (196, 140, 66)), (0.62, (226, 176, 92)), (1, (226, 176, 92))])
        img = _glow(img, w * 0.4, h * 0.18, w * 0.5, (255, 210, 130), 0.35, 1.4)  # dağınık ışık, Güneş görünmez
        clouds = _noise2(h, w, 41, 90, 5)
        img = _mix(img, np.array((240, 196, 120), F32), (clouds ** 2 * 0.4 * (np.arange(h)[:, None] < ground_y))[..., None])
        layers = [((132, 86, 46), (82, 50, 28), 0.5, 90, 2), ((108, 68, 38), (66, 40, 22), 0.3, 50, 3),
                  ((90, 56, 32), (52, 32, 18), 0.1, 30, 7)]
        ground = ((96, 62, 36), (58, 36, 20))
        haze_col = (214, 160, 84)
    else:  # jupiter (Europa benzeri buz ova)
        img = _vgrad(h, w, [(0, (2, 3, 8)), (1, (6, 8, 18))])
        img = _stars(img, 51, 700, ymax=ground_y, bright=0.9)
        img = _paste_body(img, "jupiter", int(w * 0.62), int(h * 0.30), int(h * 0.42), L=(-0.75, 0.2, 0.55), roll=-4,
                          pitch=0.12, th=1024)
        layers = [((196, 206, 214), (120, 134, 150), 0.05, 60, 3), ((176, 186, 196), (104, 118, 134), 0.0, 34, 5)]
        ground = ((182, 190, 198), (112, 124, 140))
        haze_col = (60, 70, 90)
    # dağ katmanları (uzaktan yakına)
    n = len(layers)
    for i, (col, sh, hz, amp, base) in enumerate(layers):
        hy = ground_y - 6 + i * 6
        img, _ = _ridge_layer(img, hy, amp * h / 500, 100 + i * 7 + _h(kind) % 50, col, sh, haze_col, hz,
                              base=base, sharp=(kind == "mars" and i == 0))
    # zemin düzlüğü: perspektifle büyüyen kayalar/kraterler/çatlaklar
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    gm = yy >= ground_y + 4
    persp = np.clip((yy - ground_y) / (h - ground_y), 0, 1)
    tex = _noise2(h, w, 61, 30, 4)
    gcol = _mix(np.asarray(ground[1], F32) * np.ones((h, w, 3), F32), np.asarray(ground[0], F32), (0.5 + tex * 0.6 - persp * 0.2)[..., None])
    if kind == "jupiter":
        cr = _noise2(h, w, 62, 50, 3)
        lines = np.exp(-((cr - 0.5) / 0.012) ** 2)
        gcol = _mix(gcol, np.array((150, 96, 70), F32), (lines * 0.7)[..., None])   # kırmızımsı çatlaklar (lineae)
    img[gm] = gcol[gm]
    r = _rng(_h(kind) % 1000)
    for _ in range(140 if kind != "venus" else 90):
        y = int(ground_y + 6 + (r.random() ** 1.6) * (h - ground_y - 6))
        s = (y - ground_y) / (h - ground_y)
        rx, ry = int(2 + s * 26 * r.uniform(0.4, 1.2)), int(1 + s * 9 * r.uniform(0.4, 1.0))
        x = int(r.uniform(0, w))
        x0, x1, y0, y1 = max(0, x - rx), min(w, x + rx), max(0, y - ry), min(h, y + ry)
        if x1 <= x0 or y1 <= y0:
            continue
        sy, sx = np.mgrid[y0:y1, x0:x1].astype(F32)
        e = ((sx - x) / rx) ** 2 + ((sy - y) / ry) ** 2
        m = e < 1
        top = (sy - y) < -ry * 0.1
        base = np.asarray(ground[0], F32) * (1.15 if kind != "moon" else 1.05)
        rockc = np.where(top[..., None], base * 1.12, base * 0.62)
        img[y0:y1, x0:x1][m] = rockc[m]
        sh = (e < 1.9) & (e >= 1) & (sx > x)                 # gölge (ışık soldan)
        img[y0:y1, x0:x1][sh] *= 0.72
    # yere yakın atmosfer pusu
    if kind in ("mars", "venus"):
        hz = np.exp(-((yy - ground_y) / (h * 0.10)) ** 2)[..., None] * (0.35 if kind == "mars" else 0.5)
        img = _mix(img, np.asarray(haze_col, F32), hz)
    return img


SCENES = {"menu": _menu, "moon": lambda w, h: _surface_scene(w, h, "moon"),
          "mars": lambda w, h: _surface_scene(w, h, "mars"), "venus": lambda w, h: _surface_scene(w, h, "venus"),
          "jupiter": lambda w, h: _surface_scene(w, h, "jupiter")}


def is_ready(kind, size):
    w, h = size
    return (kind, w, h) in _MEM or (_dir() / f"{kind}_{w}x{h}_v{VERSION}.png").exists()


def warm(kind, size):
    """Arka plan iş parçacığında üretim (convert() yapılmaz; ana iş parçacığı sonra kullanır)."""
    return get(kind, size, convert=False)


def get(kind, size, convert=True):
    """Boyalı arka plan (pygame Surface). Bellekte ve diskte önbelleklenir."""
    w, h = size
    key = (kind, w, h)
    s = _MEM.get(key)
    if s is not None:
        return s
    f = _dir() / f"{kind}_{w}x{h}_v{VERSION}.png"
    web = os.sys.platform == "emscripten"            # tarayıcıda PNG önbelleği yok (zlib çökmesi)
    try:
        if not web and f.exists():
            s = pygame.image.load(str(f))
            if pygame.display.get_surface() is not None:     # ekran formatına: hızlı karıştırma
                try:
                    s = s.convert()
                except pygame.error:
                    pass
            elif convert:
                try:
                    s = s.convert()
                except pygame.error:
                    pass
            _MEM[key] = s
            return s
    except Exception:
        pass
    img = SCENES[kind](w, h)
    img = painterly(img, seed=_h(kind) % 997, r=3 if w >= 1200 else 2)
    s = S3.to_surface(np.dstack([img.astype(np.uint8), np.full((h, w), 255, np.uint8)]))
    if convert or pygame.display.get_surface() is not None:
        try:
            s = s.convert()          # opak: alfa kanallı tam ekran blit tarayıcıda ~19 ms, opak ~0,5 ms
        except pygame.error:
            pass
    try:
        if web:
            raise OSError("web")
        f.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(s, str(f))
    except Exception:
        pass
    _MEM[key] = s
    return s

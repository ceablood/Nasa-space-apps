# -*- coding: utf-8 -*-
"""
AETHER-X // SİNEMATİK GÖRÜNTÜ KATMANI
"Elle boyanmış Arcane tarzı + parlak stilize AAA malzeme" yönergesinin oyun içi karşılığı.
Sahnelerin dünya katmanına (arayüzden önce) uygulanır, böylece yazılar keskin kalır:

  god_rays(...)   hacimsel ışık huzmeleri (güneşten yayılan, gürültülü açısal ışınlar)
  motes(...)      havada süzülen, ışıkta parlayan toz zerreleri
  haze(...)       ufka doğru yoğunlaşan atmosferik pus
  brush(...)      yönlü fırça darbesi + tuval dokusu (çarpma karışımı)
  grade(...)      tamamlayıcı renk uyumu: sıcak ışık / soğuk gölge, vinyet
Ayar: AJANS > Ayarlar > SİNEMATİK EFEKTLER (i18n.PREFS["cinematic"]).
"""
import math

import numpy as np
import pygame

from . import i18n
from . import space3d as S3

F32 = np.float32
_CACHE = {}


def enabled():
    return i18n.PREFS.get("cinematic", True)


def _rgba_surface(rgb, a=None):
    h, w, _ = rgb.shape
    alpha = np.full((h, w), 255, np.uint8) if a is None else np.clip(a, 0, 255).astype(np.uint8)
    return S3.to_surface(np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha]))


# ----------------------------------------------------------------- ışık huzmeleri
def _rays_texture(size, color, seed):
    key = ("rays", size, color, seed)
    s = _CACHE.get(key)
    if s is not None:
        return s
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(F32) - size / 2
    ang = np.arctan2(yy, xx)
    rad = np.sqrt(xx * xx + yy * yy) / (size / 2)
    k = 48
    pts = r.random(k + 1).astype(F32)
    pts[-1] = pts[0]
    a01 = (ang / (2 * math.pi) + 0.5) * k
    i0 = np.floor(a01).astype(np.int32) % k
    fr = a01 - np.floor(a01)
    n1 = pts[i0] * (1 - fr) + pts[i0 + 1] * fr
    pts2 = r.random(17).astype(F32)
    pts2[-1] = pts2[0]
    a2 = (ang / (2 * math.pi) + 0.5) * 16
    j0 = np.floor(a2).astype(np.int32) % 16
    f2 = a2 - np.floor(a2)
    n2 = pts2[j0] * (1 - f2) + pts2[j0 + 1] * f2
    beam = np.clip(n1 * 0.6 + n2 * 0.6 - 0.45, 0, 1) ** 2.2
    fall = np.clip(1 - rad, 0, 1) ** 1.6
    core = np.exp(-rad * 9) * 0.6
    val = (beam * fall * 0.75 + core)[..., None]
    rgb = val * np.array(color, F32)[None, None, :]
    s = _rgba_surface(rgb)
    _CACHE[key] = s
    return s


def god_rays(surf, pos, color=(255, 200, 140), strength=0.6, size=1400, t=0.0, clip=None):
    """Toplamsal (BLEND_ADD) ışık huzmeleri; pos ekran dışında olabilir (huzmeler kenardan girer)."""
    if not enabled() or strength <= 0.02:
        return
    col = tuple(int(max(0, min(255, c * strength))) for c in color)
    col = tuple(int(c) // 8 * 8 for c in col)          # önbellek dostu renk adımı
    tex = _rays_texture(size, col, 3)
    old = surf.get_clip()
    if clip is not None:
        surf.set_clip(clip)
    surf.blit(tex, (int(pos[0] - tex.get_width() / 2), int(pos[1] - tex.get_height() / 2)), special_flags=pygame.BLEND_ADD)
    surf.set_clip(old)


# ----------------------------------------------------------------- toz zerreleri
def _mote_sprite(r, color):
    key = ("mote", r, color)
    s = _CACHE.get(key)
    if s is None:
        n = r * 2 + 1
        yy, xx = np.mgrid[0:n, 0:n].astype(F32) - r
        d = np.sqrt(xx * xx + yy * yy) / max(1, r)
        v = (np.clip(1 - d, 0, 1) ** 2)[..., None] * np.array(color, F32)[None, None, :]
        s = _rgba_surface(v)
        _CACHE[key] = s
    return s


def motes(surf, rect, t, n=60, color=(255, 230, 190), seed=5, strength=1.0):
    if not enabled() or strength <= 0.02:
        return
    rect = pygame.Rect(rect)
    rng = np.random.default_rng(seed)
    base = rng.random((n, 5))
    old = surf.get_clip()
    surf.set_clip(rect)
    for i in range(n):
        x0, y0, sp, ph, sz = base[i]
        x = rect.x + (x0 * rect.w + math.sin(t * (0.2 + sp * 0.4) + ph * 6) * 26 + t * (6 + sp * 10)) % rect.w
        y = rect.y + (y0 * rect.h - t * (4 + sp * 9) + math.cos(t * 0.5 + ph * 5) * 12) % rect.h
        tw = 0.55 + 0.45 * math.sin(t * (1.5 + sp * 2) + ph * 9)
        c = tuple(int(max(0, min(255, cc * tw * strength))) for cc in color)
        spr = _mote_sprite(1 + int(sz * 2.6), c)
        surf.blit(spr, (int(x - spr.get_width() / 2), int(y - spr.get_height() / 2)), special_flags=pygame.BLEND_ADD)
    surf.set_clip(old)


# ----------------------------------------------------------------- pus
def haze(surf, rect, color, strength=0.5, top=True):
    """Ufka doğru (görünümün üst kısmı) yoğunlaşan toplamsal pus."""
    if not enabled() or strength <= 0.02:
        return
    rect = pygame.Rect(rect)
    key = ("haze", rect.size, color, int(strength * 50), top)
    s = _CACHE.get(key)
    if s is None:
        h, w = rect.h, rect.w
        y = np.linspace(0, 1, h, dtype=F32)
        prof = (1 - y) ** 2.2 if top else y ** 2.2
        rgb = np.repeat((prof[:, None] * strength)[:, :, None] * np.array(color, F32)[None, None, :], w, 1)
        s = _rgba_surface(rgb)
        _CACHE[key] = s
    surf.blit(s, rect.topleft, special_flags=pygame.BLEND_ADD)


# ----------------------------------------------------------------- fırça + renk düzenleme
def _brush_surface(size, seed=11):
    key = ("brush", size, seed)
    s = _CACHE.get(key)
    if s is not None:
        return s
    from .paint import _brush_texture, _canvas
    w, h = size
    br = _brush_texture(h, w, seed)
    cv = _canvas(h, w)
    v = 243 + br * 22 + cv * 4                         # ~221..255: çarpma ile hafif fırça izleri
    rgb = np.repeat(v[..., None], 3, 2)
    rgb[..., 2] = rgb[..., 2] * 0.995                  # hafif sıcak kâğıt tonu
    s = _rgba_surface(rgb)
    _CACHE[key] = s
    return s


def brush(surf, rect):
    if not enabled():
        return
    rect = pygame.Rect(rect)
    surf.blit(_brush_surface(rect.size), rect.topleft, special_flags=pygame.BLEND_MULT)


def _grade_surfaces(size, warm, cool):
    key = ("grade", size, warm, cool)
    g = _CACHE.get(key)
    if g is not None:
        return g
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    vig = 1 - np.clip(d - 0.55, 0, 1) * 0.5
    # çarpma: kenarlarda soğuk-mor gölge (doymuş AO hissi), merkezde nötr
    mul = np.stack([vig * (255 - (1 - vig) * (255 - cool[0])), vig * (255 - (1 - vig) * (255 - cool[1])),
                    vig * (255 - (1 - vig) * (255 - cool[2]))], 2)
    # toplama: merkezde sıcak ışık sızıntısı
    add = np.clip(1 - d, 0, 1)[..., None] ** 2 * np.array(warm, F32)[None, None, :]
    g = (_rgba_surface(mul), _rgba_surface(add))
    _CACHE[key] = g
    return g


def grade(surf, rect, warm=(18, 10, 0), cool=(150, 140, 200)):
    """Tamamlayıcı renk uyumu: sıcak merkez ışığı, soğuk/mor kenar gölgesi ve vinyet."""
    if not enabled():
        return
    rect = pygame.Rect(rect)
    mul, add = _grade_surfaces(rect.size, warm, cool)
    surf.blit(mul, rect.topleft, special_flags=pygame.BLEND_MULT)
    surf.blit(add, rect.topleft, special_flags=pygame.BLEND_ADD)


def _combined(size, haze_col, haze_k, warm, cool):
    """Fırça dokusu x vinyet/soğuk gölge (çarpma) ve pus + sıcak ışık (toplama) tek seferde."""
    key = ("comb", size, haze_col, int(haze_k * 40), warm, cool)
    g = _CACHE.get(key)
    if g is not None:
        return g
    from .paint import _brush_texture, _canvas
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    vig = 1 - np.clip(d - 0.55, 0, 1) * 0.5
    bt = (243 + _brush_texture(h, w, 11) * 22 + _canvas(h, w) * 4) / 255.0
    cool = np.array(cool, F32) / 255.0
    mul = (bt * vig)[..., None] * (1 - (1 - vig)[..., None] * (1 - cool)[None, None, :]) * 255
    add = np.clip(1 - d, 0, 1)[..., None] ** 2 * np.array(warm, F32)[None, None, :]
    if haze_col is not None and haze_k > 0:
        prof = (1 - np.linspace(0, 1, h, dtype=F32)) ** 2.2 * haze_k
        add = add + prof[:, None, None] * np.array(haze_col, F32)[None, None, :]
    g = (_rgba_surface(mul), _rgba_surface(add))
    _CACHE[key] = g
    return g


def full_pass(surf, rect, t, sun=None, sun_col=(255, 200, 140), rays=0.5, mote_col=(255, 230, 190), n_motes=50,
              haze_col=None, haze_k=0.0, warm=(18, 10, 0), cool=(150, 140, 200), brushk=True):
    """Bir sahnenin dünya katmanına tüm sinematik geçişleri uygular (2 tam ekran karıştırma + huzme + toz)."""
    if not enabled():
        return
    rect = pygame.Rect(rect)
    mul, add = _combined(rect.size, tuple(int(c) for c in haze_col) if haze_col else None, round(haze_k, 2), warm, cool)
    surf.blit(add, rect.topleft, special_flags=pygame.BLEND_ADD)
    if sun is not None and rays > 0:
        god_rays(surf, sun, sun_col, rays, t=t, clip=rect)
    motes(surf, rect, t, n_motes, mote_col)
    surf.blit(mul, rect.topleft, special_flags=pygame.BLEND_MULT)


# ===========================================================================
# v3: "müze kalitesinde stilize anahtar görsel" katmanı — oyunun her yerine
# ===========================================================================
# Uzay arka planı paletlerine göre ışık / gölge uyumu (tamamlayıcı renkler):
#   sun     : ekran dışı yıldızın konumu (huzmeler kenardan girer)
#   key     : sıcak anahtar ışık rengi, mote: toz zerresi rengi
#   warm    : merkezde sıcak ışık sızıntısı, cool: kenarlarda soğuk/mor AO
PALETTE_LIGHT = {
    "deep":   {"sun": (1520, -120), "key": (255, 196, 140), "mote": (255, 226, 190), "warm": (20, 12, 2),
               "cool": (140, 140, 215), "haze": (24, 30, 60)},
    "ember":  {"sun": (1480, -80), "key": (255, 168, 96), "mote": (255, 210, 160), "warm": (26, 12, 0),
               "cool": (120, 160, 200), "haze": (50, 26, 18)},
    "teal":   {"sun": (120, -110), "key": (180, 255, 236), "mote": (210, 255, 240), "warm": (10, 16, 12),
               "cool": (190, 130, 200), "haze": (14, 40, 46)},
    "violet": {"sun": (1500, -100), "key": (255, 180, 220), "mote": (255, 220, 240), "warm": (18, 8, 14),
               "cool": (150, 170, 220), "haze": (36, 20, 54)},
}


def space_pass(surf, palette, t, strength=1.0):
    """Ortak uzay arka planı için tam sinematik geçiş: huzmeler, toz, pus, fırça + renk uyumu.
    Arka plan katmanına uygulanır; üstüne çizilen arayüz keskin kalır."""
    if not enabled():
        return
    p = PALETTE_LIGHT.get(palette, PALETTE_LIGHT["deep"])
    lowq = i18n.PREFS.get("quality") == "standard"
    full_pass(surf, surf.get_rect(), t, sun=p["sun"], sun_col=p["key"], rays=0.55 * strength,
              mote_col=p["mote"], n_motes=0 if lowq else 38, haze_col=p["haze"], haze_k=0.8 * strength,
              warm=p["warm"], cool=p["cool"])


def bloom(surf, strength=0.85, threshold=128):
    """Parlak alanlardan yumuşak ışık taşması (çok kademeli bulanık), toplamsal.
    İnce yazılar küçültmede ortalanıp eşik altında kaldığı için keskin kalır."""
    if not enabled() or strength <= 0.02 or i18n.PREFS.get("quality") == "standard":
        return
    w, h = surf.get_size()
    try:
        s1 = pygame.transform.smoothscale(surf, (max(1, w // 8), max(1, h // 8)))
    except (ValueError, pygame.error):
        return
    s1.fill((threshold,) * 3, special_flags=pygame.BLEND_RGB_SUB)
    s2 = pygame.transform.smoothscale(s1, (max(1, w // 24), max(1, h // 24)))       # geniş hale
    s2 = pygame.transform.smoothscale(s2, s1.get_size())
    s1.blit(s2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    s1 = pygame.transform.smoothscale(s1, (max(1, w // 4), max(1, h // 4)))
    big = pygame.transform.smoothscale(s1, (w, h))
    m = int(255 * min(1.0, strength))
    big.fill((m, m, m), special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def _edge(m, off):
    e = m.copy()
    e.erase(m.overlap_mask(m, off), (0, 0))
    return e


def stylize_sprite(img, rim=(255, 196, 150), shade=(96, 84, 150), light=(1, 1), brushk=True):
    """Kenar ışığı (rim) + karşı kenarda doymuş mor AO + yüzeyde yönlü fırça dokusu + yumuşak siluet.
    light: ışığın geldiği yönün tersi ofseti (1,1) = sol-üstten ışık."""
    if not enabled() or img is None:
        return img
    try:
        w, h = img.get_size()
        if w < 4 or h < 4:
            return img
        out = img.copy()
        if brushk and w * h < 900_000:
            from .paint import _brush_texture
            v = 236 + _brush_texture(h, w, 7) * 19
            br = _rgba_surface(np.repeat(v[..., None], 3, 2))
            out.blit(br, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        m = pygame.mask.from_surface(img, 60)
        lx, ly = light
        for k, a in ((1, 0.55), (2, 0.32), (4, 0.14)):          # kenar ışığı: ışığa bakan kenar
            c = tuple(int(cc * a) for cc in rim)
            e = _edge(m, (lx * k, ly * k)).to_surface(setcolor=(*c, 255), unsetcolor=(0, 0, 0, 255))
            out.blit(e, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        for k, a in ((1, 0.55), (3, 0.3), (6, 0.15)):           # gölge kenarı: soğuk/mor AO
            c = tuple(int(255 - (255 - cc) * a) for cc in shade)
            e = _edge(m, (-lx * k, -ly * k)).to_surface(setcolor=(*c, 255), unsetcolor=(255, 255, 255, 255))
            out.blit(e, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        return out
    except Exception:
        return img

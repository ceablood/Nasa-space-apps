# -*- coding: utf-8 -*-
"""
KOZMOGENİS // ARAYÜZ
Cam görünümlü, neon kenarlı, üstüne gelince büyüyen butonlar; kayan paneller,
kaydırıcılar, sekmeler, metin girişi, barlar, prosedürel ikonlar, bildirimler.
"""
import math

import pygame

from . import i18n
from .config import C, FONT_CANDIDATES, MONO_CANDIDATES, W, H
from .fx import (Spring, clamp, draw_glow, ease_out_cubic, lerp, lerp_color,
                 scale_color, soft_circle)


# ===========================================================================
# GLOBAL ARAYÜZ BAĞLAMI
# ===========================================================================
class UIContext:
    mouse = (0, 0)
    mouse_down = False
    time = 0.0
    tooltip = None
    tooltip_color = C["cyan"]
    sound_hook = None          # callable(name)
    modal_lock = False

    @classmethod
    def sound(cls, name):
        if cls.sound_hook:
            try:
                cls.sound_hook(name)
            except Exception:
                pass

    @classmethod
    def set_tooltip(cls, text, color=None):
        cls.tooltip = text
        cls.tooltip_color = color or C["cyan"]


UI = UIContext


# ===========================================================================
# YAZI TİPLERİ
# ===========================================================================
_FONTS = {}
_TEXT_CACHE = {}


TEXT_SCALE = 1.1           # "yazıları biraz büyüt"
tr = i18n.tr


def font(size, bold=False, mono=False):
    key = (size, bold, mono)
    f = _FONTS.get(key)
    if f is None:
        px = int(round(size * (TEXT_SCALE if size < 22 else 1 + (TEXT_SCALE - 1) * 0.4)))
        try:
            f = pygame.font.SysFont(MONO_CANDIDATES if mono else FONT_CANDIDATES, px, bold=bold)
        except Exception:
            f = None
        if f is None:
            f = pygame.font.Font(None, int(px * 1.3))
            f.set_bold(bold)
        _FONTS[key] = f
    return f


def render_text(s, size=20, color=C["text"], bold=False, mono=False):
    key = (s, size, color, bold, mono)
    surf = _TEXT_CACHE.get(key)
    if surf is None:
        surf = font(size, bold, mono).render(str(s), True, color)
        if len(_TEXT_CACHE) > 4000:
            _TEXT_CACHE.clear()
        _TEXT_CACHE[key] = surf
    return surf


def text_size(s, size=20, bold=False, mono=False, raw=False):
    s = str(s)
    return font(size, bold, mono).size(s if raw else tr(s))


def fit_size(s, size, max_w, bold=False, min_size=9):
    """Metin max_w'ye sığana kadar punto küçültür (çevrilmiş metin için)."""
    while size > min_size and font(size, bold).size(s)[0] > max_w:
        size -= 1
    return size


def draw_text(surf, s, pos, size=20, color=C["text"], bold=False, anchor="topleft",
              shadow=True, glow=None, alpha=255, mono=False, raw=False, max_w=None):
    s = str(s)
    if not raw:
        s = tr(s)
    if max_w:
        size = fit_size(s, size, max_w, bold)
    img = render_text(s, size, color, bold, mono)
    r = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if glow:
        draw_glow(surf, r.center, max(r.w, r.h) * 0.6, glow, 0.35)
    if shadow:
        sh = render_text(s, size, (0, 0, 0), bold, mono)
        if alpha < 255:
            sh = sh.copy()
            sh.set_alpha(alpha // 2)
        surf.blit(sh, (r.x + 1, r.y + 2))
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, r)
    return r


def wrap_text(s, size, width, bold=False, raw=False):
    """Çevirir ve satırlara böler. Dönen satırlar çevrilmiştir: raw=True ile çizilmeli."""
    out = []
    s = str(s)
    if not raw:
        s = tr(s)
    for para in s.split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if text_size(test, size, bold, raw=True)[0] <= width or not line:
                line = test
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def draw_paragraph(surf, s, pos, width, size=18, color=C["text"], bold=False, gap=4, max_lines=None, raw=False):
    lines = wrap_text(s, size, width, bold, raw)
    if max_lines:
        lines = lines[:max_lines]
    x, y = pos
    lh = font(size, bold).get_linesize() + gap - 4
    for ln in lines:
        draw_text(surf, ln, (x, y), size, color, bold, shadow=True, raw=True)
        y += lh
    return y - pos[1]


def fmt_num(v):
    v = float(v)
    lang = i18n.LANG
    en = lang == "en"
    if abs(v) >= 1_000_000:
        s = f"{v / 1_000_000:.1f}" + ("М" if lang == "ru" else "M")
    elif abs(v) >= 10_000:
        s = f"{v / 1000:.1f}" + {"tr": "B", "en": "K", "de": "T", "fr": "k", "es": "K", "ru": "К"}.get(lang, "K")
    elif v == int(v):
        if en:
            return f"{int(v):,}"
        return f"{int(v):,}".replace(",", "\u202f" if lang in ("fr", "ru") else ".")
    else:
        s = f"{v:.1f}"
    return s if en else s.replace(".", ",")


def fmt_time(sec):
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"


# ===========================================================================
# CAM PANEL
# ===========================================================================
_PANEL_CACHE = {}


def _rounded(surf, color, rect, radius, width=0):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def glass_surface(w, h, accent=C["cyan"], alpha=180, radius=18, glow=True, strong=False):
    from . import settings as _SET
    if _SET.get("high_contrast"):                 # AYARLAR > ERİŞİLEBİLİRLİK: yüksek kontrast (opak panel)
        alpha = max(alpha, 240)
    key = (w, h, accent, alpha, radius, glow, strong)
    s = _PANEL_CACHE.get(key)
    if s is not None:
        return s
    pad = 16 if glow else 0
    s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    if glow:
        for i in range(8, 0, -1):
            a = int((40 if strong else 22) * (1 - i / 9))
            _rounded(s, (*accent, a), (pad - i * 2, pad - i * 2, w + i * 4, h + i * 4), radius + i * 2, 3)
    body = pygame.Rect(pad, pad, w, h)
    _rounded(s, (3, 6, 14, min(255, alpha + 30)), body, radius)
    # üst parlama
    hl = pygame.Surface((w, max(2, h // 2)), pygame.SRCALPHA)
    for y in range(hl.get_height()):
        k = 1 - y / hl.get_height()
        pygame.draw.line(hl, (200, 225, 255, int(26 * k * k)), (0, y), (w, y))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    _rounded(mask, (255, 255, 255, 255), (0, 0, w, h), radius)
    hl_full = pygame.Surface((w, h), pygame.SRCALPHA)
    hl_full.blit(hl, (0, 0))
    hl_full.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(hl_full, (pad, pad))
    # iç renk tonu
    tint = pygame.Surface((w, h), pygame.SRCALPHA)
    _rounded(tint, (*accent, 10), (0, 0, w, h), radius)
    s.blit(tint, (pad, pad))
    # kenarlar
    _rounded(s, (*accent, 200 if strong else 140), body, radius, 2)
    _rounded(s, (255, 255, 255, 30), body.inflate(-6, -6), max(2, radius - 3), 1)
    # köşe parlamaları
    cl = 18
    for (x, y, dx, dy) in ((body.left, body.top, 1, 1), (body.right - 1, body.top, -1, 1),
                           (body.left, body.bottom - 1, 1, -1), (body.right - 1, body.bottom - 1, -1, -1)):
        pygame.draw.line(s, (*accent, 255), (x + dx * radius * 0.4, y), (x + dx * (radius * 0.4 + cl), y), 2)
    if len(_PANEL_CACHE) > 300:
        _PANEL_CACHE.clear()
    _PANEL_CACHE[key] = s
    return s


def glass_panel(surf, rect, accent=C["cyan"], alpha=180, radius=18, glow=True, title=None,
                icon=None, strong=False, offset_alpha=255):
    rect = pygame.Rect(rect)
    s = glass_surface(rect.w, rect.h, accent, alpha, radius, glow, strong)
    pad = 16 if glow else 0
    if offset_alpha < 255:
        s = s.copy()
        s.set_alpha(offset_alpha)
    surf.blit(s, (rect.x - pad, rect.y - pad))
    if title:
        tx = rect.x + 22
        if icon:
            draw_icon(surf, icon, (rect.x + 30, rect.y + 26), 18, accent)
            tx = rect.x + 48
        draw_text(surf, title, (tx, rect.y + 14), 20, C["text"], bold=True)
        pygame.draw.line(surf, scale_color(accent, 0.6), (rect.x + 18, rect.y + 44), (rect.right - 18, rect.y + 44), 1)
        draw_glow(surf, (rect.x + 18, rect.y + 44), 8, accent, 0.8)
    return rect


def neon_line(surf, a, b, color, width=2, glow=True):
    if glow:
        pygame.draw.line(surf, scale_color(color, 0.3), a, b, width + 4)
    pygame.draw.line(surf, color, a, b, width)


def dashed_line(surf, a, b, color, dash=10, gap=8, width=2, phase=0.0):
    ax, ay = a
    bx, by = b
    d = math.hypot(bx - ax, by - ay)
    if d < 1:
        return
    ux, uy = (bx - ax) / d, (by - ay) / d
    t = -(phase % (dash + gap))
    while t < d:
        s0 = max(0, t)
        s1 = min(d, t + dash)
        if s1 > s0:
            pygame.draw.line(surf, color, (ax + ux * s0, ay + uy * s0), (ax + ux * s1, ay + uy * s1), width)
        t += dash + gap


# ===========================================================================
# BARLAR
# ===========================================================================
def draw_bar(surf, rect, frac, color, label=None, value=None, bg=(10, 16, 34), glow=True,
             segments=0, icon=None, warn_below=None, size=15):
    rect = pygame.Rect(rect)
    frac = clamp(frac, 0.0, 1.0)
    col = color
    if warn_below is not None and frac < warn_below:
        blink = 0.5 + 0.5 * math.sin(UI.time * 10)
        col = lerp_color(C["red"], color, blink * 0.3)
    pygame.draw.rect(surf, bg, rect, border_radius=rect.h // 2)
    fill = rect.copy()
    fill.w = int(rect.w * frac)
    if fill.w > 2:
        pygame.draw.rect(surf, scale_color(col, 0.55), fill, border_radius=rect.h // 2)
        inner = fill.inflate(-4, -rect.h // 2)
        inner.y = fill.y + 2
        if inner.w > 0 and inner.h > 0:
            pygame.draw.rect(surf, col, inner, border_radius=inner.h // 2)
        if glow:
            draw_glow(surf, (fill.right - 2, fill.centery), rect.h * 1.3, col, 0.7)
    if segments:
        for i in range(1, segments):
            x = rect.x + rect.w * i / segments
            pygame.draw.line(surf, (4, 8, 20), (x, rect.y + 1), (x, rect.bottom - 2), 2)
    pygame.draw.rect(surf, scale_color(color, 0.8), rect, 1, border_radius=rect.h // 2)
    tx = rect.x
    if icon:
        draw_icon(surf, icon, (rect.x - 16, rect.centery), 14, color)
    if label:
        draw_text(surf, label, (tx, rect.y - size - 6), size, C["text_dim"], bold=True)
    if value is not None:
        draw_text(surf, value, (rect.right, rect.y - size - 6), size, C["text"], bold=True, anchor="topright")


def draw_risk_bars(surf, rect, fail, partial, success, title=True):
    """Kırmızı / sarı / yeşil 3'lü risk barı."""
    rect = pygame.Rect(rect)
    rows = [("BAŞARISIZLIK RİSKİ", fail, C["red"]), ("KISMİ BAŞARI RİSKİ", partial, C["gold"]),
            ("TAM BAŞARI ŞANSI", success, C["green"])]
    gap = rect.h / 3
    for i, (lab, v, col) in enumerate(rows):
        y = rect.y + i * gap + gap * 0.55
        draw_bar(surf, (rect.x, y, rect.w, 14), v, col, label=lab if title else None,
                 value=i18n.pct(v * 100), size=13)


# ===========================================================================
# İKONLAR (prosedürel vektör)
# ===========================================================================
def draw_icon(surf, name, center, size, color, width=2):
    x, y = int(center[0]), int(center[1])
    s = size
    c = color
    dl = pygame.draw.line
    if name == "money":
        pygame.draw.circle(surf, c, (x, y), s // 2 + 2, width)
        draw_text(surf, "₺" if False else "P", (x, y), int(s * 0.9), c, bold=True, anchor="center", shadow=False)
    elif name == "rp":
        for a in range(3):
            ang = a * math.pi / 3
            rx, ry = math.cos(ang) * s * 0.55, math.sin(ang) * s * 0.55
            pygame.draw.ellipse(surf, c, (x - s * 0.55, y - s * 0.2, s * 1.1, s * 0.4), 1) if a == 0 else None
            dl(surf, c, (x - rx, y - ry), (x + rx, y + ry), 1)
        pygame.draw.circle(surf, c, (x, y), max(2, s // 6))
        pygame.draw.circle(surf, c, (x, y), s // 2, 1)
    elif name == "fuel":
        r = pygame.Rect(0, 0, s * 0.6, s * 0.9)
        r.center = (x, y + 2)
        pygame.draw.rect(surf, c, r, width, border_radius=3)
        pygame.draw.rect(surf, c, (r.x + 3, r.centery, r.w - 6, r.h // 2 - 3))
        dl(surf, c, (r.right, r.y + 3), (r.right + 4, r.y - 2), width)
    elif name == "o2":
        pygame.draw.circle(surf, c, (x - 3, y), s // 3, width)
        draw_text(surf, "2", (x + s // 3, y + 2), max(9, s // 2), c, bold=True, anchor="center", shadow=False)
    elif name == "bolt":
        pts = [(x + s * 0.1, y - s * 0.5), (x - s * 0.3, y + s * 0.05), (x, y + s * 0.05),
               (x - s * 0.1, y + s * 0.5), (x + s * 0.3, y - s * 0.05), (x, y - s * 0.05)]
        pygame.draw.polygon(surf, c, pts)
    elif name == "gear":
        for i in range(8):
            a = i * math.pi / 4 + UI.time * 0.6
            dl(surf, c, (x + math.cos(a) * s * 0.3, y + math.sin(a) * s * 0.3),
               (x + math.cos(a) * s * 0.52, y + math.sin(a) * s * 0.52), 3)
        pygame.draw.circle(surf, c, (x, y), int(s * 0.33), width)
        pygame.draw.circle(surf, c, (x, y), max(2, int(s * 0.12)))
    elif name == "rocket":
        pts = [(x, y - s * 0.55), (x + s * 0.18, y - s * 0.15), (x + s * 0.18, y + s * 0.3),
               (x - s * 0.18, y + s * 0.3), (x - s * 0.18, y - s * 0.15)]
        pygame.draw.polygon(surf, c, pts, width)
        pygame.draw.polygon(surf, c, [(x - s * 0.18, y + s * 0.05), (x - s * 0.38, y + s * 0.4), (x - s * 0.18, y + s * 0.3)])
        pygame.draw.polygon(surf, c, [(x + s * 0.18, y + s * 0.05), (x + s * 0.38, y + s * 0.4), (x + s * 0.18, y + s * 0.3)])
        pygame.draw.circle(surf, c, (x, int(y - s * 0.05)), max(2, s // 9))
    elif name == "planet":
        pygame.draw.circle(surf, c, (x, y), int(s * 0.35), width)
        pygame.draw.ellipse(surf, c, (x - s * 0.6, y - s * 0.14, s * 1.2, s * 0.28), 1)
    elif name == "star":
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = s * (0.5 if i % 2 == 0 else 0.22)
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surf, c, pts)
    elif name == "astro":
        pygame.draw.circle(surf, c, (x, int(y - s * 0.15)), int(s * 0.25), width)
        pygame.draw.rect(surf, c, (x - s * 0.15, y - s * 0.2, s * 0.3, s * 0.12), 0, border_radius=3)
        pygame.draw.arc(surf, c, (x - s * 0.4, y + s * 0.05, s * 0.8, s * 0.7), 0, math.pi, width)
    elif name == "warning":
        pts = [(x, y - s * 0.5), (x + s * 0.5, y + s * 0.4), (x - s * 0.5, y + s * 0.4)]
        pygame.draw.polygon(surf, c, pts, width)
        dl(surf, c, (x, y - s * 0.15), (x, y + s * 0.12), width + 1)
        pygame.draw.circle(surf, c, (x, int(y + s * 0.26)), 2)
    elif name == "check":
        dl(surf, c, (x - s * 0.35, y), (x - s * 0.08, y + s * 0.28), width + 1)
        dl(surf, c, (x - s * 0.08, y + s * 0.28), (x + s * 0.4, y - s * 0.3), width + 1)
    elif name == "cross":
        dl(surf, c, (x - s * 0.3, y - s * 0.3), (x + s * 0.3, y + s * 0.3), width + 1)
        dl(surf, c, (x + s * 0.3, y - s * 0.3), (x - s * 0.3, y + s * 0.3), width + 1)
    elif name == "lock":
        r = pygame.Rect(0, 0, s * 0.62, s * 0.48)
        r.center = (x, y + s * 0.12)
        pygame.draw.rect(surf, c, r, 0, border_radius=3)
        pygame.draw.arc(surf, c, (x - s * 0.22, y - s * 0.42, s * 0.44, s * 0.5), 0, math.pi, width)
    elif name == "antenna":
        pygame.draw.arc(surf, c, (x - s * 0.45, y - s * 0.45, s * 0.9, s * 0.9), math.pi * 1.0, math.pi * 1.5, width)
        pygame.draw.arc(surf, c, (x - s * 0.28, y - s * 0.28, s * 0.56, s * 0.56), math.pi * 1.0, math.pi * 1.5, width)
        dl(surf, c, (x, y), (x + s * 0.35, y + s * 0.45), width)
        pygame.draw.circle(surf, c, (x, y), 3)
    elif name == "camera":
        r = pygame.Rect(0, 0, s * 0.9, s * 0.6)
        r.center = (x, y + 2)
        pygame.draw.rect(surf, c, r, width, border_radius=4)
        pygame.draw.circle(surf, c, (x, y + 2), int(s * 0.18), width)
        pygame.draw.rect(surf, c, (x - s * 0.2, r.y - 4, s * 0.25, 4))
    elif name == "flask":
        pts = [(x - s * 0.12, y - s * 0.45), (x + s * 0.12, y - s * 0.45), (x + s * 0.12, y - s * 0.1),
               (x + s * 0.38, y + s * 0.42), (x - s * 0.38, y + s * 0.42), (x - s * 0.12, y - s * 0.1)]
        pygame.draw.polygon(surf, c, pts, width)
        pygame.draw.polygon(surf, c, [(x - s * 0.25, y + s * 0.2), (x + s * 0.25, y + s * 0.2),
                                      (x + s * 0.36, y + s * 0.4), (x - s * 0.36, y + s * 0.4)])
    elif name == "magnet":
        pygame.draw.arc(surf, c, (x - s * 0.35, y - s * 0.4, s * 0.7, s * 0.7), 0, math.pi, 4)
        dl(surf, c, (x - s * 0.33, y - s * 0.05), (x - s * 0.33, y + s * 0.38), 4)
        dl(surf, c, (x + s * 0.33, y - s * 0.05), (x + s * 0.33, y + s * 0.38), 4)
    elif name == "prism":
        pts = [(x, y - s * 0.45), (x + s * 0.42, y + s * 0.35), (x - s * 0.42, y + s * 0.35)]
        pygame.draw.polygon(surf, c, pts, width)
        for i, col in enumerate(((255, 80, 80), (255, 220, 80), (80, 255, 140), (80, 160, 255))):
            dl(surf, col, (x + s * 0.2, y), (x + s * 0.55, y - s * 0.15 + i * s * 0.1), 1)
    elif name == "box":
        r = pygame.Rect(0, 0, s * 0.8, s * 0.7)
        r.center = (x, y)
        pygame.draw.rect(surf, c, r, width, border_radius=2)
        dl(surf, c, r.topleft, (r.centerx, r.y + r.h * 0.3), 1)
        dl(surf, c, r.topright, (r.centerx, r.y + r.h * 0.3), 1)
    elif name == "wrench":
        dl(surf, c, (x - s * 0.35, y + s * 0.35), (x + s * 0.15, y - s * 0.15), 4)
        pygame.draw.circle(surf, c, (int(x + s * 0.22), int(y - s * 0.22)), int(s * 0.2), width)
    elif name == "heart":
        pygame.draw.circle(surf, c, (int(x - s * 0.17), int(y - s * 0.08)), int(s * 0.2))
        pygame.draw.circle(surf, c, (int(x + s * 0.17), int(y - s * 0.08)), int(s * 0.2))
        pygame.draw.polygon(surf, c, [(x - s * 0.37, y), (x + s * 0.37, y), (x, y + s * 0.42)])
    elif name == "medic":
        pygame.draw.rect(surf, c, (x - s * 0.12, y - s * 0.4, s * 0.24, s * 0.8))
        pygame.draw.rect(surf, c, (x - s * 0.4, y - s * 0.12, s * 0.8, s * 0.24))
    elif name == "eye":
        pygame.draw.ellipse(surf, c, (x - s * 0.5, y - s * 0.25, s, s * 0.5), width)
        pygame.draw.circle(surf, c, (x, y), int(s * 0.16))
    elif name == "chart":
        for i, hgt in enumerate((0.3, 0.55, 0.42, 0.8)):
            pygame.draw.rect(surf, c, (x - s * 0.42 + i * s * 0.22, y + s * 0.4 - s * hgt, s * 0.15, s * hgt))
    elif name == "flag":
        dl(surf, c, (x - s * 0.3, y - s * 0.45), (x - s * 0.3, y + s * 0.45), width)
        pygame.draw.polygon(surf, c, [(x - s * 0.3, y - s * 0.45), (x + s * 0.4, y - s * 0.28), (x - s * 0.3, y - s * 0.08)])
    elif name == "home":
        pygame.draw.polygon(surf, c, [(x, y - s * 0.45), (x + s * 0.45, y), (x - s * 0.45, y)], width)
        pygame.draw.rect(surf, c, (x - s * 0.32, y, s * 0.64, s * 0.42), width)
    elif name == "pickaxe":
        pygame.draw.arc(surf, c, (x - s * 0.45, y - s * 0.5, s * 0.9, s * 0.6), 0.2, math.pi - 0.2, 3)
        dl(surf, c, (x, y - s * 0.3), (x, y + s * 0.48), 3)
    elif name == "handshake":
        dl(surf, c, (x - s * 0.45, y), (x, y + s * 0.2), 3)
        dl(surf, c, (x + s * 0.45, y), (x, y + s * 0.2), 3)
        dl(surf, c, (x - s * 0.2, y - s * 0.12), (x + s * 0.2, y - s * 0.12), 3)
    elif name == "settings":
        draw_icon(surf, "gear", center, size, color, width)
    elif name == "save":
        r = pygame.Rect(0, 0, s * 0.8, s * 0.8)
        r.center = (x, y)
        pygame.draw.rect(surf, c, r, width, border_radius=3)
        pygame.draw.rect(surf, c, (r.x + 4, r.y, r.w - 8, r.h * 0.32))
    elif name == "play":
        pygame.draw.polygon(surf, c, [(x - s * 0.25, y - s * 0.35), (x + s * 0.38, y), (x - s * 0.25, y + s * 0.35)])
    elif name == "pause":
        pygame.draw.rect(surf, c, (x - s * 0.3, y - s * 0.35, s * 0.2, s * 0.7))
        pygame.draw.rect(surf, c, (x + s * 0.1, y - s * 0.35, s * 0.2, s * 0.7))
    elif name == "arrow_left":
        pygame.draw.polygon(surf, c, [(x - s * 0.4, y), (x + s * 0.1, y - s * 0.38), (x + s * 0.1, y + s * 0.38)])
        pygame.draw.rect(surf, c, (x, y - s * 0.12, s * 0.38, s * 0.24))
    elif name == "nova":
        pygame.draw.circle(surf, c, (x, y), int(s * 0.48), width)
        pygame.draw.ellipse(surf, c, (x - s * 0.3, y - s * 0.12, s * 0.6, s * 0.24))
        pygame.draw.circle(surf, (255, 255, 255), (x, y), max(2, int(s * 0.08)))
    elif name == "storm":
        pygame.draw.circle(surf, c, (x, y), int(s * 0.25))
        for i in range(8):
            a = i * math.pi / 4
            dl(surf, c, (x + math.cos(a) * s * 0.32, y + math.sin(a) * s * 0.32),
               (x + math.cos(a) * s * 0.5, y + math.sin(a) * s * 0.5), 2)
    elif name == "clock":
        pygame.draw.circle(surf, c, (x, y), int(s * 0.45), width)
        dl(surf, c, (x, y), (x, y - s * 0.3), width)
        dl(surf, c, (x, y), (x + s * 0.22, y + s * 0.05), width)
    elif name == "trophy":
        pygame.draw.polygon(surf, c, [(x - s * 0.35, y - s * 0.42), (x + s * 0.35, y - s * 0.42),
                                      (x + s * 0.22, y + s * 0.05), (x - s * 0.22, y + s * 0.05)])
        pygame.draw.rect(surf, c, (x - s * 0.06, y + s * 0.05, s * 0.12, s * 0.22))
        pygame.draw.rect(surf, c, (x - s * 0.28, y + s * 0.27, s * 0.56, s * 0.12))
    elif name == "satellite":
        pygame.draw.rect(surf, c, (x - s * 0.12, y - s * 0.12, s * 0.24, s * 0.24))
        pygame.draw.rect(surf, c, (x - s * 0.55, y - s * 0.1, s * 0.35, s * 0.2), 1)
        pygame.draw.rect(surf, c, (x + s * 0.2, y - s * 0.1, s * 0.35, s * 0.2), 1)
    elif name == "dust":
        for i in range(5):
            a = i * 1.26 + UI.time
            pygame.draw.circle(surf, c, (int(x + math.cos(a) * s * 0.3), int(y + math.sin(a) * s * 0.3)), 2)
        pygame.draw.circle(surf, c, (x, y), 3)
    elif name == "sun":
        pygame.draw.circle(surf, c, (x, y), int(s * 0.25))
        for i in range(8):
            a = i * math.pi / 4 + UI.time * 0.4
            dl(surf, c, (x + math.cos(a) * s * 0.34, y + math.sin(a) * s * 0.34),
               (x + math.cos(a) * s * 0.5, y + math.sin(a) * s * 0.5), 2)
    else:
        pygame.draw.circle(surf, c, (x, y), s // 3, width)


# ===========================================================================
# WIDGET'LAR
# ===========================================================================
class Widget:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.enabled = True

    def handle(self, e):
        return False

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


_BTN_BODY = {}
_BTN_GLOW = {}


def _button_body(size, top, bot, alpha, radius, shine_extra):
    key = (size, top, bot, alpha, radius, shine_extra)
    s = _BTN_BODY.get(key)
    if s is not None:
        return s
    w, h = size
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        pygame.draw.line(s, (*lerp_color(top, bot, t), alpha), (0, y), (w, y))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), 0, border_radius=radius)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    shine = pygame.Surface((w, max(1, h // 2)), pygame.SRCALPHA)
    pygame.draw.rect(shine, (255, 255, 255, 22 + shine_extra), shine.get_rect(), 0,
                     border_top_left_radius=radius, border_top_right_radius=radius)
    s.blit(shine, (0, 0))
    if len(_BTN_BODY) > 1500:
        _BTN_BODY.clear()
    _BTN_BODY[key] = s
    return s


def _button_glow(size, acc, k, radius):
    key = (size, acc, k, radius)
    s = _BTN_GLOW.get(key)
    if s is not None:
        return s
    w, h = size
    s = pygame.Surface((w + 40, h + 40), pygame.SRCALPHA)
    for i in range(5, 0, -1):
        a = int(34 * k * (1 - i / 6))
        pygame.draw.rect(s, (*acc, a), (20 - i * 4, 20 - i * 4, w + i * 8, h + i * 8), 0, border_radius=radius + i * 4)
    if len(_BTN_GLOW) > 800:
        _BTN_GLOW.clear()
    _BTN_GLOW[key] = s
    return s


class Button(Widget):
    """
    Cam gövde, neon kenar, hover'da yay ile büyüme, basınca küçülme,
    tıklama dalgası, ses.
    style: glass | big | ghost | danger | success | tab
    """

    def __init__(self, rect, label, on_click=None, accent=None, icon=None, size=18,
                 style="glass", tooltip=None, hotkey=None, disabled_reason=None, badge=None, data=None):
        super().__init__(rect)
        self.label = label
        self.on_click = on_click
        self.accent = accent or (C["red"] if style == "danger" else C["green"] if style == "success" else C["cyan"])
        self.icon = icon
        self.size = size
        self.style = style
        self.tooltip = tooltip
        self.hotkey = hotkey
        self.disabled_reason = disabled_reason
        self.badge = badge
        self.data = data
        self.scale = Spring(1.0, 260, 20)
        self.glow = Spring(0.0, 120, 18)
        self.hover = False
        self.pressed = False
        self.ripples = []
        self.selected = False
        self.pulse = False
        self.sublabel = None
        self._fit = (None, size)

    def set_enabled(self, ok, reason=None):
        self.enabled = ok
        self.disabled_reason = reason

    def click(self):
        if not self.enabled:
            UI.sound("deny")
            return
        UI.sound("click")
        self.ripples.append([UI.mouse[0] - self.rect.x, UI.mouse[1] - self.rect.y, 0.0])
        if self.on_click:
            self.on_click()

    def handle(self, e):
        if not self.visible:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.pressed = True
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            was = self.pressed
            self.pressed = False
            if was and self.rect.collidepoint(e.pos):
                self.click()
                return True
        if e.type == pygame.KEYDOWN and self.hotkey and e.key == self.hotkey and not UI.modal_lock:
            self.click()
            return True
        return False

    def update(self, dt):
        if not self.visible:
            return
        hov = self.rect.collidepoint(UI.mouse)
        if hov and not self.hover:
            UI.sound("hover")
        self.hover = hov
        big = 1.04 if self.style == "big" else 1.06
        if self.style == "tab":
            big = 1.02
        self.scale.target = (0.96 if self.pressed and hov else big if hov else 1.0) if self.enabled else 1.0
        self.glow.target = 1.0 if (hov and self.enabled) or self.selected else 0.0
        self.scale.update(dt)
        self.glow.update(dt)
        for r in self.ripples:
            r[2] += dt
        self.ripples = [r for r in self.ripples if r[2] < 0.5]
        if hov:
            tip = self.tooltip
            if not self.enabled and self.disabled_reason:
                tip = self.disabled_reason
            if tip:
                UI.set_tooltip(tip, self.accent if self.enabled else C["red"])

    def draw(self, surf):
        if not self.visible:
            return
        sc = round(self.scale.value * 60) / 60
        r = self.rect.copy()
        r.w = int(self.rect.w * sc)
        r.h = int(self.rect.h * sc)
        r.center = self.rect.center
        acc = self.accent if self.enabled else (90, 100, 125)
        g = clamp(self.glow.value, 0, 1)
        pulse = 0.0
        if self.pulse and self.enabled:
            pulse = 0.5 + 0.5 * math.sin(UI.time * 5)
        radius = min(16, r.h // 2) if self.style != "tab" else 10
        # dış ışıma
        if g > 0.02 or pulse > 0:
            k = max(g, pulse * 0.7)
            surf.blit(_button_glow(r.size, acc, round(k * 8) / 8, radius), (r.x - 20, r.y - 20))
        base_alpha = 120 if self.style == "ghost" else 175
        gq = round(g * 6) / 6
        pq = round(pulse * 4) / 4
        if self.style == "big":
            top = lerp_color((20, 40, 70), scale_color(acc, 0.55), 0.35 + gq * 0.3 + pq * 0.2)
            bot = lerp_color((8, 14, 30), scale_color(acc, 0.25), 0.3 + gq * 0.2)
        elif self.selected:
            top = lerp_color((24, 40, 80), scale_color(acc, 0.45), 0.6)
            bot = (10, 18, 40)
        else:
            top = lerp_color((24, 36, 70), scale_color(acc, 0.35), gq * 0.5)
            bot = (8, 14, 32)
        surf.blit(_button_body(r.size, top, bot, base_alpha, radius, int(gq * 18)), r)
        # tıklama dalgaları
        if self.ripples:
            old = surf.get_clip()
            surf.set_clip(r)
            for rx, ry, t in self.ripples:
                rr = int(10 + t * r.w * 1.4)
                pygame.draw.circle(surf, scale_color(acc, 1 - t / 0.5), (r.x + int(rx * sc), r.y + int(ry * sc)), rr, 2)
            surf.set_clip(old)
        pygame.draw.rect(surf, lerp_color(scale_color(acc, 0.55), acc, max(g, pulse)), r, 2, border_radius=radius)
        if self.style == "big":
            pygame.draw.rect(surf, (*scale_color(acc, 0.3),), r.inflate(-8, -8), 1, border_radius=max(2, radius - 4))
        # içerik
        col = C["text"] if self.enabled else C["text_mute"]
        lab = tr(self.label) if self.label else ""
        has_icon = bool(self.icon or not self.enabled)
        fkey = (lab, self.rect.w, has_icon)
        if self._fit[0] != fkey:
            avail = self.rect.w - 18 - ((self.size + 14) if has_icon else 0)
            self._fit = (fkey, fit_size(lab, self.size, avail, True, 10) if lab else self.size)
        fs = int(self._fit[1] * sc)
        if has_icon:
            ic = self.icon if self.enabled else "lock"
            tw = text_size(lab, fs, True, raw=True)[0] if lab else 0
            total = tw + (fs + 10 if lab else 0)
            ix = r.centerx - total // 2 + fs // 2 if lab else r.centerx
            draw_icon(surf, ic, (ix, r.centery), fs + 2, acc if self.enabled else C["text_mute"])
            if lab:
                draw_text(surf, lab, (ix + fs // 2 + 10, r.centery - (6 if self.sublabel else 0)), fs, col, bold=True,
                          anchor="midleft", raw=True)
        elif lab:
            draw_text(surf, lab, (r.centerx, r.centery - (8 if self.sublabel else 0)), fs, col, bold=True,
                      anchor="center", raw=True)
        if self.sublabel:
            draw_text(surf, self.sublabel, (r.centerx, r.centery + 13), max(11, fs - 5),
                      scale_color(acc, 0.95) if self.enabled else C["text_mute"], anchor="center",
                      max_w=self.rect.w - 12)
        if self.badge:
            bx, by = r.right - 6, r.y + 6
            pygame.draw.circle(surf, C["red"], (bx, by), 10)
            draw_text(surf, str(self.badge), (bx, by), 12, C["white"], bold=True, anchor="center", shadow=False)


class Slider(Widget):
    def __init__(self, rect, value=0.5, on_change=None, accent=None, label="", fmt=None, steps=0):
        super().__init__(rect)
        self.value = value
        self.on_change = on_change
        self.accent = accent or C["orange"]
        self.label = label
        self.fmt = fmt or (lambda v: i18n.pct(v * 100))
        self.steps = steps
        self.drag = False
        self.knob = Spring(1.0, 200, 18)

    def _set_from_x(self, x):
        v = clamp((x - self.rect.x) / max(1, self.rect.w), 0.0, 1.0)
        if self.steps:
            v = round(v * self.steps) / self.steps
        if v != self.value:
            if int(v * 20) != int(self.value * 20):
                UI.sound("tick")
            self.value = v
            if self.on_change:
                self.on_change(v)

    def handle(self, e):
        hit = self.rect.inflate(20, 30)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and hit.collidepoint(e.pos):
            self.drag = True
            self._set_from_x(e.pos[0])
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.drag:
            self.drag = False
            return True
        if e.type == pygame.MOUSEMOTION and self.drag:
            self._set_from_x(e.pos[0])
            return True
        if e.type == pygame.MOUSEWHEEL and hit.collidepoint(UI.mouse):
            self.value = clamp(self.value + e.y * 0.05, 0, 1)
            if self.on_change:
                self.on_change(self.value)
            return True
        return False

    def update(self, dt):
        self.knob.target = 1.35 if self.drag or self.rect.inflate(20, 30).collidepoint(UI.mouse) else 1.0
        self.knob.update(dt)

    def draw(self, surf):
        r = self.rect
        tr = pygame.Rect(r.x, r.centery - 5, r.w, 10)
        pygame.draw.rect(surf, (10, 16, 34), tr, border_radius=5)
        f = tr.copy()
        f.w = int(tr.w * self.value)
        if f.w > 0:
            pygame.draw.rect(surf, self.accent, f, border_radius=5)
        pygame.draw.rect(surf, scale_color(self.accent, 0.6), tr, 1, border_radius=5)
        kx = r.x + r.w * self.value
        draw_glow(surf, (kx, r.centery), 26 * self.knob.value, self.accent, 0.8)
        pygame.draw.circle(surf, C["white"], (int(kx), r.centery), int(10 * self.knob.value))
        pygame.draw.circle(surf, self.accent, (int(kx), r.centery), int(10 * self.knob.value), 3)
        if self.label:
            draw_text(surf, self.label, (r.x, r.y - 14), 15, C["text_dim"], bold=True)
        draw_text(surf, self.fmt(self.value), (r.right, r.y - 14), 16, C["text"], bold=True, anchor="topright")


class Toggle(Widget):
    def __init__(self, rect, value=True, on_change=None, label="", accent=None):
        super().__init__(rect)
        self.value = value
        self.on_change = on_change
        self.label = label
        self.accent = accent or C["green"]
        self.k = Spring(1.0 if value else 0.0, 220, 20)

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.value = not self.value
            UI.sound("click")
            if self.on_change:
                self.on_change(self.value)
            return True
        return False

    def update(self, dt):
        self.k.target = 1.0 if self.value else 0.0
        self.k.update(dt)

    def draw(self, surf):
        r = pygame.Rect(self.rect.right - 64, self.rect.centery - 15, 60, 30)
        col = lerp_color((60, 70, 90), self.accent, self.k.value)
        pygame.draw.rect(surf, scale_color(col, 0.4), r, border_radius=15)
        pygame.draw.rect(surf, col, r, 2, border_radius=15)
        kx = r.x + 15 + 30 * self.k.value
        draw_glow(surf, (kx, r.centery), 22, col, 0.6 * self.k.value + 0.2)
        pygame.draw.circle(surf, C["white"], (int(kx), r.centery), 11)
        draw_text(surf, self.label, (self.rect.x, self.rect.centery), 18, C["text"], anchor="midleft")


class Tabs(Widget):
    def __init__(self, rect, labels, on_change=None, accent=None, index=0, icons=None):
        super().__init__(rect)
        self.labels = labels
        self.on_change = on_change
        self.accent = accent or C["cyan"]
        self.index = index
        self.icons = icons or [None] * len(labels)
        self.buttons = []
        self._build()
        self.under = Spring(0.0, 220, 22)

    def _build(self):
        n = len(self.labels)
        w = self.rect.w / n
        self.buttons = []
        for i, lab in enumerate(self.labels):
            b = Button((self.rect.x + i * w + 3, self.rect.y, w - 6, self.rect.h), lab,
                       on_click=(lambda j=i: self.select(j)), accent=self.accent, size=16,
                       style="tab", icon=self.icons[i])
            b.selected = (i == self.index)
            self.buttons.append(b)

    def select(self, i):
        self.index = i
        for j, b in enumerate(self.buttons):
            b.selected = (j == i)
        if self.on_change:
            self.on_change(i)

    def handle(self, e):
        return any(b.handle(e) for b in self.buttons)

    def update(self, dt):
        for b in self.buttons:
            b.update(dt)
        self.under.target = self.index
        self.under.update(dt)

    def draw(self, surf):
        for b in self.buttons:
            b.draw(surf)
        w = self.rect.w / len(self.labels)
        x = self.rect.x + self.under.value * w
        pygame.draw.line(surf, self.accent, (x + 14, self.rect.bottom + 4), (x + w - 14, self.rect.bottom + 4), 3)
        draw_glow(surf, (x + w / 2, self.rect.bottom + 4), 30, self.accent, 0.6)


class TextInput(Widget):
    def __init__(self, rect, text="", placeholder="", max_len=28, on_submit=None, accent=None, size=34):
        super().__init__(rect)
        self.text = text
        self.placeholder = placeholder
        self.max_len = max_len
        self.on_submit = on_submit
        self.accent = accent or C["cyan"]
        self.size = size
        self.active = True
        self.t = 0.0
        self.shake = 0.0

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.active = self.rect.collidepoint(e.pos)
            return self.active
        if not self.active:
            return False
        if e.type == pygame.TEXTINPUT:
            if len(self.text) < self.max_len:
                self.text += e.text
                UI.sound("type")
            else:
                self.shake = 0.3
            return True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                UI.sound("type")
                return True
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.on_submit:
                    self.on_submit(self.text)
                return True
        return False

    def update(self, dt):
        self.t += dt
        self.shake = max(0.0, self.shake - dt)

    def draw(self, surf):
        r = self.rect.move(int(math.sin(self.t * 60) * 6 * self.shake), 0)
        glass_panel(surf, r, self.accent, 200, 14, glow=True, strong=self.active)
        if self.text:
            trc = draw_text(surf, self.text, (r.x + 24, r.centery), self.size, C["text"], bold=True,
                            anchor="midleft", glow=self.accent, raw=True, max_w=r.w - 48)
            cx = trc.right + 4
        else:
            draw_text(surf, self.placeholder, (r.x + 24, r.centery), self.size, C["text_mute"], anchor="midleft")
            cx = r.x + 24
        if self.active and int(self.t * 2) % 2 == 0:
            pygame.draw.line(surf, self.accent, (cx, r.centery - self.size // 2), (cx, r.centery + self.size // 2), 3)


class ScrollArea(Widget):
    """İçeriği callback ile çizilen kaydırılabilir alan."""

    def __init__(self, rect, draw_fn, content_h_fn, accent=None):
        super().__init__(rect)
        self.draw_fn = draw_fn
        self.content_h_fn = content_h_fn
        self.scroll = 0.0
        self.target = 0.0
        self.accent = accent or C["cyan"]

    def max_scroll(self):
        return max(0, self.content_h_fn() - self.rect.h)

    def handle(self, e):
        if e.type == pygame.MOUSEWHEEL and self.rect.collidepoint(UI.mouse):
            self.target = clamp(self.target - e.y * 60, 0, self.max_scroll())
            return True
        return False

    def update(self, dt):
        self.target = clamp(self.target, 0, self.max_scroll())
        self.scroll = lerp(self.scroll, self.target, min(1.0, dt * 14))

    def draw(self, surf):
        old = surf.get_clip()
        surf.set_clip(self.rect)
        self.draw_fn(surf, self.rect.x, self.rect.y - int(self.scroll))
        surf.set_clip(old)
        ms = self.max_scroll()
        if ms > 0:
            th = max(30, self.rect.h * self.rect.h / (self.rect.h + ms))
            ty = self.rect.y + (self.rect.h - th) * (self.scroll / ms)
            pygame.draw.rect(surf, scale_color(self.accent, 0.5), (self.rect.right - 5, ty, 4, th), border_radius=2)


# ===========================================================================
# BİLDİRİMLER (toast)
# ===========================================================================
class Toasts:
    def __init__(self):
        self.items = []

    def push(self, text, color=None, icon="check", dur=4.0):
        from . import settings as _SET
        dur *= float(_SET.get("toast_k"))                   # AYARLAR > OYUN: bildirim süresi
        text = tr(str(text))
        self.items.append({"text": text, "color": color or C["cyan"], "icon": icon, "t": 0.0, "dur": dur,
                           "y": Spring(0.0, 160, 20)})
        if len(self.items) > 6:
            self.items.pop(0)

    def update(self, dt):
        for it in self.items:
            it["t"] += dt
        self.items = [it for it in self.items if it["t"] < it["dur"]]
        for i, it in enumerate(reversed(self.items)):
            it["y"].target = i * 66
            it["y"].update(dt)

    def draw(self, surf):
        for it in self.items:
            t, d = it["t"], it["dur"]
            k_in = ease_out_cubic(min(1.0, t / 0.35))
            k_out = 1.0 if t < d - 0.4 else max(0.0, (d - t) / 0.4)
            w = min(640, 90 + text_size(it["text"], 17, True, raw=True)[0])
            x = W - 20 - w + int((1 - k_in) * (w + 40))
            y = 80 + it["y"].value
            r = pygame.Rect(x, y, w, 54)
            glass_panel(surf, r, it["color"], 215, 14, glow=True, offset_alpha=int(255 * k_out))
            draw_icon(surf, it["icon"], (r.x + 30, r.centery), 20, it["color"])
            draw_text(surf, it["text"], (r.x + 56, r.centery), 17, C["text"], bold=True, anchor="midleft",
                      alpha=int(255 * k_out), raw=True, max_w=r.w - 70)
            pw = int((r.w - 28) * (1 - t / d))
            pygame.draw.line(surf, it["color"], (r.x + 14, r.bottom - 6), (r.x + 14 + pw, r.bottom - 6), 2)


def draw_tooltip(surf):
    if not UI.tooltip:
        return
    from . import settings
    if not settings.get("tooltips"):
        return
    lines = wrap_text(UI.tooltip, 15, 360)
    w = max(text_size(l, 15, raw=True)[0] for l in lines) + 28
    h = len(lines) * 20 + 18
    mx, my = UI.mouse
    x = mx + 18
    y = my + 20
    if x + w > W - 8:
        x = mx - w - 12
    if y + h > H - 8:
        y = my - h - 12
    r = pygame.Rect(x, y, w, h)
    glass_panel(surf, r, UI.tooltip_color, 235, 10, glow=False)
    for i, l in enumerate(lines):
        draw_text(surf, l, (r.x + 14, r.y + 9 + i * 20), 15, C["text"], raw=True)


def draw_cursor(surf, color=C["cyan"]):
    from . import settings
    if not settings.get("custom_cursor"):
        return
    mx, my = UI.mouse
    t = UI.time
    draw_glow(surf, (mx, my), 18, color, 0.6)
    pygame.draw.circle(surf, color, (mx, my), 7 + int(math.sin(t * 6) * 1.5), 1)
    pygame.draw.circle(surf, C["white"], (mx, my), 2)


# ===========================================================================
# KÜÇÜK ÇİZİM YARDIMCILARI
# ===========================================================================
def chip(surf, pos, text, color, size=14, anchor="topleft", icon=None):
    text = tr(str(text))
    tw, th = text_size(text, size, True, raw=True)
    w = tw + 22 + (18 if icon else 0)
    r = pygame.Rect(0, 0, w, th + 8)
    setattr(r, anchor, pos)
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, 46), s.get_rect(), border_radius=r.h // 2)
    pygame.draw.rect(s, (*color, 190), s.get_rect(), 1, border_radius=r.h // 2)
    surf.blit(s, r)
    x = r.x + 11
    if icon:
        draw_icon(surf, icon, (x + 6, r.centery), size, color)
        x += 18
    draw_text(surf, text, (x, r.centery), size, color, bold=True, anchor="midleft", shadow=False, raw=True)
    return r


def stat_line(surf, x, y, w, label, value, color=C["text"], size=16, icon=None, icon_color=None):
    if icon:
        draw_icon(surf, icon, (x + 8, y + size // 2 + 1), size, icon_color or color)
        x += 24
        w -= 24
    draw_text(surf, label, (x, y), size, C["text_dim"])
    draw_text(surf, value, (x + w, y), size, color, bold=True, anchor="topright")
    return y + size + 10


def radial_progress(surf, center, radius, frac, color, width=6, bg=(20, 30, 60)):
    x, y = center
    pygame.draw.circle(surf, bg, (int(x), int(y)), radius, width)
    if frac <= 0:
        return
    steps = max(2, int(60 * frac))
    pts = []
    for i in range(steps + 1):
        a = -math.pi / 2 + math.tau * frac * i / steps
        pts.append((x + math.cos(a) * radius, y + math.sin(a) * radius))
    if len(pts) > 1:
        pygame.draw.lines(surf, color, False, pts, width)
    draw_glow(surf, pts[-1], width * 3, color, 0.9)


def soft_shadow(surf, rect, radius=24, alpha=120):
    rect = pygame.Rect(rect)
    sh = soft_circle(max(rect.w, rect.h) // 2 + radius, (0, 0, 0), alpha)
    sh = pygame.transform.smoothscale(sh, (rect.w + radius * 2, rect.h + radius * 2))
    surf.blit(sh, (rect.x - radius, rect.y - radius + 8))

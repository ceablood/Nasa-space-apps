# -*- coding: utf-8 -*-
"""
AETHER-X // NPC'LER (personel ve kolonistler)
Her NPC'nin kalıcı bir kimliği vardır (tohumla üretilir, her açılışta aynıdır):
  ad, kişilik özelliği (hız, çalışma süresi, mola sıklığı), boy, ten ve saç rengi, kıyafet aksanı, kask tipi, aksesuar.
Kıyafet yere göre değişir:
  üs (Dünya)  : araştırmacı laboratuvar önlüğü, teknisyen tulum + baret, astronot tam kıyafet + kask
  Ay          : beyaz EVA kıyafeti, altın yaldızlı vizör
  Mars        : pas/toprak tonlu keşif kıyafeti, tozlu çizmeler
  Venüs       : gümüş ısı yansıtıcı kıyafet
  Jüpiter     : istasyon üniforması — lacivert + altın şeritler, şeffaf hafif kask (yüz görünür), ışıklı rozet
İş pozları: walk, idle, dig (kazma), type (konsol), scan (tablet), carry (sandık), weld (kaynak kıvılcımı),
repair (anahtar), water (sulama), lift (spor), talk, rest. Çizimler eski oyunun yuvarlak, renkli çizgi tarzındadır.
"""
import math
import random

import pygame

from .config import C, CREW_COLORS
from .fx import draw_glow, scale_color

FIRST = ["Ada", "Deniz", "Elif", "Kaan", "Mira", "Arda", "Lina", "Emre", "Zeynep", "Can", "Nova", "Leo", "Maya", "Ayla",
         "Sami", "Iris", "Tuna", "Yuki", "Omar", "Nadia", "Ravi", "Sofia", "Ilya", "Amara", "Kenji", "Lucas", "Ece", "Bora"]
LAST = ["Yıldız", "Kaya", "Demir", "Aksoy", "Okyay", "Tan", "Rivera", "Sato", "Novak", "Mehta", "Costa", "Ivanova",
        "Okafor", "Lindqvist", "Arslan", "Güneş", "Ay", "Kuzey"]
# özellik: (ad, hız çarpanı, iş süresi çarpanı, mola olasılığı)
TRAITS = [("Çalışkan", 1.0, 1.5, 0.05), ("Meraklı", 1.1, 0.9, 0.15), ("Sakin", 0.85, 1.2, 0.1), ("Neşeli", 1.1, 1.0, 0.2),
          ("Titiz", 0.9, 1.4, 0.05), ("Uykucu", 0.75, 0.8, 0.3), ("Sosyal", 1.0, 0.9, 0.35), ("Cesur", 1.2, 1.1, 0.08)]
SKIN = [(246, 214, 186), (228, 184, 150), (198, 146, 106), (160, 110, 76), (112, 76, 52), (240, 200, 170)]
HAIR = [(40, 30, 24), (90, 60, 34), (180, 130, 70), (230, 200, 120), (20, 20, 24), (150, 60, 40), (220, 220, 225)]

OUTFIT = {
    "base":    {"suit": (236, 238, 244), "trim": None, "helmet": "dome", "visor": ((40, 80, 160), (120, 190, 255))},
    "moon":    {"suit": (240, 242, 246), "trim": (200, 60, 60), "helmet": "dome", "visor": ((150, 110, 30), (255, 214, 120))},
    "mars":    {"suit": (214, 150, 104), "trim": (90, 60, 44), "helmet": "dome", "visor": ((60, 40, 30), (230, 150, 90)), "dust": True},
    "venus":   {"suit": (200, 206, 214), "trim": (255, 190, 90), "helmet": "dome", "visor": ((120, 90, 30), (255, 230, 150)),
                "shine": True},
    "jupiter": {"suit": (34, 46, 96), "trim": (236, 190, 80), "helmet": "bubble", "visor": ((120, 200, 255), (220, 240, 255)),
                "badge": True},
}
ROLE_WORK = {"miner": "dig", "engineer": "repair", "scientist": "scan", "doctor": "scan", "pilot": "type"}


class Persona:
    """Kalıcı NPC kimliği."""

    def __init__(self, seed, role=None):
        rng = random.Random(seed)
        self.seed = seed
        self.name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        tr_ = rng.choice(TRAITS)
        self.trait, self.speed_k, self.work_k, self.break_p = tr_
        self.role = role or rng.choice(list(CREW_COLORS))
        self.col = CREW_COLORS.get(self.role, (200, 200, 210))
        self.skin = rng.choice(SKIN)
        self.hair = rng.choice(HAIR)
        self.height = rng.uniform(0.92, 1.08)
        self.accessory = rng.choice(("none", "antenna", "lamp", "belt", "patch"))
        self.stripe = rng.random() < 0.5
        self.phase = rng.uniform(0, 9)

    def describe(self):
        return f"{self.name} · {self.trait}"


# =============================================================================== çizim
def draw_person(surf, x, y, scale, p, place="base", pose="idle", t=0.0, facing=1, kind="astro", tool=None):
    """(x, y): ayak hizası (zemin). kind: astro (kıyafet + kask) · coat (laboratuvar önlüğü) · tech (tulum + baret) ·
    station (Jüpiter istasyon üniforması)."""
    s = scale * p.height
    o = OUTFIT.get(place, OUTFIT["base"])
    if kind == "astro" and place == "jupiter":
        kind = "station"
    ph = t * 1.0 + p.phase
    # vücut renkleri
    if kind == "coat":
        suit, trim = (244, 246, 250), p.col
    elif kind == "tech":
        suit, trim = scale_color(p.col, 0.9), (250, 210, 60)
    elif kind == "station":
        suit, trim = o["suit"], o["trim"]
    else:
        suit, trim = o["suit"], (o["trim"] or p.col)
    dark = scale_color(suit, 0.62)
    # poz açıları
    leg = arm_l = arm_r = 0.0
    bob = 0.0
    lean = 0.0
    if pose == "walk" or pose == "carry":
        leg = math.sin(ph * 8) * 0.45
        arm_l, arm_r = -leg * 0.8, leg * 0.8
        bob = abs(math.sin(ph * 8)) * 1.5 * s
    elif pose == "dig":
        sw = (math.sin(ph * 4) + 1) / 2
        arm_l = arm_r = -2.4 + sw * 2.0
        lean = sw * 0.15
    elif pose in ("type", "scan"):
        arm_l = arm_r = -1.2 + math.sin(ph * 10) * 0.06
    elif pose in ("weld", "repair"):
        arm_r = -1.0 + math.sin(ph * 6) * 0.35
        arm_l = -0.6
        lean = 0.12
    elif pose == "water":
        arm_r = -1.3
        lean = 0.1
    elif pose == "lift":
        k = (math.sin(ph * 3) + 1) / 2
        arm_l = arm_r = -3.0 * k
        bob = -k * 2 * s
    elif pose == "talk":
        arm_r = -0.6 + math.sin(ph * 3) * 0.4
    if pose == "carry":
        arm_l = arm_r = -1.4
    if pose == "rest":
        leg = 0.0
    y = y - bob
    hip = y - 14 * s
    sh = y - 30 * s
    bw = 7.5 * s
    lw = max(2, int(4.2 * s))
    # gölge
    sh_s = pygame.Surface((int(26 * s) + 2, int(7 * s) + 2), pygame.SRCALPHA)
    pygame.draw.ellipse(sh_s, (0, 0, 0, 70), sh_s.get_rect())
    surf.blit(sh_s, (x - 13 * s, y + bob - 3 * s))
    # bacaklar + çizmeler
    for sgn, a in ((-1, leg), (1, -leg)):
        hx = x + sgn * 3.2 * s
        fx, fy = hx + math.sin(a) * 13 * s, hip + math.cos(a) * 13 * s
        pygame.draw.line(surf, dark, (hx, hip), (fx, fy), lw + 1)
        pygame.draw.line(surf, suit, (hx, hip), (fx, fy), lw)
        boot = (80, 70, 64) if kind in ("coat", "tech") else ((150, 96, 70) if o.get("dust") else scale_color(suit, 0.45))
        pygame.draw.ellipse(surf, boot, (fx - 3.5 * s + facing * 1.5 * s, fy - 2 * s, 7.5 * s, 4.5 * s))
    # sırt çantası (EVA)
    if kind == "astro":
        pygame.draw.rect(surf, scale_color(suit, 0.75), (x - facing * 9 * s - 4 * s, sh - 1 * s, 8 * s, 15 * s), border_radius=int(2 * s) + 1)
        pygame.draw.circle(surf, (120, 230, 140) if int(t * 2 + p.phase) % 2 else (40, 90, 60),
                           (int(x - facing * 9 * s), int(sh + 2 * s)), max(1, int(1.2 * s)))
    # gövde
    tx = x + facing * lean * 6 * s
    body = pygame.Rect(0, 0, int(bw * 2), int(18 * s))
    body.midbottom = (int(tx), int(hip + 2 * s))
    if kind == "coat":                                     # önlük: aşağı genişleyen etek
        pygame.draw.polygon(surf, (220, 224, 232), [(tx - bw, sh), (tx + bw, sh), (tx + bw + 2 * s, hip + 5 * s), (tx - bw - 2 * s, hip + 5 * s)])
        pygame.draw.polygon(surf, suit, [(tx - bw + 1, sh + 1), (tx + bw - 1, sh + 1), (tx + bw + 1 * s, hip + 4 * s), (tx - bw - 1 * s, hip + 4 * s)])
        pygame.draw.line(surf, trim, (tx, sh + 2 * s), (tx, hip), max(1, int(1.5 * s)))       # gömlek (rol rengi)
        pygame.draw.rect(surf, (120, 150, 200), (tx + 2 * s, sh + 5 * s, 3 * s, 4 * s))       # cep kartı
    else:
        pygame.draw.rect(surf, dark, body.inflate(2, 2), border_radius=int(4 * s) + 1)
        pygame.draw.rect(surf, suit, body, border_radius=int(4 * s) + 1)
        if kind == "station":
            pygame.draw.line(surf, trim, (tx - bw + 1, sh + 3 * s), (tx + bw - 1, sh + 3 * s), max(1, int(1.6 * s)))
            pygame.draw.line(surf, trim, (tx, sh + 3 * s), (tx, hip), max(1, int(1.2 * s)))
            draw_glow(surf, (int(tx + 4 * s), int(sh + 7 * s)), max(3, int(4 * s)), (120, 220, 255), 0.6)
            pygame.draw.circle(surf, (140, 230, 255), (int(tx + 4 * s), int(sh + 7 * s)), max(1, int(1.5 * s)))
        elif kind == "tech":
            pygame.draw.line(surf, trim, (tx - bw + 1, sh + 9 * s), (tx + bw - 1, sh + 9 * s), max(1, int(2 * s)))     # yansıtıcı şerit
            pygame.draw.rect(surf, (70, 60, 50), (tx - bw, hip - 3 * s, bw * 2, 2.5 * s))                          # alet kemeri
        else:
            pygame.draw.rect(surf, (226, 232, 242), (tx - 4 * s, sh + 4 * s, 8 * s, 5 * s), border_radius=1)       # göğüs paneli
            for i, cc in enumerate(((255, 90, 90), (90, 220, 120), (90, 170, 255))):
                pygame.draw.circle(surf, cc, (int(tx - 2.5 * s + i * 2.5 * s), int(sh + 6.5 * s)), max(1, int(0.8 * s)))
            pygame.draw.line(surf, trim, (tx - bw + 1, hip - 5 * s), (tx + bw - 1, hip - 5 * s), max(1, int(1.6 * s)))
            if p.stripe:
                pygame.draw.line(surf, p.col, (tx - bw + 1, sh + 12 * s), (tx + bw - 1, sh + 12 * s), max(1, int(1.2 * s)))
            if o.get("dust"):
                for i in range(3):
                    pygame.draw.circle(surf, (170, 110, 70), (int(tx - 4 * s + i * 4 * s), int(hip - 1 * s)), max(1, int(1.1 * s)))
            if o.get("shine"):
                pygame.draw.line(surf, (255, 255, 255), (tx - bw + 2, sh + 2 * s), (tx - bw + 2, hip - 3 * s), 1)
    # kollar + eldivenler
    glove = (90, 90, 100) if kind in ("astro", "station") else p.skin
    for sgn, a in ((-facing, arm_l), (facing, arm_r)):          # çalışan (sağ) kol bakış yönündeki tarafta
        ax = tx + sgn * (bw + 0.5 * s)
        ay = sh + 2 * s
        ex, ey = ax + math.sin(a) * 11 * s * (sgn if pose == "walk" else -facing), ay + math.cos(a) * 11 * s
        pygame.draw.line(surf, scale_color(suit, 0.8), (ax, ay), (ex, ey), max(2, int(3.6 * s)))
        pygame.draw.circle(surf, glove, (int(ex), int(ey)), max(1, int(2.2 * s)))
    hx_r = tx + facing * (bw + 0.5 * s) + math.sin(arm_r) * 11 * s * (facing if pose == "walk" else -facing)
    hy_r = sh + 2 * s + math.cos(arm_r) * 11 * s
    # alet / taşınan
    _tool(surf, pose, tool, hx_r, hy_r, s, facing, t, p)
    # baş
    hy = sh - 7.5 * s
    hr = 7.0 * s
    hx = tx + facing * lean * 4 * s
    if kind in ("astro", "station"):
        if o["helmet"] == "bubble" or kind == "station":
            pygame.draw.circle(surf, p.skin, (int(hx), int(hy + 0.5 * s)), int(hr * 0.72))                   # yüz
            pygame.draw.arc(surf, p.hair, (hx - hr * 0.72, hy - hr * 0.72, hr * 1.44, hr * 1.2), 0.3, 2.85, max(2, int(2.6 * s)))
            pygame.draw.circle(surf, (30, 30, 40), (int(hx + facing * 2.2 * s), int(hy)), max(1, int(0.8 * s)))
            bub = pygame.Surface((int(hr * 2.6) + 2, int(hr * 2.6) + 2), pygame.SRCALPHA)
            c0 = bub.get_width() // 2
            pygame.draw.circle(bub, (*o["visor"][1], 60), (c0, c0), int(hr * 1.25))
            pygame.draw.circle(bub, (*o["visor"][1], 200), (c0, c0), int(hr * 1.25), max(1, int(1.0 * s)))
            pygame.draw.arc(bub, (255, 255, 255, 220), (c0 - hr * 0.9, c0 - hr * 0.95, hr * 1.2, hr * 1.2), 1.6, 2.7, max(1, int(1.4 * s)))
            surf.blit(bub, (hx - c0, hy - c0))
            pygame.draw.line(surf, trim, (hx - hr * 1.05, hy + hr * 0.95), (hx + hr * 1.05, hy + hr * 0.95), max(2, int(2 * s)))  # yaka halkası
        else:
            pygame.draw.circle(surf, scale_color(suit, 0.7), (int(hx), int(hy)), int(hr + 1.2 * s))                # kask kenarı
            pygame.draw.circle(surf, (246, 248, 252), (int(hx), int(hy)), int(hr))
            vis = pygame.Rect(0, 0, int(hr * 1.5), int(hr * 1.05))
            vis.center = (int(hx + facing * 1.4 * s), int(hy + 0.4 * s))
            vc, vl = o["visor"]
            pygame.draw.ellipse(surf, vc, vis)
            pygame.draw.ellipse(surf, scale_color(vl, 0.8), vis.inflate(-int(2 * s), -int(3 * s)).move(-int(facing * s), int(s)), max(1, int(1 * s)))
            pygame.draw.ellipse(surf, vl, (vis.x + vis.w * 0.18, vis.y + vis.h * 0.15, vis.w * 0.32, vis.h * 0.28))     # yansıma
            pygame.draw.rect(surf, trim, (hx - hr * 0.9, hy + hr * 0.78, hr * 1.8, 2.2 * s), border_radius=1)          # boyun halkası
            if p.accessory == "antenna":
                pygame.draw.line(surf, (190, 190, 200), (hx - facing * hr * 0.6, hy - hr * 0.6), (hx - facing * hr * 0.9, hy - hr * 1.7), 1)
                pygame.draw.circle(surf, (255, 80, 80), (int(hx - facing * hr * 0.9), int(hy - hr * 1.7)), max(1, int(1.2 * s)))
            elif p.accessory == "lamp":
                draw_glow(surf, (int(hx + facing * hr * 0.2), int(hy - hr * 0.85)), max(3, int(5 * s)), (255, 240, 200), 0.7)
                pygame.draw.circle(surf, (255, 250, 220), (int(hx + facing * hr * 0.2), int(hy - hr * 0.85)), max(1, int(1.4 * s)))
    else:
        pygame.draw.circle(surf, p.skin, (int(hx), int(hy)), int(hr * 0.9))
        pygame.draw.circle(surf, (30, 30, 40), (int(hx + facing * 2.4 * s), int(hy - 0.4 * s)), max(1, int(0.8 * s)))
        if kind == "tech":                                        # baret
            pygame.draw.ellipse(surf, (250, 200, 50), (hx - hr * 1.05, hy - hr * 1.05, hr * 2.1, hr * 1.1))
            pygame.draw.line(surf, (220, 170, 30), (hx - hr * 1.2, hy - hr * 0.35), (hx + hr * 1.2, hy - hr * 0.35), max(1, int(1.6 * s)))
        else:                                                     # saç + koruyucu gözlük (araştırmacı)
            pygame.draw.arc(surf, p.hair, (hx - hr * 0.95, hy - hr * 0.95, hr * 1.9, hr * 1.6), 0.25, 2.9, max(2, int(3 * s)))
            pygame.draw.line(surf, (120, 200, 255), (hx - hr * 0.2, hy - hr * 0.3), (hx + facing * hr * 0.85, hy - hr * 0.3), max(1, int(1.3 * s)))


def _tool(surf, pose, tool, hx, hy, s, facing, t, p):
    if pose == "dig":                                             # kazma
        a = -0.6 + math.sin(t * 4 + p.phase) * 0.8
        ex, ey = hx + math.cos(a) * 14 * s * facing, hy + math.sin(a) * 14 * s
        pygame.draw.line(surf, (130, 90, 50), (hx, hy), (ex, ey), max(1, int(1.8 * s)))
        pygame.draw.line(surf, (170, 176, 186), (ex - 5 * s, ey - 3 * s), (ex + 5 * s, ey + 3 * s), max(2, int(2.4 * s)))
    elif pose == "scan":                                          # tablet + holo
        r = pygame.Rect(0, 0, int(9 * s), int(6 * s))
        r.center = (int(hx + facing * 3 * s), int(hy - 2 * s))
        pygame.draw.rect(surf, (30, 40, 60), r, border_radius=1)
        pygame.draw.rect(surf, (90, 220, 255), r.inflate(-2, -2), border_radius=1)
        k = (t * 1.5 + p.phase) % 1.0
        hol = pygame.Surface((int(14 * s) + 2, int(10 * s) + 2), pygame.SRCALPHA)
        pygame.draw.polygon(hol, (110, 230, 255, int(110 * (1 - k))), [(hol.get_width() / 2, hol.get_height()), (0, 0), (hol.get_width(), 0)])
        surf.blit(hol, (r.centerx - hol.get_width() / 2, r.top - hol.get_height()))
    elif pose == "type":                                          # konsol (önünde)
        cx = hx + facing * 7 * s
        pygame.draw.rect(surf, (40, 52, 76), (cx - 7 * s, hy + 1 * s, 14 * s, 10 * s), border_radius=2)
        pygame.draw.rect(surf, (80, 200, 255) if int(t * 3 + p.phase) % 3 else (120, 255, 170), (cx - 5 * s, hy + 2.5 * s, 10 * s, 5 * s))
    elif pose in ("repair", "weld"):                               # anahtar / kaynak + kıvılcım
        pygame.draw.line(surf, (190, 196, 206), (hx, hy), (hx + facing * 7 * s, hy - 3 * s), max(2, int(2.2 * s)))
        if pose == "weld" or int(t * 5 + p.phase) % 4 == 0:
            rng = random.Random(int(t * 20) + p.seed)
            for _ in range(5):
                a = rng.uniform(0, math.tau)
                d = rng.uniform(2, 7) * s
                pygame.draw.line(surf, (255, 220, 120), (hx + facing * 7 * s, hy - 3 * s),
                                 (hx + facing * 7 * s + math.cos(a) * d, hy - 3 * s + math.sin(a) * d), 1)
            draw_glow(surf, (int(hx + facing * 7 * s), int(hy - 3 * s)), max(3, int(6 * s)), (255, 220, 150), 0.6)
    elif pose == "water":                                         # sulama kabı + damlalar
        pygame.draw.rect(surf, (90, 170, 120), (hx - 3 * s, hy - 3 * s, 7 * s, 6 * s), border_radius=1)
        for i in range(3):
            k = (t * 2 + i / 3 + p.phase) % 1.0
            pygame.draw.circle(surf, (120, 200, 255), (int(hx + facing * (6 + k * 4) * s), int(hy + k * 10 * s)), max(1, int(0.9 * s)))
    elif pose == "carry":                                         # sandık
        pygame.draw.rect(surf, (168, 120, 72), (hx - 8 * s, hy - 9 * s, 13 * s, 10 * s), border_radius=1)
        pygame.draw.line(surf, (120, 84, 50), (hx - 8 * s, hy - 4 * s), (hx + 5 * s, hy - 4 * s), 1)
    elif pose == "lift":                                          # dambıl
        pygame.draw.line(surf, (150, 150, 160), (hx - 8 * s, hy), (hx + 8 * s, hy), max(1, int(1.6 * s)))
        for dx in (-8, 8):
            pygame.draw.rect(surf, (60, 60, 70), (hx + dx * s - 1.5 * s, hy - 3 * s, 3 * s, 6 * s))


# =============================================================================== bina içi sahneleri
INTERIOR = {
    # bina -> (arka duvar rengi, [(iş pozu, kıyafet, sahne nesnesi)])
    "research": ((24, 40, 70), [("scan", "coat", "bench"), ("type", "coat", "screen"), ("scan", "coat", "telescope"), ("talk", "coat", None)]),
    "hangar": ((40, 40, 48), [("weld", "tech", "rocket"), ("repair", "tech", "rocket"), ("carry", "tech", None), ("type", "tech", "screen")]),
    "pads": ((30, 34, 44), [("repair", "tech", "rocket"), ("weld", "tech", "rocket"), ("type", "tech", "screen")]),
    "astro": ((26, 32, 56), [("lift", "astro", None), ("rest", "astro", "bunk"), ("talk", "astro", None), ("scan", "astro", None)]),
    "medical": ((220, 230, 236), [("scan", "coat", "bed"), ("type", "coat", "screen"), ("rest", "astro", "bed")]),
    "rec": ((60, 40, 70), [("talk", "astro", None), ("lift", "astro", None), ("rest", "astro", "bunk")]),
    "depot": ((54, 46, 36), [("carry", "tech", "crates"), ("carry", "tech", "crates"), ("scan", "tech", "crates")]),
    "fuel": ((40, 44, 40), [("repair", "tech", "tank"), ("type", "tech", "screen"), ("scan", "tech", "tank")]),
    "board": ((30, 36, 60), [("talk", "coat", "board"), ("scan", "coat", None), ("type", "coat", "screen")]),
    "nova": ((14, 24, 48), [("type", "coat", "core"), ("scan", "coat", "core"), ("type", "tech", "screen")]),
    "control": ((14, 20, 36), [("type", "coat", "screen"), ("type", "coat", "screen"), ("talk", "coat", "bigscreen"), ("type", "tech", "screen")]),
    "comms": ((20, 26, 44), [("repair", "tech", "dish"), ("type", "coat", "screen"), ("scan", "tech", None)]),
}


def _prop(surf, kind, x, y, s, t, col):
    if kind == "bench":
        pygame.draw.rect(surf, (90, 100, 120), (x - 26 * s, y - 14 * s, 52 * s, 4 * s))
        for i, cc in enumerate(((120, 255, 170), (255, 140, 200), (120, 200, 255))):
            pygame.draw.rect(surf, cc, (x - 20 * s + i * 14 * s, y - 24 * s, 6 * s, 10 * s), border_radius=2)
    elif kind in ("screen", "bigscreen"):
        w = 46 if kind == "bigscreen" else 24
        r = pygame.Rect(0, 0, int(w * s), int(16 * s))
        r.midbottom = (int(x), int(y - 26 * s))
        pygame.draw.rect(surf, (20, 28, 44), r.inflate(4, 4), border_radius=3)
        pygame.draw.rect(surf, (40, 120, 180), r, border_radius=2)
        for i in range(4):
            yy = r.y + 3 + i * r.h / 4.5
            pygame.draw.line(surf, (140, 230, 255), (r.x + 3, yy), (r.x + 3 + (r.w - 6) * (0.4 + 0.5 * abs(math.sin(t + i))), yy), 1)
    elif kind == "telescope":
        pygame.draw.line(surf, (150, 156, 170), (x, y), (x + 18 * s, y - 30 * s), max(2, int(5 * s)))
        pygame.draw.line(surf, (90, 96, 110), (x + 4 * s, y), (x - 6 * s, y + 2 * s), 2)
    elif kind == "rocket":
        pygame.draw.rect(surf, (226, 230, 238), (x - 10 * s, y - 70 * s, 20 * s, 66 * s), border_radius=int(6 * s))
        pygame.draw.polygon(surf, col, [(x - 10 * s, y - 68 * s), (x + 10 * s, y - 68 * s), (x, y - 86 * s)])
        for i in range(3):
            pygame.draw.line(surf, (200, 170, 90), (x - 22 * s, y - i * 22 * s), (x + 22 * s, y - i * 22 * s), 1)   # iskele
    elif kind == "bunk":
        pygame.draw.rect(surf, (70, 80, 110), (x - 22 * s, y - 10 * s, 44 * s, 8 * s), border_radius=2)
    elif kind == "bed":
        pygame.draw.rect(surf, (200, 210, 220), (x - 24 * s, y - 12 * s, 48 * s, 8 * s), border_radius=3)
        pygame.draw.line(surf, (255, 90, 90), (x + 24 * s, y - 30 * s), (x + 24 * s, y - 12 * s), 1)
        pygame.draw.rect(surf, (40, 60, 80), (x + 20 * s, y - 40 * s, 12 * s, 10 * s))
        k = (t * 1.2) % 1.0
        pygame.draw.line(surf, (120, 255, 150), (x + 21 * s, y - 35 * s), (x + 21 * s + k * 10 * s, y - 35 * s - (4 * s if 0.4 < k < 0.5 else 0)), 1)
    elif kind == "crates":
        for i in range(4):
            pygame.draw.rect(surf, (168, 120, 72), (x - 30 * s + (i % 2) * 16 * s, y - 14 * s - (i // 2) * 14 * s, 14 * s, 13 * s), border_radius=1)
    elif kind == "tank":
        pygame.draw.ellipse(surf, (200, 206, 214), (x - 18 * s, y - 50 * s, 36 * s, 48 * s))
        pygame.draw.rect(surf, (255, 140, 60), (x - 18 * s, y - 30 * s, 36 * s, 4 * s))
    elif kind == "core":
        draw_glow(surf, (int(x), int(y - 36 * s)), int(26 * s), (80, 220, 255), 0.6 + 0.2 * math.sin(t * 3))
        pygame.draw.circle(surf, (120, 230, 255), (int(x), int(y - 36 * s)), int(10 * s), 2)
    elif kind == "dish":
        pygame.draw.arc(surf, (200, 206, 214), (x - 22 * s, y - 50 * s, 44 * s, 30 * s), 3.3, 6.1, max(2, int(3 * s)))
        pygame.draw.line(surf, (150, 156, 170), (x, y), (x, y - 34 * s), 2)
    elif kind == "board":
        pygame.draw.rect(surf, (230, 234, 240), (x - 24 * s, y - 50 * s, 48 * s, 26 * s), border_radius=2)
        for i in range(3):
            pygame.draw.line(surf, (60, 90, 160), (x - 18 * s, y - 44 * s + i * 7 * s), (x + 10 * s, y - 44 * s + i * 7 * s), 1)


_INT_BG = {}


def draw_interior(surf, rect, key, t, accent, alpha=110, seed=0):
    """Bina paneli arka planı: içeride iş yapan NPC'ler (yarı saydam katman; önündeki yazılar okunur kalır)."""
    r = pygame.Rect(rect)
    wall, slots = INTERIOR.get(key, ((30, 36, 54), [("type", "coat", "screen"), ("talk", "coat", None)]))
    floor = int(r.h * 0.82)
    bg = _INT_BG.get((key, r.size))
    if bg is None:                                                     # duvar + zemin: bir kez çizilir
        bg = pygame.Surface(r.size, pygame.SRCALPHA)
        for yy in range(r.h):
            k = yy / max(1, r.h)
            c = tuple(int(v * (0.55 + 0.45 * (1 - k))) for v in wall)
            pygame.draw.line(bg, c, (0, yy), (r.w, yy))
        pygame.draw.rect(bg, scale_color(wall, 0.5), (0, floor, r.w, r.h - floor))
        for xx in range(0, r.w + 30, 48):                              # zemin karoları
            pygame.draw.line(bg, scale_color(wall, 0.65), (xx, floor), (xx - 30, r.h), 1)
        for i in range(3):                                             # tavan ışıkları
            draw_glow(bg, (int(r.w * (0.2 + 0.3 * i)), 10), 50, (255, 240, 210), 0.25)
        if len(_INT_BG) > 30:
            _INT_BG.clear()
        _INT_BG[(key, r.size)] = bg
    lay = bg.copy()
    n = len(slots)
    s = r.h / 210.0
    for i, (pose, kind, prop) in enumerate(slots):
        x = r.w * (0.14 + 0.72 * i / max(1, n - 1))
        p = Persona(seed * 97 + i * 13 + len(key))
        fac = 1 if i % 2 == 0 else -1
        if prop:
            _prop(lay, prop, x + fac * 22 * s, floor, s * 0.75, t + i, accent)
        draw_person(lay, x, floor, 1.25 * s, p, "base", pose, t + i * 0.7, fac, kind)
    lay.set_alpha(alpha)
    surf.blit(lay, r.topleft)


# =============================================================================== üs personeli
BASE_JOBS = {
    # bina: [(iş pozu, kıyafet, sahne nesnesi)] — binanın önündeki çalışma noktaları
    "research": [("scan", "coat", "telescope"), ("scan", "coat", "bench"), ("type", "coat", "screen")],
    "hangar": [("weld", "tech", None), ("repair", "tech", None)],
    "pads": [("repair", "tech", None), ("type", "tech", None)],
    "fuel": [("repair", "tech", None)],
    "depot": [("carry", "tech", "crates")],
    "astro": [("lift", "astro", None), ("talk", "astro", None)],
    "medical": [("scan", "coat", None)],
    "control": [("type", "coat", None)],
    "comms": [("repair", "tech", None)],
    "nova": [("scan", "coat", None)],
    "board": [("talk", "coat", None)],
    "rec": [("talk", "astro", None)],
}
WALK_Y = 548          # yaya yolu (ana caddenin kenarı)


class Walker:
    """Üs personeli: kendi çalışma noktasında iş yapar, mola verir, başka binaya gider (yaya yolu üzerinden)."""

    def __init__(self, seed, home, slot, spots):
        self.p = Persona(seed)
        self.home, self.slot = home, slot
        self.pose, self.kind, self.prop = BASE_JOBS[home][slot % len(BASE_JOBS[home])]
        self.spots = spots
        self.x, self.y = spots[home][slot % len(spots[home])]
        self.state = "work"
        self.timer = random.Random(seed).uniform(2, 9) * self.p.work_k
        self.path = []
        self.facing = 1
        self.rng = random.Random(seed + 1)
        self.carry = False

    def go(self, key, slot=0):
        tx, ty = self.spots[key][slot % len(self.spots[key])]
        self.path = [(self.x, WALK_Y), (tx, WALK_Y), (tx, ty)]
        self.state = "walk"

    def update(self, dt, night):
        if self.state == "walk":
            if not self.path:
                self.state = "work"
                self.timer = self.rng.uniform(6, 14) * self.p.work_k
                return
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            d = math.hypot(dx, dy)
            spd = 34 * self.p.speed_k
            if d < 2:
                self.path.pop(0)
                return
            if abs(dx) > 0.5:
                self.facing = 1 if dx > 0 else -1
            self.x += dx / d * min(d, spd * dt)
            self.y += dy / d * min(d, spd * dt)
            return
        self.timer -= dt
        if self.timer > 0:
            return
        if self.pose == "carry":                                    # depo <-> hangar sandık taşıma
            self.carry = not self.carry
            self.go("hangar" if self.carry else "depot", self.slot)
            return
        r = self.rng.random()
        if r < self.p.break_p:                                      # mola: başka bir binaya uğra (sohbet / dinlenme)
            dest = self.rng.choice([k for k in self.spots if k != self.home] or [self.home])
            self.go(dest, self.rng.randrange(3))
            self.back = True
        elif getattr(self, "back", False):
            self.back = False
            self.go(self.home, self.slot)
        else:
            self.timer = self.rng.uniform(5, 12) * self.p.work_k

    def current_pose(self):
        if self.state == "walk":
            return "carry" if self.carry else "walk"
        if getattr(self, "back", False):
            return "talk"
        return self.pose

    def draw(self, surf, t, scale):
        draw_person(surf, self.x, self.y, scale, self.p, "base", self.current_pose(), t, self.facing, self.kind)

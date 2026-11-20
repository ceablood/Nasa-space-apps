# -*- coding: utf-8 -*-
"""
GELİŞMİŞ FIRLATMA ÜSSÜ - 12 ALAN
Tepeden harita görünümü: ortada 3 rampa, etrafında binalar, aralarında yollar
ve gidip gelen küçük araçlar. Gece her binanın ışığı yanar. Bir binaya
tıklayınca kamera yumuşakça zoom yapar ve bina paneli kayarak gelir.
"""
import math
import random

import pygame

from . import Scene
from .. import cinema
from .. import archviz
from .. import art
from .. import data as D
from ..config import C, H, TOPBAR_H, W
from ..i18n import tr
from ..fx import (HAS_NUMPY, ParticleSystem, Spring, clamp, draw_glow, ease_out_cubic, lerp, lerp_color,
                  scale_color, soft_circle, vertical_gradient)
from ..ui import (UI, Button, chip, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, radial_progress,
                  render_text, fmt_num, fmt_time)

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def wpos(p):
    return (int(80 + p[0] * 0.82), int(70 + p[1] * 0.8))


def wsize(s):
    return (int(s[0] * 0.82), int(s[1] * 0.8))


RING = [(220, 330), (1575, 330), (1575, 872), (220, 872)]
AVENUE = [(0, 560), (1575, 560)]
GATE = (92, 560)

# Bina -> bağlanacağı sahne / sekme
ACTIONS = {
    "hangar": [("ROKET TASARLA", "hangar", {}, "wrench")],
    "research": [("AR-GE EKRANI", "research", {}, "flask")],
    "astro": [("ASTRONOTLAR", "crew", {"tab": 0}, "astro"), ("İŞE AL", "crew", {"tab": 1}, "astro")],
    "medical": [("SAĞLIK DURUMU", "crew", {"tab": 2}, "medic")],
    "rec": [("DİNLENME", "crew", {"tab": 3}, "heart")],
    "depot": [("DEPOYU AÇ", "depot", {"tab": 0}, "box")],
    "fuel": [("YAKIT YÖNETİMİ", "depot", {"tab": 2}, "fuel")],
    "board": [("GÖREV TAHTASI", "quests", {"tab": 0}, "chart"), ("BAŞARIMLAR", "quests", {"tab": 2}, "trophy")],
    "nova": [("NOVA İLE KONUŞ", "nova", {}, "nova")],
    "control": [("GÖREV KONTROL", "control", {}, "eye")],
    "comms": [],
    "pads": [],
}


class Vehicle:
    def __init__(self, path, speed, color, offset):
        self.path = path
        self.speed = speed
        self.color = color
        self.d = offset
        self.len = sum(math.dist(path[i], path[(i + 1) % len(path)]) for i in range(len(path)))

    def pos(self):
        d = self.d % self.len
        n = len(self.path)
        for i in range(n):
            a, b = self.path[i], self.path[(i + 1) % n]
            seg = math.dist(a, b)
            if d <= seg:
                k = d / max(1, seg)
                return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k), math.atan2(b[1] - a[1], b[0] - a[0])
            d -= seg
        return self.path[0], 0

    def update(self, dt):
        self.d += self.speed * dt


class BaseScene(Scene):
    music = "base"
    ambient = "amb_base"
    title = "ÜS"

    def __init__(self, app):
        super().__init__(app)
        self.world = pygame.Surface((W, H))
        self.static = None
        self.static_night = None
        self.ps = ParticleSystem(900)
        self.zoom = Spring(1.0, 90, 16)
        self.fx = Spring(W / 2, 90, 16)
        self.fy = Spring(H / 2, 90, 16)
        self.selected = None
        self.hover = None
        self.panel_k = Spring(0.0, 160, 18)
        self.panel_buttons = []
        self.rects = {}
        for b in D.BUILDINGS:
            cx, cy = wpos(b["pos"])
            w, h = wsize(b["size"])
            self.rects[b["key"]] = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        self.vehicles = []
        rng = random.Random(4)
        for i in range(9):
            path = RING if i < 6 else [(220, 560), (1575, 560), (1575, 572), (220, 572)]
            self.vehicles.append(Vehicle(path if i % 2 == 0 else path[::-1], rng.uniform(40, 80),
                                         rng.choice([C["gold"], C["cyan"], C["white"], C["orange"]]),
                                         rng.uniform(0, 3000)))
        self.crane = 0.0
        self.shadows = {}
        self.advisor = None
        self.adv_t = 0.0
        self.adv_button = None

    # ------------------------------------------------------------------ giriş
    def enter(self, focus=None, **kw):
        self.selected = None
        self.panel_k.snap(0.0)
        self.zoom.snap(1.0)
        self.fx.snap(W / 2)
        self.fy.snap(H / 2)
        self.widgets = []
        self.panel_buttons = []
        self.refresh_advisor()
        if focus:
            self.select(focus)
        g = self.game
        if g.s["flags"].get("first_base"):
            g.s["flags"]["first_base"] = False
            self.app.say(f"{g.name}, burası Fırlatma Üssü. Bir binaya tıkla, kamera yaklaşsın. "
                         f"Roket tasarlamak için Montaj Hangarı'na git.", "happy")

    def refresh_advisor(self):
        self.advisor = self.app.nova.advisor()
        self.adv_t = 0.0
        title, text, target = self.advisor
        self.widgets = [w for w in self.widgets if w is not self.adv_button]
        self.adv_button = self.add(Button((24, TOPBAR_H + 118, 120, 34), "GİT", lambda: self.app.go(target),
                                          accent=C["cyan"], size=14, icon="play"))

    # ------------------------------------------------------------- statik zemin
    def build_static(self, night):
        """Zemin: dokulu çim/sulak alan, asfalt yollar, beton bina parselleri (gerçekçi, ızgarasız)."""
        s = pygame.Surface((W, H))
        if HAS_NUMPY:
            rng = np.random.default_rng(3)

            def fbm(sh, octs):
                out = np.zeros(sh, np.float32)
                amp, tot = 1.0, 0.0
                for o in range(octs):
                    k = 2 ** (octs - o + 1)
                    g = rng.random((sh[1] // k + 2, sh[0] // k + 2)).astype(np.float32)
                    gs = pygame.surfarray.make_surface((np.dstack([g, g, g]) * 255).astype(np.uint8))
                    gs = pygame.transform.smoothscale(gs, ((sh[1] // k + 2) * k, (sh[0] // k + 2) * k))
                    g = pygame.surfarray.array3d(gs)[:sh[1], :sh[0], 0].T.astype(np.float32) / 255
                    out += g * amp
                    tot += amp
                    amp *= 0.55
                return out / tot
            n = fbm((H, W), 6)
            fine = rng.random((H, W)).astype(np.float32)
            day_g = np.array((70, 92, 62), np.float32)            # bastırılmış, doğal çim yeşili
            dry_g = np.array((104, 104, 74), np.float32)          # kuru ot
            night_g = np.array((18, 26, 36), np.float32)
            base = day_g[None, None, :] * (1 - n[..., None]) + dry_g[None, None, :] * n[..., None]
            base = base * (0.9 + 0.12 * fine[..., None])
            base = base * (1 - night) + night_g[None, None, :] * night * (0.85 + 0.3 * n[..., None])
            arr = np.clip(base, 0, 255).astype(np.uint8).transpose(1, 0, 2)
            pygame.surfarray.blit_array(s, arr)
        else:
            s.blit(vertical_gradient((W, H), (70, 90, 62), (60, 80, 58)), (0, 0))
        # çevre çiti
        fence = lerp_color((150, 150, 146), (54, 62, 86), night)
        pygame.draw.rect(s, fence, (150, 200, W - 170, H - 214), 2, border_radius=30)
        # yollar: kenar şeridi + asfalt + soluk şerit çizgisi
        road = lerp_color((64, 66, 70), (20, 22, 30), night)
        edge = lerp_color((112, 112, 106), (40, 46, 66), night)
        lane = lerp_color((206, 186, 120), (120, 108, 70), night)
        pts = RING + [RING[0]]
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(s, edge, a, b, 34)
            pygame.draw.line(s, road, a, b, 28)
        pygame.draw.line(s, edge, AVENUE[0], AVENUE[1], 34)
        pygame.draw.line(s, road, AVENUE[0], AVENUE[1], 28)
        for a, b in list(zip(pts, pts[1:])) + [tuple(AVENUE)]:
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy)
            for t in range(0, int(d), 34):
                k0, k1 = t / d, min(1, (t + 16) / d)
                pygame.draw.line(s, lane, (a[0] + dx * k0, a[1] + dy * k0), (a[0] + dx * k1, a[1] + dy * k1), 2)
        # bina bağlantı yolları
        for key, r in self.rects.items():
            c = r.center
            targets = [(c[0], 330), (c[0], 872), (220, c[1]), (1575, c[1]), (c[0], 560)]
            best = min(targets, key=lambda p: math.dist(p, c))
            pygame.draw.line(s, edge, c, best, 20)
            pygame.draw.line(s, road, c, best, 14)
        # beton parseller (bina temelleri)
        for key, r in self.rects.items():
            base = r.inflate(26, 22)
            pygame.draw.rect(s, lerp_color((96, 100, 98), (30, 36, 52), night), base, border_radius=6)
            pygame.draw.rect(s, lerp_color((80, 84, 82), (26, 30, 46), night), base, 2, border_radius=6)
        # giriş kapısı
        pygame.draw.rect(s, lerp_color((110, 112, 110), (34, 40, 64), night), (GATE[0] - 30, GATE[1] - 60, 60, 120),
                         border_radius=8)
        return s

    # ------------------------------------------------------------- seçim/panel
    def select(self, key):
        self.selected = key
        r = self.rects[key]
        self.zoom.target = 1.55
        # paneli sağa yerleştirmek için odak biraz sağa
        self.fx.target = clamp(r.centerx + 150, W / 2 / 1.55, W - W / 2 / 1.55)
        self.fy.target = clamp(r.centery, H / 2 / 1.55, H - H / 2 / 1.55)
        self.panel_k.target = 1.0
        self.app.audio.play("whoosh", 0.4)
        self.build_panel()

    def deselect(self):
        self.selected = None
        self.zoom.target = 1.0
        self.fx.target = W / 2
        self.fy.target = H / 2
        self.panel_k.target = 0.0
        self.panel_buttons = []

    def panel_rect(self):
        k = ease_out_cubic(clamp(self.panel_k.value, 0, 1))
        return pygame.Rect(W - 560 + int((1 - k) * 600), TOPBAR_H + 16, 536, H - TOPBAR_H - 32)

    def build_panel(self):
        self.panel_buttons = []
        key = self.selected
        if not key:
            return
        g = self.game
        b = D.BUILDING[key]
        pr = pygame.Rect(W - 560, TOPBAR_H + 16, 536, H - TOPBAR_H - 32)
        y = pr.bottom - 74
        cost = g.upgrade_cost(key)
        if cost is not None:
            lab = f"SEVİYE {g.lvl(key) + 1}'E YÜKSELT · {fmt_num(cost)} P" if g.lvl(key) > 0 or cost else "KUR"
            if g.lvl(key) == 0:
                lab = f"İNŞA ET · {fmt_num(cost)} P"
            ub = Button((pr.x + 24, y, pr.w - 48, 54), lab, lambda: self.upgrade(key), accent=C["gold"], icon="star",
                        size=17, style="big")
            ok, why = g.can_upgrade(key)
            ub.set_enabled(ok, why)
            ub.pulse = ok
            self.panel_buttons.append(ub)
            y -= 64
        for label, scene, kw, icon in reversed(ACTIONS.get(key, [])):
            self.panel_buttons.append(Button((pr.x + 24, y, pr.w - 48, 50), label,
                                             (lambda s=scene, k=kw: self.app.go(s, **k)), accent=b["color"],
                                             icon=icon, size=16))
            y -= 60
        if key == "fuel":
            fb = Button((pr.x + 24, y, pr.w - 48, 48), "MARKETTEN 50 KG YAKIT AL (200 P)",
                        lambda: self.act(g.buy_fuel, 50), accent=C["orange"], icon="fuel", size=15)
            self.panel_buttons.append(fb)
        if key == "pads":
            for i in range(3):
                pad = g.s["pads"][i]
                bx = pr.x + 24
                by = pr.y + 300 + i * 92
                if pad and pad["prep"] <= 0:
                    lb = Button((pr.right - 190, by + 18, 160, 46), "FIRLAT", (lambda j=i: self.launch(j)),
                                accent=C["green"], icon="rocket", size=17, style="big")
                    lb.pulse = True
                    self.panel_buttons.append(lb)
                if pad:
                    self.panel_buttons.append(Button((pr.right - 250, by + 24, 50, 34), "", (lambda j=i: self.scrub(j)),
                                                     accent=C["red"], icon="cross", size=12,
                                                     tooltip="Fırlatmayı iptal et (%50 iade)"))
            self.panel_buttons.append(Button((pr.x + 24, pr.bottom - 138, pr.w - 48, 50), "YENİ ROKET TASARLA",
                                             lambda: self.app.go("hangar"), accent=C["orange"], icon="wrench", size=16))
        self.panel_buttons.append(Button((pr.right - 58, pr.y + 14, 40, 40), "", self.deselect, accent=C["text_dim"],
                                         icon="cross", size=14, hotkey=pygame.K_ESCAPE))

    def upgrade(self, key):
        if self.act(self.game.upgrade, key):
            lv = self.game.lvl(key)
            r = self.rects[key]
            for i in range(4):
                self.ps.sparks(r.centerx + random.uniform(-r.w / 2, r.w / 2), r.centery, 16, C["gold"])
            self.ps.ring(r.centerx, r.centery, 200, C["gold"])
            if key == "nova":
                self.app.say(f"{self.game.name}, yeni çekirdeklerim çevrimiçi. Artık Seviye {lv} NOVA'yım!", "happy")
        self.build_panel()
        self.refresh_advisor()

    def scrub(self, i):
        self.game.scrub_pad(i)
        self.build_panel()

    def launch(self, i):
        self.app.go("launch", pad=i)

    def rebuild(self):
        self.build_panel()

    # ------------------------------------------------------------------ olay
    def screen_to_world(self, p):
        z = self.zoom.value
        return (self.fx.value + (p[0] - W / 2) / z, self.fy.value + (p[1] - H / 2) / z)

    def world_to_screen(self, p):
        z = self.zoom.value
        return (W / 2 + (p[0] - self.fx.value) * z, H / 2 + (p[1] - self.fy.value) * z)

    def handle(self, e):
        for b in reversed(self.panel_buttons):
            if b.handle(e):
                return True
        if super().handle(e):
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.selected and self.panel_rect().collidepoint(e.pos):
                return True
            if e.pos[1] < TOPBAR_H:
                return False
            wp = self.screen_to_world(e.pos)
            for key, r in self.rects.items():
                if r.inflate(16, 16).collidepoint(wp):
                    if key == self.selected:
                        self.deselect()
                    else:
                        self.select(key)
                    return True
            if self.selected:
                self.deselect()
                return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and self.selected:
            self.deselect()
            return True
        return False

    # --------------------------------------------------------------- güncelle
    def update(self, dt):
        super().update(dt)
        for s in (self.zoom, self.fx, self.fy, self.panel_k):
            s.update(dt)
        for v in self.vehicles:
            v.update(dt)
        for b in self.panel_buttons:
            b.update(dt)
        self.ps.update(dt)
        self.crane += dt
        self.adv_t += dt
        if self.adv_t > 25:
            self.refresh_advisor()
        # hover
        self.hover = None
        if not (self.selected and self.panel_rect().collidepoint(UI.mouse)) and UI.mouse[1] > TOPBAR_H:
            wp = self.screen_to_world(UI.mouse)
            for key, r in self.rects.items():
                if r.inflate(16, 16).collidepoint(wp):
                    self.hover = key
                    UI.set_tooltip(f"{D.BUILDING[key]['name']} · Sv{self.game.lvl(key)}", D.BUILDING[key]["color"])
        # efekt yayımı
        g = self.game
        fr = self.rects["fuel"]
        if random.random() < 0.08:
            self.ps.smoke(fr.x + 30, fr.y + 10, 1, angle=-math.pi / 2, spread=0.3, speed=(10, 30), size=(5, 9),
                          life=(1.5, 3), color=(220, 220, 230), alpha=60, grow=10, grav=-8)
        for i, pad in enumerate(g.s["pads"]):
            if pad:
                cx, cy = self.pad_center(i)
                if random.random() < 0.15:
                    self.ps.smoke(cx, cy + 22, 1, angle=0, spread=math.pi, speed=(5, 25), size=(5, 10),
                                  life=(1, 2.5), color=(230, 235, 245), alpha=70, grow=12, grav=-4)
        # panel durumunun canlı kalması
        if self.selected == "pads" and int(self.t * 2) % 2 == 0:
            ready = sum(1 for p in g.s["pads"] if p and p["prep"] <= 0)
            have = sum(1 for b in self.panel_buttons if b.label == "FIRLAT")
            if ready != have:
                self.build_panel()

    def pad_center(self, i):
        r = self.rects["pads"]
        return (r.x + r.w * (0.18 + 0.32 * i), r.centery)

    # ------------------------------------------------------------------ çizim
    def night_factor(self):
        h = self.game.hour_of_day()
        if 7 <= h <= 18:
            return 0.15
        if h < 5 or h > 20.5:
            return 1.0
        if h < 7:
            return 1.0 - (h - 5) / 2 * 0.85
        return 0.15 + (h - 18) / 2.5 * 0.85

    def draw(self, surf):
        night = self.night_factor()
        nq = round(night * 8) / 8
        if self.static is None or self.static[0] != nq:
            self.static = (nq, self.build_static(nq))
        ws = self.world
        ws.blit(self.static[1], (0, 0))
        self.draw_world(ws, night)
        if cinema.enabled():
            day = 1.0 - night
            cinema.full_pass(ws, ws.get_rect(), self.t, sun=(int(W * 0.84), -90),
                             sun_col=(255, 196, 136) if day > 0.5 else (150, 180, 255), rays=0.3 + 0.5 * day,
                             mote_col=(255, 228, 190) if day > 0.5 else (190, 210, 255), n_motes=44,
                             haze_col=(60, 46, 30) if day > 0.5 else (20, 28, 64), haze_k=0.7,
                             warm=(int(40 * day), int(22 * day), 4), cool=(130, 120, 205))
        z = self.zoom.value
        if abs(z - 1.0) < 0.003:
            surf.blit(ws, (0, 0))
        else:
            vw, vh = W / z, H / z
            vx = clamp(self.fx.value - vw / 2, 0, W - vw)
            vy = clamp(self.fy.value - vh / 2, 0, H - vh)
            rect = pygame.Rect(int(vx), int(vy), int(vw), int(vh))
            sub = pygame.Surface(rect.size)
            sub.blit(ws, (0, 0), rect)
            pygame.transform.smoothscale(sub, (W, H), surf)
        self.draw_overlay(surf)

    def draw_world(self, s, night):
        g = self.game
        t = self.t
        # araçlar
        for v in self.vehicles:
            (x, y), a = v.pos()
            ca, sa = math.cos(a), math.sin(a)
            body = [(x + ca * 10 - sa * 5, y + sa * 10 + ca * 5), (x + ca * 10 + sa * 5, y + sa * 10 - ca * 5),
                    (x - ca * 10 + sa * 5, y - sa * 10 - ca * 5), (x - ca * 10 - sa * 5, y - sa * 10 + ca * 5)]
            pygame.draw.polygon(s, scale_color(v.color, 0.7), body)
            if night > 0.4:
                draw_glow(s, (x + ca * 16, y + sa * 16), 14, (255, 240, 200), 0.6 * night)
                draw_glow(s, (x - ca * 11, y - sa * 11), 6, (255, 60, 60), 0.6 * night)
        # binalar
        for b in D.BUILDINGS:
            self.draw_building(s, b, night, t)
        # giriş tabelası
        self.draw_sign(s, night, t)
        self.ps.draw(s)
        # gece ışık havuzu
        if night > 0.3:
            for key, r in self.rects.items():
                if g.lvl(key) > 0:
                    draw_glow(s, r.center, max(r.w, r.h) * 0.75, scale_color(D.BUILDING[key]["color"], 0.4),
                              0.3 * night)
            for x in range(240, 1560, 160):
                for y in (330, 872):
                    draw_glow(s, (x, y - 18), 20, (255, 220, 150), 0.5 * night)

    def draw_sign(self, s, night, t):
        g = self.game
        col = g.color
        r = pygame.Rect(18, 600, 230, 92)
        pygame.draw.line(s, (120, 120, 130), (r.x + 30, r.bottom), (r.x + 30, r.bottom + 30), 4)
        pygame.draw.line(s, (120, 120, 130), (r.right - 30, r.bottom), (r.right - 30, r.bottom + 30), 4)
        pygame.draw.rect(s, (8, 12, 26), r, border_radius=10)
        flick = 0.85 + 0.15 * math.sin(t * 13) * (1 if random.random() < 0.02 else 0)
        pygame.draw.rect(s, scale_color(col, flick), r, 3, border_radius=10)
        draw_glow(s, r.center, 140, col, 0.25 + 0.35 * night)
        name = g.name.upper()
        fs = 22 if len(name) <= 14 else 16
        draw_text(s, name, (r.centerx, r.y + 14), fs, C["white"], bold=True, anchor="midtop", glow=col)
        draw_text(s, "- FIRLATMA ÜSSÜ -", (r.centerx, r.y + 56), 14, scale_color(col, flick), bold=True,
                  anchor="midtop")
        # kapı bariyeri
        ang = math.sin(t * 0.6) * 0.5 + 0.5
        pygame.draw.line(s, (255, 80, 80), (GATE[0] - 30, GATE[1] - 44),
                         (GATE[0] - 30 + 60 * math.cos(ang * 1.4), GATE[1] - 44 - 60 * math.sin(ang * 1.4)), 4)

    def draw_building(self, s, b, night, t):
        g = self.game
        key = b["key"]
        r = self.rects[key]
        lv = g.lvl(key)
        col = b["color"]
        hov = (self.hover == key) or (self.selected == key)
        dim = 0.35 if lv == 0 else 1.0
        # gerçekçi 3B bina modeli (önbellekli) + oyun durumuna bağlı hareketli katman
        extra = {}
        if key == "pads":
            extra["centers"] = tuple((round(self.pad_center(i)[0] - r.x), round(self.pad_center(i)[1] - r.y),
                                      (58, 74, 92)[i]) for i in range(3))
        elif key == "fuel":
            extra["n"] = 2 + lv
        img, (ox, oy) = archviz.building(key, r.size, lv, night, self.game.color, **extra)
        s.blit(img, (r.x - ox, r.y - oy))
        fn = getattr(self, "d_" + key, None)
        if fn and (lv > 0 or key == "pads"):
            fn(s, r, lv, col, night, t, dim)
        if lv == 0:
            draw_icon(s, "lock", (r.centerx, r.centery - 30), 26, C["gold"])
        # hover çerçevesi
        if hov:
            k = 0.6 + 0.4 * math.sin(t * 5)
            pygame.draw.rect(s, col, r.inflate(20, 20), 2, border_radius=16)
            draw_glow(s, r.midtop, 40, col, 0.6 * k)
            for cx, cy in (r.inflate(20, 20).topleft, r.inflate(20, 20).topright, r.inflate(20, 20).bottomleft,
                           r.inflate(20, 20).bottomright):
                draw_glow(s, (cx, cy), 12, col, k)
        # etiket
        lab = render_text(tr(b["short"]), 13, C["white"], True)
        lr = lab.get_rect(midtop=(r.centerx, r.bottom + 10))
        bg = pygame.Surface((lr.w + 40, lr.h + 8), pygame.SRCALPHA)
        pygame.draw.rect(bg, (6, 10, 24, 200), bg.get_rect(), border_radius=8)
        pygame.draw.rect(bg, (*col, 200 if hov else 110), bg.get_rect(), 1, border_radius=8)
        s.blit(bg, (lr.x - 20, lr.y - 4))
        s.blit(lab, lr)
        # seviye noktaları
        for i in range(b["max"]):
            cc = col if i < lv else (60, 70, 90)
            pygame.draw.circle(s, cc, (lr.right + 10 + i * 9, lr.centery), 3)
        # yükseltme oku
        ok, _ = g.can_upgrade(key)
        if ok:
            ay = r.y - 14 + math.sin(t * 4) * 4
            pygame.draw.polygon(s, C["gold"], [(r.right - 6, ay - 10), (r.right + 4, ay), (r.right - 16, ay)])
            pygame.draw.rect(s, C["gold"], (r.right - 9, ay, 6, 8))
            draw_glow(s, (r.right - 6, ay - 2), 14, C["gold"], 0.6)

    # ------------------------------------------------------------- hareketli katmanlar (modelin üstü)
    @staticmethod
    def _top(r, fx, fy, z):
        """Ayak izindeki (fx, fy oranı) noktanın z yüksekliğindeki ekran konumu (archviz izdüşümü)."""
        return (r.x + r.w * fx - z * archviz.KX, r.y + r.h * fy - z * archviz.KZ)

    def d_pads(self, s, r, lv, col, night, t, dim):
        g = self.game
        for i in range(3):
            cx, cy = self.pad_center(i)
            open_ = lv >= i + 1
            size = (58, 74, 92)[i]
            pr = pygame.Rect(0, 0, size, size)
            pr.center = (int(cx), int(cy))
            label = "ABC"[i]
            draw_text(s, f"RAMPA {label}", (pr.centerx, pr.bottom + 6), 11,
                      C["gold"] if open_ else C["text_mute"], bold=True, anchor="midtop")
            if not open_:
                draw_icon(s, "lock", pr.center, 18, C["text_mute"])
                continue
            # kule tepesinde uçak ikaz lambası
            zt = 40 + 18 * i + 3
            tx = pr.right + 2 + max(7, size * 0.14) / 2 - zt * archviz.KX
            ty = pr.y + size * 0.2 - zt * archviz.KZ
            if (t * 1.3 + i * 0.3) % 1 < 0.5:
                draw_glow(s, (tx, ty), 12, (255, 70, 60), 0.9)
            pad = g.s["pads"][i]
            if pad:
                bo, _ = art.render_booster(min(3, i + 1), g.name, g.color, 0.24)
                s.blit(bo, (pr.centerx - bo.get_width() // 2 - 2, pr.centery - bo.get_height() + 10))
                if pad["prep"] > 0:
                    frac = 1 - pad["prep"] / D.PAD_PREP_SEC[i + 1]
                    radial_progress(s, (pr.centerx, pr.centery + 6), size // 2 + 6, frac, C["orange"], 3)
                else:
                    k = 0.5 + 0.5 * math.sin(t * 6)
                    draw_glow(s, pr.center, size * 0.7, C["green"], 0.35 * k)
                    draw_text(s, "HAZIR", (pr.centerx, pr.y - 26), 12, C["green"], bold=True, anchor="midtop")

    def d_research(self, s, r, lv, col, night, t, dim):
        c = self._top(r, 0.5, 0.5, 30 + 6 * lv + min(r.w, r.h) * 0.12)
        if lv >= 3:
            draw_glow(s, c, min(r.w, r.h) * 0.5, (110, 200, 235), 0.18 + 0.08 * math.sin(t * 2))
        if self.game.s["research"]["active"]:
            k = self.game.research_progress()[1]
            radial_progress(s, c, min(r.w, r.h) // 2 + 8, k, C["cyan"], 3)

    def d_astro(self, s, r, lv, col, night, t, dim):
        for i in range(min(4, len(self.game.s["crew"]))):
            c = self.game.s["crew"][i]
            if c["status"] == "ready":
                art.draw_astronaut(s, r.x + 26 + i * 22, r.bottom + 2, c["type"], 0.36, t)

    def d_depot(self, s, r, lv, col, night, t, dim):
        used = self.game.depot_used() / max(1, self.game.depot_cap())
        rng = random.Random(5)
        for i in range(int(2 + used * 8)):                       # önde istiflenmiş sandıklar
            bx = r.x + 10 + rng.random() * (r.w - 40)
            by = r.bottom - 12 + rng.random() * 6
            pygame.draw.rect(s, rng.choice([(150, 116, 74), (132, 102, 66), (166, 132, 84)]), (bx, by - 10, 14, 10))
            pygame.draw.rect(s, (80, 60, 40), (bx, by - 10, 14, 10), 1)
        fx = r.x + 20 + (math.sin(t * 0.7) * 0.5 + 0.5) * (r.w - 60)
        pygame.draw.rect(s, (206, 168, 84), (fx, r.bottom + 4, 20, 11), border_radius=3)
        if night > 0.4:
            draw_glow(s, (fx + 24, r.bottom + 9), 14, (255, 236, 200), 0.5)

    def d_board(self, s, r, lv, col, night, t, dim):
        # çatıdaki LED pano: görevler kayar
        z = 22
        scr = pygame.Rect(0, 0, int(r.w * 0.8), int(r.h * 0.56))
        tl = self._top(r, 0.1, 0.2, z)
        scr.topleft = (int(tl[0]), int(tl[1]))
        pygame.draw.rect(s, (10, 14, 22), scr, border_radius=4)
        pygame.draw.rect(s, scale_color(col, 0.6), scr, 1, border_radius=4)
        q = self.game.s["quests"]
        items = [it["text"] for it in q["daily"] + q["weekly"]] or ["GÖREV YOK"]
        old = s.get_clip()
        s.set_clip(scr.inflate(-6, -6))
        off = (t * 22) % (len(items) * 20)
        for i in range(len(items) * 2):
            it = items[i % len(items)]
            draw_text(s, "> " + tr(it), (scr.x + 6, scr.y + 4 + i * 20 - off), 11, (150, 220, 120), bold=True,
                      shadow=False, raw=True, max_w=scr.w - 12)
        s.set_clip(old)

    def d_nova(self, s, r, lv, col, night, t, dim):
        c = self._top(r, 0.5, 0.48, 40 + 8 * lv)
        k = 0.7 + 0.3 * math.sin(t * 2)
        draw_glow(s, c, r.w * 0.34, scale_color(col, 0.8), 0.45 * k)
        px = c[0] + math.sin(t * 0.8) * r.w * 0.08
        pygame.draw.circle(s, lerp_color(col, (230, 240, 245), 0.4), (int(px), int(c[1])), max(4, int(r.h * 0.06)))
        for i in range(lv):
            a = t * (1 + i * 0.5) + i
            rr = int(r.w * 0.3 + i * 7)
            pygame.draw.arc(s, scale_color(col, 0.7), (c[0] - rr, c[1] - rr * 0.8, rr * 2, rr * 1.6), a, a + 1.2, 2)

    def d_control(self, s, r, lv, col, night, t, dim):
        if self.game.s["storms"] and self.game.storm_active():
            draw_glow(s, r.center, r.w * 0.6, C["red"], 0.3 + 0.2 * math.sin(t * 8))

    def d_fuel(self, s, r, lv, col, night, t, dim):
        full = self.game.s["fuel"] / max(1, self.game.fuel_cap())
        draw_bar(s, (r.x + 10, r.bottom + 4, r.w - 20, 6), full, C["orange"], glow=False)
        if full > 0.95:
            draw_glow(s, (r.right - 14, r.bottom + 7), 12, C["green"], 0.7)

    def d_comms(self, s, r, lv, col, night, t, dim):
        z = 44 + 8 * lv + 3
        tip = self._top(r, 0.44, 0.42, z)
        tip = (tip[0] + 4, tip[1])
        a = t * 0.5
        dw = r.w * 0.5
        dh = r.h * 0.26 * (0.4 + 0.6 * abs(math.cos(a)))
        dish = pygame.Rect(0, 0, int(dw), int(max(4, dh)))
        dish.center = (int(tip[0]), int(tip[1]))
        pygame.draw.ellipse(s, (188, 192, 196), dish)
        pygame.draw.ellipse(s, (120, 126, 136), dish, 2)
        pygame.draw.ellipse(s, (150, 156, 166), dish.inflate(-dish.w * 0.45, -dish.h * 0.45), 1)
        feed = (dish.centerx + math.sin(a) * 16, dish.centery - 22)
        pygame.draw.line(s, (160, 164, 170), dish.center, feed, 2)
        draw_glow(s, feed, 12, col, 0.7)
        for i in range(lv):
            rr = int(20 + ((t * 40 + i * 30) % 90))
            fade = 1 - rr / 110
            if fade > 0.3:                     # sönük halkalar koyu çizgiye dönüşmesin
                pygame.draw.circle(s, scale_color(col, fade), (int(feed[0]), int(feed[1])), rr, 1)

    def d_medical(self, s, r, lv, col, night, t, dim):
        sick = [c for c in self.game.s["crew"] if c["status"] == "sick"]
        if sick:
            draw_text(s, f"{len(sick)}", (r.right - 8, r.y - 40), 13, C["red"], bold=True, anchor="topright")
            draw_icon(s, "medic", (r.right - 26, r.y - 32), 14, C["red"])

    def d_rec(self, s, r, lv, col, night, t, dim):
        rest = [c for c in self.game.s["crew"] if c["status"] == "resting"]
        for i, c in enumerate(rest[:3]):
            art.draw_astronaut(s, r.x + r.w * 0.6 + i * 22, r.y + r.h * 0.7, c["type"], 0.36, t)

    # ------------------------------------------------------------- bina çizimleri
    def _roof(self, s, r, base, dim, radius=10):
        c1 = scale_color(base, 0.95 * dim)
        c2 = scale_color(base, 0.55 * dim)
        for i in range(r.h):
            k = i / max(1, r.h)
            pygame.draw.line(s, lerp_color(c1, c2, k), (r.x + 2, r.y + i), (r.right - 3, r.y + i))
        pygame.draw.rect(s, scale_color(base, 0.35 * dim), r, 2, border_radius=radius)

    def _windows(self, s, r, night, t, rows=2, cols=6, color=(255, 230, 150), seed=0):
        rng = random.Random(seed)
        for j in range(rows):
            for i in range(cols):
                x = r.x + 10 + i * (r.w - 20) / cols
                y = r.y + 10 + j * (r.h - 20) / rows
                on = rng.random() < 0.75 and (night > 0.35 or rng.random() < 0.25)
                c = color if on else (40, 50, 70)
                pygame.draw.rect(s, c, (x, y, (r.w - 20) / cols - 5, 6), border_radius=2)
                if on and night > 0.5:
                    draw_glow(s, (x + 6, y + 3), 9, color, 0.35)

    def b_pads(self, s, r, lv, col, night, t, dim):
        g = self.game
        pygame.draw.rect(s, (52, 54, 62) if night < 0.5 else (30, 32, 42), r, border_radius=12)
        pygame.draw.rect(s, (90, 92, 100), r, 2, border_radius=12)
        for i in range(3):
            cx, cy = self.pad_center(i)
            open_ = lv >= i + 1
            size = (58, 74, 92)[i]
            pr = pygame.Rect(0, 0, size, size)
            pr.center = (int(cx), int(cy))
            pygame.draw.rect(s, (70, 72, 82) if open_ else (40, 42, 50), pr, border_radius=8)
            pygame.draw.rect(s, (255, 206, 84) if open_ else (80, 80, 90), pr, 2, border_radius=8)
            pygame.draw.circle(s, (30, 30, 36), pr.center, size // 3)
            pygame.draw.circle(s, (120, 120, 130), pr.center, size // 3, 2)
            # kule
            tw = pygame.Rect(pr.right + 4, pr.y - 6, 14, pr.h + 12)
            pygame.draw.rect(s, (200, 70, 50) if open_ else (70, 60, 60), tw)
            for k in range(0, tw.h, 10):
                pygame.draw.line(s, (120, 40, 30), (tw.x, tw.y + k), (tw.right, tw.y + k + 10), 1)
            if open_:
                blink = (t * 1.3 + i * 0.3) % 1 < 0.5
                if blink:
                    draw_glow(s, (tw.centerx, tw.y), 14, (255, 60, 60), 1.0)
                draw_glow(s, pr.center, size, (255, 210, 140), 0.18 + 0.25 * night)
            label = "ABC"[i]
            draw_text(s, f"RAMPA {label}", (pr.centerx, pr.bottom + 4), 11,
                      C["gold"] if open_ else C["text_mute"], bold=True, anchor="midtop")
            if not open_:
                draw_icon(s, "lock", pr.center, 18, C["text_mute"])
            pad = g.s["pads"][i]
            if pad:
                bo, _ = art.render_booster(min(3, i + 1), g.name, g.color, 0.24)
                s.blit(bo, (pr.centerx - bo.get_width() // 2, pr.centery - bo.get_height() + 16))
                if pad["prep"] > 0:
                    frac = 1 - pad["prep"] / D.PAD_PREP_SEC[i + 1]
                    radial_progress(s, (pr.centerx, pr.centery + 6), size // 2 + 6, frac, C["orange"], 3)
                else:
                    k = 0.5 + 0.5 * math.sin(t * 6)
                    draw_glow(s, pr.center, size * 0.9, C["green"], 0.5 * k)
                    draw_text(s, "HAZIR", (pr.centerx, pr.y - 22), 12, C["green"], bold=True, anchor="midtop")

    def b_research(self, s, r, lv, col, night, t, dim):
        c = r.center
        rad = min(r.w, r.h) // 2
        pygame.draw.circle(s, (40, 60, 90), c, rad + 6)
        dome = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
        for i in range(rad, 0, -2):
            k = i / rad
            pygame.draw.circle(dome, (*lerp_color((180, 240, 255), (40, 120, 200), k), int(200 * (1 - k * 0.4))),
                               (rad, rad), i)
        s.blit(dome, (c[0] - rad, c[1] - rad))
        for a in range(0, 180, 30):
            ang = math.radians(a)
            pygame.draw.line(s, (200, 240, 255), (c[0] - math.cos(ang) * rad, c[1] - math.sin(ang) * rad * 0.2),
                             (c[0] + math.cos(ang) * rad, c[1] + math.sin(ang) * rad * 0.2), 1)
        pygame.draw.circle(s, (220, 250, 255), c, rad, 2)
        pygame.draw.ellipse(s, (255, 255, 255), (c[0] - rad * 0.55, c[1] - rad * 0.7, rad * 0.5, rad * 0.25))
        for i in range(4):
            a = t * 0.6 + i * 1.6
            pygame.draw.circle(s, (70, 220, 120), (int(c[0] + math.cos(a) * rad * 0.5), int(c[1] + math.sin(a) * rad * 0.3)), 3)
        if lv >= 3:
            draw_glow(s, c, rad * 1.5, (90, 220, 255), 0.55 + 0.25 * math.sin(t * 2))
        if self.game.s["research"]["active"]:
            k = self.game.research_progress()[1]
            radial_progress(s, c, rad + 12, k, C["cyan"], 3)

    def b_astro(self, s, r, lv, col, night, t, dim):
        self._roof(s, r, (70, 100, 170), dim)
        self._windows(s, r.inflate(-10, -40).move(0, -10), night, t, 1, 7, seed=2)
        gym = pygame.Rect(r.x + 10, r.bottom - 38, 50, 28)
        pygame.draw.rect(s, (40, 60, 110), gym, border_radius=4)
        pygame.draw.line(s, (220, 220, 230), (gym.x + 8, gym.centery), (gym.right - 8, gym.centery), 3)
        pygame.draw.circle(s, (220, 220, 230), (gym.x + 8, gym.centery), 5)
        pygame.draw.circle(s, (220, 220, 230), (gym.right - 8, gym.centery), 5)
        sim = pygame.Rect(r.right - 70, r.bottom - 42, 58, 32)
        pygame.draw.ellipse(s, (20, 30, 60), sim)
        a = t * 2
        pygame.draw.line(s, (70, 140, 255), sim.center, (sim.centerx + math.cos(a) * 24, sim.centery + math.sin(a) * 12), 3)
        for i in range(min(4, len(self.game.s["crew"]))):
            c = self.game.s["crew"][i]
            if c["status"] == "ready":
                art.draw_astronaut(s, r.x + 90 + i * 22, r.bottom - 24, c["type"], 0.42, t)

    def b_depot(self, s, r, lv, col, night, t, dim):
        self._roof(s, r, (150, 130, 80), dim)
        for i in range(int(r.w / 26)):
            pygame.draw.line(s, (120, 100, 60), (r.x + 10 + i * 26, r.y + 4), (r.x + 10 + i * 26, r.bottom - 4), 1)
        used = self.game.depot_used() / max(1, self.game.depot_cap())
        rng = random.Random(5)
        for i in range(int(4 + used * 14)):
            bx = r.x + 14 + rng.random() * (r.w - 40)
            by = r.y + 14 + rng.random() * (r.h - 40)
            pygame.draw.rect(s, rng.choice([(200, 150, 70), (170, 120, 60), (220, 180, 90)]), (bx, by, 16, 14))
            pygame.draw.rect(s, (90, 60, 30), (bx, by, 16, 14), 1)
        fx = r.x + 20 + (math.sin(t * 0.7) * 0.5 + 0.5) * (r.w - 60)
        pygame.draw.rect(s, (255, 206, 84), (fx, r.bottom - 26, 22, 14), border_radius=3)
        pygame.draw.line(s, (60, 60, 60), (fx + 22, r.bottom - 24), (fx + 30, r.bottom - 24), 3)
        if night > 0.4:
            draw_glow(s, (fx + 30, r.bottom - 20), 16, (255, 240, 200), 0.6)

    def b_board(self, s, r, lv, col, night, t, dim):
        pygame.draw.rect(s, (10, 16, 26), r, border_radius=8)
        pygame.draw.rect(s, col, r, 2, border_radius=8)
        scr = r.inflate(-16, -16)
        q = self.game.s["quests"]
        items = [it["text"] for it in q["daily"] + q["weekly"]] or ["GÖREV YOK"]
        old = s.get_clip()
        s.set_clip(scr)
        off = (t * 22) % (len(items) * 22)
        for i in range(len(items) * 2):
            it = items[i % len(items)]
            y = scr.y + i * 22 - off
            draw_text(s, "> " + tr(it), (scr.x + 6, y), 12, C["lime"], bold=True, shadow=False, raw=True, max_w=scr.w - 10)
        s.set_clip(old)
        draw_glow(s, r.center, r.w * 0.6, col, 0.2 + 0.3 * night)

    def b_nova(self, s, r, lv, col, night, t, dim):
        pygame.draw.rect(s, (6, 6, 10), r, border_radius=14)
        pygame.draw.rect(s, (40, 50, 70), r, 2, border_radius=14)
        c = r.center
        eye = pygame.Rect(0, 0, int(r.w * 0.6), int(r.h * 0.32))
        eye.center = c
        k = 0.7 + 0.3 * math.sin(t * 2)
        draw_glow(s, c, r.w * 0.7, col, 0.6 * k)
        pygame.draw.ellipse(s, (8, 30, 50), eye)
        pygame.draw.ellipse(s, col, eye, 2)
        px = c[0] + math.sin(t * 0.8) * eye.w * 0.2
        pygame.draw.circle(s, lerp_color(col, C["white"], 0.5), (int(px), c[1]), int(eye.h * 0.35))
        draw_glow(s, (px, c[1]), eye.h, col, 0.9)
        for i in range(lv):
            a = t * (1 + i * 0.5) + i
            rr = int(r.w * 0.45 + i * 8)
            pygame.draw.arc(s, scale_color(col, 0.8), (c[0] - rr, c[1] - rr, rr * 2, rr * 2), a, a + 1.2, 2)

    def b_control(self, s, r, lv, col, night, t, dim):
        self._roof(s, r, (90, 40, 90), dim)
        for i in range(3):
            sr = pygame.Rect(r.x + 14 + i * (r.w - 28) / 3, r.y + 14, (r.w - 28) / 3 - 8, r.h * 0.45)
            pygame.draw.rect(s, (8, 12, 26), sr, border_radius=4)
            pts = [(sr.x + k * sr.w / 12, sr.centery + math.sin(t * 3 + k + i) * sr.h * 0.3) for k in range(13)]
            pygame.draw.lines(s, (255, 70, 200) if i != 1 else (70, 255, 160), False, pts, 2)
            pygame.draw.rect(s, scale_color(col, 0.7), sr, 1, border_radius=4)
        for i in range(6):
            pygame.draw.circle(s, (230, 230, 240), (int(r.x + 22 + i * (r.w - 44) / 5), int(r.bottom - 22)), 5)
            pygame.draw.rect(s, (60, 60, 80), (r.x + 14 + i * (r.w - 44) / 5, r.bottom - 14, 16, 6))
        if self.game.s["storms"] and self.game.storm_active():
            draw_glow(s, r.center, r.w * 0.7, C["red"], 0.4 + 0.3 * math.sin(t * 8))

    def b_fuel(self, s, r, lv, col, night, t, dim):
        full = self.game.s["fuel"] / max(1, self.game.fuel_cap())
        n = 2 + lv
        for i in range(n):
            cx = r.x + 30 + i * (r.w - 60) / max(1, n - 1)
            cy = r.centery
            rad = int(min(34, r.h * 0.34))
            pygame.draw.circle(s, (230, 232, 240), (int(cx), cy), rad)
            pygame.draw.circle(s, (160, 165, 180), (int(cx), cy), rad, 2)
            pygame.draw.circle(s, (250, 250, 255), (int(cx - rad * 0.3), int(cy - rad * 0.3)), rad // 3)
            lc = C["green"] if full > 0.95 else C["orange"]
            pygame.draw.circle(s, lc, (int(cx), cy + rad - 6), 3)
            if full > 0.95:
                draw_glow(s, (cx, cy + rad - 6), 12, C["green"], 0.8)
        pygame.draw.line(s, (180, 180, 190), (r.x + 20, r.bottom - 10), (r.right - 20, r.bottom - 10), 4)
        draw_bar(s, (r.x + 10, r.y - 2, r.w - 20, 6), full, C["orange"], glow=False)

    def b_hangar(self, s, r, lv, col, night, t, dim):
        self._roof(s, r, (170, 176, 190), dim, 18)
        for i in range(8):
            y = r.y + 8 + i * (r.h - 16) / 8
            pygame.draw.line(s, (130, 136, 150), (r.x + 6, y), (r.right - 6, y), 1)
        door = pygame.Rect(r.x + r.w * 0.2, r.bottom - 14, r.w * 0.6, 12)
        pygame.draw.rect(s, (40, 44, 56), door)
        if night > 0.4:
            draw_glow(s, door.center, door.w * 0.6, (255, 230, 170), 0.5)
        cx = r.x + 30 + (math.sin(t * 0.5) * 0.5 + 0.5) * (r.w - 60)
        pygame.draw.line(s, (255, 206, 84), (r.x + 6, r.y + 22), (r.right - 6, r.y + 22), 4)
        pygame.draw.rect(s, (255, 160, 40), (cx - 10, r.y + 16, 20, 12))
        pygame.draw.line(s, (200, 200, 210), (cx, r.y + 28), (cx, r.centery + 10), 1)
        # yatay roket
        rk = pygame.Rect(0, 0, int(r.w * 0.55), 16)
        rk.center = (r.centerx, r.centery + 16)
        pygame.draw.rect(s, (240, 242, 248), rk, border_radius=8)
        pygame.draw.polygon(s, self.game.color, [(rk.right, rk.y), (rk.right + 16, rk.centery), (rk.right, rk.bottom)])
        for i in range(3):
            wx = r.x + 30 + i * 40 + math.sin(t * 2 + i) * 6
            pygame.draw.circle(s, (255, 140, 50), (int(wx), r.bottom - 26), 4)

    def b_comms(self, s, r, lv, col, night, t, dim):
        c = (r.centerx, r.centery + 10)
        pygame.draw.circle(s, (70, 70, 90), c, 22)
        a = t * 0.5
        dw = r.w * 0.85
        dh = r.h * 0.42 * (0.4 + 0.6 * abs(math.cos(a)))
        dish = pygame.Rect(0, 0, int(dw), int(dh))
        dish.center = (c[0], c[1] - 24)
        pygame.draw.ellipse(s, (220, 225, 240), dish)
        pygame.draw.ellipse(s, (140, 150, 180), dish, 3)
        pygame.draw.ellipse(s, (180, 190, 210), dish.inflate(-dish.w * 0.4, -dish.h * 0.4), 1)
        tip = (dish.centerx + math.sin(a) * 30, dish.centery - 40)
        pygame.draw.line(s, (200, 200, 210), dish.center, tip, 2)
        draw_glow(s, tip, 18, col, 0.8)
        for i in range(lv):
            rr = int(20 + ((t * 40 + i * 30) % 90))
            pygame.draw.circle(s, scale_color(col, 1 - rr / 110), (int(tip[0]), int(tip[1])), rr, 1)

    def b_medical(self, s, r, lv, col, night, t, dim):
        self._roof(s, r, (230, 232, 240), dim)
        cr = 18
        pygame.draw.rect(s, (230, 40, 60), (r.centerx - 6, r.centery - cr, 12, cr * 2))
        pygame.draw.rect(s, (230, 40, 60), (r.centerx - cr, r.centery - 6, cr * 2, 12))
        if night > 0.4:
            draw_glow(s, r.center, 40, (255, 60, 80), 0.5)
        sick = [c for c in self.game.s["crew"] if c["status"] == "sick"]
        for i, c in enumerate(sick[:3]):
            pygame.draw.rect(s, (200, 210, 230), (r.x + 12 + i * 26, r.bottom - 24, 22, 12), border_radius=3)
            pygame.draw.circle(s, (240, 200, 180), (r.x + 18 + i * 26, r.bottom - 18), 4)

    def b_rec(self, s, r, lv, col, night, t, dim):
        pygame.draw.rect(s, (40, 110, 60) if night < 0.5 else (20, 60, 36), r, border_radius=14)
        rng = random.Random(8)
        for i in range(9):
            tx = r.x + 16 + rng.random() * (r.w - 32)
            ty = r.y + 16 + rng.random() * (r.h - 32)
            pygame.draw.circle(s, (30, 90, 45), (int(tx), int(ty)), 12)
            pygame.draw.circle(s, (60, 150, 80), (int(tx - 3), int(ty - 3)), 7)
        pool = pygame.Rect(r.x + r.w * 0.55, r.y + 14, r.w * 0.36, r.h * 0.34)
        pygame.draw.rect(s, (60, 170, 230), pool, border_radius=8)
        pygame.draw.line(s, (180, 230, 255), (pool.x + 6, pool.centery + math.sin(t * 2) * 3),
                         (pool.right - 6, pool.centery - math.sin(t * 2) * 3), 2)
        screen = pygame.Rect(r.x + 14, r.bottom - 40, r.w * 0.4, 26)
        pygame.draw.rect(s, (10, 10, 20), screen)
        if lv >= 1:
            hue = (math.sin(t) * 0.5 + 0.5)
            pygame.draw.rect(s, lerp_color((255, 70, 200), (62, 230, 255), hue), screen.inflate(-6, -6))
            if night > 0.4:
                draw_glow(s, screen.center, 40, (255, 120, 220), 0.4)
        rest = [c for c in self.game.s["crew"] if c["status"] == "resting"]
        for i, c in enumerate(rest[:3]):
            art.draw_astronaut(s, r.x + 40 + i * 30, r.centery, c["type"], 0.4, t)

    # ------------------------------------------------------------------ ekran
    def draw_overlay(self, surf):
        g = self.game
        # NOVA tavsiye kartı
        if self.advisor:
            title, text, target = self.advisor
            r = pygame.Rect(24, TOPBAR_H + 14, 420, 146)
            glass_panel(surf, r, C["cyan"], 190, 16)
            draw_icon(surf, "nova", (r.x + 26, r.y + 26), 22, C["cyan"])
            draw_text(surf, "NOVA ÖNERİSİ · " + title.upper(), (r.x + 46, r.y + 15), 13, C["cyan"], bold=True)
            draw_paragraph(surf, text, (r.x + 18, r.y + 42), r.w - 36, 15, C["text"], max_lines=3)
            self.adv_button.rect.topleft = (r.right - 136, r.bottom - 44)
        # hızlı durum: zafer yolu
        steps = g.victory_progress()
        done = sum(1 for _, ok in steps if ok)
        r2 = pygame.Rect(24, TOPBAR_H + 174, 420, 42)
        glass_panel(surf, r2, C["gold"], 170, 12, glow=False)
        draw_text(surf, "HEDEF: JÜPİTER'DE DEV KOLONİ", (r2.x + 14, r2.y + 6), 12, C["gold"], bold=True)
        for i, (lab, ok) in enumerate(steps):
            x = r2.x + 18 + i * 66
            pygame.draw.circle(surf, C["gold"] if ok else (60, 70, 90), (x, r2.y + 30), 6)
            if i < len(steps) - 1:
                pygame.draw.line(surf, C["gold"] if ok else (60, 70, 90), (x + 7, r2.y + 30), (x + 59, r2.y + 30), 2)
            if pygame.Rect(x - 10, r2.y + 20, 20, 20).collidepoint(UI.mouse):
                UI.set_tooltip(lab + (" (tamam)" if ok else ""), C["gold"])
        draw_text(surf, f"{done}/{len(steps)}", (r2.right - 14, r2.y + 6), 12, C["text"], bold=True, anchor="topright")
        self.draw_widgets(surf)
        if self.panel_k.value > 0.02 and self.selected:
            self.draw_panel(surf)

    def draw_panel(self, surf):
        g = self.game
        key = self.selected
        b = D.BUILDING[key]
        pr = self.panel_rect()
        dx = pr.x - (W - 560)
        glass_panel(surf, pr, b["color"], 225, 20, strong=True)
        draw_glow(surf, (pr.x + 50, pr.y + 50), 50, b["color"], 0.6)
        draw_icon(surf, b["icon"], (pr.x + 50, pr.y + 50), 34, b["color"])
        draw_text(surf, b["name"], (pr.x + 90, pr.y + 24), 24, C["text"], bold=True)
        lv = g.lvl(key)
        draw_text(surf, f"SEVİYE {lv} / {b['max']}", (pr.x + 90, pr.y + 56), 14, b["color"], bold=True)
        for i in range(b["max"]):
            cc = b["color"] if i < lv else (50, 60, 80)
            pygame.draw.rect(surf, cc, (pr.x + 200 + i * 30, pr.y + 60, 24, 8), border_radius=4)
        draw_paragraph(surf, b["desc"], (pr.x + 26, pr.y + 96), pr.w - 52, 16, C["text_dim"], max_lines=3)
        y = pr.y + 168
        if key != "pads":
            for l in range(0 if 0 in b["levels"] else 1, b["max"] + 1):
                txt = b["levels"].get(l)
                if not txt:
                    continue
                cur = (l == lv)
                rr = pygame.Rect(pr.x + 24, y, pr.w - 48, 34)
                if cur:
                    pygame.draw.rect(surf, scale_color(b["color"], 0.25), rr, border_radius=8)
                    pygame.draw.rect(surf, b["color"], rr, 1, border_radius=8)
                draw_text(surf, f"Sv{l}", (rr.x + 12, rr.centery), 14, b["color"] if l <= lv else C["text_mute"],
                          bold=True, anchor="midleft")
                draw_text(surf, txt, (rr.x + 60, rr.centery), 15, C["text"] if l <= lv else C["text_mute"],
                          anchor="midleft")
                y += 40
            self.draw_extra(surf, key, pr, y)
        else:
            self.draw_pad_slots(surf, pr)
        for bt in self.panel_buttons:
            if dx:
                bt.rect.x += dx
            bt.draw(surf)
            if dx:
                bt.rect.x -= dx

    def draw_extra(self, surf, key, pr, y):
        g = self.game
        y += 8
        x = pr.x + 26
        w = pr.w - 52
        if key == "research":
            ap = g.research_progress()
            if ap:
                k, frac, left = ap
                draw_text(surf, f"Aktif: {D.RESEARCH_BY_KEY[k]['name']}", (x, y), 15, C["text"], bold=True)
                draw_bar(surf, (x, y + 26, w, 10), frac, C["cyan"], value=fmt_time(left))
            else:
                draw_text(surf, "Laboratuvar boşta.", (x, y), 15, C["text_dim"])
            draw_text(surf, f"Süre: {int(g.research_duration())} sn · İndirim: %{int(D.RESEARCH_DISCOUNT[g.lvl('research')] * 100)}",
                      (x, y + 50), 14, C["text_dim"])
        elif key == "astro":
            draw_text(surf, f"Kadro: {len(g.s['crew'])}/{g.crew_cap()}", (x, y), 16, C["text"], bold=True)
            for i, c in enumerate(g.s["crew"][:8]):
                art.draw_astronaut(surf, x + 20 + i * 52, y + 70, c["type"], 0.75, self.t, c["tired"], c["status"] == "sick")
        elif key == "depot":
            draw_bar(surf, (x, y + 20, w, 12), g.depot_used() / g.depot_cap(), C["gold"], label="DOLULUK",
                     value=f"{g.depot_used()}/{g.depot_cap()}")
        elif key == "fuel":
            draw_bar(surf, (x, y + 20, w, 12), g.s["fuel"] / g.fuel_cap(), C["orange"], label="TANK",
                     value=f"{int(g.s['fuel'])}/{g.fuel_cap()} kg")
            draw_text(surf, f"Üretim: saatte {g.fuel_rate()} kg (bedava) · Market: 4 Para/kg", (x, y + 44), 14, C["text_dim"])
        elif key == "comms":
            draw_text(surf, f"Mevcut menzil: {D.RANGE_NAME[g.comms_range()]}", (x, y), 17, C["text"], bold=True)
            draw_paragraph(surf, "Roket anteni ve kule menzili birlikte yetmezse bağlantı kopar: veriler gelmez, "
                                 "NOVA yolda sana yardım edemez.", (x, y + 30), w, 14, C["text_dim"])
        elif key == "nova":
            draw_paragraph(surf, self.app.nova.forecast(), (x, y), w, 15, C["cyan"])
        elif key == "control":
            h = g.s["history"][:3]
            for i, m in enumerate(h):
                col = {"success": C["green"], "partial": C["gold"], "fail": C["red"]}[m["outcome"]]
                draw_text(surf, f"Gün {m['day']} · {D.PLANET[m['planet']]['name']}", (x, y + i * 26), 15, C["text"])
                draw_text(surf, {"success": "BAŞARILI", "partial": "KISMİ", "fail": "BAŞARISIZ"}[m["outcome"]],
                          (x + w, y + i * 26), 14, col, bold=True, anchor="topright")
        elif key == "medical":
            sick = [c for c in g.s["crew"] if c["status"] == "sick"]
            draw_text(surf, f"Hasta: {len(sick)}", (x, y), 16, C["text"], bold=True)
        elif key == "rec":
            rest = [c for c in g.s["crew"] if c["status"] == "resting"]
            tired = [c for c in g.s["crew"] if c["tired"] and c["status"] == "ready"]
            draw_text(surf, f"Dinlenen: {len(rest)} · Yorgun: {len(tired)}", (x, y), 16, C["text"], bold=True)
        elif key == "board":
            draw_text(surf, f"Alınmamış ödül: {g.unclaimed_quests()}", (x, y), 16, C["lime"], bold=True)

    def draw_pad_slots(self, surf, pr):
        g = self.game
        draw_text(surf, "RAMPALAR", (pr.x + 26, pr.y + 176), 15, C["orange"], bold=True)
        draw_paragraph(surf, "Hangarda 'RAMPAYA HAZIRLA' ile aynı anda 3 roket hazırlayabilirsin.",
                       (pr.x + 26, pr.y + 200), pr.w - 52, 14, C["text_dim"])
        for i in range(3):
            r = pygame.Rect(pr.x + 24, pr.y + 300 + i * 92, pr.w - 48, 80)
            open_ = g.lvl("pads") >= i + 1
            pad = g.s["pads"][i]
            col = C["green"] if pad and pad["prep"] <= 0 else C["orange"] if pad else (90, 100, 125)
            glass_panel(surf, r, col, 150, 12, glow=False)
            draw_text(surf, f"{D.PAD_NAME[i + 1]} · {D.ROCKET_SIZE_NAME[i + 1]} roket", (r.x + 16, r.y + 10), 16,
                      C["text"] if open_ else C["text_mute"], bold=True)
            if not open_:
                draw_text(surf, f"Kilitli · Rampa Sv{i + 1} gerekli", (r.x + 16, r.y + 40), 14, C["text_mute"])
            elif pad:
                d = pad["design"]
                draw_text(surf, f"Hedef: {D.PLANET[d['planet']]['name']} · {D.PART['hull'][d['hull']]['name']}",
                          (r.x + 16, r.y + 36), 14, C["text_dim"])
                if pad["prep"] > 0:
                    draw_bar(surf, (r.x + 16, r.y + 62, 200, 6), 1 - pad["prep"] / D.PAD_PREP_SEC[i + 1], C["orange"],
                             glow=False)
                    draw_text(surf, f"Hazırlanıyor {int(pad['prep']) + 1} sn", (r.x + 226, r.y + 54), 13, C["orange"])
            else:
                draw_text(surf, "Boş", (r.x + 16, r.y + 40), 14, C["text_dim"])

# -*- coding: utf-8 -*-
"""
GEZEGENLER VE KOLONİLER
Koloni 3 bina ile başlar: Ev, Maden, Araştırma Kulübesi.
Mutluluk: mutluysa daha çok maden toplar; düşerse çalışmazlar.
Artırmak için: Yemek, Film Gecesi, Spor Salonu.
Seviye büyüdükçe: Hastane, Okul, Park.
Koloniler arası ticaret: Ay Mars'a maden, Mars Ay'a yemek gönderir.
"""
import math
import random

import numpy as np
import pygame

from . import Scene
from .. import paint
from ..colony3d import Colony3D
from .. import space3d as S3
from .. import i18n
from .. import art
from .. import npc
from ..i18n import tr
from .. import data as D
from ..config import C, CREW_COLORS, H, TOPBAR_H, W
from ..fx import DustStorm, ParticleSystem, draw_glow, lerp_color, scale_color, vertical_gradient, clamp
from ..ui import UI, Button, Tabs, chip, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, fmt_num

GROUND = 600


class ColonyScene(Scene):
    music = "colony"
    ambient = "amb_colony"
    title = "KOLONİLER"
    title_icon = "flag"
    accent = C["green"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("deep", 44, 0.7)
        self.idx = 0
        self.ps = ParticleSystem(800)
        self.walkers = []
        self.sky = {}
        self.dust = DustStorm((40, TOPBAR_H + 160, 940, 500), 7)
        self.world = Colony3D(self)          # 3B koloni görünümü (görsel katman, oyun mantığından ayrı)
        self.view3d = True

    def enter(self, planet=None, **kw):
        g = self.game
        if planet in D.PLANET_ORDER:
            self.idx = D.PLANET_ORDER.index(planet)
        else:
            for i, p in enumerate(D.PLANET_ORDER):
                if g.colony(p):
                    self.idx = i
                    break
        self.reset_walkers()
        self.setup_world()
        self.rebuild()

    def setup_world(self):
        c = self.game.colony(self.planet)
        if c:
            self.world.setup(self.planet, c, self.game)

    @property
    def planet(self):
        return D.PLANET_ORDER[self.idx]

    def set_idx(self, i):
        self.idx = i
        self.world.place = None
        self.reset_walkers()
        self.setup_world()
        self.rebuild()

    def toggle_view(self):
        self.view3d = not self.view3d
        self.world.place = None
        self.app.audio.play("tick")
        self.rebuild()

    def handle(self, e):
        if super().handle(e):
            return True
        if self.view3d and self.game.colony(self.planet):
            return self.world.handle(e, pygame.Rect(40, TOPBAR_H + 160, 940, 500))
        return False

    def reset_walkers(self):
        c = self.game.colony(self.planet)
        self.walkers = []
        if not c:
            return
        n = min(14, int(c["pop"]))
        roles = list(CREW_COLORS.keys())
        for i in range(n):
            p = npc.Persona(sum(map(ord, self.planet)) * 131 + i * 7919, roles[i % len(roles)])
            # [x, hız, kişi, iş pozu, iş süresi sayacı]: çalış -> yürü -> çalış döngüsü
            self.walkers.append([random.uniform(80, 940), random.choice([-1, 1]) * random.uniform(14, 34) * p.speed_k, p,
                                 npc.ROLE_WORK.get(p.role, "scan"), random.uniform(0, 6)])

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.back_button()
        labels = []
        for p in D.PLANET_ORDER:
            c = g.colony(p)
            labels.append(D.PLANET[p]["name"].upper() + (f" · SV{c['level']}" if c else ""))
        self.add(Tabs((40, TOPBAR_H + 100, 900, 46), labels, self.set_idx, C["green"], self.idx,
                      ["flag" if g.colony(p) else "planet" for p in D.PLANET_ORDER]))
        c = g.colony(self.planet)
        px = W - 600
        if not c:
            b = self.add(Button((px + 40, TOPBAR_H + 566, 480, 60), f"{D.TO[self.planet].upper()} İNİŞ GÖREVİ TASARLA",
                                self.plan_landing, accent=C["orange"], icon="rocket", size=17, style="big"))
            if not g.planet_unlocked(self.planet):
                b.set_enabled(False, g.req_text(D.PLANET[self.planet]["unlock"]))
            return
        vb = self.add(Button((480, H - 140, 230, 50), "2B GÖRÜNÜM" if self.view3d else "3B GÖRÜNÜM", self.toggle_view,
                             accent=C["violet"], icon="planet", size=14))
        vb.selected = self.view3d
        y = TOPBAR_H + 360
        for i, b in enumerate(D.COLONY_BUILDINGS):
            col, row = i % 2, i // 2
            r = (px + 20 + col * 280, y + row * 62, 270, 54)
            cost = g.colony_build_cost(self.planet, b["key"])
            n = c["buildings"][b["key"]]
            bt = self.add(Button(r, f"{b['name']} ({n}) · {fmt_num(cost)}", (lambda k=b["key"]: self.build(k)),
                                 accent=C["green"], icon=b["icon"], size=13, tooltip=b["desc"]))
            if c["level"] < b["level_req"]:
                bt.set_enabled(False, f"Koloni Seviye {b['level_req']} gerekli")
            elif g.money < cost:
                bt.set_enabled(False, f"{cost} Para gerekli")
        ay = y + 4 * 62 + 10
        for i, a in enumerate(D.COLONY_ACTIONS):
            cost = int(a["cost"] * D.COLONY_PLANET_MULT[self.planet])
            bt = self.add(Button((px + 20 + i * 280, ay, 270, 50), f"{a['name']} · {cost}",
                                 (lambda k=a["key"]: self.action(k)), accent=C["pink"], icon=a["icon"], size=14,
                                 tooltip=a["desc"]))
            bt.set_enabled(g.money >= cost, f"{cost} Para gerekli")
        if c["level"] < 3:
            need = D.COLONY_LEVEL_POP[c["level"] + 1]
            cost = g.colony_level_cost(self.planet)
            lb = self.add(Button((px + 20, TOPBAR_H + 290, 550, 56), f"KOLONİ SEVİYE {c['level'] + 1} · {fmt_num(cost)} P "
                                                                     f"(nüfus {need})", self.level_up, accent=C["gold"],
                                 icon="star", size=15, style="big"))
            ok = c["pop"] >= need and g.money >= cost
            lb.set_enabled(ok, f"Nüfus {need} olmalı" if c["pop"] < need else f"{cost} Para gerekli")
            lb.pulse = ok
        if self.planet in ("moon", "mars"):
            on = g.s["trade"]
            tb = self.add(Button((40, H - 140, 420, 50),
                                 "TİCARET YOLU: AÇIK" if on else "AY <-> MARS TİCARETİ BAŞLAT", self.trade,
                                 accent=C["cyan"] if on else C["text_dim"], icon="handshake", size=14,
                                 tooltip="Ay Mars'a maden (inşaat -%15), Mars Ay'a yemek gönderir"))
            tb.selected = on
            if not (g.colony("moon") and g.colony("mars")):
                tb.set_enabled(False, "Ay ve Mars kolonisi gerekli")

    def plan_landing(self):
        self.app.go("hangar", planet=self.planet, mode="inis")

    def build(self, k):
        if self.view3d and self.game.colony(self.planet):
            c = self.game.colony(self.planet)
            b = D.COLONY_BUILDING[k]
            cost = self.game.colony_build_cost(self.planet, k)
            if c["level"] < b["level_req"] or self.game.money < cost:
                self.act(self.game.colony_build, self.planet, k)      # oyunun kendi uyarısı
                self.rebuild()
                return
            self.world.start_place(k)                                # 3B: önce yerleştirme önizlemesi
            self.app.audio.play("tick")
            return
        if self.act(self.game.colony_build, self.planet, k, ok_sound="clunk"):
            for i in range(20):
                self.ps.sparks(random.uniform(100, 900), GROUND - 30, 3, C["gold"])
        self.rebuild()

    def action(self, k):
        if self.act(self.game.colony_action, self.planet, k, ok_sound="pickup"):
            if k == "movie":
                self.ps.glow(500, GROUND - 120, 40, C["magenta"], speed=(40, 160))
            else:
                self.ps.glow(500, GROUND - 60, 30, C["gold"], speed=(40, 160))
        self.rebuild()

    def level_up(self):
        if self.act(self.game.colony_level_up, self.planet, ok_sound="levelup"):
            self.app.say(f"{self.game.name}, {D.PLANET[self.planet]['name']} kolonisi büyüyor! Yeni binalar açıldı.", "happy")
            self.reset_walkers()
        self.rebuild()

    def trade(self):
        self.act(self.game.toggle_trade)
        self.rebuild()

    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        c0 = self.game.colony(self.planet)
        if c0 and self.view3d:
            if self.world.colony is not c0:
                self.setup_world()
            if sum(c0["buildings"].values()) != len(c0.get("layout3d", [])):
                self.world.sync_layout()
            if max(1, min(12, int(c0["pop"]))) != len(self.world.agents):
                self.world.spawn_agents()
            self.world.update(dt, pygame.Rect(40, TOPBAR_H + 160, 940, 500))
        if self.planet == "mars":
            self.dust.update(dt)
        c = self.game.colony(self.planet)
        for w in self.walkers:
            w[4] -= dt
            if w[4] < -6 * w[2].work_k:                       # iş bitti: yeniden yürü
                w[4] = random.uniform(4, 9)
            if w[4] > 0:                                      # yürüyor
                w[0] += w[1] * dt
                if w[0] < 60 or w[0] > 960:
                    w[1] *= -1
        sig = (self.game.money // 50, c and (int(c["pop"]), c["level"], int(c["happiness"])))
        if getattr(self, "_sig", None) != sig:
            self._sig = sig
            self.rebuild()

    # ----------------------------------------------------------------- çizim
    def draw(self, surf):
        g = self.game
        p = D.PLANET[self.planet]
        c = g.colony(self.planet)
        self.bg.draw(surf, 0.7)
        if c:
            self.draw_colony(surf, p, c)
        else:
            self.draw_empty(surf, p)
        self.draw_title(surf, sub=f"{g.colony_count()} koloni · Bayraklarda {g.name} yazıyor")
        self.draw_widgets(surf)
        self.ps.draw(surf)

    def draw_empty(self, surf, p):
        g = self.game
        # henüz koloni yok: hedefin boyalı manzarası + üstünde ışıklı 3B gezegen
        scene = pygame.Rect(40, TOPBAR_H + 160, 940, 500)
        view = paint.get(self.planet, scene.size).copy()
        view.fill((150, 150, 158, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(view, scene.topleft)
        pygame.draw.rect(surf, scale_color(p["glow"], 0.7), scene, 1, border_radius=4)
        img = self.__dict__.setdefault("_p3d", {}).get(self.planet)
        if img is None:
            M = S3.rot_z(math.radians(-14)) @ S3.rot_x(0.3)
            L = S3.norm3(np.array((-0.6, 0.35, 0.72), dtype=np.float32))
            img = S3.to_surface(S3.render_body(self.planet, 200, M, L, 0.7, 0.0, 1024))
            self._p3d[self.planet] = img
        surf.blit(img, (scene.centerx - img.get_width() // 2, scene.centery - img.get_height() // 2))
        r = pygame.Rect(W - 600, TOPBAR_H + 160, 560, 380)
        glass_panel(surf, r, p["glow"], 200, 18)
        draw_text(surf, p["name"].upper(), (r.x + 24, r.y + 20), 32, C["text"], bold=True, glow=p["glow"])
        rows = [("Uzaklık", p["distance"]), ("Zorluk", p["difficulty"]), ("Maden", D.MINERAL[p["mineral"]]["name"]),
                ("Özel", p["special"]), ("Yerçekimi", p["gravity"]),
                ("Koloni kurma", f"{fmt_num(p['colony_cost'])} Para")]
        for i, (a, b) in enumerate(rows):
            draw_text(surf, a, (r.x + 24, r.y + 80 + i * 32), 15, C["text_dim"])
            draw_text(surf, b, (r.right - 24, r.y + 80 + i * 32), 15, C["text"], bold=True, anchor="topright")
        draw_paragraph(surf, "Koloni kurmak için gezegene iniş yap. İnişten sonra sonuç ekranında 'KOLONİ KUR' çıkar. "
                             "İstasyon Modülü ile 'Koloni Seferi' yaparsan kurulum %50 indirimli.",
                       (r.x + 24, r.bottom - 74), r.w - 48, 13, C["text_mute"])

    def draw_colony(self, surf, p, c):
        g = self.game
        t = self.t
        # gökyüzü + zemin sahnesi
        scene = pygame.Rect(40, TOPBAR_H + 160, 940, 500)
        old = surf.get_clip()
        surf.set_clip(scene)
        if self.view3d:
            self.world.draw(surf, scene, paint.get(self.planet, scene.size))
            self.draw_overlays(surf, scene, p, c, old)
            return
        surf.blit(paint.get(self.planet, scene.size), scene.topleft)   # boyalı fotogerçekçi manzara
        gy = GROUND
        # binalar
        b = c["buildings"]
        order = [("house", (230, 232, 240)), ("mine", (180, 140, 90)), ("hut", (120, 200, 255)),
                 ("gym", (255, 140, 170)), ("hospital", (255, 255, 255)), ("school", (255, 206, 84)), ("park", (70, 220, 120))]
        x = scene.x + 40
        for k, col in order:
            for j in range(min(3, b[k])):
                self.draw_dome(surf, x, gy, k, col, t)
                x += 108
                if x > scene.right - 140:
                    break
        art.draw_flag(surf, scene.right - 120, gy, g.name, g.color, t, 1.0)
        # sakinler
        for wx, vx, per, job, tm in self.walkers:
            pose = "walk" if tm > 0 else job
            npc.draw_person(surf, scene.x + wx * scene.w / 1000, gy + 30, 1.25, per, self.planet, pose, t, 1 if vx > 0 else -1, "astro")
        self.draw_overlays(surf, scene, p, c, old)

    def draw_overlays(self, surf, scene, p, c, old):
        g = self.game
        if self.planet == "mars":
            self.dust.draw(surf)
            if self.dust.intensity() > 0.3:
                draw_text(surf, "TOZ FIRTINASI", (scene.right - 20, scene.y + 16), 16, C["orange"], bold=True,
                          anchor="topright")
        # mutluluk tonu
        if c["happiness"] < 30:
            ov = pygame.Surface(scene.size, pygame.SRCALPHA)
            ov.fill((255, 40, 60, 40))
            surf.blit(ov, scene.topleft)
        surf.set_clip(old)
        glass_panel(surf, scene, p["glow"], 0, 18, glow=True)
        if self.view3d:
            wd = self.world
            draw_text(surf, "WASD: kaydır · Q/E: döndür · Orta/sağ tık sürükle: yörünge · Tekerlek: yakınlaş · Tık: seç · F: odakla",
                      (scene.centerx, scene.bottom + 6), 12, C["text_dim"], anchor="midtop", max_w=scene.w)
            if wd.place:
                bn = pygame.Rect(scene.x + 20, scene.y + 14, scene.w - 40, 56)
                glass_panel(surf, bn, C["green"] if wd.place.get("valid") else C["red"], 230, 12)
                draw_text(surf, f"YERLEŞTİR: {D.COLONY_BUILDING[wd.place['key']]['name']}", (bn.x + 16, bn.y + 8), 16,
                          C["white"], bold=True)
                draw_text(surf, "Sol tık: yerleştir · R: 90° döndür · Sağ tık / ESC: iptal", (bn.x + 16, bn.y + 32), 12,
                          C["text_dim"])
                if wd.place.get("cell") and not wd.place.get("valid"):
                    draw_text(surf, "Geçersiz konum", (bn.right - 16, bn.y + 18), 15, C["red"], bold=True, anchor="topright")
            elif wd.cam.follow is not None:
                fa = wd.cam.follow
                role = D.CREW_TYPE.get(fa.role, {}).get("name", fa.role)
                draw_text(surf, tr("Takip ediliyor") + f": {tr(role)} · {fa.label()}", (scene.x + 20, scene.y + 16), 14, C["gold"],
                          bold=True, raw=True, max_w=scene.w - 40)
            if wd.lighting()[4] < 0.25:
                draw_text(surf, "Gece: kolonistler uyuyor", (scene.right - 20, scene.y + 40), 13, C["cyan"], bold=True,
                          anchor="topright")
        # sağ panel
        r = pygame.Rect(W - 600, TOPBAR_H + 160, 560, 120)
        glass_panel(surf, r, C["green"], 200, 16)
        draw_text(surf, f"{p['name'].upper()} KOLONİSİ · SEVİYE {c['level']}", (r.x + 20, r.y + 12), 18, C["text"], bold=True)
        cap = g.colony_capacity(c)
        rates = g.colony_rates(c)
        draw_bar(surf, (r.x + 20, r.y + 60, 250, 10), c["pop"] / max(1, cap), C["cyan"], label="NÜFUS",
                 value=f"{int(c['pop'])}/{cap}", size=12)
        hc = C["green"] if c["happiness"] > 60 else C["gold"] if c["happiness"] > 30 else C["red"]
        draw_bar(surf, (r.x + 290, r.y + 60, 250, 10), c["happiness"] / 100, hc, label="MUTLULUK",
                 value=i18n.pct(c['happiness']), size=12, warn_below=0.3)
        draw_bar(surf, (r.x + 20, r.y + 98, 250, 8), c["food"] / 200, C["orange"], label=None, glow=False)
        draw_text(surf, f"Yemek {int(c['food'])} ({rates['food']:+.1f}/sa)", (r.x + 20, r.y + 80), 11, C["text_dim"])
        scap = g.colony_storage_cap(c)
        draw_bar(surf, (r.x + 290, r.y + 98, 250, 8), c["storage"] / scap, C["gold"], glow=False)
        draw_text(surf, f"{D.MINERAL[p['mineral']]['name']} deposu {int(c['storage'])}/{scap} (+{rates['mine']:.1f}/sa)",
                  (r.x + 290, r.y + 80), 11, C["text_dim"])
        wf = g.colony_work_factor(c)
        if wf == 0:
            draw_text(surf, "Mutluluk çok düşük: koloni ÇALIŞMIYOR!", (scene.x + 20, scene.y + 16), 18, C["red"], bold=True)
        draw_text(surf, f"Araştırma: +{rates['rp']:.1f} Puan/sa · Verim ×{wf:.2f}", (scene.x + 20, scene.bottom - 30),
                  14, C["text"], bold=True)
        draw_text(surf, "Maden, bu gezegene iniş yapan roketle Dünya'ya getirilir.", (W - 580, TOPBAR_H + 360 + 4 * 62 + 70),
                  12, C["text_mute"])

    def draw_dome(self, surf, x, gy, kind, col, t):
        w, h = 92, 64
        r = pygame.Rect(x, gy - h + 8, w, h)
        pygame.draw.ellipse(surf, scale_color(col, 0.55), r)
        inner = r.inflate(-10, -10)
        pygame.draw.ellipse(surf, scale_color(col, 0.9), inner, 0)
        pygame.draw.ellipse(surf, (255, 255, 255), (r.x + 18, r.y + 10, 26, 10))
        pygame.draw.rect(surf, scale_color(col, 0.4), (x, gy - 2, w, 10))
        icon = D.COLONY_BUILDING[kind]["icon"]
        draw_icon(surf, icon, (r.centerx, r.centery + 6), 22, (20, 30, 50))
        if kind == "mine":
            a = t * 3
            pygame.draw.line(surf, (90, 70, 40), (r.right - 10, gy - 20), (r.right + 10, gy - 20 - math.sin(a) * 10), 4)
        if kind == "hut":
            draw_glow(surf, (r.centerx, r.y), 18, (120, 220, 255), 0.6 + 0.3 * math.sin(t * 3))

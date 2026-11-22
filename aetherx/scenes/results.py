# -*- coding: utf-8 -*-
"""
GEZEGENE İNİŞ / KOLONİ KUR / DÜNYA'YA DÖNÜŞ / GÖREV SONUCU
"""
import math
import random

import pygame

from . import Scene
from .. import cinema
from .. import paint
from .. import art
from .. import data as D
from ..config import C, H, W
from ..fx import DustStorm, ParticleSystem, Shake, SpaceBackground, clamp, draw_glow, ease_out_back, ease_out_cubic, scale_color
from ..ui import UI, Button, chip, draw_icon, draw_text, glass_panel, fmt_num


class ResultsScene(Scene):
    music = "colony"
    ambient = "amb_colony"
    show_topbar = False
    allow_events = False

    def __init__(self, app):
        super().__init__(app)
        self.ps = ParticleSystem(1600)
        self.shake = Shake()
        self.space = SpaceBackground("deep", 81, 360, 0.8)
        self.dust = DustStorm((0, 0, W, H), 11, 60)

    def enter(self, **kw):
        m = self.app.mission
        res = m["result"]
        g = self.game
        self.res = res
        self.design = m["design"]
        self.planet = res["planet"]
        self.pl = D.PLANET[self.planet]
        self.hull = D.PART["hull"][self.design["hull"]]
        roles = g.crew_roles(res["crew"])
        self.surface_minerals = 0
        self.pickup = 0
        # yüzey madenciliği + koloni deposu
        if res["landed"]:
            base = int(self.hull["cargo"] * 0.55 * (1.5 if "miner" in roles else 1.0) * g.mining_mult())
            base = max(3, base)
            self.surface_minerals = base
            mk = self.pl["mineral"]
            res["minerals"][mk] = res["minerals"].get(mk, 0) + base
            left = self.hull["cargo"] * 2 - base
            if g.colony(self.planet) and left > 0:
                self.pickup = g.pickup_colony_storage(self.planet, left)
                res["minerals"][mk] += self.pickup
        self.supplied = False
        if res["landed"] and res["mode"] == "koloni" and g.colony(self.planet):
            self.supplied = g.supply_colony(self.planet, len(res["crew"]))
        self.summary = g.complete_mission(res)
        self.phase = "landing" if res["landed"] else ("return" if res["outcome"] != "fail" or res["crew"] else "summary")
        self.phase_t = 0.0
        if self.phase == "landing" and res.get("touchdown"):
            self.phase_t = 3.6       # iniş oyuncu tarafından zaten yapıldı: yalnız yüzey sahnesinin sonu gösterilir
        self.ps.clear()
        self.widgets = []
        self.colony_btn = None
        self.k = 0.0
        out = res["outcome"]
        self.app.audio.music("colony" if out == "success" else "base")
        self.app.say(self.app.nova.celebrate(self.planet, out, self.summary["first_visit"] or self.summary["first_landing"]),
                     "happy" if out == "success" else "alert" if out == "fail" else "calm")
        if self.phase == "summary":          # doğrudan özet ekranıyla açılırsa (mürettebatsız başarısızlık) düğmeler de gelsin
            self.build_buttons()

    def build_buttons(self):
        self.widgets = []
        g = self.game
        y = H - 110
        self.add(Button((W // 2 - 380, y, 240, 58), "ÜSSE DÖN", lambda: self.app.go("base"), accent=C["cyan"],
                        icon="home", size=17, hotkey=pygame.K_RETURN))
        self.add(Button((W // 2 - 120, y, 240, 58), "YENİ GÖREV", lambda: self.app.go("hangar"), accent=C["orange"],
                        icon="rocket", size=17))
        self.add(Button((W // 2 + 140, y, 240, 58), "DEPOYA GİT", lambda: self.app.go("depot"), accent=C["gold"],
                        icon="box", size=17))
        if self.summary["can_found"] and not g.colony(self.planet):
            disc = 0.5 if self.res["mode"] == "koloni" else 0.0
            cost = g.colony_found_cost(self.planet, disc)
            b = self.add(Button((W // 2 - 260, y - 82, 520, 66), f"{D.AT[self.planet].upper()} KOLONİ KUR · {fmt_num(cost)} P",
                                lambda: self.found(disc), accent=C["green"], icon="flag", size=19, style="big"))
            b.pulse = g.money >= cost
            b.set_enabled(g.money >= cost, f"{cost} Para gerekli")
            self.colony_btn = b

    def found(self, disc):
        if self.act(self.game.found_colony, self.planet, disc, ok_sound="success"):
            self.app.say(f"{self.game.name}, {D.AT[self.planet]} ilk koloni kuruldu! Bayrağımız dalgalanıyor. "
                         f"Ev, Maden ve Araştırma Kulübesi hazır.", "happy")
            for i in range(5):
                self.ps.sparks(W // 2 + random.uniform(-300, 300), H // 2, 20, C["green"])
            self.build_buttons()

    def rebuild(self):
        if self.phase == "summary":
            self.build_buttons()

    # ---------------------------------------------------------------- döngü
    def update(self, dt):
        super().update(dt)
        self.phase_t += dt
        self.space.update(dt)
        if self.planet == "mars":
            self.dust.update(dt)
        self.ps.update(dt)
        self.shake.update(dt)
        if self.phase == "landing":
            k = self.phase_t / 4.2
            cx = W // 2
            cy = self.craft_y()
            if k < 0.9:
                self.ps.fire(cx, cy + 60, 4, math.pi / 2, 0.25, (160, 300), (6, 14), (0.15, 0.35), "blue")
            if 0.82 < k < 1.0:
                gy = H - 170
                for side in (-1, 1):
                    self.ps.smoke(cx + side * 30, gy, 3, angle=(0 if side > 0 else math.pi), spread=0.3,
                                  speed=(100, 260), size=(14, 30), life=(1.2, 2.4),
                                  color=scale_color(self.pl["color"], 0.9), alpha=150, grow=40, grav=-5)
                self.shake.set_min(0.2)
            if k >= 1.6:
                self.next_phase()
        elif self.phase == "return":
            if self.phase_t < 2.6:
                x, y = self.reentry_pos()
                self.ps.fire(x, y, 6, -2.4, 0.4, (100, 260), (10, 22), (0.2, 0.5), "fire")
                self.shake.set_min(0.12)
            if self.phase_t >= 3.2:
                self.next_phase()
        else:
            self.k = min(1.0, self.k + dt * 1.6)

    def next_phase(self):
        if self.phase == "landing":
            self.phase = "return"
            self.phase_t = 0
            self.ps.clear()
            self.app.audio.play("whoosh")
        else:
            self.phase = "summary"
            self.phase_t = 0
            self.ps.clear()
            self.build_buttons()
            self.app.audio.play("coin")

    def handle(self, e):
        if self.phase != "summary" and e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.next_phase()
            return True
        return super().handle(e)

    def craft_y(self):
        k = clamp(self.phase_t / 4.2, 0, 1)
        return 80 + ease_out_cubic(k) * (H - 330)

    def reentry_pos(self):
        k = clamp(self.phase_t / 2.6, 0, 1)
        return W * 0.8 - k * W * 0.5, H * 0.15 + k * H * 0.45

    # ----------------------------------------------------------------- çizim
    def draw(self, surf):
        ox, oy = self.shake.offset(12)
        if self.phase == "landing":
            self.draw_landing(surf, ox, oy)
        elif self.phase == "return":
            self.draw_return(surf, ox, oy)
        else:
            self.draw_summary(surf)
        self.ps.draw(surf, ox, oy)
        if self.phase != "summary":
            draw_text(surf, "Geçmek için tıkla", (W // 2, H - 40), 14, C["text_mute"], anchor="midtop")
        self.draw_widgets(surf)

    def draw_landing(self, surf, ox, oy):
        g = self.game
        pl = self.pl
        gy = H - 170 + oy
        if self.planet in paint.SCENES:
            # boyalı fotogerçekçi yüzey manzarası (gök + dağlar + zemin)
            bg = paint.get(self.planet, (W + 40, H + 30))
            surf.blit(bg, (-20 + ox, -15 + oy))
            cinema.motes(surf, (0, 0, W, H), self.t, 50, (255, 226, 190))
            cinema.grade(surf, (0, 0, W, H))
        else:
            self.space.draw(surf, 0.7)
            art.draw_planet(surf, self.planet, (W // 2 + ox, H + 1100 - 300 + oy), 1100, light=(-0.3, -0.9))
        # koloni varsa binalar ve bayrak
        col = g.colony(self.planet)
        if col:
            for i in range(min(6, sum(col["buildings"].values()))):
                bx = 200 + i * 190
                pygame.draw.ellipse(surf, (220, 225, 235), (bx, gy - 40, 110, 70))
                pygame.draw.ellipse(surf, (150, 200, 255), (bx + 20, gy - 30, 30, 16))
            art.draw_flag(surf, W - 320, gy, g.name, g.color, self.t, 1.0)
        # iniş aracı
        craft, _ = art.render_spacecraft(self.design["hull"], self.design["engine"], self.design["power"],
                                         self.design["antenna"], self.design["payloads"], g.name, g.color, 0.9)
        cy = self.craft_y()
        surf.blit(craft, (W // 2 - craft.get_width() // 2 + ox, cy - craft.get_height() // 2 + oy))
        if self.planet == "mars":
            self.dust.draw(surf)
        k = self.phase_t / 4.2
        draw_text(surf, f"{pl['name'].upper()} YÜZEYİNE İNİŞ", (W // 2, 60), 36, C["text"], bold=True,
                  anchor="midtop", glow=pl["glow"])
        draw_text(surf, f"Yerçekimi {pl['gravity']} · İrtifa {max(0, int((1 - k) * 1200))} m", (W // 2, 110), 17,
                  C["text_dim"], anchor="midtop")
        if k >= 1.0:
            draw_text(surf, "TEMAS! İniş başarılı.", (W // 2, 150), 24, C["green"], bold=True, anchor="midtop",
                      glow=C["green"])
            if self.res["crew"]:
                for i, cid in enumerate(self.res["crew"]):
                    c = g.crew_by_id(cid)
                    if c:
                        walk = min(1.0, (self.phase_t - 4.2) / 2.0)
                        art.draw_astronaut(surf, W // 2 + 60 + i * 50 + walk * 120, gy - 20, c["type"], 1.0, self.t,
                                           wave=True)

    def draw_return(self, surf, ox, oy):
        self.space.draw(surf, 0.8)
        art.draw_planet(surf, "earth", (W // 2 + 120 + ox, H + 380 + oy), 760, light=(-0.4, -0.8))
        x, y = self.reentry_pos()
        k = clamp(self.phase_t / 2.6, 0, 1)
        draw_glow(surf, (x, y), 90 * (1 - k * 0.5), (255, 160, 60), 0.9)
        pygame.draw.circle(surf, (240, 240, 250), (int(x), int(y)), 12)
        if self.phase_t > 2.6:
            kk = clamp((self.phase_t - 2.6) / 0.5, 0, 1)
            px, py = x, y + kk * 40
            pygame.draw.arc(surf, (255, 120, 60), (px - 40, py - 70, 80, 70), 0, math.pi, 4)
            pygame.draw.line(surf, (200, 200, 210), (px - 38, py - 35), (px, py), 1)
            pygame.draw.line(surf, (200, 200, 210), (px + 38, py - 35), (px, py), 1)
        draw_text(surf, "DÜNYA'YA DÖNÜŞ", (W // 2, 60), 36, C["text"], bold=True, anchor="midtop", glow=C["orange"])
        draw_text(surf, "Atmosfere giriş · Isı kalkanı 1600°C", (W // 2, 110), 17, C["text_dim"], anchor="midtop")

    def draw_summary(self, surf):
        g = self.game
        self.space.draw(surf, 0.9)
        res = self.res
        sm = self.summary
        out = res["outcome"]
        col = {"success": C["green"], "partial": C["gold"], "fail": C["red"]}[out]
        title = {"success": "GÖREV BAŞARILI", "partial": "KISMİ BAŞARI", "fail": "GÖREV BAŞARISIZ"}[out]
        k = ease_out_back(self.k)
        art.draw_planet(surf, self.planet, (W - 250, 300), int(160 * k + 1))
        draw_text(surf, f"{g.name.upper()} · {self.pl['name'].upper()} GÖREVİ", (120, 80), 18, C["text_dim"], bold=True)
        draw_text(surf, title, (120, 110), int(60 * k + 1), col, bold=True, glow=col)
        draw_text(surf, res["reason"], (124, 190), 18, C["text"])
        r = pygame.Rect(120, 240, 820, 420)
        glass_panel(surf, r, col, 200, 20)
        x, y = r.x + 30, r.y + 24
        draw_text(surf, "ÖDÜLLER", (x, y), 16, col, bold=True)
        draw_icon(surf, "money", (r.right - 260, y + 10), 20, C["gold"])
        draw_text(surf, f"+{fmt_num(sm['money'])}", (r.right - 240, y - 2), 26, C["gold"], bold=True)
        draw_icon(surf, "rp", (r.right - 120, y + 10), 20, C["cyan"])
        draw_text(surf, f"+{sm['rp']}", (r.right - 100, y - 2), 26, C["cyan"], bold=True)
        y += 50
        lines = list(sm["lines"])
        if self.surface_minerals:
            lines.append(f"Yüzeyden {self.surface_minerals} {D.MINERAL[self.pl['mineral']]['name']} çıkarıldı")
        if self.pickup:
            lines.append(f"Koloni deposundan {self.pickup} birim yüklendi")
        if self.supplied:
            lines.append("Koloniye ikmal ve yeni sakinler ulaştı")
        if not lines:
            lines = ["Bu görevden ödül alınamadı."]
        for i, ln in enumerate(lines[:10]):
            kk = clamp(self.phase_t * 4 - i * 0.4, 0, 1)
            draw_icon(surf, "check" if out != "fail" else "cross", (x + 8, y + 10 + i * 30), 14, col)
            draw_text(surf, ln, (x + 28 + (1 - kk) * 40, y + i * 30), 17, C["text"], alpha=int(255 * kk))
        # sayaçlar
        cy = r.bottom - 70
        items = [("pickaxe", "Asteroit", res["asteroids"]), ("dust", "Yıldız Tozu", res["stardust"]),
                 ("camera", "Fotoğraf", res["photos"]), ("satellite", "Kurtarma", res["rescues"]),
                 ("warning", "Hasar", res["damage"])]
        for i, (ic, lab, n) in enumerate(items):
            xx = x + i * 156
            draw_icon(surf, ic, (xx + 14, cy + 20), 20, C["cyan"])
            draw_text(surf, str(n), (xx + 34, cy + 6), 22, C["text"], bold=True)
            draw_text(surf, lab, (xx + 34, cy + 34), 12, C["text_dim"])
        if sm["first_landing"] or sm["first_visit"]:
            chip(surf, (r.right, r.y - 40), "İLK İNİŞ" if sm["first_landing"] else "İLK VARIŞ", C["gold"], 16,
                 anchor="topright", icon="star")
        # mürettebat
        if res["crew"]:
            draw_text(surf, "MÜRETTEBAT", (1000, 520), 14, C["text_dim"], bold=True)
            for i, cid in enumerate(res["crew"]):
                c = g.crew_by_id(cid)
                if c:
                    art.draw_astronaut(surf, 1030 + i * 90, 600, c["type"], 1.0, self.t, c["tired"], c["status"] == "sick",
                                       wave=out == "success")
                    draw_text(surf, g.crew_status_label(c), (1030 + i * 90, 650), 11,
                              C["red"] if c["status"] == "sick" else C["orange"] if c["tired"] else C["green"],
                              bold=True, anchor="midtop")

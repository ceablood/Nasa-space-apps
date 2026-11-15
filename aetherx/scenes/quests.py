# -*- coding: utf-8 -*-
"""
GÖREV TAHTASI + BAŞARIMLAR
Günlük görev: "Ay'a git, 3 fotoğraf çek" -> 100 Para + 20 Puan
Haftalık görev: "Mars'ta koloni kur" -> 1000 Para + 100 Puan
Başarımlar: rozet + para. NOVA görevleri: NOVA'nın özel önerisi.
"""
import math

import pygame

from . import Scene
from .. import data as D
from ..config import C, H, MIN_PER_DAY, TOPBAR_H, W
from ..fx import draw_glow, scale_color, ParticleSystem
from ..ui import UI, Button, Tabs, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, fmt_num, chip


class QuestsScene(Scene):
    music = "base"
    ambient = "amb_control"
    title = "GÖREV TAHTASI"
    title_icon = "chart"
    accent = C["lime"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("teal", 17, 0.7)
        self.tab = 0
        self.items = []
        self.ps = ParticleSystem(500)

    def enter(self, tab=0, **kw):
        self.tab = tab
        self.rebuild()

    def set_tab(self, i):
        self.tab = i
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.items = []
        self.back_button()
        self.add(Tabs((40, TOPBAR_H + 100, 720, 46), ["GÜNLÜK", "HAFTALIK", "BAŞARIMLAR"], self.set_tab, C["lime"],
                      self.tab, ["clock", "chart", "trophy"]))
        if self.tab in (0, 1):
            kind = "daily" if self.tab == 0 else "weekly"
            for i, it in enumerate(g.s["quests"][kind]):
                r = pygame.Rect(40, TOPBAR_H + 176 + i * 112, 960, 100)
                self.items.append((it, r))
                if it["done"] and not it["claimed"]:
                    b = self.add(Button((r.right - 200, r.y + 24, 180, 52), "ÖDÜLÜ AL", (lambda k=kind, j=i: self.claim(k, j)),
                                        accent=C["gold"], icon="money", size=16, style="big"))
                    b.pulse = True
            self.add(Button((40, H - 140, 420, 50), "NOVA'DAN ÖZEL GÖREV İSTE", self.nova_quest, accent=C["cyan"],
                            icon="nova", size=15))
        cost = g.upgrade_cost("board")
        if cost is not None:
            ub = self.add(Button((W - 480, TOPBAR_H + 100, 440, 46),
                                 f"GÖREV TAHTASI SV{g.lvl('board') + 1} · {fmt_num(cost)} P",
                                 lambda: self.act(g.upgrade, "board", ok_sound="levelup"), accent=C["gold"], icon="star",
                                 size=14, tooltip="Daha fazla günlük/haftalık görev (yeni günde)"))
            ok, why = g.can_upgrade("board")
            ub.set_enabled(ok, why)

    def claim(self, kind, i):
        if self.act(self.game.claim_quest, kind, i, ok_sound="coin"):
            for k in range(20):
                self.ps.sparks(900, TOPBAR_H + 226 + i * 112, 4, C["gold"])
        self.rebuild()

    def nova_quest(self):
        txt, planet = self.app.nova.suggest()
        self.app.say(txt, "think")

    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        q = self.game.s["quests"]
        sig = tuple((it["p"], it["done"], it["claimed"]) for it in q["daily"] + q["weekly"]) + (q["day"], q["week"])
        if getattr(self, "_sig", None) != sig:
            self._sig = sig
            self.rebuild()

    def draw(self, surf):
        g = self.game
        self.bg.draw(surf)
        left_d = MIN_PER_DAY - g.minutes % MIN_PER_DAY
        left_w = (7 - (g.day - 1) % 7) * MIN_PER_DAY - g.minutes % MIN_PER_DAY
        self.draw_title(surf, sub=f"Yeni günlük görevler: {left_d / 60:.1f} saat · Haftalık: {left_w / 60 / 24:.1f} gün")
        # dijital tahta çerçevesi
        if self.tab in (0, 1):
            fr = pygame.Rect(26, TOPBAR_H + 162, 988, 4 * 112 + 20)
            pygame.draw.rect(surf, (6, 12, 10), fr, border_radius=16)
            pygame.draw.rect(surf, scale_color(C["lime"], 0.5), fr, 2, border_radius=16)
            for y in range(fr.y, fr.bottom, 4):
                pygame.draw.line(surf, (10, 22, 14), (fr.x + 4, y), (fr.right - 4, y))
            for idx, (it, r) in enumerate(self.items):
                slide = max(0, 1 - (self.t * 3 - idx * 0.3))
                rr = r.move(int(slide * 60), 0)
                col = C["gold"] if it["done"] and not it["claimed"] else C["green"] if it["claimed"] else C["lime"]
                glass_panel(surf, rr, col, 150, 14)
                draw_icon(surf, "check" if it["done"] else "chart", (rr.x + 36, rr.centery), 24, col)
                draw_text(surf, it["text"], (rr.x + 70, rr.y + 16), 20, C["text"], bold=True)
                draw_text(surf, f"Ödül: {it['money']} Para + {it['rp']} Puan", (rr.x + 70, rr.y + 46), 14, C["gold"])
                n = it["n"]
                draw_bar(surf, (rr.x + 70, rr.y + 74, 560, 8), it["p"] / n, col, glow=False)
                draw_text(surf, f"{it['p']}/{n}", (rr.x + 640, rr.y + 66), 14, C["text"], bold=True)
                if it["claimed"]:
                    draw_text(surf, "ALINDI", (rr.right - 30, rr.centery), 18, C["green"], bold=True, anchor="midright")
            if not self.items:
                draw_text(surf, "Bu dönem için görev yok.", (60, TOPBAR_H + 200), 18, C["text_dim"])
        else:
            self.draw_achievements(surf)
        self.draw_widgets(surf)
        self.ps.draw(surf)

    def draw_achievements(self, surf):
        g = self.game
        got = g.s["achievements"]
        draw_text(surf, f"{len(got)}/{len(D.ACHIEVEMENTS)} başarım", (40, TOPBAR_H + 170), 18, C["gold"], bold=True)
        cols = 6
        for i, a in enumerate(D.ACHIEVEMENTS):
            r = pygame.Rect(40 + (i % cols) * 256, TOPBAR_H + 206 + (i // cols) * 182, 244, 172)
            ok = a["key"] in got
            col = C["gold"] if ok else (80, 90, 115)
            hov = r.collidepoint(UI.mouse)
            glass_panel(surf, r, col, 170 if ok else 120, 16, strong=hov and ok)
            cx, cy = r.centerx, r.y + 58
            if ok:
                draw_glow(surf, (cx, cy), 56, C["gold"], 0.5 + 0.2 * math.sin(self.t * 2 + i))
            pygame.draw.circle(surf, scale_color(col, 0.3), (cx, cy), 36)
            pygame.draw.circle(surf, col, (cx, cy), 36, 3)
            for k in range(8):
                ang = k * math.pi / 4 + (self.t * 0.4 if ok else 0)
                pygame.draw.line(surf, col, (cx + math.cos(ang) * 38, cy + math.sin(ang) * 38),
                                 (cx + math.cos(ang) * 46, cy + math.sin(ang) * 46), 2)
            draw_icon(surf, a["icon"] if ok else "lock", (cx, cy), 28, C["white"] if ok else col)
            draw_text(surf, a["name"], (cx, r.y + 104), 15, C["text"] if ok else C["text_dim"], bold=True, anchor="midtop")
            draw_paragraph(surf, a["desc"], (r.x + 14, r.y + 130), r.w - 28, 12, C["text_dim"], max_lines=2)
            if a["money"]:
                draw_text(surf, f"+{a['money']} P", (r.right - 12, r.y + 10), 12, C["gold"] if ok else C["text_mute"],
                          bold=True, anchor="topright")
            if hov and ok:
                UI.set_tooltip(f"{g.name}, '{a['name']}' başarımını kazandı!", C["gold"])

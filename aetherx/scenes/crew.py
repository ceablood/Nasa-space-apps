# -*- coding: utf-8 -*-
"""
ASTRONOT MERKEZİ + SAĞLIK MERKEZİ + EĞLENCE VE DİNLENME ALANI
5 tip: Pilot (mavi), Mühendis (turuncu), Bilim İnsanı (yeşil), Doktor (beyaz),
Madenci (kahverengi). 2 yolculuk üst üste yapan astronot yorulur; 1 yolculuk
dinlenirse ya da Eğlence Alanı'nda dinlenirse düzelir.
"""
import math

import pygame

from . import Scene
from .. import art
from .. import data as D
from ..config import C, CREW_COLORS, H, TOPBAR_H, W
from ..fx import draw_glow, scale_color
from ..ui import (UI, Button, Tabs, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, fmt_num, fmt_time,
                  chip)


class CrewScene(Scene):
    music = "base"
    ambient = "amb_base"
    title = "ASTRONOT MERKEZİ"
    title_icon = "astro"
    accent = C["blue"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("deep", 33, 0.8)
        self.tab = 0
        self.cards = []

    def enter(self, tab=0, **kw):
        self.tab = tab
        self.rebuild()

    def set_tab(self, i):
        self.tab = i
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.cards = []
        self.back_button()
        self.tabs = self.add(Tabs((40, TOPBAR_H + 100, 760, 46), ["KADRO", "İŞE AL", "SAĞLIK MERKEZİ", "DİNLENME ALANI"],
                                  self.set_tab, C["blue"], self.tab, ["astro", "money", "medic", "heart"]))
        getattr(self, f"build_{self.tab}")()

    # ---------------------------------------------------------------- kadro
    def build_0(self):
        g = self.game
        for i, c in enumerate(g.s["crew"]):
            col, row = i % 4, i // 4
            r = pygame.Rect(40 + col * 386, TOPBAR_H + 170 + row * 176, 376, 164)
            self.cards.append((c, r))
            by = r.bottom - 44
            if c["status"] == "ready":
                cost = D.TRAIN_COST * c["rank"]
                tb = self.add(Button((r.x + 110, by, 120, 34), f"EĞİT {cost}", (lambda cid=c["id"]: self.act(g.train, cid)),
                                     accent=C["gold"], size=12, icon="star", style="gold",
                                     tooltip=f"Rütbe {c['rank'] + 1}: etkisi %12 artar"))
                if c["rank"] >= D.MAX_RANK:
                    tb.set_enabled(False, "Maksimum rütbe")
                elif g.money < cost:
                    tb.set_enabled(False, f"{cost} Para gerekli")
                rb = self.add(Button((r.x + 238, by, 92, 34), "DİNLEN", (lambda cid=c["id"]: self.act(g.rest, cid)),
                                     accent=C["green"], size=12))
                rb.set_enabled(c["tired"] or c["streak"] > 0, "Zaten dinç")
            self.add(Button((r.right - 40, r.y + 10, 30, 30), "", (lambda cid=c["id"]: self.act(g.dismiss, cid)),
                            accent=C["red"], icon="cross", size=10, tooltip="Ajanstan ayır"))

    def build_1(self):
        g = self.game
        for i, t in enumerate(D.CREW_TYPES):
            r = pygame.Rect(40 + i * 306, TOPBAR_H + 180, 294, 470)
            self.cards.append((t, r))
            b = self.add(Button((r.x + 24, r.bottom - 70, r.w - 48, 52), f"İŞE AL · {t['hire']} P",
                                (lambda k=t["key"]: self.hire(k)), accent=C["gold"], size=16, icon="money",
                                style="gold"))
            if len(g.s["crew"]) >= g.crew_cap():
                b.set_enabled(False, "Kadro dolu: Astronot Merkezi'ni yükselt")
            elif g.money < t["hire"]:
                b.set_enabled(False, f"{t['hire']} Para gerekli")
        cost = g.upgrade_cost("astro")
        if cost is not None:
            ub = self.add(Button((W - 460, TOPBAR_H + 100, 420, 46),
                                 f"MERKEZ SV{g.lvl('astro') + 1} · KADRO {D.ASTRO_CAP[g.lvl('astro') + 1]} · {fmt_num(cost)} P",
                                 lambda: self.act(g.upgrade, "astro", ok_sound="levelup"), accent=C["gold"], size=14,
                                 icon="star", style="gold"))
            ok, why = g.can_upgrade("astro")
            ub.set_enabled(ok, why)

    def hire(self, k):
        if self.act(self.game.hire, k, ok_sound="success"):
            t = D.CREW_TYPE[k]
            self.app.say(f"{self.game.name}, yeni {t['name']} kadroya katıldı. {t['desc']}", "happy")

    def build_2(self):
        g = self.game
        cost = g.upgrade_cost("medical")
        if cost is not None:
            ub = self.add(Button((W - 460, TOPBAR_H + 100, 420, 46),
                                 f"SAĞLIK MERKEZİ SV{g.lvl('medical') + 1} · {fmt_num(cost)} P",
                                 lambda: self.act(g.upgrade, "medical", ok_sound="levelup"), accent=C["gold"], size=14,
                                 icon="star", style="gold"))
            ok, why = g.can_upgrade("medical")
            ub.set_enabled(ok, why)

    def build_3(self):
        g = self.game
        cost = g.upgrade_cost("rec")
        if cost is not None:
            ub = self.add(Button((W - 460, TOPBAR_H + 100, 420, 46),
                                 f"DİNLENME ALANI SV{g.lvl('rec') + 1} · {fmt_num(cost)} P",
                                 lambda: self.act(g.upgrade, "rec", ok_sound="levelup"), accent=C["gold"], size=14,
                                 icon="star", style="gold"))
            ok, why = g.can_upgrade("rec")
            ub.set_enabled(ok, why)
        tired = [c for c in g.s["crew"] if c["status"] == "ready" and (c["tired"] or c["streak"] > 0)]
        b = self.add(Button((40, TOPBAR_H + 170, 420, 54), f"TÜM YORGUNLARI DİNLENDİR ({len(tired)})", self.rest_all,
                            accent=C["green"], icon="heart", size=16))
        b.set_enabled(bool(tired), "Yorgun astronot yok")

    def rest_all(self):
        for c in list(self.game.s["crew"]):
            if c["status"] == "ready" and (c["tired"] or c["streak"] > 0):
                self.game.rest(c["id"])
        self.app.audio.play("pickup")
        self.rebuild()

    # ---------------------------------------------------------------- döngü
    def update(self, dt):
        super().update(dt)
        sig = tuple((c["id"], c["status"], c["rank"], c["tired"]) for c in self.game.s["crew"]) + (self.game.money // 50,)
        if getattr(self, "_sig", None) != sig:
            self._sig = sig
            self.rebuild()

    def draw(self, surf):
        g = self.game
        self.bg.draw(surf)
        self.draw_title(surf, sub=f"Kadro {len(g.s['crew'])}/{g.crew_cap()} · Her yolculuğa en fazla 3 astronot")
        getattr(self, f"draw_{self.tab}")(surf)
        self.draw_widgets(surf)                  # düğmeler kartların üstünde (eskiden kartlar düğmeleri soluk gösteriyordu)

    def draw_0(self, surf):
        g = self.game
        if not g.s["crew"]:
            draw_text(surf, "Kadroda astronot yok. 'İŞE AL' sekmesinden astronot al.", (40, TOPBAR_H + 190), 18,
                      C["text_dim"])
        for c, r in self.cards:
            col = CREW_COLORS[c["type"]]
            glass_panel(surf, r, col, 170, 16)
            art.draw_astronaut(surf, r.x + 56, r.y + 70, c["type"], 1.25, self.t, c["tired"], c["status"] == "sick",
                               wave=r.collidepoint(UI.mouse))
            t = D.CREW_TYPE[c["type"]]
            draw_text(surf, c["name"], (r.x + 110, r.y + 14), 18, C["text"], bold=True)
            draw_text(surf, f"{t['name']} · {t['color_name']}", (r.x + 110, r.y + 40), 13, col, bold=True)
            for i in range(D.MAX_RANK):
                draw_icon(surf, "star", (r.x + 120 + i * 20, r.y + 70), 14, C["gold"] if i < c["rank"] else (60, 70, 90))
            st = g.crew_status_label(c)
            stc = {"HAZIR": C["green"], "YORGUN": C["orange"], "HASTA": C["red"], "DİNLENİYOR": C["cyan"],
                   "EĞİTİMDE": C["gold"], "GÖREVDE": C["violet"]}.get(st, C["text"])
            chip(surf, (r.x + 190, r.y + 61), st, stc, 12)
            draw_text(surf, f"{c['trips']} yolculuk · üst üste {c['streak']}", (r.x + 110, r.y + 90), 12, C["text_dim"])
            if c["status"] in ("training",):
                draw_bar(surf, (r.x + 110, r.bottom - 30, 220, 8), 1 - c["timer"] / (D.TRAIN_SEC / D.TRAIN_SPEED[g.lvl('astro')]),
                         C["gold"], value=fmt_time(c["timer"]), size=11)
            elif c["status"] in ("sick", "resting"):
                total = (D.HEAL_HOURS if c["status"] == "sick" else D.REST_HOURS)[g.lvl("medical" if c["status"] == "sick" else "rec")] * 60
                draw_bar(surf, (r.x + 110, r.bottom - 30, 220, 8), 1 - c["timer"] / max(1, total),
                         C["red"] if c["status"] == "sick" else C["cyan"],
                         value=f"{c['timer'] / 60:.1f} saat", size=11)

    def draw_1(self, surf):
        for t, r in self.cards:
            col = CREW_COLORS[t["key"]]
            hov = r.collidepoint(UI.mouse)
            glass_panel(surf, r, col, 180, 18, strong=hov)
            draw_glow(surf, (r.centerx, r.y + 150), 110, col, 0.35 + (0.2 if hov else 0))
            art.draw_astronaut(surf, r.centerx, r.y + 150, t["key"], 2.4, self.t, wave=hov)
            draw_text(surf, t["name"], (r.centerx, r.y + 250), 26, C["text"], bold=True, anchor="midtop", glow=col)
            draw_text(surf, f"Üniforma: {t['color_name']}", (r.centerx, r.y + 286), 13, col, bold=True, anchor="midtop")
            draw_paragraph(surf, t["desc"], (r.x + 22, r.y + 318), r.w - 44, 15, C["text_dim"], max_lines=4)

    def draw_2(self, surf):
        g = self.game
        sick = [c for c in g.s["crew"] if c["status"] == "sick"]
        draw_text(surf, f"İyileşme süresi: {D.HEAL_HOURS[g.lvl('medical')]} oyun saati", (40, TOPBAR_H + 170), 18,
                  C["text"], bold=True)
        draw_text(surf, "Nükleer motor radyasyonu ve Jüpiter radyasyon kuşağı astronotları hasta edebilir. "
                        "Doktor yolda iyileştirir.", (40, TOPBAR_H + 200), 15, C["text_dim"])
        if not sick:
            r = pygame.Rect(40, TOPBAR_H + 250, 600, 120)
            glass_panel(surf, r, C["green"], 150, 16)
            draw_icon(surf, "heart", (r.x + 50, r.centery), 34, C["green"])
            draw_text(surf, "Herkes sağlıklı!", (r.x + 90, r.centery), 22, C["text"], bold=True, anchor="midleft")
        for i, c in enumerate(sick):
            r = pygame.Rect(40, TOPBAR_H + 250 + i * 110, 700, 96)
            glass_panel(surf, r, C["red"], 170, 14)
            art.draw_astronaut(surf, r.x + 50, r.y + 46, c["type"], 1.0, self.t, sick=True)
            draw_text(surf, c["name"], (r.x + 100, r.y + 16), 18, C["text"], bold=True)
            draw_text(surf, c.get("reason", "Hasta"), (r.x + 100, r.y + 42), 14, C["red"])
            draw_bar(surf, (r.x + 100, r.y + 70, 560, 8), 1 - c["timer"] / (D.HEAL_HOURS[g.lvl("medical")] * 60),
                     C["green"], glow=False)
        # bina görseli
        r = pygame.Rect(W - 460, TOPBAR_H + 180, 420, 300)
        glass_panel(surf, r, C["red"], 140, 18)
        pygame.draw.rect(surf, (230, 232, 240), (r.x + 60, r.y + 70, 300, 170), border_radius=12)
        pygame.draw.rect(surf, (230, 40, 60), (r.centerx - 14, r.y + 100, 28, 90))
        pygame.draw.rect(surf, (230, 40, 60), (r.centerx - 45, r.y + 131, 90, 28))
        draw_glow(surf, (r.centerx, r.y + 145), 80, (255, 60, 80), 0.3 + 0.1 * math.sin(self.t * 2))
        for i in range(3):
            pygame.draw.rect(surf, (180, 200, 230), (r.x + 80 + i * 90, r.y + 210, 60, 18), border_radius=4)

    def draw_3(self, surf):
        g = self.game
        draw_text(surf, f"Dinlenme süresi: {D.REST_HOURS[g.lvl('rec')]} oyun saati", (500, TOPBAR_H + 186), 18,
                  C["text"], bold=True)
        lst = [c for c in g.s["crew"] if c["status"] == "resting" or c["tired"]]
        for i, c in enumerate(lst[:8]):
            r = pygame.Rect(40 + (i % 2) * 520, TOPBAR_H + 250 + (i // 2) * 110, 500, 96)
            col = C["cyan"] if c["status"] == "resting" else C["orange"]
            glass_panel(surf, r, col, 160, 14)
            art.draw_astronaut(surf, r.x + 50, r.y + 46, c["type"], 1.0, self.t, tired=c["tired"])
            draw_text(surf, c["name"], (r.x + 100, r.y + 16), 18, C["text"], bold=True)
            draw_text(surf, "Dinleniyor" if c["status"] == "resting" else "Yorgun: verim %50", (r.x + 100, r.y + 42), 14, col)
            if c["status"] == "resting":
                draw_bar(surf, (r.x + 100, r.y + 70, 360, 8), 1 - c["timer"] / (D.REST_HOURS[g.lvl("rec")] * 60),
                         C["cyan"], glow=False)
        # park görseli
        r = pygame.Rect(W - 460, TOPBAR_H + 180, 420, 300)
        glass_panel(surf, r, C["green"], 140, 18)
        pygame.draw.rect(surf, (40, 110, 60), r.inflate(-40, -40), border_radius=16)
        scr = pygame.Rect(r.x + 50, r.y + 50, 160, 80)
        pygame.draw.rect(surf, (10, 10, 20), scr)
        hue = math.sin(self.t) * 0.5 + 0.5
        pygame.draw.rect(surf, (int(255 * hue), 90, int(255 * (1 - hue))), scr.inflate(-10, -10))
        draw_text(surf, "SİNEMA", (scr.centerx, scr.bottom + 6), 12, C["white"], bold=True, anchor="midtop")
        pygame.draw.rect(surf, (60, 170, 230), (r.x + 240, r.y + 50, 140, 80), border_radius=10)
        draw_text(surf, "HAVUZ", (r.x + 310, r.y + 136), 12, C["white"], bold=True, anchor="midtop")
        pygame.draw.rect(surf, (200, 160, 110), (r.x + 50, r.y + 180, 330, 70), border_radius=10)
        draw_text(surf, "YEMEKHANE", (r.x + 215, r.y + 206), 14, (40, 20, 10), bold=True, anchor="midtop")

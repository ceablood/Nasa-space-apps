# -*- coding: utf-8 -*-
"""
DEPO + YAKIT DEPOSU
Madenler (Ay Taşı 10, Kızıl Maden 50, Sülfür 80, Gaz Madeni 200, Asteroit
Cevheri 35), Yıldız Tozu ve Tamir Kitleri. Madenler Dünya'da satılır.
Yakıt Deposu bedava yakıt üretir; market daha pahalıdır.
"""
import math
import random

import pygame

from . import Scene
from .. import data as D
from ..config import C, H, MARKET_FUEL_PRICE, REPAIR_KIT_PRICE, TOPBAR_H, W
from ..fx import ParticleSystem, draw_glow, lerp_color, scale_color
from ..ui import UI, Button, Tabs, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, fmt_num


class DepotScene(Scene):
    music = "base"
    ambient = "amb_hangar"
    title = "DEPO"
    title_icon = "box"
    accent = C["gold"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("ember", 91, 0.6)
        self.tab = 0
        self.ps = ParticleSystem(700)
        self.rows = []

    def enter(self, tab=0, **kw):
        self.tab = tab
        self.rebuild()

    def set_tab(self, i):
        self.tab = i
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.rows = []
        self.back_button()
        self.add(Tabs((40, TOPBAR_H + 100, 640, 46), ["MADENLER", "TAMİR KİTLERİ", "YAKIT DEPOSU"], self.set_tab,
                      C["gold"], self.tab, ["box", "wrench", "fuel"]))
        if self.tab == 0:
            y = TOPBAR_H + 180
            for m in D.MINERALS:
                have = g.s["inventory"].get(m["key"], 0)
                r = pygame.Rect(40, y, 900, 74)
                self.rows.append((m, r))
                b1 = self.add(Button((r.right - 300, r.y + 14, 130, 46), "10 SAT", (lambda k=m["key"]: self.sell(k, 10)),
                                     accent=C["gold"], size=14))
                b1.set_enabled(have >= 1, "Stok yok")
                b2 = self.add(Button((r.right - 160, r.y + 14, 140, 46), "HEPSİNİ SAT", (lambda k=m["key"]: self.sell(k)),
                                     accent=C["gold"], size=14, icon="money"))
                b2.set_enabled(have >= 1, "Stok yok")
                y += 84
            total = sum(g.s["inventory"].get(m["key"], 0) * m["price"] for m in D.MINERALS)
            sb = self.add(Button((40, y + 10, 900, 60), f"TÜM MADENLERİ SAT · +{fmt_num(total)} P", self.sell_all,
                                 accent=C["gold"], icon="money", size=19, style="big"))
            sb.set_enabled(total > 0, "Satılacak maden yok")
            sb.pulse = total > 0
        elif self.tab == 1:
            for i, n in enumerate((1, 5)):
                b = self.add(Button((40 + i * 320, TOPBAR_H + 330, 300, 58), f"{n} TAMİR KİTİ · {n * REPAIR_KIT_PRICE} P",
                                    (lambda k=n: self.act(g.buy_repair_kit, k, ok_sound="clunk")), accent=C["orange"],
                                    icon="wrench", size=16))
                b.set_enabled(g.money >= n * REPAIR_KIT_PRICE, f"{n * REPAIR_KIT_PRICE} Para gerekli")
        else:
            for i, kg in enumerate((25, 50, 100)):
                b = self.add(Button((40 + i * 250, TOPBAR_H + 560, 236, 54), f"{kg} KG · {kg * MARKET_FUEL_PRICE} P",
                                    (lambda k=kg: self.act(g.buy_fuel, k, ok_sound="coin")), accent=C["orange"],
                                    icon="fuel", size=15))
                b.set_enabled(g.money >= kg * MARKET_FUEL_PRICE and g.s["fuel"] < g.fuel_cap(), "Para yetersiz veya tank dolu")
            cost = g.upgrade_cost("fuel")
            if cost is not None:
                ub = self.add(Button((40, TOPBAR_H + 630, 740, 50),
                                     f"YAKIT DEPOSU SV{g.lvl('fuel') + 1} · {fmt_num(cost)} P", lambda: self.act(g.upgrade, "fuel", ok_sound="levelup"),
                                     accent=C["gold"], icon="star", size=15))
                ok, why = g.can_upgrade("fuel")
                ub.set_enabled(ok, why)
        if self.tab != 2:
            cost = g.upgrade_cost("depot")
            if cost is not None:
                ub = self.add(Button((W - 500, TOPBAR_H + 100, 460, 46),
                                     f"DEPO SV{g.lvl('depot') + 1} · {D.DEPOT_CAP[g.lvl('depot') + 1]} BİRİM · {fmt_num(cost)} P",
                                     lambda: self.act(g.upgrade, "depot", ok_sound="levelup"), accent=C["gold"], icon="star",
                                     size=14))
                ok, why = g.can_upgrade("depot")
                ub.set_enabled(ok, why)

    def sell(self, k, n=None):
        total = self.game.sell(k, n)
        if total:
            for i in range(10):
                self.ps.glow(random.uniform(300, 900), random.uniform(250, 600), 2, C["gold"], speed=(60, 200))
        self.rebuild()

    def sell_all(self):
        total = self.game.sell_all()
        if total:
            self.app.say(f"{self.game.name}, madenler satıldı: +{total} Para. Yeni roket parçalarına yatırım yapabilirsin.",
                         "happy")
            for i in range(30):
                self.ps.sparks(random.uniform(100, 900), random.uniform(250, 700), 6, C["gold"])
        self.rebuild()

    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        g = self.game
        sig = (g.money // 20, int(g.s["fuel"]) // 5, g.depot_used())
        if getattr(self, "_sig", None) != sig:
            self._sig = sig
            self.rebuild()

    def draw(self, surf):
        g = self.game
        self.bg.draw(surf)
        self.draw_title(surf, sub=f"Depo Sv{g.lvl('depot')} · Doluluk {g.depot_used()}/{g.depot_cap()}")
        if self.tab == 0:
            self.draw_minerals(surf)
        elif self.tab == 1:
            self.draw_kits(surf)
        else:
            self.draw_fuel(surf)
        self.draw_widgets(surf)
        self.draw_side(surf)
        self.ps.draw(surf)

    def draw_minerals(self, surf):
        g = self.game
        for m, r in self.rows:
            have = g.s["inventory"].get(m["key"], 0)
            glass_panel(surf, r, m["color"], 160, 14)
            pygame.draw.circle(surf, scale_color(m["color"], 0.5), (r.x + 40, r.centery), 22)
            draw_glow(surf, (r.x + 40, r.centery), 30, m["color"], 0.5)
            pts = [(r.x + 40 + math.cos(i * 1.05 + self.t * 0.5) * 18, r.centery + math.sin(i * 1.05 + self.t * 0.5) * 14)
                   for i in range(6)]
            pygame.draw.polygon(surf, m["color"], pts)
            draw_text(surf, m["name"], (r.x + 80, r.y + 12), 19, C["text"], bold=True)
            draw_text(surf, f"Birim fiyat: {m['price']} Para", (r.x + 80, r.y + 42), 13, C["text_dim"])
            draw_text(surf, f"×{have}", (r.x + 380, r.y + 20), 26, C["text"], bold=True)
            draw_text(surf, f"= {fmt_num(have * m['price'])} P", (r.x + 470, r.y + 26), 18, C["gold"], bold=True)

    def draw_kits(self, surf):
        g = self.game
        r = pygame.Rect(40, TOPBAR_H + 180, 640, 130)
        glass_panel(surf, r, C["orange"], 170, 16)
        draw_icon(surf, "wrench", (r.x + 60, r.centery), 44, C["orange"])
        draw_text(surf, f"Tamir Kiti ×{g.s['inventory']['repair_kit']}", (r.x + 110, r.y + 24), 26, C["text"], bold=True)
        draw_paragraph(surf, "Mühendis yolda tamir kitiyle bozuk parçayı 5 saniyede onarır. Kit yoksa tamir 9 saniye sürer.",
                       (r.x + 110, r.y + 62), r.w - 140, 15, C["text_dim"])

    def draw_fuel(self, surf):
        g = self.game
        r = pygame.Rect(40, TOPBAR_H + 170, 740, 370)
        glass_panel(surf, r, C["orange"], 160, 18)
        frac = g.s["fuel"] / max(1, g.fuel_cap())
        n = 2 + g.lvl("fuel")
        for i in range(n):
            tr = pygame.Rect(r.x + 40 + i * 130, r.y + 40, 100, 240)
            pygame.draw.rect(surf, (230, 232, 240), tr, border_radius=40)
            inner = tr.inflate(-14, -14)
            h = int(inner.h * frac)
            fr = pygame.Rect(inner.x, inner.bottom - h, inner.w, h)
            if h > 2:
                pygame.draw.rect(surf, lerp_color((255, 190, 80), (230, 100, 30), 0.5), fr, border_radius=30)
                pygame.draw.line(surf, (255, 230, 170), (fr.x + 8, fr.y + 4 + math.sin(self.t * 3 + i) * 3),
                                 (fr.right - 8, fr.y + 4 - math.sin(self.t * 3 + i) * 3), 2)
            pygame.draw.rect(surf, (150, 155, 170), tr, 3, border_radius=40)
            lc = C["green"] if frac > 0.95 else C["orange"]
            pygame.draw.circle(surf, lc, (tr.centerx, tr.bottom + 16), 6)
            draw_glow(surf, (tr.centerx, tr.bottom + 16), 16, lc, 0.8)
        draw_text(surf, f"{int(g.s['fuel'])}/{g.fuel_cap()} kg", (r.right - 30, r.y + 40), 30, C["text"], bold=True,
                  anchor="topright")
        draw_text(surf, f"Üretim: saatte {g.fuel_rate()} kg", (r.right - 30, r.y + 84), 16, C["orange"], bold=True,
                  anchor="topright")
        draw_text(surf, f"Market: {MARKET_FUEL_PRICE} Para/kg", (r.right - 30, r.y + 110), 14, C["text_dim"],
                  anchor="topright")
        draw_text(surf, "Fırlatmada önce depodaki yakıt kullanılır, eksik kısım marketten alınır.",
                  (r.x + 30, r.bottom - 40), 14, C["text_dim"])

    def draw_side(self, surf):
        g = self.game
        r = pygame.Rect(W - 500, TOPBAR_H + 170, 460, 360)
        glass_panel(surf, r, C["cyan"], 170, 18)
        draw_text(surf, "DEPO ÖZETİ", (r.x + 22, r.y + 18), 16, C["cyan"], bold=True)
        draw_bar(surf, (r.x + 22, r.y + 72, r.w - 44, 14), g.depot_used() / g.depot_cap(), C["gold"], label="DOLULUK",
                 value=f"{g.depot_used()}/{g.depot_cap()}")
        inv = g.s["inventory"]
        lines = [("dust", "Yıldız Tozu", inv["stardust"], C["cyan"]), ("wrench", "Tamir Kiti", inv["repair_kit"], C["orange"])]
        lines += [("box", m["name"], inv.get(m["key"], 0), m["color"]) for m in D.MINERALS]
        y = r.y + 110
        for ic, n, v, col in lines:
            draw_icon(surf, ic, (r.x + 34, y + 9), 16, col)
            draw_text(surf, n, (r.x + 56, y), 15, C["text_dim"])
            draw_text(surf, str(v), (r.right - 24, y), 15, C["text"], bold=True, anchor="topright")
            y += 30
        draw_text(surf, "Yıldız Tozu, Araştırma Merkezi'nde Puana çevrilir (1 = 10 Puan).", (r.x + 22, r.bottom - 30), 12,
                  C["text_mute"])

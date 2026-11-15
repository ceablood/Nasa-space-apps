# -*- coding: utf-8 -*-
"""
GÖREV KONTROL MERKEZİ - NASA'DAKİ GİBİ
Dev ekranlar: canlı Güneş Sistemi haritası, son simülasyon, rampalar,
görev geçmişi ve uzay havası alarmları.
"""
import math

import pygame

from . import Scene
from .. import art
from .. import data as D
from ..config import C, H, TOPBAR_H, W
from ..fx import draw_glow, scale_color, draw_grid, scanlines
from ..ui import UI, Button, chip, draw_bar, draw_icon, draw_text, glass_panel, fmt_num, draw_risk_bars

ORBITS = {"venus": 120, "earth": 175, "mars": 240, "jupiter": 340}
SPEEDS = {"venus": 0.16, "earth": 0.1, "mars": 0.06, "jupiter": 0.025}


class ControlScene(Scene):
    music = "space"
    ambient = "amb_control"
    title = "GÖREV KONTROL MERKEZİ"
    title_icon = "eye"
    accent = C["magenta"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("violet", 13, 0.6)

    def enter(self, **kw):
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.back_button()
        self.add(Button((W - 330, TOPBAR_H + 24, 290, 46), "YENİ GÖREV TASARLA", lambda: self.app.go("hangar"),
                        accent=C["orange"], icon="wrench", size=15))
        cost = g.upgrade_cost("control")
        if cost is not None:
            ub = self.add(Button((W - 660, TOPBAR_H + 24, 320, 46), f"KONTROL SV{g.lvl('control') + 1} · {fmt_num(cost)} P",
                                 lambda: self.act(g.upgrade, "control", ok_sound="levelup"), accent=C["gold"], icon="star",
                                 size=14, tooltip=D.BUILDING["control"]["levels"][g.lvl("control") + 1]))
            ok, why = g.can_upgrade("control")
            ub.set_enabled(ok, why)
        for i in range(3):
            p = g.s["pads"][i]
            if p and p["prep"] <= 0:
                b = self.add(Button((W - 220, TOPBAR_H + 420 + i * 70, 170, 46), "FIRLAT", (lambda j=i: self.app.go("launch", pad=j)),
                                    accent=C["green"], icon="rocket", size=15, style="big"))
                b.pulse = True

    def update(self, dt):
        super().update(dt)
        sig = tuple((p["prep"] <= 0) if p else None for p in self.game.s["pads"])
        if getattr(self, "_sig", None) != sig:
            self._sig = sig
            self.rebuild()

    def draw(self, surf):
        g = self.game
        self.bg.draw(surf, 0.6)
        # masalar ve kulaklıklı görevliler
        for i in range(10):
            x = 60 + i * 150
            pygame.draw.rect(surf, (14, 18, 34), (x, H - 120, 130, 60), border_radius=6)
            pygame.draw.rect(surf, scale_color(C["magenta"], 0.4), (x + 10, H - 112, 110, 26), border_radius=4)
            pts = [(x + 12 + k * 9, H - 99 + math.sin(self.t * 4 + k + i) * 6) for k in range(12)]
            pygame.draw.lines(surf, C["green"] if i % 3 else C["cyan"], False, pts, 1)
            pygame.draw.circle(surf, (30, 36, 60), (x + 65, H - 140), 14)
            pygame.draw.arc(surf, (90, 90, 110), (x + 49, H - 158, 32, 30), 0, math.pi, 3)
        self.draw_title(surf, sub=f"{g.name} Görev Kontrol · Sv{g.lvl('control')} · {g.time_label()}")
        self.draw_map(surf)
        self.draw_sim(surf)
        self.draw_pads(surf)
        self.draw_history(surf)
        self.draw_widgets(surf)

    def draw_map(self, surf):
        g = self.game
        r = pygame.Rect(40, TOPBAR_H + 100, 760, 520)
        glass_panel(surf, r, C["magenta"], 200, 18)
        draw_grid(surf, (r.x + 8, r.y + 8, r.w - 16, r.h - 16), C["magenta"], 40, 0.1, self.t)
        draw_text(surf, "CANLI GÜNEŞ SİSTEMİ HARİTASI", (r.x + 20, r.y + 14), 14, C["magenta"], bold=True)
        cx, cy = r.x + 330, r.centery + 10
        draw_glow(surf, (cx, cy), 80, (255, 200, 80), 0.9)
        pygame.draw.circle(surf, (255, 220, 120), (cx, cy), 26)
        pos = {}
        for key, rad in ORBITS.items():
            pygame.draw.ellipse(surf, (60, 70, 110), (cx - rad, cy - rad * 0.55, rad * 2, rad * 1.1), 1)
            a = self.t * SPEEDS[key] + hash(key) % 7
            px, py = cx + math.cos(a) * rad, cy + math.sin(a) * rad * 0.55
            pos[key] = (px, py)
            size = {"earth": 14, "venus": 12, "mars": 11, "jupiter": 24}[key]
            art.draw_planet(surf, key, (int(px), int(py)), size, glow=False)
            name = "Dünya" if key == "earth" else D.PLANET[key]["name"]
            draw_text(surf, name, (px, py + size + 4), 12, C["text"], bold=True, anchor="midtop")
            if key != "earth":
                v = g.s["visits"][key]
                if g.colony(key):
                    draw_icon(surf, "flag", (px + size + 8, py - size), 14, C["green"])
                elif v:
                    draw_icon(surf, "check", (px + size + 8, py - size), 12, C["cyan"])
                elif not g.planet_unlocked(key):
                    draw_icon(surf, "lock", (px + size + 8, py - size), 12, C["text_mute"])
        ea = pos["earth"]
        ma = self.t * 0.8
        mp = (ea[0] + math.cos(ma) * 28, ea[1] + math.sin(ma) * 16)
        art.draw_planet(surf, "moon", (int(mp[0]), int(mp[1])), 6, glow=False)
        pos["moon"] = mp
        if g.colony("moon"):
            draw_icon(surf, "flag", (mp[0] + 10, mp[1] - 10), 10, C["green"])
        # menzil halkası (iletişim kulesi)
        reach = {0: 0, 1: 40, 2: 90, 3: 220}[g.comms_range()]
        if reach:
            pygame.draw.circle(surf, scale_color(C["violet"], 0.6), (int(ea[0]), int(ea[1])), reach, 1)
            draw_text(surf, f"Kule menzili: {D.RANGE_NAME[g.comms_range()]}", (r.x + 20, r.bottom - 30), 12,
                      C["violet"], bold=True)
        # hazırdaki roket rotaları
        for p in g.s["pads"]:
            if p:
                tgt = pos.get(p["design"]["planet"])
                if tgt:
                    pygame.draw.line(surf, C["orange"], ea, tgt, 1)
                    k = (self.t * 0.4) % 1
                    draw_glow(surf, (ea[0] + (tgt[0] - ea[0]) * k, ea[1] + (tgt[1] - ea[1]) * k), 10, C["orange"], 0.9)
        storm = g.storm_active()
        if storm:
            for i in range(5):
                rr = int(40 + ((self.t * 80 + i * 60) % 300))
                pygame.draw.circle(surf, scale_color(C["gold"], 1 - rr / 340), (cx, cy), rr, 2)
            chip(surf, (r.right - 20, r.y + 14), "GÜNEŞ FIRTINASI AKTİF", C["gold"], 13, anchor="topright", icon="storm")
        surf.blit(scanlines((r.w, r.h), 18), r.topleft)

    def draw_sim(self, surf):
        g = self.game
        r = pygame.Rect(830, TOPBAR_H + 100, W - 870, 250)
        glass_panel(surf, r, C["cyan"], 190, 18)
        draw_text(surf, "SON SİMÜLASYON", (r.x + 20, r.y + 14), 14, C["cyan"], bold=True)
        sim = g.s.get("last_sim")
        if not sim:
            draw_text(surf, "Henüz simülasyon yapılmadı. Hangarda 'SİMÜLE ET'e bas.", (r.x + 20, r.y + 50), 15,
                      C["text_dim"])
            return
        draw_text(surf, f"Hedef: {D.PLANET[sim['planet']]['name']} · Gün {sim['day']}", (r.right - 20, r.y + 14), 13,
                  C["text_dim"], anchor="topright")
        d = sim["dist"]
        draw_risk_bars(surf, (r.x + 20, r.y + 40, r.w * 0.5, 120), d["fail"], d["partial"], d["success"])
        x = r.x + r.w * 0.5 + 50
        draw_text(surf, "OLASI ARIZA NOKTALARI", (x, r.y + 48), 12, C["text_dim"], bold=True)
        for i, (reason, frac, p) in enumerate(sim["points"][:4]):
            draw_icon(surf, "warning", (x + 8, r.y + 80 + i * 36), 14, C["red"] if p > 0.05 else C["gold"])
            draw_text(surf, reason, (x + 24, r.y + 72 + i * 36), 13, C["text"], max_w=r.right - x - 40)
            draw_text(surf, f"rota %{int(frac * 100)} · olasılık %{int(p * 100)}", (x + 24, r.y + 88 + i * 36), 11,
                      C["text_dim"])
        if g.lvl("control") >= 3:
            draw_text(surf, "Sv3 arıza tahmini aktif: risk -%2", (r.x + 20, r.bottom - 30), 12, C["green"], bold=True)

    def draw_pads(self, surf):
        g = self.game
        r = pygame.Rect(830, TOPBAR_H + 370, W - 870, 250)
        glass_panel(surf, r, C["orange"], 190, 18)
        draw_text(surf, "RAMPA DURUMU", (r.x + 20, r.y + 14), 14, C["orange"], bold=True)
        for i in range(3):
            y = r.y + 48 + i * 70
            open_ = g.lvl("pads") >= i + 1
            p = g.s["pads"][i]
            draw_text(surf, D.PAD_NAME[i + 1], (r.x + 20, y + 8), 17, C["text"] if open_ else C["text_mute"], bold=True)
            if not open_:
                draw_text(surf, "Kilitli", (r.x + 150, y + 10), 14, C["text_mute"])
            elif not p:
                draw_text(surf, "Boş", (r.x + 150, y + 10), 14, C["text_dim"])
            else:
                dd = p["design"]
                draw_text(surf, f"{D.PLANET[dd['planet']]['name']} · {D.PART['hull'][dd['hull']]['name']}", (r.x + 150, y),
                          14, C["text"])
                if p["prep"] > 0:
                    draw_bar(surf, (r.x + 150, y + 28, 240, 7), 1 - p["prep"] / D.PAD_PREP_SEC[i + 1], C["orange"], glow=False)
                else:
                    draw_text(surf, "FIRLATMAYA HAZIR", (r.x + 150, y + 22), 13, C["green"], bold=True)

    def draw_history(self, surf):
        g = self.game
        r = pygame.Rect(40, TOPBAR_H + 640, W - 80, 90)
        glass_panel(surf, r, C["text_dim"], 170, 14)
        draw_text(surf, "GÖREV GEÇMİŞİ", (r.x + 20, r.y + 10), 13, C["text_dim"], bold=True)
        st = g.s["stats"]
        rate = st["success"] / max(1, st["launches"])
        draw_text(surf, f"{st['launches']} fırlatma · başarı %{int(rate * 100)}", (r.right - 20, r.y + 10), 13, C["text"],
                  bold=True, anchor="topright")
        for i, m in enumerate(g.s["history"][:6]):
            x = r.x + 20 + i * 250
            col = {"success": C["green"], "partial": C["gold"], "fail": C["red"]}[m["outcome"]]
            pygame.draw.circle(surf, col, (x + 6, r.y + 52), 6)
            draw_text(surf, f"Gün {m['day']} · {D.PLANET[m['planet']]['name']}", (x + 20, r.y + 36), 14, C["text"], bold=True)
            draw_text(surf, f"+{m['money']} P · +{m['rp']} Puan", (x + 20, r.y + 56), 12, C["text_dim"])
        if not g.s["history"]:
            draw_text(surf, "Henüz görev yok.", (r.x + 20, r.y + 44), 14, C["text_mute"])

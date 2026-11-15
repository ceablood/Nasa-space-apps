# -*- coding: utf-8 -*-
"""
ARAŞTIRMA MERKEZİ
Puan vermez; araştırma süresini kısaltır ve para maliyetini düşürür.
Araştırma Puanı sahada toplanır: Yıldız Tozu (1 = 10 Puan), uydu kurtarma,
ilk iniş, fotoğraflar ve bilim insanı bonusu.
"""
import math

import pygame

from . import Scene
from .. import i18n
from .. import art
from ..i18n import tr
from .. import data as D
from ..config import C, H, TOPBAR_H, W, STARDUST_TO_RP
from ..fx import draw_glow, scale_color, clamp, ParticleSystem
from ..ui import (UI, Button, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, radial_progress,
                  fmt_num, fmt_time, chip)

ROWS = [
    ("BAŞLANGIÇ", None, ["fuelchem", "bigsolar"]),
    ("AY", "moon", ["aero", "lander", "sail"]),
    ("MARS", "mars", ["ion", "fission", "rtg", "laser"]),
    ("MARS II", "mars", ["station", "cargo", "heatshield"]),
    ("JÜPİTER", "jupiter", ["plasma", "dsn", "armor"]),
]
CARD_W, CARD_H = 220, 92


class ResearchScene(Scene):
    music = "base"
    ambient = "amb_lab"
    title = "ARAŞTIRMA MERKEZİ"
    title_icon = "flask"
    accent = C["cyan"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("teal", 51, 0.8)
        self.sel = "fuelchem"
        self.mode = "tech"
        self.cards = {}
        self.ps = ParticleSystem(500)

    def enter(self, mode=None, **kw):
        if mode:
            self.mode = mode
        a = self.game.s["research"]["active"]
        if a:
            self.sel = a["key"]
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.cards = {}
        self.back_button()
        for i, (m, lab, ic) in enumerate((("tech", "TEKNOLOJİ", "flask"), ("suit", "ASTRONOT KIYAFETİ", "astro"))):
            b = self.add(Button((W - 900 + i * 200, TOPBAR_H + 22, 192, 42), lab, (lambda mm=m: self.set_mode(mm)),
                                accent=C["cyan"], icon=ic, size=13, style="tab"))
            b.selected = (self.mode == m)
        if self.mode == "suit":
            self.build_suit()
            return
        y = TOPBAR_H + 112
        for label, planet, keys in ROWS:
            for i, k in enumerate(keys):
                r = pygame.Rect(150 + i * (CARD_W + 10), y, CARD_W, CARD_H)
                st = g.research_state(k)
                acc = {"done": C["green"], "active": C["cyan"], "available": C["gold"], "locked": (80, 90, 115)}[st]
                b = self.add(Button(r, "", (lambda kk=k: self.select(kk)), accent=acc, size=12))
                b.selected = (k == self.sel)
                b.pulse = (st == "available" and g.rp >= g.research_cost(k)[0])
                self.cards[k] = b
            y += CARD_H + 22
        pr = self.panel_rect()
        st = g.research_state(self.sel)
        rp, money = g.research_cost(self.sel)
        lab = {"done": "TAMAMLANDI", "active": "ARAŞTIRILIYOR...", "available": "ARAŞTIRMAYI BAŞLAT",
               "locked": "KİLİTLİ"}[st]
        sb = self.add(Button((pr.x + 24, pr.y + 300, pr.w - 48, 58), lab, lambda: self.start(self.sel),
                             accent=C["cyan"], icon="play", size=18, style="big"))
        if st != "available":
            sb.set_enabled(False, g.req_text(D.RESEARCH_BY_KEY[self.sel]["req"]) if st == "locked" else lab)
        else:
            ok, why = True, ""
            if g.s["research"]["active"]:
                ok, why = False, "Laboratuvar meşgul"
            elif g.rp < rp:
                ok, why = False, f"{rp} Puan gerekli (sende {g.rp})"
            elif g.money < money:
                ok, why = False, f"{money} Para gerekli"
            sb.set_enabled(ok, why)
            sb.pulse = ok
        dust = g.s["inventory"]["stardust"]
        db = self.add(Button((pr.x + 24, pr.bottom - 74, pr.w - 48, 52),
                             f"YILDIZ TOZUNU İŞLE ({dust} > +{dust * STARDUST_TO_RP} Puan)", self.process,
                             accent=C["violet"], icon="dust", size=15))
        db.set_enabled(dust > 0, "Depoda Yıldız Tozu yok")
        cost = g.upgrade_cost("research")
        if cost is not None:
            ub = self.add(Button((pr.x + 24, pr.bottom - 134, pr.w - 48, 50),
                                 f"MERKEZİ SEVİYE {g.lvl('research') + 1}'E YÜKSELT · {fmt_num(cost)} P",
                                 lambda: self.act(g.upgrade, "research", ok_sound="levelup"), accent=C["gold"],
                                 icon="star", size=14))
            ok, why = g.can_upgrade("research")
            ub.set_enabled(ok, why)

    def set_mode(self, m):
        self.mode = m
        self.app.audio.play("tick")
        self.rebuild()

    # ---------------------------------------------------------- kıyafet laboratuvarı
    def build_suit(self):
        g = self.game
        for i, trk in enumerate(D.SUIT_TRACKS):
            r = pygame.Rect(620, TOPBAR_H + 120 + i * 196, 940, 180)
            cost = g.suit_upgrade_cost(trk["key"])
            if cost is None:
                b = self.add(Button((r.right - 300, r.bottom - 70, 276, 52), "MAKSİMUM SEVİYE", None,
                                    accent=C["green"], size=15))
                b.set_enabled(False, "Maksimum seviye")
                continue
            rp, money = cost
            b = self.add(Button((r.right - 300, r.bottom - 70, 276, 52), "GELİŞTİR", (lambda k=trk["key"]: self.suit_up(k)),
                                accent=C["gold"], icon="star", size=16, style="big"))
            b.sublabel = f"{rp} Puan + {money} Para"
            ok, why = True, ""
            if g.lvl("research") < 1:
                ok, why = False, "Araştırma Merkezi gerekli"
            elif g.rp < rp:
                ok, why = False, f"{rp} Araştırma Puanı gerekli"
            elif g.money < money:
                ok, why = False, f"{money} Para gerekli"
            b.set_enabled(ok, why)
            b.pulse = ok

    def suit_up(self, k):
        if self.act(self.game.suit_upgrade, k, ok_sound="levelup"):
            for _ in range(30):
                self.ps.sparks(300, 470, 3, C["gold"])
            self.app.say(f"{self.game.name}, kıyafet geliştirildi: {D.SUIT_TRACK[k]['name']}.", "happy")
        self.rebuild()

    def draw_suit(self, surf):
        g = self.game
        st = g.suit_stats()
        su = D.SUIT[g.s["suit"]["type"]]
        lp = pygame.Rect(40, TOPBAR_H + 120, 560, 572)
        pygame.draw.rect(surf, (0, 0, 0), lp, border_radius=18)
        pygame.draw.rect(surf, su["color"], lp, 2, border_radius=18)
        draw_glow(surf, (lp.centerx, lp.y + 200), 170, su["color"], 0.3)
        art.draw_astronaut(surf, lp.centerx, lp.y + 205, "engineer", 4.2, self.t, wave=True)
        draw_text(surf, su["name"], (lp.centerx, lp.y + 360), 28, C["white"], bold=True, anchor="midtop")
        x, w = lp.x + 36, lp.w - 72
        y = lp.y + 430
        draw_bar(surf, (x, y, w, 12), min(1, st["dur"] / 8), C["orange"], label="DAYANIKLILIK", value=f"{st['dur']}/8",
                 segments=8, size=14)
        draw_bar(surf, (x, y + 52, w, 12), min(1, st["mob"] / 8), C["green"], label="HAREKET KABİLİYETİ",
                 value=f"{st['mob']}/8", segments=8, size=14)
        draw_bar(surf, (x, y + 104, w, 12), st["life"] / 4, C["cyan"], label="YAŞAM DESTEK",
                 value="+" + i18n.pct(st['life'] * 12), segments=4, size=14)
        for i, trk in enumerate(D.SUIT_TRACKS):
            r = pygame.Rect(620, TOPBAR_H + 120 + i * 196, 940, 180)
            lv = g.s["suit"][trk["key"]]
            pygame.draw.rect(surf, (0, 0, 0), r, border_radius=16)
            pygame.draw.rect(surf, C["gold"] if lv < trk["max"] else C["green"], r, 1, border_radius=16)
            draw_icon(surf, trk["icon"], (r.x + 44, r.y + 46), 30, C["gold"])
            draw_text(surf, trk["name"], (r.x + 84, r.y + 24), 24, C["white"], bold=True)
            draw_text(surf, f"Seviye {lv} / {trk['max']}", (r.x + 84, r.y + 58), 15, C["gold"], bold=True)
            draw_paragraph(surf, trk["desc"], (r.x + 30, r.y + 92), 580, 16, C["white"], max_lines=3)
            for k in range(trk["max"]):
                pygame.draw.rect(surf, C["gold"] if k < lv else (50, 56, 70), (r.right - 300 + k * 70, r.y + 30, 60, 10),
                                 border_radius=5)
        draw_text(surf, "Kıyafet etkileri: dayanıklılık radyasyon, yaralanma ve zorlu yüzey riskini; hareket kabiliyeti "
                        "tamir hızını ve yüzeyden toplanan madeni belirler.", (200, H - 46), 14, C["text_dim"], max_w=W - 240)

    def panel_rect(self):
        return pygame.Rect(W - 470, TOPBAR_H + 100, 446, H - TOPBAR_H - 130)

    def select(self, k):
        self.sel = k
        self.app.audio.play("tick")
        self.rebuild()

    def start(self, k):
        if self.act(self.game.start_research, k, ok_sound="success"):
            r = D.RESEARCH_BY_KEY[k]
            self.app.say(f"{self.game.name}, {r['name']} araştırması başladı. "
                         f"{int(self.game.research_duration())} saniye sürecek.")

    def process(self):
        gain = self.game.process_stardust()
        if gain:
            pr = self.panel_rect()
            self.ps.glow(pr.centerx, pr.bottom - 48, 40, C["violet"], speed=(60, 220))
        self.rebuild()

    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        g = self.game
        # durum değişirse kartları tazele
        sig = (tuple(g.s["research"]["done"]), bool(g.s["research"]["active"]), g.rp // 10, g.money // 50,
               tuple(g.s["suit"].values()))
        if getattr(self, "_sig", None) != sig:
            self._sig = sig
            self.rebuild()

    def draw(self, surf):
        g = self.game
        self.bg.draw(surf)
        self.draw_title(surf, sub=f"Seviye {g.lvl('research')} · Süre {int(g.research_duration())} sn · "
                                  f"Para indirimi %{int(D.RESEARCH_DISCOUNT[g.lvl('research')] * 100)} · Puan indirimi yok")
        draw_icon(surf, "rp", (W - 300, TOPBAR_H + 42), 26, C["cyan"])
        draw_text(surf, f"{fmt_num(g.rp)} Puan", (W - 280, TOPBAR_H + 28), 26, C["cyan"], bold=True)
        if self.mode == "suit":
            self.draw_suit(surf)
            self.draw_widgets(surf)
            self.ps.draw(surf)
            return
        y = TOPBAR_H + 112
        for label, planet, keys in ROWS:
            draw_text(surf, label, (40, y + 18), 16, C["text"], bold=True)
            if planet:
                draw_text(surf, f"{D.TO[planet]} git", (40, y + 44), 12, C["text_dim"])
                ok = g.s["visits"][planet] > 0
                draw_icon(surf, "check" if ok else "lock", (120, y + 70), 14, C["green"] if ok else C["text_mute"])
            y += CARD_H + 22
        self.draw_widgets(surf)
        for k, b in self.cards.items():
            self.draw_card(surf, k, b)
        self.draw_panel(surf)
        self.ps.draw(surf)

    def draw_card(self, surf, k, b):
        g = self.game
        r = D.RESEARCH_BY_KEY[k]
        st = g.research_state(k)
        rect = b.rect
        col = b.accent
        draw_icon(surf, r["icon"], (rect.x + 22, rect.y + 24), 18, col)
        name = tr(r["name"])
        if len(name) > 18 and " " in name:
            parts = name.split(" ")
            draw_text(surf, " ".join(parts[:-1]), (rect.x + 40, rect.y + 10), 13, C["text"], bold=True, raw=True,
                      max_w=rect.w - 50)
            draw_text(surf, parts[-1], (rect.x + 40, rect.y + 27), 13, C["text"], bold=True, raw=True, max_w=rect.w - 50)
        else:
            draw_text(surf, name, (rect.x + 40, rect.y + 16), 14, C["text"], bold=True, raw=True, max_w=rect.w - 50)
        rp, money = g.research_cost(k)
        if st == "done":
            draw_icon(surf, "check", (rect.right - 20, rect.y + 20), 16, C["green"])
            draw_text(surf, "TAMAMLANDI", (rect.x + 14, rect.bottom - 26), 12, C["green"], bold=True)
        elif st == "active":
            _, frac, left = g.research_progress()
            draw_bar(surf, (rect.x + 14, rect.bottom - 22, rect.w - 28, 8), frac, C["cyan"], glow=True)
            draw_text(surf, fmt_time(left), (rect.right - 14, rect.bottom - 42), 12, C["cyan"], bold=True,
                      anchor="topright")
        else:
            c1 = C["cyan"] if g.rp >= rp else C["red"]
            c2 = C["gold"] if g.money >= money else C["red"]
            if st == "locked":
                c1 = c2 = C["text_mute"]
                draw_icon(surf, "lock", (rect.right - 20, rect.y + 20), 14, C["text_mute"])
            draw_text(surf, f"{rp} Puan", (rect.x + 14, rect.bottom - 44), 13, c1, bold=True)
            draw_text(surf, f"{money} Para", (rect.x + 14, rect.bottom - 24), 13, c2, bold=True)

    def draw_panel(self, surf):
        g = self.game
        pr = self.panel_rect()
        r = D.RESEARCH_BY_KEY[self.sel]
        st = g.research_state(self.sel)
        glass_panel(surf, pr, C["cyan"], 215, 20, strong=True)
        draw_glow(surf, (pr.x + 54, pr.y + 56), 50, C["cyan"], 0.6)
        draw_icon(surf, r["icon"], (pr.x + 54, pr.y + 56), 34, C["cyan"])
        draw_text(surf, r["name"], (pr.x + 98, pr.y + 30), 22, C["text"], bold=True)
        draw_text(surf, {"done": "TAMAMLANDI", "active": "ARAŞTIRILIYOR", "available": "ARAŞTIRILABİLİR",
                         "locked": "KİLİTLİ"}[st], (pr.x + 98, pr.y + 62), 13,
                  {"done": C["green"], "active": C["cyan"], "available": C["gold"], "locked": C["text_mute"]}[st], bold=True)
        y = pr.y + 108
        draw_text(surf, "ETKİ", (pr.x + 26, y), 13, C["text_dim"], bold=True)
        draw_paragraph(surf, r["effect"], (pr.x + 26, y + 20), pr.w - 52, 16, C["text"])
        y += 70
        rp, money = g.research_cost(self.sel)
        draw_text(surf, "MALİYET", (pr.x + 26, y), 13, C["text_dim"], bold=True)
        draw_text(surf, f"{rp} Puan  +  {money} Para", (pr.x + 26, y + 20), 18, C["gold"], bold=True)
        if money < r["money"]:
            draw_text(surf, f"(liste {r['money']} Para, merkez indirimi uygulandı)", (pr.x + 26, y + 44), 12, C["text_mute"])
        y += 70
        draw_text(surf, "ŞART", (pr.x + 26, y), 13, C["text_dim"], bold=True)
        draw_text(surf, g.req_text(r["req"]), (pr.x + 26, y + 20), 16,
                  C["green"] if g.req_met(r["req"]) else C["red"])
        ap = g.research_progress()
        if ap:
            k, frac, left = ap
            cy = pr.y + 450
            radial_progress(surf, (pr.centerx, cy), 54, frac, C["cyan"], 6)
            draw_text(surf, fmt_time(left), (pr.centerx, cy), 22, C["text"], bold=True, anchor="center")
            draw_text(surf, D.RESEARCH_BY_KEY[k]["name"], (pr.centerx, cy + 66), 14, C["cyan"], bold=True,
                      anchor="midtop")
        draw_text(surf, "Puan kaynakları: Yıldız Tozu ×10 · Uydu kurtarma +100 · İlk iniş +200 · Fotoğraf +20 · "
                        "Bilim İnsanı +50", (40, H - 34), 13, C["text_mute"])

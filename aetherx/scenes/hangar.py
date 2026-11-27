# -*- coding: utf-8 -*-
"""
MONTAJ HANGARI - ROKET TASARIMI
AŞAMA 1 Gövde · 2 Motor · 3 Elektrik · 4 İletişim · 5 Araştırma Yükü ·
6 Yakıt + Risk · 7 Simüle Et / NOVA'ya Sor / Fırlat
(+ Hedef seçimi ve Mürettebat)
"""
import copy
import math
import random

import pygame

from . import Scene
from .. import i18n
from .. import art
from .. import data as D
from .. import rocket as R
from ..config import C, H, TOPBAR_H, W, MARKET_FUEL_PRICE
from ..fx import overlay, ParticleSystem, Spring, clamp, draw_glow, ease_out_cubic, lerp_color, scale_color, draw_grid
from ..ui import (UI, Button, Slider, chip, draw_bar, draw_icon, draw_paragraph, draw_risk_bars, draw_text,
                  glass_panel, fmt_num, text_size, wrap_text, dashed_line)

STAGES = [
    ("target", "HEDEF", "planet"),
    ("hull", "1 · GÖVDE", "box"),
    ("engine", "2 · MOTOR", "fuel"),
    ("power", "3 · ELEKTRİK", "bolt"),
    ("antenna", "4 · İLETİŞİM", "antenna"),
    ("payload", "5 · ARAŞTIRMA YÜKÜ", "flask"),
    ("crew", "MÜRETTEBAT", "astro"),
    ("fuel", "6 · YAKIT + RİSK", "chart"),
]
MODES = [("kesif", "KEŞİF", "Yörünge, fotoğraf, veri"), ("inis", "İNİŞ", "Yüzeye in, maden topla"),
         ("koloni", "KOLONİ SEFERİ", "Koloni kur / ikmal")]

OPT_X, OPT_Y, OPT_W = 300, TOPBAR_H + 96, 604
PREV_X, PREV_W = 920, 330
STAT_X, STAT_W = 1266, 310


class HangarScene(Scene):
    music = "base"
    ambient = "amb_hangar"
    title = "MONTAJ HANGARI"
    title_icon = "wrench"
    accent = C["orange"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("ember", 41, 0.7)
        self.ps = ParticleSystem(600)
        self.stage = "target"
        self.design = None
        self.rep = None
        self.rot = 0.0
        self.sim = None
        self.sim_t = 0.0
        self.review = []
        self.highlight = set()
        self.alarm_t = 0.0
        self.recalc_t = 0.0
        self.opt_buttons = []
        self.fuel_slider = None
        self.tint = Spring(0.0, 40, 10)

    # ------------------------------------------------------------------ giriş
    def enter(self, planet=None, mode=None, **kw):
        g = self.game
        d = copy.deepcopy(g.s.get("last_design")) or R.empty_design("moon")
        avail = {c["id"] for c in g.crew_available()}
        d["crew"] = [c for c in d.get("crew", []) if c in avail]
        if planet:
            d["planet"] = planet
        for k, v in R.empty_design().items():
            d.setdefault(k, v)
        if mode:
            d["mode"] = mode
        self.design = d
        self.stage = "target"
        self.sim = None
        self.review = []
        self.highlight = set()
        self.recalc()
        self.rebuild()

    def recalc(self):
        self.rep = R.analyze(self.game, self.design)

    def set_part(self, slot, key):
        g = self.game
        if slot == "payload":
            pl = self.design["payloads"]
            if key in pl:
                pl.remove(key)
            else:
                if len(pl) >= D.MAX_PAYLOADS:
                    self.app.toast("En fazla 3 yük seçebilirsin (4'ten 3)", "orange", "warning")
                    self.app.audio.play("deny")
                    return
                pl.append(key)
        else:
            self.design[slot] = key
        self.app.audio.play("clunk", 0.8)
        cx = PREV_X + PREV_W // 2
        self.ps.sparks(cx + random.uniform(-40, 40), 420 + random.uniform(-60, 60), 18, C["gold"])
        if slot == "hull":
            seats = D.PART["hull"][key]["seats"]
            self.design["crew"] = self.design["crew"][:seats]
        self.sim = None
        self.highlight.discard(slot)
        self.recalc()
        self.rebuild()

    def buy(self, slot, key):
        if self.act(self.game.buy_part, slot, key, ok_sound="coin"):
            self.set_part(slot, key)

    def set_stage(self, st):
        self.stage = st
        self.rebuild()

    # --------------------------------------------------------------- widget'lar
    def rebuild(self):
        g = self.game
        if self.design is None:
            return
        self.recalc()
        self.widgets = []
        self.back_button("base", "ÜS")
        # aşama listesi
        y = TOPBAR_H + 96
        for key, label, icon in STAGES:
            b = self.add(Button((24, y, 258, 62), label, (lambda k=key: self.set_stage(k)), accent=C["orange"],
                                icon=icon, size=15, style="tab"))
            b.selected = (self.stage == key)
            b.sublabel = self.stage_summary(key)
            if key in self.highlight:
                b.accent = C["red"]
                b.pulse = True
            y += 70
        # seçenekler
        self.fuel_slider = None
        fn = getattr(self, "opts_" + self.stage)
        fn()
        # alt butonlar
        by = H - 82
        self.add(Button((300, by, 210, 60), "SİMÜLE ET", self.start_sim, accent=C["cyan"], icon="play", size=17,
                        tooltip="5 saniyelik sanal uçuş. Bedava ve sınırsız."))
        self.add(Button((520, by, 210, 60), "NOVA'YA SOR", self.ask_nova, accent=C["cyan"], icon="nova", size=17,
                        hotkey=pygame.K_n))
        pb = self.add(Button((740, by, 250, 60), "RAMPAYA HAZIRLA", self.prepare, accent=C["orange"], icon="rocket",
                             size=16, tooltip="Rampada hazırlansın; üsten fırlat. Aynı anda 3 roket."))
        ok = self.rep["ok"]
        low = self.rep["risk_level"] < 0.2
        lab = "FIRLATMAYA HAZIR" if low else "RİSKLİ AMA FIRLAT"
        fb = self.add(Button((1000, by, 576, 66), lab, self.launch, accent=C["green"] if low else C["red"],
                             icon="rocket", size=22, style="big", hotkey=pygame.K_SPACE))
        fb.rect.y = by - 3
        if not ok:
            reason = self.rep["blockers"][0] if self.rep["blockers"] else ""
            fb.set_enabled(False, reason)
            pb.set_enabled(False, reason)
            fb.label = "FIRLATILAMAZ"
        else:
            fb.pulse = True

    def stage_summary(self, key):
        d = self.design
        if key == "target":
            return f"{D.PLANET[d['planet']]['name']} · {dict((m, l) for m, l, _ in MODES)[d['mode']].title()}"
        if key in ("hull", "engine", "power", "antenna"):
            p = D.PART[key].get(d.get(key))
            return p["name"] if p else "-"
        if key == "payload":
            return ", ".join(i18n.tr(D.PART["payload"][k]["name"]) for k in d["payloads"]) or "Yok"
        if key == "crew":
            hull = D.PART["hull"].get(d["hull"])
            return f"{len(d['crew'])}/{hull['seats'] if hull else 0} koltuk"
        if key == "fuel":
            return f"Yakıt %{int(d['fuel_pct'] * 100)} · Risk {self.rep['risk_label']}"
        return ""

    def card(self, i, title, lines, status, on_click, selected=False, locked=False, accent=None, buy=None, icon=None):
        col = i % 2
        row = i // 2
        r = pygame.Rect(OPT_X + col * 304, OPT_Y + 56 + row * 132, 296, 122)
        acc = accent or C["orange"]
        b = self.add(Button(r, "", on_click, accent=acc if not locked else (90, 100, 125), size=14))
        b.selected = selected
        b.data = {"title": title, "lines": lines, "status": status, "locked": locked, "icon": icon}
        self.opt_buttons.append(b)
        if buy:
            bb = self.add(Button((r.right - 118, r.bottom - 40, 108, 32), f"AL {buy[2]}", (lambda: self.buy(buy[0], buy[1])),
                                 accent=C["gold"], size=13, icon="money"))
            ok = self.game.money >= buy[2]
            bb.set_enabled(ok, f"{buy[2]} Para gerekli")
        return b

    def part_cards(self, slot, describe):
        g = self.game
        self.opt_buttons = []
        for i, p in enumerate(D.PARTS[slot]):
            owned = g.part_owned(slot, p["key"])
            unlocked = g.part_unlocked(slot, p["key"])
            sel = (self.design.get(slot) == p["key"]) if slot != "payload" else (p["key"] in self.design["payloads"])
            if owned:
                status = "SEÇİLİ" if sel else "Sahipsin"
            elif unlocked:
                status = f"Satın al: {p['cost']} P"
            else:
                r = D.RESEARCH_BY_KEY.get(p.get("research"), {})
                status = f"Araştırma: {r.get('name', '?')}"
            buy = (slot, p["key"], p["cost"]) if (unlocked and not owned) else None
            self.card(i, p["name"], describe(p), status,
                      (lambda k=p["key"], o=owned: self.set_part(slot, k) if o else self.app.toast(
                          "Önce satın almalısın" if g.part_unlocked(slot, k) else "Araştırma gerekli", "orange", "lock")),
                      selected=sel, locked=not unlocked, buy=buy, icon=p.get("icon"))

    # ------------------------------------------------------------ aşamalar
    def opts_target(self):
        g = self.game
        self.opt_buttons = []
        for i, key in enumerate(D.PLANET_ORDER):
            p = D.PLANET[key]
            un = g.planet_unlocked(key)
            lines = [f"{p['distance']} · {p['difficulty']}", f"Maden: {D.MINERAL[p['mineral']]['name']}",
                     p["special"]]
            st = "SEÇİLİ" if self.design["planet"] == key else ("Açık" if un else g.req_text(p["unlock"]))
            self.card(i, p["name"], lines, st, (lambda k=key, u=un: self.set_target(k) if u else self.app.toast(
                g.req_text(D.PLANET[k]["unlock"]), "orange", "lock")),
                      selected=self.design["planet"] == key, locked=not un, accent=p["glow"], icon="planet")
        y = OPT_Y + 56 + 2 * 132 + 30
        for i, (m, lab, sub) in enumerate(MODES):
            b = self.add(Button((OPT_X + i * 202, y, 194, 70), lab, (lambda k=m: self.set_mode(k)),
                                accent=C["cyan"], size=16, style="tab"))
            b.sublabel = sub
            b.selected = self.design["mode"] == m

    def set_target(self, k):
        self.design["planet"] = k
        self.app.audio.play("clunk", 0.6)
        self.sim = None
        self.rebuild()

    def set_mode(self, m):
        self.design["mode"] = m
        self.app.audio.play("clunk", 0.6)
        self.sim = None
        self.rebuild()

    def opts_hull(self):
        self.part_cards("hull", lambda p: [f"Taşıma {p['capacity']} kg · Koltuk {p['seats']}",
                                           f"Dayanıklılık: {D.DUR_LABEL[p['dur']]}",
                                           f"Hız: {D.speed_label(p['speed'])} · {D.ROCKET_SIZE_NAME[p['size']]} sınıf"])

    def opts_engine(self):
        def desc(p):
            lift = "Güçlü" if p["lift"] >= 1.3 else "Dengeli" if p["lift"] >= 1.1 else "Zayıf"
            burn = "Çok yakar" if p["burn"] > 1.2 else "Orta" if p["burn"] >= 0.8 else "Az yakar" if p["burn"] > 0 else "0 yakıt"
            return [f"Kalkış: {lift} · {burn}", f"Hız ×{p['speed']:.2f}" + (" > ×1.7" if p['key'] == 'ion' else ""),
                    p["desc"]]
        self.part_cards("engine", desc)

    def opts_power(self):
        self.part_cards("power", lambda p: [f"Kapasite {p['cap']} · Üretim {p['gen']}/sn",
                                            {"battery": "Şarj olmaz", "solar": "Karanlıkta 0", "rtg": "Her zaman sabit",
                                             "fuelcell": "Yakıt tüketir"}[p["kind"]], p["desc"]])

    def opts_antenna(self):
        self.part_cards("antenna", lambda p: [f"Menzil: {D.RANGE_NAME[p['range']]}", f"Kütle {p['mass']} kg",
                                              p["desc"]])

    def opts_payload(self):
        self.part_cards("payload", lambda p: [f"Kütle {p['mass']} kg · Elektrik {p['draw']}", p["desc"]])

    def opts_crew(self):
        g = self.game
        self.opt_buttons = []
        hull = D.PART["hull"].get(self.design["hull"])
        seats = hull["seats"] if hull else 0
        crew = [c for c in g.s["crew"] if c["status"] in ("ready",)]
        for i, c in enumerate(crew[:10]):
            t = D.CREW_TYPE[c["type"]]
            sel = c["id"] in self.design["crew"]
            lines = [f"{t['name']} · Rütbe {c['rank']}", "YORGUN" if c["tired"] else "Dinç", t["desc"]]
            b = self.card(i, c["name"], lines, "SEÇİLİ" if sel else "Hazır", (lambda cid=c["id"]: self.toggle_crew(cid)),
                          selected=sel, accent=tuple(art.CREW_COLORS[c["type"]]))
            b.data["crew"] = c
        if seats == 0:
            self.add(Button((OPT_X, OPT_Y + 56, 600, 60), "Bu gövde insansız (koltuk yok)", None, accent=C["text_dim"],
                            size=15, style="ghost"))

    def toggle_crew(self, cid):
        hull = D.PART["hull"].get(self.design["hull"])
        seats = hull["seats"] if hull else 0
        cl = self.design["crew"]
        if cid in cl:
            cl.remove(cid)
        else:
            if len(cl) >= seats:
                self.app.toast(f"Bu gövdede {seats} koltuk var", "orange", "warning")
                self.app.audio.play("deny")
                return
            cl.append(cid)
        self.app.audio.play("clunk", 0.5)
        self.sim = None
        self.rebuild()

    def opts_fuel(self):
        self.opt_buttons = []
        self.fuel_slider = self.add(Slider((OPT_X + 30, OPT_Y + 120, 540, 30), self.design["fuel_pct"], self.on_fuel,
                                           C["orange"], "YAKIT", steps=20))

    def on_fuel(self, v):
        self.design["fuel_pct"] = v
        self.sim = None
        self.recalc()
        if v >= 0.98:
            self.app.toast("Çok ağır oldun!", "orange", "warning")

    # ------------------------------------------------------------ eylemler
    def ask_nova(self):
        self.review = self.app.nova.review(self.rep)
        self.highlight = {sl for _, sl in self.review if sl}
        if not self.review:
            self.app.say(f"{self.game.name}, her şey yolunda görünüyor.", "happy")
        for txt, sl in self.review[:4]:
            self.app.say(txt, "alert" if sl else "calm")
        self.rebuild()

    def start_sim(self):
        acc = {1: 0.7, 2: 0.85, 3: 1.0}[max(1, self.game.lvl("control"))]
        self.sim = R.simulate(self.rep, 500, acc)
        self.sim_t = 0.0
        self.game.s["last_sim"] = {"planet": self.design["planet"], "dist": self.sim["dist"],
                                   "points": self.sim["points"], "day": self.game.day}
        self.app.audio.play("whoosh", 0.6)

    def prepare(self):
        idx, why = self.game.reserve_pad(self.design, self.rep, prep=True)
        if idx is None:
            self.app.toast(why, "red", "warning")
            self.app.audio.play("deny")
            return
        self.app.toast(f"{D.PAD_NAME[idx + 1]}: roket hazırlanıyor", "orange", "rocket")
        self.app.audio.play("clunk")
        self.app.say(f"{self.game.name}, roket {D.PAD_NAME[idx + 1]}'ya taşındı. Hazır olunca üsten fırlatabilirsin.")
        self.enter(planet=self.design["planet"])

    def launch(self):
        idx, why = self.game.reserve_pad(self.design, self.rep, prep=False)
        if idx is None:
            self.app.toast(why, "red", "warning")
            self.app.audio.play("deny")
            return
        self.app.go("launch", pad=idx)

    # ----------------------------------------------------------------- döngü
    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        self.rot += dt * 0.7
        self.recalc_t += dt
        if self.recalc_t > 1.0:
            self.recalc_t = 0
            self.recalc()
        if self.sim:
            self.sim_t += dt
        lvl = self.rep["risk_level"] if self.rep else 0
        self.tint.target = clamp((lvl - 0.25) * 2.5, -1, 1)
        self.tint.update(dt)
        if lvl > 0.45:
            self.alarm_t += dt
            if self.alarm_t > 3.5:                 # tekrar eden alarm sesi kaldırıldı (görsel uyarı yeterli)
                self.alarm_t = 0

    def draw(self, surf):
        self.bg.draw(surf)
        t = self.t
        k = self.tint.value
        if k > 0:
            overlay(surf, (255, 40, 60, int(40 * k * (0.7 + 0.3 * math.sin(t * 4)))))
        else:
            overlay(surf, (40, 120, 255, int(-28 * k)))
        self.draw_title(surf, sub=f"{self.game.name} · Hangar Sv{self.game.lvl('hangar')} · "
                                  f"{D.ROCKET_SIZE_NAME[self.game.lvl('hangar')]} rokete kadar")
        # seçenek paneli
        pr = pygame.Rect(OPT_X - 10, OPT_Y - 4, OPT_W + 14, H - OPT_Y - 100)
        glass_panel(surf, pr, C["orange"], 150, 18)
        label = dict((k, l) for k, l, _ in STAGES)[self.stage]
        draw_text(surf, label, (OPT_X + 10, OPT_Y + 10), 20, C["text"], bold=True)
        self.draw_widgets(surf)
        self.draw_cards(surf)
        if self.stage == "fuel":
            self.draw_fuel_stage(surf)
        if self.stage == "payload":
            draw_text(surf, f"Seçili: {len(self.design['payloads'])}/3", (OPT_X + OPT_W - 10, OPT_Y + 14), 15,
                      C["gold"], bold=True, anchor="topright")
        self.draw_preview(surf, t)
        self.draw_stats(surf)
        if self.sim:
            self.draw_sim(surf)
        self.ps.draw(surf)

    def draw_cards(self, surf):
        for b in self.opt_buttons:
            if not b.visible or not isinstance(b.data, dict):
                continue
            d = b.data
            r = b.rect
            col = b.accent
            x = r.x + 16
            if d.get("crew"):
                art.draw_astronaut(surf, r.x + 34, r.y + 58, d["crew"]["type"], 0.9, self.t, d["crew"]["tired"])
                x = r.x + 66
            elif d.get("icon"):
                draw_icon(surf, d["icon"], (r.x + 26, r.y + 24), 18, col)
                x = r.x + 44
            draw_text(surf, d["title"], (x, r.y + 12), 17, C["text"] if not d["locked"] else C["text_mute"], bold=True)
            col = C["text_dim"] if not d["locked"] else C["text_mute"]
            for i, ln in enumerate(d["lines"][:3]):
                if not ln:
                    continue
                if len(ln) > 40 and "{" not in ln:          # uzun açıklama: çevir, sar, kalan satırlara sığdır
                    draw_paragraph(surf, ln, (x, r.y + 38 + i * 19), r.right - x - 12, 12, col, gap=2, max_lines=3 - i)
                    break
                draw_text(surf, ln, (x, r.y + 38 + i * 19), 13, col, max_w=r.right - x - 12)
            stc = C["green"] if d["status"] == "SEÇİLİ" else C["gold"] if d["status"].startswith("Satın") else \
                C["text_mute"] if d["locked"] else C["text_dim"]
            if not d["status"].startswith("Satın"):
                draw_text(surf, d["status"], (r.right - 12, r.bottom - 22), 12, stc, bold=True, anchor="topright", max_w=r.w - 30)
            if d["status"] == "SEÇİLİ":
                draw_icon(surf, "check", (r.right - 20, r.y + 20), 16, C["green"])
            if d["locked"]:
                draw_icon(surf, "lock", (r.right - 20, r.y + 20), 16, C["text_mute"])

    def draw_fuel_stage(self, surf):
        rep = self.rep
        hull = rep.get("hull")
        x, y = OPT_X + 30, OPT_Y + 170
        # saydam depo
        tank = pygame.Rect(x, y, 150, 300)
        glass_panel(surf, tank, C["orange"], 90, 30, glow=False)
        fill = tank.inflate(-16, -16)
        h = int(fill.h * self.design["fuel_pct"])
        fr = pygame.Rect(fill.x, fill.bottom - h, fill.w, h)
        if h > 0:
            wave = pygame.Surface(fr.size, pygame.SRCALPHA)
            for yy in range(fr.h):
                kk = yy / max(1, fr.h)
                pygame.draw.line(wave, (*lerp_color((255, 190, 80), (220, 90, 20), kk), 220), (0, yy), (fr.w, yy))
            surf.blit(wave, fr)
            pts = [(fr.x + i * fr.w / 16, fr.y + math.sin(self.t * 3 + i * 0.7) * 4) for i in range(17)]
            pygame.draw.lines(surf, (255, 230, 160), False, pts, 2)
            for i in range(5):
                bx = fr.x + 15 + (i * 37 + self.t * 20) % (fr.w - 30)
                by = fr.bottom - ((self.t * 40 + i * 50) % max(1, fr.h))
                pygame.draw.circle(surf, (255, 240, 200), (int(bx), int(by)), 3, 1)
        draw_text(surf, f"{rep.get('fuel_kg', 0):.0f} kg", (tank.centerx, tank.bottom + 10), 20, C["text"], bold=True,
                  anchor="midtop")
        if self.design["fuel_pct"] >= 0.98 or "Çok ağır oldun!" in rep["warnings"]:
            k = 0.5 + 0.5 * math.sin(self.t * 8)
            draw_text(surf, "ÇOK AĞIR OLDUN!", (tank.centerx, tank.y - 34), 18, lerp_color(C["orange"], C["red"], k),
                      bold=True, anchor="midtop")
        # yakıt kaynağı
        sx = x + 190
        g = self.game
        lines = [
            ("Depo stoğu", f"{int(g.s['fuel'])} kg"),
            ("Gereken (dönüş dahil)", f"{rep.get('fuel_need', 0) * R.RETURN_RESERVE:.0f} kg"),
            ("Yakıt payı", f"×{rep.get('fuel_margin', 0):.2f}" if rep.get("fuel_margin", 0) < 9 else "Yakıtsız"),
            ("Marketten alınacak", f"{rep.get('fuel_short', 0):.0f} kg ({rep.get('fuel_cost', 0)} P)"),
        ]
        for i, (a, b) in enumerate(lines):
            draw_text(surf, a, (sx, y + i * 30), 15, C["text_dim"])
            draw_text(surf, b, (sx + 370, y + i * 30), 15, C["text"], bold=True, anchor="topright")
        draw_text(surf, "RİSK PANELİ", (sx, y + 140), 15, C["orange"], bold=True)
        r = rep["risk"]
        draw_risk_bars(surf, (sx, y + 160, 370, 150), r["fail"], r["partial"], r["success"])
        draw_paragraph(surf, "Risk; Dayanıklılık + Motor + Yakıt + Elektrik + Menzil + Mürettebat ile hesaplanır. "
                             "Can barı yoktur.", (sx, y + 320), 370, 13, C["text_mute"])

    def slot_pos(self, slot, cx, cy):
        return {"hull": (cx, cy), "engine": (cx, cy + 95), "power": (cx - 85, cy), "antenna": (cx, cy - 115),
                "payload": (cx + 40, cy - 20), "fuel": (cx, cy + 40), "crew": (cx, cy - 30),
                "target": (cx, cy - 170)}.get(slot, (cx, cy))

    def draw_preview(self, surf, t):
        g = self.game
        d = self.design
        r = pygame.Rect(PREV_X, OPT_Y - 4, PREV_W, H - OPT_Y - 100)
        glass_panel(surf, r, g.color, 120, 18)
        draw_grid(surf, (r.x + 10, r.y + 10, r.w - 20, r.h - 20), g.color, 30, 0.12, t)
        draw_text(surf, "ROKET ÖNİZLEME", (r.centerx, r.y + 12), 13, C["text_dim"], bold=True, anchor="midtop")
        craft, nozzle = art.render_spacecraft(d.get("hull"), d.get("engine"), d.get("power"), d.get("antenna"),
                                              d.get("payloads"), g.name, g.color, 1.0, t)
        cx, cy = r.centerx, r.centery - 10
        # 3D dönüş illüzyonu
        c = math.cos(self.rot)
        sx = max(0.18, abs(c))
        img = pygame.transform.smoothscale(craft, (max(4, int(craft.get_width() * sx)), craft.get_height()))
        if c < 0:
            img = pygame.transform.flip(img, True, False)
        shade = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, int(110 * (1 - sx))))
        img.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        draw_glow(surf, (cx, cy), 160, scale_color(g.color, 0.5), 0.35)
        bob = math.sin(t * 1.5) * 6
        surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2 + bob))
        # platform
        pygame.draw.ellipse(surf, scale_color(g.color, 0.5), (cx - 120, r.bottom - 90, 240, 40), 2)
        pygame.draw.ellipse(surf, scale_color(g.color, 0.25), (cx - 90, r.bottom - 82, 180, 24), 1)
        for i in range(10):
            a = t * 0.8 + i * 0.63
            draw_glow(surf, (cx + math.cos(a) * 120, r.bottom - 70 + math.sin(a) * 20), 6, g.color, 0.6)
        # aktif slot yanıp sönsün
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        sp = self.slot_pos(self.stage, cx, cy + bob)
        pygame.draw.circle(surf, scale_color(C["orange"], 0.6 + 0.4 * pulse), (int(sp[0]), int(sp[1])),
                           int(26 + 6 * pulse), 2)
        draw_glow(surf, sp, 30, C["orange"], 0.4 * pulse)
        # NOVA'nın kırmızı daireleri
        for sl in self.highlight:
            hp = self.slot_pos(sl, cx, cy + bob)
            rr = int(34 + 4 * math.sin(t * 8))
            pygame.draw.circle(surf, C["red"], (int(hp[0]), int(hp[1])), rr, 3)
            draw_glow(surf, hp, rr, C["red"], 0.5)
        rep = self.rep
        draw_text(surf, f"{D.ROCKET_SIZE_NAME.get(rep.get('size', 1), '?')} roket · {D.PAD_NAME.get(rep.get('size', 1))}",
                  (r.centerx, r.bottom - 40), 14, C["text"], bold=True, anchor="midtop")

    def draw_stats(self, surf):
        rep = self.rep
        g = self.game
        r = pygame.Rect(STAT_X, OPT_Y - 4, STAT_W, H - OPT_Y - 100)
        glass_panel(surf, r, C["cyan"], 160, 18)
        x, y, w = r.x + 18, r.y + 16, r.w - 36
        draw_text(surf, "TELEMETRİ", (x, y), 15, C["cyan"], bold=True)
        y += 28

        def row(label, val, col=C["text"], ok=None):
            nonlocal y
            draw_text(surf, label, (x, y), 14, C["text_dim"])
            vc = col if ok is None else (C["green"] if ok else C["red"])
            draw_text(surf, val, (x + w, y), 14, vc, bold=True, anchor="topright")
            y += 22
        cap = rep.get("capacity", 0) or 1
        row("Yük / Taşıma", f"{rep.get('mounted', 0):.0f} / {cap} kg", ok=rep.get("mounted", 0) <= cap)
        row("Kalkış kütlesi", f"{rep.get('total', 0):.0f} / {rep.get('lift', 0)} kg", ok=rep.get("total", 0) <= rep.get("lift", 1))
        row("Hız", f"×{rep.get('speed', 0):.2f}")
        row("Yolculuk", f"{rep.get('flight_sec', 0):.0f} sn")
        row("Yakıt payı", f"×{min(9.9, rep.get('fuel_margin', 0)):.2f}", ok=rep.get("fuel_margin", 0) >= 1)
        bal = rep.get("e_balance", 0)
        row("Elektrik dengesi", f"{bal:+.1f}/sn", ok=rep.get("e_frac", 0) >= 1)
        row("Menzil", "BAĞLI" if rep.get("link_ok") else "KOPUK", ok=rep.get("link_ok"))
        if rep.get("crew_n"):
            row("Oksijen", f"×{min(9.9, rep.get('o2_ratio', 0)):.2f}", ok=rep.get("o2_ratio", 0) >= 1)
        row("Mürettebat", f"{rep.get('crew_n', 0)} kişi" + (" · Pilot" if rep.get("pilot") else ""))
        y += 6
        draw_text(surf, "MALİYET", (x, y), 14, C["gold"], bold=True)
        draw_text(surf, f"{rep.get('cost', 0)} P", (x + w, y), 18, C["gold"], bold=True, anchor="topright")
        y += 22
        draw_text(surf, f"Montaj {rep.get('assembly', 0)} · Rampa {rep.get('pad_fee', 0)} · Yakıt {rep.get('fuel_cost', 0)}",
                  (x, y), 12, C["text_mute"])
        y += 26
        risk = rep["risk"]
        draw_risk_bars(surf, (x, y, w, 132), risk["fail"], risk["partial"], risk["success"])
        y += 140
        if rep["blockers"]:
            draw_icon(surf, "warning", (x + 8, y + 9), 16, C["red"])
            draw_paragraph(surf, rep["blockers"][0], (x + 24, y), w - 24, 13, C["red"], max_lines=3)
        elif rep["warnings"]:
            draw_icon(surf, "warning", (x + 8, y + 9), 16, C["orange"])
            draw_paragraph(surf, rep["warnings"][0], (x + 24, y), w - 24, 13, C["orange"], max_lines=2)
        else:
            draw_icon(surf, "check", (x + 8, y + 9), 16, C["green"])
            draw_text(surf, "Tasarım geçerli", (x + 24, y), 13, C["green"], bold=True)

    def draw_sim(self, surf):
        rep = self.rep
        sim = self.sim
        T = 5.0
        k = clamp(self.sim_t / T, 0, 1)
        r = pygame.Rect(OPT_X - 10, OPT_Y + 330, OPT_W + PREV_W + 30, 230)
        glass_panel(surf, r, C["cyan"], 235, 18, strong=True)
        draw_text(surf, "SANAL UÇUŞ SİMÜLASYONU", (r.x + 20, r.y + 14), 16, C["cyan"], bold=True)
        draw_text(surf, "Görev Kontrol Merkezi'nde de görünür", (r.right - 20, r.y + 16), 12, C["text_dim"],
                  anchor="topright")
        x0, x1 = r.x + 70, r.right - 70
        ly = r.y + 90
        pl = D.PLANET[rep["planet"]]
        # bölgeler
        for a, b, kind in pl["zones"]:
            col = {"asteroids": C["orange"], "belt": C["red"], "dark": (60, 60, 90), "stardust": C["cyan"],
                   "debris": C["steel"], "heat": C["gold"], "radiation": C["violet"]}.get(kind, C["text_dim"])
            pygame.draw.rect(surf, scale_color(col, 0.5), (x0 + (x1 - x0) * a, ly - 10, (x1 - x0) * (b - a), 20),
                             border_radius=6)
        pygame.draw.line(surf, C["text_dim"], (x0, ly), (x1, ly), 2)
        art.draw_planet(surf, "earth", (x0 - 30, ly), 22, glow=False)
        art.draw_planet(surf, rep["planet"], (x1 + 30, ly), 24, glow=False)
        px = x0 + (x1 - x0) * k
        draw_glow(surf, (px, ly), 22, C["white"], 0.9)
        pygame.draw.circle(surf, C["white"], (int(px), ly), 6)
        for reason, frac, p in sim["points"]:
            fx = x0 + (x1 - x0) * frac
            if k >= frac:
                col = C["red"] if "bitti" in reason or "kayb" in reason or "kontrol" in reason else C["gold"]
                pygame.draw.line(surf, col, (fx, ly - 18), (fx, ly + 26), 2)
                draw_icon(surf, "warning", (fx, ly - 30), 16, col)
                draw_text(surf, f"{reason} (%{int(p * 100)})", (fx, ly + 32), 12, col, anchor="midtop")
        if k >= 1:
            dist = sim["dist"]
            txt = f"Başarı %{int(round(dist['success'] * 100))} · Kısmi %{int(round(dist['partial'] * 100))} · " \
                  f"Başarısız %{int(round(dist['fail'] * 100))}"
            draw_text(surf, txt, (r.centerx, r.bottom - 52), 24, C["text"], bold=True, anchor="midtop", glow=C["cyan"])
        else:
            draw_text(surf, f"Simüle ediliyor... {int(k * 100)}%", (r.centerx, r.bottom - 48), 18, C["cyan"],
                      anchor="midtop")

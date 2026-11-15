# -*- coding: utf-8 -*-
"""
AI KONTROL MERKEZİ - NOVA'NIN EVİ
Simsiyah oda, mavi göz gibi parlayan dev ekran, konuşurken ağzı oynayan yüz.
"Merhaba [Ajans İsmi], bugün ne yapalım?"
"""
import math
import random

import pygame

from . import Scene
from .. import data as D
from ..config import C, H, MIN_PER_DAY, TOPBAR_H, W
from ..fx import ParticleSystem, draw_glow, scale_color, clamp
from ..i18n import tr
from ..nova import draw_nova_face
from ..ui import UI, Button, draw_icon, draw_paragraph, draw_text, glass_panel, fmt_num, wrap_text


class NovaRoomScene(Scene):
    music = "space"
    ambient = "amb_space"
    title = "AI KONTROL MERKEZİ"
    title_icon = "nova"
    accent = C["cyan"]

    def __init__(self, app):
        super().__init__(app)
        self.ps = ParticleSystem(600)
        self.chat = []
        self.talk_t = 0.0

    def enter(self, **kw):
        g = self.game
        greet = self.app.nova.greet()
        self.chat = [("nova", tr(greet))]
        self.talk_t = 2.5
        self.app.audio.speak(greet)
        self.rebuild()

    def rebuild(self):
        g = self.game
        self.widgets = []
        self.back_button()
        x = W - 520
        y = TOPBAR_H + 120
        for label, key in self.app.nova.ask_menu():
            self.add(Button((x, y, 480, 52), label, (lambda k=key, l=label: self.ask(k, l)), accent=C["cyan"], size=16,
                            icon="nova"))
            y += 62
        cost = g.upgrade_cost("nova")
        if cost is not None:
            nxt = g.lvl("nova") + 1
            ub = self.add(Button((x, H - 150, 480, 60), f"NOVA SEVİYE {nxt} · {fmt_num(cost)} P",
                                 lambda: self.upgrade(), accent=C["gold"], icon="star", size=17, style="big",
                                 tooltip=D.BUILDING["nova"]["levels"][nxt]))
            ok, why = g.can_upgrade("nova")
            ub.set_enabled(ok, why)
            ub.pulse = ok

    def upgrade(self):
        if self.act(self.game.upgrade, "nova", ok_sound="levelup"):
            lv = self.game.lvl("nova")
            txt = {2: "Artık detaylı ve sayısal tavsiye verebiliyorum.",
                   3: "Artık geleceği tahmin edebiliyorum: fırtınaları ve en iyi fırlatma saatini söylerim."}.get(lv, "")
            self.push("nova", f"{self.game.name}, çekirdeklerim yükseltildi! Seviye {lv}. {txt}")
            for i in range(40):
                self.ps.glow(340, 390, 3, C["cyan"], speed=(80, 300))
        self.rebuild()

    def ask(self, key, label):
        self.push("you", label)
        self.push("nova", self.app.nova.answer(key))

    def push(self, who, text):
        text = tr(text)
        self.chat.append((who, text))
        del self.chat[:-8]
        if who == "nova":
            self.talk_t = 1.5 + len(text) * 0.04
            self.app.audio.speak(text)

    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        self.talk_t = max(0.0, self.talk_t - dt)
        if random.random() < 0.3:
            self.ps.glow(random.uniform(0, W), H + 5, 1, C["cyan"], speed=(10, 40), size=(1, 2), life=(4, 7), grav=-18)

    def draw(self, surf):
        g = self.game
        t = self.t
        surf.fill((2, 3, 8))
        # oda: duvar panelleri
        for i in range(12):
            x = i * 140
            pygame.draw.rect(surf, (6, 8, 16), (x + 4, TOPBAR_H + 4, 132, H), border_radius=6)
            pygame.draw.line(surf, scale_color(C["cyan"], 0.08 + 0.05 * math.sin(t + i)), (x + 70, TOPBAR_H), (x + 70, H), 1)
        self.ps.draw(surf)
        self.draw_title(surf, sub=f"NOVA Seviye {g.lvl('nova')} · {D.BUILDING['nova']['levels'][max(1, g.lvl('nova'))]}")
        cx, cy = 340, 390
        lv = max(1, g.lvl("nova"))
        draw_glow(surf, (cx, cy), 380, scale_color(C["cyan"], 0.4), 0.4 + 0.1 * math.sin(t))
        draw_nova_face(surf, (cx, cy), 190, t, 1.0 if self.talk_t > 0 else 0.0,
                       "happy" if self.talk_t > 0 and "Tebrik" in self.chat[-1][1] else "calm", lv)
        draw_text(surf, "N O V A", (cx, cy + 250), 30, C["cyan"], bold=True, anchor="midtop", glow=C["cyan"])
        # sohbet
        r = pygame.Rect(620, TOPBAR_H + 110, W - 520 - 640, H - TOPBAR_H - 260)
        glass_panel(surf, r, C["cyan"], 160, 18)
        y = r.bottom - 20
        for who, text in reversed(self.chat):
            lines = wrap_text(text, 15, r.w - 60, raw=True)
            h = len(lines) * 20 + 18
            y -= h
            if y < r.y + 10:
                break
            bx = r.x + 16 if who == "nova" else r.x + 44
            br = pygame.Rect(bx, y, r.w - 60, h - 6)
            col = C["cyan"] if who == "nova" else g.color
            bg = pygame.Surface(br.size, pygame.SRCALPHA)
            pygame.draw.rect(bg, (*col, 30), bg.get_rect(), border_radius=10)
            pygame.draw.rect(bg, (*col, 120), bg.get_rect(), 1, border_radius=10)
            surf.blit(bg, br)
            for i, ln in enumerate(lines):
                draw_text(surf, ln, (br.x + 12, br.y + 6 + i * 20), 15, C["text"] if who == "nova" else C["text_dim"],
                          raw=True)
        # fırtına zaman çizelgesi
        self.draw_timeline(surf)
        self.draw_widgets(surf)

    def draw_timeline(self, surf):
        g = self.game
        r = pygame.Rect(620, H - 130, W - 520 - 640, 70)
        glass_panel(surf, r, C["gold"], 150, 14)
        draw_text(surf, "UZAY HAVASI · ÖNÜMÜZDEKİ 24 SAAT", (r.x + 14, r.y + 8), 12, C["gold"], bold=True)
        x0, x1 = r.x + 20, r.right - 20
        ly = r.y + 46
        pygame.draw.line(surf, C["text_dim"], (x0, ly), (x1, ly), 1)
        lv = g.lvl("nova")
        now = g.minutes
        span = MIN_PER_DAY
        for h in range(0, 25, 6):
            x = x0 + (x1 - x0) * h / 24
            pygame.draw.line(surf, C["text_mute"], (x, ly - 4), (x, ly + 4))
            draw_text(surf, f"+{h}s", (x, ly + 6), 10, C["text_mute"], anchor="midtop")
        if lv >= 3:
            for s in g.s["storms"]:
                a = (s["start"] - now) / span
                b = (s["start"] + s["dur"] - now) / span
                if b < 0 or a > 1:
                    continue
                xa = x0 + (x1 - x0) * clamp(a, 0, 1)
                xb = x0 + (x1 - x0) * clamp(b, 0, 1)
                pygame.draw.rect(surf, scale_color(C["gold"], 0.4 + 0.5 * s["power"]), (xa, ly - 9, max(3, xb - xa), 18),
                                 border_radius=6)
        elif lv == 2:
            nxt = g.next_storm()
            if nxt:
                a = clamp((nxt["start"] - now) / span, 0, 1)
                xa = x0 + (x1 - x0) * a
                for i in range(8):
                    draw_glow(surf, (xa + (i - 4) * 20, ly), 16, C["gold"], 0.25)
                draw_text(surf, "~ olası fırtına", (xa, ly - 26), 11, C["gold"], anchor="midtop")
        else:
            draw_text(surf, "Tahmin için NOVA Seviye 2+ gerekli", (r.centerx, ly - 8), 13, C["text_mute"], anchor="midtop")

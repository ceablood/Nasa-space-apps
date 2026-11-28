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
from .. import cinema
from ..config import C, H, MIN_PER_DAY, TOPBAR_H, W
from ..fx import ParticleSystem, draw_glow, scale_color, clamp
from ..i18n import tr
from ..nova import draw_nova_face
from ..nova_ai import NovaAI
from ..nova_ai import engine as NE
from ..nova_ai import live as NL
from ..nova_ai.mind import Mind
from .. import i18n
from ..ui import UI, Button, TextInput, draw_icon, draw_paragraph, draw_text, font, glass_panel, fmt_num, wrap_text


class ChatInput(TextInput):
    """Uzun soruda imleç görünür kalsın: yalnız sığan son kısım çizilir."""

    def draw(self, surf):
        full = self.text
        f = font(self.size, True)
        while self.text and f.size(self.text)[0] > self.rect.w - 60:
            self.text = self.text[1:]
        try:
            super().draw(surf)
        finally:
            self.text = full


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
        self.ai = None
        self.history = []          # yazılan sorular (↑ / ↓ ile geri çağrılır)
        self.hist_i = 0
        self.thinking = None       # {"t": kalan sn, "dur": toplam, "resp": yanıt} — NOVA cevap vermeden önce düşünür
        self.last_conf = None
        self.reveal = 0.0          # son NOVA mesajının yazılan karakter sayısı (harf harf)

    def enter(self, **kw):
        g = self.game
        greet = self.app.nova.greet()
        self.chat = [("nova", tr(greet))]
        self.talk_t = 2.5
        self.app.audio.speak(greet)
        mind = getattr(self.app, "nova_mind", None)
        if mind is None:
            mind = self.app.nova_mind = Mind()
        mind.update(0.0, g)                           # ilk gözlem / uzaktayken olanlara tepki
        self.ai = NovaAI(g, self.app.nova, mind)
        self.thinking = None
        for k in ("cad", "exo", "eonet"):            # canlı NASA verisini önceden iste (masaüstü: arka plan)
            NL.LIVE.refresh(k)
        if NE._NET is None and not NL.WEB:            # sinir ağını arka planda eğit (ilk soru takılmasın)
            import threading
            threading.Thread(target=NE.get_net, daemon=True).start()
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
                                 lambda: self.upgrade(), accent=C["gold"], icon="star", size=17, style="gold",
                                 tooltip=D.BUILDING["nova"]["levels"][nxt]))
            ok, why = g.can_upgrade("nova")
            ub.set_enabled(ok, why)
            ub.pulse = ok
        cr = self.chat_rect()
        self.inp = self.add(ChatInput((cr.x, cr.bottom + 12, cr.w - 150, 50), "", "NOVA'ya bir soru yaz… (ör. Mars'ta yerçekimi?)",
                                      max_len=160, on_submit=self.ask_text, accent=C["cyan"], size=17))
        self.add(Button((cr.right - 140, cr.bottom + 12, 140, 50), "SOR", lambda: self.ask_text(self.inp.text), accent=C["gold"],
                        icon="nova", size=17, style="gold"))

    def chat_rect(self):
        return pygame.Rect(620, TOPBAR_H + 110, W - 520 - 640, H - TOPBAR_H - 322)

    def ask_text(self, text):
        text = (text or "").strip()
        if not text:
            self.inp.shake = 0.3
            return
        self.history.append(text)
        del self.history[:-30]
        self.hist_i = len(self.history)
        if self.thinking:
            self.inp.shake = 0.3                     # NOVA hâlâ düşünüyor
            return
        self.inp.text = ""
        self.push("you", text, raw=True)
        r = self.ai.respond(text)
        self.last_conf = (r["conf"], r["intent"])
        self.thinking = {"t": r["think"], "dur": r["think"], "resp": r["text"]}

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_UP, pygame.K_DOWN) and self.history:
            self.hist_i = max(0, min(len(self.history), self.hist_i + (-1 if e.key == pygame.K_UP else 1)))
            self.inp.text = self.history[self.hist_i] if self.hist_i < len(self.history) else ""
            return True
        return super().handle(e)

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
        if self.thinking:
            return
        self.push("you", label)
        self.thinking = {"t": 0.7, "dur": 0.7, "resp": tr(self.app.nova.answer(key))}

    def push(self, who, text, raw=False):
        if not raw:
            text = tr(text)
        self.chat.append((who, text))
        del self.chat[:-12]
        if who == "nova":
            self.reveal = 0.0
            self.talk_t = 1.5 + len(text) * 0.025
            self.app.audio.speak(text)
        else:
            self.reveal = 1e9

    def update(self, dt):
        super().update(dt)
        self.ps.update(dt)
        self.talk_t = max(0.0, self.talk_t - dt)
        self.reveal += dt * 70                        # harf harf yazma (~70 karakter/sn)
        if self.ai:
            self.ai.mind.update(dt, self.game)
        NL.LIVE.poll()
        if self.thinking:
            self.thinking["t"] -= dt
            if self.thinking["t"] <= 0:
                txt = self.thinking["resp"]
                self.thinking = None
                self.push("nova", txt, raw=True)
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
        cinema.full_pass(surf, surf.get_rect(), t, sun=(340, 120), sun_col=(140, 230, 255), rays=0.7,
                         mote_col=(170, 240, 255), n_motes=40, haze_col=(10, 30, 44), haze_k=0.4,
                         warm=(0, 10, 14), cool=(170, 130, 210))
        self.draw_title(surf, sub=f"NOVA Seviye {g.lvl('nova')} · {D.BUILDING['nova']['levels'][max(1, g.lvl('nova'))]}")
        cx, cy = 340, 390
        lv = max(1, g.lvl("nova"))
        mind = self.ai.mind if self.ai else None
        mood = "think" if self.thinking else (mind.face() if mind else "calm")
        mcol = {"happy": C["green"], "think": C["violet"], "worried": C["gold"], "sad": (120, 150, 255)}.get(mood, C["cyan"])
        draw_glow(surf, (cx, cy), 380, scale_color(mcol, 0.4), 0.4 + 0.1 * math.sin(t))
        self.draw_neurons(surf, cx, cy, mcol)
        draw_nova_face(surf, (cx, cy), 190, t, 1.0 if self.talk_t > 0 else 0.0, mood, lv)
        draw_text(surf, "N O V A", (cx, cy + 250), 30, C["cyan"], bold=True, anchor="midtop", glow=C["cyan"])
        self.draw_mind(surf, cx, cy + 292)
        # sohbet
        r = self.chat_rect()
        glass_panel(surf, r, C["cyan"], 160, 18)
        y = r.bottom - 20
        clip = surf.get_clip()
        surf.set_clip(r.inflate(-4, -4))
        entries = list(self.chat)
        if self.thinking:
            dots = "●" * (1 + int(t * 3) % 3)
            entries.append(("think", (tr("NOVA düşünüyor") + " " + dots)))
        last_nova = max((i for i, e in enumerate(self.chat) if e[0] == "nova"), default=-1)
        for idx in range(len(entries) - 1, -1, -1):
            who, text = entries[idx]
            lines = [ln for para in text.split("\n") for ln in (wrap_text(para, 15, r.w - 60, raw=True) or [""])]
            h = len(lines) * 20 + 18 + (8 if who == "think" else 0)
            y -= h
            if y + h < r.y:
                break
            bx = r.x + 16 if who in ("nova", "think") else r.x + 44
            br = pygame.Rect(bx, y, (r.w - 60) if who != "think" else 260, h - 6)
            col = C["cyan"] if who == "nova" else (C["violet"] if who == "think" else g.color)
            bg = pygame.Surface(br.size, pygame.SRCALPHA)
            pygame.draw.rect(bg, (*col, 30), bg.get_rect(), border_radius=10)
            pygame.draw.rect(bg, (*col, 120), bg.get_rect(), 1, border_radius=10)
            surf.blit(bg, br)
            budget = int(self.reveal) if (who == "nova" and idx == last_nova) else 10 ** 9
            for i, ln in enumerate(lines):
                if budget <= 0:
                    break
                draw_text(surf, ln[:budget], (br.x + 12, br.y + 6 + i * 20), 15,
                          C["text"] if who == "nova" else (C["violet"] if who == "think" else C["text_dim"]), raw=True)
                budget -= len(ln) + 1
            if who == "think":                      # düşünme ilerleme çubuğu
                k = 1 - max(0.0, self.thinking["t"]) / max(0.01, self.thinking["dur"])
                pygame.draw.rect(surf, scale_color(C["violet"], 0.35), (br.x + 12, br.bottom - 12, br.w - 24, 4), border_radius=2)
                pygame.draw.rect(surf, C["violet"], (br.x + 12, br.bottom - 12, int((br.w - 24) * k), 4), border_radius=2)
        surf.set_clip(clip)
        # fırtına zaman çizelgesi
        self.draw_timeline(surf)
        self.draw_widgets(surf)

    def draw_neurons(self, surf, cx, cy, col):
        """Sinir ağının gizli katmanı: 48 nöron yüzün çevresinde; parlaklık = son sorudaki gerçek etkinlik |tanh|.
        Düşünürken nöronlar sırayla ateşlenir (canlandırma; ağın gerçek hesabı soru gönderildiğinde bir kez yapılır)."""
        net = NE._NET
        hid = net.last_hidden if net is not None else None
        n = 48
        R = 236
        t = self.t
        pts = []
        for i in range(n):
            a = -math.pi / 2 + i * math.tau / n
            pts.append((cx + math.cos(a) * R, cy + math.sin(a) * R))
        for i in range(0, n, 3):                       # sinaps çizgileri (komşulara)
            j = (i + 7) % n
            pygame.draw.line(surf, scale_color(col, 0.18), pts[i], pts[j], 1)
        for i, (x, y) in enumerate(pts):
            act = abs(float(hid[i])) if hid is not None and len(hid) == n else 0.15
            if self.thinking:
                act = max(act * 0.6, 0.5 + 0.5 * math.sin(t * 9 - i * 0.8))
            r_ = 3 + 4 * act
            pygame.draw.circle(surf, scale_color(col, 0.35 + 0.65 * act), (int(x), int(y)), int(r_))
            if act > 0.55:
                draw_glow(surf, (x, y), 10 + 10 * act, col, 0.35 * act)
        if net is None:
            draw_text(surf, tr("sinir ağı eğitiliyor…"), (cx, cy - R - 26), 12, C["text_mute"], anchor="center", raw=True)

    def draw_mind(self, surf, cx, y):
        """Duygu çubukları + son yanıtın güveni (ağın olasılığı / kural eşleşmesi)."""
        if not self.ai:
            return
        tr_ = i18n.LANG == "tr"
        mind = self.ai.mind
        draw_text(surf, (tr("Ruh hali") + ": " + mind.label(tr_)), (cx, y), 14, C["text_dim"], anchor="midtop", raw=True)
        y += 24
        chips = mind.chips(tr_)
        cols = (C["green"], C["violet"], C["gold"], C["cyan"], (120, 150, 255))
        bw = 72
        x0 = cx - (bw * len(chips) + 8 * (len(chips) - 1)) // 2
        for i, ((name, v), c) in enumerate(zip(chips, cols)):
            x = x0 + i * (bw + 8)
            pygame.draw.rect(surf, (20, 24, 40), (x, y, bw, 8), border_radius=4)
            pygame.draw.rect(surf, c, (x, y, max(2, int(bw * v)), 8), border_radius=4)
            draw_text(surf, name, (x + bw // 2, y + 12), 11, C["text_mute"], anchor="midtop", raw=True)
        if self.last_conf and self.last_conf[1]:
            conf = int(round(self.last_conf[0] * 100))
            draw_text(surf, tr("Son yanıta güven") + ": " + i18n.pct(conf), (cx, y + 34), 12, C["text_mute"], anchor="midtop", raw=True)

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

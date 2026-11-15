# -*- coding: utf-8 -*-
"""
AÇILIŞ VE PROFİL OLUŞTURMA
Dil seçimi (Türkçe / English / Deutsch) -> ana menü -> NOVA: "Uzay Ajansının
adı ne olsun?" -> astronot kıyafeti seçimi -> ajans odağı -> üs.
"""
import math
import random

import pygame

from . import Scene
from .. import paint
from .. import cinema
from .. import art
from .. import data as D
from .. import i18n
from ..config import AGENCY_COLORS, C, H, W
from ..fx import ParticleSystem, clamp, draw_glow, ease_out_back, ease_out_cubic, scale_color
from ..i18n import tr
from ..nova import draw_nova_face
from ..ui import Button, TextInput, UI, chip, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, render_text, text_size

EXAMPLES = ["Selim Uzay", "Anadolu Uzay Ajansı", "Nova Space", "Türk Uzay Gücü"]
QUESTIONS = {"name": "Uzay Ajansının adı ne olsun?", "suit": "Astronotların hangi kıyafeti giysin?",
             "focus": "Ajansın neye odaklansın?", "lang": "Dil  ·  Language  ·  Sprache"}


class IntroScene(Scene):
    music = "menu"
    ambient = "amb_space"
    show_topbar = False
    allow_events = False

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("violet", 21, 1.15)
        self.ps = ParticleSystem()
        self.stage = "menu"
        self.k = 0.0
        self.color_i = 0
        self.name = ""
        self.suit = "balanced"
        self.focus = "science"
        self.input = None
        self.summary = None
        self.cards = []

    def enter(self, **kw):
        self.summary = self.game.save_summary() if self.game.has_save() else None
        self.go_stage("menu" if i18n.PREFS.get("lang_chosen") else "lang")

    def go_stage(self, st):
        self.stage = st
        self.k = 0.0
        self.widgets = []
        self.cards = []
        getattr(self, "build_" + st)()
        if st in QUESTIONS and st != "lang":
            self.app.audio.speak(tr(QUESTIONS[st]))

    def rebuild(self):
        pass

    # ----------------------------------------------------------------- dil
    def build_lang(self):
        for i, (code, label) in enumerate(i18n.LANGS):
            self.add(Button((W // 2 - 500 + (i % 3) * 340, 410 + (i // 3) * 130, 320, 110), label,
                            (lambda c=code: self.pick_lang(c, True)),
                            accent=(C["red"], C["cyan"], C["gold"], C["violet"], C["orange"], C["green"])[i % 6],
                            size=30, style="big"))

    def pick_lang(self, code, first=False):
        i18n.set_lang(code)
        i18n.PREFS["lang_chosen"] = True
        i18n.save_prefs()
        self.app.audio.play("success", 0.5)
        self.go_stage("menu")

    def lang_buttons(self):
        for i, (code, label) in enumerate(i18n.LANGS):
            n = len(i18n.LANGS)
            b = self.add(Button((W - 24 - n * 112 + i * 112, 24, 106, 38), label, (lambda c=code: self.pick_lang(c)),
                                accent=C["cyan"], size=13, style="tab"))
            b.selected = (i18n.LANG == code)

    # ---------------------------------------------------------------- menü
    def build_menu(self):
        cx = W // 2
        y = 520
        self.lang_buttons()
        if self.summary:
            b = self.add(Button((cx - 200, y, 400, 62), "KAMPANYAYA DEVAM", self.continue_game, accent=C["green"],
                                icon="play", size=20, style="big", hotkey=pygame.K_RETURN))
            b.pulse = True
            y += 76
        nb = self.add(Button((cx - 200, y, 400, 56), "YENİ KAMPANYA", lambda: self.go_stage("name"), accent=C["cyan"],
                             icon="rocket", size=19, style="big" if not self.summary else "glass",
                             hotkey=None if self.summary else pygame.K_RETURN))
        nb.pulse = not self.summary
        y += 70
        self.add(Button((cx - 200, y, 195, 48), "TAM EKRAN", self.app.toggle_fullscreen, accent=C["violet"], size=15))
        self.add(Button((cx + 5, y, 195, 48), "ÇIKIŞ", self.quit, accent=C["red"], size=15))

    def quit(self):
        self.app.running = False

    def continue_game(self):
        if self.game.load():
            st = self.game.s["settings"]
            self.app.audio.set_enabled(st.get("sound", True))
            self.app.audio.set_volumes(st.get("music"), st.get("sfx"))
            self.app.on_game_ready()
            self.app.go("base")
            self.app.say(self.app.nova.greet())
        else:
            self.app.toast("Kayıt okunamadı. Yeni kampanya başlat.", "red", "warning")

    # ----------------------------------------------------------------- isim
    def build_name(self):
        self.input = self.add(TextInput((W // 2 - 330, 470, 660, 76), self.name, "Ajans adını yaz...", 28,
                                        on_submit=lambda t: self.name_done(), accent=AGENCY_COLORS[self.color_i]))
        x0 = W // 2 - (len(EXAMPLES) * 170) // 2
        for i, ex in enumerate(EXAMPLES):
            b = self.add(Button((x0 + i * 170, 566, 160, 38), "", (lambda e=ex: self.set_name(e)), accent=C["text_dim"],
                                size=13, style="ghost"))
            b.data = ex
        for i, col in enumerate(AGENCY_COLORS):
            b = self.add(Button((W // 2 - 4 * 52 + i * 52, 628, 44, 44), "", (lambda j=i: self.set_color(j)),
                                accent=col, size=10))
            b.selected = (i == self.color_i)
            b.data = "color"
        self.next_btn = self.add(Button((W // 2 - 190, 706, 380, 64), "DEVAM", self.name_done, accent=C["green"],
                                        icon="play", size=21, style="big"))
        self.back("menu")

    def back(self, st):
        self.add(Button((40, H - 76, 150, 48), "GERİ", lambda: self.go_stage(st), accent=C["text_dim"], icon="arrow_left",
                        size=16, hotkey=pygame.K_ESCAPE))

    def set_name(self, n):
        self.input.text = n
        self.app.audio.play("clunk", 0.5)

    def set_color(self, i):
        self.color_i = i
        self.input.accent = AGENCY_COLORS[i]
        for w in self.widgets:
            if isinstance(w, Button) and w.data == "color":
                w.selected = (w.accent == AGENCY_COLORS[i])

    def name_done(self):
        name = self.input.text.strip()
        if len(name) < 2:
            self.input.shake = 0.4
            self.app.audio.play("deny")
            self.app.toast("Ajans adı en az 2 karakter olmalı", "red", "warning")
            return
        self.name = name
        self.go_stage("suit")

    # -------------------------------------------------------------- kıyafet
    def build_suit(self):
        for i, su in enumerate(D.SUITS):
            r = pygame.Rect(W // 2 - 600 + i * 410, 296, 380, 404)
            b = self.add(Button(r, "", (lambda k=su["key"]: self.set_choice("suit", k)), accent=su["color"], size=12))
            b.selected = (self.suit == su["key"])
            self.cards.append((su, b))
        self.add(Button((W // 2 - 190, 716, 380, 64), "DEVAM", lambda: self.go_stage("focus"), accent=C["green"],
                        icon="play", size=21, style="big", hotkey=pygame.K_RETURN)).pulse = True
        self.back("name")

    def set_choice(self, what, key):
        setattr(self, what, key)
        self.app.audio.play("clunk", 0.7)
        for item, b in self.cards:
            b.selected = (item["key"] == key)

    # ---------------------------------------------------------------- odak
    def build_focus(self):
        for i, fo in enumerate(D.FOCUS):
            r = pygame.Rect(W // 2 - 600 + i * 410, 290, 380, 330)
            b = self.add(Button(r, "", (lambda k=fo["key"]: self.set_choice("focus", k)), accent=fo["color"], size=12))
            b.selected = (self.focus == fo["key"])
            self.cards.append((fo, b))
        self.add(Button((W // 2 - 190, 716, 380, 64), "AJANSI KUR", self.confirm, accent=C["green"], icon="flag",
                        size=21, style="big", hotkey=pygame.K_RETURN)).pulse = True
        self.back("suit")

    def confirm(self):
        self.game.new(self.name, AGENCY_COLORS[self.color_i], self.suit, self.focus)
        self.app.on_game_ready()
        self.app.audio.play("success")
        self.app.go("base")
        self.app.say(self.app.nova.welcome_new(), "happy")

    # --------------------------------------------------------------- döngü
    def update(self, dt):
        super().update(dt)
        self.k = min(1.0, self.k + dt * 0.8)
        if random.random() < 0.25:
            self.ps.glow(random.uniform(0, W), H + 10, 1, random.choice([C["cyan"], C["violet"], C["magenta"]]),
                         speed=(20, 60), size=(1, 3), life=(3, 6), grav=-25)
        self.ps.update(dt)
        if self.stage == "name" and self.input:
            self.next_btn.pulse = len(self.input.text.strip()) >= 2

    def draw(self, surf):
        t = self.t
        # boyalı mat resim arka plan, fareye ve zamana göre hafif paralaks
        bg = paint.get("menu", (W + 48, H + 27))
        mx, my = UI.mouse
        ox = -24 - (mx / W - 0.5) * 30 + math.sin(t * 0.07) * 6
        oy = -13 - (my / H - 0.5) * 16
        surf.blit(bg, (int(ox), int(oy)))
        # sinematik: boyalı güneşten yayılan hacimsel huzmeler + süzülen toz + renk uyumu
        sun = (ox + (W + 48) * 0.16, oy + (H + 27) * 0.70 + 6)
        cinema.god_rays(surf, sun, (255, 196, 130), 0.5, size=1800, t=t)
        cinema.motes(surf, (0, 0, W, H), t, 70, (255, 224, 180))
        cinema.grade(surf, (0, 0, W, H))
        self.ps.draw(surf)
        if self.stage in ("menu", "lang"):
            self.draw_logo(surf, 150 if self.stage == "menu" else 120, t)
        self.draw_widgets(surf)
        getattr(self, "draw_" + self.stage)(surf, t)

    def draw_logo(self, surf, y, t, scale=1.0):
        word = "AETHER-X"
        fs = int(120 * scale)
        tw = sum(render_text(ch, fs, C["text"], True).get_width() for ch in word)
        x = W // 2 - tw // 2
        k = ease_out_cubic(self.k)
        for i, ch in enumerate(word):
            d = clamp(self.k * 2.4 - i * 0.12, 0, 1)
            img = render_text(ch, fs, C["text"], True)
            off = (1 - ease_out_back(d)) * 60
            col = C["cyan"] if ch != "-" else C["magenta"]
            draw_glow(surf, (x + img.get_width() / 2, y + fs * 0.55 + off), fs * 0.5, col, 0.35 * d)
            surf.blit(render_text(ch, fs, scale_color(col, 0.5), True), (x + 3, y + 4 + off))
            surf.blit(img, (x, y + off))
            x += img.get_width()
        sx = W // 2 - tw // 2 + tw * ((t * 0.35) % 1.6 - 0.3)
        draw_glow(surf, (sx, y + fs * 0.55), 90, C["white"], 0.25 * k)
        draw_text(surf, "UZAY AJANSI KOMUTA SİMÜLASYONU", (W // 2, y + fs + 14), 20, scale_color(C["cyan"], 0.9),
                  bold=True, anchor="midtop", alpha=int(255 * k))

    def question(self, surf, t, key, sub, cy=110, size=60, max_w=W - 200):
        k = ease_out_back(min(1.0, self.k * 1.6))
        draw_nova_face(surf, (W // 2, cy), size * k, t, 1.0 if self.app.audio.speaking or (t % 4) < 1.6 else 0.0, "calm", 2)
        draw_text(surf, QUESTIONS[key], (W // 2, cy + size + 22), 36, C["white"], bold=True, anchor="midtop", glow=C["cyan"],
                  max_w=max_w)
        draw_text(surf, sub, (W // 2, cy + size + 72), 17, C["text_dim"], anchor="midtop", max_w=max_w)

    def draw_lang(self, surf, t):
        draw_text(surf, QUESTIONS["lang"], (W // 2, 390), 34, C["white"], bold=True, anchor="midtop", glow=C["cyan"], raw=True)
        draw_text(surf, "Türkçe  ·  English  ·  Deutsch", (W // 2, 610), 16, C["text_dim"], anchor="midtop", raw=True)

    def draw_menu(self, surf, t):
        if self.summary:
            s = self.summary
            r = pygame.Rect(W // 2 - 260, 370, 520, 126)
            glass_panel(surf, r, s["color"], 200, 18)
            pygame.draw.circle(surf, s["color"], (r.x + 52, r.centery), 30, 2)
            draw_glow(surf, (r.x + 52, r.centery), 40, s["color"], 0.5)
            draw_icon(surf, "rocket", (r.x + 52, r.centery), 30, s["color"])
            draw_text(surf, s["name"].upper(), (r.x + 100, r.y + 18), 24, C["text"], bold=True, raw=True, max_w=400)
            draw_text(surf, f"Seviye {s['level']} · Gün {s['day']}", (r.x + 100, r.y + 52), 16, C["text_dim"])
            draw_text(surf, f"{s['money']} Para · {s['rp']} Puan", (r.x + 100, r.y + 76), 16, C["gold"], bold=True)
            cx = r.right - 20
            for p in reversed(s["colonies"]):
                cr = chip(surf, (cx, r.y + 20), D.PLANET[p]["name"], C["green"], 12, anchor="topright", icon="flag")
                cx = cr.x - 6
        draw_text(surf, "F11 tam ekran · ESC geri", (W // 2, H - 34), 13, C["text_mute"], anchor="midtop")

    def draw_name(self, surf, t):
        self.question(surf, t, "name", "Sen bir kişi değil, koca bir ajanssın. Bu isim üssünde, roketinde, bayrağında yazacak.",
                      cy=200, size=86, max_w=W - 760)
        for w in self.widgets:
            if isinstance(w, Button) and isinstance(w.data, str) and w.data != "color":
                draw_text(surf, w.data, w.rect.center, 13, C["text_dim"], bold=True, anchor="center", raw=True,
                          max_w=w.rect.w - 10)
        name = (self.input.text.strip() if self.input else "") or tr("AJANS")
        col = AGENCY_COLORS[self.color_i]
        boost, _ = art.render_booster(1, name, col, 0.9)
        x, y = W - 300, 350
        draw_glow(surf, (x + boost.get_width() // 2, y + 150), 160, col, 0.25)
        surf.blit(boost, (x, y))
        draw_text(surf, "ROKET ÖNİZLEME", (x + boost.get_width() // 2, y - 30), 13, C["text_dim"], bold=True, anchor="midtop")
        sign = pygame.Rect(70, 420, 330, 90)
        glass_panel(surf, sign, col, 210, 14, strong=True)
        draw_text(surf, name.upper()[:22], (sign.centerx, sign.y + 18), 22, C["text"], bold=True, anchor="midtop", glow=col,
                  raw=True, max_w=300)
        draw_text(surf, "FIRLATMA ÜSSÜ", (sign.centerx, sign.y + 54), 15, col, bold=True, anchor="midtop")
        draw_text(surf, "ÜS TABELASI", (sign.centerx, sign.y - 26), 13, C["text_dim"], bold=True, anchor="midtop")
        draw_text(surf, "Renk", (W // 2 - 4 * 52 - 20, 650), 15, C["text_dim"], bold=True, anchor="midright")

    def draw_suit(self, surf, t):
        self.question(surf, t, "suit", "Dayanıklı ama hantal mı, çevik ama kırılgan mı? Kıyafeti sonra Araştırma Merkezi'nde geliştirebilirsin.")
        for su, b in self.cards:
            r = b.rect
            col = su["color"]
            draw_glow(surf, (r.centerx, r.y + 120), 100, col, 0.3 + (0.25 if b.selected else 0))
            for j, ct in enumerate(("engineer", "pilot", "scientist")):
                art.draw_astronaut(surf, r.centerx + (j - 1) * 84, r.y + 112 + (0 if j == 1 else 14), ct,
                                   2.0 if j == 1 else 1.4, t + j, wave=b.selected and j == 1, suit=su["key"])
            draw_text(surf, su["name"], (r.centerx, r.y + 200), 25, C["white"], bold=True, anchor="midtop", max_w=r.w - 30)
            draw_bar(surf, (r.x + 30, r.y + 262, r.w - 60, 12), su["dur"] / 5, C["orange"], label="DAYANIKLILIK",
                     value=f"{su['dur']}/5", segments=5, size=13)
            draw_bar(surf, (r.x + 30, r.y + 308, r.w - 60, 12), su["mob"] / 5, C["green"], label="HAREKET KABİLİYETİ",
                     value=f"{su['mob']}/5", segments=5, size=13)
            draw_paragraph(surf, su["desc"], (r.x + 26, r.y + 332), r.w - 52, 14, C["white"], max_lines=4)
            if b.selected:
                chip(surf, (r.right - 14, r.y + 14), "SEÇİLİ", C["green"], 13, anchor="topright", icon="check")

    def draw_focus(self, surf, t):
        self.question(surf, t, "focus", "Bu seçim ajansına kalıcı bir üstünlük kazandırır.", cy=120)
        for fo, b in self.cards:
            r = b.rect
            col = fo["color"]
            draw_glow(surf, (r.centerx, r.y + 90), 90, col, 0.35 + (0.25 if b.selected else 0))
            pygame.draw.circle(surf, (4, 8, 18), (r.centerx, r.y + 90), 54)
            pygame.draw.circle(surf, col, (r.centerx, r.y + 90), 54, 3)
            draw_icon(surf, fo["icon"], (r.centerx, r.y + 90), 54, col)
            draw_text(surf, fo["name"], (r.centerx, r.y + 170), 25, C["white"], bold=True, anchor="midtop", max_w=r.w - 30)
            draw_paragraph(surf, fo["desc"], (r.x + 30, r.y + 222), r.w - 60, 16, C["white"], max_lines=3)
            if b.selected:
                chip(surf, (r.right - 14, r.y + 14), "SEÇİLİ", C["green"], 13, anchor="topright", icon="check")

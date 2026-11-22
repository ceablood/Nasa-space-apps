# -*- coding: utf-8 -*-
"""
AÇILIŞ VE PROFİL OLUŞTURMA
Dil seçimi (Türkçe / English / Deutsch) -> ana menü -> NOVA: "Uzay Ajansının
adı ne olsun?" -> astronot kıyafeti seçimi -> ajans odağı -> üs.
"""
import math
import random
import sys
import threading

import pygame

from . import Scene
from .. import paint
from .. import space3d as S3
from .. import cinema
from .. import art
from .. import data as D
from .. import i18n
from ..config import AGENCY_COLORS, C, H, W
from ..fx import ParticleSystem, clamp, draw_glow, ease_out_back, ease_out_cubic, scale_color
from ..i18n import tr
from ..nova import draw_nova_face
from ..ui import Button, TextInput, UI, chip, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, render_text, text_size

EXAMPLES = ["Orion Space", "Horizon Space Agency", "Nova Space", "Stellar Frontier"]
QUESTIONS = {"name": "Uzay Ajansının adı ne olsun?", "suit": "Astronotların hangi kıyafeti giysin?",
             "focus": "Ajansın neye odaklansın?", "lang": "Dil"}


# Ana menüdeki canlı gezegenler: NASA haritaları (Ay LRO, Mars Viking, Jüpiter Cassini; Venüs bulut örtüsü)
# NASA NSSDC dönüş sürelerine oranla döner. Ölçek: Jüpiter'in 9,9 saatlik günü ~40 sn -> ×891 hızlandırılmış.
LIVE = [("venus", 1000, 470, 64), ("moon", 760, 492, 40), ("mars", 1210, 478, 52), ("jupiter", 1440, 452, 92)]
TIME_SCALE = 9.9 * 3600 / 40.0
WEB = sys.platform == "emscripten"


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
        self.live = {}                  # anahtar -> son çizilen yüzey
        self.live_i = 0
        self.live_t = 0.0               # gezegen saati (sn, hızlandırılmış)
        self.pick = None                # tıklanan gezegen (NASA kartı)
        self._warming = False

    def enter(self, **kw):
        self.summary = self.game.save_summary() if self.game.has_save() else None
        self.warm_planets()
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

    # ------------------------------------------------------- canlı gezegenler
    def warm_planets(self):
        """Dokular eksikse masaüstünde arka planda hazırla (tarayıcıda yükleme ekranı zaten hazırlar)."""
        missing = [k for k, *_ in LIVE if not S3.has_texture(k, 512)]
        if not missing or self._warming:
            return
        if WEB:
            return
        self._warming = True

        def work():
            for k in missing:
                try:
                    S3.texture(k, 512)
                except Exception:
                    pass
            self._warming = False
        threading.Thread(target=work, daemon=True).start()

    def render_live(self):
        """Her karede bir gezegeni yeniden çizer (sırayla): dönüş, bulut ve toz hareketi canlı kalır, maliyet sabit."""
        if self.stage != "menu":
            return
        q = i18n.quality()
        self._live_frame = getattr(self, "_live_frame", 0) + 1
        if self._live_frame % q.get("live_every", 1):
            return
        key, x, y, R = LIVE[self.live_i % len(LIVE)]
        self.live_i += 1
        if self.pick == key:
            R = int(R * 1.12)
        th = min(q.get("live_tex", 512), 1024)
        if not S3.has_texture(key, th):
            if th > 512 and S3.has_texture(key, 512):
                th = 512 if WEB else th            # masaüstünde ultra dokusu ilk istekte üretilir (NASA haritası: hızlı)
            elif not S3.has_texture(key, 512):
                return
        nd = D.NASA[key]
        spin = (self.live_t / (nd["rot_h"] * 3600.0)) * math.tau
        try:
            M = S3.rot_z(math.radians(-12)) @ S3.rot_x(0.28)
            L = S3.norm3(S3.np.array((-0.8, -0.18, 0.56), dtype=S3.F32))
            self.live[key] = S3.to_surface(S3.render_body(key, R, M, L, spin, self.live_t / 3600.0, th))
        except Exception:
            self.live[key] = None

    def planet_at(self, pos):
        for key, x, y, R in LIVE:
            if math.hypot(pos[0] - x, pos[1] - y) <= R + 8:
                return key
        return None

    def handle(self, e):
        if self.stage == "menu" and e.type == pygame.MOUSEBUTTONDOWN and getattr(e, "button", 1) == 1:
            k = self.planet_at(e.pos)
            if k:
                self.pick = None if self.pick == k else k
                self.app.audio.play("ping", 0.5)
                return True
        return super().handle(e)

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
        x, y = 90, 430
        self.lang_buttons()
        if self.summary:
            y = 520
            b = self.add(Button((x, y, 420, 62), "KAMPANYAYA DEVAM", self.continue_game, accent=C["green"],
                                icon="play", size=20, style="big", hotkey=pygame.K_RETURN))
            b.pulse = True
            y += 76
        nb = self.add(Button((x, y, 420, 58), "YENİ KAMPANYA", lambda: self.go_stage("name"), accent=C["cyan"],
                             icon="rocket", size=19, style="big" if not self.summary else "glass",
                             hotkey=None if self.summary else pygame.K_RETURN))
        nb.pulse = not self.summary
        y += 72
        self.add(Button((x, y, 136, 48), "AYARLAR", lambda: self.app.go("settings", back="intro"), accent=C["violet"], size=14,
                        icon="settings"))
        self.add(Button((x + 142, y, 136, 48), "TAM EKRAN", self.app.toggle_fullscreen, accent=C["violet"], size=14))
        self.add(Button((x + 284, y, 136, 48), "ÇIKIŞ", self.quit, accent=C["red"], size=14))
        y += 84
        self.q_y = y
        for i, q in enumerate(i18n.QUALITY_ORDER):
            b = self.add(Button((x + i * 106, y, 100, 42), i18n.QUALITY_LABEL[q][0], (lambda qq=q: self.set_quality(qq)),
                                accent=C["gold"], size=12, style="tab", tooltip=i18n.QUALITY_LABEL[q][1]))
            b.selected = i18n.PREFS.get("quality") == q

    def set_quality(self, q):
        i18n.PREFS["quality"] = q
        i18n.save_prefs()
        self.live.clear()
        self.app.audio.play("click")
        self.go_stage("menu")

    def quit(self):
        self.app.running = False

    def continue_game(self):
        if self.game.load():
            from .. import settings as SET
            SET.apply_audio(self.app)          # ses ayarları tercih dosyasından (kampanyadan bağımsız)
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
        self.live_t += dt * TIME_SCALE
        self.render_live()
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
            self.draw_logo(surf, 120, t)
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
            col = C["magenta"] if ch in "-X" else C["cyan"]       # "-X" vurgulu
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
        draw_text(surf, QUESTIONS["lang"], (W // 2, 318), 34, C["white"], bold=True, anchor="midtop", glow=C["cyan"], raw=True)

    def draw_menu(self, surf, t):
        if self.summary:
            s = self.summary
            r = pygame.Rect(90, 380, 420, 120)
            glass_panel(surf, r, s["color"], 200, 18)
            pygame.draw.circle(surf, s["color"], (r.x + 50, r.centery), 28, 2)
            draw_glow(surf, (r.x + 50, r.centery), 38, s["color"], 0.5)
            draw_icon(surf, "rocket", (r.x + 50, r.centery), 28, s["color"])
            draw_text(surf, s["name"].upper(), (r.x + 94, r.y + 16), 22, C["text"], bold=True, raw=True, max_w=300)
            draw_text(surf, f"Seviye {s['level']} · Gün {s['day']}", (r.x + 94, r.y + 48), 15, C["text_dim"])
            draw_text(surf, f"{s['money']} Para · {s['rp']} Puan", (r.x + 94, r.y + 72), 15, C["gold"], bold=True)
            cx = r.right - 16
            for p in reversed(s["colonies"]):
                cr = chip(surf, (cx, r.bottom - 30), D.PLANET[p]["name"], C["green"], 11, anchor="topright", icon="flag")
                cx = cr.x - 6
        self.draw_live(surf, t)
        qy = getattr(self, "q_y", 700)
        draw_text(surf, "GRAFİK KALİTESİ", (90, qy - 22), 13, C["text_dim"], bold=True)
        draw_paragraph(surf, i18n.QUALITY_LABEL.get(i18n.PREFS.get("quality"), ("", ""))[1], (90, qy + 50), 420, 12,
                       C["text_dim"], max_lines=4)
        draw_text(surf, "F11 tam ekran · ESC geri", (W // 2, H - 34), 13, C["text_mute"], anchor="midtop")

    def draw_live(self, surf, t):
        draw_text(surf, "CANLI GÜNEŞ SİSTEMİ", (1100, 352), 14, C["cyan"], bold=True, anchor="midtop")
        draw_text(surf, "NASA görüntüleri · NASA dönüş sürelerine oranla ×890 hızlı · bir gezegene tıkla", (1100, 374), 12,
                  C["text_dim"], anchor="midtop")
        for key, x, y, R in LIVE:
            img = self.live.get(key)
            sel = self.pick == key
            glow = {"mars": (255, 140, 90), "venus": (255, 214, 150), "jupiter": (255, 196, 150)}.get(key, (190, 200, 230))
            draw_glow(surf, (x, y), R * (1.7 if sel else 1.45), glow, 0.32 if sel else 0.2)
            if img:
                surf.blit(img, (x - img.get_width() // 2, y - img.get_height() // 2))
            else:
                a = (t * 3 + x) % math.tau
                pygame.draw.circle(surf, (40, 50, 80), (x, y), R, 1)
                pygame.draw.arc(surf, C["cyan"], (x - R, y - R, 2 * R, 2 * R), a, a + 1.3, 2)
            if sel:
                pygame.draw.circle(surf, C["cyan"], (x, y), int(R * 1.12) + 6, 1)
            nd = D.NASA[key]
            draw_text(surf, nd["name"].upper(), (x, y + R + 14), 15, C["text"] if not sel else C["cyan"], bold=True,
                      anchor="midtop")
            draw_text(surf, i18n.num(nd['g'], 2) + " m/s²", (x, y + R + 34), 12, C["text_dim"], anchor="midtop",
                      raw=True)
        if self.pick:
            self.draw_card(surf, self.pick)

    def draw_card(self, surf, key):
        nd = D.NASA[key]
        r = pygame.Rect(690, 600, 830, 190)
        glass_panel(surf, r, C["cyan"], 225, 16)
        draw_text(surf, nd["name"].upper(), (r.x + 24, r.y + 16), 24, C["text"], bold=True)
        draw_text(surf, "Kaynak: " + D.NASA_SOURCE, (r.right - 20, r.y + 22), 12, C["gold"], anchor="topright")

        def n(v, d=0):
            return i18n.num(v, d)
        rot = nd["rot_h"]
        rows = [
            ("Yerçekimi", f"{n(nd['g'], 2)} m/s²"), ("Çap", f"{n(nd['diam_km'])} km"),
            ("Kaçış hızı", f"{n(nd['escape'], 1)} km/s"), ("Ortalama sıcaklık", f"{nd['temp_c']} °C"),
            ("Dönüş süresi", f"{n(abs(rot), 1)} saat" + (" (ters yön)" if rot < 0 else "")),
            ("Gün uzunluğu", f"{n(nd['day_h'], 1)} saat"),
            ("Yüzey basıncı", "katı yüzey yok" if nd["bar"] is None else ("yok denecek kadar az" if nd["bar"] == 0 else f"{n(nd['bar'], 2)} bar")),
            ("Uydu sayısı", str(nd["moons"])),
            ("Yörünge süresi", f"{n(nd['year_d'], 1)} gün"),
            ("Uzaklık", f"Dünya'ya {n(nd['earth_km'])} km" if "earth_km" in nd else f"Güneş'e {n(nd['sun_mkm'], 1)} milyon km"),
        ]
        for i, (k, v) in enumerate(rows):
            cx = r.x + 24 + (i % 2) * 410
            cy = r.y + 56 + (i // 2) * 25
            draw_text(surf, k, (cx, cy), 14, C["text_dim"])
            draw_text(surf, v, (cx + 380, cy), 15, C["text"], bold=True, anchor="topright")

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

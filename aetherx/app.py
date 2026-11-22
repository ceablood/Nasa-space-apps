# -*- coding: utf-8 -*-
"""
KOZMOGENİS // UYGULAMA
Pencere, ana döngü, sahne yöneticisi, üst bar (HUD), olay pencereleri,
bildirimler, NOVA balonu ve sahne geçişleri.
"""
import math
import sys
import traceback

import os
import random
import pygame

from . import cinema
from . import art
from . import data as D
from . import i18n
from .audio import Audio
from .config import C, FPS, H, TITLE, TOPBAR_H, W
from .fx import overlay, Transition, draw_glow, scale_color, Spring, ease_out_back, clamp
from .game import Game
from .nova import NovaBrain, NovaBubble, draw_nova_face
from .ui import (UI, Button, Toasts, draw_bar, draw_cursor, draw_icon, draw_text, draw_tooltip,
                 fmt_num, glass_panel, text_size, wrap_text, chip)


WEB = sys.platform == "emscripten"      # pygbag ile tarayıcıda çalışıyor
SCENES = {
    "intro": ("intro", "IntroScene"),
    "base": ("base", "BaseScene"),
    "hangar": ("hangar", "HangarScene"),
    "launch": ("launch", "LaunchScene"),
    "flight": ("flight", "FlightScene"),
    "landing": ("landing", "LandingScene"),
    "results": ("results", "ResultsScene"),
    "research": ("research", "ResearchScene"),
    "crew": ("crew", "CrewScene"),
    "depot": ("depot", "DepotScene"),
    "quests": ("quests", "QuestsScene"),
    "nova": ("nova_room", "NovaRoomScene"),
    "control": ("control", "ControlScene"),
    "colony": ("colony", "ColonyScene"),
    "agency": ("agency", "AgencyScene"),
    "solar": ("solar", "SolarScene"),
}

NAV = [
    ("base", "ÜS", "home"), ("hangar", "HANGAR", "wrench"), ("research", "AR-GE", "flask"),
    ("crew", "EKİP", "astro"), ("colony", "KOLONİ", "flag"), ("quests", "GÖREV", "chart"),
    ("solar", "ATLAS", "planet"), ("nova", "NOVA", "nova"), ("agency", "AJANS", "settings"),
]

COLOR_KEYS = {"cyan": C["cyan"], "gold": C["gold"], "green": C["green"], "red": C["red"], "orange": C["orange"],
              "pink": C["pink"], "lime": C["lime"], "violet": C["violet"], "magenta": C["magenta"]}


class App:
    def __init__(self, headless=False, max_frames=None):
        pygame.init()
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        flags = 0
        if hasattr(pygame, "SCALED"):
            flags |= pygame.SCALED | pygame.RESIZABLE
        self.flags = flags
        try:
            self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
        except TypeError:
            self.screen = pygame.display.set_mode((W, H), flags)
        except Exception:
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        try:
            pygame.mouse.set_visible(False)
        except Exception:
            pass
        try:
            pygame.key.start_text_input()
        except Exception:
            pass
        self.clock = pygame.time.Clock()
        i18n.load_prefs()
        self.game = Game()
        self.audio = Audio()
        self.audio.preload()
        UI.sound_hook = self._ui_sound
        self.nova = NovaBrain(self.game)
        self.bubble = NovaBubble(self.audio)
        self.toasts = Toasts()
        self.trans = Transition()
        self.scenes = {}
        self.scene = None
        self.scene_name = None
        self.running = True
        self.max_frames = max_frames
        self.frame = 0
        self.fps_show = False
        self.modal = None
        self.modal_buttons = []
        self.modal_k = Spring(0.0, 170, 18)
        self.nav_buttons = []
        self._build_nav()
        self.fullscreen = False
        self.go("intro", instant=True)
        self.start_loading()

    # --------------------------------------------------------------- yükleme
    def start_loading(self):
        """İlk açılışta ağır görselleri (Dünya dokusu, boyalı menü) arka planda hazırla.
        Bu sırada pencere yükleme ekranı gösterir ve tepki vermeye devam eder
        (Windows'ta 'Yanıt vermiyor' uyarısı çıkmaz)."""
        from . import paint
        from . import space3d as S3
        self.load_steps = []
        self.load_planets = {}
        if not paint.is_ready("menu", (W + 48, H + 27)):
            # her adım bir NASA dokusunu hazırlar; yükleme ekranı hazır olan gezegeni hemen gösterir
            self.load_steps = [("earth", lambda: S3.texture("earth", 1024)),
                               ("moon", lambda: S3.texture("moon", 512)),
                               ("mars", lambda: S3.texture("mars", 512)),
                               ("venus", lambda: S3.texture("venus", 512)),
                               ("jupiter", lambda: S3.texture("jupiter", 512)),
                               ("menu", lambda: paint.warm("menu", (W + 48, H + 27)))]
        self.load_done = 0
        self.load_error = None
        self.loading = False
        if not self.load_steps:
            return
        if WEB:                              # tarayıcı (WebAssembly): iş parçacığı yok, adımlar kareler arasında
            self.loading = True
            self.load_t = 0.0
            return
        if os.environ.get("AETHERX_SYNC_LOAD") == "1":
            for _, fn in self.load_steps:
                fn()
            self.load_done = len(self.load_steps)
            return
        import threading

        def work():
            try:
                for _, fn in self.load_steps:
                    fn()
                    self.load_done += 1
            except Exception as ex:          # yükleme başarısız olsa da oyun açılsın
                self.load_error = ex
            self.loading = False
        self.loading = True
        self.load_t = 0.0
        threading.Thread(target=work, daemon=True).start()

    LOAD_LABEL = {"earth": "Dünya · NASA Blue Marble + Black Marble", "moon": "Ay · NASA LRO renkli mozaiği",
                  "mars": "Mars · NASA Viking küresel mozaiği", "venus": "Venüs · bulut katmanı",
                  "jupiter": "Jüpiter · NASA Cassini haritası", "menu": "Ana menü görseli"}

    def _load_planet(self, key, R):
        """Dokusu hazır gezegeni bir kez 3B çizer (NASA dokusu + Güneş ışığı) ve önbelleğe alır."""
        img = self.load_planets.get(key)
        if img is None:
            from . import space3d as S3
            import numpy as np
            th = 1024 if key == "earth" else 512
            if not S3.has_texture(key, th):
                return None
            try:
                M = S3.rot_z(math.radians(-14)) @ S3.rot_x(0.3)
                L = S3.norm3(np.array((-0.7, 0.35, 0.62), dtype=np.float32))
                img = S3.to_surface(S3.render_body(key, R, M, L, {"earth": 1.9, "moon": 0.2, "mars": 2.4}.get(key, 0.6),
                                                   0.0, th))
            except Exception:
                img = False
            self.load_planets[key] = img
        return img or None

    def draw_loading(self):
        surf = self.screen
        surf.fill((3, 5, 14))
        t = self.load_t
        rng = random.Random(4)
        for _ in range(320):
            x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
            b = int(70 + 130 * (0.5 + 0.5 * math.sin(t * rng.uniform(0.5, 2.0) + x)))
            surf.set_at((x, y), (b, b, min(255, b + 30)))
        draw_glow(surf, (W // 2, 150), 360, C["cyan"], 0.16)
        draw_glow(surf, (W - 200, H - 120), 300, (150, 90, 255), 0.12)
        draw_text(surf, "UZAY AJANSI · KOLONİ · MEDENİYET", (W // 2, 70), 15, C["cyan"], bold=True, anchor="midtop", raw=True)
        draw_text(surf, "AETHER-X", (W // 2, 150), 96, C["white"], bold=True, anchor="center", glow=C["cyan"], raw=True)
        draw_text(surf, "Gezegenler NASA görüntüleri ve NASA verileriyle", (W // 2, 210), 18, C["text_dim"], anchor="midtop",
                  raw=True)
        # gezegen sırası: dokusu hazır olan NASA görüntüsüyle belirir, olmayan dönen halka
        keys = ["moon", "mars", "earth", "venus", "jupiter"]
        sizes = {"moon": 52, "mars": 62, "earth": 84, "venus": 76, "jupiter": 104}
        xs = [W * 0.14, W * 0.32, W * 0.5, W * 0.68, W * 0.86]
        cy = 400
        for key, x in zip(keys, xs):
            R = sizes[key]
            img = self._load_planet(key, R)
            nd = D.NASA[key]
            if img:
                draw_glow(surf, (int(x), cy), R * 1.5, {"earth": (110, 170, 255), "mars": (255, 150, 100),
                                                        "venus": (255, 220, 160), "jupiter": (255, 200, 150)}.get(key, (180, 190, 220)), 0.22)
                surf.blit(img, (x - img.get_width() / 2, cy - img.get_height() / 2))
                col = C["text"]
            else:
                a = (t * 3 + x) % math.tau
                pygame.draw.circle(surf, (30, 40, 70), (int(x), cy), R, 1)
                pygame.draw.arc(surf, C["cyan"], (x - R, cy - R, R * 2, R * 2), a, a + 1.4, 2)
                col = C["text_dim"]
            draw_text(surf, nd["name"].upper(), (x, cy + 118), 17, col, bold=True, anchor="midtop", raw=True)
            g = f"{nd['g']:.2f}".replace(".", ",")
            dk = f"{nd['diam_km']:,}".replace(",", ".")
            draw_text(surf, f"{g} m/s² · {dk} km", (x, cy + 142), 13, C["text_dim"],
                      anchor="midtop", raw=True)
            draw_text(surf, f"ort. {nd['temp_c']} °C", (x, cy + 160), 13, C["text_dim"], anchor="midtop", raw=True)
        draw_text(surf, f"Kaynak: {D.NASA_SOURCE}", (W // 2, cy + 190), 12, scale_color(C["text_dim"], 0.8),
                  anchor="midtop", raw=True)
        # ilerleme
        n = max(1, len(self.load_steps))
        frac = min(1.0, (self.load_done + 0.5) / n)
        draw_bar(surf, (W // 2 - 320, 650, 640, 12), frac, C["cyan"])
        cur = self.load_steps[min(self.load_done, n - 1)][0] if self.load_steps else "menu"
        draw_text(surf, self.LOAD_LABEL.get(cur, "Hazırlanıyor") + " hazırlanıyor…", (W // 2, 676), 17, C["text"],
                  bold=True, anchor="midtop", raw=True)
        draw_text(surf, f"{int(frac * 100)}%", (W // 2 + 320, 630), 14, C["cyan"], anchor="bottomright", raw=True)
        # dönen NASA bilgisi
        fact, src = D.NASA_FACTS[int(t / 5) % len(D.NASA_FACTS)]
        r = pygame.Rect(W // 2 - 420, 730, 840, 86)
        glass_panel(surf, r, C["gold"], 150, 14, glow=False)
        draw_text(surf, fact, (r.centerx, r.y + 16), 17, C["text"], anchor="midtop", raw=True, max_w=r.w - 40)
        draw_text(surf, "Kaynak: " + src, (r.centerx, r.y + 52), 13, C["gold"], anchor="midtop", raw=True)
        pygame.display.flip()

    # ----------------------------------------------------------------- yardımcı
    def _ui_sound(self, name):
        vol = {"hover": 0.35, "tick": 0.4, "type": 0.5}.get(name, 0.8)
        self.audio.play(name, vol)

    def toast(self, text, color="cyan", icon="check"):
        self.toasts.push(text, COLOR_KEYS.get(color, color if isinstance(color, tuple) else C["cyan"]), icon)

    def say(self, text, mood="calm", highlight=None, priority=False):
        self.bubble.level = max(1, self.game.nova_level) if self.game.s else 1
        self.bubble.say(text, mood, highlight, priority)

    def on_game_ready(self):
        """Yeni oyun / kayıt yüklendikten sonra: kıyafet stili, korunan isimler."""
        g = self.game
        art.SUIT_STYLE = g.s["suit"]["type"]
        i18n.protected.clear()
        i18n.protected.update({g.name, g.name.upper()})
        i18n._cache.clear()

    def get_scene(self, name):
        sc = self.scenes.get(name)
        if sc is None:
            mod_name, cls_name = SCENES[name]
            mod = __import__(f"aetherx.scenes.{mod_name}", fromlist=[cls_name])
            sc = getattr(mod, cls_name)(self)
            self.scenes[name] = sc
        return sc

    def go(self, name, instant=False, **kw):
        def switch():
            if self.scene:
                try:
                    self.scene.exit()
                except Exception:
                    traceback.print_exc()
            self.scene = self.get_scene(name)
            self.scene_name = name
            self.scene.enter(**kw)
            if self.scene.music:
                self.audio.music(self.scene.music)
            self.audio.ambient(self.scene.ambient)
            for b in self.nav_buttons:
                b.selected = (b.data == name)
        if instant:
            switch()
        else:
            if self.trans.active:
                return
            self.audio.play("whoosh", 0.5)
            self.trans.start(switch, 0.32)

    # ------------------------------------------------------------------ üst bar
    def _build_nav(self):
        self.nav_buttons = []
        x = W - 24
        for key, label, icon in reversed(NAV):
            w = 80
            x -= w + 3
            b = Button((x, 10, w, 44), label, (lambda k=key: self.go(k)), icon=icon, size=12, style="tab",
                       tooltip=None, data=key)
            self.nav_buttons.append(b)
        self.nav_buttons.reverse()

    def draw_topbar(self, surf):
        g = self.game
        bar = pygame.Surface((W, TOPBAR_H), pygame.SRCALPHA)
        for y in range(TOPBAR_H):
            k = y / TOPBAR_H
            pygame.draw.line(bar, (6, 12, 28, int(235 - 60 * k)), (0, y), (W, y))
        surf.blit(bar, (0, 0))
        acc = g.color
        pygame.draw.line(surf, scale_color(acc, 0.6), (0, TOPBAR_H), (W, TOPBAR_H), 1)
        draw_glow(surf, ((self.frame * 3) % W, TOPBAR_H), 20, acc, 0.5)
        # amblem
        cx, cy = 38, TOPBAR_H // 2
        draw_glow(surf, (cx, cy), 30, acc, 0.7)
        pygame.draw.circle(surf, (8, 14, 30), (cx, cy), 21)
        pygame.draw.circle(surf, acc, (cx, cy), 21, 2)
        draw_icon(surf, "rocket", (cx, cy), 24, acc)
        draw_text(surf, g.name.upper(), (68, 9), 19, C["text"], bold=True)
        xp, need, frac = g.xp_progress()
        draw_text(surf, f"SV {g.s['agency']['level']} · {g.badge()}", (68, 33), 12, scale_color(acc, 1.0), bold=True)
        draw_bar(surf, (68, 51, 190, 5), frac, acc, glow=False)
        # kaynaklar
        x = 280
        items = [
            ("money", fmt_num(g.money), C["gold"], "Para"),
            ("rp", fmt_num(g.rp), C["cyan"], "Araştırma Puanı"),
            ("fuel", f"{int(g.s['fuel'])}/{g.fuel_cap()}", C["orange"], "Yakıt Deposu (kg)"),
            ("clock", g.time_label(), C["text"], "Oyun saati"),
        ]
        for icon, val, col, tip in items:
            w = text_size(val, 16, True)[0] + 42
            r = pygame.Rect(x, 12, w, 40)
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (*col, 22), s.get_rect(), border_radius=12)
            pygame.draw.rect(s, (*col, 90), s.get_rect(), 1, border_radius=12)
            surf.blit(s, r)
            draw_icon(surf, icon, (r.x + 18, r.centery), 18, col)
            draw_text(surf, val, (r.x + 32, r.centery), 16, C["text"], bold=True, anchor="midleft")
            if r.collidepoint(UI.mouse):
                UI.set_tooltip(tip, col)
            x += w + 6
        storm = g.storm_active()
        if storm and self.scene_name not in ("solar", "base"):
            k = 0.5 + 0.5 * math.sin(UI.time * 6)
            chip(surf, (W - 24, TOPBAR_H + 8), "GÜNEŞ FIRTINASI", scale_color(C["gold"], 0.7 + 0.3 * k), 13,
                 anchor="topright", icon="storm")
        elif g.s["research"]["active"] and self.scene_name not in ("solar", "research"):
            key, frac, left = g.research_progress()
            r = pygame.Rect(W - 224, TOPBAR_H + 8, 200, 32)
            draw_text(surf, D.RESEARCH_BY_KEY[key]["name"], (r.x, r.y), 12, C["text"], bold=True, max_w=200)
            draw_bar(surf, (r.x, r.y + 20, 200, 6), frac, C["cyan"], glow=False)
        for b in self.nav_buttons:
            if b.data == "quests":
                b.badge = g.unclaimed_quests() or None
            b.draw(surf)

    # --------------------------------------------------------------- modal
    def open_event(self, ev):
        self.modal = {"kind": "event", "ev": ev}
        self.modal_k.snap(0.0)
        self.modal_k.target = 1.0
        self.modal_buttons = []
        n = len(ev["choices"])
        bw = 560
        for i, ch in enumerate(ev["choices"]):
            b = Button((W // 2 - bw // 2, H // 2 + 30 + i * 62, bw, 50), ch["label"],
                       (lambda j=i: self._resolve_event(j)), accent=C["gold"] if i == 0 else C["cyan"], size=16)
            self.modal_buttons.append(b)
        self.audio.play("alarm", 0.4)
        self.say(f"{self.game.name}, karar vermen gereken bir durum var: {ev['title']}.", "think")

    def _resolve_event(self, i):
        notes = self.game.resolve_event(i) or []
        self.modal = None
        self.modal_buttons = []
        if notes:
            self.toast(" · ".join(notes), "gold", "star")
        if self.scene:
            self.scene.rebuild()

    def open_victory(self):
        self.modal = {"kind": "victory"}
        self.modal_k.snap(0.0)
        self.modal_k.target = 1.0
        self.modal_buttons = [Button((W // 2 - 180, H // 2 + 170, 360, 56), "KAMPANYAYA DEVAM", self._close_victory,
                                     accent=C["gold"], size=18, style="big")]
        self.audio.play("success")
        self.audio.music("menu")
        self.say(f"Tebrikler {self.game.name}! Jüpiter'de dev koloniyi kurdun. İnsanlık artık gezegenler arası bir tür.",
                 "happy", priority=True)

    def _close_victory(self):
        self.game.s["flags"]["victory_seen"] = True
        self.game.save()
        self.modal = None
        self.modal_buttons = []
        if self.scene and self.scene.music:
            self.audio.current = None
            self.audio.music(self.scene.music)

    def draw_modal(self, surf):
        if not self.modal:
            return
        k = clamp(self.modal_k.value, 0, 1.2)
        overlay(surf, (2, 4, 12, int(180 * min(1, k))))
        if self.modal["kind"] == "event":
            ev = self.modal["ev"]
            n = len(ev["choices"])
            r = pygame.Rect(0, 0, 680, 220 + n * 62)
            r.center = (W // 2, H // 2 + 20 + int((1 - k) * 60))
            glass_panel(surf, r, C["gold"], 230, 20, strong=True)
            draw_icon(surf, "warning", (r.x + 44, r.y + 44), 30, C["gold"])
            draw_text(surf, "AJANS KARARI", (r.x + 80, r.y + 22), 14, C["gold"], bold=True)
            draw_text(surf, ev["title"], (r.x + 80, r.y + 40), 28, C["text"], bold=True)
            lines = wrap_text(ev["text"], 18, r.w - 80)
            for i, ln in enumerate(lines[:4]):
                draw_text(surf, ln, (r.x + 40, r.y + 92 + i * 24), 18, C["text_dim"], raw=True)
            for i, b in enumerate(self.modal_buttons):
                b.rect.y = r.y + 150 + i * 62
        elif self.modal["kind"] == "victory":
            r = pygame.Rect(0, 0, 820, 460)
            r.center = (W // 2, H // 2 + int((1 - k) * 80))
            glass_panel(surf, r, C["gold"], 235, 24, strong=True)
            t = UI.time
            for i in range(14):
                a = t * 0.5 + i * math.tau / 14
                draw_glow(surf, (r.centerx + math.cos(a) * 330, r.y + 110 + math.sin(a) * 60), 26, C["gold"], 0.5)
            draw_icon(surf, "trophy", (r.centerx, r.y + 90), 70, C["gold"])
            draw_text(surf, "KAMPANYA ZAFERİ", (r.centerx, r.y + 150), 44, C["gold"], bold=True, anchor="midtop",
                      glow=C["gold"])
            draw_text(surf, f"{self.game.name}, Jüpiter'de dev koloniyi kurdu!", (r.centerx, r.y + 214), 22, C["text"],
                      bold=True, anchor="midtop")
            st = self.game.s["stats"]
            draw_text(surf, f"{st['launches']} fırlatma · {st['asteroids']} asteroit · {st['photos']} fotoğraf · "
                            f"{self.game.colony_count()} koloni · Gün {self.game.day}",
                      (r.centerx, r.y + 256), 17, C["text_dim"], anchor="midtop")
            draw_text(surf, "Güneş Sistemi artık senin. Kolonileri büyütmeye devam edebilirsin.",
                      (r.centerx, r.y + 290), 17, C["text_dim"], anchor="midtop")
            for b in self.modal_buttons:
                b.rect.centery = r.y + 380
        for b in self.modal_buttons:
            b.draw(surf)

    # ---------------------------------------------------------------- döngü
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            pass

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11:
                self.toggle_fullscreen()
                return
            if e.key == pygame.K_F3:
                self.fps_show = not self.fps_show
                return
        if self.trans.active:
            return
        if self.modal:
            UI.modal_lock = True
            for b in self.modal_buttons:
                if b.handle(e):
                    break
            return
        UI.modal_lock = False
        if self.bubble.handle(e):
            return
        if self.scene and self.scene.show_topbar and self.game.s:
            for b in self.nav_buttons:
                if b.handle(e):
                    return
        if self.scene:
            self.scene.handle(e)

    def update(self, dt):
        UI.time += dt
        UI.mouse = pygame.mouse.get_pos()
        UI.tooltip = None
        g = self.game
        if g.s and self.scene_name not in ("intro",):
            g.update(dt)
            for text, color, icon, sound in g.notes:
                self.toast(text, color, icon)
                if sound:
                    self.audio.play(sound, 0.7)
            g.notes.clear()
            if not self.modal and self.scene and self.scene.allow_events and not self.trans.active:
                if g.s["flags"]["victory"] and not g.s["flags"]["victory_seen"]:
                    self.open_victory()
                else:
                    ev = g.pending_event()
                    if ev:
                        self.open_event(ev)
        self.audio.update(dt)
        if self.scene:
            self.scene.update(dt)
        if self.scene and self.scene.show_topbar and g.s:
            for b in self.nav_buttons:
                b.update(dt)
        for b in self.modal_buttons:
            b.update(dt)
        self.modal_k.update(dt)
        self.bubble.x = getattr(self.scene, "bubble_x", 24) if self.scene else 24
        self.bubble.update(dt)
        self.toasts.update(dt)
        self.trans.update(dt)

    def draw(self):
        if getattr(self, "loading", False):
            self.load_t = getattr(self, "load_t", 0.0) + 1 / 60
            self.draw_loading()
            return
        surf = self.screen
        if self.scene:
            self.scene.draw(surf)
            cinema.bloom(surf, (0.9 if i18n.PREFS.get("quality") in ("ultra", "max") else 0.6) * self.scene.bloom_k)
            if self.scene.show_topbar and self.game.s:
                self.draw_topbar(surf)
        self.bubble.draw(surf)
        self.draw_modal(surf)
        self.toasts.draw(surf)
        draw_tooltip(surf)
        self.trans.draw(surf)
        if self.fps_show:
            draw_text(surf, f"{self.clock.get_fps():.0f} FPS", (W - 10, H - 24), 14, C["lime"], anchor="topright")
        acc = self.game.color if self.game.s else C["cyan"]
        draw_cursor(surf, acc)
        pygame.display.flip()

    async def run_async(self):
        """Tarayıcı sürümü (pygbag): her karede kontrolü tarayıcıya geri ver."""
        import asyncio
        while self.running and getattr(self, "loading", False):
            dt = self.clock.tick(30) / 1000.0
            self.load_t += dt
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
            self.draw_loading()
            await asyncio.sleep(0)
            if self.load_done < len(self.load_steps):
                try:
                    self.load_steps[self.load_done][1]()
                except Exception as ex:
                    self.load_error = ex
                self.load_done += 1
            else:
                self.loading = False
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 1 / 20)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
            self.frame += 1
            if self.game.s and self.frame % 1800 == 0:
                try:
                    self.game.save()
                except Exception:
                    pass
            await asyncio.sleep(0)

    def run(self):
        while self.running and getattr(self, "loading", False):
            dt = self.clock.tick(30) / 1000.0
            self.load_t += dt
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
            self.draw_loading()
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 1 / 20)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
            self.frame += 1
            if self.max_frames and self.frame >= self.max_frames:
                break
        if self.game.s:
            self.game.save()
        pygame.quit()

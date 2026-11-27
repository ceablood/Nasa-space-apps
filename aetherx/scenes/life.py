# -*- coding: utf-8 -*-
"""
YAŞAYAN GEZEGENLER — KOZMOGENİS LIFE ENGINE + COSMIC AUDIO OBSERVATORY

Sekmeler:
  GEZEGEN          NASA çevre verileri, yaşanabilirlik (ayrı: yaşam bulundu mu), yaşamın kökeni hipotezleri
  YAŞAM            biyomlar, türler (GERÇEK / KURGUSAL etiketli), besin ağı, madde döngüleri, keşif ve dinleme
  ZAMAN ÇİZELGESİ  gezegenin biyolojik tarihi (Dünya: yayımlanmış tarihler) + simülasyon olayları, popülasyon grafiği
  OLAYLAR          volkan, meteor, kuraklık, buzul, sıcaklık, atmosfer, deniz seviyesi, radyasyon, yıldız, fırtına
  SES GÖZLEMEVİ    kategori sesleri, erişilebilirlik, ortam katmanları, konumsal ses testi, olay→ses günlüğü,
                   performans ve ses varlıkları/lisans bilgisi
"""
import math

import pygame

from . import Scene
from .. import data as D
from ..config import C, H, TOPBAR_H, W
from ..fx import clamp, draw_glow, scale_color
from ..life import LifeWorld
from ..life import environment as E
from ..life.biology import fitness
from ..life.habitability import CATEGORIES as HCAT
from ..cae import CATEGORIES
from ..i18n import tr
from .. import i18n as _i18n


def pct_s(v, d=0):
    """Dile göre yüzde ve ondalık: tr '%95,1', en '95.1%'."""
    t = f"{v:.{d}f}"
    return f"%{t.replace('.', ',')}" if _i18n.LANG == "tr" else f"{t}%"
from ..cae import sounds as SD
from ..ui import Button, Slider, Tabs, Toggle, chip, draw_bar, draw_icon, draw_paragraph, draw_text, glass_panel, wrap_text
from .. import life_art as LA
from .. import space3d as S3
from ..i18n import pct as _pct

# gezegen küresi: Güneş Sistemi cisimleri NASA dokusuyla; kurgusal gezegenler en yakın türdeş cismin dokusuyla (temsilî)
GLOBE_TEX = {"earth": "earth", "moon": "moon", "mars": "mars", "venus": "venus", "jupiter": "jupiter", "dunya_benzeri": "earth",
             "okyanus": "neptune", "buz": "europa", "volkanik": "io", "kurak": "mars", "radyasyon": "mercury"}
KCOL = {"bitki": (90, 210, 110), "mantar": (240, 160, 70), "mikrop": (170, 120, 255), "hayvan": (240, 90, 90)}
NROWS = 9

PLANETS = [("earth", "Dünya"), ("moon", "Ay"), ("mars", "Mars"), ("venus", "Venüs"), ("jupiter", "Jüpiter"),
           ("dunya_benzeri", "Dünya benzeri*"), ("okyanus", "Okyanus*"), ("buz", "Buz*"), ("volkanik", "Volkanik*"),
           ("kurak", "Kurak*"), ("radyasyon", "Radyasyonlu*")]
SPEEDS = [(0, "DURAKLAT"), (1, "×1 yıl/sn"), (100, "×100"), (1e4, "×10 bin"), (1e6, "×1 milyon")]
EVENTS = [("volkan", "Volkan"), ("meteor", "Meteor"), ("kuraklik", "Kuraklık"), ("buzul", "Buzul dönemi"),
          ("sicak", "Aşırı sıcak"), ("atmosfer", "Atmosfer değişimi"), ("deniz", "Deniz seviyesi"),
          ("radyasyon", "Radyasyon"), ("yildiz", "Yıldız patlaması"), ("firtina", "Fırtına")]
TABS = ["GEZEGEN", "YAŞAM", "ZAMAN ÇİZELGESİ", "OLAYLAR", "SES GÖZLEMEVİ", "GÖRÜLEN HAYVANLAR"]
KX, KY, KW, KH = 320, 236, W - 360, H - 236 - 30


def fmt_year(y, real):
    if real and y < 0:
        a = -y
        return f"{a / 1e9:.2f} milyar yıl önce".replace(".", ",") if a >= 1e9 else (
            f"{a / 1e6:.0f} milyon yıl önce" if a >= 1e6 else f"{a:,.0f} yıl önce".replace(",", "."))
    if y >= 1e6:
        return f"sim. {y / 1e6:.2f} milyon yıl".replace(".", ",")
    return f"sim. yıl {y:,.0f}".replace(",", ".")


class LifeScene(Scene):
    title = "YAŞAYAN GEZEGENLER"
    title_icon = "planet"
    music = None
    ambient = None
    accent = C["green"]

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("deep", 41, 1.0)
        self.worlds = {}
        self.key = "earth"
        self.scenario = False
        self.tab = 0
        self.speed = 1
        self.biome_i = 0
        self.scroll = 0
        self.sel = None
        self.strength = 0.6
        self.hist = []
        self.hist_t = 0.0
        self.listener_x = 0.5
        self.dio = LA.Diorama()
        self.dio_ev = LA.Diorama()
        self.globe = None
        self.globe_key = None
        self.globe_n = 0
        self.last_event = None

    # ------------------------------------------------------------------ dünya
    @property
    def world(self):
        k = (self.key, self.scenario)
        w = self.worlds.get(k)
        if w is None:
            w = LifeWorld(self.key, self.app.bus, scenario=self.scenario and self.key in E.SOLAR and self.key != "earth")
            self.worlds[k] = w
        return w

    @property
    def biome(self):
        b = self.world.env.biomes
        return b[self.biome_i % len(b)] if b else None

    def enter(self, **kw):
        self.app.cae.music.request("bilimsel araştırma", self.app.cae.now(), urgent=True)
        self.select_planet(self.key)

    def exit(self):
        self.app.cae.stop_ambience()

    def select_planet(self, key):
        self.key = key
        self.biome_i = 0
        self.scroll = 0
        self.sel = None
        self.hist = []
        self.listen()
        self.rebuild()

    def listen(self, profile=None):
        self.app.cae.set_scene(self.world, self.biome, profile)

    # ------------------------------------------------------------------ arayüz
    def rebuild(self):
        self.widgets = []
        y = 176
        for k, name in PLANETS:
            b = self.add(Button((40, y, 260, 36), name, (lambda k=k: self.select_planet(k)), accent=C["cyan"] if k in E.SOLAR else C["violet"],
                                size=14, style="tab"))
            b.selected = k == self.key
            y += 40
        self.add(Toggle((40, y + 4, 260, 34), self.scenario, self.set_scenario, "Kurgusal yaşam"))
        y += 52
        for i, (sp, lab) in enumerate(SPEEDS):
            b = self.add(Button((40 + (i % 2) * 132, y + (i // 2) * 42, 128, 36), lab, (lambda s=sp: self.set_speed(s)),
                                accent=C["gold"], size=12, style="tab"))
            b.selected = sp == self.speed
        self.tabs = self.add(Tabs((KX, 176, KW, 44), TABS, self.set_tab, C["green"], self.tab))
        t = self.tab
        if t == 1:
            bx = KX
            for i, bm in enumerate(self.world.env.biomes):
                w_ = 30 + len(bm) * 9
                b = self.add(Button((bx, KY, w_, 32), bm, (lambda i=i: self.set_biome(i)), accent=C["green"], size=12, style="tab"))
                b.selected = i == self.biome_i
                bx += w_ + 6
            self.add(Button((KX + KW - 380, KY, 180, 32), "BİYOMU ARAŞTIR", self.discover, accent=C["gold"], size=12, icon="eye"))
            self.add(Button((KX + KW - 192, KY, 192, 32), "BİYOMU DİNLE", lambda: self.listen(), accent=C["cyan"], size=12, icon="nova"))
        elif t == 3:
            for i, (k, lab) in enumerate(EVENTS):
                self.add(Button((KX + 20 + (i % 5) * 240, KY + 60 + (i // 5) * 60, 226, 48), lab,
                                (lambda k=k: self.trigger(k)), accent=C["red"] if k in ("meteor", "volkan") else C["orange"], size=15))
            self.add(Slider((KX + 20, KY + 210, 400, 20), self.strength, lambda v: setattr(self, "strength", v), C["orange"],
                            "Olay şiddeti"))
        elif t == 4:
            st = self.app.cae.settings
            for i, cat in enumerate(CATEGORIES):
                self.add(Slider((KX + 20 + (i % 2) * 230, KY + 76 + (i // 2) * 56, 200, 18), st["vol"][cat],
                                (lambda v, c=cat: self.set_vol(c, v)), C["cyan"], cat.upper()))
            for i, (k, lab) in enumerate((("mono", "Mono ses"), ("headphones", "Kulaklık profili"), ("captions", "Altyazı / sesli olay bildirimi"),
                                          ("reduce_high", "Yüksek frekansları azalt"), ("limit_loud", "Ani yüksek sesleri sınırla"))):
                self.add(Toggle((KX + 20, KY + 372 + i * 40, 450, 34), st[k], (lambda v, k=k: self.set_opt(k, v)), lab))
            for i, pr in enumerate(("açık", "mağara", "su altı", "kabin")):
                b = self.add(Button((KX + 520 + i * 102, KY + 262, 96, 32), pr, (lambda p=pr: self.listen(p)), accent=C["violet"],
                                    size=12, style="tab"))
                b.selected = self.app.cae.spatial.profile == pr
            self.add(Slider((KX + 520, KY + 362, 400, 18), self.listener_x, lambda v: setattr(self, "listener_x", v), C["violet"],
                            "Dinleyici konumu (canlı sağda, 60 m)", fmt=lambda v: f"{(v - 0.5) * 240:+.0f} m"))
            self.add(Button((KX + 520, KY + 396, 260, 36), "KONUMSAL SES TESTİ", self.spatial_test, accent=C["violet"], size=13))
            self.add(Button((KX + 790, KY + 396, 230, 36), "MİKROBİYAL TEMSİL", self.microbe_demo, accent=C["lime"], size=13,
                            tooltip="Görsel-işitsel temsil; mikropların sesi değildir"))
        self.back_button()

    def set_tab(self, i):
        self.tab = i
        self.rebuild()

    def set_speed(self, s):
        self.speed = s
        self.rebuild()

    def set_scenario(self, v):
        self.scenario = v
        self.select_planet(self.key)

    def set_biome(self, i):
        self.biome_i = i
        self.scroll = 0
        self.sel = None
        self.listen()
        self.rebuild()

    def set_vol(self, c, v):
        self.app.cae.settings.set(c, v)
        self.save_prefs()

    def set_opt(self, k, v):
        self.app.cae.settings.set(k, v)
        self.save_prefs()
        if k in ("reduce_high", "limit_loud"):
            self.app.cae.assets.cache.clear()
            self.app.cae.assets.bytes = 0
            self.listen()

    def save_prefs(self):
        try:
            from .. import i18n
            i18n.save_prefs()
        except Exception:
            pass

    def discover(self):
        found = self.world.discover(self.biome)
        if not found and not self.world.species:
            self.app.toast("Bu biyomda yaşam bulunmadı", "orange", "eye")

    def trigger(self, k):
        self.world.trigger(k, self.strength, self.biome, pos=(80.0, 0.0))
        self.last_event = (k, self.t)
        self.listen()

    def spatial_test(self):
        w = self.world
        animals = [s for s in w.species if s.alive and s.kingdom == "hayvan" and s.biome == self.biome] or \
                  [s for s in w.species if s.alive and s.kingdom == "hayvan"]
        cae = self.app.cae
        cae.spatial.listener = ((self.listener_x - 0.5) * 240.0, 0.0)
        if not animals:
            self.app.toast("Bu gezegende ses çıkaran canlı yok", "orange", "nova")
            return
        res = cae.call_of(animals[0], "çağrı", (60.0, 0.0))
        self.last_spatial = (animals[0].name, res)

    def microbe_demo(self):
        self.app.cae.play_effect("mikrobiyal temsil", "canlı")

    # ------------------------------------------------------------------ döngü
    def handle(self, e):
        if e.type == pygame.MOUSEWHEEL and self.tab in (1, 2):
            self.scroll = max(0, self.scroll - e.y)
            return True
        if e.type == pygame.MOUSEWHEEL and self.tab == 5:
            self.best_scroll = max(0, getattr(self, "best_scroll", 0) - e.y)
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.tab == 5:
            for rect, sp in getattr(self, "best_cards", []):
                if rect.collidepoint(e.pos):
                    self.best_sel = sp
                    self.app.audio.play("tick")
                    if sp.alive:
                        self.app.cae.spatial.listener = (0.0, 0.0)
                        self.app.cae.call_of(sp, "çağrı", (8.0, 0.0))
                    return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.tab == 1:
            row = self.row_at(e.pos)
            if row is not None:
                self.sel = row
                w = self.world
                if row.kingdom == "hayvan":
                    self.app.cae.spatial.listener = (0.0, 0.0)
                    self.app.cae.call_of(row, "çağrı", (8.0, 0.0))
                return True
        return super().handle(e)

    def update(self, dt):
        super().update(dt)
        if self.speed:
            self.world.step(dt * self.speed)
        self.hist_t += dt
        if self.hist_t > 0.4:
            self.hist_t = 0.0
            st = self.world.stats()
            kc = {k: 0 for k in KCOL}
            for sp in self.world.species:
                if sp.alive and sp.kingdom in kc:
                    kc[sp.kingdom] += 1
            self.hist.append((st["yıl"], st["tür"], st["biyokütle"], kc))
            self.hist = self.hist[-240:]

    # ------------------------------------------------------------------ çizim
    def draw(self, surf):
        super().draw(surf)
        w = self.world
        self.draw_title(surf, sub=f"{w.env.name} · {w.env.source}")
        draw_text(surf, fmt_year(w.year, False), (40, 160), 13, C["gold"], bold=True, anchor="bottomleft")
        draw_text(surf, "* kurgusal ötegezegen", (40, H - 92), 12, C["text_dim"])
        LA.new_frame()
        getattr(self, ("draw_planet", "draw_life", "draw_timeline", "draw_events", "draw_audio", "draw_bestiary")[self.tab])(surf, w)
        self.draw_widgets(surf)
        if self.tab == 3:
            self.draw_event_icons(surf)

    # --- GEZEGEN
    def globe_surface(self, w, R):
        """Dönen küre (NASA dokusu). Maliyet sabit kalsın diye 3 karede bir yeniden çizilir."""
        tex = GLOBE_TEX.get(w.key, "mars")
        self.globe_n += 1
        if self.globe is not None and self.globe_key == (w.key, R) and self.globe_n % 3:
            return self.globe
        th = 512 if S3.has_texture(tex, 512) else 256
        if not S3.has_texture(tex, th):
            try:
                S3.texture(tex, 256)
            except Exception:
                return None
        rot_h = abs(w.env.rotation_h) or 24.0
        spin = (self.t * 3600.0 * 0.6 / rot_h) % math.tau          # gerçek dönüş süresiyle orantılı, hızlandırılmış
        try:
            M = S3.rot_z(math.radians(-14)) @ S3.rot_x(0.3)
            L = S3.norm3(S3.np.array((-0.75, -0.2, 0.6), dtype=S3.F32))
            self.globe = S3.to_surface(S3.render_body(tex, R, M, L, spin, self.t / 60.0, th))
            self.globe_key = (w.key, R)
        except Exception:
            self.globe = None
        return self.globe

    def draw_globe(self, surf, w, center, R):
        env = w.env
        cx, cy = center
        top, bot = LA.sky_colors(env, w.key)
        p = env.pressure_bar or 0.0
        halo = S3.atmo_halo(GLOBE_TEX.get(w.key, "mars"), R, (-0.75, -0.2, 0.6)) if p > 0.005 else None
        if halo:                                                       # gerçekçi atmosfer halesi (Güneş tarafında)
            surf.blit(halo, (cx - halo.get_width() // 2, cy - halo.get_height() // 2))
        img = self.globe_surface(w, R)
        if img:
            surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
        else:
            pygame.draw.circle(surf, (40, 50, 80), (cx, cy), R, 1)
        bio = sum(sp.biomass for sp in w.species if sp.alive)
        if bio > 0:                                                    # biyosfer halkası: biyokütleyle
            a = min(1.0, math.log10(1 + bio) / 3.0)
            ring = pygame.Surface((R * 2 + 40, R * 2 + 40), pygame.SRCALPHA)
            pygame.draw.circle(ring, (90, 255, 140, int(40 + 120 * a)), (R + 20, R + 20), R + 6, 3)
            surf.blit(ring, (cx - R - 20, cy - R - 20))
        if env.magnetic_field:                                         # manyetik alan: kutup ışıkları
            for sgn in (-1, 1):
                for i in range(3):
                    rr = pygame.Rect(0, 0, R * (0.9 - i * 0.12), R * 0.22)
                    rr.center = (cx, cy + sgn * R * (0.86 - i * 0.02))
                    pygame.draw.arc(surf, (120, 255, 190) if i != 1 else (170, 140, 255),
                                    rr, 0.2 if sgn < 0 else 3.3, 2.9 if sgn < 0 else 6.1, 2)
        draw_text(surf, "temsilî görsel (kurgusal)" if env.kurgusal else "NASA dokusu · gerçek dönüş süresiyle orantılı",
                  (cx, cy + R + 12), 11, C["text_dim"], anchor="midtop")

    def draw_planet(self, surf, w):
        env = w.env
        r = pygame.Rect(KX, KY, 560, KH)
        glass_panel(surf, r, C["cyan"], 175, 16)
        draw_text(surf, "ÇEVRE (NASA)" if not env.kurgusal else "ÇEVRE (KURGUSAL)", (r.x + 20, r.y + 14), 16, C["cyan"], bold=True)
        rows = [(k, v) for k, v in env.summary().items() if k != "Atmosfer"] + [
            ("Kütle", f"{env.mass_1e24kg:g} ×10²⁴ kg"), ("Yarıçap", f"{env.radius_km:,.0f} km".replace(",", ".")),
            ("Kaçış hızı", f"{env.escape_kms:.1f} km/s"), ("Dönüş", f"{abs(env.rotation_h):g} sa" + (" (ters)" if env.rotation_h < 0 else "")),
            ("Yörünge", f"{env.orbit_d:g} gün"), ("Yüzey suyu", pct_s(env.surface_water * 100) + (" · yüzey altı" if env.subsurface_water else "")),
            ("Buz", pct_s(env.ice * 100)), ("Jeolojik etkinlik", pct_s(env.geology * 100)),
            ("Yüzey ışınımı (iyonlaştırıcı)", pct_s(env.radiation * 100))]
        half = (len(rows) + 1) // 2
        for i, (k, v) in enumerate(rows):
            x = r.x + 20 + (i // half) * 270
            y = r.y + 46 + (i % half) * 22
            draw_text(surf, k, (x, y), 12, C["text_dim"], max_w=130)
            draw_text(surf, str(v), (x + 255, y), 12, C["text"], bold=True, anchor="topright", max_w=120)
        gy = r.y + 46 + half * 22
        R = int(min(118, (r.bottom - gy - 110) // 2))
        self.draw_globe(surf, w, (r.centerx, gy + 14 + R), R)
        atm = ", ".join(f"{g} {pct_s(f * 100, 2)}" for g, f in sorted(env.atmosphere.items(), key=lambda kv: -kv[1]))
        draw_paragraph(surf, tr("Atmosfer (hacimce)") + ": " + (atm or tr("yok")), (r.x + 20, r.bottom - 58), r.w - 40, 12, C["text_dim"],
                       max_lines=3, raw=True)
        h = w.hab
        r2 = pygame.Rect(KX + 580, KY, KW - 580, 330)
        col = (C["green"], C["lime"], C["orange"], C["red"], C["text_dim"])[HCAT.index(h.category)]
        glass_panel(surf, r2, col, 175, 16)
        draw_text(surf, "YAŞANABİLİRLİK", (r2.x + 20, r2.y + 14), 16, col, bold=True)
        draw_text(surf, h.category, (r2.x + 20, r2.y + 40), 20, C["text"], bold=True, max_w=r2.w - 40)
        draw_text(surf, ("YAŞAM DOĞRULANDI" if h.life_detected else "YAŞAM BULUNMADI") if not env.kurgusal else "KURGUSAL DÜNYA",
                  (r2.right - 20, r2.y + 14), 13, C["green"] if h.life_detected else C["orange"], bold=True, anchor="topright")
        self.draw_radar(surf, h, (r2.x + 200, r2.y + 200), 88, col)
        y2 = r2.y + 78
        for txt in h.reasons[:6]:
            for line in wrap_text("• " + tr(txt), 13, r2.w - 430, raw=True)[:2]:
                draw_text(surf, line, (r2.x + 410, y2), 13, C["text"], raw=True)
                y2 += 18
            y2 += 4
        r3 = pygame.Rect(KX + 580, KY + 346, KW - 580, KH - 346)
        glass_panel(surf, r3, C["violet"], 170, 16)
        draw_text(surf, "YAŞAMIN KÖKENİ", (r3.x + 20, r3.y + 12), 16, C["violet"], bold=True)
        y = r3.y + 40
        for o in w.origin:
            colr = C["green"] if o["uygun"] else C["text_mute"]
            if o["uygun"]:
                draw_icon(surf, "check", (r3.x + 28, y + 9), 14, colr)
            draw_text(surf, o["name"], (r3.x + 42, y), 14, colr, bold=o["uygun"])
            chip(surf, (r3.x + 350, y - 2), o["label"], C["gold"] if "kurgusal" in o["label"] else C["cyan"], 11)
            y += 24
        self.draw_chain(surf, w, pygame.Rect(r3.x + 20, y + 4, r3.w - 40, r3.bottom - y - 40))
        oy = w.origin_year
        draw_text(surf, "Prebiyotik ağ (oyun modeli): " + (f"protohücre eşiği {oy / 1e6:.0f} milyon yıl" if oy else "eşiğe ulaşılmadı"),
                  (r3.x + 20, r3.bottom - 26), 12, C["text_dim"])

    def draw_radar(self, surf, h, c, R, col):
        """Yaşanabilirlik etkenleri örümcek grafiği (0 = merkez, 1 = dış halka)."""
        items = [(k, v) for k, v in h.factors.items() if v is not None]
        if len(items) < 3:
            return
        n = len(items)
        cx, cy = c
        for ring in (0.25, 0.5, 0.75, 1.0):
            pts = [(cx + math.cos(-math.pi / 2 + i * math.tau / n) * R * ring, cy + math.sin(-math.pi / 2 + i * math.tau / n) * R * ring)
                   for i in range(n)]
            pygame.draw.polygon(surf, (40, 60, 80), pts, 1)
        pts = []
        for i, (k, v) in enumerate(items):
            a = -math.pi / 2 + i * math.tau / n
            pygame.draw.line(surf, (40, 60, 80), (cx, cy), (cx + math.cos(a) * R, cy + math.sin(a) * R), 1)
            pts.append((cx + math.cos(a) * R * max(0.04, v), cy + math.sin(a) * R * max(0.04, v)))
            lx, ly = cx + math.cos(a) * (R + 14), cy + math.sin(a) * (R + 14)
            anchor = "midleft" if math.cos(a) > 0.3 else ("midright" if math.cos(a) < -0.3 else "center")
            draw_text(surf, k, (lx, ly), 11, C["green"] if v > 0.6 else C["orange"] if v > 0.3 else C["red"], anchor=anchor)
        fill = pygame.Surface((R * 2 + 4, R * 2 + 4), pygame.SRCALPHA)
        pygame.draw.polygon(fill, (*col, 70), [(x - cx + R + 2, y - cy + R + 2) for x, y in pts])
        surf.blit(fill, (cx - R - 2, cy - R - 2))
        pygame.draw.polygon(surf, col, pts, 2)
        for x, y in pts:
            pygame.draw.circle(surf, col, (int(x), int(y)), 3)

    def draw_chain(self, surf, w, rect):
        """Prebiyotik zincir: amino asit -> nükleotit -> RNA -> zar kesecikleri -> protohücre (doluluk = ağ ilerlemesi)."""
        steps = ("amino asit", "nükleotit", "RNA", "zar kesecikleri", "protohücre")
        n = len(steps)
        cy = rect.y + 26
        rr = 20
        xs = [rect.x + 50 + i * (rect.w - 100) / (n - 1) for i in range(n)]
        for i in range(n - 1):
            v = w.network.get(steps[i], 0)
            pygame.draw.line(surf, (60, 60, 100), (xs[i] + rr, cy), (xs[i + 1] - rr, cy), 3)
            if v > 0.02:
                pygame.draw.line(surf, C["violet"], (xs[i] + rr, cy), (xs[i] + rr + (xs[i + 1] - xs[i] - 2 * rr) * min(1, v), cy), 3)
        for i, (x, k) in enumerate(zip(xs, steps)):
            v = max(0.0, min(1.0, w.network.get(k, 0)))
            pygame.draw.circle(surf, (20, 18, 40), (int(x), cy), rr)
            if v > 0.01:
                pygame.draw.arc(surf, C["violet"], (x - rr, cy - rr, rr * 2, rr * 2), math.pi / 2, math.pi / 2 + v * math.tau, 4)
            if v >= 0.999:
                draw_glow(surf, (int(x), cy), 26, C["violet"], 0.5)
            ic = ("cell" if i == 4 else "multi" if i == 3 else "o2" if i in (0, 1) else "cambrian")
            LA.era_icon(surf, ic, (x, cy), 22, C["text"] if v > 0.5 else C["text_mute"])
            draw_text(surf, k, (x, cy + rr + 6), 11, C["text_dim"], anchor="midtop")
            draw_text(surf, pct_s(v * 100), (x, cy + rr + 20), 11, C["violet"], bold=True, anchor="midtop", raw=True)

    # --- YAŞAM
    def rows(self):
        w = self.world
        sp = [s for s in w.species if s.biome == self.biome]
        sp.sort(key=lambda s: (not s.alive, -s.biomass))
        return sp

    def row_at(self, pos):
        x, y = pos
        top = KY + 272 + 40 - 4
        if not (KX <= x <= KX + 860 and top <= y <= top + NROWS * 34):
            return None
        i = (y - top) // 34 + self.scroll
        rows = self.rows()
        return rows[i] if 0 <= i < len(rows) else None

    def storm_of(self, w):
        return max([x["strength"] for x in w.weather if x.get("biome") in (None, self.biome)] + [0.0])

    def draw_life(self, surf, w):
        dr = pygame.Rect(KX, KY + 44, 880, 220)
        if self.biome:
            ev = None
            if self.last_event and self.t - self.last_event[1] < 6:
                ev = (self.last_event[0], self.t - self.last_event[1])
            self.dio.draw(surf, dr, w, self.biome, self.t, 1 / 30, ev, self.storm_of(w))
            alive = sum(1 for s in w.species if s.biome == self.biome and s.alive)
            chip(surf, (dr.x + 10, dr.y + 10), f"{tr(self.biome)} · {alive} {tr('tür')}", C["green"], 12)
            draw_text(surf, "Temsilî canlı kesit: canlı sayısı biyokütleyle orantılı", (dr.right - 10, dr.bottom - 20), 11, C["text"],
                      anchor="topright")
        r = pygame.Rect(KX, KY + 272, 880, KH - 272)
        glass_panel(surf, r, C["green"], 175, 16)
        rows = self.rows()
        if not w.species:
            draw_paragraph(surf, f"{w.env.name}: NASA'ya göre bu cisimde yaşam bulunmamıştır. Kurgusal bir senaryo görmek "
                                 "için soldaki \"Hipotetik yaşam\" anahtarını aç.", (r.x + 24, r.y + 30), r.w - 48, 17, C["text"])
        heads = (("TÜR", 50), ("ALEM", 330), ("BESLENME", 420), ("YAŞAM ALANI", 530), ("BİYOKÜTLE", 640), ("UYGUNLUK", 790))
        for t_, x in heads:
            draw_text(surf, t_, (r.x + x, r.y + 14), 12, C["text_dim"], bold=True)
        y = r.y + 40
        for s in rows[self.scroll:self.scroll + NROWS]:
            sel = s is self.sel
            if sel:
                pygame.draw.rect(surf, (20, 50, 60), (r.x + 8, y - 4, r.w - 16, 30), border_radius=8)
            col = C["text"] if s.alive else C["text_mute"]
            LA.species_art(surf, s, r.x + 28, y + 22, 22, self.t, s.alive)
            draw_text(surf, s.name + ("" if s.alive else " †"), (r.x + 50, y), 15, col, bold=True, max_w=190)
            chip(surf, (r.x + 248, y - 1), "GERÇEK" if s.real else "KURGUSAL", C["green"] if s.real else C["gold"], 10)
            draw_text(surf, s.kingdom, (r.x + 330, y + 2), 13, col)
            draw_text(surf, s.genome.diet, (r.x + 420, y + 2), 13, col)
            draw_text(surf, s.genome.habitat, (r.x + 530, y + 2), 13, col)
            draw_bar(surf, (r.x + 640, y + 6, 130, 9), min(1.0, s.biomass / 120), KCOL.get(s.kingdom, C["green"]), glow=False)
            fit = fitness(s.genome, w.env, s.biome) if s.alive else 0
            draw_bar(surf, (r.x + 790, y + 6, 70, 9), fit, C["cyan"] if fit > 0.5 else C["orange"], glow=False)
            y += 34
        if len(rows) > NROWS:
            draw_text(surf, f"{self.scroll + 1}-{min(len(rows), self.scroll + NROWS)} / {len(rows)} (fare tekerleği)", (r.right - 20, r.bottom - 22),
                      12, C["text_dim"], anchor="topright")
        # sağ: ayrıntı (portre), döngüler, besin ağı
        r2 = pygame.Rect(KX + 900, KY + 44, KW - 900, KH - 44)
        glass_panel(surf, r2, C["cyan"], 175, 16)
        x0, y = r2.x + 18, r2.y + 14
        if self.sel:
            s = self.sel
            LA.species_portrait(surf, s, (x0, y, r2.w - 36, 120), self.t, s.kingdom != "hayvan")
            if s.kingdom == "hayvan":                                   # gerçekçi 3B (dönen)
                img = LA.portrait3d(s, 120, self.t)
                surf.blit(img, (x0 + (r2.w - 36) // 2 - 60, y))
            y += 128
            draw_text(surf, s.name, (x0, y), 17, C["text"], bold=True, max_w=r2.w - 36)
            y += 24
            draw_paragraph(surf, s.note or "", (x0, y), r2.w - 36, 12, C["text_dim"], max_lines=2)
            y += 34
            g = s.genome
            for k, v in (("Metabolizma", g.metabolism), ("Boy", f"10^{g.size:.1f} m"), ("Sıcaklık optimumu", f"{g.temp_opt:.0f} °C"),
                         ("Sosyallik", pct_s(g.social * 100))):
                draw_text(surf, k, (x0, y), 12, C["text_dim"])
                draw_text(surf, str(v), (r2.right - 18, y), 12, C["text"], bold=True, anchor="topright")
                y += 18
            if s.kingdom == "hayvan":
                f0 = max(70.0, min(7000.0, 900.0 * 10 ** (-0.6 * (g.size + 1.0))))
                draw_text(surf, f"Ses profili: ~{f0:.0f} Hz temel frekans (beden boyundan)", (x0, y + 2), 11, C["cyan"], max_w=r2.w - 36)
                y += 20
            y += 6
        else:
            draw_text(surf, "Ayrıntı ve figür için listeden bir tür seç", (x0, y), 12, C["text_dim"], max_w=r2.w - 36)
            y += 26
        draw_text(surf, "MADDE DÖNGÜLERİ (göreli)", (x0, y), 13, C["cyan"], bold=True)
        y += 20
        for k, v in w.eco.pools.items():
            draw_bar(surf, (x0 + 90, y + 4, r2.w - 130, 8), min(1.0, v / (0.35 if k == "oksijen" else 1.5)), C["cyan"], glow=False)
            draw_text(surf, k, (x0, y), 12, C["text_dim"])
            y += 17
        y += 8
        draw_text(surf, "BESİN AĞI", (x0, y), 13, C["green"], bold=True)
        self.draw_web(surf, pygame.Rect(x0, y + 18, r2.w - 36, r2.bottom - y - 30), w)

    def draw_web(self, surf, rect, w):
        sp = [s for s in w.species if s.alive and s.biome == self.biome]
        if not sp:
            return
        levels = {}
        for s in sp:
            levels.setdefault(s.trophic, []).append(s)
        pos = {}
        lv = sorted(levels)
        for i, L in enumerate(lv):
            row = levels[L]
            y = rect.bottom - 14 - i * (rect.h - 28) / max(1, len(lv) - 1)
            for j, s in enumerate(row):
                pos[s.sid] = (rect.x + (j + 0.5) * rect.w / len(row), y)
        for c, p in w.eco.food_web():
            if c in pos and p in pos:
                pygame.draw.line(surf, (60, 110, 90), pos[p], pos[c], 1)
        for s in sp:
            x, y = pos[s.sid]
            col = {"üretici": C["green"], "ayrıştırıcı": C["violet"], "otçul": C["lime"], "hepçil": C["gold"], "etçil": C["red"]}[s.genome.diet]
            rr = 9 + min(6, s.biomass ** 0.3)
            pygame.draw.circle(surf, (14, 22, 36), (int(x), int(y)), int(rr))
            pygame.draw.circle(surf, col, (int(x), int(y)), int(rr), 2)
            LA.species_art(surf, s, x, y + rr * 0.6, rr * 1.3, self.t, True)

    # --- ZAMAN ÇİZELGESİ
    def draw_eras(self, surf, rect):
        """Dünya'nın biyolojik tarihi şeridi (yayımlanmış tarihler); üstel zaman ekseni (yakın geçmiş açılır)."""
        x0, x1 = rect.x + 40, rect.right - 40
        cy = rect.y + 46
        pygame.draw.line(surf, (90, 80, 50), (x0, cy), (x1, cy), 3)
        def X(gya):                                   # üstel ölçek: yakın geçmiş açılır, eski çağlar sıkışmaz
            return x0 + (x1 - x0) * (1 - (gya / 4.54) ** 0.35)
        last = {True: -999, False: -999}
        for i, (gya, ic, lab) in enumerate(LA.ERAS):
            x = X(gya)
            up = i % 2 == 0
            lift = 14 if x - last[up] < 120 else 0          # yakın komşu etiketle çakışmasın: bir kat yukarı/aşağı
            last[up] = x if not lift else -999
            pygame.draw.circle(surf, C["gold"], (int(x), cy), 5)
            yy = cy - 22 - lift if up else cy + 22 + lift
            pygame.draw.line(surf, (90, 80, 50), (x, cy), (x, yy), 1)
            LA.era_icon(surf, ic, (x, yy), 18, C["gold"])
            draw_text(surf, lab, (x, yy - 13 if up else yy + 12), 10, C["text"], anchor="midbottom" if up else "midtop")
        draw_text(surf, "4,54 milyar yıl önce", (x0, cy + 52), 10, C["text_dim"])
        draw_text(surf, "bugün", (x1, cy + 52), 10, C["text_dim"], anchor="topright")

    def draw_timeline(self, surf, w):
        r = pygame.Rect(KX, KY, 780, KH)
        glass_panel(surf, r, C["gold"], 175, 16)
        draw_text(surf, "GEZEGENİN BİYOLOJİK TARİHİ", (r.x + 20, r.y + 14), 16, C["gold"], bold=True)
        items = sorted(w.timeline, key=lambda e: e[0])
        y = r.y + 46
        nshow = 22
        if w.key == "earth":
            self.draw_eras(surf, pygame.Rect(r.x, r.y + 36, r.w, 116))
            y = r.y + 166
            nshow = 17
        start = max(0, len(items) - nshow - self.scroll)
        for yr, kind, txt, real in items[start:start + nshow]:
            draw_text(surf, fmt_year(yr, real), (r.x + 20, y), 12, C["gold"] if real else C["cyan"], bold=True)
            draw_text(surf, txt, (r.x + 210, y), 13, C["text"], max_w=r.w - 330)
            chip(surf, (r.right - 16, y - 2), "gerçek tarih" if real else "simülasyon", C["green"] if real else C["violet"], 10, anchor="topright")
            y += 24
        r2 = pygame.Rect(KX + 800, KY, KW - 800, KH)
        glass_panel(surf, r2, C["cyan"], 175, 16)
        draw_text(surf, "TÜR SAYISI VE BİYOKÜTLE", (r2.x + 20, r2.y + 14), 16, C["cyan"], bold=True)
        gr = pygame.Rect(r2.x + 20, r2.y + 50, r2.w - 40, 260)
        pygame.draw.rect(surf, (10, 16, 34), gr, border_radius=8)
        for i in range(1, 4):
            pygame.draw.line(surf, (24, 32, 56), (gr.x, gr.y + gr.h * i / 4), (gr.right, gr.y + gr.h * i / 4), 1)
        if len(self.hist) > 1:
            n = len(self.hist)
            mt = max(1, max(h[1] for h in self.hist))
            mb = max(1e-6, max(h[2] for h in self.hist))
            base = [0.0] * n
            X = [gr.x + i * gr.w / (n - 1) for i in range(n)]
            for kname in ("mikrop", "mantar", "bitki", "hayvan"):        # alemlere göre yığılmış alan
                vals = [h[3].get(kname, 0) if len(h) > 3 else 0 for h in self.hist]
                if not any(vals):
                    continue
                top = [b_ + v for b_, v in zip(base, vals)]
                poly = [(X[i], gr.bottom - 6 - top[i] / mt * (gr.h - 30)) for i in range(n)] + \
                       [(X[i], gr.bottom - 6 - base[i] / mt * (gr.h - 30)) for i in range(n - 1, -1, -1)]
                fill = pygame.Surface(gr.size, pygame.SRCALPHA)
                pygame.draw.polygon(fill, (*KCOL[kname], 120), [(x - gr.x, y_ - gr.y) for x, y_ in poly])
                surf.blit(fill, gr.topleft)
                base = top
            pts = [(X[i], gr.bottom - 6 - (h[2] / mb) * (gr.h - 30)) for i, h in enumerate(self.hist)]
            pygame.draw.lines(surf, C["cyan"], False, pts, 2)
            draw_text(surf, f"{tr('tür')} {self.hist[-1][1]}", (gr.x + 8, gr.y + 6), 13, C["green"], bold=True, raw=True)
            draw_text(surf, f"{tr('biyokütle')} {self.hist[-1][2]:.0f}", (gr.right - 8, gr.y + 6), 13, C["cyan"], bold=True,
                      anchor="topright", raw=True)
        lx = gr.x
        for kname, col in KCOL.items():
            pygame.draw.rect(surf, col, (lx, gr.bottom + 10, 12, 12), border_radius=3)
            draw_text(surf, kname, (lx + 18, gr.bottom + 8), 12, C["text_dim"])
            lx += 96
        pygame.draw.line(surf, C["cyan"], (lx, gr.bottom + 16), (lx + 16, gr.bottom + 16), 2)
        draw_text(surf, "biyokütle", (lx + 22, gr.bottom + 8), 12, C["text_dim"])
        st = w.stats()
        y = r2.y + 350
        for k in ("tür", "yok olan"):
            draw_text(surf, k.capitalize(), (r2.x + 20, y), 15, C["text_dim"])
            draw_text(surf, str(st[k]), (r2.right - 20, y), 15, C["text"], bold=True, anchor="topright")
            y += 26
        draw_paragraph(surf, "Zamanı soldaki düğmelerle hızlandır. ×10 bin ve üstünde evrim çalışır: mutasyon, doğal seçilim, "
                             "genetik sürüklenme, darboğaz, göç (coğrafi izolasyon), türleşme ve yok oluş.", (r2.x + 20, y + 10),
                       r2.w - 40, 13, C["text_dim"])

    # --- OLAYLAR
    def draw_events(self, surf, w):
        r = pygame.Rect(KX, KY, KW, KH)
        glass_panel(surf, r, C["orange"], 175, 16)
        draw_text(surf, f"ÇEVRESEL DEĞİŞİM · hedef biyom: {self.biome or '-'}", (r.x + 20, r.y + 16), 16, C["orange"], bold=True)
        draw_text(surf, "Olaylar çevreyi ve popülasyonları değiştirir, zaman çizelgesine yazılır ve ses motorunu tetikler.",
                  (r.x + 20, r.y + 250), 14, C["text_dim"])
        dr = pygame.Rect(r.x + 20, r.y + 280, 760, r.h - 300)
        if self.biome:
            ev = None
            if self.last_event and self.t - self.last_event[1] < 6:
                ev = (self.last_event[0], self.t - self.last_event[1])
            self.dio_ev.draw(surf, dr, w, self.biome, self.t, 1 / 30, ev, self.storm_of(w))
            if not ev:
                draw_text(surf, "Bir olay seç: etkisi burada canlandırılır", (dr.centerx, dr.y + 12), 13, C["text"], anchor="midtop")
        x = r.x + 800
        y = r.y + 280
        draw_text(surf, "OLAY GÜNLÜĞÜ", (x, y), 12, C["cyan"], bold=True)
        for ev in list(self.app.bus.history)[-12:][::-1]:
            y += 22
            draw_text(surf, ev["name"], (x, y), 12, C["cyan"], bold=True)
            parts = [tr(ev[k]) for k in ("label", "biome", "species") if ev.get(k)]
            if ev.get("strength") is not None:
                parts.append(pct_s(ev["strength"] * 100, 0))
            draw_text(surf, " · ".join(parts), (x + 190, y), 12, C["text"], max_w=r.right - x - 210, raw=True)

    def draw_event_icons(self, surf):
        for i, (k, lab) in enumerate(EVENTS):
            bx, by = KX + 20 + (i % 5) * 240, KY + 60 + (i // 5) * 60
            col = C["red"] if k in ("meteor", "volkan") else C["orange"]
            LA.event_icon(surf, k, (bx + 26, by + 24), 26, col)

    # --- SES GÖZLEMEVİ
    def draw_audio(self, surf, w):
        cae = self.app.cae
        r = pygame.Rect(KX, KY, 490, KH)
        glass_panel(surf, r, C["cyan"], 175, 16)
        draw_text(surf, "SES AYARLARI · ERİŞİLEBİLİRLİK", (r.x + 20, r.y + 14), 15, C["cyan"], bold=True)
        r2 = pygame.Rect(KX + 500, KY, 560, KH)
        glass_panel(surf, r2, C["violet"], 175, 16)
        draw_text(surf, f"ORTAM: {w.env.name} · {self.biome or '-'}", (r2.x + 20, r2.y + 14), 15, C["violet"], bold=True)
        draw_text(surf, cae.label, (r2.x + 20, r2.y + 38), 13, C["text_dim"])
        tg = cae.layer_targets()
        y = r2.y + 64
        bufs = getattr(cae, "layer_buf", {}) or {}
        pos = int(self.t * 44100)
        for k in ("atmosfer", "okyanus", "jeoloji", "canlı", "bitki", "uzay aracı"):
            v = tg.get(k, 0)
            draw_bar(surf, (r2.x + 130, y + 4, 200, 10), v, C["violet"], glow=False)
            draw_text(surf, k, (r2.x + 20, y), 13, C["text_dim"])
            draw_text(surf, "sessiz" if v < 0.01 else _pct(v * 100), (r2.x + 340, y), 13, C["text"], raw=True)
            arr = bufs.get(k)
            if arr is not None and len(arr) > 4096 and v >= 0.01:      # katmanın gerçek dalga biçimi (kayan pencere)
                o = pos % (len(arr) - 2048)
                seg = arr[o:o + 2048:32]
                if getattr(seg, "ndim", 1) > 1:
                    seg = seg[:, 0]
                seg = [float(q) for q in seg]
                m = max(abs(q) for q in seg) or 1.0
                pts = [(r2.x + 400 + i * 140 / len(seg), y + 9 - seg[i] / m * 8 * min(1.0, v * 2)) for i in range(len(seg))]
                pygame.draw.lines(surf, C["cyan"], False, pts, 1)
            else:
                pygame.draw.line(surf, (40, 50, 80), (r2.x + 400, y + 9), (r2.x + 540, y + 9), 1)
            y += 24
        draw_text(surf, "Akustik profil", (r2.x + 20, r2.y + 240), 13, C["text_dim"], bold=True)
        if getattr(self, "last_spatial", None):
            nm, res = self.last_spatial
            txt = "duyulmaz (vakum ya da çok uzak)" if res is None else f"sol %{res[0] * 100:.0f} · sağ %{res[1] * 100:.0f} · {res[2]:.0f} m"
            draw_text(surf, f"{nm}: {txt}", (r2.x + 20, r2.y + 444), 13, C["text"], max_w=r2.w - 40)
        mus = cae.music
        draw_text(surf, f"Dinamik müzik: {mus.state or '-'} → '{DMAP(mus)}'", (r2.x + 20, r2.y + 476), 13, C["gold"])
        draw_paragraph(surf, "Uzay boşluğunda dış ortam sesi yoktur; araç ve giysi içi sesler duyulur. Uzaydaki motor/patlama "
                             "sesleri sinematik temsildir. Mikrobiyal sesler görsel-işitsel temsildir, ölçüm değildir.",
                       (r2.x + 20, r2.y + 504), r2.w - 40, 12, C["text_dim"])
        r3 = pygame.Rect(KX + 1070, KY, KW - 1070, KH)
        glass_panel(surf, r3, C["gold"], 175, 16)
        draw_text(surf, "OLAY → SES (geliştirici)", (r3.x + 16, r3.y + 14), 13, C["gold"], bold=True)
        y = r3.y + 38
        for t, name, key, res in list(cae.events.log)[-9:][::-1]:
            draw_text(surf, f"{name} → {tr(key) if key else '-'}", (r3.x + 16, y), 11, C["cyan"], bold=True, max_w=r3.w - 32, raw=True)
            draw_text(surf, res, (r3.x + 16, y + 14), 11, C["text_dim"], max_w=r3.w - 32)
            y += 34
        p = cae.perf
        y = r3.bottom - 170
        draw_text(surf, "PERFORMANS", (r3.x + 16, y), 13, C["gold"], bold=True)
        for k, v in (("sentez", f"{p['synth_ms']:.0f} ms toplam"), ("üretilen ses", p["builds"]), ("çalınan", p["played"]),
                     ("bütçeden düşen", p["dropped"]), ("önbellek", f"{cae.assets.bytes / 1048576:.1f} MB"),
                     ("varlık künyesi", f"{len(cae.assets.meta)} kayıt")):
            y += 20
            draw_text(surf, k, (r3.x + 16, y), 12, C["text_dim"])
            draw_text(surf, str(v), (r3.right - 16, y), 12, C["text"], bold=True, anchor="topright")
        draw_text(surf, "Lisans: özgün prosedürel sentez", (r3.x + 16, r3.bottom - 24), 11, C["green"])

    # --- GÖRÜLEN HAYVANLAR (keşfedilen hayvanların gerçekçi 3B çizimleri)
    def seen_animals(self):
        out = []
        for (key, scen), w in self.worlds.items():
            for sp in w.species:
                if sp.kingdom == "hayvan" and sp.discovered:
                    out.append((w, sp))
        out.sort(key=lambda ws: (ws[0].env.name, not ws[1].alive, ws[1].name))
        return out

    def draw_bestiary(self, surf, w):
        seen = self.seen_animals()
        r = pygame.Rect(KX, KY, 470, KH)
        glass_panel(surf, r, C["gold"], 180, 16)
        draw_text(surf, "GÖRÜLEN HAYVANLAR", (r.x + 20, r.y + 14), 16, C["gold"], bold=True)
        if not seen:
            draw_paragraph(surf, "Henüz hayvan görmedin. YAŞAM sekmesinde bir biyomu ARAŞTIR: keşfedilen hayvanlar burada gerçekçi 3B "
                                 "çizimleriyle toplanır.", (r.x + 20, r.y + 50), r.w - 40, 15, C["text"])
            return
        sel = getattr(self, "best_sel", None)
        if sel is None or all(sel is not sp for _, sp in seen):
            sel = self.best_sel = seen[0][1]
        wsel = next(wd for wd, sp in seen if sp is sel)
        view = pygame.Rect(r.x + 15, r.y + 44, r.w - 30, KH - 44 - 230)
        bg = pygame.Surface(view.size)
        for yy in range(view.h):
            k = yy / view.h
            pygame.draw.line(bg, (int(18 + 26 * k), int(26 + 30 * k), int(44 + 26 * k)), (0, yy), (view.w, yy))
        surf.blit(bg, view.topleft)
        draw_glow(surf, (view.centerx, view.bottom - 40), 160, (120, 160, 210), 0.25)
        img = LA.portrait3d(sel, min(view.w, view.h) - 20, self.t * 0.8, ss=1)
        surf.blit(img, (view.centerx - img.get_width() // 2, view.y + (view.h - img.get_height()) // 2 + 10))
        pygame.draw.rect(surf, (90, 110, 150), view, 1, border_radius=6)
        chip(surf, (view.x + 10, view.y + 10), "GERÇEK" if sel.real else "KURGUSAL", C["green"] if sel.real else C["gold"], 11)
        y = view.bottom + 10
        draw_text(surf, sel.name + ("" if sel.alive else " †"), (r.x + 20, y), 20, C["text"], bold=True, max_w=r.w - 40)
        y += 30
        g = sel.genome
        par = next((p_ for p_ in wsel.species if p_.sid == sel.parent), None) if sel.parent is not None else None
        rows = [("Gezegen", wsel.env.name), ("Biyom", tr(sel.biome)), ("Yaşam alanı", tr(g.habitat)), ("Beslenme", tr(g.diet)),
                ("Boy", f"10^{g.size:.1f} m"), ("Sıcaklık optimumu", f"{g.temp_opt:.0f} °C"),
                ("Köken", (tr("evrimleşti, atası") + ": " + par.name) if par else tr("başlangıç türü"))]
        for k, v in rows:
            draw_text(surf, k, (r.x + 20, y), 13, C["text_dim"])
            draw_text(surf, str(v), (r.right - 20, y), 13, C["text"], bold=True, anchor="topright", max_w=260, raw=True)
            y += 20
        draw_text(surf, "3B çizim genomdan üretilir; temsilîdir.", (r.x + 20, r.bottom - 26), 11, C["text_mute"])
        # sağ: kart ızgarası
        r2 = pygame.Rect(KX + 490, KY, KW - 490, KH)
        glass_panel(surf, r2, C["cyan"], 175, 16)
        draw_text(surf, tr("{0} tür görüldü").format(len(seen)), (r2.x + 20, r2.y + 14), 15, C["cyan"], bold=True, raw=True)
        cw, chh = 150, 172
        cols = max(1, (r2.w - 30) // (cw + 10))
        rows_vis = max(1, (r2.h - 60) // (chh + 10))
        sc = getattr(self, "best_scroll", 0)
        sc = self.best_scroll = min(sc, max(0, (len(seen) + cols - 1) // cols - rows_vis))
        self.best_cards = []
        for i, (wd, sp) in enumerate(seen[sc * cols:(sc + rows_vis) * cols]):
            cx = r2.x + 20 + (i % cols) * (cw + 10)
            cy = r2.y + 46 + (i // cols) * (chh + 10)
            card = pygame.Rect(cx, cy, cw, chh)
            on = sp is sel
            pygame.draw.rect(surf, (24, 40, 60) if on else (16, 24, 40), card, border_radius=10)
            pygame.draw.rect(surf, C["gold"] if on else (50, 70, 100), card, 2 if on else 1, border_radius=10)
            im = LA.card3d(sp, cw - 10)
            if im is not None:
                surf.blit(im, (cx + 5, cy + 4))
            else:
                LA.species_art(surf, sp, cx + cw / 2, cy + 110, 60, self.t, sp.alive)
            draw_text(surf, sp.name + ("" if sp.alive else " †"), (cx + 8, cy + chh - 40), 12, C["text"] if sp.alive else C["text_mute"],
                      bold=True, max_w=cw - 16, raw=True)
            draw_text(surf, wd.env.name.split(" (")[0], (cx + 8, cy + chh - 22), 11, C["text_dim"], max_w=cw - 16)
            self.best_cards.append((card, sp))
        if len(seen) > cols * rows_vis:
            draw_text(surf, "fare tekerleği: kaydır", (r2.right - 20, r2.y + 16), 11, C["text_dim"], anchor="topright")


def DMAP(m):
    return m.STATES.get(m.state, "-") if m.state else "-"

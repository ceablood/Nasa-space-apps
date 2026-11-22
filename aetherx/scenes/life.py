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

PLANETS = [("earth", "Dünya"), ("moon", "Ay"), ("mars", "Mars"), ("venus", "Venüs"), ("jupiter", "Jüpiter"),
           ("dunya_benzeri", "Dünya benzeri*"), ("okyanus", "Okyanus*"), ("buz", "Buz*"), ("volkanik", "Volkanik*"),
           ("kurak", "Kurak*"), ("radyasyon", "Radyasyonlu*")]
SPEEDS = [(0, "DURAKLAT"), (1, "×1 yıl/sn"), (100, "×100"), (1e4, "×10 bin"), (1e6, "×1 milyon")]
EVENTS = [("volkan", "Volkan"), ("meteor", "Meteor"), ("kuraklik", "Kuraklık"), ("buzul", "Buzul dönemi"),
          ("sicak", "Aşırı sıcak"), ("atmosfer", "Atmosfer değişimi"), ("deniz", "Deniz seviyesi"),
          ("radyasyon", "Radyasyon"), ("yildiz", "Yıldız patlaması"), ("firtina", "Fırtına")]
TABS = ["GEZEGEN", "YAŞAM", "ZAMAN ÇİZELGESİ", "OLAYLAR", "SES GÖZLEMEVİ"]
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
            self.hist.append((st["yıl"], st["tür"], st["biyokütle"]))
            self.hist = self.hist[-240:]

    # ------------------------------------------------------------------ çizim
    def draw(self, surf):
        super().draw(surf)
        w = self.world
        self.draw_title(surf, sub=f"{w.env.name} · {w.env.source}")
        draw_text(surf, fmt_year(w.year, False), (40, 160), 13, C["gold"], bold=True, anchor="bottomleft")
        draw_text(surf, "* kurgusal ötegezegen", (40, H - 92), 12, C["text_dim"])
        getattr(self, ("draw_planet", "draw_life", "draw_timeline", "draw_events", "draw_audio")[self.tab])(surf, w)
        self.draw_widgets(surf)

    # --- GEZEGEN
    def draw_planet(self, surf, w):
        env = w.env
        r = pygame.Rect(KX, KY, 560, KH)
        glass_panel(surf, r, C["cyan"], 175, 16)
        draw_text(surf, "ÇEVRE (NASA)" if not env.kurgusal else "ÇEVRE (KURGUSAL)", (r.x + 20, r.y + 14), 16, C["cyan"], bold=True)
        rows = list(env.summary().items()) + [
            ("Kütle", f"{env.mass_1e24kg:g} ×10²⁴ kg"), ("Yarıçap", f"{env.radius_km:,.0f} km".replace(",", ".")),
            ("Kaçış hızı", f"{env.escape_kms:.1f} km/s"), ("Dönüş", f"{abs(env.rotation_h):g} sa" + (" (ters)" if env.rotation_h < 0 else "")),
            ("Yörünge", f"{env.orbit_d:g} gün"), ("Yüzey suyu", f"%{env.surface_water * 100:.0f}" + (" · yüzey altı" if env.subsurface_water else "")),
            ("Buz", f"%{env.ice * 100:.0f}"), ("Jeolojik etkinlik", f"%{env.geology * 100:.0f}"),
            ("Yüzey ışınımı (iyonlaştırıcı)", f"%{env.radiation * 100:.0f}")]
        y = r.y + 46
        for k, v in rows:
            draw_text(surf, k, (r.x + 20, y), 14, C["text_dim"])
            draw_text(surf, str(v), (r.right - 20, y), 14, C["text"], bold=True, anchor="topright", max_w=300)
            y += 24
        atm = ", ".join(f"{g} {pct_s(f * 100, 2)}" for g, f in sorted(env.atmosphere.items(), key=lambda kv: -kv[1]))
        draw_paragraph(surf, "Atmosfer (hacimce): " + (atm or "yok"), (r.x + 20, y + 6), r.w - 40, 13, C["text_dim"], max_lines=3)
        h = w.hab
        r2 = pygame.Rect(KX + 580, KY, KW - 580, 330)
        col = (C["green"], C["lime"], C["orange"], C["red"], C["text_dim"])[HCAT.index(h.category)]
        glass_panel(surf, r2, col, 175, 16)
        draw_text(surf, "YAŞANABİLİRLİK", (r2.x + 20, r2.y + 14), 16, col, bold=True)
        draw_text(surf, h.category, (r2.x + 20, r2.y + 40), 20, C["text"], bold=True, max_w=r2.w - 40)
        draw_text(surf, ("YAŞAM DOĞRULANDI" if h.life_detected else "YAŞAM BULUNMADI") if not env.kurgusal else "KURGUSAL DÜNYA",
                  (r2.right - 20, r2.y + 14), 13, C["green"] if h.life_detected else C["orange"], bold=True, anchor="topright")
        y = r2.y + 78
        for k, v in h.factors.items():
            if v is None:
                continue
            draw_bar(surf, (r2.x + 150, y + 4, 240, 10), v, C["green"] if v > 0.6 else C["orange"] if v > 0.3 else C["red"], glow=False)
            draw_text(surf, k, (r2.x + 20, y), 13, C["text_dim"])
            y += 22
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
        y += 6
        for k in ("amino asit", "nükleotit", "RNA", "zar kesecikleri", "protohücre"):
            draw_bar(surf, (r3.x + 160, y + 4, 260, 9), w.network.get(k, 0), C["violet"], glow=False)
            draw_text(surf, k, (r3.x + 20, y), 12, C["text_dim"])
            y += 19
        oy = w.origin_year
        draw_text(surf, "Prebiyotik ağ (oyun modeli): " + (f"protohücre eşiği {oy / 1e6:.0f} milyon yıl" if oy else "eşiğe ulaşılmadı"),
                  (r3.x + 20, y + 4), 12, C["text_dim"])

    # --- YAŞAM
    def rows(self):
        w = self.world
        sp = [s for s in w.species if s.biome == self.biome]
        sp.sort(key=lambda s: (not s.alive, -s.biomass))
        return sp

    def row_at(self, pos):
        x, y = pos
        if not (KX <= x <= KX + 860 and KY + 84 <= y <= KY + 84 + 15 * 34):
            return None
        i = (y - KY - 84) // 34 + self.scroll
        rows = self.rows()
        return rows[i] if 0 <= i < len(rows) else None

    def draw_life(self, surf, w):
        r = pygame.Rect(KX, KY + 44, 880, KH - 44)
        glass_panel(surf, r, C["green"], 175, 16)
        rows = self.rows()
        if not w.species:
            draw_paragraph(surf, f"{w.env.name}: NASA'ya göre bu cisimde yaşam bulunmamıştır. Kurgusal bir senaryo görmek "
                                 "için soldaki \"Hipotetik yaşam\" anahtarını aç.", (r.x + 24, r.y + 30), r.w - 48, 17, C["text"])
        heads = (("TÜR", 20), ("ALEM", 330), ("BESLENME", 420), ("YAŞAM ALANI", 530), ("BİYOKÜTLE", 640), ("UYGUNLUK", 790))
        for t, x in heads:
            draw_text(surf, t, (r.x + x, r.y + 14), 12, C["text_dim"], bold=True)
        y = r.y + 40
        for s in rows[self.scroll:self.scroll + 15]:
            sel = s is self.sel
            if sel:
                pygame.draw.rect(surf, (20, 50, 60), (r.x + 8, y - 4, r.w - 16, 30), border_radius=8)
            col = C["text"] if s.alive else C["text_mute"]
            draw_text(surf, s.name + ("" if s.alive else " †"), (r.x + 20, y), 15, col, bold=True, max_w=210)
            chip(surf, (r.x + 238, y - 1), "GERÇEK" if s.real else "KURGUSAL", C["green"] if s.real else C["gold"], 10)
            draw_text(surf, s.kingdom, (r.x + 330, y + 2), 13, col)
            draw_text(surf, s.genome.diet, (r.x + 420, y + 2), 13, col)
            draw_text(surf, s.genome.habitat, (r.x + 530, y + 2), 13, col)
            draw_bar(surf, (r.x + 640, y + 6, 130, 9), min(1.0, s.biomass / 120), C["green"], glow=False)
            fit = fitness(s.genome, w.env, s.biome) if s.alive else 0
            draw_bar(surf, (r.x + 790, y + 6, 70, 9), fit, C["cyan"] if fit > 0.5 else C["orange"], glow=False)
            y += 34
        if len(rows) > 15:
            draw_text(surf, f"{self.scroll + 1}-{min(len(rows), self.scroll + 15)} / {len(rows)} (fare tekerleği)", (r.right - 20, r.bottom - 26),
                      12, C["text_dim"], anchor="topright")
        # sağ: ayrıntı, döngüler, besin ağı
        r2 = pygame.Rect(KX + 900, KY + 44, KW - 900, KH - 44)
        glass_panel(surf, r2, C["cyan"], 175, 16)
        x0, y = r2.x + 18, r2.y + 14
        if self.sel:
            s = self.sel
            draw_text(surf, s.name, (x0, y), 18, C["text"], bold=True, max_w=r2.w - 36)
            y += 28
            draw_paragraph(surf, s.note or "", (x0, y), r2.w - 36, 13, C["text_dim"], max_lines=3)
            y += 52
            g = s.genome
            for k, v in (("Metabolizma", g.metabolism), ("Boy", f"10^{g.size:.1f} m"), ("Sıcaklık optimumu", f"{g.temp_opt:.0f} °C"),
                         ("Sosyallik", pct_s(g.social * 100))):
                draw_text(surf, k, (x0, y), 13, C["text_dim"])
                draw_text(surf, str(v), (r2.right - 18, y), 13, C["text"], bold=True, anchor="topright")
                y += 20
            if s.kingdom == "hayvan":
                f0 = max(70.0, min(7000.0, 900.0 * 10 ** (-0.6 * (g.size + 1.0))))
                draw_text(surf, f"Ses profili: ~{f0:.0f} Hz temel frekans (beden boyundan)", (x0, y + 4), 12, C["cyan"],
                          max_w=r2.w - 36)
                y += 24
            y += 8
        draw_text(surf, "MADDE DÖNGÜLERİ (göreli)", (x0, y), 13, C["cyan"], bold=True)
        y += 22
        for k, v in w.eco.pools.items():
            draw_bar(surf, (x0 + 90, y + 4, r2.w - 130, 9), min(1.0, v / (0.35 if k == "oksijen" else 1.5)), C["cyan"], glow=False)
            draw_text(surf, k, (x0, y), 12, C["text_dim"])
            y += 19
        y += 10
        draw_text(surf, "BESİN AĞI", (x0, y), 13, C["green"], bold=True)
        self.draw_web(surf, pygame.Rect(x0, y + 20, r2.w - 36, r2.bottom - y - 34), w)

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
            rr = 4 + min(9, s.biomass ** 0.4)
            pygame.draw.circle(surf, col, (int(x), int(y)), int(rr))

    # --- ZAMAN ÇİZELGESİ
    def draw_timeline(self, surf, w):
        r = pygame.Rect(KX, KY, 780, KH)
        glass_panel(surf, r, C["gold"], 175, 16)
        draw_text(surf, "GEZEGENİN BİYOLOJİK TARİHİ", (r.x + 20, r.y + 14), 16, C["gold"], bold=True)
        items = sorted(w.timeline, key=lambda e: e[0])
        start = max(0, len(items) - 22 - self.scroll)
        y = r.y + 46
        for yr, kind, txt, real in items[start:start + 22]:
            draw_text(surf, fmt_year(yr, real), (r.x + 20, y), 12, C["gold"] if real else C["cyan"], bold=True)
            draw_text(surf, txt, (r.x + 210, y), 13, C["text"], max_w=r.w - 330)
            chip(surf, (r.right - 16, y - 2), "gerçek tarih" if real else "simülasyon", C["green"] if real else C["violet"], 10, anchor="topright")
            y += 24
        r2 = pygame.Rect(KX + 800, KY, KW - 800, KH)
        glass_panel(surf, r2, C["cyan"], 175, 16)
        draw_text(surf, "TÜR SAYISI VE BİYOKÜTLE", (r2.x + 20, r2.y + 14), 16, C["cyan"], bold=True)
        if len(self.hist) > 1:
            gr = pygame.Rect(r2.x + 20, r2.y + 50, r2.w - 40, 260)
            pygame.draw.rect(surf, (10, 16, 34), gr, border_radius=8)
            mt = max(1, max(h[1] for h in self.hist))
            mb = max(1e-6, max(h[2] for h in self.hist))
            for idx, col, m in ((1, C["green"], mt), (2, C["cyan"], mb)):
                pts = [(gr.x + i * gr.w / (len(self.hist) - 1), gr.bottom - 8 - (h[idx] / m) * (gr.h - 16)) for i, h in enumerate(self.hist)]
                pygame.draw.lines(surf, col, False, pts, 2)
            draw_text(surf, f"tür {self.hist[-1][1]}", (gr.x + 8, gr.y + 6), 13, C["green"], bold=True)
            draw_text(surf, f"biyokütle {self.hist[-1][2]:.0f}", (gr.right - 8, gr.y + 6), 13, C["cyan"], bold=True, anchor="topright")
        st = w.stats()
        y = r2.y + 330
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
        y = r.y + 290
        for ev in list(self.app.bus.history)[-12:][::-1]:
            draw_text(surf, ev["name"], (r.x + 20, y), 13, C["cyan"], bold=True)
            parts = [tr(ev[k]) for k in ("label", "biome", "species") if ev.get(k)]
            if ev.get("strength") is not None:
                parts.append(pct_s(ev["strength"] * 100, 0))
            draw_text(surf, " · ".join(parts), (r.x + 240, y), 13, C["text"], max_w=r.w - 260, raw=True)
            y += 22

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
        for k in ("atmosfer", "okyanus", "jeoloji", "canlı", "bitki", "uzay aracı"):
            v = tg.get(k, 0)
            draw_bar(surf, (r2.x + 130, y + 4, 260, 10), v, C["violet"], glow=False)
            draw_text(surf, k, (r2.x + 20, y), 13, C["text_dim"])
            draw_text(surf, "sessiz" if v < 0.01 else f"%{v * 100:.0f}", (r2.x + 410, y), 13, C["text"])
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


def DMAP(m):
    return m.STATES.get(m.state, "-") if m.state else "-"

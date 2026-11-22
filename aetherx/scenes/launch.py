# -*- coding: utf-8 -*-
"""
FIRLATMA - YERDEN UZAYA KESİNTİSİZ SİNEMATİK

Rampa, kule, binalar ve ağaçlar YERDE kalır; kamera yalnızca roketi izler.
Aşamalar: geri sayım -> ateşleme (su püskürtme, duman) -> kalkış (kule
kollarından ayrılma) -> bulut katmanı -> Max-Q (ses hızı yoğunlaşma bulutu)
-> 1. kademe ayrılması (güçlendirici düşer) -> ince atmosfer (alev
genişler) -> uzay, Dünya'nın eğriliği -> yörünge.
"""
import math
import random

import numpy as np
import pygame

from . import Scene
from .. import art
from .. import data as D
from .. import i18n
from .. import cinema
from .. import rocket as R
from .. import space3d as S3
from ..config import C, H, W
from ..fx import WEB
from ..fx import (ParticleSystem, Shake, Starfield, clamp, draw_glow, ease_out_back, ease_out_cubic, lerp,
                  lerp_color, overlay, scale_color, vertical_gradient, soft_circle)
from ..ui import UI, Button, draw_bar, draw_text, glass_panel

GS = 780                       # zeminin ekrandaki y'si (kamera 0'dayken)
SEP_ALT = 5200                 # 1. kademe ayrılması (piksel irtifa)
SPACE_ALT = 9000
END_ALT = 12500
KM_PER_PX = 0.016              # HUD için

CONTROL = [(0.2, "GÖREV KONTROL: Tüm istasyonlar, fırlatma için durum bildirin."),
           (0.8, "YAKIT: Hazır.  ELEKTRİK: Hazır.  İLETİŞİM: Hazır."),
           (1.3, "NOVA: Yörünge hesaplandı. Fırlatmaya onay veriyorum.")]
# Gerçek bir yörünge fırlatmasının tipik hız profili (Falcon 9 / Soyuz telemetrisi, yaklaşık):
# 14 km'de Max-Q ~1.500 km/sa, 80 km'de kademe ayrılması ~8.000 km/sa, ~200 km'de yörünge hızı ~27.600 km/sa (7,66 km/s).
SPEED_PROFILE = [(0, 0), (1, 300), (5, 900), (14, 1600), (35, 3600), (60, 6200), (83, 8300), (120, 14500),
                 (160, 21500), (200, 27600)]


def real_speed(km):
    pts = SPEED_PROFILE
    if km >= pts[-1][0]:
        return pts[-1][1]
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if a <= km <= b:
            return va + (vb - va) * (km - a) / (b - a)
    return 0.0


EVENTS = [(0.0, "Kalkış! Kule temizlendi."), (900, "Ses hızı aşıldı (Max-Q)."),
          (SEP_ALT, "1. kademe ayrıldı. Üst kademe ateşlendi."), (SPACE_ALT, "Uzaya ulaşıldı. Yörüngeye giriliyor.")]


class LaunchScene(Scene):
    bloom_k = 0.25           # egzoz bulutları zaten parlak: aşırı patlamasın
    music = "launch"
    show_topbar = False
    allow_events = False

    def __init__(self, app):
        super().__init__(app)
        self.ps = ParticleSystem(2600)
        self.shake = Shake()
        self.stars = Starfield(W, H, 520, 61)
        self.sky_cache = {}
        rng = random.Random(9)
        # bulutlar 3-11 km arasında (troposfer)
        self.clouds = [(rng.uniform(-200, W + 200), rng.uniform(190, 690), rng.uniform(80, 220), rng.uniform(0.5, 1.0))
                       for _ in range(30)]
        self.clouds += [(rng.uniform(-200, W + 200), rng.uniform(700, 760), rng.uniform(200, 340), 0.35) for _ in range(8)]
        self.trees = [(rng.uniform(0, W), rng.uniform(0.7, 1.3), rng.random()) for _ in range(70)]

    # ------------------------------------------------------------------ giriş
    def enter(self, pad=0, **kw):
        g = self.game
        p = g.take_pad(pad)
        if not p:
            self.app.go("base")
            return
        self.pad = pad
        self.design = p["design"]
        self.rep = R.analyze(g, self.design)
        self.app.mission = {"design": self.design, "rep": self.rep, "pad": pad, "start_min": g.minutes}
        self.t = 0.0
        self._hz = None
        self.alt = 0.0
        self.vel = 0.0
        self.cam = 0.0
        self.count_shown = None
        self.ignited = self.lifted = self.done = self.separated = False
        self.ev_i = 0
        self.ev_text = None
        self.ev_t = 0.0
        self.ps.clear()
        self.size = self.rep.get("size", 1)
        self.eng = self.design["engine"]
        self.booster, self.b_nozzle = art.render_booster(self.size, g.name, g.color, 1.0)
        craft, self.c_noz = art.render_spacecraft(self.design["hull"], self.design["engine"], self.design["power"],
                                                  self.design["antenna"], self.design["payloads"], g.name, g.color, 1.0)
        bw = self.booster.get_width() * 0.62
        k = clamp(bw / max(1, craft.get_width() * 0.45), 0.35, 1.0)
        self.ck = k
        self.craft = pygame.transform.smoothscale(craft, (int(craft.get_width() * k), int(craft.get_height() * k)))
        self.fall = None                       # düşen güçlendirici: [x, y_dünya, vx, vy, açı, açısal hız]
        self.fairing = []
        self.widgets = [Button((W - 190, H - 70, 160, 46), "ATLA", self.skip, accent=C["text_dim"], size=15,
                               hotkey=pygame.K_ESCAPE)]
        self.night = g.is_night()
        self.app.bubble.clear()
        self.app.audio.ambient("amb_base")

    def skip(self):
        if not self.done:
            self.done = True
            self.app.audio.stop_loop(800)
            self.app.audio.ambient(None)
            self.app.go("flight")

    # ---------------------------------------------------------------- konumlar
    def sy(self, world_y):
        """Dünya yüksekliği -> ekran y."""
        return GS - (world_y - self.cam)

    def rocket_world(self):
        """Güçlendiricinin merkezinin dünya yüksekliği."""
        return self.alt + self.booster.get_height() / 2 + 26

    # ----------------------------------------------------------------- döngü
    def update(self, dt):
        super().update(dt)
        t = self.t
        a = self.app.audio
        n = None
        for i, tt in enumerate((1.6, 2.6, 3.6)):
            if t >= tt:
                n = 3 - i
        if t >= 4.6:
            n = 0
        if n != self.count_shown and n is not None:
            self.count_shown = n
            a.play("beep" if n > 0 else "go", 0.9)
        if t >= 4.0 and not self.ignited:
            self.ignited = True
            a.loop("launch", 0.9)
            self.shake.add(0.5)
        if t >= 4.9 and not self.lifted:
            self.lifted = True
            self.shake.add(0.6)
        # fizik: itki - kütle - sürüklenme
        if self.lifted:
            thrust = 90.0 if not self.separated else 140.0      # kütle azaldıkça ivme artar
            drag = 0.00004 * self.vel * self.vel * max(0.0, 1 - self.alt / SPACE_ALT)
            self.vel += (thrust + self.vel * 0.13 - drag) * dt
            self.alt += self.vel * dt
        old_cam = self.cam
        self.cam = max(0.0, self.alt - 140)
        dcam = self.cam - old_cam
        if dcam:
            for q in self.ps.p:                       # parçacıklar dünyaya bağlıdır: kamera kayınca aşağı iner
                q.y += dcam
            for rr in self.ps.rings:
                rr[1] += dcam
        # olay yazıları
        if self.lifted and self.ev_i < len(EVENTS) and self.alt >= EVENTS[self.ev_i][0]:
            self.ev_text = EVENTS[self.ev_i][1]
            self.ev_t = 3.0
            if self.ev_i == 1:
                a.play("whoosh", 0.8)
            self.ev_i += 1
            a.play("radio", 0.6)
        self.ev_t = max(0.0, self.ev_t - dt)
        # kademe ayrılması
        if self.alt >= SEP_ALT and not self.separated:
            self.separated = True
            x, y = W // 2, self.rocket_world()
            self.fall = [x, y, -30.0, self.vel * 0.6, 0.0, -0.5]
            a.play("sep", 1.0)
            a.stop_loop(1500)
            self.shake.add(0.4)
            self.ps.sparks(x, self.sy(y + self.booster.get_height() / 2), 40, (255, 220, 160), grav=0)
            self.ps.ring(x, self.sy(y + self.booster.get_height() / 2), 120, (255, 230, 200))
            for side in (-1, 1):
                self.fairing.append([x + side * 14, y + self.booster.get_height() / 2 + self.c_noz[1] * self.ck * 0.5,
                                     side * 70.0, self.vel * 0.7, 0.0, side * 1.6])
        if self.fall:
            f = self.fall
            f[3] -= 160 * dt
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            f[4] += f[5] * dt
        for f in self.fairing:
            f[3] -= 160 * dt
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            f[4] += f[5] * dt
        # sarsıntı: atmosferde güçlü, uzayda yok
        if self.ignited:
            dense = clamp(1 - self.alt / 3000, 0, 1)
            sh = D.PART["engine"][self.eng].get("shake", 0.5)
            self.shake.set_min((0.18 + 0.3 * sh) * dense + (0.25 if 700 < self.alt < 1300 else 0))
        self.emit_particles(dt)
        self.ps.update(dt, wind=-30 * clamp(1 - self.alt / 4000, 0, 1))
        self.shake.update(dt)
        self.stars.update(dt)
        if (self.alt >= END_ALT or t > 34) and not self.done:
            self.skip()

    def emit_particles(self, dt):
        if not self.ignited:
            return
        x = W // 2
        wy = self.rocket_world()
        bh = self.booster.get_height()
        thin = clamp((self.alt - 2500) / 6000, 0, 1)                  # ince atmosfer: alev genişler
        if not self.separated:
            nx, ny = x, self.sy(wy - bh / 2) + 22
            self.ps.fire(nx, ny, n=10, angle=math.pi / 2, spread=0.2 + thin * 0.9, speed=(380, 760), size=(12, 30),
                         life=(0.2, 0.5 + thin * 0.4), ramp="fire", drag=1.5 - thin)
            if self.size >= 2:
                for side in (-1, 1):
                    self.ps.fire(nx + side * self.booster.get_width() * 0.28, ny - 8, n=5, angle=math.pi / 2,
                                 spread=0.2 + thin * 0.6, speed=(300, 600), size=(8, 20), life=(0.2, 0.45), ramp="fire")
            if self.alt < 3200:
                self.ps.smoke(nx, ny + 30, n=3, angle=math.pi / 2, spread=0.35, speed=(30, 100), size=(20, 40),
                              life=(4.0, 7.0), color=(222, 222, 228), alpha=150 * (1 - self.alt / 3200), grow=34, grav=0)
            if self.alt < 260:                                         # rampa: alev kanalından yanlara duman ve su
                gy = self.sy(0)
                for side in (-1, 1):
                    self.ps.smoke(x + side * 70, gy - 12, n=5, angle=(0 if side > 0 else math.pi), spread=0.3,
                                  speed=(220, 520), size=(34, 64), life=(3.0, 5.5), color=(232, 232, 238), alpha=180,
                                  grow=60, grav=-12)
                    if self.t < 7:
                        self.ps.glow(x + side * 110, gy - 30, 3, (190, 220, 255), speed=(80, 220), size=(1, 3),
                                     life=(0.4, 0.9), grav=500)
            if 700 < self.alt < 1300:                                  # Max-Q: yoğunlaşma konisi
                cy = self.sy(wy + bh * 0.1)
                for _ in range(3):
                    a = random.uniform(-0.9, 0.9)
                    self.ps.smoke(x + math.sin(a) * 50, cy + abs(a) * 40, 1, angle=math.pi / 2 + a * 0.6, spread=0.2,
                                  speed=(40, 120), size=(10, 20), life=(0.3, 0.6), color=(240, 244, 250), alpha=140,
                                  grow=30, grav=0)
        else:
            nx = x
            ny = self.sy(wy - bh / 2) + 6
            art.emit_flame(self.ps, nx, ny, self.eng, math.pi / 2, 1.0, 1.1 + thin * 0.6)
        if self.fall and self.fall[1] > self.cam - 400:
            f = self.fall
            if random.random() < 0.6:
                self.ps.smoke(f[0], self.sy(f[1] - bh / 2), 1, angle=-math.pi / 2, spread=1.0, speed=(10, 40),
                              size=(6, 12), life=(1.0, 2.0), color=(200, 200, 210), alpha=80, grow=20, grav=0)

    # ------------------------------------------------------------------ çizim
    def sky(self):
        k = clamp(self.alt / 3200, 0, 1) ** 0.7                 # 50 km üstünde gökyüzü neredeyse siyah
        if self.night:
            top, bot = (6, 10, 26), (24, 34, 66)
        else:
            top, bot = (52, 120, 205), (168, 208, 238)
        top = lerp_color(top, (1, 2, 8), clamp(k * 1.25, 0, 1))
        bot = lerp_color(bot, (8, 12, 34) if not self.night else (4, 6, 18), k)
        key = (top, bot)
        s = self.sky_cache.get(key)
        if s is None:
            s = vertical_gradient((W, H), top, bot)
            if len(self.sky_cache) > 60:
                self.sky_cache.clear()
            self.sky_cache[key] = s
        return s

    def draw(self, surf):
        ox, oy = self.shake.offset(22)
        frame = surf
        frame.blit(self.sky(), (0, 0))
        k = clamp(self.alt / 3200, 0, 1)
        if self.night or k > 0.25:
            self.stars.draw(frame, max(clamp((k - 0.25) / 0.6, 0, 1), 0.9 if self.night else 0))
        self.draw_earth_curve(frame)
        self.draw_ground(frame, ox, oy)
        self.draw_clouds(frame, ox, oy, back=True)
        self.draw_rocket(frame, ox, oy)
        self.ps.draw(frame, ox, oy)
        self.draw_clouds(frame, ox, oy, back=False)
        # sinematik: alçak irtifada güneş huzmeleri ve yer pusu, uzayda soğuk renk uyumu
        low = clamp(1 - self.alt / 2600, 0, 1)
        if not self.night:
            cinema.god_rays(frame, (W * 0.84, H * 0.1), (255, 214, 160), 0.38 * low, size=1700, t=self.t)
            cinema.haze(frame, (0, H // 2, W, H // 2), (90, 80, 70), 0.35 * low, top=False)
        cinema.motes(frame, (0, 0, W, H), self.t, 40, (255, 230, 200) if low > 0.3 else (170, 200, 255), strength=0.8)
        cinema.grade(frame, (0, 0, W, H))
        if self.ignited and self.alt < 600:
            kk = clamp(1.0 - (self.t - 4.0) / 3.0, 0, 1)
            if kk > 0:
                overlay(frame, (255, 200, 140, int(70 * kk)))
        self.draw_hud(frame)
        self.draw_widgets(frame)

    def draw_earth_curve(self, s):
        """Uzaya yaklaşırken alt kenarda Dünya'nın eğriliği ve atmosfer çizgisi."""
        k = clamp((self.alt - 6000) / 5500, 0, 1)
        if k <= 0:
            return
        R = int(lerp(9000, 2600, k))
        cy = H + R - int(lerp(40, 170, k))
        img, top = self.horizon(R, cy, k)
        s.blit(img, (0, top))

    def horizon(self, R, cy, k):
        """Önbellekli ufuk: irtifa ilerlemesi (k) 1/60, zaman 1/3 sn adımla değiştiğinde yeniden hesaplanır.
        Eskiden her karede tam doku örneklemesi yapılıyordu (tarayıcıda kare başına ~400 ms)."""
        key = (round(k * 60), int(self.t * 3), i18n.PREFS.get("quality"))
        c = self.__dict__.get("_hz")
        if c is None or c[0] != key:
            img, top = self._horizon(R, cy, k)
            c = self._hz = (key, img, top, cy)
        # aynı adım içinde ufuk eğrisi gerçek cy ile birlikte kayar (kesintisiz yükseliş)
        return c[1], c[2] + int(cy - c[3])

    def _horizon(self, R, cy, k):
        """Uzaydan Dünya ufku: gerçek Dünya dokusu, eğrilik, atmosfer kuşağı, bulut gölgesi (1/4 çözünürlük)."""
        q = 1 if i18n.quality_level() >= 2 else 2
        top = int(cy - R - 30)
        hh = H - top
        if hh <= 2:
            return pygame.Surface((W, 1), pygame.SRCALPHA), H
        w4, h4 = W // q, max(1, hh // q)
        x = (np.arange(w4, dtype=np.float32) + 0.5) * q - W / 2
        y = (np.arange(h4, dtype=np.float32) + 0.5) * q + top
        X, Y = np.meshgrid(x, y)
        d = np.sqrt(X * X + (Y - cy) ** 2) / R                      # 0 merkez, 1 kenar
        inside = d < 1.0
        z = np.sqrt(np.clip(1 - d * d, 0, 1))
        want = max(512, i18n.quality().get("tex", 512))
        if want > 1024 and not (S3.has_texture("earth", want) or S3.disk_has("earth", want)):
            want = 1024                      # 2048 doku fırlatma sırasında üretilmez (atlas üretir ve diske yazar)
        tex = S3.texture("earth", want)
        # görünen şerit ~ Akdeniz'den ekvatora: Türkiye-Afrika-Arabistan manzarası
        lon = 0.62 + X / W * 1.1 * (1.15 - 0.15 * z) + self.t * 0.004
        lat = 0.78 - np.clip((Y - (cy - R)) / max(1.0, H - (cy - R)), 0, 1) * 0.75
        th_, tw_ = tex["rgb"].shape[:2]
        fx = (lon / (2 * math.pi) + 0.5) % 1.0 * tw_ - 0.5          # çift doğrusal (bilinear) örnekleme:
        fy = np.clip((0.5 - lat / math.pi) * th_ - 0.5, 0, th_ - 1.001)  # kıyılarda merdiven izi olmaz
        x0 = np.floor(fx).astype(np.int32); y0 = np.floor(fy).astype(np.int32)
        ax = (fx - x0)[..., None]; ay = (fy - y0)[..., None]
        x0 %= tw_; x1 = (x0 + 1) % tw_; y1 = np.minimum(y0 + 1, th_ - 1)

        def samp(arr):
            a = arr.astype(np.float32)
            if a.ndim == 2:
                a = a[..., None]
            return ((a[y0, x0] * (1 - ax) + a[y0, x1] * ax) * (1 - ay) + (a[y1, x0] * (1 - ax) + a[y1, x1] * ax) * ay)

        rgb = samp(tex["rgb"])
        cl = samp(tex["cloud"])
        # kıyı çizgisini yeniden keskinleştir: okyanus oranını yumuşak örnekleyip smoothstep ile
        # pürüzsüz bir kontur elde ederiz (büyütülmüş dokudaki piksel merdivenleri kaybolur)
        if "spec" in tex:
            if "_ocean" not in tex:
                sp = tex["spec"]
                tex["_ocean"] = tex["rgb"][sp > 0.97].reshape(-1, 3).mean(0).astype(np.float32)
            ocean = tex["_ocean"]
            oc = np.clip(samp(tex["spec"]), 0, 1)
            land = np.clip((rgb - oc * ocean) / np.maximum(1 - oc, 0.08), 0, 255)
            w = oc * oc * (3 - 2 * oc)
            w = np.clip((w - 0.35) / 0.3, 0, 1)
            w = w * w * (3 - 2 * w)
            rgb = land * (1 - w) + ocean * w
        rgb = rgb * (1 - cl) + 250 * cl
        edge = (1.0 - d) * R                                          # kenara piksel uzaklığı
        light = 0.55 + 0.45 * np.clip(edge / 260.0, 0, 1)[..., None]
        limb = np.clip(1 - edge / (26 * k + 4), 0, 1)[..., None] ** 1.6   # ince mavi atmosfer kuşağı
        rgb = rgb * light * (1 - limb * 0.7) + np.array((120, 180, 255), dtype=np.float32) * limb * 0.85
        a = np.clip(edge / q + 0.5, 0, 1) * 255                       # yumuşak (antialias) kenar
        out = np.clip(1 + edge / (14 * k + 3), 0, 1) * (edge < 0)        # dışarıdaki parıltı
        rgb = np.where(out[..., None] > 0, np.array((90, 150, 255), dtype=np.float32), rgb)
        a = np.maximum(a, out * 150).astype(np.uint8)
        arr = np.zeros((h4, w4, 4), dtype=np.uint8)
        arr[..., :3] = np.clip(rgb, 0, 255)
        arr[..., 3] = a
        small = S3.to_surface(arr)
        return pygame.transform.smoothscale(small, (w4 * q, h4 * q)), top

    def draw_ground(self, s, ox, oy):
        gy = self.sy(0) + oy
        if gy > H + 400:
            return
        night = self.night
        # uzak ufuk (paralaks): deniz ve dağlar daha yavaş kayar
        hy = GS - 70 + (self.cam * 0.55) + oy
        if hy < H + 50:
            sea = (14, 26, 52) if night else (46, 108, 160)
            pygame.draw.rect(s, sea, (0, hy, W, H))
            for i in range(10):
                yy = hy + 6 + i * 9
                pygame.draw.line(s, scale_color(sea, 1.25), (W * 0.55 + i * 30, yy), (W, yy), 1)
            mt = (22, 30, 50) if night else (96, 120, 140)
            pts = [(0, hy)] + [(i * 80, hy - 30 - 34 * (math.sin(i * 1.3) * 0.5 + 0.5)) for i in range(9)] + [(700, hy)]
            pygame.draw.polygon(s, mt, pts)
            if night:
                for i in range(40):
                    draw_glow(s, (40 + i * 16, hy - 4), 6, (255, 210, 140), 0.5)
        if gy > H + 300:
            return
        land = (28, 34, 30) if night else (92, 118, 72)
        pygame.draw.rect(s, land, (0, gy - 40, W, H))
        pygame.draw.rect(s, (36, 38, 44) if night else (128, 124, 116), (0, gy - 40, W, 14))         # yol
        for i in range(0, W, 60):
            pygame.draw.line(s, (220, 200, 90), (i + ox, gy - 33), (i + 30 + ox, gy - 33), 2)
        # ağaçlar
        for x, sc, sh in self.trees:
            if abs(x - W / 2) < 300:
                continue
            tx, ty = x + ox, gy - 42
            c = lerp_color((20, 52, 30), (40, 96, 50), sh) if not night else lerp_color((8, 20, 14), (16, 34, 22), sh)
            pygame.draw.line(s, (60, 42, 30), (tx, ty), (tx, ty - 14 * sc), 3)
            pygame.draw.circle(s, c, (int(tx), int(ty - 22 * sc)), int(12 * sc))
            pygame.draw.circle(s, scale_color(c, 1.25), (int(tx - 3 * sc), int(ty - 26 * sc)), int(6 * sc))
        # montaj binası (VAB) ve tabela
        g = self.game
        vb = pygame.Rect(70 + ox, gy - 300, 230, 260)
        pygame.draw.rect(s, (200, 204, 212) if not night else (70, 74, 86), vb)
        pygame.draw.rect(s, (120, 126, 140), vb, 2)
        pygame.draw.rect(s, (80, 86, 100), (vb.x + 60, vb.y + 60, 110, 200))
        for i in range(8):
            pygame.draw.line(s, (150, 156, 170), (vb.x + 60, vb.y + 60 + i * 25), (vb.x + 170, vb.y + 60 + i * 25), 1)
        pygame.draw.rect(s, g.color, (vb.x + 14, vb.y + 14, 60, 36))
        draw_text(s, g.name.upper(), (vb.x + 84, vb.y + 22), 15, (20, 26, 44) if not night else C["white"], bold=True,
                  raw=True, max_w=vb.w - 96, shadow=False)
        if night:
            for i in range(6):
                draw_glow(s, (vb.x + 20 + i * 38, vb.bottom - 8), 12, (255, 220, 160), 0.6)
        # su kulesi
        wt = (W - 260 + ox, gy - 40)
        for dx in (-22, 22):
            pygame.draw.line(s, (120, 124, 136), (wt[0] + dx, wt[1]), (wt[0] + dx * 0.4, wt[1] - 130), 3)
        pygame.draw.ellipse(s, (226, 228, 236) if not night else (90, 94, 108), (wt[0] - 40, wt[1] - 190, 80, 66))
        # paratoner direkleri ve teller
        masts = [W // 2 - 230, W // 2 + 230]
        for mx in masts:
            pygame.draw.line(s, (170, 170, 180), (mx + ox, gy - 40), (mx + ox, gy - 420), 4)
            if (self.t * 1.2 + mx) % 1 < 0.5:
                draw_glow(s, (mx + ox, gy - 420), 12, (255, 60, 60), 1.0)
        pygame.draw.line(s, (130, 130, 140), (masts[0] + ox, gy - 420), (masts[1] + ox, gy - 420), 1)
        # rampa platformu ve alev kanalı
        pad = pygame.Rect(W // 2 - 190 + ox, gy - 56, 380, 30)
        pygame.draw.rect(s, (110, 112, 120) if not night else (60, 62, 72), pad)
        pygame.draw.rect(s, (30, 30, 34), (W // 2 - 60 + ox, gy - 40, 120, 26))
        pygame.draw.polygon(s, (90, 92, 100), [(pad.x, pad.bottom), (pad.x - 50, gy - 26), (pad.right + 50, gy - 26),
                                               (pad.right, pad.bottom)])
        # servis kulesi (yerde kalır)
        bh = self.booster.get_height()
        th = bh + int(self.c_noz[1] * self.ck) + 40
        tx = W // 2 - self.booster.get_width() // 2 - 110 + ox
        tr = pygame.Rect(tx, gy - 56 - th, 64, th)
        pygame.draw.rect(s, (170, 60, 40) if not night else (110, 44, 34), tr)
        for yy in range(tr.y, tr.bottom, 28):
            pygame.draw.line(s, (110, 36, 26), (tr.x, yy), (tr.right, yy + 28), 3)
            pygame.draw.line(s, (110, 36, 26), (tr.right, yy), (tr.x, yy + 28), 3)
        arm_k = clamp((self.t - 3.0) / 1.2, 0, 1)
        for i in range(3):
            ay = gy - 56 - 100 - i * (th - 160) / 2
            reach = (self.booster.get_width() * 0.5 + 40) * (1 - ease_out_cubic(arm_k)) + 8
            pygame.draw.rect(s, (150, 150, 160), (tr.right, ay, reach, 9))
        if (self.t * 1.5) % 1 < 0.5:
            draw_glow(s, (tr.centerx, tr.y), 18, (255, 60, 60), 1.0)
        # projektörler
        for i, lx in enumerate((W // 2 - 330, W // 2 + 330)):
            pygame.draw.line(s, (90, 90, 100), (lx + ox, gy - 40), (lx + ox, gy - 110), 3)
            draw_glow(s, (lx + ox, gy - 112), 22, (255, 240, 200), 0.9)
            if night:
                beam = [(lx + ox, gy - 112), (W // 2 + ox - 40 + i * 80, gy - 56 - th), (W // 2 + ox + i * 80, gy - 56 - th)]
                bs = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.polygon(bs, (255, 240, 200, 26), beam)
                s.blit(bs, (0, 0))

    def draw_clouds(self, s, ox, oy, back):
        if self.night and self.alt < 200:
            return
        # tarayıcıda büyük yumuşak bulutlar yarı çözünürlüklü katmana çizilip büyütülür (alfa karıştırma pahalı)
        k = 0.5 if WEB else 1.0
        dst = s
        if WEB:
            lay = self.__dict__.get("_cloud_lay")
            if lay is None:
                lay = self._cloud_lay = pygame.Surface((W // 2, H // 2), pygame.SRCALPHA)
            lay.fill((0, 0, 0, 0))
            dst = lay
        used = False
        for i, (x, wy, r, a) in enumerate(self.clouds):
            if (i % 2 == 0) != back:
                continue
            y = self.sy(wy) + oy
            if -200 < y < H + 200:
                col = (222, 226, 232) if not self.night else (70, 80, 104)
                sp = soft_circle(int(r * k), col, int(200 * a))
                dst.blit(sp, ((x - r + ox) * k, (y - r) * k))
                dst.blit(soft_circle(int(r * 0.7 * k), col, int(200 * a)), ((x - r * 0.2 + ox) * k, (y - r * 0.9) * k))
                used = True
        if WEB and used:
            s.blit(pygame.transform.scale(dst, (W, H)), (0, 0))      # bulut zaten yumuşak: en yakın komşu yeterli

    def draw_rocket(self, s, ox, oy):
        x = W // 2 + ox
        wy = self.rocket_world()
        bw, bh = self.booster.get_size()
        cw, ch = self.craft.get_size()
        cy_b = self.sy(wy) + oy
        if self.fall:
            f = self.fall
            img = pygame.transform.rotate(self.booster, math.degrees(f[4]))
            fy = self.sy(f[1]) + oy
            if -400 < fy < H + 400:
                s.blit(img, (f[0] + ox - img.get_width() // 2, fy - img.get_height() // 2))
        for f in self.fairing:
            fy = self.sy(f[1]) + oy
            if -100 < fy < H + 100:
                w = max(4, int(20 * self.ck))
                hh = max(8, int(44 * self.ck))
                sh = pygame.Surface((w, hh), pygame.SRCALPHA)
                pygame.draw.polygon(sh, (236, 238, 244), [(0, hh), (w, hh), (w * 0.6, 0)] if f[2] > 0 else
                                    [(0, hh), (w, hh), (w * 0.4, 0)])
                img = pygame.transform.rotate(sh, math.degrees(f[4]))
                s.blit(img, (f[0] + ox - img.get_width() // 2, fy - img.get_height() // 2))
        if not self.separated:
            if self.ignited:
                art.draw_flame_core(s, x, cy_b + bh // 2 + 4, "solid", math.pi / 2, 1.3, 1.6, self.t)
                # şok elmasları (Mach diamonds)
                if self.lifted:
                    for i in range(4):
                        draw_glow(s, (x, cy_b + bh // 2 + 40 + i * 34), 13 - i * 2, (255, 250, 220), 0.9 - i * 0.18)
            s.blit(self.booster, (x - bw // 2, cy_b - bh // 2))
            s.blit(self.craft, (x - cw // 2, self.craft_top(cy_b)))
        else:
            top = self.craft_top(cy_b)
            ny = top + self.c_noz[1] * self.ck
            art.draw_flame_core(s, x, ny, self.eng, math.pi / 2, 1.0, 1.2, self.t)
            s.blit(self.craft, (x - cw // 2, top))

    def craft_top(self, cy_b):
        """Üst kademenin nozulu güçlendiricinin tepesine oturacak şekilde görüntü y'si."""
        return int(cy_b - self.booster.get_height() / 2 - self.c_noz[1] * self.ck + 2)

    def draw_hud(self, s):
        g = self.game
        t = self.t
        pl = D.PLANET[self.design["planet"]]
        draw_text(s, f"{g.name.upper()} GÖREV KONTROL", (40, 30), 22, C["white"], bold=True, glow=g.color)
        draw_text(s, f"{D.PAD_NAME[self.pad + 1]} · Hedef: {pl['name']} · {D.ROCKET_SIZE_NAME[self.size]} roket",
                  (40, 62), 16, C["white"])
        for i, (tt, line) in enumerate(CONTROL):
            if t >= tt and not self.lifted:
                draw_text(s, line, (40, 100 + i * 26), 16, C["cyan"], alpha=int(255 * clamp((t - tt) * 3, 0, 1)))
        n = self.count_shown
        if n is not None and (not self.lifted or (n == 0 and t < 6.2)):
            base = {3: 1.6, 2: 2.6, 1: 3.6, 0: 4.6}.get(n, 0)
            k = ease_out_back(clamp((t - base) * 2.5, 0, 1))
            txt = str(n) if n else "ATEŞLEME!"
            size = int((170 if n else 90) * k) + 10
            draw_text(s, txt, (W // 2, H // 2 - 160), size, C["white"] if n else C["orange"], bold=True, anchor="center",
                      glow=C["orange"], alpha=int(255 * clamp(1.4 - (t - base), 0, 1)))
        if self.lifted:
            r = pygame.Rect(W - 340, 26, 310, 184)
            pygame.draw.rect(s, (0, 0, 0), r, border_radius=14)
            pygame.draw.rect(s, C["orange"], r, 1, border_radius=14)
            km = self.alt * KM_PER_PX
            spd = real_speed(km)
            rows = [("İRTİFA", f"{km:.1f} km"), ("HIZ", f"{spd:,.0f} km/sa".replace(",", ".")),
                    ("KADEME", "2" if self.separated else "1"),
                    ("ATMOSFER", i18n.pct(100 * math.exp(-km / 8.5)))]
            for i, (a, b) in enumerate(rows):
                draw_text(s, a, (r.x + 18, r.y + 16 + i * 40), 15, C["white"], bold=True, max_w=150)
                draw_text(s, b, (r.right - 18, r.y + 12 + i * 40), 22, C["orange"] if i == 1 else C["white"], bold=True,
                          anchor="topright")
            draw_bar(s, (40, H - 40, 520, 8), clamp(self.alt / END_ALT, 0, 1), C["cyan"], label="YÖRÜNGEYE", size=13)
        else:
            draw_text(s, f"T-{max(0, 4.6 - t):04.1f}", (W - 40, 30), 36, C["orange"], bold=True, anchor="topright",
                      glow=C["orange"])
        if self.ev_t > 0 and self.ev_text:
            a = int(255 * clamp(self.ev_t / 0.5, 0, 1))
            br = pygame.Rect(0, 0, 640, 52)
            br.midtop = (W // 2, 120)
            pygame.draw.rect(s, (0, 0, 0), br, border_radius=12)
            pygame.draw.rect(s, C["cyan"], br, 1, border_radius=12)
            draw_text(s, self.ev_text, br.center, 20, C["white"], bold=True, anchor="center", alpha=a, max_w=br.w - 20)

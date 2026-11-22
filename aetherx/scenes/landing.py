# -*- coding: utf-8 -*-
"""
MOTORLU İNİŞ - MİNİ OYUN (yolculuktan sonra, yüzeye inen görevlerde)

Yan görünüşten iniş: aracı yerçekimine karşı motorla yavaşlat, eğerek yatay hızı öldür,
iniş alanına yumuşakça kon.
  W / ↑ / SPACE  : motor (basılı tut)
  A-D / ← →      : eğ (itki yönü)
  L              : NOVA iniş desteği (otomatik güdüm; tuşa basınca bırakır)
  N              : NOVA'ya sor      X : yörüngeye dön (iniş iptal)
  Fare / parmak  : ekrana basılı tut = motor, aracın soluna/sağına bas = o yöne eğ

Yerçekimleri gerçek (Ay 1,62 · Mars 3,71 · Venüs 8,87 m/s²). Başlangıç irtifası ve
yakıt bütçesi oyun ölçeğidir (gerçek inişler 15 km+ irtifadan başlar).
"""
import math
import random

import pygame

from . import Scene
from .. import art
from .. import data as D
from ..config import C, H, W
from ..fx import ParticleSystem, Shake, clamp, draw_glow, lerp, overlay, scale_color
from ..ui import UI, Button, chip, draw_bar, draw_icon, draw_text, glass_panel

# gök cismi: yerçekimi (gerçek), sürüklenme katsayısı (oyun: atmosfer yoğunluğuna göre), renkler
BODY = {
    "moon": {"g": 1.62, "drag": 0.0, "wind": 0.0, "sky": ((2, 3, 8), (6, 8, 16)), "ground": (128, 128, 134),
             "ground2": (70, 70, 78), "far": (54, 56, 64), "dust": (170, 168, 165), "stars": True,
             "note": "vakum: paraşüt yok, toz balistik uçar"},
    "mars": {"g": 3.71, "drag": 0.00025, "wind": 2.2, "sky": ((196, 140, 100), (120, 72, 52)), "ground": (176, 92, 56),
             "ground2": (112, 52, 32), "far": (150, 86, 62), "dust": (205, 140, 100), "stars": False,
             "note": "0,6 kPa CO₂: atmosfer çok ince, motor şart"},
    "venus": {"g": 8.87, "drag": 0.0040, "wind": 1.2, "sky": ((214, 160, 82), (120, 76, 34)), "ground": (96, 70, 48),
              "ground2": (56, 40, 30), "far": (150, 104, 60), "dust": (170, 120, 70), "stars": False,
              "note": "92 bar: kalın atmosfer düşüşü yavaşlatır"},
}
LANDABLE = set(BODY)
START_ALT = 1800.0
START_DX = -1500.0
SAFE_VY, SAFE_VX, SAFE_TILT = 2.6, 2.0, 10.0      # yumuşak temas sınırları
HARD_VY = 5.5


class Terrain:
    """1B yükseklik profili (m). x=0 iniş alanı; çevresi düzleştirilmiş."""

    def __init__(self, key, seed):
        rnd = random.Random(seed)
        self.x0, self.x1, self.step = -3600.0, 1600.0, 4.0
        n = int((self.x1 - self.x0) / self.step) + 1
        ph = [rnd.uniform(0, math.tau) for _ in range(6)]
        h = []
        for i in range(n):
            x = self.x0 + i * self.step
            if key == "mars":      # uzun kum tepeleri + kayalık sırtlar
                v = 34 * math.sin(x / 410 + ph[0]) + 14 * math.sin(x / 95 + ph[1]) + 5 * math.sin(x / 23 + ph[2])
            elif key == "venus":   # volkanik basamaklar
                v = 46 * math.sin(x / 520 + ph[0]) + 22 * abs(math.sin(x / 160 + ph[1])) + 6 * math.sin(x / 31 + ph[2])
            else:                  # Ay: yumuşak tepeler
                v = 28 * math.sin(x / 600 + ph[0]) + 10 * math.sin(x / 140 + ph[1]) + 3 * math.sin(x / 37 + ph[2])
            h.append(v)
        if key == "moon":          # kraterler (çanak + kenar)
            for _ in range(26):
                cx, r = rnd.uniform(self.x0, self.x1), rnd.uniform(20, 140)
                for i in range(n):
                    d = abs(self.x0 + i * self.step - cx) / r
                    if d < 1.0:
                        h[i] -= 0.22 * r * (1 - d * d)
                    elif d < 1.4:
                        h[i] += 0.06 * r * (1 - (d - 1) / 0.4)
        # iniş alanı: ±45 m düz, ±160 m'ye kadar yumuşak geçiş
        base = h[int((0 - self.x0) / self.step)]
        for i in range(n):
            x = abs(self.x0 + i * self.step)
            if x < 45:
                h[i] = 0.0
            elif x < 160:
                k = (x - 45) / 115
                k = k * k * (3 - 2 * k)
                h[i] = (h[i] - base) * k
            else:
                h[i] -= base
        self.h = h

    def at(self, x):
        f = (clamp(x, self.x0, self.x1) - self.x0) / self.step
        i = min(int(f), len(self.h) - 2)
        t = f - i
        return self.h[i] * (1 - t) + self.h[i + 1] * t

    def slope(self, x):
        return abs(self.at(x + 4) - self.at(x - 4)) / 8.0


class Lander:
    def __init__(self, g, thrust, budget):
        self.x, self.y = START_DX, START_ALT
        self.vx, self.vy = 58.0, -32.0
        self.ang = -8.0           # derece; + sağa eğik (itki +x)
        self.g = g
        self.tmax = thrust        # m/s² en çok itki ivmesi
        self.dv = budget          # kalan Δv (m/s) = yakıt
        self.dv0 = budget
        self.throttle = 0.0


class LandingScene(Scene):
    music = "space"
    ambient = "amb_space"
    show_topbar = False
    allow_events = False
    bloom_k = 0.35           # parlak Mars/Venüs göğünde parlama aracı ve zemini yıkamasın

    def __init__(self, app):
        super().__init__(app)
        self.ps = ParticleSystem(1800)
        self.shake = Shake()
        self.sky_cache = {}

    # ------------------------------------------------------------------ giriş
    def enter(self, **kw):
        m = getattr(self.app, "mission", None)
        if not m or "result" not in m:
            self.app.go("base")
            return
        self.res = m["result"]
        self.design = m["design"]
        self.key = self.res["planet"]
        self.pl = D.PLANET[self.key]
        self.b = BODY[self.key]
        g = self.game
        self.terrain = Terrain(self.key, sum(map(ord, self.key + g.name)))
        eng = D.PART["engine"][self.design["engine"]]
        self.eng_key = self.design["engine"]
        # itki: aracın gerçek ağırlığından bağımsız oyun ölçeği; her gök cisminde yerçekiminin ~2,6 katı
        thrust = max(6.0, 2.6 * self.b["g"])
        frac = clamp(self.res.get("fuel_left", 0) / max(1.0, self.res.get("fuel_max", 1.0)), 0.0, 1.0) \
            if self.res.get("fuel_max") else 0.6
        if eng.get("burn", 1) == 0:
            frac = 0.6        # elektrikli itki: iniş için kimyasal iniş kademesi varsayılır
        self.L = Lander(self.b["g"], thrust, self.plan_budget(thrust) * (1.2 + 0.6 * frac))
        craft, nozzle = art.render_spacecraft(self.design["hull"], self.design["engine"], self.design["power"],
                                              self.design["antenna"], self.design["payloads"], g.name, g.color, 0.42)
        self.craft = craft
        cw, ch = craft.get_size()
        self.noz = (nozzle[0] - cw / 2, nozzle[1] - ch / 2)
        self.colony = bool(g.colony(self.key))
        self.assist = False
        self.state = "fly"        # fly | landed | crashed | aborted
        self.end_t = 0.0
        self.verdict = None
        self.scale = 0.2
        self.cam = [self.L.x, self.L.y]
        self.callouts = {1000: False, 500: False, 200: False, 100: False, 30: False, 10: False}
        self.warn_t = 0.0
        self._eng_on = False
        self._eng_vol = 0.0
        self.warn = False
        self.hard = False
        self.landed_pad = False
        self._done = False
        self.flash = 0.0
        self.ps.clear()
        self.far = self._far_hills()
        self.widgets = []
        y = H - 74
        self.btn_assist = self.add(Button((24, y, 230, 54), "İNİŞ DESTEĞİ", self.toggle_assist, accent=C["cyan"],
                                          icon="nova", size=15, hotkey=pygame.K_l,
                                          tooltip="NOVA güdümü alır; motor/eğme tuşuna basınca sana bırakır (L)"))
        self.add(Button((264, y, 190, 54), "NOVA'YA SOR", self.ask_nova, accent=C["cyan"], icon="nova", size=15,
                        hotkey=pygame.K_n))
        self.btn_abort = self.add(Button((W - 254, y, 230, 54), "YÖRÜNGEYE DÖN", self.abort, accent=C["red"],
                                         icon="warning", size=14, hotkey=pygame.K_x,
                                         tooltip="İnişi iptal et: veriler korunur, yüzey madenciliği olmaz (X)"))
        self.btn_go = Button((W // 2 - 150, H // 2 + 120, 300, 58), "DEVAM", self.finish, accent=C["green"], size=18,
                             style="big", hotkey=pygame.K_RETURN)
        place = "koloninin iniş alanına" if self.colony else "işaretli iniş alanına"
        self.app.say(f"{g.name}, {self.pl['name']} yüzeyine iniyoruz. Hedef {place}. Motor W ya da SPACE, "
                     f"eğmek için A-D. İstersen L ile iniş desteğini açarım.", "calm")

    def _far_hills(self):
        rnd = random.Random(self.key)
        ph = [rnd.uniform(0, math.tau) for _ in range(3)]
        return [0.5 + 0.3 * math.sin(i / 9 + ph[0]) + 0.15 * math.sin(i / 3.3 + ph[1]) + 0.05 * math.sin(i * 1.7 + ph[2])
                for i in range((W + 40) // 20 + 1)]

    # --------------------------------------------------------------- eylemler
    def toggle_assist(self):
        if self.state != "fly":
            return
        self.assist = not self.assist
        self.app.audio.play("beep" if self.assist else "tick")
        self.app.toast("NOVA iniş desteği AÇIK" if self.assist else "Kumanda sende", "cyan", "nova")

    def abort(self):
        if self.state != "fly":
            return
        self.state = "aborted"
        self.verdict = ("İNİŞ İPTAL", "Araç yörüngeye döndü. Veriler korundu, yüzeye inilmedi.", C["orange"])
        self.end_t = 0.0
        self.app.audio.play("whoosh")

    def ask_nova(self):
        L = self.L
        alt = L.y - self.terrain.at(L.x)
        net = L.tmax - L.g
        stop = (L.vy * L.vy) / (2 * max(0.1, net)) if L.vy < 0 else 0
        if self.state != "fly":
            return
        if L.dv < L.dv0 * 0.15:
            self.app.say("Yakıt kritik. Yatay hızı bırak, yalnız düşüşü durdur ve dik kon.", "alert")
        elif abs(L.vx) > 12 and alt < 300:
            d = "sola" if L.vx > 0 else "sağa"
            self.app.say(f"Yatay hız {abs(L.vx):.0f} m/s, yere yakınız. Aracı {d} eğip motoru yak.", "alert")
        elif L.vy < 0 and stop > alt * 0.8:
            self.app.say(f"Durma mesafen {stop:.0f} m, irtifa {alt:.0f} m. Motoru şimdi yak!", "alert")
        else:
            dist = abs(L.x)
            self.app.say(f"İrtifa {alt:.0f} m, hedefe {dist:.0f} m. Yumuşak temas için dikey hız "
                         f"{SAFE_VY:.1f} m/s'nin altında, araç dik olmalı. Yerçekimi {self.b['g']:.2f} m/s².")

    # ------------------------------------------------------------------- olay
    def handle(self, e):
        if self.state != "fly":
            if self.end_t > 1.0 and self.btn_go.handle(e):
                return True
            return True
        return super().handle(e)

    # --------------------------------------------------------------- güncelle
    def update(self, dt):
        super().update(dt)
        self.btn_go.update(dt)
        self.update_camera(dt)
        self.shake.update(dt)
        self.ps.update(dt, wind=self.b["wind"] * 4)
        self.flash = max(0.0, self.flash - dt * 1.6)
        if self.state != "fly":
            self.end_t += dt
            return
        L = self.L
        dt = min(dt, 1 / 30)
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        over_ui = UI.mouse[1] > H - 90
        thr_in = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE] or (mouse[0] and not over_ui)
        rot_in = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        if self.assist and (thr_in or rot_in):
            self.assist = False
            self.app.toast("Kumanda sende", "cyan", "nova")
        if self.assist:
            thr, ang = self.guidance()
            L.ang += clamp(ang - L.ang, -60 * dt, 60 * dt)
            L.throttle = thr
        else:
            if mouse[0] and not over_ui and not rot_in:       # dokunmatik: basılan yana eğ
                sx, _ = self.to_screen(L.x, L.y)
                target = clamp((UI.mouse[0] - sx) / 260 * 40, -40, 40)
                L.ang += clamp(target - L.ang, -55 * dt, 55 * dt)
            L.ang = clamp(L.ang + rot_in * 55 * dt, -60, 60)
            L.throttle = 1.0 if thr_in else 0.0
        if L.dv <= 0:
            L.throttle = 0.0
        # fizik
        a = L.throttle * L.tmax
        rad = math.radians(L.ang)
        ax, ay = math.sin(rad) * a, math.cos(rad) * a - L.g
        v = math.hypot(L.vx, L.vy)
        if self.b["drag"] and v > 0:
            ax -= self.b["drag"] * v * L.vx
            ay -= self.b["drag"] * v * L.vy
        if self.b["wind"]:
            ax += math.sin(self.t * 0.7) * self.b["wind"] * 0.25
        L.vx += ax * dt
        L.vy += ay * dt
        L.x += L.vx * dt
        L.y += L.vy * dt
        L.dv = max(0.0, L.dv - a * dt)
        ground = self.terrain.at(L.x)
        alt = L.y - ground
        # efektler
        # motor sesi: sürekli döngü, şiddeti itkiyle (eskiden 0,09 sn'de bir "vuruş" efekti çatırtı yapıyordu).
        # Ay'da dışarıda ses yoktur; duyulan, araç gövdesinden kabine iletilen uğultudur.
        self.engine_sound(L.throttle)
        if L.throttle > 0:
            if alt < 45:
                k = 1 - alt / 45
                gx, gy = self.to_screen(L.x, ground)
                for side in (-1, 1):
                    self.ps.smoke(gx + side * 10, gy - 2, n=1 + int(2 * k), angle=math.pi if side < 0 else 0.0,
                                  spread=0.25, speed=(80 * k + 40, 260 * k + 60), size=(8, 18), life=(0.8, 1.8),
                                  color=self.b["dust"], alpha=int(120 * k + 40), grow=30,
                                  grav=0 if self.key == "moon" else -6)
        self.callout(alt)
        if alt <= 0:
            self.touchdown(ground)

    def update_camera(self, dt):
        """İrtifa azaldıkça yaklaş; araç ile zemin arası ekrana sığsın (kare hızından bağımsız yumuşatma)."""
        L = self.L
        ground = self.terrain.at(L.x)
        alt = max(0.0, L.y - ground)
        want = clamp(420 / (alt + 70), 0.2, 3.4)
        self.scale = lerp(self.scale, want, 1 - math.exp(-dt * 3.5))
        self.cam[0] = lerp(self.cam[0], L.x, 1 - math.exp(-dt * 12))
        self.cam[1] = lerp(self.cam[1], (L.y + ground) / 2 + 6, 1 - math.exp(-dt * 12))

    def engine_sound(self, thr):
        au = self.app.audio
        if not au or not getattr(au, "ok", False):
            return
        if thr > 0.02 and not self._eng_on:
            au.loop("engine", 0.0, fade=250)
            self._eng_on = True
            cae = getattr(self.app, "cae", None)
            if cae and cae.bus:
                cae.bus.publish("EngineStart", planet=self.key)
        if self._eng_on:
            k = getattr(self, "_eng_vol", 0.0)
            k += (thr * 0.75 - k) * 0.15
            self._eng_vol = k
            try:
                au.loop_ch.set_volume(k * au.sfx_vol)
            except Exception:
                pass
            if thr <= 0.02 and k < 0.02:
                au.stop_loop(300)
                self._eng_on = False

    def guidance(self, L=None):
        """NOVA iniş desteği: iniş alanına frenleme profiliyle yaklaş (vx² = 2·a·mesafe), yatay hız
        sönmeden alçalma; son 15 m'de araç dik, dikey hız 1,2 m/s."""
        L = L or self.L
        alt = L.y - self.terrain.at(L.x)
        d = abs(L.x)
        a_h = 0.3 * L.tmax
        vx_des = -math.copysign(min(40.0, math.sqrt(2 * a_h * d)), L.x) if d > 6 else -L.x * 0.25
        vy_des = -clamp(0.09 * alt + 1.2, 1.2, 38)
        if d > 25 and alt < 160:
            vy_des = max(vy_des, -0.4 if alt > 40 else 0.4)      # hedefe varmadan yere yaklaşma
        ax = (vx_des - L.vx) * 0.9
        ay = (vy_des - L.vy) * 1.2 + L.g
        v = math.hypot(L.vx, L.vy)
        if self.b["drag"]:
            ax += self.b["drag"] * v * L.vx
            ay += self.b["drag"] * v * L.vy
        ay = max(ay, 0.05)
        lim = 6 if alt < 12 else 45
        ang = clamp(math.degrees(math.atan2(ax, ay)), -lim, lim)
        thr = clamp(math.hypot(ax, ay) / L.tmax, 0.0, 1.0)
        return thr, ang

    def plan_budget(self, thrust):
        """Yakıt bütçesi: NOVA güdümünün bu arazide harcayacağı Δv önceden benzetilir; oyuncunun payı
        yolculuktan kalan yakıta göre eklenir (manuel iniş biraz daha cömert yakıt ister)."""
        L = Lander(self.b["g"], thrust, 1e9)
        used, dt = 0.0, 1 / 30
        for _ in range(30 * 400):
            thr, ang = self.guidance(L)
            L.ang += clamp(ang - L.ang, -60 * dt, 60 * dt)
            a = thr * L.tmax
            rad = math.radians(L.ang)
            ax, ay = math.sin(rad) * a, math.cos(rad) * a - L.g
            v = math.hypot(L.vx, L.vy)
            if self.b["drag"] and v > 0:
                ax -= self.b["drag"] * v * L.vx
                ay -= self.b["drag"] * v * L.vy
            L.vx += ax * dt
            L.vy += ay * dt
            L.x += L.vx * dt
            L.y += L.vy * dt
            used += a * dt
            if L.y <= self.terrain.at(L.x):
                break
        return used

    def callout(self, alt):
        for h in sorted(self.callouts, reverse=True):
            if not self.callouts[h] and alt < h:
                self.callouts[h] = True
                if h <= 30:
                    self.app.say(f"{h} metre. Dikey hız {abs(self.L.vy):.1f} m/s.", "calm", priority=True)
                else:
                    self.app.audio.play("ping", 0.4)
        # düşüş çok hızlı uyarısı
        L = self.L
        net = L.tmax - L.g
        self.warn = L.vy < 0 and (L.vy * L.vy) / (2 * max(0.1, net)) > alt * 0.85 and alt < 900
        self.warn_t = self.warn_t + 1 if self.warn else 0

    def touchdown(self, ground):
        L = self.L
        L.y = ground
        tilt = abs(L.ang)
        slope = self.terrain.slope(L.x)
        vy, vx = abs(L.vy), abs(L.vx)
        on_pad = abs(L.x) < 45
        self.contact = (vy, vx, tilt, abs(L.x))
        if vy <= SAFE_VY and vx <= SAFE_VX and tilt <= SAFE_TILT and slope < 0.2:
            self.state = "landed"
            prec = "iniş alanının tam ortasına" if abs(L.x) < 12 else ("iniş alanına" if on_pad else "alan dışına")
            self.verdict = ("YUMUŞAK İNİŞ", f"Temas {vy:.1f} m/s · yatay {vx:.1f} m/s · {prec} ({abs(L.x):.0f} m)",
                            C["green"])
            self.app.audio.play("success")
        elif vy <= HARD_VY and tilt <= 22 and slope < 0.35:
            self.state = "landed"
            self.hard = True
            self.verdict = ("SERT İNİŞ", f"Temas {vy:.1f} m/s, eğim {tilt:.0f}°. Araç ayakta ama gövde hasar aldı.",
                            C["orange"])
            self.app.audio.play("clunk")
            self.shake.add(10)
        else:
            self.state = "crashed"
            why = "çok hızlı" if vy > HARD_VY else ("çok eğik" if tilt > 22 else "zemin çok engebeli")
            self.verdict = ("İNİŞ BAŞARISIZ", f"Temas {vy:.1f} m/s, eğim {tilt:.0f}° — {why}. Mürettebat acil "
                                              f"kalkış kademesiyle yörüngeye döndü.", C["red"])
            sx, sy = self.to_screen(L.x, L.y)
            self.ps.sparks(sx, sy, 60)
            self.ps.shards(sx, sy, 24, self.b["ground2"])
            self.shake.add(26)
            self.flash = 1.0
            self.app.audio.play("explosion")
        self.landed_pad = on_pad
        self.end_t = 0.0
        L.vx = L.vy = 0.0
        L.throttle = 0.0
        if self.app.audio and getattr(self.app.audio, "ok", False):
            self.app.audio.stop_loop(400)
        self._eng_on = False
        cae = getattr(self.app, "cae", None)
        if cae and cae.bus and self.state == "landed":
            cae.bus.publish("PlanetLanding", planet=self.key, soft=not getattr(self, "hard", False))

    def finish(self):
        """Sonucu görev sonucuna işler ve sonuç ekranına geçer."""
        if getattr(self, "_done", False):
            return
        self._done = True
        res = self.res
        mk = self.pl["mineral"]
        if self.state == "landed":
            res["landed"] = True
            cargo = D.PART["hull"][self.design["hull"]].get("cargo", 8)
            if getattr(self, "landed_pad", False) and not getattr(self, "hard", False):
                bonus = max(2, int(cargo * 0.25))
                res["minerals"][mk] = res["minerals"].get(mk, 0) + bonus
                res["landing_bonus"] = bonus
                self.app.toast(f"Hassas iniş ödülü: +{bonus} {D.MINERAL[mk]['name']}",
                               "gold", "star")
            if getattr(self, "hard", False):
                res["damage"] = res.get("damage", 0) + 1
        else:
            res["landed"] = False
            if self.state == "crashed":
                res["damage"] = res.get("damage", 0) + 2
            if res["outcome"] == "success":
                res["outcome"] = "partial"
            why = "İniş iptal edildi" if self.state == "aborted" else "İniş başarısız: acil kalkışla yörüngeye dönüldü"
            res["reason"] = why if res.get("reason") in (None, "", "Hedefe ulaşıldı") else res["reason"] + "; " + why
        res["touchdown"] = getattr(self, "contact", None)
        self.app.go("results")

    def exit(self):
        if self.app.audio and getattr(self.app.audio, "ok", False):
            self.app.audio.stop_loop(300)
        self._eng_on = False
        self._done = False
        self.hard = False
        self.landed_pad = False

    # -------------------------------------------------------------------- çizim
    def to_screen(self, x, y):
        return (W * 0.5 + (x - self.cam[0]) * self.scale, H * 0.56 - (y - self.cam[1]) * self.scale)

    def sky(self):
        img = self.sky_cache.get(self.key)
        if img is None:
            img = pygame.Surface((W, H))
            top, bot = self.b["sky"]
            for yy in range(H):
                k = yy / H
                img.fill(tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)), (0, yy, W, 1))
            if self.b["stars"]:
                rnd = random.Random(3)
                for _ in range(420):
                    c = rnd.randint(90, 235)
                    img.set_at((rnd.randrange(W), rnd.randrange(int(H * 0.8))), (c, c, min(255, c + 12)))
            self.sky_cache[self.key] = img
        return img

    def draw(self, surf):
        L = self.L
        ground = self.terrain.at(L.x)
        alt = max(0.0, L.y - ground)
        ox, oy = self.shake.offset(16)
        surf.blit(self.sky(), (0, 0))
        # gökte: Ay'dan Dünya, diğerlerinde güneş halesi
        if self.key == "moon":
            art.draw_planet(surf, "earth", (W - 260, 150), 46)
        else:
            draw_glow(surf, (W - 300, 130), 180, (255, 236, 200) if self.key == "mars" else (255, 220, 150), 0.35)
        # uzak tepeler (paralaks)
        far = self.b["far"]
        base_y = self.to_screen(0, self.terrain.at(L.x))[1]
        hy = clamp(base_y - 60, H * 0.35, H + 40)
        pts = [(0, H)]
        for i, v in enumerate(self.far):
            x = i * 20 - (self.cam[0] * 0.02) % 20
            pts.append((x, hy - 20 - v * 60))
        pts.append((W, H))
        pygame.draw.polygon(surf, far, pts)
        if self.key != "moon":
            overlay(surf, self.b["sky"][1] + (40,))
        # zemin
        x_left = self.cam[0] - (W * 0.5 + 20) / self.scale
        x_right = self.cam[0] + (W * 0.5 + 20) / self.scale
        step = max(2.0, 3.0 / self.scale)
        pts = []
        x = x_left
        while x <= x_right:
            sx, sy = self.to_screen(x, self.terrain.at(x))
            pts.append((sx + ox, sy + oy))
            x += step
        if pts:
            poly = pts + [(W + 40, H + 40), (-40, H + 40)]
            pygame.draw.polygon(surf, self.b["ground2"], poly)
            pygame.draw.lines(surf, self.b["ground"], False, pts, max(2, int(3 * min(1.5, self.scale))))
            # yüzey dokusu: yakında taşlar
            if self.scale > 1.2:
                rnd = random.Random(int(x_left / 6))
                xx = math.floor(x_left / 6) * 6
                while xx < x_right:
                    r = random.Random(int(xx * 13.7)).random()
                    if r > 0.82:
                        sx, sy = self.to_screen(xx, self.terrain.at(xx))
                        pygame.draw.circle(surf, scale_color(self.b["ground"], 0.8), (int(sx + ox), int(sy + oy + 2)),
                                           max(1, int(self.scale * (0.3 + r * 0.6))))
                    xx += 6
        self.draw_pad(surf, ox, oy)
        # araç
        sx, sy = self.to_screen(L.x, L.y)
        sx += ox
        sy += oy
        size = max(46, 9 * self.scale)
        k = size / self.craft.get_height()
        img = pygame.transform.rotozoom(self.craft, -L.ang, k)
        rad = math.radians(L.ang)
        cy = sy - size * 0.5 * math.cos(rad)
        cx = sx + size * 0.5 * math.sin(rad)
        if self.state not in ("crashed", "aborted"):
            nx = cx + (self.noz[0] * math.cos(rad) - self.noz[1] * math.sin(rad)) * k
            ny = cy + (self.noz[0] * math.sin(rad) + self.noz[1] * math.cos(rad)) * k
            if L.throttle > 0:
                art.draw_flame_core(surf, nx, ny, self.eng_key, math.pi / 2 + rad, L.throttle * 0.9,
                                    0.55 * k / 0.42 + 0.25, self.t)
                draw_glow(surf, (int(nx), int(ny + 10)), 40, (255, 190, 120), 0.35 * L.throttle)
            surf.blit(img, (cx - img.get_width() / 2, cy - img.get_height() / 2))
            # iniş bacakları
            for s in (-1, 1):
                fx = sx + s * size * 0.42 * math.cos(rad)
                fy = sy + s * size * 0.42 * math.sin(rad)
                hx = cx + s * size * 0.16 * math.cos(rad)
                hy2 = cy + s * size * 0.16 * math.sin(rad) + size * 0.2
                pygame.draw.line(surf, (200, 204, 214), (hx, hy2), (fx, fy), max(2, int(size / 26)))
                pygame.draw.line(surf, (200, 204, 214), (fx - 6, fy), (fx + 6, fy), max(2, int(size / 26)))
        self.ps.draw(surf)
        if self.flash > 0:
            overlay(surf, (255, 240, 220, int(200 * self.flash)))
        self.draw_hud(surf, alt)
        self.draw_widgets(surf)
        if self.state != "fly":
            self.draw_end(surf)

    def draw_pad(self, surf, ox, oy):
        y = self.terrain.at(0)
        lx, ly = self.to_screen(-45, y)
        rx, _ = self.to_screen(45, y)
        pygame.draw.line(surf, (70, 72, 78), (lx + ox, ly + oy + 2), (rx + ox, ly + oy + 2), max(3, int(self.scale * 1.2)))
        blink = int(self.t * 2) % 2 == 0
        for px in (-45, 45):
            sx, sy = self.to_screen(px, y)
            col = C["green"] if self.colony else C["orange"]
            pygame.draw.line(surf, (160, 160, 170), (sx + ox, sy + oy), (sx + ox, sy + oy - max(8, 4 * self.scale)), 2)
            if blink:
                draw_glow(surf, (int(sx + ox), int(sy + oy - max(8, 4 * self.scale))), 14, col, 0.9)
        if self.colony:   # koloni kubbeleri iniş alanının yanında
            for i, (dx, r) in enumerate(((-130, 20), (-180, 14), (110, 24), (160, 12))):
                sx, sy = self.to_screen(dx, self.terrain.at(dx))
                rr = max(4, int(r * self.scale))
                pygame.draw.circle(surf, (150, 170, 190), (int(sx + ox), int(sy + oy)), rr, draw_top_right=True,
                                   draw_top_left=True)
                pygame.draw.circle(surf, (210, 230, 250), (int(sx + ox), int(sy + oy)), rr, 2, draw_top_right=True,
                                   draw_top_left=True)
                if self.scale > 0.6:
                    draw_glow(surf, (int(sx + ox), int(sy + oy - rr * 0.4)), rr * 0.8, (255, 210, 150), 0.25)
        cx, cy = self.to_screen(0, y)
        if self.scale < 1.6:
            draw_text(surf, "KOLONİ İNİŞ ALANI" if self.colony else "İNİŞ ALANI", (cx + ox, cy + oy - 36), 13,
                      C["green"] if self.colony else C["orange"], bold=True, anchor="midbottom")

    def draw_hud(self, surf, alt):
        L = self.L
        title = f"MOTORLU İNİŞ · {self.pl['name'].upper()}"
        draw_text(surf, title, (W // 2, 22), 26, C["text"], bold=True, anchor="midtop", glow=scale_color(C["cyan"], 0.5))
        chip(surf, (W // 2, 62), f"yerçekimi {self.b['g']:.2f} m/s² (gerçek) · {self.b['note']}", C["cyan"], 12,
             anchor="midtop")
        # sol panel: göstergeler
        r = pygame.Rect(20, 20, 330, 300)
        glass_panel(surf, r, C["cyan"], 175, 14)
        fly = self.state == "fly"
        rows = [
            ("İRTİFA", f"{alt:,.0f} m".replace(",", "."), C["text"] if alt > 50 else C["gold"]),
            ("DİKEY HIZ", f"{L.vy:+.1f} m/s", C["red"] if fly and ((L.vy < -SAFE_VY and alt < 40) or self.warn) else C["text"]),
            ("YATAY HIZ", f"{L.vx:+.1f} m/s", C["red"] if fly and abs(L.vx) > SAFE_VX and alt < 40 else C["text"]),
            ("EĞİM", f"{L.ang:+.0f}°", C["red"] if abs(L.ang) > SAFE_TILT and alt < 30 else C["text"]),
            ("HEDEFE", f"{abs(L.x):,.0f} m {'←' if L.x > 0 else '→'}".replace(",", "."),
             C["green"] if abs(L.x) < 45 else C["text"]),
        ]
        y = r.y + 16
        for k, v, col in rows:
            draw_text(surf, k, (r.x + 18, y + 4), 13, C["text_dim"], bold=True)
            draw_text(surf, v, (r.right - 18, y), 22, col, bold=True, anchor="topright", raw=True)
            y += 38
        draw_bar(surf, (r.x + 40, y + 14, r.w - 60, 12), L.dv / max(1, L.dv0), C["orange"], label="YAKIT (Δv)",
                 value=f"{L.dv:.0f} m/s", icon="fuel", warn_below=0.2)
        # sağ: dikey hız şeridi (güvenli bant yeşil)
        tr = pygame.Rect(W - 150, 110, 120, 420)
        glass_panel(surf, tr, C["gold"], 170, 14)
        draw_text(surf, "DÜŞÜŞ", (tr.centerx, tr.y + 10), 13, C["text_dim"], bold=True, anchor="midtop")
        top, bot = tr.y + 40, tr.bottom - 40
        span = 40.0
        def vy_y(v):
            return top + (bot - top) * (clamp(-v, -5, span) + 5) / (span + 5)
        pygame.draw.rect(surf, scale_color(C["green"], 0.35), (tr.x + 30, vy_y(0), 30, vy_y(-SAFE_VY) - vy_y(0)))
        pygame.draw.rect(surf, scale_color(C["orange"], 0.3), (tr.x + 30, vy_y(-SAFE_VY), 30, vy_y(-HARD_VY) - vy_y(-SAFE_VY)))
        pygame.draw.rect(surf, (60, 70, 90), (tr.x + 30, top, 30, bot - top), 1)
        for v in (0, 10, 20, 30, 40):
            yy = vy_y(-v)
            pygame.draw.line(surf, (90, 100, 120), (tr.x + 62, yy), (tr.x + 70, yy), 1)
            draw_text(surf, str(v), (tr.x + 74, yy - 8), 12, C["text_dim"], raw=True)
        yy = vy_y(L.vy)
        col = C["green"] if -L.vy <= SAFE_VY else C["orange"] if -L.vy <= HARD_VY else C["red"]
        pygame.draw.polygon(surf, col, [(tr.x + 24, yy), (tr.x + 12, yy - 8), (tr.x + 12, yy + 8)])
        draw_text(surf, "m/s", (tr.centerx, bot + 10), 12, C["text_dim"], anchor="midtop")
        # destek durumu ve uyarılar
        st = "NOVA DESTEĞİ AÇIK" if self.assist else "MANUEL"
        chip(surf, (W // 2, 96), st, C["cyan"] if self.assist else C["text_dim"], 13, anchor="midtop", icon="nova")
        if self.state == "fly" and self.warn and int(self.t * 5) % 2 == 0:
            draw_text(surf, "MOTORU YAK — DÜŞÜŞ ÇOK HIZLI", (W // 2, 140), 24, C["red"], bold=True, anchor="midtop",
                      glow=scale_color(C["red"], 0.6))
        if self.state == "fly" and L.dv <= 0:
            draw_text(surf, "YAKIT BİTTİ", (W // 2, 176), 22, C["orange"], bold=True, anchor="midtop")
        if self.state == "fly" and alt < 60 and abs(L.ang) > SAFE_TILT:
            draw_text(surf, "ARACI DÜZELT", (W // 2, 176), 20, C["gold"], bold=True, anchor="midtop")

    def draw_end(self, surf):
        k = clamp(self.end_t / 0.6, 0, 1)
        overlay(surf, (4, 6, 14, int(140 * k)))
        title, text, col = self.verdict
        r = pygame.Rect(W // 2 - 380, H // 2 - 130, 760, 300)
        glass_panel(surf, r, col, int(220 * k), 18)
        draw_icon(surf, "check" if col == C["green"] else "warning", (r.centerx, r.y + 46), 38, col)
        draw_text(surf, title, (r.centerx, r.y + 78), 34, col, bold=True, anchor="midtop", glow=scale_color(col, 0.5))
        draw_text(surf, text, (r.centerx, r.y + 132), 16, C["text"], anchor="midtop", max_w=r.w - 60)
        if self.state == "landed" and getattr(self, "landed_pad", False) and not getattr(self, "hard", False):
            draw_text(surf, "Hassas iniş: yüzey madenciliğine ek kargo", (r.centerx, r.y + 166), 15, C["gold"],
                      anchor="midtop")
        if self.end_t > 1.0:
            self.btn_go.draw(surf)

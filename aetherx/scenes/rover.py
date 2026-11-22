# -*- coding: utf-8 -*-
"""
ROVER — GERÇEKÇİ GEZEGEN ARACI SÜRÜŞÜ (ana oyunun içinde 3B)

Akış: gezegen (Ay / Mars / Titan) -> araç -> görev -> sürüş.
Kontroller (değiştirilebilir): W ileri · S geri/fren · A-D direksiyon · SPACE el freni · SHIFT hız modu ·
C kamera · F araca bin/in · L farlar · R kurtar · P otopilot · E numune. Dokunmatik: direksiyon + pedallar.
Kameralar: takip, kokpit, ön (tampon), serbest (fareyle döndür, tekerlekle yakınlaş).
"""
import math
import random
from collections import deque

import numpy as np
import pygame

from . import Scene
from .. import art
from .. import i18n
from ..config import C, H, W
from ..fx import clamp, draw_glow, scale_color
from ..i18n import tr
from ..ui import Button, draw_bar, draw_paragraph, draw_text, glass_panel
from ..vehicles import CATALOG, Controls, Rover, Terrain, VEHICLES_FOR
from ..vehicles import missions as MS
from ..vehicles.controls import ACTION_LABEL, KeyMap, TouchControls
from ..vehicles.planets import PLANETS, SURFACES
from ..vehicles.render3d import Camera, TerrainRenderer, VehicleModel

CAMS = ("takip", "kokpit", "ön", "serbest")
RES = {"low": (320, 180, 110, 380), "medium": (400, 225, 150, 460), "high": (480, 270, 200, 560), "ultra": (640, 360, 260, 700)}


def n_(v, d=0):
    return i18n.num(v, d)


class RoverScene(Scene):
    title = "ROVER"
    title_icon = "rocket"
    music = None
    ambient = None
    accent = C["orange"]
    show_topbar = False
    bloom_k = 0.4

    def __init__(self, app):
        super().__init__(app)
        self.ensure_bg("ember", 63, 1.0)
        self.keys = KeyMap(i18n.PREFS)
        self.touch = TouchControls(W, H)
        self.stage = "setup"
        self.planet = "moon"
        self.vkey = "lrv"
        self.mkey = "kesif"
        self.terrains = {}
        self.cam_i = 0
        self.rebind = None

    # ---------------------------------------------------------------- kurulum
    def enter(self, **kw):
        self.stage = "setup"
        self.rebuild()

    def exit(self):
        au = self.app.audio
        if au and getattr(au, "ok", False):
            au.stop_loop(300)

    def rebuild(self):
        self.widgets = []
        if self.stage == "setup":
            y = 210
            for i, p in enumerate(("moon", "mars", "titan")):
                b = self.add(Button((80 + i * 230, y, 220, 54), PLANETS[p]["name"], (lambda p=p: self.pick_planet(p)),
                                    accent=C["orange"], size=17, style="tab"))
                b.selected = p == self.planet
            y = 330
            for i, k in enumerate(VEHICLES_FOR[self.planet]):
                b = self.add(Button((80, y + i * 64, 700, 56), CATALOG[k].name, (lambda k=k: self.pick_vehicle(k)),
                                    accent=C["cyan"], size=15, style="tab"))
                b.selected = k == self.vkey
            ms = MS.build(self.planet, self.terrain(self.planet))
            for i, m in enumerate(ms):
                b = self.add(Button((840 + (i % 2) * 360, 210 + (i // 2) * 64, 350, 56), m.title, (lambda k=m.key: self.pick_mission(k)),
                                    accent=C["gold"], size=13, style="tab"))
                b.selected = m.key == self.mkey
            self.add(Button((W // 2 - 200, H - 120, 400, 64), "SÜRÜŞE BAŞLA", self.start, accent=C["green"], icon="play", size=20,
                            style="big", hotkey=pygame.K_RETURN))
            self.add(Button((W - 330, H - 120, 260, 56), "KONTROLLER", self.open_rebind, accent=C["violet"], size=15))
            self.back_button()
        elif self.stage == "pause":
            self.add(Button((W // 2 - 180, H // 2 - 80, 360, 56), "DEVAM ET", self.resume, accent=C["green"], size=18, style="big"))
            self.add(Button((W // 2 - 180, H // 2 - 10, 360, 50), "KONTROLLER", self.open_rebind, accent=C["violet"], size=15))
            self.add(Button((W // 2 - 180, H // 2 + 50, 360, 50), "GÖREVİ BIRAK", self.to_setup, accent=C["red"], size=15))
        elif self.stage == "rebind":
            for i, a in enumerate(self.keys.keys):
                self.add(Button((W // 2 - 360 + (i % 2) * 370, 200 + (i // 2) * 62, 350, 52),
                                f"{tr(ACTION_LABEL[a])}   [{self.keys.keys[a].upper()}]", (lambda a=a: self.wait_key(a)),
                                accent=C["cyan"] if self.rebind != a else C["gold"], size=14))
            self.add(Button((W // 2 - 360, H - 150, 340, 54), "VARSAYILANLAR", self.reset_keys, accent=C["orange"], size=15))
            self.add(Button((W // 2 + 20, H - 150, 340, 54), "TAMAM", self.close_rebind, accent=C["green"], size=15))

    def terrain(self, planet):
        t = self.terrains.get(planet)
        if t is None:
            t = Terrain(planet)
            self.terrains[planet] = t
        return t

    def pick_planet(self, p):
        self.planet = p
        self.vkey = VEHICLES_FOR[p][0]
        self.rebuild()

    def pick_vehicle(self, k):
        self.vkey = k
        self.rebuild()

    def pick_mission(self, k):
        self.mkey = k
        self.rebuild()

    def open_rebind(self):
        self._prev_stage = self.stage
        self.stage = "rebind"
        self.rebind = None
        self.rebuild()

    def close_rebind(self):
        self.stage = getattr(self, "_prev_stage", "setup")
        self.rebuild()

    def wait_key(self, a):
        self.rebind = a
        self.rebuild()

    def reset_keys(self):
        self.keys.reset()
        i18n.save_prefs()
        self.rebuild()

    def resume(self):
        self.stage = "drive"
        self.widgets = []

    def to_setup(self):
        self.exit()
        self.stage = "setup"
        self.rebuild()

    # ------------------------------------------------------------------ başla
    def start(self):
        t = self.terrain(self.planet)
        spec = CATALOG[self.vkey]
        c = t.size / 2
        self.rover = Rover(spec, t, c + 4, c, 0.0)
        self.model = VehicleModel(spec)
        q = i18n.PREFS.get("quality", "high")
        w, h, L, far = RES.get(q, RES["high"])
        self.rend = TerrainRenderer(t, w, h, L, far)
        self.cam = Camera()
        self.cam_pos = None
        self.free_yaw, self.free_pitch, self.free_dist = 0.0, -0.3, 12.0
        self.mission = next(m for m in MS.build(self.planet, t) if m.key == self.mkey)
        self.on_foot = None
        self.autopilot = False
        self.tracks = deque(maxlen={"low": 300, "medium": 700, "high": 1400, "ultra": 3000}.get(q, 1400))
        self._last_track = [None] * len(self.rover.wpos)
        self.dust = []
        self.shake = 0.0
        self.sample_flag = False
        self.msg = None
        self.msg_t = 0.0
        self.sun = np.array(PLANETS[self.planet]["sun"], dtype=np.float32)
        self.sun /= np.linalg.norm(self.sun)
        self.rover.lights = self.planet == "titan"
        self.stage = "drive"
        self.widgets = []
        self.eng_on = False
        self.app.say(f"{tr(self.mission.title)}: {tr(self.mission.desc)}", "calm")

    # ---------------------------------------------------------------- olaylar
    def handle(self, e):
        if self.stage == "rebind" and self.rebind and e.type == pygame.KEYDOWN:
            if e.key != pygame.K_ESCAPE:
                sw = self.keys.bind(self.rebind, e.key)
                i18n.save_prefs()
                if sw:
                    self.app.toast(f"{tr(ACTION_LABEL[sw])} ↔ {tr(ACTION_LABEL[self.rebind])}", "gold", "settings")
            self.rebind = None
            self.rebuild()
            return True
        if self.stage != "drive":
            return super().handle(e)
        if self.touch.handle(e):
            return True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.stage = "pause"
                self.rebuild()
                return True
            k = self.keys
            if k.is_event(e, "kamera"):
                self.cam_i = (self.cam_i + 1) % len(CAMS)
            elif k.is_event(e, "bin/in"):
                self.toggle_foot()
            elif k.is_event(e, "farlar"):
                self.rover.lights = not self.rover.lights
                self.app.audio.play("click")
            elif k.is_event(e, "kurtar"):
                self.rover.recover()
                self.say("Kurtarma: araç doğrultuldu (enerji harcandı).")
            elif k.is_event(e, "otopilot"):
                self.autopilot = not self.autopilot
                self.say("Otopilot AÇIK" if self.autopilot else "Otopilot KAPALI")
            elif k.is_event(e, "numune"):
                self.sample_flag = True
        if e.type == pygame.MOUSEWHEEL and CAMS[self.cam_i] == "serbest":
            self.free_dist = clamp(self.free_dist - e.y * 1.2, 4, 40)
        if e.type == pygame.MOUSEMOTION and CAMS[self.cam_i] == "serbest" and e.buttons[0]:
            self.free_yaw -= e.rel[0] * 0.006
            self.free_pitch = clamp(self.free_pitch - e.rel[1] * 0.004, -1.2, 0.2)
        return False

    def toggle_foot(self):
        r = self.rover
        if self.on_foot is None:
            if not r.s.crewed or r.speed > 0.5:
                self.say("Araçtan inmek için dur (yalnız mürettebatlı araçlarda).")
                return
            self.on_foot = [r.x - math.sin(r.yaw) * (r.s.track / 2 + 1.0), r.y + math.cos(r.yaw) * (r.s.track / 2 + 1.0), r.yaw, 0.0]
            self.say("Araçtan indin. WASD yürü, E numune al, F araca bin.")
        else:
            if math.hypot(self.on_foot[0] - r.x, self.on_foot[1] - r.y) > 6:
                self.say("Araca binmek için yaklaş (6 m).")
                return
            self.on_foot = None

    def say(self, text):
        self.msg = tr(text)
        self.msg_t = 3.5

    # ---------------------------------------------------------------- güncelle
    def update(self, dt):
        super().update(dt)
        if self.stage != "drive":
            return
        dt = min(dt, 1 / 20)
        r = self.rover
        pressed = pygame.key.get_pressed()
        k = self.keys
        for b in self.touch.take_pressed():
            self.handle(pygame.event.Event(pygame.KEYDOWN, key=k.codes.get(b) or 0))
        ctl = Controls()
        if self.on_foot is None:
            if self.autopilot:
                ctl = MS.autopilot(r, self.mission.current, r.t)
                if any(k.held(pressed, a) for a in ("ileri", "geri", "sol", "sağ")):
                    self.autopilot = False
                    self.say("Kumanda sende")
            else:
                fwd = k.held(pressed, "ileri")
                back = k.held(pressed, "geri")
                vf = r.forward_speed
                ctl.throttle = 1.0 if fwd else (-1.0 if back and vf < 0.3 else 0.0)
                ctl.brake = 1.0 if back and vf > 0.3 else (0.3 if not fwd and not back and abs(vf) < 0.4 else 0.0)
                ctl.steer = (1.0 if k.held(pressed, "sağ") else 0.0) - (1.0 if k.held(pressed, "sol") else 0.0)
                ctl.handbrake = k.held(pressed, "el freni")
                ctl.boost = k.held(pressed, "hız modu")
                tc = self.touch.controls()
                if self.touch.touches:
                    ctl.throttle = max(ctl.throttle, tc.throttle)
                    ctl.brake = max(ctl.brake, tc.brake)
                    ctl.steer = tc.steer if abs(tc.steer) > abs(ctl.steer) else ctl.steer
        else:
            ctl.brake = 1.0
            self.walk(dt, pressed)
        r.step(ctl, dt)
        for ev in r.events:
            if ev[0] == "çarpışma":
                self.shake = min(1.0, self.shake + ev[1] * 0.4)
                self.app.audio.play("clunk", min(1.0, 0.3 + ev[1] * 0.3))
                if ev[1] > 1.0:
                    self.say(tr("Çarpışma: {0} m/s — hasar {1}").format(n_(ev[1], 1), i18n.pct(r.damage * 100)))
            elif ev[0] == "devrilme":
                self.shake = 1.0
                self.app.audio.play("explosion", 0.5)
                self.say("Araç devrildi! R ile kurtar.")
            elif ev[0] == "arıza":
                self.say(tr("Tekerlek motoru {0} arızalandı").format(ev[1] + 1))
                self.app.audio.play("alarm", 0.5)
        r.events.clear()
        res = self.mission.update(r, dt, (self.on_foot[0], self.on_foot[1]) if self.on_foot else None, self.sample_flag, self.autopilot)
        self.sample_flag = False
        if res == "done":
            self.say(tr("GÖREV TAMAMLANDI") + ": " + tr(self.mission.title))
            self.app.audio.play("success")
            self.reward()
        elif res == "fail":
            self.say(tr("GÖREV BAŞARISIZ") + ": " + tr(self.mission.reason))
            self.app.audio.play("fail")
        elif res:
            self.say(res)
            self.app.audio.play("ping", 0.6)
        self.update_tracks_dust(dt)
        self.update_camera(dt)
        self.engine_audio()
        self.msg_t = max(0.0, self.msg_t - dt)
        self.shake = max(0.0, self.shake - dt * 1.5)
        self.rend.light_on = r.lights
        self.rend.visibility = 0.25 if self.mission.storm and self.mission.state == "aktif" else 1.0

    def reward(self):
        g = self.game
        if g and g.s:
            money, rp = self.mission.reward
            try:
                g.s["money"] = g.s.get("money", 0) + money
                g.s["rp"] = g.s.get("rp", 0) + rp
                self.app.toast(tr("+{0} Para · +{1} Puan").format(money, rp), "gold", "money")
            except Exception:
                pass

    def walk(self, dt, pressed):
        f = self.on_foot
        k = self.keys
        g = PLANETS[self.planet]["g"]
        speed = 1.1 if g < 2 else 1.4                       # düşük yerçekiminde sekerek yürüme (Apollo ~1 m/s)
        turn = (1 if k.held(pressed, "sağ") else 0) - (1 if k.held(pressed, "sol") else 0)
        f[2] -= turn * 1.8 * dt
        mv = (1 if k.held(pressed, "ileri") else 0) - (0.6 if k.held(pressed, "geri") else 0)
        f[0] += math.cos(f[2]) * mv * speed * dt
        f[1] += math.sin(f[2]) * mv * speed * dt
        f[3] += mv * dt * 6

    def update_tracks_dust(self, dt):
        r = self.rover
        q = i18n.quality()
        for i in range(len(r.wpos)):
            if not r.contact[i]:
                continue
            wx, wy = r.wheel_world(i)
            last = self._last_track[i]
            if last is None or math.hypot(wx - last[0], wy - last[1]) > 0.45:
                self.tracks.append((wx, wy, r.t.height(wx, wy) + 0.03))
                self._last_track[i] = (wx, wy)
            sf = SURFACES[r.t.surface_at(wx, wy)]
            if sf["dust"] and r.speed > 0.4 and random.random() < (0.25 + r.wheel_slip[i]) * q.get("fx", 1.0) * dt * 30:
                ang = r.yaw + math.pi + random.uniform(-0.5, 0.5)
                sp = random.uniform(0.4, 1.4) * (r.speed * 0.6 + r.wheel_slip[i] * 2)
                self.dust.append([wx, wy, r.t.height(wx, wy) + 0.1, math.cos(ang) * sp, math.sin(ang) * sp,
                                  random.uniform(0.5, 1.8) * (1 + r.wheel_slip[i]), random.uniform(0.8, 1.6), sf["dust"]])
        g = PLANETS[self.planet]["g"]
        rho = PLANETS[self.planet]["rho"]
        drag = 0.0 if rho == 0 else min(3.0, rho * 0.6 + 0.6)   # Ay: sürtünmesiz balistik yay
        wind = PLANETS[self.planet]["wind"] * 0.1
        alive = []
        for p in self.dust:
            p[3] += (wind - p[3] * drag) * dt
            p[4] += (-p[4] * drag) * dt
            p[5] += (-g - p[5] * drag) * dt
            p[0] += p[3] * dt
            p[1] += p[4] * dt
            p[2] += p[5] * dt
            p[6] -= dt
            if p[6] > 0 and p[2] > r.t.height(p[0], p[1]) - 0.05:
                alive.append(p)
        self.dust = alive[-int(600 * q.get("fx", 1.0)):]

    def update_camera(self, dt):
        r, cam = self.rover, self.cam
        mode = CAMS[self.cam_i]
        spd = r.speed
        cam.fov = math.radians(66 + min(10, spd * 2.5))
        if self.on_foot is not None:
            fx, fy, fyaw, ph = self.on_foot
            tx, ty = fx - math.cos(fyaw) * 3.5, fy - math.sin(fyaw) * 3.5
            tz = r.t.height(tx, ty) + 2.0
            cam.x, cam.y, cam.z, cam.yaw, cam.pitch = tx, ty, max(tz, r.t.height(fx, fy) + 1.6), fyaw, -0.18
            cam.roll = 0.0
        elif mode == "takip":
            d = 5.5 + r.s.wheelbase * 1.1 + spd * 0.5
            want = (r.x - math.cos(r.yaw) * d, r.y - math.sin(r.yaw) * d)
            if self.cam_pos is None:
                self.cam_pos = list(want)
                self.cam_yaw = r.yaw
            k = 1 - math.exp(-dt * 3.0)                       # yumuşak takip (yay)
            self.cam_pos[0] += (want[0] - self.cam_pos[0]) * k
            self.cam_pos[1] += (want[1] - self.cam_pos[1]) * k
            dy = (r.yaw - self.cam_yaw + math.pi) % (2 * math.pi) - math.pi
            self.cam_yaw += dy * (1 - math.exp(-dt * 3.5))
            cam.x, cam.y = self.cam_pos
            cam.z = max(r.t.height(cam.x, cam.y) + 1.2, r.z + 1.8 + r.s.cg_h)
            cam.yaw = self.cam_yaw
            cam.pitch = -math.atan2(cam.z - r.z, d) * 0.85
            cam.roll = 0.0
        elif mode == "kokpit":
            sx, sy, sz = self.model.seat
            c, s = math.cos(r.yaw), math.sin(r.yaw)
            cam.x, cam.y = r.x + c * sx, r.y + s * sx
            cam.z = r.z + sz + sx * -math.sin(r.pitch)
            cam.yaw, cam.pitch, cam.roll = r.yaw, -0.06 - r.pitch, r.roll      # r.pitch < 0: burun yukarı
        elif mode == "ön":
            off = r.s.wheelbase / 2 + 0.6
            cam.x, cam.y = r.x + math.cos(r.yaw) * off, r.y + math.sin(r.yaw) * off
            cam.z = r.z + 0.1 - off * math.sin(r.pitch)
            cam.yaw, cam.pitch, cam.roll = r.yaw, -r.pitch - 0.02, r.roll
            cam.fov = math.radians(84)
        else:   # serbest
            yaw = r.yaw + self.free_yaw
            cam.x = r.x - math.cos(yaw) * self.free_dist * math.cos(self.free_pitch)
            cam.y = r.y - math.sin(yaw) * self.free_dist * math.cos(self.free_pitch)
            cam.z = max(r.t.height(cam.x, cam.y) + 1.0, r.z - math.sin(self.free_pitch) * self.free_dist)
            cam.yaw = yaw
            cam.pitch = -math.atan2(cam.z - r.z, self.free_dist * math.cos(self.free_pitch))
            cam.roll = 0.0
        # sarsıntı: süspansiyon dikey hızı + çarpışma (ayar: sinematik efektler)
        k = (abs(r.vz) * 0.03 + self.shake * 0.25) * (1 if i18n.PREFS.get("cinematic", True) else 0.3)
        cam.z += random.uniform(-k, k) * 0.5
        cam.pitch += random.uniform(-k, k) * 0.05

    def engine_audio(self):
        au = self.app.audio
        if not au or not getattr(au, "ok", False):
            return
        p = self.rover.power_kw / max(0.1, self.rover.s.motor_kw)
        if p > 0.05 and not self.eng_on:
            au.loop("engine", 0.0, fade=300)
            self.eng_on = True
        if self.eng_on:
            try:
                au.loop_ch.set_volume(min(0.6, 0.12 + p * 0.5) * au.sfx_vol * (0.5 if self.planet == "moon" else 1.0))
            except Exception:
                pass
            if p < 0.02:
                au.stop_loop(400)
                self.eng_on = False

    # ------------------------------------------------------------------- çizim
    def draw(self, surf):
        if self.stage in ("setup",) or (self.stage == "rebind" and not hasattr(self, "rover")):
            self.bg.draw(surf)
            self.draw_setup(surf)
            self.draw_widgets(surf)
            if self.stage == "rebind":
                self.draw_rebind(surf)
            return
        self.draw_world(surf)
        self.draw_hud(surf)
        if self.stage == "pause":
            pygame.draw.rect(surf, (4, 6, 14), (W // 2 - 220, H // 2 - 140, 440, 280), border_radius=18)
            draw_text(surf, "DURAKLATILDI", (W // 2, H // 2 - 124), 22, C["text"], bold=True, anchor="midtop")
            self.draw_widgets(surf)
        elif self.stage == "rebind":
            self.draw_rebind(surf)

    def draw_setup(self, surf):
        draw_text(surf, "ROVER · GEZEGEN ARACI SÜRÜŞÜ", (80, 100), 34, C["text"], bold=True, glow=scale_color(C["orange"], 0.5))
        draw_text(surf, "Gezegen", (80, 182), 15, C["text_dim"], bold=True)
        draw_text(surf, "Araç", (80, 302), 15, C["text_dim"], bold=True)
        draw_text(surf, "Görev", (840, 182), 15, C["text_dim"], bold=True)
        p = PLANETS[self.planet]
        s = CATALOG[self.vkey]
        r = pygame.Rect(80, 560, 700, 200)
        glass_panel(surf, r, C["cyan"], 175, 16)
        draw_text(surf, s.name, (r.x + 20, r.y + 14), 18, C["text"], bold=True)
        rows = [("Kütle", f"{n_(s.mass)} kg"), ("En yüksek hız", f"{n_(s.top_speed * 3.6, 1)} km/h"), ("Motor", f"{n_(s.motor_kw, 2)} kW"),
                ("Batarya", f"{n_(s.battery_kwh, 1)} kWh"), ("Tekerlek", f"{s.wheels} × Ø{n_(s.wheel_r * 200)} cm" if not s.tracked else "palet"),
                ("Devrilme açısı", f"{n_(math.degrees(math.atan((s.track / 2) / s.cg_h)))}°")]
        for i, (k, v) in enumerate(rows):
            x = r.x + 20 + (i % 2) * 340
            y = r.y + 50 + (i // 2) * 26
            draw_text(surf, k, (x, y), 14, C["text_dim"])
            draw_text(surf, v, (x + 320, y), 14, C["text"], bold=True, anchor="topright", raw=True)
        draw_paragraph(surf, tr(s.note) + "  " + ((tr("Varsayım") + ": " + tr(s.assumed)) if s.assumed else ""), (r.x + 20, r.y + 132), r.w - 40, 12,
                       C["text_dim"], max_lines=4, raw=True)
        r2 = pygame.Rect(840, 560, 710, 200)
        glass_panel(surf, r2, C["gold"], 175, 16)
        draw_text(surf, f"{tr(p['name'])} · " + tr("yerçekimi") + f" {n_(p['g'], 3)} m/s²", (r2.x + 20, r2.y + 14), 17, C["text"], bold=True, raw=True)
        lines = [f"{tr('Basınç')}: {n_(p['pressure_bar'], 4)} bar · {tr('Sıcaklık')}: {n_(p['temp_c'])} °C",
                 f"{tr('Kaynak')}: {tr(p['source'])}",
                 tr("Zemin tutunma katsayıları literatüre dayalı yaklaşık değerlerdir; Titan zemini ölçülmemiştir (oyun varsayımı).")]
        y = r2.y + 50
        for ln in lines:
            draw_paragraph(surf, ln, (r2.x + 20, y), r2.w - 40, 13, C["text_dim"], max_lines=2, raw=True)
            y += 40

    def draw_rebind(self, surf):
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        surf.blit(dim, (0, 0))
        pygame.draw.rect(surf, (4, 6, 14), (W // 2 - 400, 120, 800, H - 190), border_radius=18)
        draw_text(surf, "KONTROLLER", (W // 2, 140), 24, C["text"], bold=True, anchor="midtop")
        draw_text(surf, "Değiştirmek için bir eyleme tıkla, sonra yeni tuşa bas. Aynı tuş başka eylemdeyse yer değiştirir.",
                  (W // 2, 172), 13, C["text_dim"], anchor="midtop")
        self.draw_widgets(surf)
        draw_text(surf, "Dokunmatik: sol altta direksiyon (sürükle), sağ altta gaz/fren pedalları ve düğmeler.",
                  (W // 2, H - 84), 13, C["text_dim"], anchor="midtop")

    def draw_world(self, surf):
        r, cam, rend = self.rover, self.cam, self.rend
        fog = 70.0 if rend.visibility < 1 else None
        img = rend.render(cam, fog)
        sc = W / rend.w
        if abs(cam.roll) > 0.01:
            img = pygame.transform.rotate(img, math.degrees(cam.roll))
            img = pygame.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
            surf.blit(img, (W // 2 - img.get_width() // 2, H // 2 - img.get_height() // 2))
        else:
            pygame.transform.smoothscale(img, (W, H), surf)
        self.draw_tracks(surf, sc)
        self.draw_rocks(surf, sc)
        self.draw_beacon(surf, sc)
        if CAMS[self.cam_i] != "kokpit" or self.on_foot is not None:
            self.model.draw(surf, rend, cam, r, self.sun, sc, r.damage, r.lights)
        self.draw_dust(surf, sc)
        if self.on_foot is not None:
            f = self.on_foot
            P = np.array(((f[0], f[1], r.t.height(f[0], f[1]) + 0.9),), dtype=np.float32)
            sx, sy, dep = rend.project(cam, P)
            if dep[0] > 0.5:
                k = clamp(5.0 / dep[0], 0.3, 2.5)
                art.draw_astronaut(surf, int(sx[0] * sc), int(sy[0] * sc), "pilot", k, self.t + f[3])
        if rend.visibility < 1:          # fırtına: süzülen toz çizgileri
            for i in range(60):
                x = (i * 137 + self.t * 900) % W
                y = (i * 71 + self.t * 120) % H
                pygame.draw.line(surf, (210, 160, 120), (x, y), (x - 30, y + 4), 1)
        if CAMS[self.cam_i] == "kokpit" and self.on_foot is None:
            self.draw_cockpit_frame(surf)

    def draw_rocks(self, surf, sc):
        r, rend, cam = self.rover, self.rend, self.cam
        R = r.t.rocks_near(cam.x, cam.y, 140)
        if not len(R):
            return
        P = np.column_stack([R[:, 0], R[:, 1], r.t.heights(R[:, 0], R[:, 1]) + R[:, 2] * 0.5])
        sx, sy, dep = rend.project(cam, P)
        vis = rend.visible(sx, sy, dep)
        order = np.argsort(-dep)
        base = np.array(SURFACES["kaya" if self.planet != "titan" else "buz kaya"]["color"], dtype=np.float32)
        for i in order:
            if not vis[i] or dep[i] < 0.5:
                continue
            rad = R[i, 2] * rend.focal / dep[i] * sc
            if rad < 0.6:
                continue
            x, y = sx[i] * sc, sy[i] * sc
            lit = tuple(int(c) for c in np.clip(base * 1.25, 0, 255))
            dark = tuple(int(c) for c in base * 0.45)
            pygame.draw.ellipse(surf, dark, (x - rad, y - rad * 0.55, rad * 2, rad * 1.25))
            pygame.draw.ellipse(surf, lit, (x - rad * 0.9 + rad * 0.2, y - rad * 0.6, rad * 1.4, rad * 0.9))

    def draw_tracks(self, surf, sc):
        if not self.tracks:
            return
        P = np.array(self.tracks, dtype=np.float32)
        d = np.hypot(P[:, 0] - self.cam.x, P[:, 1] - self.cam.y)
        P = P[d < 80]
        if not len(P):
            return
        sx, sy, dep = self.rend.project(self.cam, P)
        vis = self.rend.visible(sx, sy, dep)
        col = tuple(int(c * 0.55) for c in SURFACES[self.rover.t.surface_at(self.rover.x, self.rover.y)]["color"])
        for x, y, dd, v in zip(sx, sy, dep, vis):
            if v and dd > 0.8:
                s = max(1, int(5 * sc / dd))
                pygame.draw.rect(surf, col, (int(x * sc) - s, int(y * sc), s * 2, max(1, s // 2)))

    def draw_dust(self, surf, sc):
        if not self.dust:
            return
        P = np.array([p[:3] for p in self.dust], dtype=np.float32)
        sx, sy, dep = self.rend.project(self.cam, P)
        for (x, y, dd), p in zip(zip(sx, sy, dep), self.dust):
            if dd > 0.5:
                rr = max(1, int(3 * sc / dd * (0.5 + p[6])))
                pygame.draw.circle(surf, p[7], (int(x * sc), int(y * sc)), rr)

    def draw_beacon(self, surf, sc):
        o = self.mission.current
        if not o:
            return
        g = self.rover.t.height(o.x, o.y)
        P = np.array(((o.x, o.y, g), (o.x, o.y, g + 30)), dtype=np.float32)
        sx, sy, dep = self.rend.project(self.cam, P)
        if dep[0] < 1 or dep[1] < 1 or not np.all(np.isfinite(np.concatenate([sx, sy]))):
            return
        x0, y0, x1, y1 = (float(clamp(v, -4000, 4000)) for v in (sx[0] * sc, sy[0] * sc, sx[1] * sc, sy[1] * sc))
        if -50 < x0 < W + 50:
            pygame.draw.line(surf, C["gold"], (x0, y0), (x1, y1), 2)
            draw_glow(surf, (int(x1), int(y1)), 18, C["gold"], 0.8)
            dist = math.hypot(o.x - self.rover.x, o.y - self.rover.y)
            draw_text(surf, f"{tr(o.label)} · {n_(dist)} m", (x1, y1 - 26), 14, C["gold"], bold=True, anchor="midbottom", raw=True)

    def draw_cockpit_frame(self, surf):
        s = self.rover.s
        if s.key in ("sev", "mars_rover", "titan_crawler"):        # kapalı kabin: direkler + tavan
            pygame.draw.polygon(surf, (16, 18, 24), [(0, 0), (W, 0), (W, 90), (0, 90)])
            pygame.draw.polygon(surf, (22, 24, 30), [(0, 0), (140, 0), (60, H), (0, H)])
            pygame.draw.polygon(surf, (22, 24, 30), [(W, 0), (W - 140, 0), (W - 60, H), (W, H)])
        pygame.draw.rect(surf, (18, 20, 26), (0, H - 230, W, 230))
        pygame.draw.line(surf, (60, 66, 80), (0, H - 230), (W, H - 230), 3)
        if self.rover.lights:
            pygame.draw.rect(surf, (40, 44, 30), (W // 2 - 300, H - 226, 600, 4))

    # --------------------------------------------------------------- gösterge
    def comms(self):
        """Üsse iletişim: uzaklık + arazi görüş hattı (tepeler sinyali keser)."""
        r = self.rover
        c = r.t.size / 2
        dist = math.hypot(r.x - c, r.y - c)
        h0 = r.t.height(c, c) + 6.0          # üs anteni
        h1 = r.z + 1.5
        blocked = False
        for k in range(1, 20):
            t = k / 20
            x, y = c + (r.x - c) * t, c + (r.y - c) * t
            if r.t.height(x, y) > h0 + (h1 - h0) * t:
                blocked = True
                break
        q = max(0.0, 1 - dist / 1600) * (0.15 if blocked else 1.0)
        return q, blocked

    def draw_hud(self, surf):
        r = self.rover
        d = r.dashboard()
        # sol üst: görev
        m = self.mission
        mr = pygame.Rect(20, 20, 470, 150)
        glass_panel(surf, mr, C["gold"], 170, 14)
        draw_text(surf, tr(m.title).upper(), (mr.x + 16, mr.y + 12), 15, C["gold"], bold=True, raw=True)
        o = m.current
        st = {"başarılı": tr("GÖREV TAMAMLANDI"), "başarısız": tr("GÖREV BAŞARISIZ") + ": " + tr(m.reason)}.get(m.state)
        draw_paragraph(surf, st or (tr("Hedef") + ": " + tr(o.label) if o else ""), (mr.x + 16, mr.y + 38), mr.w - 32, 14, C["text"],
                       max_lines=2, raw=True)
        done = sum(1 for x in m.obj if x.done)
        draw_bar(surf, (mr.x + 16, mr.y + 86, mr.w - 32, 8), done / len(m.obj), C["gold"], glow=False)
        info = f"{done}/{len(m.obj)}"
        if m.time_limit:
            info += f" · {tr('kalan süre')} {max(0, int(m.time_limit - m.t))} s"
        if o and o.kind == "bekle" and o.t > 0:
            info += f" · {tr('ölçüm')} {n_(o.t, 1)}/{n_(o.hold)} s"
        if m.cargo:
            info += f" · {tr('kargo')} {n_(m.cargo)} kg"
        draw_text(surf, info, (mr.x + 16, mr.y + 104), 13, C["text_dim"], raw=True)
        draw_text(surf, f"{tr('Kamera')}: {tr(CAMS[self.cam_i])} (C) · {tr('Otopilot')}: {tr('AÇIK') if self.autopilot else tr('KAPALI')} (P)",
                  (mr.x + 16, mr.y + 124), 12, C["cyan"], raw=True)
        # sağ üst: radar (60 m) + navigasyon + iletişim
        rr = pygame.Rect(W - 250, 20, 230, 290)
        glass_panel(surf, rr, C["cyan"], 170, 14)
        cx, cy, R = rr.centerx, rr.y + 120, 95
        pygame.draw.circle(surf, (14, 26, 40), (cx, cy), R)
        pygame.draw.circle(surf, (50, 90, 120), (cx, cy), R, 1)
        pygame.draw.circle(surf, (40, 70, 96), (cx, cy), R // 2, 1)
        ca, sa = math.cos(-r.yaw + math.pi / 2), math.sin(-r.yaw + math.pi / 2)
        for x, y, rad in r.t.rocks_near(r.x, r.y, 60):
            dx, dy = x - r.x, y - r.y
            px, py = dx * ca - dy * sa, dx * sa + dy * ca
            if rad * 0.8 > r.s.clearance:
                pygame.draw.circle(surf, C["red"] if rad > 0.6 else C["orange"], (int(cx + px * R / 60), int(cy - py * R / 60)), 3)
        if o:
            dx, dy = o.x - r.x, o.y - r.y
            px, py = dx * ca - dy * sa, dx * sa + dy * ca
            L = math.hypot(px, py)
            k = min(1.0, (R - 6) / max(1e-6, L * R / 60))
            pygame.draw.circle(surf, C["gold"], (int(cx + px * R / 60 * k), int(cy - py * R / 60 * k)), 6, 2)
        pygame.draw.polygon(surf, C["green"], [(cx, cy - 8), (cx - 5, cy + 6), (cx + 5, cy + 6)])
        draw_text(surf, "RADAR 60 m", (rr.x + 12, rr.y + 8), 11, C["text_dim"], bold=True)
        if o:
            dist = math.hypot(o.x - r.x, o.y - r.y)
            brg = (math.degrees(math.atan2(o.x - r.x, o.y - r.y)) + 360) % 360
            draw_text(surf, f"NAV {n_(dist)} m · {n_(brg)}°", (rr.x + 12, rr.y + 226), 13, C["gold"], bold=True, raw=True)
        q, blocked = self.comms()
        draw_text(surf, f"{tr('İletişim')} {i18n.pct(q * 100)}" + (f" · {tr('tepe engelliyor')}" if blocked else ""), (rr.x + 12, rr.y + 248), 12,
                  C["green"] if q > 0.4 else C["orange"] if q > 0.1 else C["red"], raw=True)
        draw_text(surf, f"{tr(d['zemin'])} · {tr('patinaj')} {i18n.pct(d['patinaj'] * 100)}", (rr.x + 12, rr.y + 266), 12, C["text_dim"], raw=True)
        # alt: gösterge paneli (gerçek araç verisi)
        y0 = H - 150
        panel = pygame.Rect(W // 2 - 520, y0, 1040, 132)
        glass_panel(surf, panel, C["orange"], 190, 16)
        # hız göstergesi
        gx, gy = panel.x + 90, panel.y + 70
        top = r.s.top_speed * 3.6 * 1.3
        pygame.draw.circle(surf, (12, 18, 30), (gx, gy), 56)
        for k in range(0, 11):
            a = math.radians(225 - k * 27)
            pygame.draw.line(surf, (90, 100, 120), (gx + math.cos(a) * 48, gy - math.sin(a) * 48), (gx + math.cos(a) * 55, gy - math.sin(a) * 55), 2)
        a = math.radians(225 - min(1.0, d["hız_kmh"] / top) * 270)
        pygame.draw.line(surf, C["orange"], (gx, gy), (gx + math.cos(a) * 46, gy - math.sin(a) * 46), 3)
        draw_text(surf, f"{n_(d['hız_kmh'], 1)}", (gx, gy + 14), 18, C["text"], bold=True, anchor="midtop", raw=True)
        draw_text(surf, "km/h", (gx, gy + 36), 10, C["text_dim"], anchor="midtop")
        x = panel.x + 170
        bars = [("BATARYA", d["batarya_yüzde"] / 100, f"{i18n.pct(d['batarya_yüzde'])} · {n_(d['batarya_kwh'], 2)} kWh", C["green"]),
                ("GÜÇ", min(1.0, d["güç_kw"] / max(0.1, r.s.motor_kw * 1.35)), f"{n_(d['güç_kw'], 2)} kW", C["cyan"]),
                ("MOTOR SICAKLIĞI", clamp((d["motor_c"] + 60) / 210, 0, 1), f"{n_(d['motor_c'])} °C", C["red"] if d["motor_c"] > 110 else C["orange"]),
                ("HASAR", d["hasar_yüzde"] / 100, i18n.pct(d['hasar_yüzde']), C["red"])]
        for i, (lab, v, txt, col) in enumerate(bars):
            bx = x + (i % 2) * 260
            by = panel.y + 22 + (i // 2) * 52
            draw_text(surf, lab, (bx, by), 11, C["text_dim"], bold=True)
            draw_text(surf, txt, (bx + 240, by), 12, C["text"], bold=True, anchor="topright", raw=True)
            draw_bar(surf, (bx, by + 20, 240, 8), v, col, glow=False)
        # yön şeridi ve ufuk göstergesi
        hx = panel.x + 720
        draw_text(surf, f"{tr('YÖN')} {n_(d['yön_derece'])}°", (hx, panel.y + 18), 13, C["text"], bold=True, raw=True)
        ac = (hx + 60, panel.y + 82)
        pygame.draw.circle(surf, (12, 18, 30), ac, 38)
        roll = math.radians(d["yalpa"])
        off = clamp(-d["yunuslama"] * 1.2, -30, 30)          # burun yukarı -> ufuk çizgisi aşağı
        p1 = (ac[0] - math.cos(roll) * 36, ac[1] + off - math.sin(roll) * 36)
        p2 = (ac[0] + math.cos(roll) * 36, ac[1] + off + math.sin(roll) * 36)
        pygame.draw.line(surf, C["cyan"], p1, p2, 2)
        pygame.draw.circle(surf, (60, 80, 100), ac, 38, 1)
        draw_text(surf, f"{tr('Eğim')} {n_(d['eğim'])}° · {tr('yalpa')} {n_(d['yalpa'])}°", (hx + 110, panel.y + 52), 12, C["text_dim"], raw=True)
        draw_text(surf, f"{tr('Yükseklik')} {n_(d['yükseklik_m'], 1)} m", (hx + 110, panel.y + 72), 12, C["text_dim"], raw=True)
        sysst = []
        if d["arızalı_tekerlek"]:
            sysst.append(tr("arızalı tekerlek") + " " + ",".join(str(i + 1) for i in d["arızalı_tekerlek"]))
        if d["devrildi"]:
            sysst.append(tr("DEVRİLDİ (R)"))
        if d["yüzüyor"]:
            sysst.append(tr("yüzüyor"))
        if r.lights:
            sysst.append(tr("farlar"))
        draw_text(surf, tr("Sistemler") + ": " + (", ".join(sysst) if sysst else tr("normal")), (hx + 110, panel.y + 92), 12,
                  C["red"] if d["devrildi"] or d["arızalı_tekerlek"] else C["green"], raw=True, max_w=300)
        if self.msg_t > 0 and self.msg:
            draw_text(surf, self.msg, (W // 2, 200), 20, C["text"], bold=True, anchor="midtop", glow=scale_color(C["orange"], 0.4), raw=True)
        if self.touch.active:
            self.draw_touch(surf)
        draw_text(surf, tr("ESC: duraklat · C kamera · F bin/in · L far · R kurtar · P otopilot · E numune"), (W // 2, H - 14), 11,
                  C["text_mute"], anchor="midbottom")

    def draw_touch(self, surf):
        t = self.touch
        pygame.draw.circle(surf, (20, 30, 46), t.wheel_c, t.wheel_r, 4)
        a = -t.steer * 1.2
        for k in range(3):
            aa = a + k * 2 * math.pi / 3 - math.pi / 2
            pygame.draw.line(surf, (90, 110, 140), t.wheel_c, (t.wheel_c[0] + math.cos(aa) * t.wheel_r, t.wheel_c[1] + math.sin(aa) * t.wheel_r), 4)
        for rect, lab, col in ((t.gas, "GAZ", C["green"]), (t.brake, "FREN", C["red"])):
            pygame.draw.rect(surf, scale_color(col, 0.3), rect, border_radius=14)
            pygame.draw.rect(surf, col, rect, 2, border_radius=14)
            draw_text(surf, lab, rect.center, 15, C["text"], bold=True, anchor="center")
        for k, rect in t.buttons.items():
            pygame.draw.rect(surf, (20, 30, 46), rect, border_radius=12)
            pygame.draw.rect(surf, C["cyan"], rect, 1, border_radius=12)
            draw_text(surf, {"kamera": "KAMERA", "bin/in": "BİN/İN", "farlar": "FAR", "kurtar": "R"}[k], rect.center, 12, C["text"], bold=True,
                      anchor="center")

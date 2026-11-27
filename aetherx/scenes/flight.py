# -*- coding: utf-8 -*-
"""
YOLCULUK - MİNİ OYUN (Görev Kontrol'den canlı takip)

Oynanış: Fare/parmak ya da W-S ile roketi yukarı-aşağı oynat.
Asteroitlerden kaç veya lazerle kır (SPACE / sol tık). Yıldız Tozu topla,
uydu kurtar, fotoğraf çek (F). Hızlandır (D) / Yavaşlat (A), Tamir (R),
NOVA'ya sor (N), Görev Kontrol haritası (TAB).

Can barı YOK. Yakıt, Oksijen, Elektrik barları ve ayrı ayrı Parça Durumu
(Motor / Panel / Anten) vardır. Bozulan parça kırmızı olur.
"""
import math
import random

import numpy as np
import pygame

from . import Scene
from .. import space3d as S3
from .. import i18n
from .. import art
from .. import data as D
from .. import rocket as R
from ..config import C, GAME_MIN_PER_SEC, H, W
from ..fx import (overlay, ParticleSystem, Shake, SpaceBackground, Spring, clamp, draw_glow, ease_out_cubic, lerp,
                  lerp_color, scale_color)
from ..ui import (UI, Button, chip, dashed_line, draw_bar, draw_icon, draw_text, glass_panel, radial_progress,
                  fmt_time)

TOP, BOTTOM = 110, H - 120
ROCKET_X = 260
PARTS = [("engine", "MOTOR", "fuel"), ("power", "PANEL", "bolt"), ("antenna", "ANTEN", "antenna")]
SPAWN = {   # bölge -> (aralık sn, tür ağırlıkları)
    "space":     (1.6, {"rock": 6, "gold": 0.4, "ice": 0.6, "ore": 0.8}),
    "debris":    (0.55, {"debris": 8, "rock": 1}),
    "asteroids": (0.65, {"rock": 6, "big": 1, "gold": 0.9, "ice": 1.0, "ore": 1.4}),
    "belt":      (0.38, {"rock": 7, "big": 2, "gold": 1.2, "ice": 1.0, "ore": 1.8}),
    "stardust":  (1.3, {"rock": 3, "ice": 1}),
    "dark":      (1.2, {"rock": 5, "ore": 1}),
    "heat":      (1.1, {"rock": 4, "gold": 0.5}),
    "radiation": (0.9, {"rock": 5, "big": 1, "gold": 1}),
}


class Obj:
    __slots__ = ("kind", "x", "y", "vx", "vy", "r", "hp", "seed", "rot", "spin", "dead", "used", "t", "ore",
                 "data")

    def __init__(self, kind, x, y, vx, vy, r, hp=1):
        self.kind, self.x, self.y, self.vx, self.vy, self.r, self.hp = kind, x, y, vx, vy, r, hp
        self.seed = random.randint(0, 9999)
        self.rot = random.uniform(0, 360)
        self.spin = random.uniform(-60, 60)
        self.dead = False
        self.used = False
        self.t = 0.0
        self.ore = False
        self.data = None


# ===========================================================================
# SİMÜLASYON
# ===========================================================================
class FlightSim:
    def __init__(self, game, design, rep):
        self.g = game
        self.d = design
        self.rep = rep
        self.pl = D.PLANET[design["planet"]]
        self.hull = D.PART["hull"][design["hull"]]
        self.eng = D.PART["engine"][design["engine"]]
        self.pwr = D.PART["power"][design["power"]]
        self.ant = D.PART["antenna"][design["antenna"]]
        self.payloads = set(design.get("payloads", []))
        self.crew = list(design.get("crew", []))
        self.roles = game.crew_roles(self.crew)
        self.dist = self.pl["dist"]
        self.progress = 0.0
        self.elapsed = 0.0
        self.throttle = 1.0
        self.speed = 0.0
        self.fuel = rep.get("fuel_kg", 0.0)
        self.fuel_max = max(1.0, self.hull["tank"])
        self.energy = self.pwr["cap"]
        self.e_max = self.pwr["cap"]
        self.o2 = rep.get("o2_sec", 0.0) if self.crew else 0.0
        self.o2_max = max(1.0, self.o2)
        self.y = H / 2
        self.vy = 0.0
        self.target_y = H / 2
        self.parts = {"engine": True, "power": True, "antenna": True}
        self.repair = None           # (parça, kalan, toplam)
        self.objs = []
        self.shots = []
        self.spawn_t = 1.2
        self.misc_t = 4.0
        self.laser_cd = 0.0
        self.photo_cd = 0.0
        self.outcome = None
        self.reason = ""
        self.stranded = 0.0
        self.blackout = False
        self.events = []              # (tür, veri) - sahne efektleri için
        self.stats = {"asteroids": 0, "stardust": 0, "photos": 0, "rescues": 0, "damage": 0,
                      "minerals": {}, "fuel_pick": 0}
        self.storm_warned = False
        self.storm_on = False
        self.sickness = {cid: 0.0 for cid in self.crew}
        self.heat = 0.0
        self.link_lost = False
        self.station_spawned = False
        self.sats_left = random.choice([0, 1, 1, 2])
        self.photo_ops = 0
        self.dodge = rep.get("dodge", 0.45)
        # fizik: yan iticilerin ivmesi = itki / kütle (ağır roket daha hantal döner)
        self.mass = max(40.0, float(rep.get("total", 150)) - (rep.get("fuel_kg", 0.0) or 0.0))
        self.accel = 2600.0 * clamp(170.0 / self.mass, 0.35, 1.6)
        self.cluster_t = random.uniform(2.0, 5.0)
        self.injury = game.injury_chance()
        self.sick_k = game.sick_mult()
        self.repair_k = game.repair_mult()
        self.pilot = self.roles.get("pilot", 0.0)
        self.engineer = self.roles.get("engineer", 0.0)
        self.doctor = self.roles.get("doctor", 0.0)
        self.miner = self.roles.get("miner", 0.0)
        self.burn_k = R.BURN_K * (0.9 if game.has_tech("fuelchem") else 1.0)
        self.heat_ok = game.has_tech("heatshield") or self.hull.get("heat_shield")
        self.start_min = game.minutes
        self.nova_tip_t = 0.0
        self.threat = None
        self.e_warned = False
        self.f_warned = False
        self.o_warned = False

    # ------------------------------------------------------------ yardımcı
    @property
    def frac(self):
        return clamp(self.progress / self.dist, 0, 1)

    def zone(self):
        f = self.frac
        for a, b, k in self.pl["zones"]:
            if a <= f < b:
                return k
        return "space"

    def sun(self):
        return lerp(1.0, self.pl["sun"], self.frac)

    def link_ok(self):
        if not self.parts["antenna"]:
            return False
        if self.rep.get("link_ok"):
            return True
        return self.frac < self.rep.get("link_lost_at", 0.3)

    def emit(self, etype, **data):
        self.events.append((etype, data))

    # ----------------------------------------------------------- güncelle
    def update(self, dt, inp):
        if self.outcome:
            return
        self.elapsed += dt
        self.laser_cd = max(0.0, self.laser_cd - dt)
        self.photo_cd = max(0.0, self.photo_cd - dt)
        zone = self.zone()
        # --- hız -----------------------------------------------------------
        if self.eng["key"] == "ion":
            ramp = clamp(self.elapsed / 30.0, 0, 1)
            espd = lerp(self.eng["speed"], self.eng["speed_max"], ramp)
        elif self.eng.get("solar"):
            espd = max(0.35, self.eng["speed"] * self.sun() ** 0.85)
        else:
            espd = self.eng["speed"]
        thrust_ok = self.parts["engine"]
        if self.eng["burn"] > 0 and self.fuel <= 0:
            thrust_ok = False
        if self.eng["key"] == "ion" and self.energy <= 0.05:
            thrust_ok = False
        target = self.hull["speed"] * espd * self.throttle * (1.0 if self.pilot else 0.85)
        if not self.parts["engine"]:
            target *= 0.35
        if not thrust_ok and self.parts["engine"]:
            target = 0.0
        self.speed += (target - self.speed) * min(1.0, dt * (0.6 if target < self.speed else 1.2))
        self.progress += self.speed * dt
        # --- yakıt ---------------------------------------------------------
        if self.parts["engine"] and self.eng["burn"] > 0 and self.fuel > 0:
            self.fuel = max(0.0, self.fuel - self.eng["burn"] * self.burn_k * (self.throttle ** 1.6) * dt)
        if self.pwr["kind"] == "fuelcell" and self.parts["power"] and self.fuel > 0:
            self.fuel = max(0.0, self.fuel - self.pwr.get("fuel_use", 0.07) * dt)
        if self.eng["burn"] > 0 and self.fuel <= 0 or (self.eng["key"] == "ion" and self.energy <= 0.05):
            if self.speed < 0.08:
                self.stranded += dt
                if self.stranded > 6.0:
                    self.finish("fail", "Yakıt bitti: roket yolda kaldı" if self.fuel <= 0 else
                                "Elektrik bitti: iyon motoru durdu, roket yolda kaldı")
                    return
        else:
            self.stranded = 0.0
        # --- elektrik ------------------------------------------------------
        storm = self.g.storm_active()
        self.storm_on = bool(storm)
        gen = 0.0
        if self.parts["power"]:
            k = self.pwr["kind"]
            if k == "solar":
                gen = self.pwr["gen"] * self.sun() * (0.0 if zone == "dark" else 1.0) * (0.45 if storm else 1.0)
            elif k == "rtg":
                gen = self.pwr["gen"]
            elif k == "fuelcell":
                gen = self.pwr["gen"] if self.fuel > 0 else 0.0
        draw = D.BASE_DRAW + self.ant["draw"] + sum(D.PART["payload"][p]["draw"] for p in self.payloads)
        draw += self.eng["draw"] * (self.throttle if self.parts["engine"] else 0.2) + 0.15 * len(self.crew)
        if storm:
            draw += 0.8 * storm["power"]
        self.energy = clamp(self.energy + (gen - draw) * dt, 0.0, self.e_max)
        was = self.blackout
        self.blackout = self.energy <= 0.05
        if self.blackout and not was:
            self.emit("blackout")
        if self.energy < self.e_max * 0.2 and not self.e_warned and not self.blackout:
            self.e_warned = True
            self.emit("tip", kind="power")
        # --- oksijen -------------------------------------------------------
        if self.crew:
            self.o2 = max(0.0, self.o2 - dt)
            if self.o2 < self.o2_max * 0.2 and not self.o_warned:
                self.o_warned = True
                self.emit("tip", kind="o2")
            if self.o2 <= 0:
                self.finish("fail", "Oksijen bitti: astronotlar bayıldı, kurtarma ekibi gönderildi")
                return
        if self.eng["burn"] > 0 and self.fuel < self.fuel_max * 0.15 and not self.f_warned:
            self.f_warned = True
            self.emit("tip", kind="fuel")
        # --- fırtına -------------------------------------------------------
        nxt = self.g.next_storm()
        warn_min = 0
        if "magneto" in self.payloads:
            warn_min = 30
        if self.g.nova_level >= 3:
            warn_min = max(warn_min, 40)
        if nxt and not storm and warn_min:
            lead = nxt["start"] - self.g.minutes
            if 0 < lead <= warn_min and not self.storm_warned:
                self.storm_warned = True
                self.emit("storm_warn", seconds=lead / GAME_MIN_PER_SEC)
        if storm:
            self.storm_warned = False
            armor = 0.6 if self.hull["dur"] >= 4 else 1.0
            if random.random() < 0.035 * storm["power"] * dt * 10 * armor * 0.1:
                self.damage_random("Güneş Fırtınası")
        # --- ısı / radyasyon ----------------------------------------------
        if zone == "heat" and not self.heat_ok:
            self.heat += dt
            self.energy = max(0.0, self.energy - 0.6 * dt)
            if random.random() < 0.02 * dt * 10 * 0.1 * 3:
                self.damage_random("Aşırı ısı")
        rad = 0.0
        if self.eng.get("radiation"):
            rad += 0.9
        if zone == "radiation":
            rad += 2.2
        if rad and self.crew:
            k = 0.3 if self.doctor else 1.0
            for cid in self.sickness:
                self.sickness[cid] = clamp(self.sickness[cid] + rad * k * self.sick_k * dt * 1.2
                                           - (0.8 * self.doctor * dt), 0, 100)
        # --- bağlantı -----------------------------------------------------
        if not self.link_ok() and not self.link_lost:
            self.link_lost = True
            self.emit("link_lost")
        # --- kontrol --------------------------------------------------------
        if inp.get("mouse_y") is not None:
            self.target_y = inp["mouse_y"]
        self.target_y += inp.get("axis", 0) * 640 * dt
        self.target_y = clamp(self.target_y, TOP + 20, BOTTOM - 20)
        max_v = 560 * self.dodge * (0.5 if not self.parts["engine"] else 1.0)
        want = clamp((self.target_y - self.y) * 6.0, -max_v, max_v)
        mass_now = self.mass + self.fuel
        acc = self.accel * (170.0 / mass_now) ** 0.5 * (1.25 if self.pilot else 0.8)
        dv = clamp(want - self.vy, -acc * dt, acc * dt)          # sınırlı ivme: atalet
        self.vy += dv
        self.y += self.vy * dt
        if self.y < TOP + 16 or self.y > BOTTOM - 16:            # ekran sınırına yumuşak çarpma
            self.y = clamp(self.y, TOP + 16, BOTTOM - 16)
            self.vy *= -0.25
        # --- tamir ----------------------------------------------------------
        if self.repair:
            part, left, total = self.repair
            left -= dt
            if left <= 0:
                self.parts[part] = True
                self.repair = None
                self.emit("repaired", part=part)
            else:
                self.repair = (part, left, total)
        # --- ateş -----------------------------------------------------------
        if inp.get("fire") and self.laser_cd <= 0 and not self.blackout and self.energy >= D.LASER_COST_E:
            self.laser_cd = 0.22
            self.energy -= D.LASER_COST_E
            self.shots.append([ROCKET_X + 50, self.y, 1300.0])
            self.emit("laser")
        # --- doğurma --------------------------------------------------------
        self.spawn(dt, zone)
        # --- nesneler --------------------------------------------------------
        scroll = 360 * self.speed
        for o in self.objs:
            o.t += dt
            o.x += (o.vx - scroll) * dt
            o.y += o.vy * dt
            o.rot += o.spin * dt
            if o.y < TOP - 60 or o.y > BOTTOM + 60:
                o.vy *= -1
            if o.x < -120:
                o.dead = True
        for s in self.shots:
            s[0] += s[2] * dt
        self.shots = [s for s in self.shots if s[0] < W + 40]
        self.collide()
        self.objs = [o for o in self.objs if not o.dead]
        self.find_threat()
        # --- varış ----------------------------------------------------------
        if self.progress >= self.dist:
            self.arrive()
            return
        if not any(self.parts.values()):
            self.finish("fail", "Tüm sistemler çöktü: araç kontrolden çıktı")

    def spawn(self, dt, zone):
        interval, weights = SPAWN.get(zone, SPAWN["space"])
        interval /= (0.75 + 0.25 * self.pl["diff"])
        interval /= max(0.4, self.speed)
        self.spawn_t -= dt
        if self.spawn_t <= 0 and self.frac < 0.97:
            self.spawn_t = interval * random.uniform(0.6, 1.4)
            kinds = list(weights.keys())
            kind = random.choices(kinds, [weights[k] for k in kinds])[0]
            y = random.uniform(TOP + 30, BOTTOM - 30)
            if kind == "debris":
                self.objs.append(Obj("debris", W + 40, y, random.uniform(-380, -240), random.uniform(-30, 30),
                                     random.uniform(9, 14)))
            elif kind == "big":
                self.objs.append(Obj("big", W + 90, y, random.uniform(-40, 0), random.uniform(-25, 25),
                                     random.uniform(46, 62), hp=4))
            else:
                r = random.uniform(14, 26) if kind != "gold" else random.uniform(18, 26)
                o = Obj("rock" if kind == "ore" else kind, W + 50, y, random.uniform(-110, -10),
                        random.uniform(-45, 45), r, hp=1 if r < 20 else 2)
                o.ore = (kind == "ore")
                self.objs.append(o)
        # asteroit kümeleri: kuşak bölgelerinde kayalar dağınık değil, gruplar halinde gelir
        self.cluster_t -= dt * max(0.4, self.speed)
        if self.cluster_t <= 0 and self.frac < 0.95:
            dense = zone in ("asteroids", "belt")
            self.cluster_t = random.uniform(2.2, 3.8) if dense else random.uniform(9, 16)
            cy = random.uniform(TOP + 90, BOTTOM - 90)
            vx = random.uniform(-90, -30)
            vyc = random.uniform(-20, 20)
            n = random.randint(5, 9) if dense else random.randint(3, 5)
            gold = dense and random.random() < 0.35
            for k in range(n):
                rr = random.uniform(10, 24)
                o = Obj("rock", W + 40 + random.uniform(0, 260), cy + random.gauss(0, 55), vx + random.uniform(-15, 15),
                        vyc + random.uniform(-8, 8), rr, hp=1 if rr < 20 else 2)
                o.ore = random.random() < 0.3
                if gold and k == 0:
                    o.kind, o.r = "gold", 22
                self.objs.append(o)
        # yıldız tozu
        dust_rate = 7.0 if zone == "stardust" else 0.9
        if random.random() < dust_rate * dt:
            self.objs.append(Obj("dust", W + 20, random.uniform(TOP + 20, BOTTOM - 20), random.uniform(-60, 0),
                                 random.uniform(-20, 20), 10))
        # özel nesneler
        self.misc_t -= dt
        if self.misc_t <= 0:
            self.misc_t = random.uniform(6, 11)
            roll = random.random()
            if "camera" in self.payloads and roll < 0.45:
                o = Obj("photo", W + 80, random.uniform(TOP + 60, BOTTOM - 60), -30, 0, 36)
                o.data = random.choice(["Kuyruklu yıldız", "Nebula bulutu", "Uzak galaksi", "Çift yıldız"])
                self.objs.append(o)
                self.photo_ops += 1
                self.emit("tip", kind="photo")
            elif self.sats_left > 0 and roll < 0.75 and self.frac > 0.15:
                self.sats_left -= 1
                self.objs.append(Obj("sat", W + 60, random.uniform(TOP + 60, BOTTOM - 60), -20,
                                     random.uniform(-15, 15), 30))
                self.emit("tip", kind="satellite")
        if not self.station_spawned and self.frac > 0.45 and self.dist > 50:
            self.station_spawned = True
            self.objs.append(Obj("station", W + 120, random.uniform(TOP + 120, BOTTOM - 120), 0, 0, 52))
            self.emit("tip", kind="station")

    def collide(self):
        rx, ry = ROCKET_X, self.y
        for o in self.objs:
            if o.dead:
                continue
            # lazer
            if o.kind in ("rock", "big", "gold", "ice", "debris"):
                for s in self.shots:
                    if abs(s[0] - o.x) < o.r + 8 and abs(s[1] - o.y) < o.r + 6:
                        s[0] = W + 100
                        o.hp -= 1
                        self.emit("hit_obj", x=o.x, y=o.y, kind=o.kind)
                        if o.hp <= 0:
                            self.destroy(o)
                        break
            if o.dead:
                continue
            d = math.hypot(o.x - rx, o.y - ry)
            if o.kind in ("rock", "big", "gold", "ice", "debris"):
                if d < o.r + 20:
                    o.dead = True
                    self.stats["damage"] += 1
                    self.emit("crash", x=o.x, y=o.y, big=o.kind == "big")
                    chance = clamp(0.78 - self.hull["dur"] * 0.15, 0.14, 0.7)
                    if o.kind == "big":
                        chance = 1.0
                    if o.kind == "debris":
                        chance *= 0.6
                    if random.random() < chance:
                        self.damage_random("Çarpışma")
                    if o.kind == "big" and random.random() < 0.5:
                        self.damage_random("Çarpışma")
                    # darbe: momentum aktarımı (küçük kaya hafif, dev kaya sert iter)
                    self.vy += (self.y - o.y) / max(1.0, d) * (o.r ** 2) * 0.9 * 170.0 / self.mass
                    for cid in self.crew:
                        if random.random() < self.injury:
                            self.sickness[cid] = min(100, self.sickness[cid] + 50)
                            self.emit("injury")
            elif o.kind == "dust" and d < 34:
                o.dead = True
                self.stats["stardust"] += 1
                self.emit("pickup", x=o.x, y=o.y, kind="dust")
            elif o.kind == "fuelpick" and d < 34:
                o.dead = True
                add = min(self.fuel_max - self.fuel, 6)
                self.fuel += add
                self.stats["fuel_pick"] += add
                self.emit("pickup", x=o.x, y=o.y, kind="fuel")
            elif o.kind == "ore_pick" and d < 36:
                o.dead = True
                k, n = o.data
                self.stats["minerals"][k] = self.stats["minerals"].get(k, 0) + n
                self.emit("pickup", x=o.x, y=o.y, kind="ore", n=n)
            elif o.kind == "station" and d < 90 and not o.used:
                o.used = True
                add = self.fuel_max - self.fuel
                self.fuel = self.fuel_max
                self.energy = self.e_max
                self.emit("station", add=add)
            elif o.kind == "sat" and d < 60 and not o.used:
                o.used = True
                o.dead = True
                self.stats["rescues"] += 1
                self.emit("rescue", x=o.x, y=o.y)

    def destroy(self, o):
        o.dead = True
        self.stats["asteroids"] += 1
        self.emit("destroy", x=o.x, y=o.y, kind=o.kind, r=o.r)
        mult = 2 if self.miner else 1
        if o.kind == "gold":
            n = random.randint(7, 12) * mult
            self._drop_ore(o, "astro_ore", n)
        elif o.ore:
            n = random.randint(3, 6) * mult
            self._drop_ore(o, "astro_ore", n)
        elif o.kind == "ice":
            p = Obj("fuelpick", o.x, o.y, -40, random.uniform(-20, 20), 12)
            self.objs.append(p)
        elif o.kind == "big":
            for _ in range(3):
                self.objs.append(Obj("rock", o.x, o.y + random.uniform(-30, 30), random.uniform(-60, 60),
                                     random.uniform(-120, 120), random.uniform(12, 16)))

    def _drop_ore(self, o, key, n):
        p = Obj("ore_pick", o.x, o.y, -30, random.uniform(-15, 15), 14)
        p.data = (key, n)
        self.objs.append(p)

    def damage_random(self, cause):
        ok = [k for k, v in self.parts.items() if v and not (self.repair and self.repair[0] == k)]
        if not ok:
            ok = [k for k, v in self.parts.items() if v]
        if not ok:
            return
        p = random.choice(ok)
        self.parts[p] = False
        if self.repair and self.repair[0] == p:
            self.repair = None
        self.emit("broken", part=p, cause=cause)

    def start_repair(self):
        broken = [k for k, v in self.parts.items() if not v]
        if not broken:
            return "Bozuk parça yok"
        if not self.engineer:
            return "Mühendis yok: tamir edilemez"
        if self.repair:
            return "Tamir sürüyor"
        part = broken[0]
        kits = self.g.s["inventory"].get("repair_kit", 0)
        base = 5.0 if kits > 0 else 9.0
        if kits > 0:
            self.g.s["inventory"]["repair_kit"] -= 1
        base /= max(0.3, self.engineer)
        base *= self.repair_k
        if self.g.has_pact("JAXA"):
            base *= 0.7
        self.repair = (part, base, base)
        self.emit("repair_start", part=part, kit=kits > 0)
        return None

    def photo(self):
        if "camera" not in self.payloads:
            return "Kamera Sistemi takılı değil"
        if self.photo_cd > 0:
            return None
        if self.blackout or self.energy < D.PHOTO_COST_E:
            return "Elektrik yetersiz"
        target = None
        for o in self.objs:
            if o.kind == "photo" and not o.used and 200 < o.x < W - 40:
                target = o
                break
        if not target and self.frac > 0.88 and not getattr(self, "_planet_photo", False):
            self._planet_photo = True
            target = "planet"
        if not target:
            return "Fotoğraf fırsatı yok"
        self.photo_cd = 0.8
        self.energy -= D.PHOTO_COST_E
        self.stats["photos"] += 1
        if target != "planet":
            target.used = True
        self.emit("photo", x=(target.x if target != "planet" else W - 200), y=(target.y if target != "planet" else H / 2))
        return None

    def find_threat(self):
        best = None
        for o in self.objs:
            if o.kind in ("rock", "big", "debris") and o.x > ROCKET_X and o.x < ROCKET_X + 600:
                if abs(o.y - self.y) < o.r + 50:
                    if best is None or o.x < best.x:
                        best = o
        self.threat = best

    def arrive(self):
        reasons = []
        outcome = "success"
        if not self.link_ok():
            outcome = "partial"
            reasons.append("Bağlantı yok: veriler Dünya'ya ulaşmadı")
        if not self.parts["antenna"]:
            outcome = "partial"
        if self.heat > 6:
            outcome = "partial"
            reasons.append("Aşırı ısı sensörleri yaktı")
        mode = self.d["mode"]
        landed = False
        if mode in ("inis", "koloni"):
            if self.parts["engine"] and (self.fuel > 0 or self.eng["burn"] == 0):
                landed = True
            else:
                outcome = "partial"
                reasons.append("İniş için motor/yakıt yetersiz: yörüngede kalındı")
        self.landed = landed
        self.finish(outcome, "; ".join(reasons) if reasons else "Hedefe ulaşıldı")

    def finish(self, outcome, reason):
        if self.outcome:
            return
        self.outcome = outcome
        self.reason = reason
        if not hasattr(self, "landed"):
            self.landed = False
        self.emit("finish", outcome=outcome)

    def result(self):
        sick = [cid for cid, v in self.sickness.items() if v > 45]
        minerals = dict(self.stats["minerals"])
        return {
            "planet": self.d["planet"], "mode": self.d["mode"], "outcome": self.outcome, "reason": self.reason,
            "photos": self.stats["photos"], "stardust": self.stats["stardust"], "rescues": self.stats["rescues"],
            "asteroids": self.stats["asteroids"], "minerals": minerals, "crew": self.crew,
            "damage": self.stats["damage"], "landed": self.landed and self.outcome != "fail",
            "radiation": bool(self.eng.get("radiation")), "sick_ids": sick, "fuel_left": self.fuel, "fuel_max": self.fuel_max,
            "elapsed": self.elapsed, "hull": self.hull["key"],
        }


# ===========================================================================
# SAHNE
# ===========================================================================
class FlightScene(Scene):
    music = "space"
    ambient = "amb_space"
    show_topbar = False
    allow_events = False

    def __init__(self, app):
        super().__init__(app)
        self.ps = ParticleSystem(2600)
        self.shake = Shake()
        self.bgs = {}

    def enter(self, **kw):
        m = getattr(self.app, "mission", None)
        if not m:
            self.app.go("base")
            return
        g = self.game
        self.sim = FlightSim(g, m["design"], m["rep"])
        pl = self.sim.pl
        pal = {"moon": "deep", "mars": "ember", "venus": "ember", "jupiter": "violet"}[pl["key"]]
        if pal not in self.bgs:
            self.bgs[pal] = SpaceBackground(pal, 70 + len(self.bgs), 420, 0.9)
        self.bg = self.bgs[pal]
        craft, nozzle = art.render_spacecraft(m["design"]["hull"], m["design"]["engine"], m["design"]["power"],
                                              m["design"]["antenna"], m["design"]["payloads"], g.name, g.color, 0.55)
        self.craft = pygame.transform.rotate(craft, -90)
        cw, ch = craft.get_size()
        # yukarı bakan sprite'ta nozul (nx, ny) -> sağa bakanda
        self.noz_off = (-(nozzle[1] - ch / 2), (nozzle[0] - cw / 2))
        self.ps.clear()
        self.paused = False
        self.map_big = False
        self.end_t = 0.0
        self.flash = 0.0
        self.mouse_active = False
        self.last_mouse = UI.mouse
        self.banner = None
        self.banner_t = 0.0
        self.storm_lead = 0.0
        self.tint = Spring(0.0, 30, 10)
        self.widgets = []
        y = H - 74
        self.btn_slow = self.add(Button((24, y, 150, 54), "YAVAŞLAT", lambda: self.set_throttle(-1), accent=C["cyan"],
                                        size=15, hotkey=pygame.K_a, tooltip="Yakıt biriktir (A)"))
        self.btn_fast = self.add(Button((184, y, 150, 54), "HIZLANDIR", lambda: self.set_throttle(1), accent=C["orange"],
                                        size=15, hotkey=pygame.K_d, tooltip="Çok yakıt yakar (D)"))
        self.btn_rep = self.add(Button((344, y, 170, 54), "TAMİR ET", self.do_repair, accent=C["orange"], icon="wrench",
                                       size=15, hotkey=pygame.K_r, tooltip="Mühendis bozuk parçayı tamir eder (R)"))
        self.btn_nova = self.add(Button((524, y, 190, 54), "NOVA'YA SOR", self.ask_nova, accent=C["cyan"], icon="nova",
                                        size=15, hotkey=pygame.K_n))
        self.btn_photo = self.add(Button((724, y, 170, 54), "FOTOĞRAF", self.do_photo, accent=C["gold"], icon="camera",
                                         size=15, hotkey=pygame.K_f))
        self.btn_photo.visible = "camera" in self.sim.payloads
        self.add(Button((W - 174, y, 150, 54), "DURAKLAT", self.toggle_pause, accent=C["text_dim"], icon="pause",
                        size=14, hotkey=pygame.K_ESCAPE))
        self.pause_buttons = [
            Button((W // 2 - 170, H // 2 - 20, 340, 56), "DEVAM ET", self.toggle_pause, accent=C["green"], size=18,
                   style="big"),
            Button((W // 2 - 170, H // 2 + 50, 340, 50), "GÖREVİ İPTAL ET", self.abort, accent=C["red"], size=16),
        ]
        self.app.say(f"{g.name}, yörüngedeyiz. Hedef {pl['name']}. Fareyle ya da W-S ile yönlendir, "
                     f"SPACE ile lazer at.", "calm")

    # ------------------------------------------------------------- eylemler
    def set_throttle(self, d):
        steps = [0.6, 1.0, 1.45]
        i = min(range(3), key=lambda j: abs(steps[j] - self.sim.throttle))
        i = clamp(i + d, 0, 2)
        self.sim.throttle = steps[i]
        self.app.audio.play("tick")

    def do_repair(self):
        err = self.sim.start_repair()
        if err:
            self.app.toast(err, "red", "warning")
            self.app.audio.play("deny")

    def do_photo(self):
        err = self.sim.photo()
        if err:
            self.app.toast(err, "orange", "camera")

    def ask_nova(self):
        if not self.sim.link_ok():
            self.app.say(self.app.nova.flight_tip({"kind": "nolink"}), "alert")
            return
        s = self.sim
        th = s.threat
        broken = [n for k, n, _ in PARTS if not s.parts[k]]
        if broken:
            self.app.say(self.app.nova.flight_tip({"kind": "broken", "part": broken[0].title()}), "alert")
        elif th:
            self.app.say(self.app.nova.flight_tip({"kind": "big" if th.kind == "big" else "asteroid",
                                                   "dy": 1 if th.y > s.y else -1}), "alert")
        elif s.storm_on:
            self.app.say(self.app.nova.flight_tip({"kind": "storm"}), "alert")
        elif s.fuel < s.fuel_max * 0.25 and s.eng["burn"] > 0:
            self.app.say(self.app.nova.flight_tip({"kind": "fuel"}), "alert")
        else:
            gold = next((o for o in s.objs if o.kind == "gold" and o.x > ROCKET_X), None)
            if gold:
                self.app.say(self.app.nova.flight_tip({"kind": "gold"}))
            else:
                eta = (s.dist - s.progress) / max(0.1, s.speed)
                self.app.say(f"{self.game.name}, rota temiz. {s.pl['name']} varışına yaklaşık {int(eta)} saniye.")

    def toggle_pause(self):
        self.paused = not self.paused
        self.app.audio.play("click")

    def abort(self):
        self.paused = False
        self.sim.finish("fail", "Görev iptal edildi, araç geri çağrıldı")

    # ---------------------------------------------------------------- olay
    def handle(self, e):
        if self.paused:
            for b in self.pause_buttons:
                if b.handle(e):
                    return True
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.toggle_pause()
            return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_TAB:
            self.map_big = not self.map_big
            return True
        if e.type == pygame.MOUSEMOTION:
            if math.dist(e.pos, self.last_mouse) > 3:
                self.mouse_active = True
            self.last_mouse = e.pos
        if super().handle(e):
            return True
        return False

    # -------------------------------------------------------------- güncelle
    def update(self, dt):
        for b in (self.pause_buttons if self.paused else []):
            b.update(dt)
        if self.paused:
            for w in self.widgets:
                w.update(dt)
            return
        super().update(dt)
        s = self.sim
        keys = pygame.key.get_pressed()
        axis = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            axis -= 1
            self.mouse_active = False
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            axis += 1
            self.mouse_active = False
        mouse = pygame.mouse.get_pressed()
        over_ui = UI.mouse[1] > H - 90
        fire = keys[pygame.K_SPACE] or (mouse[0] and not over_ui)
        inp = {"axis": axis, "fire": fire, "mouse_y": UI.mouse[1] if (self.mouse_active and not over_ui) else None}
        s.update(dt, inp)
        self.process_events()
        # efektler
        vx = 360 * s.speed
        self.bg.update(dt, vx * 0.6)
        nx = ROCKET_X + self.noz_off[0]
        ny = s.y + self.noz_off[1]
        power = (s.throttle if s.parts["engine"] and (s.fuel > 0 or s.eng["burn"] == 0) else 0.0)
        if s.eng["key"] == "ion" and s.blackout:
            power = 0
        art.emit_flame(self.ps, nx, ny, s.eng["key"], math.pi, power, 0.8)
        if not s.parts["engine"] and random.random() < 0.4:
            self.ps.smoke(nx + 20, ny, 1, angle=math.pi, spread=0.6, speed=(60, 120), size=(6, 12), life=(0.8, 1.5),
                          color=(90, 90, 100), alpha=140, grow=20, grav=0)
        if s.storm_on and random.random() < 0.6:
            self.ps.glow(W + 10, random.uniform(TOP, BOTTOM), 1, (255, 220, 120), speed=(200, 400), size=(2, 4),
                         life=(1.5, 2.5), drag=0)
            for q in self.ps.p[-1:]:
                q.vx = -random.uniform(500, 900)
                q.vy = random.uniform(-40, 40)
        self.ps.update(dt)
        for q in self.ps.p:
            if q.kind in ("smoke", "shard", "spark"):
                q.x -= vx * dt * 0.7
        self.shake.update(dt)
        self.flash = max(0.0, self.flash - dt * 3)
        self.banner_t = max(0.0, self.banner_t - dt)
        self.tint.target = 1.0 if s.storm_on else 0.0
        self.tint.update(dt)
        if self.storm_lead > 0:
            self.storm_lead -= dt
        if s.outcome:
            self.end_t += dt
            if self.end_t > 2.2:
                self.finish()

    def process_events(self):
        s = self.sim
        a = self.app.audio
        for kind, d in s.events:
            if kind == "laser":
                a.play("laser", 0.35, 0.05)
            elif kind == "hit_obj":
                self.ps.sparks(d["x"], d["y"], 10, (255, 200, 120))
                a.play("hit", 0.3, 0.05)
            elif kind == "destroy":
                ramp = "gold" if d["kind"] == "gold" else "blue" if d["kind"] == "ice" else "fire"
                self.ps.explosion(d["x"], d["y"], 0.5 if d["r"] < 30 else 1.0, ramp)
                col = {"gold": (240, 190, 70), "ice": (180, 225, 255)}.get(d["kind"], (130, 115, 100))
                self.ps.shards(d["x"], d["y"], 12, col)
                a.play("explosion", 0.35, 0.08)
                self.shake.add(0.12)
            elif kind == "crash":
                self.ps.explosion(d["x"], d["y"], 0.8)
                self.shake.add(0.55 if d["big"] else 0.35)
                a.play("hit", 0.9)
                self.flash = 0.5
            elif kind == "broken":
                name = dict((k, n) for k, n, _ in PARTS)[d["part"]]
                self.show_banner(f"{name} BOZULDU! ({d['cause']})", C["red"])
                a.play("alarm", 0.7)
                if s.link_ok():
                    self.app.say(self.app.nova.flight_tip({"kind": "broken", "part": name.title()}), "alert")
            elif kind == "repair_start":
                a.play("repair", 0.7)
                self.show_banner("Mühendis tamire başladı" + (" (Tamir Kiti)" if d["kit"] else " (kitsiz, yavaş)"),
                                 C["orange"])
            elif kind == "repaired":
                a.play("success", 0.5)
                self.show_banner("Parça tamir edildi!", C["green"])
            elif kind == "pickup":
                a.play("pickup", 0.35, 0.04)
                col = {"dust": (150, 220, 255), "fuel": (255, 160, 60), "ore": (255, 200, 90)}[d["kind"]]
                self.ps.glow(d["x"], d["y"], 12, col, speed=(40, 140))
            elif kind == "station":
                a.play("coin", 0.8)
                self.show_banner("Yakıt istasyonu: depo ve batarya dolduruldu!", C["orange"])
            elif kind == "injury":
                self.show_banner("Astronot sarsıldı: kıyafet darbeyi tam karşılayamadı", C["orange"])
            elif kind == "rescue":
                a.play("success", 0.6)
                self.show_banner("Uydu kurtarıldı! +100 Puan", C["cyan"])
                self.ps.ring(d["x"], d["y"], 120, C["cyan"])
            elif kind == "photo":
                a.play("flash", 0.8)
                self.flash = 1.0
                self.show_banner("Fotoğraf çekildi! +20 Puan", C["gold"])
            elif kind == "blackout":
                a.play("alarm", 0.6)
                self.show_banner("ELEKTRİK BİTTİ: ışıklar söndü, radar kapandı", C["red"])
            elif kind == "storm_warn":
                self.storm_lead = d["seconds"]
                a.play("alarm", 0.5)
                self.show_banner(f"GÜNEŞ FIRTINASI {int(d['seconds'])} SN İÇİNDE!", C["gold"])
                if s.link_ok():
                    self.app.say(self.app.nova.flight_tip({"kind": "storm"}), "alert")
            elif kind == "link_lost":
                a.play("deny", 0.6)
                self.show_banner("BAĞLANTI KOPTU: Dünya ile iletişim yok", C["red"])
            elif kind == "tip":
                if s.link_ok():
                    self.app.say(self.app.nova.flight_tip({"kind": d["kind"]}), "alert" if d["kind"] in ("fuel", "o2", "power") else "calm")
            elif kind == "finish":
                if d["outcome"] == "fail":
                    a.play("fail")
                    self.ps.explosion(ROCKET_X, s.y, 1.0) if "Çarp" in s.reason or "çöktü" in s.reason else None
                else:
                    a.play("success", 0.7)
        s.events.clear()
        if s.storm_on and not getattr(self, "_storm_music", False):
            self._storm_music = True
            a.music("storm", 900)
            a.play("storm", 0.6)
        elif not s.storm_on and getattr(self, "_storm_music", False):
            self._storm_music = False
            a.music("space", 1500)

    def show_banner(self, text, color):
        self.banner = (text, color)
        self.banner_t = 2.6

    def finish(self):
        if getattr(self, "_finished", False):
            return
        self._finished = True
        res = self.sim.result()
        self.app.mission["result"] = res
        # yüzeye inen görev: önce oyuncunun yönettiği motorlu iniş (Jüpiter gaz devi: iniş yok)
        from .landing import LANDABLE
        self.app.go("landing" if res["landed"] and res["planet"] in LANDABLE else "results")

    def exit(self):
        self._finished = False
        self._storm_music = False

    # ------------------------------------------------------------------ çizim
    def draw(self, surf):
        s = self.sim
        ox, oy = self.shake.offset(18)
        frame = surf
        self.bg.draw(frame, 1.0, streak=max(0, (s.speed - 1.0) * 30) if s.throttle > 1.2 else 0)
        self.draw_bodies(frame)
        self.draw_zone_fx(frame)
        self.draw_objs(frame, ox, oy)
        # roket
        ry = s.y + oy
        tilt = clamp(-s.vy / 25, -18, 18)
        img = pygame.transform.rotate(self.craft, tilt)
        if not s.blackout:
            art.draw_flame_core(frame, ROCKET_X + self.noz_off[0] + ox, ry + self.noz_off[1], s.eng["key"], math.pi,
                                s.throttle if s.parts["engine"] and (s.fuel > 0 or s.eng["burn"] == 0) else 0, 0.7, self.t)
        self.ps.draw(frame, ox * 0, 0)
        frame.blit(img, (ROCKET_X - img.get_width() // 2 + ox, ry - img.get_height() // 2))
        if not s.blackout:
            draw_glow(frame, (ROCKET_X + 40 + ox, ry), 20, (255, 255, 220), 0.4)
        for sx, sy, _ in s.shots:
            pygame.draw.line(frame, (255, 90, 120), (sx - 30, sy), (sx, sy), 3)
            draw_glow(frame, (sx, sy), 14, (255, 70, 120), 0.9)
        # tonlar
        if self.tint.value > 0.02:
            overlay(frame, (255, 200, 60, int(70 * self.tint.value * (0.8 + 0.2 * math.sin(self.t * 9)))))
        if s.blackout:
            overlay(frame, (0, 0, 0, 170))
        if self.flash > 0:
            overlay(frame, (255, 255, 255, int(200 * self.flash * self.flash)))
        self.draw_hud(frame)
        self.draw_widgets(frame)
        if self.paused:
            self.draw_pause(frame)
        if s.outcome:
            self.draw_end(frame)

    def planet3d(self, surf, key, center, R):
        """Güneş ışığıyla aydınlanan gerçek 3B gezegen (atlas çizicisi); boyut kovalarında önbelleklenir."""
        R = max(6, int(R))
        step = 4 if R < 120 else 12
        rb = max(8, int(round(R / step) * step))
        cache = self.__dict__.setdefault("_p3d", {})
        img = cache.get((key, rb))
        if img is None:
            try:
                th = S3.safe_tex(key, max(256, i18n.quality()["tex"]))
                M = S3.rot_z(math.radians(-12)) @ S3.rot_x(0.28)
                L = S3.norm3(np.array((-0.62, 0.32, 0.72), dtype=np.float32))
                img = S3.to_surface(S3.render_body(key, rb, M, L, 0.8, 0.0, th))
            except Exception:
                img = False
            if len(cache) > 24:
                cache.clear()
            cache[(key, rb)] = img
        if not img:
            art.draw_planet(surf, key, center, R)
            return
        halo = S3.atmo_halo(key, R, (-0.62, 0.32, 0.72))          # gerçekçi atmosfer parlaması (Güneş tarafında)
        if halo:
            surf.blit(halo, (center[0] - halo.get_width() // 2, center[1] - halo.get_height() // 2))
        if rb != R:
            img = pygame.transform.smoothscale(img, (int(img.get_width() * R / rb), int(img.get_height() * R / rb)))
        surf.blit(img, (center[0] - img.get_width() // 2, center[1] - img.get_height() // 2))

    def draw_bodies(self, surf):
        s = self.sim
        f = s.frac
        if f < 0.25:
            k = f / 0.25
            x = int(-80 - k * 500)
            self.planet3d(surf, "earth", (x, H // 2 + 60), 340)
        if f > 0.55:
            k = (f - 0.55) / 0.45
            rad = int(40 + ease_out_cubic(k) * 260)
            x = int(W + 260 - k * 520)
            self.planet3d(surf, s.pl["key"], (x, H // 2), rad)

    def draw_zone_fx(self, surf):
        s = self.sim
        z = s.zone()
        if z == "dark":
            overlay(surf, (0, 0, 10, 110))
        elif z == "heat":
            overlay(surf, (255, 110, 30, 40 + int(20 * math.sin(self.t * 3))))
        elif z == "radiation":
            overlay(surf, (150, 60, 255, 34))
        elif z == "stardust":
            for i in range(6):
                x = (W - (self.t * 120 + i * 300) % (W + 300)) + 150
                draw_glow(surf, (x, H / 2 + math.sin(i * 2 + self.t) * 200), 160, (60, 140, 220), 0.25)

    def draw_objs(self, surf, ox, oy):
        s = self.sim
        spectro = "spectro" in s.payloads and not s.blackout
        for o in s.objs:
            x, y = o.x + ox, o.y + oy
            if o.kind in ("rock", "big", "gold", "ice", "debris"):
                kind = o.kind if not o.ore else "ore"
                spr = art.asteroid_sprite(kind, o.r, o.seed)
                img = pygame.transform.rotate(spr, o.rot)
                if s.blackout:
                    img = img.copy()
                    img.set_alpha(110)
                surf.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
                if o.kind == "gold":
                    draw_glow(surf, (x, y), o.r * 1.6, (255, 200, 80), 0.45 + 0.2 * math.sin(self.t * 5 + o.seed))
                elif o.kind == "ice":
                    draw_glow(surf, (x, y), o.r * 1.4, (120, 200, 255), 0.3)
                if spectro and (o.ore or o.kind == "gold"):
                    for i, col in enumerate(((255, 80, 80), (255, 220, 80), (80, 255, 140), (80, 160, 255))):
                        pygame.draw.circle(surf, col, (int(x), int(y)), int(o.r + 6 + i * 3), 1)
                if o.kind == "big" and o.hp < 4:
                    for i in range(4 - o.hp):
                        pygame.draw.line(surf, (255, 160, 80), (x - o.r * 0.4 + i * 8, y - o.r * 0.3),
                                         (x - o.r * 0.1 + i * 8, y + o.r * 0.4), 2)
            elif o.kind == "dust":
                k = 0.7 + 0.3 * math.sin(self.t * 8 + o.seed)
                draw_glow(surf, (x, y), 16, (150, 220, 255), k)
                pygame.draw.circle(surf, C["white"], (int(x), int(y)), 3)
            elif o.kind == "fuelpick":
                draw_glow(surf, (x, y), 18, (255, 160, 60), 0.9)
                draw_icon(surf, "fuel", (x, y), 16, (255, 230, 180))
            elif o.kind == "ore_pick":
                draw_glow(surf, (x, y), 20, (255, 200, 90), 0.9)
                draw_icon(surf, "pickaxe", (x, y), 16, (255, 240, 200))
            elif o.kind == "station":
                art.draw_fuel_station(surf, x, y, self.t, 1.2)
                if not o.used:
                    draw_text(surf, "YAKIT İSTASYONU", (x, y - 80), 13, C["orange"], bold=True, anchor="midtop")
            elif o.kind == "sat":
                art.draw_satellite(surf, x, y, self.t, 1.0)
                pygame.draw.circle(surf, scale_color(C["cyan"], 0.6 + 0.4 * math.sin(self.t * 6)), (int(x), int(y)), 48, 1)
                draw_text(surf, "KAYIP UYDU", (x, y - 70), 13, C["cyan"], bold=True, anchor="midtop")
            elif o.kind == "photo":
                self.draw_photo_target(surf, o, x, y)

    def draw_photo_target(self, surf, o, x, y):
        name = o.data or ""
        if name == "Kuyruklu yıldız":
            for i in range(14):
                draw_glow(surf, (x + i * 12, y - i * 3), 30 - i * 1.6, (170, 230, 255), 0.6 - i * 0.03)
            draw_glow(surf, (x, y), 22, C["white"], 1.0)
        elif name == "Nebula bulutu":
            for i in range(6):
                draw_glow(surf, (x + math.cos(i) * 30, y + math.sin(i * 1.7) * 24), 50, (200, 80, 220), 0.4)
        elif name == "Uzak galaksi":
            for i in range(30):
                a = i * 0.5
                rr = i * 2
                pygame.draw.circle(surf, (220, 210, 255), (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr * 0.4)), 2)
            draw_glow(surf, (x, y), 40, (220, 200, 255), 0.7)
        else:
            draw_glow(surf, (x - 14, y), 26, (255, 200, 140), 0.9)
            draw_glow(surf, (x + 18, y + 6), 18, (140, 190, 255), 0.9)
        if not o.used:
            k = 0.5 + 0.5 * math.sin(self.t * 6)
            pygame.draw.circle(surf, scale_color(C["gold"], 0.5 + 0.5 * k), (int(x), int(y)), 56, 2)
            draw_text(surf, f"FOTOĞRAF FIRSATI · {name}", (x, y + 64), 12, C["gold"], bold=True, anchor="midtop")

    def draw_hud(self, surf):
        s = self.sim
        g = self.game
        # sol: barlar
        r = pygame.Rect(20, 20, 330, 168 if s.crew else 126)
        glass_panel(surf, r, C["cyan"], 175, 14)
        y = r.y + 34
        draw_bar(surf, (r.x + 40, y, r.w - 60, 12), s.fuel / s.fuel_max, C["orange"], label="YAKIT",
                 value=f"{s.fuel:.0f} kg" if s.eng["burn"] > 0 or s.pwr["kind"] == "fuelcell" else "GEREKMEZ",
                 icon="fuel", warn_below=0.2)
        y += 42
        draw_bar(surf, (r.x + 40, y, r.w - 60, 12), s.energy / s.e_max, C["cyan"], label="ELEKTRİK",
                 value=f"{s.energy:.1f}", icon="bolt", warn_below=0.25)
        y += 42
        if s.crew:
            draw_bar(surf, (r.x + 40, y, r.w - 60, 12), s.o2 / s.o2_max, C["green"], label="OKSİJEN",
                     value=fmt_time(s.o2), icon="o2", warn_below=0.25)
        # parça durumu
        pr = pygame.Rect(20, r.bottom + 12, 330, 96)
        glass_panel(surf, pr, C["orange"], 170, 14)
        draw_text(surf, "PARÇA DURUMU", (pr.x + 16, pr.y + 10), 13, C["text_dim"], bold=True)
        for i, (key, name, icon) in enumerate(PARTS):
            cx = pr.x + 60 + i * 105
            ok = s.parts[key]
            col = C["green"] if ok else C["red"]
            if not ok and int(self.t * 4) % 2 == 0:
                col = scale_color(C["red"], 0.6)
            pygame.draw.circle(surf, scale_color(col, 0.25), (cx, pr.y + 52), 22)
            pygame.draw.circle(surf, col, (cx, pr.y + 52), 22, 2)
            draw_icon(surf, icon, (cx, pr.y + 52), 18, col)
            draw_text(surf, name, (cx, pr.y + 78), 11, col, bold=True, anchor="midtop")
            if s.repair and s.repair[0] == key:
                radial_progress(surf, (cx, pr.y + 52), 28, 1 - s.repair[1] / s.repair[2], C["orange"], 3)
        # mürettebat
        if s.crew:
            cr = pygame.Rect(20, pr.bottom + 12, 330, 74)
            glass_panel(surf, cr, C["violet"], 160, 14, glow=False)
            for i, cid in enumerate(s.crew):
                c = g.crew_by_id(cid)
                if not c:
                    continue
                art.draw_astronaut(surf, cr.x + 40 + i * 100, cr.y + 30, c["type"], 0.62, self.t, c["tired"],
                                   s.sickness.get(cid, 0) > 45)
                draw_text(surf, D.CREW_TYPE[c["type"]]["name"], (cr.x + 62 + i * 100, cr.y + 12), 11, C["text_dim"])
                if "biolab" in s.payloads:
                    hv = 1 - s.sickness.get(cid, 0) / 100
                    draw_bar(surf, (cr.x + 62 + i * 100, cr.y + 34, 40, 6), hv, C["green"] if hv > 0.55 else C["red"],
                             glow=False)
        # görev kontrol mini harita
        self.draw_minimap(surf)
        # sağ üst: hız ve sayaçlar
        rr = pygame.Rect(W - 300, 20, 280, 168)
        glass_panel(surf, rr, C["gold"], 170, 14)
        draw_text(surf, "HIZ", (rr.x + 16, rr.y + 12), 13, C["text_dim"], bold=True)
        draw_text(surf, f"×{s.speed:.2f}", (rr.right - 16, rr.y + 8), 22, C["text"], bold=True, anchor="topright")
        for i, st in enumerate((0.6, 1.0, 1.45)):
            col = C["orange"] if abs(s.throttle - st) < 0.05 else (60, 70, 90)
            pygame.draw.rect(surf, col, (rr.x + 16 + i * 34, rr.y + 40, 28, 8), border_radius=4)
        eta = (s.dist - s.progress) / max(0.05, s.speed)
        draw_text(surf, f"Varış: {fmt_time(eta)}", (rr.right - 16, rr.y + 38), 14, C["text_dim"], anchor="topright")
        st = s.stats
        items = [("pickaxe", st["asteroids"], C["orange"]), ("dust", st["stardust"], C["cyan"]),
                 ("camera", st["photos"], C["gold"]), ("satellite", st["rescues"], C["cyan"]),
                 ("box", sum(st["minerals"].values()), C["gold"])]
        for i, (ic, n, col) in enumerate(items):
            x = rr.x + 30 + (i % 3) * 86
            y = rr.y + 82 + (i // 3) * 40
            draw_icon(surf, ic, (x, y), 18, col)
            draw_text(surf, str(n), (x + 18, y), 18, C["text"], bold=True, anchor="midleft")
        # radar uyarıları
        if not s.blackout:
            for o in s.objs:
                if o.kind in ("rock", "big", "debris") and o.x > W - 10 and o.x < W + 200:
                    k = 1 - (o.x - W) / 200
                    pygame.draw.polygon(surf, scale_color(C["red"], 0.5 + 0.5 * k),
                                        [(W - 30, o.y), (W - 12, o.y - 10), (W - 12, o.y + 10)])
            if s.threat and s.link_ok() and int(self.t * 4) % 2 == 0:
                draw_text(surf, "! ÇARPIŞMA ROTASI", (ROCKET_X + 60, s.y - 60), 13, C["red"], bold=True)
        # fırtına uyarısı
        if self.storm_lead > 0 and not s.storm_on:
            draw_text(surf, f"GÜNEŞ FIRTINASI: {int(self.storm_lead) + 1} SN", (W // 2, 160), 24, C["gold"],
                      bold=True, anchor="midtop", glow=C["gold"])
        if s.storm_on:
            draw_text(surf, "GÜNEŞ FIRTINASI", (W // 2, 160), 26, C["gold"], bold=True, anchor="midtop",
                      glow=C["gold"], alpha=int(180 + 75 * math.sin(self.t * 8)))
        # banner
        if self.banner and self.banner_t > 0:
            text, col = self.banner
            a = int(255 * clamp(self.banner_t / 0.4, 0, 1))
            br = pygame.Rect(0, 0, 700, 50)
            br.midtop = (W // 2, 200)
            glass_panel(surf, br, col, 210, 14, offset_alpha=a)
            draw_text(surf, text, br.center, 19, C["text"], bold=True, anchor="center", alpha=a)
        # kontrol ipucu
        draw_text(surf, "FARE / W-S: yön · SPACE / SOL TIK: lazer · A/D: hız · R: tamir · F: fotoğraf · TAB: harita",
                  (W // 2, H - 98), 12, C["text_mute"], anchor="midtop")
        self.btn_rep.set_enabled(bool(s.engineer), "Mühendis yok")
        self.btn_rep.pulse = any(not v for v in s.parts.values()) and bool(s.engineer)

    def draw_minimap(self, surf):
        s = self.sim
        big = self.map_big
        r = pygame.Rect(W // 2 - (360 if big else 260), 20, 720 if big else 520, 200 if big else 110)
        glass_panel(surf, r, C["magenta"], 190, 14)
        draw_text(surf, f"{self.game.name.upper()} GÖREV KONTROL", (r.x + 16, r.y + 10), 12, C["magenta"], bold=True)
        draw_text(surf, f"{D.PLANET[s.d['planet']]['name'].upper()}", (r.right - 16, r.y + 10), 12, C["text_dim"],
                  bold=True, anchor="topright")
        x0, x1 = r.x + 46, r.right - 46
        ly = r.y + (110 if big else 64)
        for a, b, kind in s.pl["zones"]:
            col = {"asteroids": C["orange"], "belt": C["red"], "dark": (50, 50, 80), "stardust": C["cyan"],
                   "debris": C["steel"], "heat": C["gold"], "radiation": C["violet"]}.get(kind, C["text_dim"])
            pygame.draw.rect(surf, scale_color(col, 0.45), (x0 + (x1 - x0) * a, ly - 7, (x1 - x0) * (b - a), 14),
                             border_radius=5)
        art.draw_planet(surf, "earth", (x0 - 22, ly), 14, glow=False)
        art.draw_planet(surf, s.pl["key"], (x1 + 22, ly), 16, glow=False)
        px = x0 + (x1 - x0) * s.frac
        # bağlantı çizgisi
        if s.link_ok():
            pygame.draw.line(surf, C["green"], (x0 - 22, ly - 22), (px, ly - 4), 2)
            draw_text(surf, "BAĞLANTI", (r.x + 16, r.bottom - 22), 11, C["green"], bold=True)
        else:
            dashed_line(surf, (x0 - 22, ly - 22), (px, ly - 4), C["red"], 8, 6, 2, self.t * 30)
            draw_text(surf, "BAĞLANTI KOPTU", (r.x + 16, r.bottom - 22), 11, C["red"], bold=True)
        pygame.draw.line(surf, C["text_dim"], (x0, ly), (x1, ly), 1)
        draw_glow(surf, (px, ly), 16, C["white"], 0.9)
        pygame.draw.circle(surf, C["white"], (int(px), ly), 5)
        draw_text(surf, i18n.pct(s.frac * 100), (px, ly + 12), 11, C["text"], bold=True, anchor="midtop")
        if big:
            yy = ly + 34
            vals = [("Yakıt", f"{s.fuel:.0f} kg"), ("Elektrik", f"{s.energy:.1f}"),
                    ("Oksijen", fmt_time(s.o2) if s.crew else "-"), ("Süre", fmt_time(s.elapsed))]
            for i, (a, b) in enumerate(vals):
                draw_text(surf, a, (r.x + 30 + i * 170, yy), 12, C["text_dim"])
                draw_text(surf, b, (r.x + 30 + i * 170, yy + 16), 16, C["text"], bold=True)

    def draw_pause(self, surf):
        overlay(surf, (2, 4, 12, 170))
        draw_text(surf, "DURAKLATILDI", (W // 2, H // 2 - 110), 40, C["text"], bold=True, anchor="midtop",
                  glow=C["cyan"])
        for b in self.pause_buttons:
            b.draw(surf)

    def draw_end(self, surf):
        s = self.sim
        k = clamp(self.end_t / 0.6, 0, 1)
        txt = {"success": "HEDEFE ULAŞILDI", "partial": "KISMİ BAŞARI", "fail": "GÖREV BAŞARISIZ"}[s.outcome]
        col = {"success": C["green"], "partial": C["gold"], "fail": C["red"]}[s.outcome]
        overlay(surf, (2, 4, 12, int(140 * k)))
        draw_text(surf, txt, (W // 2, H // 2 - 50), 54, col, bold=True, anchor="center", glow=col, alpha=int(255 * k))
        draw_text(surf, s.reason, (W // 2, H // 2 + 10), 18, C["text"], anchor="center", alpha=int(255 * k))

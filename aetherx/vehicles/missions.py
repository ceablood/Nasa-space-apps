# -*- coding: utf-8 -*-
"""
AETHER-X // SÜRÜŞ GÖREVLERİ
Görevler arazinin gerçek özelliklerinden kurulur (krater merkezi, kayalık alan, göl kıyısı). Her görev hedef
noktalarından oluşur; hedef türleri:
  ulaş   : yarıçap içine gir
  numune : aracı durdur (hız < 0,3 m/s) ve numune al (E) ya da aracın dışında yürüyerek al
  bekle  : noktada belirli süre dur (bilimsel ölçüm)
  yükle  : kargo al (araç kütlesi artar)        teslim : kargoyu bırak
  kurtar : arızalı aracı bağla (kütle + çekme direnci)
Süre sınırı, fırtına (görüş), otopilot zorunluluğu görev özelliğidir. Ödüller oyun varsayımıdır.
"""
import math
import random


class Objective:
    def __init__(self, kind, x, y, label, radius=12.0, hold=0.0, mass=0.0):
        self.kind, self.x, self.y, self.label = kind, x, y, label
        self.radius, self.hold, self.mass = radius, hold, mass
        self.done = False
        self.t = 0.0


class Mission:
    def __init__(self, key, title, desc, objectives, time_limit=None, storm=False, autopilot=False, reward=(300, 120)):
        self.key, self.title, self.desc = key, title, desc
        self.obj = objectives
        self.time_limit = time_limit
        self.storm = storm
        self.autopilot = autopilot
        self.reward = reward
        self.t = 0.0
        self.state = "aktif"      # aktif | başarılı | başarısız
        self.reason = ""
        self.auto_dist = 0.0
        self.cargo = 0.0

    @property
    def current(self):
        for o in self.obj:
            if not o.done:
                return o
        return None

    def update(self, rover, dt, on_foot=None, sample_pressed=False, autopilot_on=False):
        if self.state != "aktif":
            return None
        self.t += dt
        if autopilot_on:
            self.auto_dist += rover.speed * dt
        if self.time_limit and self.t > self.time_limit:
            self.state, self.reason = "başarısız", "Süre doldu"
            return "fail"
        if rover.sunk:
            self.state, self.reason = "başarısız", "Araç metan gölünde battı"
            return "fail"
        if rover.battery <= 0 and rover.speed < 0.05:
            self.state, self.reason = "başarısız", "Batarya bitti"
            return "fail"
        o = self.current
        if o is None:
            return None
        px, py = (on_foot if on_foot else (rover.x, rover.y))
        d = math.hypot(px - o.x, py - o.y)
        msg = None
        if d <= o.radius:
            if o.kind == "ulaş":
                if not self.autopilot or autopilot_on or self.auto_dist > 50:
                    o.done, msg = True, o.label
            elif o.kind == "numune":
                if (on_foot or rover.speed < 0.3) and sample_pressed:
                    o.done, msg = True, o.label
            elif o.kind == "bekle":
                if rover.speed < 0.3:
                    o.t += dt
                    if o.t >= o.hold:
                        o.done, msg = True, o.label
                else:
                    o.t = 0.0
            elif o.kind in ("yükle", "kurtar"):
                if rover.speed < 0.5:
                    rover.extra_mass += o.mass
                    self.cargo += o.mass
                    if o.kind == "kurtar":
                        rover.tow_drag += 120.0
                    o.done, msg = True, o.label
            elif o.kind == "teslim":
                if rover.speed < 0.5:
                    rover.extra_mass = max(0.0, rover.extra_mass - self.cargo)
                    rover.tow_drag = 0.0
                    self.cargo = 0.0
                    o.done, msg = True, o.label
        if self.current is None:
            self.state = "başarılı"
            return "done"
        return msg


def build(planet, terrain, seed=3):
    """Gezegene göre 10 görev. Başlangıç (koloni) harita merkezinde."""
    rng = random.Random(seed)
    c = terrain.size / 2
    home = (c, c)

    def at(dist, ang):
        return c + math.cos(ang) * dist, c + math.sin(ang) * dist

    crater = max(terrain.craters, key=lambda k: k[2]) if terrain.craters else (c + 220, c + 120, 60, 10)
    rocky = max(((x, y) for x, y, r in terrain.rocks[:200]), key=lambda p: sum(1 for x2, y2, r2 in terrain.rocks
                                                                                if math.hypot(x2 - p[0], y2 - p[1]) < 25),
                default=at(180, 2.0)) if len(terrain.rocks) else at(180, 2.0)
    M = []
    a0 = rng.uniform(0, math.tau)
    M.append(Mission("kesif", "Uzun mesafe keşfi", "Üç uzak gözlem noktasına sür ve koloniye dön.",
                     [Objective("ulaş", *at(320, a0), "1. gözlem noktası", 15), Objective("ulaş", *at(420, a0 + 1.5), "2. gözlem noktası", 15),
                      Objective("ulaş", *at(300, a0 + 3.0), "3. gözlem noktası", 15), Objective("ulaş", *home, "Koloniye dönüş", 15)],
                     reward=(500, 200)))
    M.append(Mission("numune", "Bilimsel numune toplama", "Üç farklı zeminden numune al: dur ve E'ye bas (ya da araçtan inip yürüyerek al).",
                     [Objective("numune", *at(120, a0 + 0.5), "Numune 1", 7), Objective("numune", *at(200, a0 + 2.2), "Numune 2", 7),
                      Objective("numune", *at(160, a0 + 4.0), "Numune 3", 7)], reward=(400, 260)))
    M.append(Mission("tasima", "Koloni malzemesi taşıma", "Depodan 400 kg malzeme yükle ve koloniye götür (araç ağırlaşır).",
                     [Objective("yükle", *at(260, a0 + 1.0), "Depoda malzeme yüklendi", 10, mass=400),
                      Objective("teslim", *home, "Malzeme koloniye teslim edildi", 14)], reward=(450, 80)))
    M.append(Mission("kurtarma", "Hasarlı rover kurtarma", "Arızalı keşif robotuna ulaş, çekme halatını bağla ve koloniye çek.",
                     [Objective("kurtar", *at(340, a0 + 2.6), "Robot bağlandı", 10, mass=430),
                      Objective("teslim", *home, "Robot koloniye çekildi", 14)], reward=(550, 150)))
    M.append(Mission("arazi", "Zorlu arazi geçişi", "Kayalık bölgeyi devrilmeden ve ağır hasar almadan geç.",
                     [Objective("ulaş", rocky[0], rocky[1], "Kayalık bölgenin içi", 14),
                      Objective("ulaş", *at(380, math.atan2(rocky[1] - c, rocky[0] - c) + 0.4), "Geçiş tamam", 16)], reward=(420, 120)))
    if planet == "titan" and terrain.lake_level is not None:
        lake = terrain.lake
        import numpy as np
        ys, xs = np.nonzero(lake)
        lx, ly = float(xs.mean() * terrain.cell), float(ys.mean() * terrain.cell)
        M.append(Mission("krater", "Metan gölü kıyı araştırması", "Ligeia Mare benzeri gölün kıyısına in, ölçüm yap; amfibi araçla göle gir.",
                         [Objective("bekle", lx + 70, ly, "Kıyıda ölçüm", 18, hold=6), Objective("ulaş", lx, ly, "Göl yüzeyi", 25)], reward=(600, 320)))
    else:
        cx, cy, cr, cd = crater
        M.append(Mission("krater", "Krater araştırması", "Kraterin tabanına in, ölçüm yap ve kenara geri tırman.",
                         [Objective("ulaş", cx + cr * 1.2, cy, "Krater kenarı", 14), Objective("bekle", cx, cy, "Taban ölçümü", 14, hold=5),
                          Objective("ulaş", cx - cr * 1.25, cy, "Karşı kenara tırmanış", 16)], reward=(520, 300)))
    storm_title = {"mars": "Toz fırtınasında sığınak", "moon": "Güneş parçacık fırtınası: sığınak",
                   "titan": "Metan yağmurunda sığınak"}[planet]
    storm_desc = {"mars": "Toz fırtınası yaklaşıyor, görüş düşüyor: 4 dakika içinde koloniye dön.",
                  "moon": "Güneş parçacık olayı (SPE): radyasyon artmadan 4 dakika içinde sığınağa ulaş.",
                  "titan": "Metan yağmuru ve pus: görüş düşüyor, 4 dakika içinde üsse dön."}[planet]
    M.append(Mission("firtina", storm_title, storm_desc,
                     [Objective("ulaş", *at(250, a0 + 3.3), "Konumdan ayrıl", 18), Objective("ulaş", *home, "Sığınağa ulaşıldı", 15)],
                     time_limit=240, storm=True, reward=(480, 140)))
    M.append(Mission("otonom", "Otonom keşif", "Otopilotu aç (P): araç hedeflere kendisi gider, engellerden kaçar.",
                     [Objective("ulaş", *at(200, a0 + 0.9), "Otonom nokta 1", 15), Objective("ulaş", *at(260, a0 + 1.9), "Otonom nokta 2", 15),
                      Objective("ulaş", *at(180, a0 + 2.9), "Otonom nokta 3", 15)], autopilot=True, reward=(380, 220)))
    M.append(Mission("acil", "Koloniye acil malzeme", "Tıbbi ikmali 3 dakika içinde dış istasyondan koloniye getir.",
                     [Objective("yükle", *at(230, a0 + 5.0), "İkmal alındı", 10, mass=120), Objective("teslim", *home, "İkmal teslim edildi", 14)],
                     time_limit=180, reward=(520, 90)))
    M.append(Mission("bilim", "Bilimsel araştırma noktası", "Sismometre noktasına git ve 8 saniye kıpırdamadan ölçüm al.",
                     [Objective("bekle", *at(290, a0 + 4.4), "Sismik ölçüm", 12, hold=8)], reward=(360, 280)))
    return M


def autopilot(rover, target, terrain):
    """Basit otonom sürüş: hedefe dön (pure pursuit), eğim ve öndeki büyük kayalarda yavaşla/kaçın.
    Döner: Controls benzeri (throttle, brake, steer)."""
    from .physics import Controls
    if target is None:
        return Controls(brake=1.0)
    dx, dy = target.x - rover.x, target.y - rover.y
    want = math.atan2(dy, dx)
    err = (want - rover.yaw + math.pi) % (2 * math.pi) - math.pi
    steer = max(-1.0, min(1.0, -err * 1.8))           # +steer = sağ (saat yönü)
    # engel taraması: önde 18 m içinde şasiyi aşan kaya varsa kaçınma yönüne dön
    fx, fy = math.cos(rover.yaw), math.sin(rover.yaw)
    for rx, ry, rr in terrain.rocks_near(rover.x + fx * 9, rover.y + fy * 9, 10):
        if rr * 0.8 < rover.s.clearance:
            continue
        side = (rx - rover.x) * -fy + (ry - rover.y) * fx
        ahead = (rx - rover.x) * fx + (ry - rover.y) * fy
        if 0 < ahead < 18 and abs(side) < rr + rover.s.track:
            steer = max(-1.0, min(1.0, steer + math.copysign(0.9, side)))   # kaya solda -> sağa kaç
    slope = terrain.slope_deg(rover.x + fx * 4, rover.y + fy * 4)
    dist = math.hypot(dx, dy)
    v_des = rover.s.top_speed * (0.4 if slope > 15 else 0.85) * min(1.0, dist / 20 + 0.3) * (1 - 0.5 * abs(steer))
    v = rover.forward_speed
    return Controls(throttle=max(0.0, min(1.0, (v_des - v) * 1.5)), brake=max(0.0, min(1.0, (v - v_des) * 0.8)), steer=steer)

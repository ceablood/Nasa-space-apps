# -*- coding: utf-8 -*-
"""
AETHER-X // GERÇEKÇİ YÜZEY ARACI FİZİĞİ (Realistic Space Vehicle Driving Engine — yüzey bölümü)

Model (her alt adım 1/120 sn):
  * Gövde: kütle, ağırlık merkezi yüksekliği, eylemsizlik momentleri; yükseklik, yunuslama (pitch), yalpa (roll).
  * Süspansiyon: her tekerlekte yay + sönümleyici; sıkışma tekerleğin altındaki ZEMİN + KAYA yüksekliğinden.
    Normal kuvvetler gövdeyi taşır ve döndürür (yokuşta arka tekerlekler yüklenir, virajda dış tekerlekler).
  * Tekerlek/palet: elektrik motoru (sabit tork, temel hızın üstünde sabit güç), fren, el freni (arka kilit),
    yuvarlanma direnci Crr·N, sürtünme çemberi (boyuna + yanal ≤ μ·N). Gevşek zeminde eğimle artan patinaj
    (C++ çekirdeğindeki slip_ratio eğrisi: Opportunity/Curiosity gözlemleri) etkin tutunmayı düşürür.
  * Eğim: yerçekiminin yüzeye paralel bileşeni; atmosferde aerodinamik sürükleme ½ρCdA·v² (Ay'da yok).
  * Çarpışma: alçak kayaların üstünden geçilir (süspansiyon), şasi açıklığından büyük kayalar çarpar
    (darbe + hasar). Statik devrilme eşiği atan(iz genişliği/2 ÷ ağırlık merkezi yüksekliği).
  * Enerji: motor elektrik gücü = tekerlek mekanik gücü / verim + sabit tüketim; patinajda tekerlek boşa döner
    (aynı ilerleme için 1/(1−s) kat iş). Isı: kayıp güç motoru ısıtır; soğuma ortama (vakumda yalnız ışınım:
    yavaş; Titan'ın yoğun soğuk atmosferi hızlı). Aşırı ısı torku düşürür; hasar ve ısı arıza riskini artırır.

Araç verileri: Apollo LRV (NASA: boş 210 kg, en çok 700 kg yüklü, 4 tekerlek, Ø 81,8 cm, 4 × 0,19 kW,
2 × 36 V 121 Ah gümüş-çinko ≈ 8,7 kWh, ~13 km/h). Diğerleri NASA kavram çalışmaları (LTV, SEV) ve KURGUSAL tasarımlar;
varsayımlar `assumed` alanında açıkça işaretlidir.
"""
import math
import random
from dataclasses import dataclass

from .planets import PLANETS, SURFACES

SUB = 1 / 120.0


@dataclass
class VehicleSpec:
    key: str
    name: str
    mass: float               # kg, yüklü (mürettebat dahil)
    cg_h: float               # m, ağırlık merkezi yüksekliği (zeminden)
    wheelbase: float          # m
    track: float              # m, iz genişliği
    wheels: int               # 4 ya da 6 (palette 2 sanal "palet" x 3 temas)
    wheel_r: float            # m
    motor_kw: float           # toplam en yüksek motor gücü
    torque_n: float           # toplam tekerlek torku (N·m)
    top_speed: float          # m/s
    battery_kwh: float
    hotel_w: float            # sabit tüketim (elektronik, ısıtma)
    solar_w: float
    efficiency: float
    max_steer_deg: float
    clearance: float          # m, şasi yerden yükseklik
    k_spring: float           # N/m (tekerlek başına)
    c_damp: float             # N·s/m
    travel: float             # m, süspansiyon yolu
    cd_area: float            # Cd·A (m²)
    tracked: bool = False
    amphibious: bool = False
    crewed: bool = True
    has_cockpit: bool = True
    note: str = ""
    assumed: str = ""
    color: tuple = (200, 204, 212)


CATALOG = {
    "lrv": VehicleSpec("lrv", "Ay Gezgini (Apollo LRV)", 700, 0.65, 2.29, 1.83, 4, 0.41, 0.76, 330, 3.6, 8.7, 100, 0, 0.55,
                       24, 0.36, 9000, 900, 0.18, 0.8,
                       note="NASA Apollo 15–17 aracı: boş 210 kg, en çok 700 kg yüklü, 4 × 0,19 kW tekerlek motoru, 8,7 kWh.",
                       assumed="süspansiyon yay/sönüm, tork ve ağırlık merkezi yüksekliği oyun varsayımı", color=(196, 170, 96)),
    "ltv": VehicleSpec("ltv", "Artemis Ay Arazi Aracı (LTV)", 1200, 0.75, 2.8, 2.2, 4, 0.5, 6.0, 1500, 4.2, 30, 250, 300, 0.75,
                       28, 0.45, 16000, 1700, 0.25, 1.2,
                       note="NASA Artemis LTV gereksinimi: 2 kişilik basınçsız araç, ~15 km/h.",
                       assumed="kütle, batarya, motor gücü ve süspansiyon kavram düzeyinde oyun varsayımı", color=(222, 226, 232)),
    "sev": VehicleSpec("sev", "Basınçlı Keşif Aracı (NASA SEV)", 3000, 1.2, 3.6, 2.6, 6, 0.55, 18.0, 4200, 2.8, 120, 1500, 2000, 0.7,
                       26, 0.5, 30000, 4200, 0.3, 4.0,
                       note="NASA Space Exploration Vehicle kavramı: kabinli, 12 tekerlekli (burada 6 temas noktası), ~10 km/h.",
                       assumed="batarya, güç ve süspansiyon oyun varsayımı", color=(230, 232, 236)),
    "mars_rover": VehicleSpec("mars_rover", "Mars Basınçlı Gezgini (kurgusal)", 2600, 1.1, 3.4, 2.5, 6, 0.6, 15.0, 3800, 3.0, 90, 900, 1200, 0.72,
                              26, 0.55, 22000, 3000, 0.3, 3.6,
                              note="KURGUSAL tasarım: Mars'ta mürettebatlı uzun menzilli keşif.",
                              assumed="tüm değerler oyun varsayımı", color=(232, 228, 220)),
    "titan_crawler": VehicleSpec("titan_crawler", "Titan Kıyı Keşif Aracı (kurgusal, paletli, amfibi)", 1800, 0.8, 3.0, 2.2, 6, 0.45, 8.0, 3000, 2.2, 60, 600, 0, 0.7,
                                 22, 0.4, 16000, 2600, 0.25, 2.5, tracked=True, amphibious=True,
                                 note="KURGUSAL tasarım: paletli, metan göllerinde yüzebilen, −179 °C için yalıtımlı (RTG ile ısınır).",
                                 assumed="tüm değerler oyun varsayımı; Titan zemin tutunması ölçülmemiştir", color=(214, 140, 60)),
}
VEHICLES_FOR = {"moon": ("lrv", "ltv", "sev"), "mars": ("mars_rover", "sev"), "titan": ("titan_crawler",)}


def _tan(a):
    """Tekerlek konumları yatay düzlemde tanımlı: gövde açısının düşey karşılığı tan(açı) (±80° sınırlı)."""
    return math.tan(max(-1.396, min(1.396, a)))


def slip_curve(slope_deg, looseness):
    """C++ KozmoCore rover::slip_ratio ile aynı: düz zeminde ~%3, gevşek kumda kritik eğim düşer."""
    crit = 28.0 - 14.0 * max(0.0, min(1.0, looseness))
    s = 0.03 + 0.97 * min(1.0, max(0.0, slope_deg) / crit) ** 3
    return max(0.0, min(1.0, s))


@dataclass
class Controls:
    throttle: float = 0.0      # -1 (geri) .. 1
    brake: float = 0.0         # 0..1
    steer: float = 0.0         # -1 sol .. 1 sağ
    handbrake: bool = False
    boost: bool = False        # hız modu (Shift): tork sınırı yükselir, ısınma artar


class Rover:
    def __init__(self, spec, terrain, x=None, y=None, yaw=0.0, seed=1):
        self.s = spec
        self.t = terrain
        self.p = PLANETS[terrain.planet]
        self.g = self.p["g"]
        self.rng = random.Random(seed)
        c = terrain.size / 2
        self.x = c if x is None else x
        self.y = c if y is None else y
        self.yaw = yaw
        self.vx = self.vy = 0.0
        self.r = 0.0
        self.pitch = self.roll = 0.0
        self.wp = self.wr = 0.0
        self.z = terrain.height(self.x, self.y) + spec.cg_h
        self.vz = 0.0
        self.extra_mass = 0.0                    # kargo / çekilen araç
        self.tow_drag = 0.0
        L, T = spec.wheelbase, spec.track
        if spec.wheels == 4:
            self.wpos = [(L / 2, -T / 2), (L / 2, T / 2), (-L / 2, -T / 2), (-L / 2, T / 2)]
        else:
            self.wpos = [(L / 2, -T / 2), (L / 2, T / 2), (0.0, -T / 2), (0.0, T / 2), (-L / 2, -T / 2), (-L / 2, T / 2)]
        n = len(self.wpos)
        self.comp = [0.0] * n
        self.N = [0.0] * n
        self.wheel_ang = [0.0] * n
        self.wheel_slip = [0.0] * n
        self.contact = [True] * n
        self.wheel_fail = [False] * n
        self.battery = spec.battery_kwh
        self.motor_temp = self.p["temp_c"] if self.p["temp_c"] > -60 else -20.0   # RTG/ısıtıcıyla korunur
        self.damage = 0.0
        self.flipped = False
        self.odometer = 0.0
        self.energy_used = 0.0
        self.power_kw = 0.0
        self.last_impact = 0.0
        self.impacts = []
        self.floating = False
        self.sunk = False
        self.lights = False
        self.events = []                         # ("çarpışma", şiddet) / ("devrilme",) / ("arıza", i) ...
        self.steer_ang = 0.0
        self.place()
        self.settle(1.5)

    def place(self):
        """Aracı zemine oturt: gövde eğimi araziye uyar, yaylar yaklaşık statik sıkışmada başlar
        (ilk adımda sönümleyici sıçraması / sahte devrilme olmaz)."""
        s = self.s
        gx, gy = self.t.gradient(self.x, self.y)
        c, sn = math.cos(self.yaw), math.sin(self.yaw)
        fs = gx * c + gy * sn                 # ileri yön eğimi
        ss = -gx * sn + gy * c                # sol yön eğimi
        self.pitch = -math.atan(fs)           # az = z - lx·tan(pitch) + ly·tan(roll) zemine paralel olsun
        self.roll = math.atan(ss)
        self.wp = self.wr = self.vz = 0.0
        hz = s.cg_h - s.wheel_r
        L0 = s.travel * 0.6 + hz
        static = self.mass * self.g / (len(self.wpos) * s.k_spring)
        self.z = self.t.height(self.x, self.y) + s.wheel_r + L0 - static
        for i, (lx, ly) in enumerate(self.wpos):
            wx, wy = self.wheel_world(i)
            az = self.z - lx * _tan(self.pitch) + ly * _tan(self.roll)
            self.comp[i] = L0 - (az - (self.ground(wx, wy) + s.wheel_r))

    # ---------------------------------------------------------------- yardımcılar
    @property
    def mass(self):
        return self.s.mass + self.extra_mass

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    @property
    def forward_speed(self):
        return self.vx * math.cos(self.yaw) + self.vy * math.sin(self.yaw)

    @property
    def tip_angle(self):
        """Statik devrilme açısı (°): yan devrilme iz genişliğine, öne/arkaya devrilme dingil mesafesine göre."""
        return math.degrees(math.atan((self.s.track / 2) / self.s.cg_h))

    def ground(self, x, y):
        """Zemin + tekerleğin altındaki kaya (yarım küre) yüksekliği."""
        h = self.t.height(x, y)
        rk = self.t.rocks_near(x, y, 0.0)
        for rx, ry, rr in rk:
            d = math.hypot(x - rx, y - ry)
            if d < rr:
                h += math.sqrt(max(0.0, rr * rr - d * d)) * 0.8
        return h

    def wheel_world(self, i):
        lx, ly = self.wpos[i]
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return self.x + lx * c - ly * s, self.y + lx * s + ly * c

    def settle(self, seconds):
        for _ in range(int(seconds / SUB)):
            self._step(Controls(brake=1.0), SUB, integrate_planar=False)
        self.events.clear()

    # --------------------------------------------------------------------- adım
    def step(self, ctl, dt):
        n = max(1, int(round(dt / SUB)))
        for _ in range(n):
            self._step(ctl, dt / n)

    def _step(self, ctl, dt, integrate_planar=True):
        s, g, m = self.s, self.g, self.mass
        c, sn = math.cos(self.yaw), math.sin(self.yaw)
        surf = SURFACES[self.t.surface_at(self.x, self.y)]
        liquid = surf.get("liquid", False)
        # --- süspansiyon ve normal kuvvetler
        hz = s.cg_h - s.wheel_r          # tekerlek merkezinden ağırlık merkezine düşey uzaklık (dinlenik)
        L0 = s.travel * 0.6 + hz         # yay serbest boyu (bağlantı noktası = ağırlık merkezi düzlemi)
        Fz = 0.0
        tp = tr = 0.0
        for i, (lx, ly) in enumerate(self.wpos):
            wx, wy = self.wheel_world(i)
            # gövde eğikliği bağlantı noktası yüksekliğini değiştirir
            az = self.z - lx * _tan(self.pitch) + ly * _tan(self.roll)
            gz = self.ground(wx, wy) - (surf["sink"] * 0.5 if not liquid else 0.0)
            length = az - (gz + s.wheel_r)
            comp = L0 - length
            rate = (comp - self.comp[i]) / dt
            self.comp[i] = comp
            if comp <= 0:
                Nf = 0.0
                self.contact[i] = False
            else:
                stiff = s.k_spring * comp + (s.k_spring * 20 * (comp - s.travel) if comp > s.travel else 0.0)
                Nf = max(0.0, stiff + s.c_damp * rate)
                self.contact[i] = True
            self.N[i] = Nf
            Fz += Nf
            tp += -Nf * lx          # burun kalkar: ön tekerlek yükü azalınca
            tr += Nf * ly
        # sıvı (metan gölü): amfibi araç yüzer (kaldırma kuvveti ~ gövde batma), değilse batar
        self.floating = False
        if liquid:
            lake = self.t.lake_level if self.t.lake_level is not None else self.t.height(self.x, self.y)
            depth = lake - (self.z - s.cg_h)
            if depth > 0:
                if s.amphibious:
                    Fz += min(depth, 1.2) * m * g * 1.1
                    self.floating = depth > 0.3
                elif depth > s.wheel_r * 1.6:
                    self.sunk = True
        # --- dikey ve açısal gövde dinamiği
        Ip = m * (s.wheelbase ** 2 + s.cg_h ** 2) / 12 * 1.5
        Ir = m * (s.track ** 2 + s.cg_h ** 2) / 12 * 1.5
        self.vz += (Fz / m - g) * dt
        self.vz *= (1 - 0.6 * dt) if self.floating else 1.0
        self.z += self.vz * dt
        self.wp += (tp / Ip) * dt - self.wp * 2.0 * dt
        self.wr += (tr / Ir) * dt - self.wr * 2.0 * dt
        self.pitch += self.wp * dt
        self.roll += self.wr * dt
        # devrilme
        # yan devrilme ölçütü: gövde yalpası + virajdaki yanal ivmenin eşdeğer açısı (a_lat = v·ω)
        roll_eff = math.degrees(self.roll + math.atan2(self.forward_speed * self.r, g))
        if not self.flipped and (abs(roll_eff) > self.tip_angle or abs(math.degrees(self.pitch)) > 50):
            self.flipped = True
            self.events.append(("devrilme", 1.0))
            self.damage = min(1.0, self.damage + 0.15)
        if self.flipped:
            self.roll += (math.copysign(math.pi * 0.95, self.roll) - self.roll) * min(1.0, dt * 2)
        if not integrate_planar:
            return
        # --- motor, tutunma, fren
        mu = surf["mu"] * (1 - 0.3 * self.damage)
        gx, gy = self.t.gradient(self.x, self.y)
        grade = gx * c + gy * sn                          # ileri yöndeki yokuş (+ tırmanış)
        slip_s = slip_curve(math.degrees(math.atan(max(0.0, grade if self.forward_speed >= 0 else -grade))), surf["loose"])
        mu_eff = mu * (1 - 0.85 * max(0.0, slip_s - 0.03))
        steer_max = math.radians(s.max_steer_deg) * (1 - 0.6 * min(1.0, self.speed / max(0.5, s.top_speed * 1.4)))
        # +steer = sağ = saat yönü (yaw azalır); tekerlek açısı yaw ile aynı işaretli
        self.steer_ang += (-ctl.steer * steer_max - self.steer_ang) * min(1.0, dt * 6)
        derate = 1.0 if self.motor_temp < 110 else max(0.3, 1 - (self.motor_temp - 110) / 60)
        if self.battery <= 0:
            derate = 0.0
        alive = [not f for f in self.wheel_fail]
        driven = max(1, sum(alive))
        vfwd = self.forward_speed
        tq_max = s.torque_n * (1.35 if ctl.boost else 1.0) * derate
        p_max = s.motor_kw * 1000 * (1.35 if ctl.boost else 1.0) * derate
        top = s.top_speed * (1.25 if ctl.boost else 1.0)
        # motor eğrisi: düşük hızda sabit tork, yüksekte sabit güç; en yüksek hızda tork sönümlenir
        F_motor = ctl.throttle * tq_max / s.wheel_r
        if abs(vfwd) > 0.3:
            F_motor = math.copysign(min(abs(F_motor), p_max / abs(vfwd)), F_motor)
        if (vfwd > top and ctl.throttle > 0) or (vfwd < -top * 0.4 and ctl.throttle < 0):
            F_motor = 0.0
        Fx_w = Fy_w = 0.0
        mz = 0.0
        p_mech = 0.0
        nW = len(self.wpos)
        for i, (lx, ly) in enumerate(self.wpos):
            Ni = self.N[i]
            if Ni <= 0:
                self.wheel_slip[i] = 0.0
                continue
            front = lx > 0.1
            delta = self.steer_ang if front else (-self.steer_ang * 0.5 if s.wheels == 6 and lx < -0.1 else 0.0)
            if s.tracked:
                delta = 0.0
            hw = self.yaw + delta
            ch, sh = math.cos(hw), math.sin(hw)
            # temas noktası hızı (gövde dönüşü dahil)
            wx_r, wy_r = lx * c - ly * sn, lx * sn + ly * c
            vcx, vcy = self.vx - self.r * wy_r, self.vy + self.r * wx_r
            v_long = vcx * ch + vcy * sh
            v_lat = -vcx * sh + vcy * ch
            fl = F_motor / driven * (1 if alive[i] else 0)
            if s.tracked:      # paletli: sol/sağ paletin hız farkıyla dönüş (skid steer)
                fl += (ctl.steer * tq_max / s.wheel_r / driven) * (1 if ly > 0 else -1) * 0.8 * (1 if alive[i] else 0)
            brake = ctl.brake * mu_eff * Ni
            if ctl.handbrake and lx < 0:
                brake = mu_eff * Ni * 1.2
            rr = surf["crr"] * Ni * (1.0 + 0.5 * self.damage)
            resist = brake + rr
            # fren ve yuvarlanma direnci hıza karşı koyar (yumuşak işaret: durunca titreşim yok)
            f_long = fl - resist * math.tanh(v_long / 0.05)
            if abs(v_long) < 0.05 and abs(fl) < resist:
                f_long = -v_long / dt * m / nW * 0.5        # duran araç: statik sürtünme yerinde tutar
            lat_mu = mu_eff * (0.45 if ctl.handbrake and lx < 0 else 1.0) * (0.5 if s.tracked else 1.0)
            f_lat = -lat_mu * Ni * math.tanh(v_lat / 0.35)
            if s.tracked:
                f_lat *= 2.0
            # sürtünme çemberi
            lim = mu_eff * Ni
            mag = math.hypot(f_long, f_lat)
            spin = 0.0
            if mag > lim:
                k = lim / mag
                if abs(fl) > lim:
                    spin = min(1.0, (abs(fl) - lim) / max(1e-6, abs(fl)))
                f_long *= k
                f_lat *= k
            against = 1.0 if (abs(fl) > 1 and fl * v_long < 0 and abs(v_long) > 0.05) else 0.0   # tekerlek ileri döner, araç geri kayar
            self.wheel_slip[i] = max(spin, against, slip_s if abs(fl) > 1 else 0.0)
            fx = f_long * ch - f_lat * sh
            fy = f_long * sh + f_lat * ch
            Fx_w += fx
            Fy_w += fy
            mz += wx_r * fy - wy_r * fx
            if fl:
                p_mech += abs(fl * v_long) / max(0.05, 1 - self.wheel_slip[i])
            self.wheel_ang[i] += (v_long / s.wheel_r * (1 + spin * 3)) * dt
        # eğim (yerçekiminin yüzeye paralel bileşeni) ve aerodinamik sürükleme
        contact_k = sum(1 for n_ in self.N if n_ > 0) / nW
        norm = 1 + gx * gx + gy * gy
        Fx_w += -m * g * gx / norm * contact_k
        Fy_w += -m * g * gy / norm * contact_k
        rho = self.p["rho"]
        if rho > 0:
            v = self.speed
            Fx_w -= 0.5 * rho * s.cd_area * v * self.vx
            Fy_w -= 0.5 * rho * s.cd_area * v * self.vy
        if self.tow_drag:
            Fx_w -= self.tow_drag * self.vx
            Fy_w -= self.tow_drag * self.vy
        if self.floating:
            Fx_w -= 400 * self.vx
            Fy_w -= 400 * self.vy
        if self.flipped or self.sunk:
            Fx_w -= m * 2.0 * self.vx
            Fy_w -= m * 2.0 * self.vy
            mz = -self.r * m
        Iz = m * (s.wheelbase ** 2 + s.track ** 2) / 12
        self.vx += Fx_w / m * dt
        self.vy += Fy_w / m * dt
        self.r += mz / Iz * dt
        self.r *= (1 - 0.5 * dt)
        nx, ny = self.x + self.vx * dt, self.y + self.vy * dt
        nx, ny = self._collide(nx, ny, dt)
        self.odometer += math.hypot(nx - self.x, ny - self.y)
        self.x, self.y = nx, ny
        self.yaw += self.r * dt
        # --- enerji, ısı, arıza
        p_mech = min(p_mech, p_max)                       # motor gücü sınırı (patinajda da aşılmaz)
        p_elec = p_mech / s.efficiency + s.hotel_w + (60 if self.lights else 0)
        p_in = s.solar_w * (0.45 if self.t.planet == "mars" else 0.0 if self.t.planet == "titan" else 1.0)
        self.power_kw = p_elec / 1000
        de = (p_elec - p_in) * dt / 3.6e6
        self.battery = max(0.0, min(s.battery_kwh, self.battery - de))
        self.energy_used += max(0.0, de)
        loss = p_mech * (1 / s.efficiency - 1) * (1.6 if ctl.boost else 1.0)
        amb = self.p["temp_c"]
        cool = 2.0 + 30.0 * min(1.0, rho / 1.2) ** 0.5          # vakumda yalnız ışınım: yavaş soğuma
        target_floor = max(amb, -40.0)                              # ısıtıcılar motoru −40 °C üstünde tutar
        self.motor_temp += (loss / (s.mass * 6.0) - cool * (self.motor_temp - target_floor) / 400.0) * dt
        hazard = 2e-5 * (1 + self.damage * 6) * (1 + max(0.0, self.motor_temp - 120) / 10)
        if self.rng.random() < hazard * dt * (1 if abs(ctl.throttle) > 0.1 else 0.1):
            i = self.rng.randrange(nW)
            if not self.wheel_fail[i]:
                self.wheel_fail[i] = True
                self.events.append(("arıza", i))

    def _collide(self, nx, ny, dt):
        s = self.s
        R = 0.5 * math.hypot(s.wheelbase, s.track) * 0.85
        for rx, ry, rr in self.t.rocks_near(nx, ny, R):
            if rr * 0.8 < s.clearance and rr < s.wheel_r * 1.1:
                continue                      # üstünden geçilir (süspansiyon karşılar)
            d = math.hypot(nx - rx, ny - ry)
            if d < R + rr and d > 1e-6:
                ux, uy = (nx - rx) / d, (ny - ry) / d
                vn = self.vx * ux + self.vy * uy
                if vn < 0:
                    e = 0.5 * self.mass * vn * vn
                    self.vx -= 1.25 * vn * ux
                    self.vy -= 1.25 * vn * uy
                    hurt = min(0.5, e / (self.mass * 4.0))
                    self.damage = min(1.0, self.damage + hurt)
                    self.last_impact = abs(vn)
                    self.events.append(("çarpışma", abs(vn)))
                    self.r += (self.rng.random() - 0.5) * abs(vn) * 0.3
                nx, ny = rx + ux * (R + rr), ry + uy * (R + rr)
        return nx, ny

    def recover(self):
        """R: kurtarma — aracı doğrult, yere oturt (enerji ve zaman bedeli)."""
        self.flipped = False
        self.sunk = False
        self.roll = self.pitch = 0.0
        self.wr = self.wp = 0.0
        self.vx = self.vy = self.r = 0.0
        c = self.t.size / 2
        for _ in range(40):        # gölden kıyıya çek (amfibi olmayan araç)
            if self.s.amphibious or self.t.surface_at(self.x, self.y) != "metan gölü":
                break
            self.x += (c - self.x) * 0.1
            self.y += (c - self.y) * 0.1
        gx, gy = self.t.gradient(self.x, self.y)
        if math.hypot(gx, gy) > 0.2:          # eğimde: aracı yokuş yönüne çevir (yan devrilmeyi önler)
            down = math.atan2(-gy, -gx)
            self.yaw = down if math.cos(self.yaw - down) > 0 else down + math.pi
        self.place()
        self.battery = max(0.0, self.battery - self.s.battery_kwh * 0.02)
        self.settle(0.8)

    # ------------------------------------------------------------- gösterge verisi
    def dashboard(self):
        """Kokpit göstergeleri: doğrudan araç durumundan (sahte değer yok)."""
        heading = (90 - math.degrees(self.yaw)) % 360        # 0 = kuzey (+y), 90 = doğu (+x), saat yönünde
        return {
            "hız_kmh": self.speed * 3.6, "ileri_ms": self.forward_speed,
            "motor_c": self.motor_temp, "batarya_yüzde": 100 * self.battery / self.s.battery_kwh,
            "batarya_kwh": self.battery, "güç_kw": self.power_kw, "hasar_yüzde": 100 * self.damage,
            "yön_derece": heading, "yunuslama": math.degrees(self.pitch), "yalpa": math.degrees(self.roll),
            "eğim": self.t.slope_deg(self.x, self.y), "yükseklik_m": self.t.height(self.x, self.y),
            "zemin": self.t.surface_at(self.x, self.y), "patinaj": max(self.wheel_slip) if self.wheel_slip else 0.0,
            "devrildi": self.flipped, "arızalı_tekerlek": [i for i, f in enumerate(self.wheel_fail) if f],
            "kilometre": self.odometer / 1000, "temas": sum(self.contact), "yüzüyor": self.floating, "battı": self.sunk,
        }

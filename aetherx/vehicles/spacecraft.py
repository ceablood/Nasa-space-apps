# -*- coding: utf-8 -*-
"""
AETHER-X // UZAY ARACI DİNAMİĞİ (yüzey aracından ayrı)
  * İtki: F = ṁ·Isp·g0; kütle yakıtla azalır (Tsiolkovsky: Δv = Isp·g0·ln(m0/m1)).
  * Momentum: itki yoksa hız korunur; vakumda (ρ = 0) HİÇBİR sürükleme yoktur.
  * Açısal hareket: tepki kontrol iticileri (RCS) tork uygular, açısal hız birikir; komut bırakılınca
    dönüş SÜRER (sönüm yok), durdurmak için ters itki ya da "dönüşü öldür" (SAS) gerekir.
  * Atmosferde ayrıca aerodinamik sürükleme ½ρCdA·v² hesaplanır.
  * Yörünge hareketi için yerçekimi merkezden r⁻² ile; yüzey yakınında sabit g yaklaşımı seçilebilir.
2B düzlemde (iniş yan görünüşü) çalışır: konum (x, y), hız, açı (rad, 0 = dik), açısal hız.
"""
import math

G0 = 9.80665


class Spacecraft2D:
    def __init__(self, dry_kg, fuel_kg, thrust_n, isp_s, rcs_torque, inertia, cd_area=0.0):
        self.dry, self.fuel = dry_kg, fuel_kg
        self.thrust_max, self.isp = thrust_n, isp_s
        self.rcs_torque, self.inertia = rcs_torque, inertia
        self.cd_area = cd_area
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.ang = 0.0                 # 0 = burun yukarı; + saat yönü (itki +x yönüne eğilir)
        self.omega = 0.0
        self.throttle = 0.0
        self.rcs = 0.0                 # -1..1
        self.sas = False               # dönüşü öldür
        self.fuel_used = 0.0

    @property
    def mass(self):
        return self.dry + self.fuel

    @property
    def delta_v_left(self):
        return self.isp * G0 * math.log(self.mass / self.dry) if self.fuel > 0 else 0.0

    def step(self, dt, g=0.0, rho=0.0, central=None):
        """g: düzgün yerçekimi (m/s², aşağı). central=(GM, cx, cy): merkezî yerçekimi (yörünge)."""
        m = self.mass
        thr = max(0.0, min(1.0, self.throttle)) if self.fuel > 0 else 0.0
        F = thr * self.thrust_max
        mdot = F / (self.isp * G0) if F > 0 else 0.0
        burn = min(self.fuel, mdot * dt)
        if burn < mdot * dt and mdot > 0:
            F *= burn / (mdot * dt)
        self.fuel -= burn
        self.fuel_used += burn
        ax = math.sin(self.ang) * F / m
        ay = math.cos(self.ang) * F / m
        if central:
            GM, cx, cy = central
            dx, dy = self.x - cx, self.y - cy
            r = math.hypot(dx, dy)
            ax -= GM * dx / r ** 3
            ay -= GM * dy / r ** 3
        else:
            ay -= g
        if rho > 0 and self.cd_area > 0:          # yalnız atmosferde
            v = math.hypot(self.vx, self.vy)
            k = 0.5 * rho * self.cd_area * v / m
            ax -= k * self.vx
            ay -= k * self.vy
        self.vx += ax * dt
        self.vy += ay * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # RCS: tork -> açısal ivme; SAS açısal hızı sıfıra çeker (yine RCS gücüyle sınırlı)
        cmd = self.rcs
        if self.sas and abs(cmd) < 0.05:
            cmd = max(-1.0, min(1.0, -self.omega * self.inertia / max(1e-6, self.rcs_torque * dt) * 0.5))
        rcs_fuel = abs(cmd) * self.rcs_torque * 2e-6 * dt
        if self.fuel > rcs_fuel:
            self.fuel -= rcs_fuel
            self.omega += cmd * self.rcs_torque / self.inertia * dt
        self.ang += self.omega * dt

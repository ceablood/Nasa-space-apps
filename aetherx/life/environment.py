# -*- coding: utf-8 -*-
"""
AETHER-X // GEZEGEN ÇEVRE MOTORU (PlanetEnvironmentEngine)

Güneş Sistemi cisimleri: NASA NSSDC bilgi tabloları (nssdc.gsfc.nasa.gov/planetary/factsheet).
  kütle, yarıçap, yerçekimi, dönüş ve yörünge süresi, Güneş'e uzaklık, Güneş ışınımı (W/m²),
  küresel manyetik alan, yüzey basıncı, atmosfer bileşimi (hacimce), ortalama sıcaklık.
Yüzey suyu, buz, iç ısı ve jeolojik etkinlik NASA'nın yayımlanmış bulgularının nitel özetidir
(ör. Mars kutup buzulları, Venüs'te olası güncel volkanizma); sayı değil, sınıf olarak tutulur.

Kurgusal ötegezegenler (okyanus, buz, volkanik...) oyun içindir ve "kurgusal=True" ile işaretlidir;
gerçek keşif gibi sunulmaz.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

AU_KM = 149.6e6
SOLAR_CONST = 1361.0          # W/m², NASA (1 AU)


@dataclass
class PlanetEnvironment:
    key: str
    name: str
    mass_1e24kg: float
    radius_km: float
    gravity: float                     # m/s²
    rotation_h: float                  # eksi: ters yönde dönüş
    orbit_d: float
    sun_dist_au: float
    irradiance: float                  # W/m²
    magnetic_field: bool
    internal_heat: float               # 0..1 (nitel: iç ısı akısı)
    geology: float                     # 0..1 (volkanizma/tektonik etkinlik)
    pressure_bar: float | None         # None: katı yüzey yok
    atmosphere: dict = field(default_factory=dict)     # gaz -> hacimce oran (0..1)
    temp_c: float = 0.0
    temp_range_c: tuple = (0.0, 0.0)
    surface_water: float = 0.0         # 0..1 yüzeyde sıvı su kapsamı
    oceans: bool = False
    ice: float = 0.0                   # 0..1 buz örtüsü
    subsurface_water: bool = False     # yüzey altı sıvı su (kanıtlanmış ya da kurgusal)
    minerals: tuple = ()
    wind_ms: tuple = (0.0, 0.0)
    radiation: float = 0.0             # 0..1 yüzeye ulaşan iyonlaştırıcı ışınım (atmosfer+manyetik alan)
    known_life: bool = False           # NASA: yalnız Dünya'da yaşam bilinir
    kurgusal: bool = False
    source: str = "NASA NSSDC Gezegen Bilgi Tablosu"
    biomes: tuple = ()

    # --- türetilmiş büyüklükler ----------------------------------------------
    @property
    def escape_kms(self):
        G = 6.674e-11
        return math.sqrt(2 * G * self.mass_1e24kg * 1e24 / (self.radius_km * 1e3)) / 1e3

    @property
    def has_surface(self):
        return self.pressure_bar is not None

    @property
    def mean_molar_mass(self):
        """g/mol: atmosfer karışımının ortalama mol kütlesi (ses hızı için)."""
        M = {"N2": 28.01, "O2": 32.0, "Ar": 39.95, "CO2": 44.01, "H2": 2.016, "He": 4.003, "CH4": 16.04,
             "SO2": 64.07, "H2O": 18.02, "CO": 28.01, "Ne": 20.18, "NH3": 17.03}
        tot = sum(self.atmosphere.values()) or 1.0
        return sum(M.get(g, 30.0) * f for g, f in self.atmosphere.items()) / tot

    @property
    def gamma(self):
        """Isı sığası oranı: tek atomlu ~1,67, iki atomlu ~1,40, CO2 ~1,30 (karışım ağırlıklı)."""
        g = {"He": 1.667, "Ar": 1.667, "Ne": 1.667, "N2": 1.40, "O2": 1.40, "H2": 1.41, "CO": 1.40,
             "CO2": 1.30, "CH4": 1.31, "SO2": 1.29, "H2O": 1.33, "NH3": 1.31}
        tot = sum(self.atmosphere.values()) or 1.0
        return sum(g.get(k, 1.35) * f for k, f in self.atmosphere.items()) / tot

    @property
    def speed_of_sound(self):
        """m/s; ideal gaz: c = sqrt(γ R T / M). Atmosfer yoksa 0 (vakumda ses yayılmaz).
        Doğrulama: Dünya 15 °C ~340 m/s; Mars ~240 m/s (Perseverance ölçümü, Maurice ve ark. 2022)."""
        if not self.pressure_bar or self.pressure_bar < 1e-6 or not self.atmosphere:
            return 0.0
        T = self.temp_c + 273.15
        return math.sqrt(self.gamma * 8.314 * T / (self.mean_molar_mass / 1000.0))

    @property
    def density(self):
        """kg/m³ yaklaşık yüzey yoğunluğu (ideal gaz)."""
        if not self.pressure_bar:
            return 0.0
        return self.pressure_bar * 1e5 * self.mean_molar_mass / 1000.0 / (8.314 * (self.temp_c + 273.15))

    def summary(self):
        atm = ", ".join(f"{g} %{v * 100:.1f}".replace(".", ",") for g, v in sorted(self.atmosphere.items(),
                                                                                    key=lambda kv: -kv[1])[:3])
        return {"Yerçekimi": f"{self.gravity:.2f} m/s²", "Basınç": "katı yüzey yok" if self.pressure_bar is None else
                f"{self.pressure_bar:g} bar", "Atmosfer": atm or "yok", "Sıcaklık": f"{self.temp_c:.0f} °C",
                "Işınım": f"{self.irradiance:.0f} W/m²", "Manyetik alan": "var" if self.magnetic_field else "yok",
                "Ses hızı": f"{self.speed_of_sound:.0f} m/s" if self.speed_of_sound else "ses yayılmaz (vakum)"}


def _irr(au):
    return SOLAR_CONST / (au * au)


# --- NASA verisiyle Güneş Sistemi ---------------------------------------------
SOLAR = {
    "earth": PlanetEnvironment(
        "earth", "Dünya", 5.97, 6371.0, 9.80, 23.9, 365.2, 1.0, 1361.0, True, 0.6, 0.7, 1.014,
        {"N2": 0.7808, "O2": 0.2095, "Ar": 0.00934, "CO2": 0.00042}, 15, (-89, 57), 0.71, True, 0.1, True,
        ("silikat", "karbonat", "demir oksit"), (0, 100), 0.02, known_life=True,
        biomes=("tropikal orman", "çöl", "okyanus", "buzul", "volkanik bölge")),
    "moon": PlanetEnvironment(
        "moon", "Ay", 0.073, 1737.4, 1.62, 655.7, 27.3, 1.0, 1361.0, False, 0.05, 0.02, 0.0, {}, -20, (-173, 127),
        0.0, False, 0.01, False, ("anortozit", "bazalt", "ilmenit", "kutup krater buzu"), (0, 0), 1.0,
        source="NASA NSSDC Ay Bilgi Tablosu; kutup buzu: NASA LRO/LCROSS",
        biomes=("regolit ovası", "kalıcı gölgeli krater")),
    "mars": PlanetEnvironment(
        "mars", "Mars", 0.642, 3389.5, 3.71, 24.6, 687.0, 1.524, 586.2, False, 0.15, 0.1, 0.00636,
        {"CO2": 0.951, "N2": 0.0259, "Ar": 0.0194, "O2": 0.0016, "CO": 0.0006}, -59, (-89, -31), 0.0, False, 0.05,
        False, ("bazalt", "demir oksit", "perklorat", "kil"), (2, 30), 0.6,
        source="NASA NSSDC Mars Bilgi Tablosu; kutup buzulları: NASA MRO/Mars Express",
        biomes=("toz ovası", "kutup buzulu", "kanyon")),
    "venus": PlanetEnvironment(
        "venus", "Venüs", 4.87, 6051.8, 8.87, -5832.5, 224.7, 0.723, 2601.3, False, 0.5, 0.6, 92.0,
        {"CO2": 0.965, "N2": 0.035, "SO2": 0.00015}, 464, (462, 466), 0.0, False, 0.0, False,
        ("bazalt", "kükürt bileşikleri"), (0.3, 1.0), 0.0,
        source="NASA NSSDC Venüs Bilgi Tablosu; güncel volkanizma olasılığı: NASA Magellan yeniden analizi (2023)",
        biomes=("volkanik ova", "tessera yayla")),
    "jupiter": PlanetEnvironment(
        "jupiter", "Jüpiter", 1898.0, 69911.0, 24.79, 9.9, 4331.0, 5.204, 50.5, True, 0.8, 0.0, None,
        {"H2": 0.898, "He": 0.102, "CH4": 0.003}, -108, (-161, -108), 0.0, False, 0.0, False, (), (40, 150), 1.0,
        source="NASA NSSDC Jüpiter Bilgi Tablosu (1 bar seviyesi)", biomes=("bulut kuşağı",)),
}

# --- kurgusal ötegezegen şablonları (oyun) -------------------------------------
FICTIONAL = {
    "dunya_benzeri": dict(name="Kepler-X Thalassa (kurgusal)", gravity=10.4, pressure_bar=1.3,
                          atmosphere={"N2": 0.74, "O2": 0.23, "Ar": 0.01, "CO2": 0.02}, temp_c=19, surface_water=0.62,
                          oceans=True, ice=0.08, geology=0.6, magnetic_field=True, radiation=0.03,
                          biomes=("tropikal orman", "çöl", "okyanus", "buzul")),
    "okyanus": dict(name="Aqua-7 (kurgusal okyanus gezegeni)", gravity=11.8, pressure_bar=2.4,
                    atmosphere={"N2": 0.82, "O2": 0.12, "CO2": 0.05, "Ar": 0.01}, temp_c=24, surface_water=0.97,
                    oceans=True, ice=0.0, geology=0.5, magnetic_field=True, radiation=0.02, biomes=("okyanus", "resif")),
    "buz": dict(name="Glacies (kurgusal buz gezegeni)", gravity=7.1, pressure_bar=0.4,
                atmosphere={"N2": 0.9, "CH4": 0.08, "Ar": 0.02}, temp_c=-70, surface_water=0.0, oceans=False, ice=0.95,
                subsurface_water=True, geology=0.35, magnetic_field=False, radiation=0.2, biomes=("buzul", "buz altı okyanusu")),
    "volkanik": dict(name="Ignis Prime (kurgusal volkanik gezegen)", gravity=9.2, pressure_bar=3.0,
                     atmosphere={"CO2": 0.7, "N2": 0.2, "SO2": 0.08, "H2O": 0.02}, temp_c=68, surface_water=0.12,
                     oceans=False, ice=0.0, geology=1.0, magnetic_field=True, radiation=0.05,
                     biomes=("volkanik bölge", "sıcak su kaynakları", "çöl")),
    "kurak": dict(name="Dunea (kurgusal kurak gezegen)", gravity=8.5, pressure_bar=0.7,
                  atmosphere={"N2": 0.7, "CO2": 0.25, "O2": 0.04, "Ar": 0.01}, temp_c=38, surface_water=0.02,
                  oceans=False, ice=0.02, geology=0.3, magnetic_field=True, radiation=0.08, biomes=("çöl", "tuz ovası")),
    "radyasyon": dict(name="Hadron b (kurgusal yüksek radyasyonlu gezegen)", gravity=9.9, pressure_bar=0.2,
                      atmosphere={"CO2": 0.6, "N2": 0.38, "Ar": 0.02}, temp_c=-5, surface_water=0.05, oceans=False,
                      ice=0.3, subsurface_water=True, geology=0.4, magnetic_field=False, radiation=0.9,
                      biomes=("çorak ova", "yer altı mağaraları")),
}


def fictional(kind):
    p = FICTIONAL[kind]
    base = SOLAR["earth"]
    env = replace(base, key=kind, known_life=False, kurgusal=True, source="Kurgusal ötegezegen (oyun)",
                  mass_1e24kg=base.mass_1e24kg * (p["gravity"] / 9.8) ** 1.6, radius_km=base.radius_km * (p["gravity"] / 9.8) ** 0.3,
                  minerals=("silikat", "demir"), temp_range_c=(p["temp_c"] - 30, p["temp_c"] + 25), wind_ms=(1, 40),
                  subsurface_water=p.get("subsurface_water", False), internal_heat=p["geology"] * 0.8)
    for k, v in p.items():
        if k != "subsurface_water":
            setattr(env, k, v)
    env.irradiance = SOLAR_CONST * (1.0 if kind != "buz" else 0.35)
    return env


def get(key):
    if key in SOLAR:
        return replace(SOLAR[key])
    return fictional(key)


ALL_KEYS = tuple(SOLAR) + tuple(FICTIONAL)

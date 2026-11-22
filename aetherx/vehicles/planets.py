# -*- coding: utf-8 -*-
"""
AETHER-X // SÜRÜŞ İÇİN GEZEGEN VE ZEMİN PARAMETRELERİ

Gerçek veriler (NASA):
  Ay    : g 1,62 m/s², atmosfer yok (NSSDC Ay Bilgi Tablosu); gündüz ~+120 °C, gece ~−170 °C.
  Mars  : g 3,71 m/s², 6,36 mb (0,0064 bar), yoğunluk ~0,016 kg/m³, ort. −59 °C, rüzgâr 2–30 m/s (NSSDC Mars).
  Titan : kütle 1345,5×10²⁰ kg, yarıçap 2575 km (NSSDC Satürn uyduları) -> g = GM/r² = 1,354 m/s²;
          yüzey 94 K (−179 °C) ve 1,467 bar (Huygens, ESA/NASA 2005); atmosfer ~%95 N₂, ~%5 CH₄ (Huygens GCMS);
          yoğunluk ~5,4 kg/m³; metan/etan gölleri (Cassini RADAR, ör. Ligeia Mare).
Zemin tutunma (μ) ve yuvarlanma direnci (Crr) katsayıları toprak mekaniği literatürüne dayalı YAKLAŞIK değerlerdir:
  gevşek regolit/kum μ≈0,4–0,5 ve Crr≈0,12–0,2 (Bekker; Apollo LRV ve Mars gezgini deneyimi), kaya μ≈0,8, buz (Titan
  94 K'de çok soğuk su buzu) μ≈0,35 — Titan zemin değerleri ÖLÇÜLMEMİŞTİR, OYUN VARSAYIMIDIR ve arayüzde öyle etiketlenir.
"""

PLANETS = {
    "moon": {"name": "Ay", "g": 1.62, "rho": 0.0, "pressure_bar": 0.0, "temp_c": -20.0, "wind": 0.0,
             "source": "NASA NSSDC Ay Bilgi Tablosu", "sky": ((2, 3, 8), (8, 10, 18)), "fog": None, "sun": (0.55, -0.35, 0.75),
             "surfaces": ("regolit", "kaya", "krater tabanı"), "storm": False},
    "mars": {"name": "Mars", "g": 3.71, "rho": 0.016, "pressure_bar": 0.0064, "temp_c": -59.0, "wind": 7.0,
             "source": "NASA NSSDC Mars Bilgi Tablosu", "sky": ((196, 150, 112), (120, 78, 58)), "fog": (178, 130, 96),
             "sun": (0.5, -0.4, 0.62), "surfaces": ("gevşek kum", "kaya", "regolit", "toz"), "storm": True},
    "titan": {"name": "Titan", "g": 1.354, "rho": 5.4, "pressure_bar": 1.467, "temp_c": -179.0, "wind": 0.7,
              "source": "NASA NSSDC + Cassini-Huygens (yüzey koşulları)", "sky": ((176, 120, 60), (120, 78, 36)),
              "fog": (150, 104, 54), "sun": (0.2, -0.3, 0.9), "surfaces": ("organik kum", "buz kaya", "metan gölü", "ıslak kıyı"),
              "storm": False},
}

# zemin: μ (tepe tutunma), Crr (yuvarlanma direnci), gevşeklik (patinaj eğrisi), batma (m), renk, toz, kaynak
SURFACES = {
    "regolit":      {"mu": 0.55, "crr": 0.12, "loose": 0.5, "sink": 0.01, "color": (128, 126, 122), "dust": (150, 148, 144), "assumed": False},
    "kaya":         {"mu": 0.80, "crr": 0.04, "loose": 0.0, "sink": 0.0, "color": (100, 96, 92), "dust": None, "assumed": False},
    "krater tabanı": {"mu": 0.50, "crr": 0.15, "loose": 0.7, "sink": 0.02, "color": (110, 108, 104), "dust": (140, 138, 134), "assumed": False},
    "gevşek kum":   {"mu": 0.42, "crr": 0.18, "loose": 0.9, "sink": 0.03, "color": (184, 112, 70), "dust": (205, 140, 100), "assumed": False},
    "toz":          {"mu": 0.48, "crr": 0.14, "loose": 0.6, "sink": 0.015, "color": (196, 128, 86), "dust": (215, 150, 110), "assumed": False},
    "organik kum":  {"mu": 0.45, "crr": 0.16, "loose": 0.8, "sink": 0.025, "color": (110, 82, 48), "dust": (140, 104, 62), "assumed": True},
    "buz kaya":     {"mu": 0.35, "crr": 0.03, "loose": 0.0, "sink": 0.0, "color": (150, 140, 120), "dust": None, "assumed": True},
    "ıslak kıyı":   {"mu": 0.30, "crr": 0.22, "loose": 1.0, "sink": 0.06, "color": (80, 62, 40), "dust": None, "assumed": True},
    "metan gölü":   {"mu": 0.05, "crr": 0.40, "loose": 1.0, "sink": 2.0, "color": (34, 28, 26), "dust": None, "assumed": True, "liquid": True},
}
SURFACE_IDS = list(SURFACES)


def surface(name):
    return SURFACES[name]

# -*- coding: utf-8 -*-
"""
AETHER-X // YAŞANABİLİRLİK MOTORU (PlanetHabitabilityEngine)

Yaşanabilirlik = koşulların BİLİNEN yaşama uygunluğu. Yaşamın gerçekten bulunması ayrı bir sorudur:
sonuçta `life_detected` alanı yalnız çevre verisindeki `known_life` bilgisinden gelir (NASA: yalnız Dünya).

Ölçütler (NASA Astrobiyoloji'nin "su, enerji, kimyasal elementler, kararlılık" çerçevesine göre):
  sıvı su (yüzey/yüzey altı) · sıcaklık · basınç/atmosfer · enerji (ışık ya da kimyasal) ·
  gerekli elementler (C, H, N, O, P, S) · iyonlaştırıcı ışınım · çevresel kararlılık.
Puanlar 0..1, eşikler oyun tasarımıdır; gerekçeler oyuncuya gösterilir.
"""
from dataclasses import dataclass, field

CATEGORIES = (
    "Bilinen yaşam açısından elverişli koşullar",
    "Bazı yaşam biçimleri için olası uygun ortam",
    "Aşırı çevresel koşullar",
    "Bilinen yaşam için elverişsiz koşullar",
    "Yetersiz veri",
)


@dataclass
class HabitabilityReport:
    category: str
    score: float
    factors: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    life_detected: bool = False
    niches: list = field(default_factory=list)     # yaşamın olası olduğu alt ortamlar (yüzey altı, buz altı...)


def _band(x, lo_bad, lo_ok, hi_ok, hi_bad):
    """lo_ok..hi_ok arası 1; dışarıda doğrusal düşüş, lo_bad/hi_bad'de 0."""
    if x is None:
        return None
    if lo_ok <= x <= hi_ok:
        return 1.0
    if x < lo_ok:
        return max(0.0, (x - lo_bad) / (lo_ok - lo_bad))
    return max(0.0, (hi_bad - x) / (hi_bad - hi_ok))


def evaluate(env):
    f, why, niches = {}, [], []
    if env.pressure_bar is None:
        return HabitabilityReport(CATEGORIES[3], 0.0, {"yüzey": 0.0},
                                  ["Katı yüzey yok: gaz devinin derinliklerinde basınç ve sıcaklık hızla artar."],
                                  env.known_life, [])
    # su
    water = max(env.surface_water, 0.6 if env.subsurface_water else 0.0, 0.15 if env.ice > 0.2 else 0.0)
    f["sıvı su"] = min(1.0, water * 1.4)
    if env.surface_water > 0.05:
        why.append(f"Yüzeyin %{env.surface_water * 100:.0f}'i sıvı suyla kaplı.")
    elif env.subsurface_water:
        why.append("Yüzey altında sıvı su var ya da olası.")
        niches.append("yüzey altı / buz altı su")
    elif env.ice > 0.2:
        why.append("Su yalnız buz olarak bulunuyor.")
    else:
        why.append("Yüzeyde sıvı su yok.")
    # sıcaklık (bilinen yaşam: ~-20..+122 °C; Dünya'da en sıcak çoğalma 122 °C, Methanopyrus kandleri)
    f["sıcaklık"] = _band(env.temp_c, -40, -15, 60, 122)
    if env.temp_c > 122:
        why.append(f"Ortalama {env.temp_c:.0f} °C: bilinen en dayanıklı canlının sınırı (122 °C) aşılıyor.")
    elif env.temp_c < -40:
        why.append(f"Ortalama {env.temp_c:.0f} °C: yüzeyde sıvı su kalıcı olamaz.")
    # basınç: sıvı su için üçlü nokta 0,006 bar üstü gerekir
    p = env.pressure_bar
    f["atmosfer"] = 0.0 if p < 0.006 else _band(p, 0.006, 0.3, 5, 500)
    if p < 0.006:
        why.append("Basınç suyun üçlü noktasının (0,006 bar) altında: sıvı su yüzeyde kaynar/buharlaşır.")
    # enerji
    light = min(1.0, env.irradiance / 300.0)
    chem = min(1.0, env.geology * 0.9 + env.internal_heat * 0.3)
    f["enerji"] = max(light * (1.0 if p >= 0.006 else 0.6), chem)
    if chem > light:
        niches.append("kimyasal enerji (hidrotermal)")
    # elementler: atmosfer/mineral çeşitliliğinden kaba gösterge
    have = set(env.atmosphere) | {"silikat"} if env.minerals else set(env.atmosphere)
    elem = 0.4 + 0.15 * len({"CO2", "N2", "O2", "H2O", "CH4", "NH3", "SO2"} & have) + (0.1 if env.minerals else 0)
    f["elementler"] = min(1.0, elem)
    # ışınım (atmosfer kalınlığı + manyetik alan kalkanı)
    f["ışınım"] = 1.0 - env.radiation
    if env.radiation > 0.5:
        why.append("Yüzeye ulaşan iyonlaştırıcı ışınım yüksek (ince atmosfer, manyetik alan yok).")
        niches.append("yer altı (ışınım kalkanı)")
    # kararlılık: aşırı jeoloji ve aşırı sıcaklık salınımı düşürür
    swing = abs(env.temp_range_c[1] - env.temp_range_c[0])
    f["kararlılık"] = max(0.0, 1.0 - max(0.0, env.geology - 0.7) * 1.5 - max(0.0, swing - 80) / 250)
    vals = [v for v in f.values() if v is not None]
    if len(vals) < 4:
        return HabitabilityReport(CATEGORIES[4], 0.0, f, why + ["Değerlendirme için veri yetersiz."], env.known_life, niches)
    core = min(f["sıvı su"], f["sıcaklık"] if f["sıcaklık"] is not None else 0, f["atmosfer"])
    score = 0.5 * core + 0.5 * (sum(vals) / len(vals))
    if core >= 0.6 and score >= 0.7 and f["ışınım"] >= 0.5:
        cat = CATEGORIES[0]
    elif niches and score >= 0.3:
        cat = CATEGORIES[1]
    elif score >= 0.35 or (f["sıcaklık"] or 0) < 0.3 and water > 0.1:
        cat = CATEGORIES[2]
    else:
        cat = CATEGORIES[3]
    if env.known_life:
        why.append("Yaşam doğrulanmış (NASA: bilinen tek yaşamlı gezegen).")
    else:
        why.append("Bu cisimde yaşam bulunmamıştır." if not env.kurgusal else "Kurgusal gezegen: yaşam oyunda üretilir.")
    return HabitabilityReport(cat, round(score, 3), f, why, env.known_life, niches)

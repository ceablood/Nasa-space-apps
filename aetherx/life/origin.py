# -*- coding: utf-8 -*-
"""
AETHER-X // YAŞAMIN BAŞLANGICI (LifeOriginEngine)

İki ayrı katalog tutulur:
  HYPOTHESES  : bilimsel literatürde tartışılan hipotezler (kanıtlanmış değildir; "bilimsel hipotez" etiketli)
  FICTIONAL   : oyun için kurgusal senaryolar ("kurgusal" etiketli)

Kimyasal ağ: küçük bir prebiyotik tepkime ağı (CO2/CH4/NH3/H2O/H2 -> HCN, formaldehit -> amino asit,
şeker, nükleotit -> peptit/RNA; yağ asitleri -> zar kesecikleri). Tepkime hızları gezegenin enerji
kaynaklarına (UV, şimşek, hidrotermal) ve suya bağlıdır; "protohücre" eşiğine ulaşma süresi hesaplanır.
Bu bir oyun modelidir; sayılar gerçek kimyasal kinetik değildir.
"""
from __future__ import annotations

import math

HYPOTHESES = [
    {"key": "hydrothermal", "name": "Alkali hidrotermal bacalar", "label": "bilimsel hipotez",
     "needs": {"water": 0.3, "geology": 0.2}, "energy": "kimyasal (H2 + CO2 gradyanı)",
     "text": "Okyanus tabanındaki bacalarda doğal proton gradyanları ilkel metabolizmayı besleyebilir."},
    {"key": "rna_world", "name": "RNA dünyası", "label": "bilimsel hipotez", "needs": {"water": 0.2},
     "energy": "UV / kimyasal", "text": "Hem bilgi taşıyan hem tepkime hızlandıran RNA, DNA ve proteinlerden önce gelmiş olabilir."},
    {"key": "lipid", "name": "Lipit kesecikleri (zar benzeri yapılar)", "label": "bilimsel hipotez",
     "needs": {"water": 0.2}, "energy": "—", "text": "Yağ asitleri suda kendiliğinden kesecik oluşturur; ilkel hücre zarına model olur."},
    {"key": "tidal_pools", "name": "Sığ gölcükler (ıslanma–kuruma döngüsü)", "label": "bilimsel hipotez",
     "needs": {"water": 0.05, "light": 0.3}, "energy": "UV + ıslanma–kuruma",
     "text": "Kara üzerindeki gölcüklerde tekrarlanan kuruma, nükleotitlerin zincirlenmesini kolaylaştırabilir."},
    {"key": "panspermia", "name": "Panspermi", "label": "bilimsel hipotez (kanıtlanmamış)", "needs": {},
     "energy": "—", "text": "Yaşamın tohumları göktaşlarıyla başka bir gökcisminden taşınmış olabilir; köken sorusunu yalnız erteler."},
]

FICTIONAL = [
    {"key": "silicon", "name": "Silisyum tabanlı kristal metabolizma", "label": "kurgusal",
     "needs": {"geology": 0.6}, "energy": "jeotermal", "text": "Oyun senaryosu: sıcak kayaçlarda kendini kopyalayan silikat ağları."},
    {"key": "ammonia", "name": "Amonyak çözücülü biyokimya", "label": "kurgusal (spekülatif)",
     "needs": {"cold": 0.5}, "energy": "kimyasal", "text": "Oyun senaryosu: çok soğuk dünyalarda su yerine sıvı amonyak."},
]

# prebiyotik ağ: ürün -> (girdiler, enerji türü)
NETWORK = {
    "HCN": (("CH4", "NH3"), "şimşek/UV"),
    "formaldehit": (("CO2", "H2"), "UV/hidrotermal"),
    "amino asit": (("HCN", "formaldehit"), "su"),
    "şeker": (("formaldehit",), "mineral katalizi"),
    "nükleotit": (("şeker", "HCN"), "fosfat"),
    "yağ asidi": (("CO2", "H2"), "hidrotermal"),
    "peptit": (("amino asit",), "ıslanma-kuruma"),
    "RNA": (("nükleotit",), "ıslanma-kuruma"),
    "zar kesecikleri": (("yağ asidi",), "su"),
    "protohücre": (("RNA", "zar kesecikleri", "peptit"), "—"),
}


def energy_sources(env):
    light = min(1.0, env.irradiance / 1361.0) * (0.3 if (env.pressure_bar or 0) > 10 else 1.0)
    lightning = min(1.0, (env.pressure_bar or 0) * 0.5) if env.pressure_bar else 0.0
    hydro = min(1.0, env.geology * (1.0 if (env.oceans or env.subsurface_water) else 0.3))
    return {"UV": light, "şimşek": lightning, "hidrotermal": hydro}


def plausible(env, include_fiction=False):
    w = max(env.surface_water, 0.5 if env.subsurface_water else 0.0)
    feats = {"water": w, "geology": env.geology, "light": min(1.0, env.irradiance / 1361.0),
             "cold": 1.0 if env.temp_c < -60 else 0.0}
    out = []
    for h in HYPOTHESES + (FICTIONAL if include_fiction else []):
        ok = all(feats.get(k, 0) >= v for k, v in h["needs"].items())
        out.append({**h, "uygun": ok})
    return out


def simulate_network(env, years=4e9, steps=400):
    """Kaba prebiyotik kinetik: her ürün, girdilerinin en küçüğü x enerji x su ile birikir.
    Döner: (son derişimler, protohücre eşiğine ulaşılan yıl ya da None). Ayar: Dünya ~0,7 milyar yılda eşiğe ulaşır
    (en eski yaşam izleri Dünya oluştuktan ~0,8 milyar yıl sonra)."""
    E = energy_sources(env)
    water = max(env.surface_water, 0.6 if env.subsurface_water else 0.0)
    if env.temp_c > 150 or env.pressure_bar is None:
        water = 0.0
    conc = {"CO2": min(1.0, env.atmosphere.get("CO2", 0) * 5 + 0.2), "CH4": min(1.0, env.atmosphere.get("CH4", 0) * 50 + 0.1),
            "NH3": 0.1 + 0.5 * env.geology, "H2": 0.2 + 0.5 * E["hidrotermal"], "H2O": water}
    for k in NETWORK:
        conc.setdefault(k, 0.0)
    drive = {"şimşek/UV": max(E["şimşek"], E["UV"]), "UV/hidrotermal": max(E["UV"], E["hidrotermal"]),
             "su": water, "mineral katalizi": 0.3 + 0.4 * env.geology, "fosfat": 0.4, "hidrotermal": E["hidrotermal"],
             "ıslanma-kuruma": min(1.0, water * 2) * (0.5 + 0.5 * min(1.0, env.surface_water * 4)), "—": 1.0}
    dt = years / steps
    reached = None
    for i in range(steps):
        for prod, (ins, src) in NETWORK.items():
            rate = min(conc[x] for x in ins) * drive[src] * water * 6e-9
            conc[prod] = min(1.0, conc[prod] + rate * dt - conc[prod] * 1e-9 * dt)
        if reached is None and conc["protohücre"] > 0.05:
            reached = (i + 1) * dt
    return conc, reached

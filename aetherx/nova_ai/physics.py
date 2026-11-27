# -*- coding: utf-8 -*-
"""
NOVA HESAP MOTORU — gerçek yörünge mekaniği ve roket formülleri.
Tüm fonksiyonlar SI birimleriyle çalışır; sonuçlar sohbet için okunur metne çevrilir (engine.py).
Basitleştirmeler açıkça yazılıdır: dairesel ve eş düzlemli yörüngeler, iki cisim problemi.
"""
import math

from .facts import BODIES

G = 6.674e-11                  # m³ kg⁻¹ s⁻²
AU = 1.495978707e11            # m
MU_SUN = 1.32712440018e20      # m³/s²
C_LIGHT = 299792458.0          # m/s
G0 = 9.80665                   # m/s² (standart yerçekimi, Isp dönüşümü)
DAY = 86400.0


def mu(key):
    b = BODIES[key]
    return G * b["mass"] * 1e24


def radius_m(key):
    return BODIES[key]["radius"] * 1000.0


def surface_gravity(key):
    return mu(key) / radius_m(key) ** 2


def escape_velocity(key, alt_km=0.0):
    """Kaçış hızı (m/s): v = sqrt(2μ/r)."""
    return math.sqrt(2 * mu(key) / (radius_m(key) + alt_km * 1000))


def orbital_velocity(key, alt_km):
    """Dairesel yörünge hızı (m/s): v = sqrt(μ/r)."""
    return math.sqrt(mu(key) / (radius_m(key) + alt_km * 1000))


def orbital_period(key, alt_km):
    """Dairesel yörünge periyodu (s): T = 2π sqrt(r³/μ)."""
    r = radius_m(key) + alt_km * 1000
    return 2 * math.pi * math.sqrt(r ** 3 / mu(key))


def low_orbit_alt(key):
    """Makul alçak yörünge yüksekliği (km): atmosferli cisimlerde üstüne çıkılır."""
    return {"earth": 400, "venus": 250, "mars": 250, "titan": 1500, "jupiter": 5000, "saturn": 3000,
            "uranus": 2000, "neptune": 2000, "sun": 1e6}.get(key, 100)


def tsiolkovsky(isp_s, m0, mf):
    """Roket denklemi: Δv = Isp·g0·ln(m0/mf)  (m/s)."""
    if mf <= 0 or m0 <= mf or isp_s <= 0:
        return 0.0
    return isp_s * G0 * math.log(m0 / mf)


def mass_ratio_for(dv, isp_s):
    """İstenen Δv için gerekli kütle oranı m0/mf."""
    return math.exp(dv / (isp_s * G0))


def heliocentric_a(key):
    """Güneş etrafındaki yörünge yarıçapı (m). Uydular için ana gezegeninki."""
    b = BODIES[key]
    k = b.get("parent", key)
    return BODIES[k]["a_au"] * AU


def hohmann(a1, a2, mu_c=MU_SUN):
    """Hohmann transferi: (Δv1, Δv2, uçuş süresi s) — iki dairesel yörünge arası."""
    at = (a1 + a2) / 2
    v1 = math.sqrt(mu_c / a1)
    v2 = math.sqrt(mu_c / a2)
    vp = math.sqrt(mu_c * (2 / a1 - 1 / at))
    va = math.sqrt(mu_c * (2 / a2 - 1 / at))
    t = math.pi * math.sqrt(at ** 3 / mu_c)
    return abs(vp - v1), abs(v2 - va), t


def transfer(src, dst):
    """Gezegenler arası Hohmann (güneş merkezli). Aynı gezegen sistemindeyse None."""
    a1, a2 = heliocentric_a(src), heliocentric_a(dst)
    if abs(a1 - a2) < 1e6:
        return None
    dv1, dv2, t = hohmann(a1, a2)
    return {"dv_depart": dv1, "dv_arrive": dv2, "days": t / DAY, "a1": a1, "a2": a2}


def synodic_days(src, dst):
    """Ardışık fırlatma pencereleri arasındaki süre (gün): 1/|1/T1 − 1/T2|."""
    def period(k):
        b = BODIES[BODIES[k].get("parent", k)] if BODIES[k].get("parent") else BODIES[k]
        return b["year"]
    t1, t2 = period(src), period(dst)
    if not t1 or not t2 or abs(t1 - t2) < 1e-6:
        return None
    return 1.0 / abs(1.0 / t1 - 1.0 / t2)


def distance_range_m(src, dst):
    """Güneş merkezli eş düzlemli dairesel yörüngelerle en yakın / en uzak mesafe (m)."""
    if BODIES[src].get("parent") == dst or BODIES[dst].get("parent") == src:
        k = src if BODIES[src].get("parent") else dst
        d = BODIES[k]["orbit_km"] * 1000.0
        return d, d
    a1, a2 = heliocentric_a(src), heliocentric_a(dst)
    if src == "sun" or dst == "sun":
        d = max(a1, a2)
        return d, d
    return abs(a1 - a2), a1 + a2


def light_delay(src, dst):
    """Işık (radyo) gecikmesi, tek yön (s): (en kısa, en uzun)."""
    lo, hi = distance_range_m(src, dst)
    return lo / C_LIGHT, hi / C_LIGHT


def weight_on(key, mass_kg):
    """mass_kg kütlenin o cisimdeki ağırlığı, Dünya'da tartılan kg cinsinden."""
    return mass_kg * BODIES[key]["g"] / BODIES["earth"]["g"]


def jump_height(key, earth_jump_m=0.5):
    """Aynı sıçrama hızıyla erişilen yükseklik (m), atmosfer ihmal: h ∝ 1/g."""
    return earth_jump_m * BODIES["earth"]["g"] / BODIES[key]["g"]


def solar_flux(key):
    """Güneş ışınımı (W/m²): 1361/a² (AU)."""
    a = heliocentric_a(key) / AU
    return 1361.0 / (a * a) if a > 0 else None


def twr(thrust_n, mass_kg, key="earth"):
    """İtki/ağırlık oranı."""
    return thrust_n / (mass_kg * BODIES[key]["g"])


def burn_time(m0, mf, thrust_n, isp_s):
    """Sabit itkide yakıt yakma süresi (s): ṁ = F/(Isp·g0)."""
    mdot = thrust_n / (isp_s * G0)
    return (m0 - mf) / mdot if mdot > 0 else 0.0


# ----------------------------------------------------------------- okunur biçimler
def fmt_dur(sec, tr_=True):
    if sec < 90:
        return fmt_num(sec, 1, tr_) + (" sn" if tr_ else " s")
    if sec < 5400:
        return fmt_num(sec / 60, 1, tr_) + (" dk" if tr_ else " min")
    if sec < 3 * DAY:
        return fmt_num(sec / 3600, 1, tr_) + (" saat" if tr_ else " h")
    d = sec / DAY
    if d < 800:
        return fmt_num(d, 1 if d < 60 else 0, tr_) + (" gün" if tr_ else " days")
    return fmt_num(d / 365.25, 1, tr_) + (" yıl" if tr_ else " years")


def fmt_dist(m, tr_=True):
    if m < 1e9:
        return fmt_num(m / 1000, 0, tr_) + " km"
    return fmt_num(m / 1e9, 1, tr_) + (" milyon km" if tr_ else " million km")


def fmt_speed(ms, tr_=True):
    if ms >= 1000:
        v = f"{ms / 1000:.2f} km/s"
    else:
        v = f"{ms:.0f} m/s"
    return v.replace(".", ",") if tr_ else v


def fmt_num(x, d=1, tr_=True):
    s = f"{x:,.{d}f}"
    if tr_:
        s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    return s

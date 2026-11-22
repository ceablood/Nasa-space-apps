# -*- coding: utf-8 -*-
"""
AETHER-X // KOZMİK SES MOTORU — SES TASARIMI
  PlanetaryAmbienceEngine · AtmosphericAudioEngine · OceanAudioEngine · GeologicalAudioEngine ·
  FloraAudioEngine · FaunaAudioEngine · MicrobialAudioEngine · EcosystemAudioEngine · WeatherAudioEngine ·
  SpacecraftAudioEngine

Fizik kuralları:
  * Ses maddesel ortamda yayılır. Atmosfersiz yüzeyde (Ay) dış ortam sesi YOKTUR; yalnız giysi/araç içi sesler
    ve yapı yoluyla iletilen titreşimler çalınır. Uzaydaki motor/patlama sesleri "sinematik" etiketlidir.
  * Atmosferde ses hızı ve yüksek frekans sönümü gaz karışımına ve yoğunluğa bağlıdır. Mars'ta (0,006 bar, CO2)
    sesler ~20 dB daha zayıf ve tizler sönük duyulur (Perseverance SuperCam mikrofonu, Maurice ve ark. 2022);
    Venüs'te (92 bar) yoğun atmosfer alçak frekansları güçlü taşır.
  * Canlı sesleri türün biyolojisinden türetilir (rastgele seçilmez): beden boyu -> temel frekans, yaşam alanı ve
    sosyallik -> çağrı biçimi. Mikroorganizmaların duyulabilir ses çıkardığı iddia edilmez; mikrobiyal sesler
    "görsel-işitsel temsil" etiketlidir.
"""
import math
import random

import numpy as np

from . import synth as S

LOOP = 12.0      # ortam döngüsü uzunluğu (sn)


# ---------------------------------------------------------------- atmosfer
def atmosphere_profile(env):
    """Ortamın akustik profili: gain (dB'den doğrusal), tiz kesimi, alçak vurgu, vakum mu."""
    p = env.pressure_bar
    if not p or p < 1e-4 or not env.atmosphere:
        return {"vacuum": True, "gain": 0.0, "hi": 0, "low_boost": 0.0, "speed": 0.0, "label": "vakum: dış ortam sesi yok"}
    rho = env.density
    # algılanan şiddet ~ yoğunlukla (empedans) ölçeklenir; Dünya 1,2 kg/m³ referans. Mars ~0,016 -> ~ -20 dB
    gain = max(0.08, min(1.6, (rho / 1.2) ** 0.5))
    # yüksek frekans sönümü: CO2 ağırlıklı ince atmosfer tizleri yutar (Mars), yoğun atmosfer ise tizleri korur
    co2 = env.atmosphere.get("CO2", 0)
    hi = 12000 if rho > 0.5 else int(2500 + 9000 * min(1.0, rho / 0.5) * (1 - 0.6 * co2))
    low = min(1.0, max(0.0, math.log10(max(rho, 1e-3) / 1.2) * 0.5)) if rho > 1.2 else 0.0
    return {"vacuum": False, "gain": gain, "hi": hi, "low_boost": low, "speed": env.speed_of_sound,
            "label": f"ses hızı {env.speed_of_sound:.0f} m/s · yoğunluk {rho:.3g} kg/m³"}


def wind_layer(env, strength, seed=1):
    prof = atmosphere_profile(env)
    if prof["vacuum"]:
        return np.zeros(S.n_of(LOOP), dtype=S.F32)
    lo = 60 if prof["low_boost"] < 0.3 else 25
    hi = min(prof["hi"], 900 + 1500 * strength)
    base = S.shaped_noise(LOOP, lo, hi, slope=1.4, seed=seed)
    gust = S.smooth_lfo(LOOP, 0.25, seed + 7, 1.0) ** 1.6
    howl = S.shaped_noise(LOOP, 300, 700, slope=0.5, seed=seed + 3) * (gust ** 3) * 0.25 * strength
    out = (base * (0.35 + 0.65 * gust) + howl) * prof["gain"] * (0.25 + 0.75 * strength)
    if prof["low_boost"] > 0:
        out += S.shaped_noise(LOOP, 18, 90, slope=2.0, seed=seed + 9) * prof["low_boost"] * 0.6
    return out.astype(S.F32)


def rain_layer(env, intensity, seed=2):
    prof = atmosphere_profile(env)
    if prof["vacuum"] or intensity <= 0:
        return np.zeros(S.n_of(LOOP), dtype=S.F32)
    bed = S.shaped_noise(LOOP, 400, min(prof["hi"], 6000), slope=0.6, seed=seed) * 0.35
    buf = bed * intensity
    rng = np.random.default_rng(seed)
    drop = S.fft_filter(S.fade_edges(np.random.default_rng(1).uniform(-1, 1, S.n_of(0.012)).astype(S.F32)), 1500, 5000)
    for _ in range(int(600 * intensity)):
        S.place_wrap(buf, drop * rng.uniform(0.05, 0.3), rng.uniform(0, LOOP) * S.SR)
    return (buf * prof["gain"]).astype(S.F32)


def thunder(env, distance_km=3.0, seed=4):
    """Gök gürültüsü: uzaklık arttıkça tizler sönümlenir ve ses gecikir (gecikmeyi çağıran hesaplar)."""
    prof = atmosphere_profile(env)
    if prof["vacuum"]:
        return None
    d = 5.0
    x = S.shaped_noise(d, 20, 2500 / (1 + distance_km * 0.6), slope=1.6, seed=seed)
    env_ = np.exp(-S.t_of(d) / (0.8 + distance_km * 0.25)) * (1 - np.exp(-S.t_of(d) * 30))
    crack = S.shaped_noise(d, 800, 5000, 0.4, seed + 1) * np.exp(-S.t_of(d) * 18) * max(0.0, 1 - distance_km / 2)
    return S.fade_edges(((x * env_ + crack * 0.6) * prof["gain"]).astype(S.F32), 30)


# ----------------------------------------------------------------- okyanus
def ocean_layer(env, wave=0.5, underwater=False, seed=3):
    if underwater:     # su altı: alçak uğultu, kabarcıklar, tizler yok
        buf = S.shaped_noise(LOOP, 20, 350, slope=1.8, seed=seed) * 0.6
        rng = np.random.default_rng(seed)
        for _ in range(40):
            f0 = rng.uniform(300, 900)
            b = S.tone(lambda t, f0=f0: f0 + t * 2500, 0.06) * np.exp(-S.t_of(0.06) / 0.02)
            S.place_wrap(buf, S.fade_edges(b.astype(S.F32)) * rng.uniform(0.05, 0.15), rng.uniform(0, LOOP) * S.SR)
        return buf.astype(S.F32)
    prof = atmosphere_profile(env)
    if prof["vacuum"]:
        return np.zeros(S.n_of(LOOP), dtype=S.F32)
    t = S.t_of(LOOP)
    # dalga periyodu 6 sn (döngüye tam 2 dalga): kabarma + kıyıya çarpma
    swell = (0.5 - 0.5 * np.cos(2 * np.pi * t / 6.0)) ** 3
    surf = S.shaped_noise(LOOP, 120, min(prof["hi"], 3500), slope=1.0, seed=seed) * (0.15 + 0.85 * swell)
    low = S.shaped_noise(LOOP, 25, 160, slope=1.8, seed=seed + 1) * 0.5
    return ((surf * (0.4 + 0.6 * wave) + low) * prof["gain"]).astype(S.F32)


# ------------------------------------------------------------------ jeoloji
def geology_layer(env, activity, seed=5):
    """Sürekli yer altı titreşimi (vakumda bile giysiye zeminden iletilir -> her zaman var, çok alçak)."""
    if activity <= 0.05:
        return np.zeros(S.n_of(LOOP), dtype=S.F32)
    x = S.shaped_noise(LOOP, 15, 110, slope=2.0, seed=seed) * activity
    lava = S.shaped_noise(LOOP, 80, 600, slope=1.2, seed=seed + 2) * S.smooth_lfo(LOOP, 0.6, seed + 3) * 0.3 * activity
    return (x + (lava if not atmosphere_profile(env)["vacuum"] else 0)).astype(S.F32)


def eruption(env, strength=0.7, distance_km=5.0, seed=6):
    d = 6.0
    prof = atmosphere_profile(env)
    g = prof["gain"] if not prof["vacuum"] else 0.35       # vakumda yalnız zeminden gelen titreşim
    hi = 3000 if not prof["vacuum"] else 120
    boom = S.shaped_noise(d, 18, hi / (1 + distance_km * 0.2), slope=1.8, seed=seed)
    e = (1 - np.exp(-S.t_of(d) * 40)) * np.exp(-S.t_of(d) / (1.2 + strength * 1.5))
    rumble = S.shaped_noise(d, 15, 80, 2.0, seed + 1) * np.exp(-S.t_of(d) / 3.5) * 0.6
    return S.fade_edges(((boom * e + rumble) * g * (0.5 + strength)).astype(S.F32), 40)


def impact(env, strength=0.8, seed=7):
    return eruption(env, strength * 1.2, 2.0, seed)


def ice_crack(seed=8):
    d = 0.5
    rng = np.random.default_rng(seed)
    out = np.zeros(S.n_of(d), dtype=S.F32)
    for _ in range(6):
        tt = S.t_of(0.04)
        c = S.shaped_noise(0.04, 1500, 6000, 0.2, int(rng.integers(1e6))) * np.exp(-tt / 0.006) * (1 - np.exp(-tt / 0.0008))
        S.place(out, c.astype(S.F32) * rng.uniform(0.3, 1), rng.uniform(0, d - 0.05) * S.SR)
    out += S.tone(lambda t: 900 - t * 600, d) * np.exp(-S.t_of(d) / 0.12) * 0.25
    return S.fade_edges(out)


# -------------------------------------------------------------------- bitki
def rustle_layer(env, foliage, wind_strength, seed=9):
    """Yaprak hışırtısı yalnız rüzgâr varken ve bitki örtüsüyle orantılı (sürekli gereksiz gürültü yok)."""
    prof = atmosphere_profile(env)
    if prof["vacuum"] or foliage <= 0.02 or wind_strength < 0.15:
        return np.zeros(S.n_of(LOOP), dtype=S.F32)
    gust = S.smooth_lfo(LOOP, 0.4, seed + 1) ** 2
    x = S.shaped_noise(LOOP, 1500, min(prof["hi"], 7000), 0.5, seed) * gust
    return (x * foliage * wind_strength * 0.5 * prof["gain"]).astype(S.F32)


# --------------------------------------------------------------------- fauna
def species_voice(species, kind="çağrı"):
    """Türün biyolojisinden ses: boyut -> temel frekans (büyük beden = alçak), yaşam alanı/sosyallik -> biçim.
    kind: çağrı | alarm | çiftleşme | yavru | sürü"""
    g = species.genome
    seed = sum(map(ord, species.name)) * 31 + {"çağrı": 0, "alarm": 1, "çiftleşme": 2, "yavru": 3, "sürü": 4}.get(kind, 0)
    rng = random.Random(seed)
    f0 = max(70.0, min(7000.0, 900.0 * 10 ** (-0.6 * (g.size + 1.0))))
    if kind == "alarm":
        f0 *= 1.25
    if kind == "yavru":
        f0 *= 1.6
    if g.habitat == "su" and g.size > -1:                 # büyük deniz canlısı: uzun kayan çağrı (balina benzeri)
        d = 2.2 + rng.random()
        out = S.tone(lambda t: f0 * (1 + 0.5 * np.sin(np.pi * t / d)), d, ((1, 1), (2, 0.35), (3, 0.12)), 0.01, 3)
        out *= S.env_adsr(len(out), 0.4, 0.3, 0.8, 0.6)
    elif g.habitat == "hava":                              # kuş benzeri: hızlı cıvıltı dizisi
        n = {"çağrı": 3, "alarm": 6, "çiftleşme": 5, "yavru": 4, "sürü": 2}.get(kind, 3)
        out = np.zeros(S.n_of(0.12 * n + 0.2), dtype=S.F32)
        for i in range(n):
            a, b = f0 * rng.uniform(0.9, 1.3), f0 * rng.uniform(1.4, 2.0)
            c = S.tone(lambda t, a=a, b=b: a + (b - a) * (t / 0.09), 0.09, ((1, 1), (2, 0.2)))
            S.place(out, S.fade_edges(c * S.env_adsr(len(c), 0.005, 0.02, 0.6, 0.03)), i * 0.12 * S.SR)
    elif g.size < -1.8:                                    # böcek benzeri: tırtıklı ötüş (stridulasyon)
        d = 0.6 if kind != "çiftleşme" else 1.2
        t = S.t_of(d)
        pulse = (np.sin(2 * np.pi * (30 + rng.random() * 30) * t) > 0.3).astype(S.F32)
        out = S.tone(f0, d) * pulse * S.env_adsr(len(t), 0.02, 0.05, 0.9, 0.1)
    elif g.size < -0.5:                                    # kurbağa benzeri: vıraklama (darbe dizisi)
        out = np.zeros(S.n_of(0.9), dtype=S.F32)
        for i in range(3 if kind != "alarm" else 6):
            c = S.tone(f0 * 0.9, 0.11, ((1, 1), (3, 0.5), (5, 0.25))) * np.exp(-S.t_of(0.11) / 0.04)
            S.place(out, S.fade_edges(c), i * 0.16 * S.SR)
    else:                                                  # memeli/büyük kara canlısı: ses tellerinden uluma/kükreme
        d = 1.0 + 0.6 * rng.random() + (0.6 if kind == "çiftleşme" else 0)
        shape = (lambda t: f0 * (1 + 0.25 * np.sin(np.pi * t / d))) if g.diet != "etçil" else (lambda t: f0 * (1.2 - 0.3 * t / d))
        out = S.tone(shape, d, ((1, 1), (2, 0.5), (3, 0.3), (4, 0.15)), 0.02, 6)
        if g.diet == "etçil" or kind == "alarm":           # kükreme: soluklu gürültü bileşeni
            out += S.shaped_noise(d, f0 * 0.8, f0 * 6, 0.8, seed) * 0.35
        out *= S.env_adsr(len(out), 0.08, 0.2, 0.7, 0.4)
    if g.social > 0.6 and kind == "sürü":                  # sürü: birkaç bireyin üst üste binen çağrısı
        layered = out.copy()
        for k in range(2):
            S.place(layered, out * 0.6, (0.07 + 0.11 * k) * S.SR)
        out = layered
    return S.fade_edges(S.normalize(out.astype(S.F32), 0.8))


def fauna_layer(env, soundscape, voices, seed=11):
    """Popülasyon tabanlı canlı katmanı: her birey ayrı ses değil; yoğunlukla orantılı sayıda çağrı döngüye dağıtılır."""
    prof = atmosphere_profile(env)
    buf = np.zeros(S.n_of(LOOP), dtype=S.F32)
    if prof["vacuum"]:
        return buf
    rng = np.random.default_rng(seed)
    for group, voice, density in voices:
        n = int(round(density * {"böcek": 14, "kuş": 7, "kurbağa": 6, "memeli": 2, "deniz": 2}.get(group, 3)))
        for _ in range(n):
            S.place_wrap(buf, voice * rng.uniform(0.15, 0.5), rng.uniform(0, LOOP) * S.SR)
    if soundscape.get("böcek", 0) > 0.05:              # sürekli böcek zemini (yoğunlukla)
        t = S.t_of(LOOP)
        hum = S.shaped_noise(LOOP, 3500, min(prof["hi"], 6500), 0.3, seed + 5)
        buf += hum * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t)) * 0.08 * soundscape["böcek"]
    return (S.fft_filter(buf, None, prof["hi"]) * prof["gain"]).astype(S.F32)


# --------------------------------------------------------------- mikrobiyal
def microbial_representation(activity=0.5, seed=12):
    """GÖRSEL-İŞİTSEL TEMSİL: mikroskop/laboratuvar modunda hücresel etkinliği anlatan soyut ses.
    Mikropların duyulabilir ses çıkardığı iddia edilmez."""
    d = 4.0
    rng = np.random.default_rng(seed)
    out = S.shaped_noise(d, 200, 900, 1.2, seed) * 0.15
    for _ in range(int(20 + 60 * activity)):
        f = rng.uniform(600, 1800)
        c = S.tone(f, 0.05, ((1, 1), (2, 0.3))) * np.exp(-S.t_of(0.05) / 0.012)
        S.place(out, S.fade_edges(c.astype(S.F32)) * rng.uniform(0.1, 0.4), rng.uniform(0, d - 0.06) * S.SR)
    return S.fade_edges(S.normalize(out.astype(S.F32), 0.6), 30)


# ------------------------------------------------------------- uzay aracı
def engine_loop(throttle=1.0, vacuum=False, seed=13):
    """Motor sesi: araç İÇİNDEN (yapı yoluyla iletilen uğultu). Dışarıdan dinlenirse vakumda sinematik temsildir."""
    d = 4.0
    base = S.shaped_noise(d, 20, 220 if vacuum else 900, 1.6, seed) * (0.6 + 0.4 * throttle)
    tonal = S.tone(48 + 20 * throttle, d, ((1, 0.25), (2, 0.12), (3, 0.06)))
    return S.normalize((base + tonal).astype(S.F32), 0.7)


def cockpit_hum(seed=14):
    hum = S.tone(60, LOOP, ((1, 0.12), (2, 0.06), (3, 0.03))) + S.shaped_noise(LOOP, 40, 400, 1.5, seed) * 0.3
    rng = np.random.default_rng(seed)
    for _ in range(5):
        b = S.tone(rng.choice((880.0, 1320.0, 990.0)), 0.07) * np.exp(-S.t_of(0.07) / 0.03) * 0.15
        S.place_wrap(hum, S.fade_edges(b.astype(S.F32)), rng.uniform(0, LOOP) * S.SR)
    return hum.astype(S.F32)


def scanner_sweep():
    d = 1.4
    x = S.tone(lambda t: 400 + 1800 * (t / d), d, ((1, 1), (2, 0.2))) * S.env_adsr(S.n_of(d), 0.05, 0.1, 0.6, 0.4)
    return S.fade_edges(S.normalize(x, 0.5))


def landing_gear():
    d = 0.8
    x = S.shaped_noise(d, 60, 1500, 1.0, 21) * np.exp(-S.t_of(d) / 0.12)
    x += S.tone(180, d, ((1, 1), (2.7, 0.4))) * np.exp(-S.t_of(d) / 0.2) * 0.5
    return S.fade_edges(S.normalize(x.astype(S.F32), 0.7))


def discovery_chime(rare=False):
    notes = (72, 76, 79, 84) if not rare else (72, 76, 79, 83, 86, 91)
    d = 0.18 * len(notes) + 1.0
    out = np.zeros(S.n_of(d), dtype=S.F32)
    for i, m in enumerate(notes):
        f = 440 * 2 ** ((m - 69) / 12)
        c = S.tone(f, 1.0, ((1, 1), (2, 0.25), (3, 0.1))) * np.exp(-S.t_of(1.0) / 0.35)
        S.place(out, S.fade_edges(c.astype(S.F32)) * 0.4, i * 0.18 * S.SR)
    return S.normalize(S.reverb(out, 0.3), 0.6)


def report_tone():
    d = 0.9
    x = S.tone(lambda t: 520 - 140 * (t / d), d, ((1, 1), (2, 0.2))) * S.env_adsr(S.n_of(d), 0.05, 0.2, 0.5, 0.4)
    return S.fade_edges(S.normalize(x, 0.45))

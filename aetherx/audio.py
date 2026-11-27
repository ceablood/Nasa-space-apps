# -*- coding: utf-8 -*-
"""
KOZMOGENİS // SES VE MÜZİK
Hiçbir ses dosyası gerekmez: tüm efektler ve müzikler numpy ile prosedürel
olarak sentezlenir.

  Fırlatma  : gürültü + yükselen müzik
  Uzay      : sakin, derin uzay ambiyansı
  Fırtına   : gergin, nabız gibi atan müzik
  Koloni    : neşeli arpej
  NOVA      : yumuşak robot sesi (hece blipleri)
  Buton     : hafif "tık"
  Parça     : metalik "tak"
"""
import math
import random

import pygame

try:
    import numpy as np
    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None
    HAS_NUMPY = False

SR = 44100
# Ses tamponu: 512 örnek (~12 ms) yük altında (özellikle tarayıcıda) boşalıp çatırtı yapıyordu.
# Masaüstü 2048 (~46 ms), tarayıcı 4096 (~93 ms): gecikme hissedilmez, kesilme olmaz.
import sys as _sys
BUFFER = 4096 if _sys.platform == "emscripten" else 2048


# ===========================================================================
# SENTEZ YARDIMCILARI
# ===========================================================================
def _n(dur):
    return int(round(SR * dur))


def _t(dur):
    return np.arange(_n(dur), dtype=np.float32) / SR


def _env(n, a=0.005, d=0.1, s=0.6, r=0.1, dur=None):
    """ADSR zarfı (saniye)."""
    total = n / SR
    a_n = _n(a)
    d_n = _n(d)
    r_n = _n(r)
    s_n = max(0, n - a_n - d_n - r_n)
    parts = [
        np.linspace(0, 1, max(1, a_n), dtype=np.float32),
        np.linspace(1, s, max(1, d_n), dtype=np.float32),
        np.full(s_n, s, dtype=np.float32),
        np.linspace(s, 0, max(1, r_n), dtype=np.float32),
    ]
    e = np.concatenate(parts)
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]


def _exp_decay(n, tau):
    return np.exp(-np.arange(n, dtype=np.float32) / (SR * tau))


def _sine(freq, dur, phase=0.0):
    t = _t(dur)
    if callable(freq):
        f = freq(t)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph + phase).astype(np.float32)
    return np.sin(2 * np.pi * freq * t + phase).astype(np.float32)


def _saw(freq, dur):
    t = _t(dur)
    return (2 * ((t * freq) % 1.0) - 1).astype(np.float32)


def _square(freq, dur, duty=0.5):
    t = _t(dur)
    return np.where((t * freq) % 1.0 < duty, 1.0, -1.0).astype(np.float32)


def _tri(freq, dur):
    t = _t(dur)
    return (2 * np.abs(2 * ((t * freq) % 1.0) - 1) - 1).astype(np.float32)


def _noise(dur, seed=None):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, _n(dur)).astype(np.float32)


def _lowpass(x, k):
    """Basit hareketli ortalama alçak geçiren (k örnek)."""
    k = max(1, int(k))
    if k == 1:
        return x
    ker = np.ones(k, dtype=np.float32) / k
    return np.convolve(x, ker, mode="same").astype(np.float32)


def _highpass(x, k):
    return (x - _lowpass(x, k)).astype(np.float32)


def _mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n, dtype=np.float32)
    for p in parts:
        out[:len(p)] += p
    return out


def _taper(x, a_ms=1.5, r_ms=8.0):
    """Yerleştirilen parçanın başı/sonu yumuşak: sönmemiş bir notanın kesildiği yerde tık oluşmaz."""
    x = np.array(x, dtype=np.float32)
    a, r = min(len(x) // 4, _n(a_ms / 1000)), min(len(x) // 3, _n(r_ms / 1000))
    if a > 1:
        x[:a] *= np.linspace(0, 1, a, dtype=np.float32)
    if r > 1:
        x[-r:] *= np.linspace(1, 0, r, dtype=np.float32)
    return x


def _place(buf, x, start):
    s = int(start)
    if s >= len(buf):
        return
    x = _taper(x)
    e = min(len(buf), s + len(x))
    buf[s:e] += x[:e - s]


def _norm(x, peak=0.9):
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    if m < 1e-6:
        return x
    return (x / m * peak).astype(np.float32)


def _reverb(x, delays=(0.031, 0.047, 0.071, 0.113), decay=0.42):
    out = x.copy()
    for i, d in enumerate(delays):
        n = _n(d)
        g = decay ** (i + 1)
        if n < len(x):
            out[n:] += x[:-n] * g
    return out


_OSC_CACHE = {}


def _memo(fn):
    """Aynı parametreli dalga bir kez üretilir (müzikte tekrar eden notalar): kopya döner."""
    def w(*a):
        k = (fn.__name__,) + tuple(round(v, 4) if isinstance(v, float) else v for v in a)
        v = _OSC_CACHE.get(k)
        if v is None:
            if len(_OSC_CACHE) > 400:
                _OSC_CACHE.clear()
            v = _OSC_CACHE[k] = fn(*a)
        return v.copy()
    return w


@_memo
def _bl_saw(freq, dur, max_h=60):
    """Bant sınırlı testere (toplamsal): Nyquist üstü harmonik yok -> örtüşme (aliasing) kaynaklı sertlik yok."""
    t = _t(dur)
    out = np.zeros_like(t)
    K = int(min(max_h, 15000 // max(1.0, freq)))
    for k in range(1, max(1, K) + 1):
        out += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * freq * t) / k
    return (out * (2 / np.pi)).astype(np.float32)


@_memo
def _bl_square(freq, dur, max_h=40):
    """Bant sınırlı kare (yalnız tek harmonikler, %50 doluluk: DC yok)."""
    t = _t(dur)
    out = np.zeros_like(t)
    K = int(min(max_h, 15000 // max(1.0, freq)))
    for k in range(1, max(1, K) + 1, 2):
        out += np.sin(2 * np.pi * k * freq * t) / k
    return (out * (4 / np.pi)).astype(np.float32)


@_memo
def _bnoise(dur, lo, hi, seed=0, slope=0.0):
    """Bant sınırlı gürültü (frekans uzayında biçimlenir): lo..hi dışında enerji yok -> tıslama/cızırtı yok."""
    from .cae import synth as CS
    n = _n(dur)
    x = CS.shaped_noise(max(dur, 0.01), lo, hi, slope, seed)
    return (x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))).astype(np.float32)


def _fft_band(x, lo=None, hi=None, circular=False):
    """Yumuşak kenarlı bant süzgeci. Döngülerde dairesel (dikiş bozulmaz), tek seferlik seslerde sıfır dolgulu."""
    n = len(x)
    if n < 16 or (not lo and not hi):
        return x
    pad = 0 if circular else min(n, _n(0.25))
    y = np.pad(x, (0, pad)) if pad else x
    N = len(y)
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1.0 / np.sqrt(1.0 + (f / hi) ** 6)
    if lo:
        g *= 1.0 / np.sqrt(1.0 + (lo / np.maximum(f, 1e-3)) ** 4)
    y = np.fft.irfft(X * g, N).astype(np.float32)
    return y[:n]


_IR_CACHE = {}


def _ir(rt, seed=5):
    """Yumuşak, yoğun oda yanıtı: erken yansımalar + üstel sönen bant sınırlı gürültü kuyruğu."""
    key = (round(rt, 2), seed)
    if key not in _IR_CACHE:
        n = _n(rt * 1.2)
        t = np.arange(n, dtype=np.float32) / SR
        tail = _bnoise(rt * 1.2, 120, 6500, seed, 0.6) * np.exp(-6.9 * t / rt)
        tail *= np.clip(t / 0.012, 0, 1)                   # ön gecikme: kuru sesle çakışma yok
        for d, a in ((0.011, 0.5), (0.019, -0.35), (0.029, 0.28), (0.041, -0.2)):
            k = _n(d)
            if k < n:
                tail[k] += a * 8
        _IR_CACHE[key] = (tail / (np.sqrt(np.sum(tail ** 2)) + 1e-9)).astype(np.float32)
    return _IR_CACHE[key]


def _reverb_soft(x, rt=1.1, wet=0.22, circular=False, seed=5):
    """FFT evrişimli yankı (tarak süzgeci yerine): metalik çınlama yok. Döngüde kuyruk başa sarılır."""
    ir = _ir(rt, seed)
    n = len(x)
    if circular:
        # doğrusal evrişim (2'nin kuvveti uzunlukta, hızlı) + taşan kuyruğu başa katla = dairesel evrişim
        ir = ir[:n]
        N = 1 << int(np.ceil(np.log2(n + len(ir))))
        full = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n + len(ir) - 1]
        y = full[:n].copy()
        y[:len(full) - n] += full[n:]
        y = y.astype(np.float32)
    else:
        N = 1 << int(np.ceil(np.log2(n + len(ir))))
        y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n + len(ir) - 1].astype(np.float32)
        x = np.pad(x, (0, len(y) - n))
    dry_rms = float(np.sqrt(np.mean(x ** 2))) + 1e-9
    wet_rms = float(np.sqrt(np.mean(y ** 2))) + 1e-9
    return (x + y * (wet * dry_rms / wet_rms)).astype(np.float32)


MASTER = 0.8          # karıştırma payı: aynı anda çalan kanallar toplandığında kırpılma (çatırtı) olmaz


def finish(x, loop=False):
    """Bütün seslerin son işleme zinciri:
    DC ve 25 Hz altı uğultu temizlenir, 14 kHz üstü tıslama yumuşakça kesilir, tek seferlik seslerde başta 3 ms /
    sonda 25 ms geçiş (tık yok), tepe 0,95'i aşarsa yalnız ölçeklenir (tanh doyumu / bozulma yok)."""
    x = np.asarray(x, dtype=np.float32)
    if len(x) < 16:
        return x
    x = x - float(np.mean(x))
    x = _fft_band(x, 25, 14000, circular=loop)
    if not loop:
        a, r = min(len(x) // 4, _n(0.003)), min(len(x) // 3, _n(0.025))
        if a > 1:
            x[:a] *= np.linspace(0, 1, a, dtype=np.float32)
        if r > 1:
            x[-r:] *= np.linspace(1, 0, r, dtype=np.float32) ** 2
    m = float(np.max(np.abs(x)))
    if m > 0.95:
        x = x * (0.95 / m)
    return x.astype(np.float32)


def note_freq(n):
    """MIDI nota -> Hz"""
    return 440.0 * (2 ** ((n - 69) / 12.0))


# ===========================================================================
# EFEKTLER
# ===========================================================================
def sfx_click():
    """Yumuşak tıklama: alçak frekans, kısa (eskiden 1,75 + 3,3 kHz)."""
    n = _n(0.05)
    x = _sine(620, 0.05) * _exp_decay(n, 0.01) * 0.7 + _sine(930, 0.05) * _exp_decay(n, 0.006) * 0.2
    return _norm(x, 0.28)


def sfx_hover():
    """Kaldırıldı: her düğme üzerinde çalan tiz ses baş ağrısı yapıyordu (sessiz)."""
    return np.zeros(_n(0.01), dtype=np.float32)


def sfx_tick():
    """Yumuşak, alçak 'tık' (eskiden 3,8 kHz tiz)."""
    n = _n(0.04)
    return _norm(_sine(700, 0.04) * np.hanning(n).astype(np.float32), 0.08)


def sfx_type():
    n = _n(0.04)
    win = np.hanning(n).astype(np.float32)
    x = (_bnoise(0.04, 900, 3000, 3) * 0.4 + _sine(500, 0.04) * 0.4) * win
    return _norm(x, 0.12)


def sfx_deny():
    n = _n(0.18)
    e = _env(n, 0.008, 0.05, 0.7, 0.08)
    x = (_bl_square(150, 0.18, 12) + _bl_square(142, 0.18, 12)) * e * 0.5      # bant sınırlı, DC yok
    return _norm(x, 0.35)


def sfx_clunk():
    """'Tak' - metalik parça takma sesi."""
    d = 0.42
    n = _n(d)
    x = np.zeros(n, dtype=np.float32)
    for f, a, tau in ((310, 1.0, 0.09), (873, 0.55, 0.05), (1462, 0.35, 0.03), (2210, 0.2, 0.02), (165, 0.7, 0.12)):
        x += _sine(f, d) * _exp_decay(n, tau) * a
    x += _bnoise(d, 300, 4000, 5) * _exp_decay(n, 0.006) * 0.8
    return _norm(_reverb_soft(x, 0.6, 0.18), 0.72)


def sfx_whoosh():
    d = 0.55
    n = _n(d)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    x = _bnoise(d, 200, 2500, 7, 0.8) * env
    return _norm(x, 0.45)


def sfx_launch():
    """Uzun fırlatma kükremesi."""
    d = 7.0
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    from .cae import synth as CS
    rumble = _bnoise(d, 25, 260, 11, 1.6) * 1.0 + _bnoise(d, 120, 900, 12, 1.0) * 0.35
    # alev titremesi: rastgele dürtüler (çatırtı) yerine yavaş genlik dalgalanmalı bant gürültüsü
    flicker = _bnoise(d, 300, 2200, 13, 0.6) * CS.smooth_lfo(d, 9.0, 3)[:n] * 0.22
    env = np.clip(t / 1.2, 0, 1) * np.clip((d - t) / 2.0, 0, 1)
    sub = np.sin(2 * np.pi * np.cumsum(38 + t * 3) / SR) * 0.45
    x = (rumble + flicker + sub) * env
    return _norm(x, 0.95)


def sfx_explosion():
    d = 1.6
    n = _n(d)
    x = _bnoise(d, 30, 700, 21, 1.4) * _exp_decay(n, 0.35) * 1.2
    x += _bnoise(d, 200, 3500, 22, 0.8) * _exp_decay(n, 0.06) * 0.7
    x += _sine(lambda t: 90 - t * 40, d) * _exp_decay(n, 0.25) * 0.8
    return _norm(_reverb_soft(x, 1.4, 0.25), 0.88)


def sfx_hit():
    d = 0.35
    n = _n(d)
    x = _bnoise(d, 80, 2500, 31, 0.8) * _exp_decay(n, 0.06) + _sine(110, d) * _exp_decay(n, 0.08) * 0.7
    return _norm(x, 0.7)


def sfx_laser():
    d = 0.2
    n = _n(d)
    x = _sine(lambda t: 900 * np.exp(-t * 10) + 220, d) * _exp_decay(n, 0.06)
    return _norm(x, 0.3)


def sfx_pickup():
    d = 0.32
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((76, 83, 88)):
        tone = _sine(note_freq(nn), 0.16) * _exp_decay(_n(0.16), 0.05)
        _place(buf, tone, SR * 0.055 * i)
    return _norm(buf, 0.45)


def sfx_coin():
    d = 0.5
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((84, 91)):
        tone = (_sine(note_freq(nn), 0.35) + _sine(note_freq(nn) * 2.01, 0.35) * 0.3) * _exp_decay(_n(0.35), 0.09)
        _place(buf, tone, SR * 0.07 * i)
    return _norm(buf, 0.45)


def sfx_alarm():
    """Uyarı: yumuşak iki tonlu alçak çan (eskiden 880/660 Hz sert dalgalanan siren)."""
    d = 0.9
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, f in enumerate((523.25, 392.0)):
        tone = (_sine(f, 0.45) + _sine(f * 2, 0.45) * 0.15) * _env(_n(0.45), 0.02, 0.1, 0.5, 0.25)
        _place(buf, tone, SR * 0.38 * i)
    return _norm(buf, 0.32)


def sfx_beep(freq=880, d=0.22):
    """Yumuşak bip: frekans en çok 700 Hz, saf ton, yumuşak zarf."""
    freq = min(freq, 700)
    n = _n(d)
    x = _sine(freq, d) * _env(n, 0.012, 0.05, 0.6, 0.1)
    return _norm(x, 0.3)


def sfx_success():
    d = 1.6
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((72, 76, 79, 84)):
        tone = (_sine(note_freq(nn), 1.0) + _tri(note_freq(nn), 1.0) * 0.3) * _exp_decay(_n(1.0), 0.35)
        _place(buf, tone, SR * 0.11 * i)
    return _norm(_reverb_soft(buf, 1.2, 0.22), 0.6)


def sfx_fail():
    d = 1.6
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((67, 63, 60, 55)):
        tone = _bl_saw(note_freq(nn), 0.7, 14) * _exp_decay(_n(0.7), 0.25)
        _place(buf, tone, SR * 0.17 * i)
    return _norm(_reverb_soft(buf, 1.2, 0.22), 0.55)


def sfx_repair():
    d = 0.9
    buf = np.zeros(_n(d), dtype=np.float32)
    for i in range(7):
        n = _n(0.05)
        c = _bnoise(0.05, 1200, 5000, 40 + i) * _exp_decay(n, 0.006) * 0.6 + _sine(1100 + i * 40, 0.05) * _exp_decay(n, 0.01) * 0.5
        _place(buf, c, SR * 0.11 * i)
    return _norm(buf, 0.5)


def sfx_flash():
    d = 0.25
    n = _n(d)
    x = _bnoise(d, 1500, 7000, 50) * _exp_decay(n, 0.012) * 0.6           # deklanşör
    x += _sine(lambda t: 3600 - t * 7000, d) * _exp_decay(n, 0.05) * 0.3
    return _norm(x, 0.45)


def sfx_storm():
    d = 3.0
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    wind = _bnoise(d, 60, 700, 60, 1.2) * (0.6 + 0.4 * np.sin(t * 3.1)) + _bnoise(d, 300, 1800, 61, 0.8) * 0.25
    rumble = _bnoise(d, 25, 160, 62, 1.5) * _env(n, 0.8, 0.6, 0.5, 1.0) * 0.6     # uzak gök gürültüsü (tık yok)
    env = _env(n, 0.4, 0.3, 0.9, 0.8)
    return _norm((wind + rumble) * env, 0.6)


def sfx_levelup():
    d = 1.4
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((67, 71, 74, 79, 83)):
        tone = _sine(note_freq(nn), 0.6) * _exp_decay(_n(0.6), 0.2)
        _place(buf, tone, SR * 0.07 * i)
    return _norm(_reverb_soft(buf, 1.0, 0.2), 0.6)


def sfx_nova_blip(pitch):
    """NOVA konuşma sesi: alçak, yumuşak, kısa (eskiden kare dalgalı ve tiz)."""
    d = 0.07
    n = _n(d)
    f = 190 * pitch
    x = _sine(f, d) * 0.7 + _sine(f * 2, d) * 0.2
    x = x * _env(n, 0.012, 0.02, 0.6, 0.035)
    return _norm(x, 0.16)


def sfx_ping():
    d = 0.9
    n = _n(d)
    x = (_sine(660, d) + _sine(990, d) * 0.2) * _exp_decay(n, 0.2) * np.minimum(1, np.arange(n) / _n(0.01))
    return _norm(_reverb_soft(x, 1.0, 0.18), 0.26)


def sfx_radio():
    d = 0.32
    n = _n(d)
    x = _sine(1050, d) * _env(n, 0.004, 0.02, 0.8, 0.03) * 0.6
    x += _bnoise(d, 700, 3500, 71) * _exp_decay(n, 0.02) * 0.35         # telsiz paraziti (bant sınırlı)
    return _norm(x, 0.35)


def sfx_sep():
    d = 1.1
    n = _n(d)
    x = _sine(lambda t: 120 * np.exp(-t * 6) + 40, d) * _exp_decay(n, 0.12)
    x += _bnoise(d, 200, 3500, 72, 0.8) * _exp_decay(n, 0.03) * 0.7
    x += _bnoise(d, 900, 5500, 73, 0.5) * _env(n, 0.05, 0.2, 0.3, 0.6) * 0.18       # gaz tahliyesi
    return _norm(_reverb_soft(x, 1.0, 0.2), 0.7)


# ===========================================================================
# ORTAM SESLERİ (her sahneye derinlik)
# ===========================================================================
def _loopable(x, fade=0.5):
    f = _n(fade)
    body = x[:-f].copy()
    k = np.linspace(0, 1, f, dtype=np.float32)
    body[:f] = body[:f] * k + x[-f:] * (1 - k)
    return body


def ambient_track(name):
    """Sahne ortam sesleri. Taban gürültüleri frekans uzayında bant sınırlı üretilir (cae.synth.shaped_noise):
    eski beyaz gürültü + kayan ortalama tabanındaki tıslama/cızırtı yok, döngü noktası tıksız."""
    from .cae import synth as CS
    d = 9.0
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    rng = random.Random(sum(map(ord, name)))
    buf = np.zeros(n, dtype=np.float32)

    def bed(lo, hi, slope, seed):
        x = CS.shaped_noise(d, lo, hi, slope, seed)
        return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)))
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / d)          # döngü boyunca tam bir periyot: dikişsiz
    if name == "amb_base":                       # açık hava: rüzgâr + uzak jeneratör uğultusu
        buf += bed(60, 700, 1.4, 201) * (0.55 + 0.45 * lfo) * 0.5
        buf += _sine(58, d) * 0.05 + _sine(116, d) * 0.02
    elif name == "amb_hangar":                   # makine uğultusu + ara sıra metal sesleri
        buf += bed(40, 300, 1.6, 202) * 0.35 + (_sine(48, d) + _sine(96, d) * 0.4) * 0.06
        for _ in range(5):
            c = sfx_clunk() * rng.uniform(0.15, 0.4)
            _place(buf, c, rng.uniform(0.3, d - 1.0) * SR)
    elif name == "amb_control":                  # kontrol odası: havalandırma uğultusu + bip sesleri (cızırtı yok)
        buf += bed(50, 500, 1.6, 203) * 0.3 + _sine(60, d) * 0.03
        pass                                     # rastgele bipler kaldırıldı (baş ağrısı)
    elif name == "amb_space":                    # derin uzay (kabin içi): vuru yapan alçak uğultu + ince parıltılar
        buf += (_sine(41, d) + _sine(373 / 9, d)) * 0.16 + _sine(82, d) * 0.04   # tam sayı periyot: döngüde tık yok
        buf += bed(30, 260, 1.8, 204) * 0.3
        pass                                     # tiz parıltılar (1,7–3,1 kHz) kaldırıldı
    elif name == "amb_colony":                   # ince atmosfer rüzgârı + yaşam destek uğultusu
        buf += bed(150, 1200, 1.2, 205) * (0.5 + 0.5 * lfo) * 0.35
        buf += _sine(72, d) * 0.04
    elif name == "amb_lab":                      # laboratuvar: kabarcıklar + uğultu
        buf += _sine(96, d) * 0.03 + bed(60, 400, 1.6, 206) * 0.25
        for _ in range(26):
            f0 = rng.uniform(500, 1400)
            ch = _sine(lambda tt, f0=f0: f0 + tt * 2600, 0.07) * _exp_decay(_n(0.07), 0.02) * rng.uniform(0.03, 0.09)
            _place(buf, ch, rng.uniform(0, d - 0.2) * SR)
    else:
        buf += bed(60, 500, 1.4, 207) * 0.3
    return _norm(buf, 0.42)


# ===========================================================================
# MÜZİK
# ===========================================================================
def _pad(freqs, dur, detune=0.004, bright=0.25):
    n = _n(dur)
    x = np.zeros(n, dtype=np.float32)
    for f in freqs:
        for dt in (-detune, 0, detune):
            x += _sine(f * (1 + dt), dur) * 0.33
            x += _tri(f * 2 * (1 + dt), dur) * 0.05 * bright
    return x * _env(n, dur * 0.3, dur * 0.2, 0.8, dur * 0.35)


def _pluck(f, dur, bright=0.6, tau=0.25):
    n = _n(dur)
    x = _bl_saw(f, dur, 24) * bright * 0.7 + _sine(f, dur)
    return x * _exp_decay(n, tau)


def _kick(d=0.4):
    n = _n(d)
    return _sine(lambda t: 50 + 110 * np.exp(-t * 30), d) * _exp_decay(n, 0.12)


def _hat(d=0.06, seed=0):
    n = _n(d)
    return _bnoise(d, 6000, 11000, seed % 6) * _exp_decay(n, 0.015) * 0.18


def _smooth_len(n):
    """n'e en yakın 2·3·5·7 çarpanlı uzunluk: döngü süzgeci/yankısı (FFT) asal uzunlukta yavaşlamaz."""
    best = None
    for a in range(0, 24):
        for b in range(0, 10):
            for c in range(0, 6):
                v = (2 ** a) * (3 ** b) * (5 ** c)
                if v > n * 1.01:
                    break
                for d in (1, 7, 49):
                    w = v * d
                    if n * 0.995 <= w <= n * 1.005 and (best is None or abs(w - n) < abs(best - n)):
                        best = w
    return best or n


def music_track(name, bars=8):
    from .cae.synth import place_wrap as _place      # döngü: taşan kuyruk başa sarılır (kesik nota yok)
    bpm = {"base": 80, "space": 60, "storm": 132, "colony": 108, "launch": 120, "menu": 70}.get(name, 80)
    n = _smooth_len(_n(60.0 / bpm * 4 * bars))     # FFT'ye uygun uzunluk (tempo farkı < %0,5)
    dur = n / SR
    bar = dur / bars
    beat = bar / 4
    buf = np.zeros(n, dtype=np.float32)
    if name in ("base", "menu"):
        prog = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)] * (bars // 4 + 1)
        for i in range(bars):
            ch = prog[i]
            _place(buf, _pad([note_freq(nn) for nn in ch], bar * 1.25, bright=0.4) * 0.22, bar * i)
            _place(buf, _sine(note_freq(ch[0] - 12), bar) * _env(_n(bar), 0.3, 0.3, 0.7, 0.5) * 0.18, bar * i)
            for k in range(8):
                nn = ch[k % 3] + (12 if k >= 4 else 0) + 12
                tone = (_sine(note_freq(nn), beat * 1.5) + _sine(note_freq(nn) * 3, beat * 1.5) * 0.08) \
                    * _exp_decay(_n(beat * 1.5), 0.35) * 0.07
                _place(buf, tone, bar * i + k * beat * 0.5)
        if name == "menu":
            for i in range(0, bars, 2):
                bell = (_sine(note_freq(81), 3.0) + _sine(note_freq(81) * 2.76, 3.0) * 0.3) * _exp_decay(_n(3), 0.8) * 0.06
                _place(buf, bell, bar * i)
    elif name == "space":
        def lsine(f):                     # döngüye tam sayıda periyot: dikişte tık yok
            return _sine(round(f * dur) / dur, dur)[:n]
        drone = lsine(note_freq(38)) * 0.16 + lsine(note_freq(45)) * 0.1
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * np.arange(n) / n)
        buf += (drone * lfo).astype(np.float32)
        chords = [(50, 57, 62, 69), (48, 55, 60, 67), (53, 57, 60, 65), (45, 52, 57, 64)]
        for i in range(bars):
            ch = chords[i % 4]
            _place(buf, _pad([note_freq(nn) for nn in ch], bar * 1.6, 0.006, 0.15) * 0.14, bar * i)
        rng = random.Random(4)
        for i in range(bars * 3):
            nn = rng.choice((74, 76, 79, 81, 86, 88))
            tone = _sine(note_freq(nn), 2.5) * _exp_decay(_n(2.5), 0.7) * 0.035
            _place(buf, tone, rng.uniform(0, dur - 2.5))
    elif name == "storm":
        for i in range(bars):
            for k in range(8):
                nn = 40 if k % 4 != 3 else 41
                tone = _pluck(note_freq(nn), beat * 0.5, 0.8, 0.08) * 0.22
                _place(buf, tone, bar * i + k * beat * 0.5)
            _place(buf, _pad([note_freq(52), note_freq(53), note_freq(59)], bar * 1.1, 0.01, 0.6) * 0.1, bar * i)
            for k in range(4):
                _place(buf, _kick(0.3) * 0.35, bar * i + k * beat)
            for k in range(16):
                _place(buf, _hat(0.05, k + i * 16) * (1.0 if k % 2 else 0.5), bar * i + k * beat * 0.25)
    elif name == "colony":
        prog = [(60, 64, 67), (65, 69, 72), (67, 71, 74), (60, 64, 67)]
        for i in range(bars):
            ch = prog[i % 4]
            for k in range(8):
                nn = ch[(k * 2) % 3] + (12 if k % 4 == 3 else 0)
                _place(buf, _pluck(note_freq(nn), beat * 0.8, 0.5, 0.18) * 0.12, bar * i + k * beat * 0.5)
            for k in range(4):
                _place(buf, _pluck(note_freq(ch[0] - 24), beat, 0.3, 0.3) * 0.2, bar * i + k * beat)
            _place(buf, _pad([note_freq(nn) for nn in ch], bar, 0.004, 0.3) * 0.08, bar * i)
            for k in (1, 3):
                _place(buf, _hat(0.06, i * 4 + k) * 0.8, bar * i + k * beat)
    elif name == "launch":
        for i in range(bars):
            k_int = 1 + i / bars
            ch = (50, 57, 62) if i % 2 == 0 else (53, 60, 65)
            _place(buf, _pad([note_freq(nn) for nn in ch], bar * 1.1, 0.006, 0.6) * 0.16 * k_int, bar * i)
            for k in range(4):
                _place(buf, _kick(0.35) * 0.4, bar * i + k * beat)
            for k in range(8):
                nn = ch[k % 3] + 12
                _place(buf, _pluck(note_freq(nn), beat * 0.45, 0.7, 0.07) * 0.09 * k_int, bar * i + k * beat * 0.5)
        buf += (_bnoise(dur, 60, 900, 99, 1.0) * np.linspace(0, 0.1, n)).astype(np.float32)
    buf = _reverb_soft(buf, 1.6, 0.28, circular=True)
    return _norm(buf, 0.65)


# ===========================================================================
# SES MOTORU
# ===========================================================================
class Audio:
    SFX = {
        "click": sfx_click, "hover": sfx_hover, "tick": sfx_tick, "type": sfx_type, "deny": sfx_deny,
        "clunk": sfx_clunk, "whoosh": sfx_whoosh, "launch": sfx_launch, "explosion": sfx_explosion,
        "hit": sfx_hit, "laser": sfx_laser, "pickup": sfx_pickup, "coin": sfx_coin, "alarm": sfx_alarm,
        "beep": lambda: sfx_beep(880), "go": lambda: sfx_beep(1320, 0.5), "success": sfx_success,
        "fail": sfx_fail, "repair": sfx_repair, "flash": sfx_flash, "storm": sfx_storm,
        "levelup": sfx_levelup, "ping": sfx_ping, "radio": sfx_radio, "sep": sfx_sep,
        "engine": lambda: __import__("aetherx.cae.sounds", fromlist=["engine_loop"]).engine_loop(1.0, False),
    }
    LOOPED = {"engine"}          # dikişsiz döngü: kenar geçişi uygulanmaz

    def __init__(self, enabled=True, music_vol=0.55, sfx_vol=0.8):
        self.ok = False
        self.enabled = enabled
        self.music_vol = music_vol
        self.sfx_vol = sfx_vol
        self.master = 1.0            # ana ses (AYARLAR > SES)
        self.amb_vol = 0.8           # ortam sesleri
        self.ui_vol = 0.8            # arayüz tıklamaları
        self.voice_vol = 0.8         # NOVA konuşma sesi
        self.sounds = {}
        self.tracks = {}
        self.music_raw = {}           # yükleme sırasında üretilen müzik (numpy); Sound'a çalarken çevrilir
        self.current = None
        self.music_ch = [None, None]
        self.active_ch = 0
        self.nova_queue = []
        self.nova_timer = 0.0
        self.nova_blips = []
        self.loops = {}
        self.last_play = {}
        self.amb = {}
        self.amb_current = None
        self.amb_ch = None
        if not HAS_NUMPY:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(SR, -16, 2, BUFFER)
                pygame.mixer.init(SR, -16, 2, BUFFER)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(10)      # 0-3 eski motor (müzik, döngü, ortam), 4-9 CAE ortam katmanları
            self.music_ch = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self.loop_ch = pygame.mixer.Channel(2)
            self.amb_ch = pygame.mixer.Channel(3)
            self.ok = True
        except Exception:
            self.ok = False

    # --- dönüştürme --------------------------------------------------------
    def _to_sound(self, mono, loop=False):
        # son işleme zinciri (DC, tıslama, tık, tepe) + karıştırma payı; doyum/kırpma bozulması yok
        mono = finish(mono, loop)
        arr = np.clip(mono * (32767 * MASTER), -32767, 32767).astype(np.int16)
        init = pygame.mixer.get_init()
        ch = init[2] if init else 2
        if ch == 2:
            arr = np.ascontiguousarray(np.column_stack((arr, arr)))
        return pygame.sndarray.make_sound(arr)

    def _get(self, name):
        s = self.sounds.get(name)
        if s is None and name in self.SFX:
            try:
                s = self._to_sound(self.SFX[name](), name in self.LOOPED)
            except Exception:
                s = False
            self.sounds[name] = s
        if name.startswith("nova") and s is None:
            pass
        return s or None

    def preload(self):
        if not self.ok:
            return
        for k in ("click", "hover", "tick", "clunk", "deny", "type", "beep", "pickup"):
            self._get(k)
        for i in range(6):
            self.nova_blips.append(self._to_sound(sfx_nova_blip(0.85 + i * 0.09)))

    # --- çalma -------------------------------------------------------------
    def play(self, name, vol=1.0, min_gap=0.03):
        if not (self.ok and self.enabled):
            return None
        now = pygame.time.get_ticks() / 1000.0
        if now - self.last_play.get(name, -9) < min_gap:
            return None
        self.last_play[name] = now
        s = self._get(name)
        if not s:
            return None
        ch = s.play()
        if ch:
            ch.set_volume(min(1.0, vol * self.sfx_vol * self.master))
        return ch

    def loop(self, name, vol=0.6, fade=400):
        """Uzun süreli döngü (fırlatma kükremesi, fırtına rüzgârı)."""
        if not (self.ok and self.enabled):
            return
        s = self._get(name)
        if not s:
            return
        self.loop_ch.play(s, loops=-1, fade_ms=fade)
        self.loop_vol = vol
        self.loop_ch.set_volume(vol * self.sfx_vol * self.master)

    def stop_loop(self, fade=600):
        if self.ok:
            self.loop_ch.fadeout(fade)

    def music(self, name, fade=1400):
        if not self.ok:
            return
        if name == self.current:
            return
        self.current = name
        old = self.music_ch[self.active_ch]
        if old:
            old.fadeout(fade)
        if not self.enabled or name is None:
            return
        tr = self.tracks.get(name)
        if tr is None:
            try:
                raw = self.music_raw.pop(name, None)
                tr = self._to_sound(raw if raw is not None else music_track(name), True)
            except Exception:
                tr = False
            self.tracks[name] = tr
        if not tr:
            return
        self.active_ch = 1 - self.active_ch
        ch = self.music_ch[self.active_ch]
        ch.play(tr, loops=-1, fade_ms=fade)
        ch.set_volume(self.music_vol * self.master)

    def prepare_music(self, names):
        """Müziği önceden üret (yükleme ekranında, iş parçacığında güvenli: yalnız numpy)."""
        for nm in names:
            if nm not in self.tracks and nm not in self.music_raw:
                try:
                    self.music_raw[nm] = music_track(nm)
                except Exception:
                    pass

    def ambient(self, name, fade=900):
        """Sahneye özgü ortam sesi döngüsü."""
        if not self.ok or name == self.amb_current:
            return
        self.amb_current = name
        self.amb_ch.fadeout(fade)
        if not self.enabled or not name:
            return
        snd = self.amb.get(name)
        if snd is None:
            try:
                snd = self._to_sound(ambient_track(name), True)
            except Exception:
                snd = False
            self.amb[name] = snd
        if snd:
            self.amb_ch.play(snd, loops=-1, fade_ms=fade)
            self.amb_ch.set_volume(0.5 * self.amb_vol * self.master)

    def set_volumes(self, music=None, sfx=None, master=None, amb=None, ui=None, voice=None):
        for k, v in (("music_vol", music), ("sfx_vol", sfx), ("master", master), ("amb_vol", amb), ("ui_vol", ui),
                     ("voice_vol", voice)):
            if v is not None:
                setattr(self, k, max(0.0, min(1.0, float(v))))
        if self.ok:                      # çalan kanallar anında güncellenir
            ch = self.music_ch[self.active_ch]
            if ch:
                ch.set_volume(self.music_vol * self.master)
            self.amb_ch.set_volume(0.5 * self.amb_vol * self.master)
            self.loop_ch.set_volume(getattr(self, "loop_vol", 0.6) * self.sfx_vol * self.master)

    def set_enabled(self, on):
        self.enabled = on
        if not self.ok:
            return
        if not on:
            for ch in self.music_ch:
                ch.stop()
            self.loop_ch.stop()
            self.amb_ch.stop()
        else:
            cur, self.current = self.current, None
            self.music(cur or "base")
            amb, self.amb_current = self.amb_current, None
            self.ambient(amb)

    # --- NOVA konuşması ----------------------------------------------------
    def speak(self, text):
        """Metindeki hece sayısına göre yumuşak robot blipleri sıralar."""
        if not (self.ok and self.enabled and self.nova_blips):
            return
        vowels = "aeıioöuüAEIİOÖUÜ"
        seq = []
        for ch in text[:140]:
            if ch in vowels:
                seq.append(random.randrange(len(self.nova_blips)))
            elif ch in ".,!?":
                seq.append(-1)
        self.nova_queue = [q for i, q in enumerate(seq) if q < 0 or i % 3 == 0][:14]   # seyrek ve kısa
        self.nova_timer = 0.0

    def update(self, dt):
        if not self.nova_queue:
            return
        self.nova_timer -= dt
        if self.nova_timer <= 0:
            i = self.nova_queue.pop(0)
            if i >= 0:
                ch = self.nova_blips[i].play()
                if ch:
                    ch.set_volume(0.5 * self.voice_vol * self.master)
                self.nova_timer = 0.085
            else:
                self.nova_timer = 0.2

    @property
    def speaking(self):
        return bool(self.nova_queue)

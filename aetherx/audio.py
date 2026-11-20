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


def _place(buf, x, start):
    s = int(start)
    if s >= len(buf):
        return
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


def note_freq(n):
    """MIDI nota -> Hz"""
    return 440.0 * (2 ** ((n - 69) / 12.0))


# ===========================================================================
# EFEKTLER
# ===========================================================================
def sfx_click():
    n = _n(0.045)
    x = _sine(1750, 0.045) * _exp_decay(n, 0.008) * 0.6
    x += _sine(3300, 0.045) * _exp_decay(n, 0.004) * 0.25
    x += _noise(0.045, 1) * _exp_decay(n, 0.002) * 0.25
    return _norm(x, 0.5)


def sfx_hover():
    n = _n(0.03)
    x = _sine(2600, 0.03) * _exp_decay(n, 0.006)
    return _norm(x, 0.14)


def sfx_tick():
    n = _n(0.02)
    return _norm(_sine(3800, 0.02) * _exp_decay(n, 0.003), 0.2)


def sfx_type():
    n = _n(0.03)
    x = _highpass(_noise(0.03, 3), 6) * _exp_decay(n, 0.004) + _sine(1200, 0.03) * _exp_decay(n, 0.005) * 0.3
    return _norm(x, 0.3)


def sfx_deny():
    n = _n(0.18)
    x = _square(150, 0.18, 0.3) * _env(n, 0.005, 0.05, 0.7, 0.08) * 0.5
    x += _square(142, 0.18, 0.3) * _env(n, 0.005, 0.05, 0.7, 0.08) * 0.5
    return _norm(_lowpass(x, 8), 0.35)


def sfx_clunk():
    """'Tak' - metalik parça takma sesi."""
    d = 0.42
    n = _n(d)
    x = np.zeros(n, dtype=np.float32)
    for f, a, tau in ((310, 1.0, 0.09), (873, 0.55, 0.05), (1462, 0.35, 0.03), (2210, 0.2, 0.02), (165, 0.7, 0.12)):
        x += _sine(f, d) * _exp_decay(n, tau) * a
    x += _lowpass(_noise(d, 5), 3) * _exp_decay(n, 0.006) * 1.2
    return _norm(_reverb(x), 0.75)


def sfx_whoosh():
    d = 0.55
    n = _n(d)
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    x = _lowpass(_noise(d, 7), 14) * env
    return _norm(x, 0.45)


def sfx_launch():
    """Uzun fırlatma kükremesi."""
    d = 7.0
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    rumble = _lowpass(_noise(d, 11), 60) * 2.2 + _lowpass(_noise(d, 12), 18) * 0.6
    crackle = _highpass(_noise(d, 13), 4) * (np.random.default_rng(2).random(n) > 0.985) * 0.8
    env = np.clip(t / 1.2, 0, 1) * np.clip((d - t) / 2.0, 0, 1)
    sub = np.sin(2 * np.pi * (38 + t * 3) * t) * 0.5
    x = (rumble + crackle + sub) * env
    return _norm(x, 0.95)


def sfx_explosion():
    d = 1.6
    n = _n(d)
    x = _lowpass(_noise(d, 21), 30) * _exp_decay(n, 0.35) * 1.5
    x += _lowpass(_noise(d, 22), 6) * _exp_decay(n, 0.06)
    x += _sine(lambda t: 90 - t * 40, d) * _exp_decay(n, 0.25) * 0.8
    return _norm(_reverb(x), 0.9)


def sfx_hit():
    d = 0.35
    n = _n(d)
    x = _lowpass(_noise(d, 31), 10) * _exp_decay(n, 0.06) + _sine(110, d) * _exp_decay(n, 0.08) * 0.7
    return _norm(x, 0.7)


def sfx_laser():
    d = 0.22
    n = _n(d)
    x = _sine(lambda t: 1900 * np.exp(-t * 14) + 300, d)
    x = x * _exp_decay(n, 0.07)
    x += _sine(lambda t: 3800 * np.exp(-t * 18) + 500, d) * _exp_decay(n, 0.04) * 0.3
    return _norm(x, 0.4)


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
    d = 0.9
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    f = np.where((t * 4) % 1 < 0.5, 880, 660)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.6 + _square(110, d, 0.5) * 0.08
    x *= _env(n, 0.01, 0.1, 0.9, 0.1)
    return _norm(x, 0.5)


def sfx_beep(freq=880, d=0.22):
    n = _n(d)
    x = (_sine(freq, d) + _sine(freq * 2, d) * 0.2) * _env(n, 0.003, 0.04, 0.7, 0.08)
    return _norm(x, 0.5)


def sfx_success():
    d = 1.6
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((72, 76, 79, 84)):
        tone = (_sine(note_freq(nn), 1.0) + _tri(note_freq(nn), 1.0) * 0.3) * _exp_decay(_n(1.0), 0.35)
        _place(buf, tone, SR * 0.11 * i)
    return _norm(_reverb(buf), 0.6)


def sfx_fail():
    d = 1.6
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((67, 63, 60, 55)):
        tone = _saw(note_freq(nn), 0.7) * _exp_decay(_n(0.7), 0.25)
        _place(buf, _lowpass(tone, 12), SR * 0.17 * i)
    return _norm(_reverb(buf), 0.55)


def sfx_repair():
    d = 0.9
    buf = np.zeros(_n(d), dtype=np.float32)
    for i in range(7):
        n = _n(0.05)
        c = _highpass(_noise(0.05, 40 + i), 3) * _exp_decay(n, 0.006) + _sine(1100 + i * 40, 0.05) * _exp_decay(n, 0.01) * 0.4
        _place(buf, c, SR * 0.11 * i)
    return _norm(buf, 0.5)


def sfx_flash():
    d = 0.25
    n = _n(d)
    x = _highpass(_noise(d, 50), 3) * _exp_decay(n, 0.012)
    x += _sine(lambda t: 4000 - t * 9000, d) * _exp_decay(n, 0.05) * 0.3
    return _norm(x, 0.45)


def sfx_storm():
    d = 3.0
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    wind = _lowpass(_noise(d, 60), 40) * (0.6 + 0.4 * np.sin(t * 3.1)) + _lowpass(_noise(d, 61), 9) * 0.3
    crack = _highpass(_noise(d, 62), 3) * (np.random.default_rng(5).random(n) > 0.996) * 2
    env = _env(n, 0.4, 0.3, 0.9, 0.8)
    return _norm((wind + crack) * env, 0.6)


def sfx_levelup():
    d = 1.4
    buf = np.zeros(_n(d), dtype=np.float32)
    for i, nn in enumerate((67, 71, 74, 79, 83)):
        tone = _sine(note_freq(nn), 0.6) * _exp_decay(_n(0.6), 0.2)
        _place(buf, tone, SR * 0.07 * i)
    return _norm(_reverb(buf), 0.6)


def sfx_nova_blip(pitch):
    d = 0.075
    n = _n(d)
    f = 280 * pitch
    x = _square(f, d, 0.35) * 0.35 + _sine(f * 2, d) * 0.4 + _sine(f * 3.02, d) * 0.15
    x = _lowpass(x, 5) * _env(n, 0.006, 0.02, 0.6, 0.03)
    return _norm(x, 0.28)


def sfx_ping():
    d = 0.9
    n = _n(d)
    x = (_sine(1320, d) + _sine(1980, d) * 0.3) * _exp_decay(n, 0.22)
    return _norm(_reverb(x), 0.4)


def sfx_radio():
    d = 0.32
    n = _n(d)
    x = _sine(1050, d) * _env(n, 0.004, 0.02, 0.8, 0.03) * 0.6
    x += _highpass(_noise(d, 71), 3) * _exp_decay(n, 0.02) * 0.5
    return _norm(x, 0.35)


def sfx_sep():
    d = 1.1
    n = _n(d)
    x = _sine(lambda t: 120 * np.exp(-t * 6) + 40, d) * _exp_decay(n, 0.12)
    x += _lowpass(_noise(d, 72), 4) * _exp_decay(n, 0.03) * 0.9
    x += _highpass(_noise(d, 73), 5) * _env(n, 0.05, 0.2, 0.3, 0.6) * 0.25          # gaz tahliyesi
    return _norm(_reverb(x), 0.7)


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
    d = 9.0
    n = _n(d)
    t = np.arange(n, dtype=np.float32) / SR
    rng = random.Random(sum(map(ord, name)))
    buf = np.zeros(n, dtype=np.float32)
    if name == "amb_base":                       # açık hava: rüzgâr + uzak jeneratör uğultusu
        buf += _lowpass(_noise(d, 201), 70) * (0.6 + 0.4 * np.sin(t * 0.7)) * 2.4
        buf += _sine(58, d) * 0.05 + _sine(116.5, d) * 0.02
    elif name == "amb_hangar":                   # makine uğultusu + ara sıra metal sesleri
        buf += _lowpass(_saw(48, d) + _saw(48.6, d), 30) * 0.12
        buf += _lowpass(_noise(d, 202), 24) * 0.9
        for _ in range(5):
            c = sfx_clunk() * rng.uniform(0.15, 0.4)
            _place(buf, c, rng.uniform(0.3, d - 1.0) * SR)
    elif name == "amb_control":                  # kontrol odası: bip sesleri + cızırtı
        buf += _lowpass(_noise(d, 203), 40) * 0.8
        for _ in range(14):
            b = sfx_beep(rng.choice((660, 880, 990, 1320)), rng.uniform(0.05, 0.12)) * rng.uniform(0.08, 0.22)
            _place(buf, b, rng.uniform(0.1, d - 0.6) * SR)
    elif name == "amb_space":                    # derin uzay: vuru yapan alçak uğultu + ince parıltılar
        buf += (_sine(41, d) + _sine(41.4, d)) * 0.16 + _sine(82.3, d) * 0.04
        buf += _lowpass(_noise(d, 204), 120) * 1.2
        for _ in range(6):
            f0 = rng.choice((1760, 2093, 2637, 3136))
            s_ = _sine(f0, 2.2) * np.sin(np.linspace(0, np.pi, _n(2.2))) ** 2 * 0.015
            _place(buf, s_, rng.uniform(0, d - 2.4) * SR)
    elif name == "amb_colony":                   # ince atmosfer rüzgârı + yaşam destek uğultusu
        buf += _highpass(_lowpass(_noise(d, 205), 26), 300) * (0.5 + 0.5 * np.sin(t * 1.1 + 1)) * 2.2
        buf += _sine(72, d) * 0.04
    elif name == "amb_lab":                      # laboratuvar: kabarcıklar + uğultu
        buf += _sine(96, d) * 0.03 + _lowpass(_noise(d, 206), 50) * 0.7
        for _ in range(26):
            f0 = rng.uniform(500, 1400)
            ch = _sine(lambda tt, f0=f0: f0 + tt * 2600, 0.07) * _exp_decay(_n(0.07), 0.02) * rng.uniform(0.03, 0.09)
            _place(buf, ch, rng.uniform(0, d - 0.2) * SR)
    else:
        buf += _lowpass(_noise(d, 207), 60)
    return _norm(_loopable(buf), 0.42)


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
    x = _saw(f, dur) * bright + _sine(f, dur)
    return _lowpass(x, 6) * _exp_decay(n, tau)


def _kick(d=0.4):
    n = _n(d)
    return _sine(lambda t: 50 + 110 * np.exp(-t * 30), d) * _exp_decay(n, 0.12)


def _hat(d=0.06, seed=0):
    n = _n(d)
    return _highpass(_noise(d, seed), 2) * _exp_decay(n, 0.015) * 0.3


def music_track(name, bars=8):
    bpm = {"base": 80, "space": 60, "storm": 132, "colony": 108, "launch": 120, "menu": 70}.get(name, 80)
    beat = 60.0 / bpm
    bar = beat * 4
    dur = bar * bars
    n = _n(dur)
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
        drone = _sine(note_freq(38), dur) * 0.16 + _sine(note_freq(45), dur) * 0.1
        lfo = 0.6 + 0.4 * np.sin(np.arange(n) / SR * 0.21)
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
        buf += (_lowpass(_noise(dur, 99), 30) * np.linspace(0, 0.12, n)).astype(np.float32)
    buf = _reverb(buf, (0.05, 0.09, 0.13, 0.21), 0.38)
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
    }

    def __init__(self, enabled=True, music_vol=0.55, sfx_vol=0.8):
        self.ok = False
        self.enabled = enabled
        self.music_vol = music_vol
        self.sfx_vol = sfx_vol
        self.sounds = {}
        self.tracks = {}
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
                pygame.mixer.pre_init(SR, -16, 2, 512)
                pygame.mixer.init(SR, -16, 2, 512)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(4)
            self.music_ch = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self.loop_ch = pygame.mixer.Channel(2)
            self.amb_ch = pygame.mixer.Channel(3)
            self.ok = True
        except Exception:
            self.ok = False

    # --- dönüştürme --------------------------------------------------------
    def _to_sound(self, mono):
        arr = np.clip(mono * 32767, -32767, 32767).astype(np.int16)
        init = pygame.mixer.get_init()
        ch = init[2] if init else 2
        if ch == 2:
            arr = np.ascontiguousarray(np.column_stack((arr, arr)))
        return pygame.sndarray.make_sound(arr)

    def _get(self, name):
        s = self.sounds.get(name)
        if s is None and name in self.SFX:
            try:
                s = self._to_sound(self.SFX[name]())
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
            ch.set_volume(vol * self.sfx_vol)
        return ch

    def loop(self, name, vol=0.6, fade=400):
        """Uzun süreli döngü (fırlatma kükremesi, fırtına rüzgârı)."""
        if not (self.ok and self.enabled):
            return
        s = self._get(name)
        if not s:
            return
        self.loop_ch.play(s, loops=-1, fade_ms=fade)
        self.loop_ch.set_volume(vol * self.sfx_vol)

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
                tr = self._to_sound(music_track(name))
            except Exception:
                tr = False
            self.tracks[name] = tr
        if not tr:
            return
        self.active_ch = 1 - self.active_ch
        ch = self.music_ch[self.active_ch]
        ch.play(tr, loops=-1, fade_ms=fade)
        ch.set_volume(self.music_vol)

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
                snd = self._to_sound(ambient_track(name))
            except Exception:
                snd = False
            self.amb[name] = snd
        if snd:
            self.amb_ch.play(snd, loops=-1, fade_ms=fade)
            self.amb_ch.set_volume(0.5 * self.sfx_vol)

    def set_volumes(self, music=None, sfx=None):
        if music is not None:
            self.music_vol = music
        if sfx is not None:
            self.sfx_vol = sfx
        if self.ok:
            ch = self.music_ch[self.active_ch]
            if ch:
                ch.set_volume(self.music_vol)

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
        self.nova_queue = seq[:60]
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
                    ch.set_volume(0.5 * self.sfx_vol)
                self.nova_timer = 0.085
            else:
                self.nova_timer = 0.2

    @property
    def speaking(self):
        return bool(self.nova_queue)

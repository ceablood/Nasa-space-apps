# -*- coding: utf-8 -*-
"""
AETHER-X // KOZMİK SES MOTORU — SENTEZ ÇEKİRDEĞİ
Bütün sesler bu projede numpy ile üretilir (ses dosyası, lisans gerektiren kayıt yok).

Cızırtı neden vardı, nasıl giderildi:
  Eski ortam seslerinin tabanı düzgün dağılımlı beyaz gürültüydü; kayan ortalama "alçak geçiren" süzgecin yan
  lobları yüksek frekansları geçirdiği için sürekli bir tıslama/cızırtı kalıyordu. Burada gürültü FREKANS
  UZAYINDA biçimlendirilir: istenen bant dışındaki bileşenler sıfırdır (tıslama yok) ve ters FFT ile elde
  edilen dalga kendiliğinden periyodiktir, yani döngü noktasında tık sesi de oluşmaz.
"""
import math

import numpy as np

SR = 44100
F32 = np.float32


def n_of(dur):
    return int(round(SR * dur))


def t_of(dur):
    return np.arange(n_of(dur), dtype=F32) / SR


def shaped_noise(dur, lo, hi, slope=1.0, seed=0, tilt_hz=None):
    """Bant sınırlı, döngüye uygun gürültü. lo..hi Hz dışında enerji yok; kenarlar yumuşak (kosinüs).
    slope: 1/f^slope eğimi (0 beyaz, 1 pembe, 2 kahverengi) — bant içinde."""
    n = n_of(dur)
    rng = np.random.default_rng(seed)
    nf = n // 2 + 1
    f = np.fft.rfftfreq(n, 1.0 / SR).astype(F32)
    mag = np.zeros(nf, dtype=F32)
    band = (f >= lo * 0.7) & (f <= hi * 1.3)
    ff = np.maximum(f[band], 1.0)
    w = np.ones_like(ff)
    # yumuşak kenarlar: lo*0.7..lo ve hi..hi*1.3 arasında kosinüs geçişi
    a = (ff < lo)
    w[a] = 0.5 - 0.5 * np.cos(np.pi * (ff[a] - lo * 0.7) / (lo * 0.3))
    b = (ff > hi)
    w[b] = 0.5 + 0.5 * np.cos(np.pi * (ff[b] - hi) / (hi * 0.3))
    mag[band] = w / ff ** (slope * 0.5)
    ph = rng.uniform(0, 2 * np.pi, nf).astype(F32)
    spec = mag * (np.cos(ph) + 1j * np.sin(ph))
    x = np.fft.irfft(spec, n).astype(F32)
    m = float(np.max(np.abs(x))) or 1.0
    return x / m


def smooth_lfo(dur, rate_hz, seed=0, depth=1.0):
    """Yavaş, döngülü rastgele zarf (0..1): rüzgâr hamleleri, dalga kabarması için."""
    x = shaped_noise(dur, max(0.02, rate_hz * 0.3), rate_hz, 0.0, seed)
    return (0.5 + 0.5 * x * depth).astype(F32)


def fft_filter(x, lo=None, hi=None):
    """Yumuşak kenarlı bant geçiren (FFT). Kısa efektler ve erişilebilirlik (yüksek frekans azaltma) için."""
    n = len(x)
    if n < 8:
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1.0 / np.sqrt(1.0 + (f / hi) ** 8)
    if lo:
        g *= 1.0 / np.sqrt(1.0 + (lo / np.maximum(f, 1e-3)) ** 8)
    return np.fft.irfft(X * g, n).astype(F32)


def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1):
    a_n, d_n, r_n = n_of(a), n_of(d), n_of(r)
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate([np.linspace(0, 1, max(1, a_n)), np.linspace(1, s, max(1, d_n)), np.full(s_n, s),
                        np.linspace(s, 0, max(1, r_n))]).astype(F32)
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def tone(freq_fn, dur, harmonics=((1, 1.0),), vib=0.0, vib_rate=5.0):
    """Frekansı zamanla değişebilen (glissando) harmonikli ton; faz birikimiyle tık sesi yok."""
    t = t_of(dur)
    f = freq_fn(t) if callable(freq_fn) else np.full_like(t, freq_fn)
    if vib:
        f = f * (1 + vib * np.sin(2 * np.pi * vib_rate * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    out = np.zeros_like(t)
    for k, amp in harmonics:
        out += amp * np.sin(ph * k)
    return out.astype(F32)


def place(buf, x, start):
    s = int(start)
    if s >= len(buf) or s + len(x) <= 0:
        return
    if s < 0:
        x = x[-s:]
        s = 0
    e = min(len(buf), s + len(x))
    buf[s:e] += x[:e - s]


def place_wrap(buf, x, start):
    """Döngü tamponuna dairesel yerleştirme: sona taşan kısım başa sarılır (döngüde kesilme yok)."""
    s = int(start) % len(buf)
    k = min(len(x), len(buf) - s)
    buf[s:s + k] += x[:k]
    if k < len(x):
        buf[:len(x) - k] += x[k:]


def reverb(x, room=0.3, size=1.0):
    """Basit erken yansıma + sönen kuyruk (mağara, kabin)."""
    out = x.copy()
    for i, d in enumerate((0.023, 0.041, 0.067, 0.097, 0.131, 0.173)):
        n = n_of(d * size)
        if n < len(x):
            out[n:] += x[:-n] * (room ** (i + 1)) * 1.6
    return out


def soft_limit(x, ceiling=0.9):
    """Yumuşak sınırlayıcı (tanh): ani yüksek sesleri ve sertçe kırpılan dalgayı (çatırtı) önler."""
    return (np.tanh(x / ceiling) * ceiling).astype(F32)


def normalize(x, peak=0.8):
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    return x if m < 1e-9 else (x / m * peak).astype(F32)


def fade_edges(x, ms=8):
    """Tek seferlik efektlerde baş/son tık sesini önleyen kısa geçiş."""
    k = min(len(x) // 2, n_of(ms / 1000.0))
    if k > 1:
        r = np.linspace(0, 1, k, dtype=F32)
        x[:k] *= r
        x[-k:] *= r[::-1]
    return x

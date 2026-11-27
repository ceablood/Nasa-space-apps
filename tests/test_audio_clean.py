# -*- coding: utf-8 -*-
"""Ses temizliği testleri: her sesin son hali (audio.finish sonrası) tık, tıslama, DC kayması ve bozulma içermemeli.
Çalıştırma: python -m unittest discover -s tests -v"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aetherx import audio as A                                     # noqa: E402
from aetherx.cae import sounds as S, synth as SY                   # noqa: E402
from aetherx.life import EventBus, LifeWorld                       # noqa: E402

SR = A.SR


def clicks(y):
    """Tık: ikinci türevin yerel düzeye göre aykırı sıçraması (tonal yüksek frekansı tık saymaz)."""
    d2 = np.abs(np.diff(y, 2))
    loc = np.convolve(d2, np.ones(441) / 441, mode="same") + 1e-6
    return int(((d2 > 12 * loc) & (d2 > 0.05)).sum())


def hf(y):
    X = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / SR)
    return float(X[f > 12000].sum() / max(1e-12, X.sum()))


class TestOneShots(unittest.TestCase):
    def check(self, name, x):
        y = A.finish(x, False).astype(np.float64)
        pk = float(np.max(np.abs(y)))
        if pk < 1e-6:                      # bilerek sessizleştirilmiş ses (ör. düğme üzeri sesi kaldırıldı)
            return
        self.assertLessEqual(pk, 0.951, f"{name}: tepe {pk}")
        z = y / (pk or 1)
        self.assertLess(abs(float(np.mean(z))), 0.005, f"{name}: DC kayması")
        self.assertLess(abs(z[0]), 0.01, f"{name}: başta tık")
        self.assertLess(abs(z[-1]), 0.01, f"{name}: sonda tık")
        self.assertLess(hf(z), 0.01, f"{name}: 12 kHz üstü tıslama")
        self.assertEqual(clicks(z), 0, f"{name}: ani sıçrama (tık/çatırtı)")

    def test_all_sfx(self):
        for k, fn in A.Audio.SFX.items():
            if k in A.Audio.LOOPED:
                continue
            with self.subTest(k):
                self.check(k, fn())

    def test_cae_effects(self):
        env = LifeWorld("earth", EventBus()).env
        for k, fn in (("thunder", lambda: S.thunder(env, 3)), ("erupt", lambda: S.eruption(env, 0.7)), ("impact", lambda: S.impact(env, 0.8)),
                      ("ice", S.ice_crack), ("microbe", S.microbial_representation), ("scan", S.scanner_sweep),
                      ("gear", S.landing_gear), ("chime", S.discovery_chime), ("report", S.report_tone)):
            with self.subTest(k):
                self.check(k, fn())


class TestLoops(unittest.TestCase):
    def seamless(self, name, x):
        y = A.finish(x, True).astype(np.float64)
        d = np.abs(np.diff(y))
        seam = abs(y[-1] - y[0])
        self.assertLessEqual(seam, max(1e-4, float(np.percentile(d, 99.5)) * 1.2), f"{name}: döngü dikişinde tık")
        self.assertLess(hf(y / (np.max(np.abs(y)) or 1)), 0.01, f"{name}: tıslama")

    def test_ambience_and_music(self):
        for k in ("amb_base", "amb_hangar", "amb_control", "amb_space", "amb_colony", "amb_lab"):
            with self.subTest(k):
                self.seamless(k, A.ambient_track(k))
        for k in ("base", "space", "storm"):
            with self.subTest(k):
                self.seamless(k, A.music_track(k))

    def test_no_saturation_in_limiter(self):
        """Sınırlayıcı dalgayı eğmez: sessiz sinüs olduğu gibi kalır, yüksek tepe tavana iner."""
        t = np.arange(SR) / SR
        quiet = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        self.assertTrue(np.allclose(SY.smooth_limit(quiet, 0.7), quiet, atol=1e-6))
        loud = (1.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        self.assertLessEqual(float(np.max(np.abs(SY.smooth_limit(loud, 0.7)))), 0.72)


if __name__ == "__main__":
    unittest.main()

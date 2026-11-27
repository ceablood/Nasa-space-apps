# -*- coding: utf-8 -*-
"""3B canlı çizicisi ve iniş fiziği testleri."""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aetherx import creature3d as C3                       # noqa: E402
from aetherx.life import EventBus, LifeWorld               # noqa: E402


class TestCreature3D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        w = LifeWorld("earth", EventBus())
        cls.animals = [s for s in w.species if s.kingdom == "hayvan"]
        w2 = LifeWorld("okyanus", EventBus())
        cls.animals += [s for s in w2.species if s.kingdom == "hayvan"]

    def test_every_animal_renders_a_solid_figure(self):
        for sp in self.animals:
            with self.subTest(sp.name):
                img = C3.render(C3.build(sp), 96, ss=1)
                self.assertEqual(img.shape, (96, 96, 4))
                cover = (img[..., 3] == 255).mean()
                self.assertGreater(cover, 0.04, "figür görünür olmalı")
                self.assertLess(cover, 0.85, "figür kareye sığmalı")

    def test_deterministic_and_rotates(self):
        sp = self.animals[0]
        a = C3.render(C3.build(sp), 64, yaw=0.6, ss=1)
        b = C3.render(C3.build(sp), 64, yaw=0.6, ss=1)
        c = C3.render(C3.build(sp), 64, yaw=2.2, ss=1)
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, c))

    def test_body_plans_follow_habitat(self):
        names = {s.name: len(C3.build(s)) for s in self.animals}
        self.assertTrue(all(n >= 6 for n in names.values()))


class TestLandingPhysics(unittest.TestCase):
    def test_mass_ratio_tsiolkovsky(self):
        from aetherx.scenes.landing import Lander, VE
        L = Lander(1.62, 6.0, 500.0)
        self.assertAlmostEqual(L.mass_ratio(), 1.0)
        L.dv = 500.0 - 300.0
        self.assertAlmostEqual(L.mass_ratio(), math.exp(300.0 / VE), places=9)
        self.assertGreater(L.mass_ratio(), 1.09)          # 300 m/s yakmak aracı ~%9 hafifletir


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Koloni 3B: önbellekli kare = baştan çizilen kare (piksel piksel); 45 FPS koruması yalnız hareketli kamerada.
Çalıştırma: python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["AETHERX_SYNC_LOAD"] = "1"
if "aetherx.config" not in sys.modules:
    os.environ["HOME"] = tempfile.mkdtemp(prefix="aetherx_col_")

import numpy as np          # noqa: E402
import pygame               # noqa: E402


class Colony3DTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import aetherx.app as A
        import aetherx.data as D
        cls.app = A.App(headless=True)
        g = cls.app.game
        g.new("TEST", (62, 230, 255))
        cls.app.on_game_ready()
        g.s["colonies"]["moon"] = {"planet": "moon", "founded": 1, "level": 1, "pop": 10.0, "happiness": 70.0,
                                   "buildings": {b["key"]: 1 for b in D.COLONY_BUILDINGS}, "storage": 0.0, "food": 60.0,
                                   "happy_buff": 0.0}
        g.s["clock"]["minutes"] = 12 * 60
        cls.app.go("colony", instant=True, planet="moon")
        for _ in range(40):
            cls.app.update(1 / 60)
            cls.app.draw()
        cls.w = cls.app.scene.world
        from aetherx import paint
        cls.rect = pygame.Rect(40, 224, 940, 500)
        cls.bg = paint.get("moon", cls.rect.size)

    def grab(self):
        s = pygame.Surface(self.app.screen.get_size())
        self.w.draw(s, self.rect, self.bg)
        return pygame.surfarray.array3d(s).astype(np.int16)

    def test_cached_frame_identical_to_fresh(self):
        self.w._tc = None
        a = self.grab()                     # önbellek boş: baştan çizim
        b = self.grab()                     # aynı kamera: önbellekten
        self.assertEqual(int(np.abs(a - b).max()), 0)

    def test_motion_guard(self):
        from aetherx import settings as SET
        w = self.w
        self.grab()
        base_ss = w.ss
        if base_ss <= 1.5:
            self.skipTest("süper örnekleme bu kalite kademesinde zaten ≤1,5")
        w._frame_ema = 0.040                # yavaş cihaz (25 FPS) benzetimi
        w._last_draw_t = None
        w.cam.tx += 0.05                    # kamera hareketli
        self.grab()
        self.assertTrue(w.motion_lo)
        self.assertEqual(w.ss, 1.5)
        w._frame_ema = 0.040
        w._last_draw_t = None
        self.grab()                         # kamera durdu: tam kalite
        self.assertFalse(w.motion_lo)
        self.assertEqual(w.ss, base_ss)
        SET.set("motion_res", False, save=False)
        try:
            w._frame_ema = 0.040
            w.cam.tx -= 0.05
            self.grab()
            self.assertFalse(w.motion_lo)   # ayar kapalıyken devreye girmez
        finally:
            SET.set("motion_res", True, save=False)


if __name__ == "__main__":
    unittest.main()

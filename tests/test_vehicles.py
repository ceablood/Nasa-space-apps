# -*- coding: utf-8 -*-
"""Gezegen aracı sürüş motoru testleri — KOZMOGENİS V3.0 §I (10 test) + uzay aracı fiziği ayrımı (§G).
Çalıştırma: python -m unittest discover -s tests -v   (pencere/ses aygıtı gerekmez)"""
import math
import os
import sys
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame                                                         # noqa: E402

from aetherx.vehicles import CATALOG, Controls, Rover, Terrain        # noqa: E402
from aetherx.vehicles.controls import DEFAULT_KEYS, KeyMap, TouchControls  # noqa: E402
from aetherx.vehicles.physics import slip_curve                       # noqa: E402
from aetherx.vehicles.planets import PLANETS, SURFACES, SURFACE_IDS   # noqa: E402
from aetherx.vehicles.render3d import Camera, TerrainRenderer         # noqa: E402
from aetherx.vehicles.spacecraft import G0, Spacecraft2D              # noqa: E402

DT = 1 / 60
_CACHE = {}


def flat(planet, surface="regolit", slope_deg=0.0, rocks=()):
    """Gerçek arazi nesnesi; yükseklik düz (ya da +x yönünde sabit eğimli), tek zemin türü."""
    if planet not in _CACHE:
        _CACHE[planet] = Terrain(planet, n=128)
    base = _CACHE[planet]
    t = Terrain.__new__(Terrain)
    t.__dict__.update(base.__dict__)
    xs = np.arange(t.n, dtype=np.float32) * t.cell
    t.h = np.tile(((xs - t.size / 2) * math.tan(math.radians(slope_deg))).astype(np.float32), (t.n, 1))
    t.surf = np.full((t.n, t.n), SURFACE_IDS.index(surface), dtype=np.int8)
    t.rocks = np.array(rocks, dtype=np.float32).reshape(-1, 3)
    t.lake_level = None
    t.lake = np.zeros((t.n, t.n), bool)
    return t


def run(rover, ctl, seconds):
    for _ in range(int(seconds / DT)):
        rover.step(ctl, DT)


def settled(spec, terrain, yaw=0.0):
    c = terrain.size / 2
    r = Rover(spec, terrain, c, c, yaw)
    r.rng.random = lambda: 1.0            # rastgele arıza kapalı (deterministik test)
    run(r, Controls(brake=1.0), 2.0)
    return r


class T01FlatAccelBrake(unittest.TestCase):
    def test_accelerates_to_top_speed_and_brakes_like_mu_g(self):
        t = flat("moon")
        r = settled(CATALOG["lrv"], t)
        t0 = 0.0
        while r.forward_speed < 0.95 * r.s.top_speed and t0 < 30:
            r.step(Controls(throttle=1.0), DT)
            t0 += DT
        self.assertLess(t0, 20, "LRV düz zeminde en yüksek hıza 20 s içinde ulaşmalı")
        run(r, Controls(throttle=1.0), 5)
        self.assertLess(r.forward_speed, r.s.top_speed * 1.08, "en yüksek hız aşılmamalı")
        v0 = r.forward_speed
        tb = 0.0
        while r.speed > 0.05 and tb < 20:
            r.step(Controls(brake=1.0), DT)
            tb += DT
        mu = SURFACES["regolit"]["mu"]
        crr = SURFACES["regolit"]["crr"]
        pred = v0 / ((mu + crr) * PLANETS["moon"]["g"])
        self.assertAlmostEqual(tb, pred, delta=pred * 0.35, msg=f"fren süresi {tb:.2f}s, μg tahmini {pred:.2f}s")


class T02Slope(unittest.TestCase):
    def climb(self, deg, surface="regolit", planet="moon", veh="lrv"):
        t = flat(planet, surface, deg)
        r = settled(CATALOG[veh], t)
        x0 = r.x
        run(r, Controls(throttle=1.0), 20)
        return r.x - x0, r

    def test_moderate_slope_climbable_steep_slope_stalls(self):
        d10, _ = self.climb(10)
        d0, _ = self.climb(0)
        d35, r35 = self.climb(35, "gevşek kum", "mars", "mars_rover")
        self.assertGreater(d10, 15, "10° regolit yokuşu tırmanılabilmeli")
        self.assertLess(d10, d0, "yokuşta düzlüğe göre daha az yol alınmalı")
        self.assertLess(d35, 3, f"35° gevşek kum: araç ilerleyememeli (aldığı yol {d35:.1f} m)")
        self.assertGreater(max(r35.wheel_slip), 0.5, "dik gevşek yokuşta patinaj yüksek olmalı")


class T03LooseSoil(unittest.TestCase):
    def test_loose_sand_slips_more_than_rock(self):
        self.assertGreater(slip_curve(15, SURFACES["gevşek kum"]["loose"]), slip_curve(15, SURFACES["kaya"]["loose"]) * 2)
        res = {}
        for s in ("gevşek kum", "kaya"):
            t = flat("mars", s, 15)
            r = settled(CATALOG["mars_rover"], t)
            x0 = r.x
            slip = []
            for _ in range(int(15 / DT)):
                r.step(Controls(throttle=1.0), DT)
                slip.append(max(r.wheel_slip))
            res[s] = (r.x - x0, float(np.mean(slip)))
        self.assertGreater(res["gevşek kum"][1], res["kaya"][1])
        self.assertLess(res["gevşek kum"][0], res["kaya"][0])


class T04Gravity(unittest.TestCase):
    def test_braking_distance_scales_inverse_with_g(self):
        dist = {}
        for p in ("moon", "mars"):
            t = flat(p)
            r = settled(CATALOG["sev"], t)
            r.vx = 2.5                         # aynı başlangıç hızı
            x0 = r.x
            run(r, Controls(brake=1.0), 8)
            dist[p] = r.x - x0
        ratio = dist["moon"] / dist["mars"]
        g_ratio = PLANETS["mars"]["g"] / PLANETS["moon"]["g"]
        self.assertAlmostEqual(ratio, g_ratio, delta=g_ratio * 0.3, msg=f"durma mesafesi oranı {ratio:.2f}, g oranı {g_ratio:.2f}")

    def test_titan_has_air_drag_moon_has_none(self):
        self.assertEqual(PLANETS["moon"]["rho"], 0.0)
        self.assertGreater(PLANETS["titan"]["rho"], 4.0)        # Huygens: ~5,4 kg/m³


class T05CollisionRollover(unittest.TestCase):
    def test_rock_impact_damages(self):
        t = flat("moon")
        c = t.size / 2
        t.rocks = np.array([[c + 10, c, 1.4]], dtype=np.float32)
        r = settled(CATALOG["lrv"], t)
        run(r, Controls(throttle=1.0), 8)
        self.assertGreater(r.damage, 0.0)
        self.assertTrue(any(e[0] == "çarpışma" for e in r.events) or r.impacts)
        self.assertLess(r.x, c + 10, "araç kayanın içinden geçmemeli")

    def test_safe_side_slope_does_not_flip(self):
        t = flat("moon", slope_deg=30)
        r = settled(CATALOG["lrv"], t, yaw=math.pi / 2)
        run(r, Controls(), 3)
        self.assertFalse(r.flipped, "30° yan eğim LRV'nin statik devrilme açısının (~55°) altında")

    def test_recover_on_slope_turns_vehicle_downhill(self):
        t = flat("moon", slope_deg=45)
        r = settled(CATALOG["lrv"], t, yaw=math.pi / 2)
        r.recover()
        run(r, Controls(brake=1.0), 2)
        self.assertFalse(r.flipped)
        self.assertLess(abs(math.sin(r.yaw)), 0.1, "kurtarma aracı yokuş yönüne çevirmeli")

    def test_side_slope_rollover_and_recover(self):
        t = flat("moon", slope_deg=62)
        r = settled(CATALOG["lrv"], t, yaw=math.pi / 2)    # yokuşa yan dur: devrilme
        run(r, Controls(), 3)
        self.assertTrue(r.flipped, f"62° yan eğimde LRV devrilmeli (yalpa {math.degrees(r.roll):.0f}°)")
        t.h[:] = 0.0                                       # düz zemine çekildi
        r.recover()
        self.assertFalse(r.flipped)
        self.assertEqual(r.roll, 0.0)


class T06Suspension(unittest.TestCase):
    def test_drop_settles_with_damping(self):
        t = flat("mars")
        r = settled(CATALOG["mars_rover"], t)
        z_eq = r.z
        r.z += 0.3
        r.vz = 0.0
        zs = []
        for _ in range(int(6 / DT)):
            r.step(Controls(brake=1.0), DT)
            zs.append(r.z - z_eq)
        zs = np.array(zs)
        self.assertLess(abs(zs[-30:]).max(), 0.02, "6 s sonra denge konumuna oturmalı")
        first = abs(zs[: int(1 / DT)]).max()
        late = abs(zs[int(3 / DT):]).max()
        self.assertLess(late, first * 0.3, "salınım sönmeli")
        s = r.s
        static = r.mass * r.g / (len(r.wpos) * s.k_spring)
        self.assertAlmostEqual(np.mean(r.comp), static, delta=static * 0.25 + 0.005)


class T07Battery(unittest.TestCase):
    def test_battery_drop_equals_power_integral(self):
        t = flat("moon")
        r = settled(CATALOG["ltv"], t)
        b0 = r.battery
        e = 0.0
        for i in range(int(90 / DT)):
            r.step(Controls(throttle=1.0, steer=0.3 if i % 600 < 300 else -0.3), DT)
            e += r.power_kw * DT / 3600
        solar = r.s.solar_w / 1000 * 90 / 3600
        self.assertAlmostEqual(b0 - r.battery, e - solar, delta=max(0.002, e * 0.08))
        self.assertGreater(r.odometer, 100)


class T08Dashboard(unittest.TestCase):
    def test_dashboard_matches_state(self):
        t = flat("mars", slope_deg=8)
        r = settled(CATALOG["mars_rover"], t)
        run(r, Controls(throttle=1.0, steer=0.4), 6)
        d = r.dashboard()
        self.assertAlmostEqual(d["hız_kmh"], r.speed * 3.6, places=6)
        self.assertAlmostEqual(d["batarya_kwh"], r.battery, places=6)
        self.assertAlmostEqual(d["batarya_yüzde"], 100 * r.battery / r.s.battery_kwh, places=6)
        self.assertAlmostEqual(d["güç_kw"], r.power_kw, places=6)
        self.assertAlmostEqual(d["hasar_yüzde"], 100 * r.damage, places=6)
        self.assertAlmostEqual(d["motor_c"], r.motor_temp, places=6)
        self.assertAlmostEqual(d["yön_derece"] % 360, (90 - math.degrees(r.yaw)) % 360, delta=0.01)
        self.assertEqual(d["zemin"], t.surface_at(r.x, r.y))
        self.assertAlmostEqual(d["eğim"], t.slope_deg(r.x, r.y), places=6)
        self.assertAlmostEqual(d["yunuslama"], math.degrees(r.pitch), places=6)
        self.assertAlmostEqual(d["yalpa"], math.degrees(r.roll), places=6)


class T09Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_keymap_rebind_swap_reset(self):
        store = {}
        k = KeyMap(store)
        self.assertEqual(k.conflicts(), [])
        sw = k.bind("ileri", pygame.K_s)         # S zaten "geri": yer değiştirir
        self.assertEqual(sw, "geri")
        self.assertEqual(k.keys["ileri"], "s")
        self.assertEqual(k.keys["geri"], "w")
        self.assertEqual(k.conflicts(), [])
        self.assertEqual(store["keys"]["ileri"], "s")
        k2 = KeyMap(store)                        # kaydedilen eşleme geri yüklenir
        self.assertEqual(k2.codes["ileri"], pygame.K_s)
        e = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s)
        self.assertTrue(k2.is_event(e, "ileri"))
        pressed = {pygame.K_s: True}
        self.assertTrue(k2.held(type("P", (), {"__getitem__": lambda s, c: pressed.get(c, False)})(), "ileri"))
        k2.reset()
        self.assertEqual(k2.keys, DEFAULT_KEYS)

    def test_touch_wheel_and_pedals(self):
        tc = TouchControls(1600, 900)
        cx, cy = tc.wheel_c
        tc.handle(pygame.event.Event(pygame.FINGERDOWN, x=cx / 1600, y=cy / 900, finger_id=1))
        tc.handle(pygame.event.Event(pygame.FINGERMOTION, x=(cx + tc.wheel_r) / 1600, y=cy / 900, finger_id=1))
        g = tc.gas.center
        tc.handle(pygame.event.Event(pygame.FINGERDOWN, x=g[0] / 1600, y=g[1] / 900, finger_id=2))
        for _ in range(20):
            c = tc.controls()
        self.assertGreater(c.steer, 0.95, "sağa sürükleme = sağa direksiyon")
        self.assertGreater(c.throttle, 0.5)
        tc.handle(pygame.event.Event(pygame.FINGERUP, x=g[0] / 1600, y=g[1] / 900, finger_id=2))
        b = tc.brake.center
        tc.handle(pygame.event.Event(pygame.FINGERDOWN, x=b[0] / 1600, y=b[1] / 900, finger_id=3))
        c = tc.controls()
        self.assertEqual(c.throttle, 0.0)
        self.assertEqual(c.brake, 1.0)
        k = tc.buttons["kamera"].center
        tc.handle(pygame.event.Event(pygame.FINGERDOWN, x=k[0] / 1600, y=k[1] / 900, finger_id=4))
        self.assertEqual(tc.take_pressed(), ["kamera"])

    def test_steer_right_turns_clockwise(self):
        for v, p in (("lrv", "moon"), ("titan_crawler", "titan")):
            t = flat(p, "organik kum" if p == "titan" else "regolit")
            r = settled(CATALOG[v], t)
            run(r, Controls(throttle=1.0, steer=1.0), 4)
            self.assertLess(r.yaw, -0.1, f"{v}: sağa direksiyon saat yönünde dönmeli")


class T10Performance(unittest.TestCase):
    def test_renderer_timing_per_quality(self):
        pygame.init()
        t = Terrain("mars")
        out = {}
        for q, (w, h, L, far) in {"low": (320, 180, 110, 380), "ultra": (640, 360, 260, 700)}.items():
            rend = TerrainRenderer(t, w, h, L, far)
            cam = Camera()
            cam.x = cam.y = t.size / 2
            cam.z = 3.0
            rend.render(cam, None)
            t0 = time.perf_counter()
            for i in range(10):
                cam.yaw = i * 0.3
                rend.render(cam, None)
            out[q] = (time.perf_counter() - t0) / 10 * 1000
        print(f"\n  arazi çizimi: düşük {out['low']:.1f} ms, ultra {out['ultra']:.1f} ms")
        self.assertLess(out["low"], out["ultra"])
        self.assertLess(out["low"], 60)

    def test_physics_step_cost(self):
        t = flat("moon")
        r = settled(CATALOG["sev"], t)
        t0 = time.perf_counter()
        run(r, Controls(throttle=1.0), 10)
        per = (time.perf_counter() - t0) / (10 / DT) * 1000
        self.assertLess(per, 8, f"fizik adımı {per:.2f} ms")


class TSpacecraftSeparate(unittest.TestCase):
    def test_no_drag_in_vacuum_momentum_conserved(self):
        s = Spacecraft2D(1000, 500, 20000, 300, 400, 2000, cd_area=4.0)
        s.vx, s.vy = 1500.0, 30.0
        for _ in range(6000):
            s.step(0.01, g=0.0, rho=0.0)
        self.assertEqual((s.vx, s.vy), (1500.0, 30.0))

    def test_drag_only_in_atmosphere(self):
        s = Spacecraft2D(1000, 500, 20000, 300, 400, 2000, cd_area=4.0)
        s.vx = 200.0
        for _ in range(100):
            s.step(0.01, g=0.0, rho=1.2)
        self.assertLess(s.vx, 200.0)

    def test_rcs_rotation_persists_until_countered(self):
        s = Spacecraft2D(1000, 500, 20000, 300, 400, 2000)
        s.rcs = 1.0
        for _ in range(100):
            s.step(0.01)
        s.rcs = 0.0
        w = s.omega
        self.assertAlmostEqual(w, 400 / 2000 * 1.0, delta=0.01)
        for _ in range(500):
            s.step(0.01)
        self.assertAlmostEqual(s.omega, w, places=9, msg="RCS bırakılınca dönüş sürmeli (sönüm yok)")
        s.sas = True
        for _ in range(500):
            s.step(0.01)
        self.assertLess(abs(s.omega), 0.01, "SAS dönüşü durdurmalı")

    def test_tsiolkovsky_delta_v(self):
        s = Spacecraft2D(1000, 500, 20000, 300, 0, 2000)
        dv0 = s.delta_v_left
        self.assertAlmostEqual(dv0, 300 * G0 * math.log(1500 / 1000), places=6)
        s.throttle = 1.0
        while s.fuel > 0:
            s.step(0.001)
        self.assertAlmostEqual(s.vy, dv0, delta=dv0 * 0.005)


if __name__ == "__main__":
    unittest.main()

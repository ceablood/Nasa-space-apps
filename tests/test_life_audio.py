# -*- coding: utf-8 -*-
"""Yaşam Motoru (KLE) ve Kozmik Ses Motoru (CAE) testleri — spesifikasyon §30 senaryoları.
Çalıştırma: python -m unittest discover -s tests -v   (pygame penceresi/ses aygıtı gerekmez)"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from aetherx.life import EventBus, LifeWorld                       # noqa: E402
from aetherx.life import environment as E                          # noqa: E402
from aetherx.life import habitability as Hb                        # noqa: E402
from aetherx.life import origin as O                               # noqa: E402
from aetherx.cae import CosmicAudio                                 # noqa: E402
from aetherx.cae import sounds as SD, synth as S                    # noqa: E402
from aetherx.cae.engine import AudioSettings, Spatial, DynamicMusic # noqa: E402


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def hf_ratio(x, f0=8000):
    X = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / S.SR)
    return float((X[f > f0] ** 2).sum() / max(1e-12, (X ** 2).sum()))


class TestEnvironmentNASA(unittest.TestCase):
    def test_nasa_values(self):
        mars, earth, venus = E.get("mars"), E.get("earth"), E.get("venus")
        self.assertAlmostEqual(mars.gravity, 3.71)
        self.assertAlmostEqual(mars.atmosphere["CO2"], 0.951)          # NASA Mars bilgi tablosu
        self.assertAlmostEqual(earth.atmosphere["O2"], 0.2095)
        self.assertEqual(venus.pressure_bar, 92.0)
        self.assertAlmostEqual(earth.escape_kms, 11.2, delta=0.1)

    def test_speed_of_sound(self):
        self.assertAlmostEqual(E.get("earth").speed_of_sound, 340, delta=6)
        self.assertAlmostEqual(E.get("mars").speed_of_sound, 240, delta=15)   # Perseverance ölçümü ~240 m/s
        self.assertEqual(E.get("moon").speed_of_sound, 0.0)

    def test_habitability_separate_from_life(self):
        r = Hb.evaluate(E.get("earth"))
        self.assertEqual(r.category, Hb.CATEGORIES[0])
        self.assertTrue(r.life_detected)
        for k in ("moon", "mars", "venus", "jupiter"):
            self.assertFalse(Hb.evaluate(E.get(k)).life_detected, k)
        ice = Hb.evaluate(E.get("buz"))
        self.assertEqual(ice.category, Hb.CATEGORIES[1])                 # buz altı okyanusu: olası
        self.assertFalse(ice.life_detected)

    def test_origin_labels(self):
        labels = {h["label"] for h in O.plausible(E.get("earth"), True)}
        self.assertIn("bilimsel hipotez", labels)
        self.assertTrue(any("kurgusal" in l for l in labels))
        _, y = O.simulate_network(E.get("earth"))
        self.assertIsNotNone(y)
        _, y2 = O.simulate_network(E.get("moon"))
        self.assertIsNone(y2)


class TestLifeScenarios(unittest.TestCase):
    def run_world(self, key, years=1000, step=5, **kw):
        bus = EventBus()
        names = []
        bus.subscribe("*", lambda e: names.append(e["name"]))
        w = LifeWorld(key, bus, **kw)
        for _ in range(int(years / step)):
            w.step(step)
        return w, names

    def test_1_forest_planet(self):
        w, _ = self.run_world("earth")
        forest = [s for s in w.species if s.biome == "tropikal orman" and s.alive]
        self.assertGreaterEqual(len(forest), 5)
        self.assertTrue(all(s.real for s in w.species))
        self.assertEqual(sum(not s.alive for s in w.species), 0, "Dünya grupları 1000 yılda yok olmamalı")

    def test_2_ocean_many_species(self):
        w, _ = self.run_world("okyanus")
        self.assertGreaterEqual(sum(s.alive for s in w.species), 10)
        self.assertTrue(all(s.kurgusal for s in w.species))

    def test_3_under_ice_life(self):
        w, _ = self.run_world("buz")
        sub = [s for s in w.species if s.alive and s.genome.habitat in ("buzaltı", "yeraltı", "su")]
        self.assertTrue(sub)

    def test_4_volcanic(self):
        w, names = self.run_world("volkanik", 200)
        w.trigger("volkan", 0.9)
        self.assertIn("VolcanicEruption", [e["name"] for e in w.bus.history])
        self.assertTrue(any(s.genome.metabolism == "kemosentez" for s in w.species))

    def test_5_storm(self):
        w, _ = self.run_world("dunya_benzeri", 50)
        w.trigger("firtina", 0.8)
        self.assertTrue(w.weather)
        for _ in range(30):
            w.step(1)
        self.assertFalse(w.weather)
        self.assertIn("StormEnded", [e["name"] for e in w.bus.history])

    def test_6_ecosystem_collapse(self):
        w, _ = self.run_world("dunya_benzeri", 100)
        before = w.stats()["biyokütle"]
        for _ in range(3):
            w.trigger("meteor", 1.0)
        self.assertLess(w.stats()["biyokütle"], before * 0.6)      # çöküş anı
        w.step(1)
        self.assertIn("EcosystemChanged", [e["name"] for e in w.bus.history])
        self.assertTrue(any("Meteor" in t[2] for t in w.timeline))

    def test_7_evolution_changes_species(self):
        w, names = self.run_world("volkanik", years=3e6, step=1e5)
        self.assertIn("Speciation", names)
        self.assertGreater(len(w.species), 16)

    def test_8_airless_world(self):
        w, _ = self.run_world("moon", 100)
        self.assertEqual(w.species, [])
        self.assertIn("yaşam bulunmamıştır", w.timeline[0][2])
        w2 = LifeWorld("mars", scenario=True)
        self.assertTrue(w2.species and all(s.kurgusal and s.kingdom == "mikrop" for s in w2.species))

    def test_9_landing_event_reaches_audio(self):
        bus = EventBus()
        clock = FakeClock()
        cae = CosmicAudio(None, bus, {}, clock)
        bus.publish("PlanetLanding", planet="mars")
        self.assertEqual(cae.events.log[-1][1], "PlanetLanding")
        self.assertIn("çalındı", cae.events.log[-1][3])

    def test_10_simultaneous_events(self):
        bus = EventBus()
        clock = FakeClock()
        cae = CosmicAudio(None, bus, {}, clock)
        w = LifeWorld("dunya_benzeri", bus)
        cae.set_scene(w, "tropikal orman")
        for k in ("volkan", "meteor", "firtina", "radyasyon", "yildiz"):
            w.trigger(k, 0.7)
        names = [e[1] for e in cae.events.log]
        for n in ("VolcanicEruption", "MeteorImpact", "StormStarted", "RadiationSpike", "StellarFlare"):
            self.assertIn(n, names)
        self.assertEqual(len(w.timeline) - sum(1 for e in w.timeline if e[1] != "olay"), 5)


class TestAudio(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.clock = FakeClock()
        self.cae = CosmicAudio(None, self.bus, {}, self.clock)

    def test_no_hiss_in_ambience(self):
        w = LifeWorld("earth", self.bus)
        self.cae.set_scene(w, "tropikal orman")
        mix = sum(self.cae.layer_buf.values())
        self.assertLess(hf_ratio(mix), 0.002)
        from aetherx import audio as A
        for name in ("amb_space", "amb_control", "amb_colony", "amb_base"):
            self.assertLess(hf_ratio(A.ambient_track(name)), 0.002, name)

    def test_loops_are_seamless(self):
        x = S.shaped_noise(SD.LOOP, 60, 900, 1.4, 1)
        self.assertLess(abs(float(x[0] - x[-1])), 0.05)       # periyodik: döngü noktasında sıçrama yok

    def test_vacuum_is_silent_outside(self):
        w = LifeWorld("moon", self.bus)
        self.cae.set_scene(w)
        tg = self.cae.layer_targets()
        for k in ("atmosfer", "okyanus", "canlı", "bitki"):
            self.assertEqual(tg[k], 0.0)
        self.assertEqual(tg["uzay aracı"], 1.0)                  # yalnız araç/giysi içi
        self.assertIsNone(SD.thunder(w.env))

    def test_mars_quieter_than_earth(self):
        e, m = E.get("earth"), E.get("mars")
        ge, gm = SD.atmosphere_profile(e)["gain"], SD.atmosphere_profile(m)["gain"]
        db = 20 * np.log10(gm / ge)
        self.assertLess(db, -15)                                 # Perseverance: ~20 dB daha zayıf
        self.assertLess(SD.atmosphere_profile(m)["hi"], SD.atmosphere_profile(e)["hi"])

    def test_distance_attenuation_and_pan(self):
        sp = Spatial()
        l1, r1, _ = sp.params((5, 0))
        l2, r2, _ = sp.params((100, 0))
        self.assertGreater(r1, r2)
        self.assertGreater(r1, l1)                               # sağdaki kaynak sağ kulakta güçlü
        lm, rm, _ = sp.params((50, 0), mono=True)
        self.assertAlmostEqual(lm, rm)

    def test_event_dedupe_and_budget(self):
        self.bus.publish("SpeciesExtinction", species="A", biome="b")
        self.bus.publish("SpeciesExtinction", species="A", biome="b")
        self.assertIn("yinelenen", self.cae.events.log[-1][3])
        self.cae.events.MAX_VOICES = 1
        self.bus.publish("PlanetLanding", planet="x")
        self.clock.t += 0.1
        self.bus.publish("Speciation", species="Z")              # düşük öncelik, bütçe dolu
        self.assertIn("bütçe", self.cae.events.log[-1][3])

    def test_species_voice_from_biology(self):
        w = LifeWorld("earth", self.bus)
        by = {s.name: s for s in w.species}
        def f0(x):
            X = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / S.SR)
            return f[np.argmax(X[1:]) + 1]
        big, small = SD.species_voice(by["Büyük memeliler (yırtıcı)"]), SD.species_voice(by["Böcekler"])
        self.assertLess(f0(big), f0(small))                      # büyük beden = alçak ses
        self.assertTrue(np.array_equal(SD.species_voice(by["Kuşlar"]), SD.species_voice(by["Kuşlar"])))  # rastgele değil

    def test_settings_persist_and_accessibility(self):
        store = {}
        st = AudioSettings(store)
        st.set("canlı", 0.3)
        st.set("reduce_high", True)
        st2 = AudioSettings(store)
        self.assertAlmostEqual(st2["vol"]["canlı"], 0.3)
        x = S.shaped_noise(2.0, 2000, 9000, 0.0, 3)
        self.assertLess(hf_ratio(st2.process(x), 5000), hf_ratio(x, 5000) * 0.2)
        self.assertLessEqual(float(np.max(np.abs(st2.process(x * 3)))), 0.71)   # ani ses sınırlayıcı

    def test_music_crossfade_dwell(self):
        m = DynamicMusic(None)
        self.assertTrue(m.request("gezegen keşfi", 0.0))
        self.assertFalse(m.request("tehlikeli bölge", 2.0))       # en kısa kalma süresi
        m.update(10.0)
        self.assertEqual(m.state, "tehlikeli bölge")

    def test_cache_budget(self):
        self.cae.assets.budget = 2 * 1024 * 1024
        for i in range(10):
            self.cae.assets.put(f"k{i}", np.zeros(S.SR * 2, dtype=np.float32))
        self.assertLessEqual(self.cae.assets.bytes, 2 * 1024 * 1024)
        self.assertGreater(self.cae.assets.evicted, 0)

    def test_microbial_is_labelled_representation(self):
        meta = self.cae.assets.meta["mikrobiyal temsil"]
        self.assertIn("temsil", meta["amaç"])
        self.assertIn("Özgün", meta["lisans"])
        self.assertEqual(self.cae.assets.meta["motor"]["etiket"], "sinematik")


if __name__ == "__main__":
    unittest.main()

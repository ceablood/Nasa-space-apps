# -*- coding: utf-8 -*-
"""NOVA sohbet motoru testleri: niyet tanıma, bağlam, gerçek fizik değerleri, Türkçe ekler, sıralama sunucusu doğrulaması.
Çalıştırma: python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if "aetherx.config" not in sys.modules:                            # kayıtlar geçici dizine (gerçek ev dizini kirlenmesin)
    import tempfile
    os.environ["HOME"] = tempfile.mkdtemp(prefix="aetherx_test_")

from aetherx import i18n                                           # noqa: E402
from aetherx.nova_ai import NovaAI, lexicon as LX, physics as P    # noqa: E402
from aetherx.nova_ai import facts as F, concepts as CO             # noqa: E402


class Physics(unittest.TestCase):
    def test_earth_mars_hohmann(self):
        t = P.transfer("earth", "mars")
        self.assertAlmostEqual(t["days"], 259, delta=3)            # bilinen değer ~259 gün
        self.assertAlmostEqual(t["dv_depart"], 2945, delta=60)

    def test_synodic(self):
        self.assertAlmostEqual(P.synodic_days("earth", "mars"), 780, delta=5)

    def test_escape_and_orbit(self):
        self.assertAlmostEqual(P.escape_velocity("earth") / 1000, 11.2, delta=0.1)
        self.assertAlmostEqual(P.escape_velocity("moon") / 1000, 2.38, delta=0.05)
        self.assertAlmostEqual(P.orbital_velocity("earth", 400) / 1000, 7.67, delta=0.03)
        self.assertAlmostEqual(P.orbital_period("earth", 400) / 60, 92.6, delta=1.0)

    def test_surface_gravity_matches_table(self):
        # Gaz devleri hariç: NASA'nın 'g' değeri 1 bar düzeyinde ekvator yarıçapı + dönme etkisiyle verilir (μ/r² ortalama yarıçapta farklı).
        for k in ("earth", "moon", "mars", "venus", "mercury", "titan", "europa"):
            self.assertAlmostEqual(P.surface_gravity(k), F.BODIES[k]["g"], delta=F.BODIES[k]["g"] * 0.06, msg=k)

    def test_rocket_equation(self):
        self.assertAlmostEqual(P.tsiolkovsky(300, 100, 30), 300 * 9.80665 * 1.2039728, delta=1)
        self.assertEqual(P.tsiolkovsky(300, 10, 20), 0.0)

    def test_light_delay_mars(self):
        lo, hi = P.light_delay("earth", "mars")
        self.assertTrue(3 * 60 < lo < 5 * 60 and 20 * 60 < hi < 23 * 60)


class Lexicon(unittest.TestCase):
    def test_bodies(self):
        self.assertEqual(LX.find_bodies(LX.normalize("Mars'ta yerçekimi")), ["mars"])
        self.assertEqual(LX.find_bodies(LX.normalize("Dünya'dan Jüpiter'e kaç gün")), ["earth", "jupiter"])
        self.assertEqual(LX.find_bodies(LX.normalize("bu ay çok çalıştım")), [])       # "ay" = month
        self.assertEqual(LX.find_bodies(LX.normalize("Ay'da bir gün")), ["moon"])

    def test_suffixes(self):
        got = [LX.ek(n, c) for n, c in (("Mars", "da"), ("Venüs", "a"), ("Dünya", "in"), ("Ay", "da"), ("Jüpiter", "dan"))]
        self.assertEqual(got, ["Mars'ta", "Venüs'e", "Dünya'nın", "Ay'da", "Jüpiter'den"])

    def test_concepts(self):
        self.assertEqual(CO.find(LX.normalize("Delta-v nedir?")), "delta_v")
        self.assertEqual(CO.find(LX.normalize("what is a hohmann transfer")), "hohmann")


class Dialogue(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("en")

    def test_english_flow(self):
        i18n.set_lang("en")
        ai = NovaAI()
        self.assertIn("3.70 m/s²", ai.reply("What is the gravity on Mars?"))
        self.assertIn("Venus", ai.reply("and Venus?"))                                 # bağlam: aynı niyet, yeni cisim
        self.assertIn("464", ai.reply("What is the temperature there?"))              # bağlam: son cisim
        self.assertIn("Delta-v", ai.reply("what is delta-v?"))
        self.assertIn("days", ai.reply("How many days from Earth to Mars?"))
        self.assertIn("13.1 kg", ai.reply("How much does 80 kg weigh on the Moon?"))
        self.assertIn("3.78 km/s", ai.reply("rocket equation isp 320 mass 500 t dry 150 t"))
        self.assertIn("help", ai.reply("asdkjh"))

    def test_turkish_flow(self):
        i18n.set_lang("tr")
        ai = NovaAI()
        self.assertIn("Mars'ın yüzey çekimi 3,70", ai.reply("Mars'ta yerçekimi ne kadar?"))
        self.assertIn("Ay'ın yüzey çekimi", ai.reply("peki ya Ay?"))
        self.assertIn("29,5 gün", ai.reply("Ay'da bir gün ne kadar sürer"))
        self.assertIn("Apollo 11", ai.reply("Ay görevleri"))
        self.assertIn("ajans kurmalı", ai.reply("ne yapmalıyım"))                     # kampanya yokken dürüst yanıt

    def test_all_bodies_all_attrs(self):
        for lang in ("en", "tr"):
            i18n.set_lang(lang)
            ai = NovaAI()
            for b in F.BODIES:
                for a in ("facts", "gravity", "temp", "day", "year", "distance", "moons", "atmo", "size", "mass", "escape",
                          "missions", "hazards", "weight", "jump", "sunlight", "orbit_calc"):
                    out = getattr(ai, "a_" + a)(b, [], "")
                    self.assertTrue(isinstance(out, str) and len(out) > 10, (lang, b, a))


class GameAware(unittest.TestCase):
    def setUp(self):
        from aetherx import data as D
        from aetherx.game import Game
        from aetherx.nova import NovaBrain
        self.g = Game()
        self.g.new("ORION", (62, 230, 255))
        self.g.s["inventory"]["moon_rock"] = 40
        self.g.s["colonies"]["moon"] = {"planet": "moon", "founded": 1, "level": 1, "pop": 10.0, "happiness": 40.0,
                                        "buildings": {b["key"]: 1 for b in D.COLONY_BUILDINGS}, "storage": 0.0,
                                        "food": 60.0, "happy_buff": 0.0}
        self.brain = NovaBrain(self.g)

    def tearDown(self):
        i18n.set_lang("en")

    def test_state_answers(self):
        i18n.set_lang("en")
        ai = NovaAI(self.g, self.brain)
        self.assertIn("×40", ai.reply("my depot"))
        self.assertIn("Crew", ai.reply("my crew"))
        self.assertIn("RP", ai.reply("what to research"))
        self.assertIn("locked", ai.reply("what do I need to go to Mars?"))
        self.assertIn("Moon colony", ai.reply("how is my moon colony"))
        self.assertIn("Fuel", ai.reply("my fuel"))
        i18n.set_lang("tr")
        ai = NovaAI(self.g, self.brain)
        self.assertIn("Ay kolonisi", ai.reply("Ay kolonim nasıl"))
        self.assertIn("Koloni kurmak", ai.reply("Ay'da koloni nasıl kurulur"))

    def test_quiz_and_convert(self):
        i18n.set_lang("en")
        ai = NovaAI()
        q = ai.reply("quiz")
        self.assertTrue(q.startswith("Question:"))
        kind, ans = ai.quiz.pending[1], ai.quiz.pending[2]
        reply = {"body": {"saturn": "Saturn", "mercury": "Mercury", "venus": "Venus", "ganymede": "Ganymede"}.get(ans, "x")}.get(kind, str(ans))
        self.assertTrue(ai.reply(reply).startswith("Correct"))
        self.assertIn("28,080 km/h", ai.reply("7.8 km/s in km/h"))
        self.assertIn("93.1 K", ai.reply("-180 C to kelvin"))


class LeaderboardServer(unittest.TestCase):
    def test_clean(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))
        import leaderboard_server as LS
        ok = LS.clean({"id": "a1b2c3d4e5f60718", "name": "ORION", "score": 1200, "money": 5000, "level": 2, "colonies": 1})
        self.assertIsNotNone(ok)
        self.assertIsNone(LS.clean({"id": "not hex!", "name": "x", "score": 1}))
        self.assertIsNone(LS.clean({"id": "a1b2c3d4e5f60718", "name": "x", "score": -5}))


if __name__ == "__main__":
    unittest.main()

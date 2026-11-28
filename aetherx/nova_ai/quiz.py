# -*- coding: utf-8 -*-
"""
NOVA BİLGİ YARIŞMASI + BİRİM ÇEVİRİCİ
Sorular facts.py / physics.py'deki gerçek veriden üretilir; sayısal yanıtlarda ±%15 tolerans vardır.
"""
import random
import re

from . import facts as F
from . import lexicon as LX
from . import physics as P
from .tx import pick as _pick

NUM_TOL = 0.15


class Quiz:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.pending = None          # (soru_tr, soru_en, tür, doğru yanıt, açıklama (tr,en))
        self.score = 0
        self.asked = 0

    # ------------------------------------------------------------- soru üretimi
    def new_question(self):
        r = self.rng
        kind = r.choice(("gravity", "day", "moons_max", "closest", "transfer", "temp", "largest_moon", "moons_n", "hottest"))
        nm = lambda k: (F.name(k, "tr"), F.name(k, "en"))
        if kind == "gravity":
            k = r.choice(("moon", "mars", "venus", "jupiter", "titan", "mercury"))
            g = F.BODIES[k]["g"]
            q = (f"{LX.ek(nm(k)[0], 'in')} yüzey çekimi yaklaşık kaç m/s²?", f"What is the surface gravity of {nm(k)[1]} in m/s²?")
            self.pending = (q, "num", g, (f"{g} m/s²", f"{g} m/s²"))
        elif kind == "day":
            k = r.choice(("mars", "jupiter", "saturn", "moon", "venus"))
            h = F.BODIES[k]["day"]
            q = (f"{LX.ek(nm(k)[0], 'da')} bir gün (güneş doğuşundan doğuşa) kaç saat sürer?",
                 f"How many hours is a solar day on {nm(k)[1]}?")
            self.pending = (q, "num", h, (f"{P.fmt_num(h, 1, True)} saat", f"{h} hours"))
        elif kind == "transfer":
            k = r.choice(("mars", "venus", "jupiter"))
            d = P.transfer("earth", k)["days"]
            q = (f"Dünya'dan {LX.ek(nm(k)[0], 'a')} Hohmann transferi kaç gün sürer?",
                 f"How many days does a Hohmann transfer from Earth to {nm(k)[1]} take?")
            self.pending = (q, "num", round(d), (f"~{round(d)} gün", f"~{round(d)} days"))
        elif kind == "temp":
            k = r.choice(("venus", "mars", "moon", "titan", "mercury"))
            t = F.BODIES[k]["temp"]
            q = (f"{LX.ek(nm(k)[0], 'in')} ortalama sıcaklığı yaklaşık kaç °C?", f"What is the average temperature of {nm(k)[1]} in °C?")
            self.pending = (q, "temp", t, (f"~{t} °C", f"~{t} °C"))
        elif kind == "moons_n":
            k = r.choice(("mars", "earth", "neptune", "uranus"))
            n = F.BODIES[k]["moons"]
            q = (f"{LX.ek(nm(k)[0], 'in')} bilinen kaç doğal uydusu var?", f"How many known moons does {nm(k)[1]} have?")
            self.pending = (q, "exact", n, (str(n), str(n)))
        elif kind == "moons_max":
            q = ("Bilinen uydu sayısı en fazla olan gezegen hangisi?", "Which planet has the most known moons?")
            self.pending = (q, "body", "saturn", (f"Satürn ({F.BODIES['saturn']['moons']})", f"Saturn ({F.BODIES['saturn']['moons']})"))
        elif kind == "closest":
            q = ("Güneş'e en yakın gezegen hangisi?", "Which planet is closest to the Sun?")
            self.pending = (q, "body", "mercury", ("Merkür", "Mercury"))
        elif kind == "hottest":
            q = ("Yüzeyi en sıcak gezegen hangisi?", "Which planet has the hottest surface?")
            self.pending = (q, "body", "venus", ("Venüs (~464 °C; Merkür'den de sıcak)", "Venus (~464 °C, hotter than Mercury)"))
        else:
            q = ("Güneş Sistemi'nin en büyük uydusu hangisi?", "What is the largest moon in the Solar System?")
            self.pending = (q, "body", "ganymede", ("Ganymede", "Ganymede"))
        self.asked += 1
        return q

    # ------------------------------------------------------------- yanıt değerlendirme
    def check(self, text):
        """(doğru_mu, açıklama (tr,en)) — bekleyen soru yoksa None."""
        if not self.pending:
            return None
        q, kind, ans, expl = self.pending
        norm = LX.normalize(text)
        ok = False
        if kind == "body":
            ok = ans in LX.find_bodies(norm) or ans in norm
        else:
            vals = [v for v, _, _ in LX.numbers(norm)]
            if vals:
                v = vals[0]
                if kind == "exact":
                    ok = int(round(v)) == ans
                elif kind == "temp":
                    if v > 0 and ans < 0 and ("eksi" in norm or "minus" in norm):
                        v = -v
                    ok = abs(v - ans) <= max(15, abs(ans) * NUM_TOL)
                else:
                    ok = abs(v - ans) <= abs(ans) * NUM_TOL
        self.pending = None
        if ok:
            self.score += 1
        return ok, expl

    def skip(self):
        if not self.pending:
            return None
        expl = self.pending[3]
        self.pending = None
        return expl


# ----------------------------------------------------------------- birim çevirici
_CONV = [
    (r"(-?\d+(?:[.,]\d+)?)\s*km/s", "kms"),
    (r"(-?\d+(?:[.,]\d+)?)\s*(?:km/sa|km/h|kmh)", "kmh"),
    (r"(-?\d+(?:[.,]\d+)?)\s*(?:au|ab)\b", "au"),
    (r"(-?\d+(?:[.,]\d+)?)\s*(?:isik yili|light years?|ly)\b", "ly"),
    (r"(-?\d+(?:[.,]\d+)?)\s*(?:°?c|derece|celsius)\b", "c"),
    (r"(-?\d+(?:[.,]\d+)?)\s*(?:kelvin|k)\b", "k"),
    (r"(-?\d+(?:[.,]\d+)?)\s*(?:mil|miles?)\b", "mi"),
]


def convert(norm, tr_):
    """'7,8 km/s kaç km/sa', '5 AU kaç km', '-180 derece kelvin' ... -> metin ya da None."""
    for rx, kind in _CONV:
        m = re.search(rx, norm)
        if not m:
            continue
        v = float(m.group(1).replace(",", "."))
        f = lambda x, d=1: P.fmt_num(x, d, tr_)
        if kind == "kms":
            return f"{f(v, 2)} km/s = {f(v * 3600, 0)} km/" + (_pick(tr_, "sa", "h")) + (
                _pick(tr_, f" ({_pick(tr_, 'ışık hızının', 'of light speed')} %{f(v / 299792.458 * 100, 4)})", f" ({f(v / 299792.458 * 100, 4)}% of light speed)"))
        if kind == "kmh":
            return f"{f(v, 0)} km/" + (_pick(tr_, "sa", "h")) + f" = {f(v / 3600, 3)} km/s"
        if kind == "au":
            km = v * P.AU / 1000
            return f"{f(v, 2)} AU = {f(km / 1e6, 1)} " + (_pick(tr_, "milyon km", "million km")) + (
                f"; {_pick(tr_, 'ışık', 'light')} {P.fmt_dur(v * P.AU / P.C_LIGHT, tr_)}")
        if kind == "ly":
            return f"{f(v, 2)} " + (_pick(tr_, "ışık yılı", "light years")) + f" = {f(v * 9.4607e12 / 1e12, 2)} " + (
                _pick(tr_, "trilyon km", "trillion km"))
        if kind == "c":
            return f"{f(v, 1)} °C = {f(v + 273.15, 1)} K = {f(v * 9 / 5 + 32, 1)} °F"
        if kind == "k":
            return f"{f(v, 1)} K = {f(v - 273.15, 1)} °C"
        if kind == "mi":
            return f"{f(v, 1)} " + (_pick(tr_, "mil", "miles")) + f" = {f(v * 1.609344, 1)} km"
    return None

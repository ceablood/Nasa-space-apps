# -*- coding: utf-8 -*-
"""
NOVA ZİHNİ — duygular, düşünme süresi ve insan gibi temkinli konuşma.
Duygular (0..1): neşe, merak, endişe, gurur, hüzün. Oyundaki gerçek olaylardan (görev sonuçları, para, fırtına, hasta
ekip, koloni mutluluğu) ve sohbetten (teşekkür, kaba söz, ilginç soru) beslenir; zamanla taban düzeyine söner.
Baskın duygu NOVA'nın yüzünün rengini/ifadesini ve cümlelerinin tonunu belirler. Bu bir benzetimdir: NOVA gerçekten
hissetmez; duygu değerleri oyun durumundan hesaplanan sayılardır ve ekranda açıkça gösterilir.
"""
import math
import random
from .tx import pick as _pick
from . import tx as _tx

EMOS = ("joy", "curiosity", "worry", "pride", "sadness")
NAME = {"joy": ("neşeli", "cheerful"), "curiosity": ("meraklı", "curious"), "worry": ("endişeli", "worried"),
        "pride": ("gururlu", "proud"), "sadness": ("hüzünlü", "a bit down"), "calm": ("sakin", "calm")}
BASE = {"joy": 0.25, "curiosity": 0.35, "worry": 0.1, "pride": 0.1, "sadness": 0.05}
HALF_LIFE = 90.0                  # sn: duygu tabana yarı yolda döner

OPEN = {
    "joy": (("Güzel soru! ", "Hemen bakayım. ", ""), ("Great question! ", "Let me check. ", "")),
    "curiosity": (("Bu ilginç… ", "Hmm, bunu düşünmeyi seviyorum. ", ""), ("Interesting… ", "Hmm, I like thinking about this. ", "")),
    "worry": (("Bir yandan fırtınaları izliyorum ama söyleyeyim: ", "", "Dikkatle bakıyorum: "),
              ("I'm keeping an eye on things, but here goes: ", "", "Looking carefully: ")),
    "pride": (("Ajansımızla gurur duyuyorum. ", "", ""), ("I'm proud of our agency. ", "", "")),
    "sadness": (("", "Biraz durgunum ama yardımcı olayım: "), ("", "I'm a little down, but let me help: ")),
    "calm": (("",), ("",)),
}


class Mind:
    def __init__(self):
        self.e = dict(BASE)
        self.t = 0.0
        self._seen = {}
        self.rng = random.Random()

    # ------------------------------------------------------------- dinamik
    def bump(self, emo, amt):
        self.e[emo] = max(0.0, min(1.0, self.e[emo] + amt))

    def update(self, dt, game=None):
        k = 1 - math.exp(-dt * math.log(2) / HALF_LIFE)
        for m in EMOS:
            self.e[m] += (BASE[m] - self.e[m]) * k
        self.t += dt
        if game is not None and game.s and (dt == 0 or int(self.t * 2) != int((self.t - dt) * 2)):
            self._observe(game)

    def _observe(self, g):
        """Oyun durumundan gelen olaylar: yalnız değişimlere tepki verir."""
        st = g.s["stats"]
        prev = self._seen
        cur = {"success": st.get("success", 0), "fail": st.get("fail", 0), "partial": st.get("partial", 0),
               "ach": len(g.s.get("achievements", [])), "level": g.s["agency"]["level"],
               "research": len(g.s["research"]["done"]),
               "cols": sum(1 for c in g.s["colonies"].values() if c)}
        if prev:
            if cur["success"] > prev["success"]:
                self.bump("joy", 0.35); self.bump("pride", 0.3); self.bump("worry", -0.2)
            if cur["fail"] > prev["fail"]:
                self.bump("sadness", 0.35); self.bump("worry", 0.25); self.bump("joy", -0.2)
            if cur["partial"] > prev["partial"]:
                self.bump("worry", 0.1); self.bump("curiosity", 0.1)
            if cur["ach"] > prev["ach"] or cur["level"] > prev["level"] or cur["cols"] > prev["cols"]:
                self.bump("pride", 0.4); self.bump("joy", 0.25)
            if cur["research"] > prev["research"]:
                self.bump("curiosity", 0.3); self.bump("joy", 0.1)
        self._seen = cur
        # sürekli koşullar (hafif, her yoklamada)
        try:
            if g.storm_active():
                self.bump("worry", 0.02)
        except Exception:
            pass
        sick = sum(1 for c in g.s["crew"] if c["status"] == "sick")
        if sick:
            self.bump("worry", 0.01 * sick)
        if g.money < 500:
            self.bump("worry", 0.015)
        cols = [c for c in g.s["colonies"].values() if c]
        if cols and min(c["happiness"] for c in cols) < 35:
            self.bump("worry", 0.01); self.bump("sadness", 0.005)

    def hear(self, norm, intent):
        """Sohbetin duygulara etkisi."""
        toks = set(norm.split())
        if toks & {"tesekkur", "tesekkurler", "sagol", "thanks", "thank", "harika", "super", "great", "awesome", "seviyorum",
                   "aferin", "bravo", "mukemmel"}:
            self.bump("joy", 0.3); self.bump("sadness", -0.2)
        if toks & {"aptal", "salak", "stupid", "useless", "dumb", "kotu", "berbat", "isesiz", "ise", "yaramaz"} and \
                not toks & {"degil", "not"}:
            self.bump("sadness", 0.3); self.bump("joy", -0.2)
        if intent in ("concept", "facts", "transfer", "rocket_eq", "missions", "compare", "asteroids", "exoplanets",
                      "earth_events", "tuik", "quiz"):
            self.bump("curiosity", 0.12)

    # ------------------------------------------------------------- ifade
    def dominant(self):
        m = max(EMOS, key=lambda k: self.e[k] - BASE[k])
        return m if self.e[m] - BASE[m] > 0.08 else "calm"

    def face(self):
        return {"joy": "happy", "pride": "happy", "curiosity": "think", "worry": "worried", "sadness": "sad"}.get(self.dominant(), "calm")

    def label(self, tr_):
        return NAME[self.dominant()][0] if tr_ else _tx.translate(NAME[self.dominant()][1])

    def opener(self, tr_):
        ops = OPEN[self.dominant()][0 if tr_ else 1]
        o = self.rng.choice(ops)
        return o if tr_ else _tx.translate(o)

    def hedge(self, conf, tr_):
        """Güvene göre insan gibi temkin: %90+ düz söyler, altında 'sanırım', %60 altında 'emin değilim'."""
        p = int(round(conf * 100))
        if conf >= 0.9:
            return ""
        if conf >= 0.7:
            return (_pick(tr_, f"Sanırım bunu soruyorsun (%{p} eminim): ", f"I think this is what you mean ({p}% sure): "))
        return (_pick(tr_, f"Emin değilim (yalnız %{p}), ama tahminim şu: ", f"I'm not sure (only {p}%), but my best guess: "))

    def think_time(self, intent, text_len):
        """Yanıt öncesi düşünme süresi (sn): hesap ve veri sorgusu daha uzun; meraklıyken biraz daha düşünür."""
        base = {"rocket_eq": 1.4, "transfer": 1.3, "compare": 1.1, "tuik": 1.2, "asteroids": 1.6, "exoplanets": 1.3,
                "earth_events": 1.4, "design_check": 1.2, "research_next": 1.0, "chance": 1.3, "quiz": 0.8}.get(intent, 0.6)
        t = base + min(0.8, text_len / 120) + self.e["curiosity"] * 0.4 + self.rng.uniform(0.0, 0.35)
        return min(3.2, t)

    def chips(self, tr_):
        """Ekranda gösterilecek duygu çubukları: [(ad, değer)]."""
        names = {"joy": ("Neşe", "Joy"), "curiosity": ("Merak", "Curiosity"), "worry": ("Endişe", "Worry"),
                 "pride": ("Gurur", "Pride"), "sadness": ("Hüzün", "Sadness")}
        return [(names[k][0] if tr_ else _tx.translate(names[k][1]), self.e[k]) for k in EMOS]

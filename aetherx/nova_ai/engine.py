# -*- coding: utf-8 -*-
"""
NOVA SOHBET MOTORU — serbest metinli soruları anlar ve yanıtlar.
Akış: normalize -> varlıklar (gök cismi, sayılar) -> niyet puanlama -> yanıtlayıcı -> bağlam belleği.
Yanıt dili oyunun diline göre seçilir: Türkçe ya da İngilizce (diğer dillerde İngilizce yanıt verilir).
Kaynaklar: facts.py (NASA gerçek veri), physics.py (formüller), concepts.py (sözlük), howto.py (oyun rehberi),
ve canlı oyun durumu (game.Game).
"""
import random

from .. import i18n
from . import concepts as CO
from . import facts as F
from . import howto as HT
from . import lexicon as LX
from . import physics as P

# niyet -> anahtar sözcükler (normalize, kök ya da tam)
INTENT_WORDS = {
    "greet": ("merhaba", "selam", "hello", "hi", "hey", "gunaydin", "iyi aksamlar", "good morning", "hallo", "bonjour", "hola",
              "privet", "naber", "nasilsin", "how are you"),
    "thanks": ("tesekkur", "sagol", "eyvallah", "thanks", "thank you", "thx", "danke", "merci", "gracias", "spasibo"),
    "identity": ("sen kimsin", "kimsin", "who are you", "what are you", "nova kim", "adin ne", "your name", "nesin"),
    "help": ("yardim", "help", "ne yapabilirsin", "what can you do", "neler sorabilirim", "komut", "commands", "ornek"),
    "gravity": ("yercekimi", "cekim", "gravity", "g kuvveti", "kutle cekimi", "gravitasyon", "schwerkraft", "gravite", "gravedad"),
    "temp": ("sicaklik", "derece", "sicak", "soguk", "temperature", "temp", "hot", "cold", "isi"),
    "day": ("gun uzunlugu", "bir gun", "gunu", "day length", "how long is a day", "donus", "rotation", "sol"),
    "year": ("bir yil", "yili", "yil uzunlugu", "year", "yorunge suresi", "orbital period", "gunes etrafinda"),
    "distance": ("uzaklik", "mesafe", "ne kadar uzak", "kac km", "distance", "how far", "far"),
    "moons": ("uydu", "uydusu", "moons", "satellites", "kac uydu", "how many moons"),
    "atmo": ("atmosfer", "hava", "atmosphere", "air", "gaz", "basinc", "pressure", "nefes", "breathe"),
    "size": ("buyukluk", "buyuk", "boyut", "yaricap", "cap", "size", "radius", "diameter", "big", "kucuk", "small"),
    "mass": ("kutle", "mass", "agir", "heavy"),
    "escape": ("kacis", "escape"),
    "missions": ("gorevler", "gorev", "mission", "missions", "kim gitti", "who visited", "visited", "tarih", "history",
                 "arac", "probe", "sonda", "rover", "gezgin", "ziyaret"),
    "hazards": ("tehlike", "zorluk", "riskler", "hazard", "danger", "dangers", "challenge", "yasanabilir", "habitable",
                "yasayabilir", "survive", "hayatta"),
    "compare": ("karsilastir", "kiyasla", "compare", "versus", "vs", "fark", "difference", "hangisi"),
    "transfer": ("transfer", "yolculuk", "ne kadar surer", "kac gun", "gitmek", "gidis", "how long", "travel", "trip",
                 "ulasmak", "varmak", "reach", "fly to", "gitsem"),
    "delay": ("gecikme", "delay", "sinyal", "signal", "iletisim", "communication", "radyo", "radio", "isik ne kadar", "light time"),
    "weight": ("kilom", "kac kilo", "agirligim", "weight", "weigh", "tartilir", "kilo gelir"),
    "jump": ("ziplama", "zipla", "jump", "sicrama"),
    "sunlight": ("gunes isigi", "isinim", "sunlight", "solar flux", "irradiance", "panel verimi", "gunes enerjisi ne kadar"),
    "rocket_eq": ("roket denklemi", "tsiolkovsky", "rocket equation", "delta v hesapla", "dv hesapla", "isp"),
    "orbit_calc": ("yorunge hizi", "orbital velocity", "orbit speed", "yorunge periyodu", "orbital period at", "yorungede"),
    "facts": ("hakkinda", "anlat", "bilgi", "tell me", "about", "nedir", "what is", "facts", "ilginc", "interesting", "bahset"),
    # oyun
    "advice": ("ne yapmaliyim", "ne yapayim", "tavsiye", "oneri", "advice", "what should i do", "next step", "siradaki"),
    "suggest": ("gorev oner", "nereye gideyim", "where should i go", "suggest mission", "hedef oner", "nereye"),
    "forecast": ("tahmin", "forecast", "hava durumu", "firtina ne zaman", "when storm", "uzay havasi"),
    "best_time": ("en iyi firlatma", "ne zaman firlatayim", "best launch", "when to launch", "firlatma saati"),
    "status": ("durum", "durumum", "status", "rapor", "report", "ozet", "summary", "nasil gidiyor", "how am i doing"),
    "colonies": ("kolonilerim", "koloniler nasil", "my colonies", "colony status", "koloni durumu"),
    "money_now": ("ne kadar param", "kac param", "how much money", "bakiye", "balance", "kasam"),
    "score_now": ("skorum", "puanim", "my score", "siram", "my rank", "kacinci"),
    "game_time": ("saat kac", "oyun saati", "what time", "hangi gun", "kacinci gun", "game time"),
    "joke": ("saka", "fikra", "joke", "funny", "komik", "guldur"),
}

# Genel sözcüklerle tetiklenen niyetler daha düşük ağırlık alır (özgül niyet kazansın)
INTENT_WEIGHT = {"facts": 0.4, "status": 0.8, "distance": 0.9, "size": 0.8, "mass": 0.8, "transfer": 0.9, "joke": 1.3}

# Bir niyet bir gök cismi gerektiriyorsa (bağlamdan da gelebilir)
BODY_INTENTS = {"gravity", "temp", "day", "year", "distance", "moons", "atmo", "size", "mass", "escape", "missions", "hazards",
                "weight", "jump", "sunlight", "orbit_calc", "facts"}
GAME_INTENTS = {"advice", "suggest", "forecast", "best_time", "status", "colonies", "money_now", "score_now", "game_time"}

JOKES = [("Astronotlar neden asla çay içmez? Çünkü bardaklar yörüngeye girer.", "Why don't astronauts drink tea? The cups keep going into orbit."),
         ("Bir atom diğerine: 'Bir elektronumu kaybettim!' — 'Emin misin?' — 'Evet, pozitifim.'",
          "One atom to another: 'I lost an electron!' 'Are you sure?' 'Yes, I'm positive.'"),
         ("Ay neden hiç aç değil? Çünkü hep dolunay.", "Why is the Moon never hungry? It's always full."),
         ("Uzayda kimse seni duyamaz; ama hesaplarını yine de iki kez kontrol ederim.",
          "In space no one can hear you scream, but I still double-check your math.")]


class NovaAI:
    """Tek oturumluk sohbet beyni. game: game.Game (None olabilir: menüde genel bilgi)."""

    def __init__(self, game=None, brain=None):
        self.game = game
        self.brain = brain                 # nova.NovaBrain (oyun durumuna dayalı tavsiyeler)
        self.last_body = None
        self.last_intent = None
        self.turns = 0

    # ------------------------------------------------------------- dil
    @property
    def tr_(self):
        return i18n.LANG == "tr"

    def L(self, pair):
        return pair[0] if self.tr_ else pair[1]

    def nm(self, key):
        return F.name(key, "tr" if self.tr_ else "en")

    # ------------------------------------------------------------- ana giriş
    def reply(self, text):
        text = (text or "").strip()
        if not text:
            return self.L(("Bir şey yazmadın. Örneğin: 'Mars'ta yerçekimi ne kadar?'", "You didn't type anything. Try: 'What is the gravity on Mars?'"))
        self.turns += 1
        norm = LX.normalize(text)
        bodies = LX.find_bodies(norm)
        nums = LX.numbers(norm)
        intent, score = self.classify(norm, bodies, nums)
        # "peki ya Mars?" / "what about Venus?" -> önceki niyeti yeni cisimle tekrarla
        if intent in (None, "facts") and bodies and self.last_intent in BODY_INTENTS and LX.has_any(
                norm, ("peki", "ya", "what about", "and", "how about", "ayrica", "bunu", "onun", "its")) and len(LX.tokens(norm)) <= 5:
            intent = self.last_intent
        if not bodies and self.last_intent in BODY_INTENTS and "ay" in LX.tokens(norm) and len(LX.tokens(norm)) <= 4:
            bodies = ["moon"]                              # "peki ya Ay?" — kısa takip sorusunda Ay = Moon
            if intent is None:
                intent = self.last_intent
        pronoun = LX.has_any(norm, ("onun", "orada", "orasi", "bunun", "its", "it", "there", "peki", "ya", "what about", "how about"))
        if intent in BODY_INTENTS and not bodies and self.last_body and (intent != "facts" or pronoun):
            bodies = [self.last_body]
        try:
            out = self.dispatch(intent, norm, bodies, nums, text)
        except Exception as ex:            # hesap/veri hatası sohbeti kırmasın
            out = self.L(("Bunu hesaplarken bir sorun çıktı", "Something went wrong while working that out")) + f" ({type(ex).__name__})."
        if bodies:
            self.last_body = bodies[-1] if intent in ("transfer", "delay", "compare") else bodies[0]
        if intent:
            self.last_intent = intent
        return out

    # ------------------------------------------------------------- niyet
    def classify(self, norm, bodies, nums):
        scores = {}
        toks = set(LX.tokens(norm))
        stems_ = set(LX.stems(norm))
        for intent, words in INTENT_WORDS.items():
            s = 0.0
            for w in words:
                if " " in w:
                    if w in norm:
                        s += 2.0 + 0.1 * len(w)
                elif w in toks:
                    s += 1.5
                elif w in stems_ or (len(w) >= 5 and any(t.startswith(w) for t in toks)):
                    s += 1.0
            if s:
                scores[intent] = s * INTENT_WEIGHT.get(intent, 1.0)
        # bağlam ipuçları
        if len(bodies) >= 2:
            if "transfer" in scores or LX.has_any(norm, ("dan", "den", "from", "to", "e", "a")):
                scores["transfer"] = scores.get("transfer", 0) + 0.8
            if "delay" in scores:
                scores["delay"] += 1.5
            if "compare" in scores:
                scores["compare"] += 1.5
        if "transfer" in scores and len(bodies) < 2 and not LX.has_any(norm, ("dan", "den", "tan", "ten", "from", "to", "a", "e", "ya", "ye")):
            scores["transfer"] *= 0.4                      # "Ay'da bir gün ne kadar sürer" yolculuk sorusu değil
        if bodies and not scores:
            scores["facts"] = 0.5
        if nums and ("rocket_eq" in scores or LX.has_any(norm, ("isp",))):
            scores["rocket_eq"] = scores.get("rocket_eq", 0) + 2.0
        if nums and bodies and "weight" in scores:
            scores["weight"] += 1.0
        if CO.find(norm) and not bodies and not any(k in scores for k in GAME_INTENTS | {"rocket_eq", "weight"}):
            scores["concept"] = 1.6 + (1.0 if LX.has_any(norm, ("nedir", "what is", "ne demek", "explain", "acikla", "meaning")) else 0)
        if HT.find(norm) and LX.has_any(norm, ("nasil", "how", "how do", "how to", "nereden", "ne ise yarar", "nasil yapilir", "where")):
            scores["howto"] = scores.get("howto", 0) + 2.6
        if not scores:
            return None, 0
        intent = max(scores, key=scores.get)
        return intent, scores[intent]

    def dispatch(self, intent, norm, bodies, nums, raw):
        b = bodies[0] if bodies else None
        if intent == "greet":
            return self.greet()
        if intent == "thanks":
            return self.L(random.choice([("Rica ederim. Yörüngede görüşürüz.", "You're welcome. See you in orbit."),
                                         ("Her zaman. Başka sorun var mı?", "Any time. Anything else?")]))
        if intent == "facts" and not bodies:
            return self.fallback(norm)
        if intent == "identity":
            return self.identity()
        if intent == "help":
            return self.help()
        if intent == "joke":
            return self.L(random.choice(JOKES))
        if intent == "concept":
            return self.concept(CO.find(norm))
        if intent == "howto":
            return self.howto(HT.find(norm))
        if intent in GAME_INTENTS:
            return self.game_answer(intent)
        if intent == "rocket_eq":
            return self.rocket_eq(norm, nums)
        if intent == "transfer":
            return self.transfer(bodies)
        if intent == "delay":
            return self.delay(bodies)
        if intent == "compare":
            return self.compare(bodies)
        if intent in BODY_INTENTS:
            if not b:
                return self.L(("Hangi gök cismini soruyorsun? Örneğin Ay, Mars, Venüs, Jüpiter, Titan, Europa.",
                               "Which body do you mean? For example the Moon, Mars, Venus, Jupiter, Titan or Europa."))
            return getattr(self, "a_" + intent)(b, nums, norm)
        return self.fallback(norm)

    # ------------------------------------------------------------- sohbet
    def greet(self):
        n = self.game.name if self.game and self.game.s else None
        if n:
            return self.L((f"Merhaba {n}! Bana gezegenleri, roket fiziğini ya da ajansının durumunu sorabilirsin.",
                           f"Hello {n}! Ask me about planets, rocket physics or your agency's status."))
        return self.L(("Merhaba! Ben NOVA. Bana uzayla ilgili her şeyi sorabilirsin.", "Hello! I'm NOVA. Ask me anything about space."))

    def identity(self):
        return self.L(("Ben NOVA, ajansının yapay zekâ asistanıyım. Bilgilerim NASA'nın gezegen verilerine, gerçek yörünge mekaniği "
                       "formüllerine ve oyunundaki canlı duruma dayanıyor. İnternete bağlı değilim; bilmediğimi uydurmam.",
                       "I'm NOVA, your agency's AI assistant. My knowledge comes from NASA planetary data, real orbital mechanics "
                       "formulas and your live game state. I'm not connected to the Internet, and I won't make up what I don't know."))

    def help(self):
        return self.L(("Şunları sorabilirsin:\n• 'Mars'ta yerçekimi ne kadar?' · 'Titan hakkında anlat'\n• 'Dünya'dan Jüpiter'e kaç gün?' · "
                       "'Mars ile iletişim gecikmesi'\n• '80 kg Ay'da kaç kilo?' · 'Isp 320 kütle 500 ton boş 150 ton roket denklemi'\n"
                       "• 'Delta-v nedir?' · 'Para nasıl kazanırım?' · 'Ne yapmalıyım?' · 'Durum raporu'",
                       "You can ask:\n• 'What is the gravity on Mars?' · 'Tell me about Titan'\n• 'How many days from Earth to Jupiter?' · "
                       "'Signal delay to Mars'\n• 'How much does 80 kg weigh on the Moon?' · 'rocket equation isp 320 mass 500 t dry 150 t'\n"
                       "• 'What is delta-v?' · 'How do I earn money?' · 'What should I do?' · 'Status report'"))

    def fallback(self, norm):
        hint = self.L(("Bunu tam anlayamadım. ", "I didn't quite get that. "))
        c = CO.find(norm)
        if c:
            return self.concept(c)
        h = HT.find(norm)
        if h:
            return self.howto(h)
        return hint + self.L(("Bir gezegen adı, bir kavram (ör. 'Hohmann nedir') ya da oyunla ilgili bir soru dene. 'Yardım' yazarsan örnekleri gösteririm.",
                              "Try a planet name, a concept (e.g. 'what is Hohmann') or a game question. Type 'help' for examples."))

    def concept(self, key):
        if not key:
            return self.fallback("")
        _, desc, game = CO.CONCEPTS[key]
        out = self.L(desc)
        if game:
            out += "\n" + self.L(("Oyunda: ", "In the game: ")) + self.L(game)
        return out

    def howto(self, key):
        if not key:
            return self.fallback("")
        return self.L(HT.HOWTO[key][1])

    # ------------------------------------------------------------- gök cismi yanıtları
    def _n(self, x, d=1):
        return P.fmt_num(x, d, self.tr_)

    def a_facts(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        kind = {"star": ("bir yıldız", "a star"), "planet": ("bir gezegen", "a planet"), "moon": ("bir uydu", "a moon"),
                "dwarf": ("bir cüce gezegen", "a dwarf planet")}[d["kind"]]
        head = f"{self.nm(b)}: {self.L(kind)}"
        if d.get("parent"):
            head += self.L((f" ({self.nm(d['parent'])} uydusu)", f" (moon of {self.nm(d['parent'])})"))
        head += ". "
        parts = [self.L(("Yarıçap", "Radius")) + f" {self._n(d['radius'], 0)} km",
                 self.L(("çekim", "gravity")) + f" {self._n(d['g'], 2)} m/s²",
                 self.L(("sıcaklık", "temperature")) + f" ~{d['temp']} °C"]
        notes = F.NOTES.get(b, [])
        k = self.turns % len(notes) if notes else 0
        extra = (" " + self.L(notes[k])) if notes else ""
        if b in F.GAME_TARGETS:
            extra += self.L((" Oyunda bu hedefe gidebilirsin.", " You can fly there in the game."))
        return head + ", ".join(parts) + "." + extra

    def a_gravity(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        ratio = d["g"] / F.BODIES["earth"]["g"]
        return self.L((f"{LX.ek(self.nm(b), 'in')} yüzey çekimi {self._n(d['g'], 2)} m/s², yani Dünya'nın {self._n(ratio, 2)} katı. "
                       f"Dünya'da 70 kg gelen biri orada {self._n(70 * ratio, 1)} kg gibi hisseder.",
                       f"Surface gravity on {self.nm(b)} is {self._n(d['g'], 2)} m/s², {self._n(ratio, 2)} times Earth's. "
                       f"Someone who weighs 70 kg on Earth would feel like {self._n(70 * ratio, 1)} kg there."))

    def a_temp(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        t = d["temp"]
        extra = ""
        if b == "moon":
            extra = self.L((" Gündüz ~+120 °C, gece ~−130 °C'ye kadar iner.", " Days reach ~+120 °C, nights drop to ~−130 °C."))
        elif b == "mercury":
            extra = self.L((" Gündüz ~430 °C, gece ~−180 °C.", " Daytime ~430 °C, night ~−180 °C."))
        elif b == "mars":
            extra = self.L((" Ekvatorda yaz öğlesi ~20 °C'ye çıkabilir, kutuplarda ~−125 °C'ye iner.",
                            " Equatorial summer noons can reach ~20 °C; the poles drop to ~−125 °C."))
        elif d["p_bar"] is None:
            extra = self.L((" (Gaz devi: bulut tepesi sıcaklığı; derinlere indikçe ısınır.)", " (Gas giant: cloud-top temperature; it heats up with depth.)"))
        return self.L((f"{LX.ek(self.nm(b), 'in')} ortalama sıcaklığı yaklaşık {t} °C.", f"The average temperature on {self.nm(b)} is about {t} °C.")) + extra

    def a_day(self, b, nums=None, norm=""):
        h = F.BODIES[b]["day"]
        txt = P.fmt_dur(h * 3600, self.tr_)
        rel = h / 24.0
        return self.L((f"{LX.ek(self.nm(b), 'da')} bir gün (güneş doğuşundan doğuşa) {txt} sürer — Dünya gününün {self._n(rel, 2)} katı.",
                       f"A day on {self.nm(b)} (sunrise to sunrise) lasts {txt}, {self._n(rel, 2)} Earth days."))

    def a_year(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        if not d.get("year"):
            return self.L(("Güneş bir yıldız; kendi etrafında yılı yok, ama Samanyolu merkezini ~230 milyon yılda dolanır.",
                           "The Sun has no year of its own, but it circles the Milky Way's centre every ~230 million years."))
        y = d["year"]
        if d.get("parent"):
            return self.L((f"{self.nm(b)}, {self.nm(d['parent'])} etrafında bir turu {self._n(y, 2)} günde tamamlar.",
                           f"{self.nm(b)} completes one orbit of {self.nm(d['parent'])} in {self._n(y, 2)} days."))
        return self.L((f"{self.nm(b)} Güneş'i {self._n(y, 0 if y > 1000 else 1)} Dünya gününde ({self._n(y / 365.25, 2)} yıl) dolanır.",
                       f"{self.nm(b)} orbits the Sun in {self._n(y, 0 if y > 1000 else 1)} Earth days ({self._n(y / 365.25, 2)} years)."))

    def a_distance(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        if b == "earth":
            return self.L(("Dünya, Güneş'ten ortalama 149,6 milyon km (1 AU) uzaktadır.", "Earth is on average 149.6 million km (1 AU) from the Sun."))
        if d.get("parent"):
            km = d["orbit_km"]
            base = self.L((f"{self.nm(b)}, {LX.ek(self.nm(d['parent']), 'a')} ortalama {self._n(km, 0)} km uzaklıkta dolanır.",
                           f"{self.nm(b)} orbits {self.nm(d['parent'])} at an average of {self._n(km, 0)} km."))
            if d["parent"] == "earth":
                return base + self.L((" Işık bu yolu ~1,3 saniyede alır.", " Light covers that in about 1.3 seconds."))
            lo, hi = P.distance_range_m("earth", d["parent"])
            return base + self.L((f" Dünya'dan uzaklığı {P.fmt_dist(lo, True)} ile {P.fmt_dist(hi, True)} arasında değişir.",
                                  f" Its distance from Earth ranges between {P.fmt_dist(lo, False)} and {P.fmt_dist(hi, False)}."))
        if b == "sun":
            return self.a_distance("earth")
        lo, hi = P.distance_range_m("earth", b)
        return self.L((f"{self.nm(b)} Güneş'ten ortalama {self._n(d['a_au'], 3)} AU ({P.fmt_dist(d['a_au'] * P.AU, True)}) uzakta. "
                       f"Dünya'ya uzaklığı yaklaşık {P.fmt_dist(lo, True)} ile {P.fmt_dist(hi, True)} arasında değişir.",
                       f"{self.nm(b)} is {self._n(d['a_au'], 3)} AU ({P.fmt_dist(d['a_au'] * P.AU, False)}) from the Sun on average. "
                       f"Its distance from Earth ranges from about {P.fmt_dist(lo, False)} to {P.fmt_dist(hi, False)}."))

    def a_moons(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        if d["kind"] == "moon":
            return self.L((f"{self.nm(b)} kendisi bir uydu; {self.nm(d['parent'])} etrafında dolanır.",
                           f"{self.nm(b)} is itself a moon, orbiting {self.nm(d['parent'])}."))
        n = d["moons"]
        kids = [k for k, v in F.BODIES.items() if v.get("parent") == b]
        named = ", ".join(self.nm(k) for k in kids)
        out = self.L((f"{self.nm(b)} için bilinen uydu sayısı: {n}.", f"Known moons of {self.nm(b)}: {n}."))
        if named:
            out += self.L((f" Bildiklerim: {named}.", f" I know about: {named}."))
        if n > 10:
            out += self.L((" (Sayı yeni keşiflerle artıyor; 2024 itibarıyla.)", " (The count grows with new discoveries; as of 2024.)"))
        return out

    def a_atmo(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        p = d["p_bar"]
        if p is None:
            ps = self.L(("katı yüzey olmadığından yüzey basıncı tanımsız", "no solid surface, so surface pressure is undefined"))
        elif p == 0:
            ps = self.L(("yüzey basıncı yok denecek kadar düşük", "surface pressure is practically zero"))
        else:
            ps = self.L((f"yüzey basıncı {self._n(p, 3 if p < 0.1 else 1)} bar (Dünya: 1 bar)", f"surface pressure {self._n(p, 3 if p < 0.1 else 1)} bar (Earth: 1 bar)"))
        breathe = "" if b == "earth" else self.L((" İnsan orada giysisiz nefes alamaz.", " A human cannot breathe there without a suit."))
        return f"{self.nm(b)}: {self.L(d['atm'])}; {ps}.{breathe}"

    def a_size(self, b, nums=None, norm=""):
        d = F.BODIES[b]
        r = d["radius"]
        rel = r / F.BODIES["earth"]["radius"]
        vol = rel ** 3
        if rel >= 1:
            cmp_ = self.L((f"Dünya'nın {self._n(rel, 2)} katı genişliğinde; içine yaklaşık {self._n(vol, 0)} Dünya sığar.",
                           f"{self._n(rel, 2)} times as wide as Earth; about {self._n(vol, 0)} Earths would fit inside."))
        else:
            cmp_ = self.L((f"çapı Dünya'nın %{self._n(rel * 100, 1)}'i kadar.", f"its diameter is {self._n(rel * 100, 1)}% of Earth's."))
        return self.L((f"{LX.ek(self.nm(b), 'in')} yarıçapı {self._n(r, 0)} km (çap {self._n(2 * r, 0)} km); {cmp_}",
                       f"{self.nm(b)} has a radius of {self._n(r, 0)} km (diameter {self._n(2 * r, 0)} km); {cmp_}"))

    def a_mass(self, b, nums=None, norm=""):
        m = F.BODIES[b]["mass"]
        rel = m / F.BODIES["earth"]["mass"]
        return self.L((f"{LX.ek(self.nm(b), 'in')} kütlesi {self._sci(m * 1e24)} kg; Dünya'nın {self._n(rel, 4 if rel < 0.01 else 2)} katı.",
                       f"{self.nm(b)} has a mass of {self._sci(m * 1e24)} kg, {self._n(rel, 4 if rel < 0.01 else 2)} times Earth's."))

    def _sci(self, x):
        import math
        e = int(math.floor(math.log10(abs(x))))
        m = x / 10 ** e
        return f"{self._n(m, 2)}×10^{e}"

    def a_escape(self, b, nums=None, norm=""):
        v = P.escape_velocity(b)
        alt = P.low_orbit_alt(b)
        vo = P.orbital_velocity(b, alt)
        return self.L((f"{LX.ek(self.nm(b), 'in')} yüzeyinden kaçış hızı {P.fmt_speed(v, True)}. {self._n(alt, 0)} km yükseklikte dairesel yörünge hızı "
                       f"{P.fmt_speed(vo, True)}.",
                       f"Escape velocity from {self.nm(b)} is {P.fmt_speed(v, False)}. Circular orbit speed at {self._n(alt, 0)} km is "
                       f"{P.fmt_speed(vo, False)}."))

    def a_orbit_calc(self, b, nums=None, norm=""):
        alt = next((v for v, u, _ in (nums or []) if u in ("km", "")), None) or P.low_orbit_alt(b)
        v = P.orbital_velocity(b, alt)
        t = P.orbital_period(b, alt)
        return self.L((f"{self.nm(b)} etrafında {self._n(alt, 0)} km yükseklikte dairesel yörünge: hız {P.fmt_speed(v, True)}, "
                       f"bir tur {P.fmt_dur(t, True)}. (v = √(μ/r))",
                       f"Circular orbit {self._n(alt, 0)} km above {self.nm(b)}: speed {P.fmt_speed(v, False)}, one lap takes "
                       f"{P.fmt_dur(t, False)}. (v = √(μ/r))"))

    def a_missions(self, b, nums=None, norm=""):
        ms = F.MISSIONS.get(b)
        if not ms:
            par = F.BODIES[b].get("parent")
            if par and F.MISSIONS.get(par):
                ms = F.MISSIONS[par]
                head = self.L((f"{self.nm(b)} için özel bir görev kaydım yok; {self.nm(par)} sistemindeki görevler:",
                               f"I have no dedicated missions for {self.nm(b)}; missions to the {self.nm(par)} system:"))
            else:
                return self.L((f"{self.nm(b)} için kayıtlı görev bilgim yok.", f"I have no mission records for {self.nm(b)}."))
        else:
            head = self.L((f"{self.nm(b)} için önemli görevler:", f"Key missions to {self.nm(b)}:"))
        lines = [f"• {y} {n}: {self.L(d)}" for y, n, d in sorted(ms)]
        return head + "\n" + "\n".join(lines)

    def a_hazards(self, b, nums=None, norm=""):
        hz = F.HAZARDS.get(b)
        if not hz:
            d = F.BODIES[b]
            bits = []
            if d["p_bar"] in (0, 0.0) or (d["p_bar"] is not None and d["p_bar"] < 0.01):
                bits.append(self.L(("atmosfer yok: basınçlı yaşam alanı ve radyasyon kalkanı gerekir", "no atmosphere: pressurised habitats and radiation shielding needed")))
            if d["temp"] < -100:
                bits.append(self.L((f"aşırı soğuk (~{d['temp']} °C)", f"extreme cold (~{d['temp']} °C)")))
            if d["temp"] > 100:
                bits.append(self.L((f"aşırı sıcak (~{d['temp']} °C)", f"extreme heat (~{d['temp']} °C)")))
            if d["p_bar"] is None:
                bits.append(self.L(("katı yüzey yok", "no solid surface")))
            flux = P.solar_flux(b) if b != "sun" else None
            if flux and flux < 100:
                bits.append(self.L((f"zayıf güneş ışığı (~{self._n(flux, 0)} W/m²)", f"weak sunlight (~{self._n(flux, 0)} W/m²)")))
            if not bits:
                return self.L((f"{self.nm(b)} için özel risk kaydım yok.", f"I have no specific hazard notes for {self.nm(b)}."))
            return self.L((f"{self.nm(b)} için başlıca zorluklar: ", f"Main challenges on {self.nm(b)}: ")) + "; ".join(bits) + "."
        out = self.L((f"{LX.ek(self.nm(b), 'da')} gerçek dünyadaki başlıca tehlikeler:", f"Main real-world hazards on {self.nm(b)}:"))
        return out + "\n" + "\n".join("• " + self.L(h) for h in hz)

    def a_weight(self, b, nums=None, norm=""):
        kg = next((v for v, u, _ in (nums or []) if u in ("kg", "", "t", "ton")), 70.0)
        w = P.weight_on(b, kg)
        return self.L((f"Dünya'da {self._n(kg, 1)} kg gelen biri {LX.ek(self.nm(b), 'da')} {self._n(w, 1)} kg gibi tartılır "
                       f"(kütle aynı kalır, yalnız ağırlık değişir).",
                       f"Someone who weighs {self._n(kg, 1)} kg on Earth would register {self._n(w, 1)} kg on {self.nm(b)} "
                       f"(mass stays the same; only weight changes)."))

    def a_jump(self, b, nums=None, norm=""):
        h = P.jump_height(b, 0.5)
        return self.L((f"Dünya'da 50 cm zıplayabilen biri {LX.ek(self.nm(b), 'da')} aynı güçle yaklaşık {self._n(h, 2)} m zıplar.",
                       f"Someone who jumps 50 cm on Earth would reach about {self._n(h, 2)} m on {self.nm(b)} with the same push."))

    def a_sunlight(self, b, nums=None, norm=""):
        f = P.solar_flux(b) if b != "sun" else None
        if not f:
            return self.L(("Güneş'in yüzeyinde ışınım ~63 MW/m²'dir.", "At the Sun's surface the flux is ~63 MW/m²."))
        return self.L((f"{LX.ek(self.nm(b), 'da')} güneş ışınımı yaklaşık {self._n(f, 0)} W/m² (Dünya: 1.361 W/m², oran %{self._n(f / 13.61, 1)}).",
                       f"Sunlight at {self.nm(b)} is about {self._n(f, 0)} W/m² (Earth: 1,361 W/m², {self._n(f / 13.61, 1)}%)."))

    # ------------------------------------------------------------- iki cisim
    def _pair(self, bodies):
        if len(bodies) >= 2:
            return bodies[0], bodies[1]
        if len(bodies) == 1:
            return ("earth", bodies[0]) if bodies[0] != "earth" else (self.last_body or "moon", "earth")
        return None, None

    def transfer(self, bodies):
        a, b = self._pair(bodies)
        if not a:
            return self.L(("Nereden nereye? Örneğin: 'Dünya'dan Mars'a kaç gün?'", "From where to where? E.g. 'How many days from Earth to Mars?'"))
        if F.BODIES[a].get("parent") == b or F.BODIES[b].get("parent") == a:
            moon = a if F.BODIES[a].get("parent") else b
            par = F.BODIES[moon]["parent"]
            r1 = P.radius_m(par) + P.low_orbit_alt(par) * 1000
            r2 = F.BODIES[moon]["orbit_km"] * 1000
            dv1, dv2, t = P.hohmann(r1, r2, P.mu(par))
            return self.L((f"{self.nm(par)} alçak yörüngesinden {LX.ek(self.nm(moon), 'a')} Hohmann transferi ~{P.fmt_dur(t, True)} sürer; "
                           f"çıkış ateşlemesi {P.fmt_speed(dv1, True)}. (Apollo bu yolu ~3 günde aldı.)" if moon == "moon" else
                           f"{self.nm(par)} alçak yörüngesinden {LX.ek(self.nm(moon), 'a')} Hohmann transferi ~{P.fmt_dur(t, True)} sürer; "
                           f"çıkış ateşlemesi {P.fmt_speed(dv1, True)}.",
                           f"A Hohmann transfer from low {self.nm(par)} orbit to {self.nm(moon)} takes ~{P.fmt_dur(t, False)}; "
                           f"departure burn {P.fmt_speed(dv1, False)}." + (" (Apollo made the trip in about 3 days.)" if moon == "moon" else "")))
        tr_ = P.transfer(a, b)
        if not tr_:
            return self.L(("Bu iki cisim aynı gezegen sisteminde; güneş merkezli transfer gerekmez.", "Both bodies are in the same planetary system; no heliocentric transfer needed."))
        syn = P.synodic_days(a, b)
        win = ""
        if syn:
            win = self.L((f" Uygun fırlatma pencereleri ~{self._n(syn, 0)} günde bir ({self._n(syn / 30.44, 1)} ay) açılır.",
                          f" Launch windows open about every {self._n(syn, 0)} days ({self._n(syn / 30.44, 1)} months)."))
        return self.L((f"{self.nm(a)} → {self.nm(b)} Hohmann transferi: ~{P.fmt_dur(tr_['days'] * P.DAY, True)}. Güneş merkezli Δv: "
                       f"çıkışta {P.fmt_speed(tr_['dv_depart'], True)}, varışta {P.fmt_speed(tr_['dv_arrive'], True)}.{win} "
                       f"(Dairesel, eş düzlemli yörünge varsayımı; gerçek görevler biraz farklıdır.)",
                       f"{self.nm(a)} → {self.nm(b)} Hohmann transfer: ~{P.fmt_dur(tr_['days'] * P.DAY, False)}. Heliocentric Δv: "
                       f"{P.fmt_speed(tr_['dv_depart'], False)} at departure, {P.fmt_speed(tr_['dv_arrive'], False)} at arrival.{win} "
                       f"(Assumes circular, coplanar orbits; real missions differ somewhat.)"))

    def delay(self, bodies):
        a, b = self._pair(bodies)
        if not a:
            a, b = "earth", "mars"
        lo, hi = P.light_delay(a, b)
        if abs(lo - hi) < 1e-6:
            return self.L((f"{self.nm(a)} ile {self.nm(b)} arasında radyo sinyali tek yönde {P.fmt_dur(lo, True)} gecikir.",
                           f"A radio signal between {self.nm(a)} and {self.nm(b)} takes {P.fmt_dur(lo, False)} one way."))
        return self.L((f"{self.nm(a)} ile {self.nm(b)} arasında tek yönlü sinyal gecikmesi {P.fmt_dur(lo, True)} (en yakın) ile "
                       f"{P.fmt_dur(hi, True)} (en uzak) arasında değişir. Soru-cevap için bunu ikiyle çarp.",
                       f"One-way signal delay between {self.nm(a)} and {self.nm(b)} ranges from {P.fmt_dur(lo, False)} (closest) to "
                       f"{P.fmt_dur(hi, False)} (farthest). Double it for a question and answer."))

    def compare(self, bodies):
        if len(bodies) < 2:
            if len(bodies) == 1:
                bodies = [bodies[0], "earth" if bodies[0] != "earth" else "mars"]
            else:
                return self.L(("Hangi iki cismi karşılaştırayım?", "Which two bodies should I compare?"))
        a, b = bodies[0], bodies[1]
        A, B = F.BODIES[a], F.BODIES[b]
        rows = [(("Yarıçap", "Radius"), A["radius"], B["radius"], "km", 0),
                (("Çekim", "Gravity"), A["g"], B["g"], "m/s²", 2),
                (("Sıcaklık", "Temperature"), A["temp"], B["temp"], "°C", 0),
                (("Gün", "Day"), A["day"], B["day"], self.L(("saat", "h")), 1),
                (("Uydu", "Moons"), A["moons"], B["moons"], "", 0)]
        lines = [f"{self.nm(a)} vs {self.nm(b)}:"]
        for lab, x, y, u, d in rows:
            lines.append(f"• {self.L(lab)}: {self._n(x, d)} {u} · {self._n(y, d)} {u}".rstrip())
        big = a if A["radius"] > B["radius"] else b
        lines.append(self.L((f"{self.nm(big)} daha büyük; yarıçap oranı {self._n(max(A['radius'], B['radius']) / min(A['radius'], B['radius']), 2)}.",
                             f"{self.nm(big)} is larger; radius ratio {self._n(max(A['radius'], B['radius']) / min(A['radius'], B['radius']), 2)}.")))
        return "\n".join(lines)

    # ------------------------------------------------------------- hesap
    def rocket_eq(self, norm, nums):
        isp = None
        masses = []
        for v, u, prev in nums:
            if prev == "isp" or (isp is None and u in ("s", "sn", "saniye", "second", "seconds")):
                isp = v
                continue
            k = 1000.0 if u in ("t", "ton") else 1.0
            masses.append(v * k)
        if isp is None:
            free = [v for v, u, _ in nums if u == ""]
            if free and 100 <= free[0] <= 10000 and len(nums) >= 3:
                isp = free[0]
                masses = masses[1:]
        if isp is None or len(masses) < 2:
            return self.L(("Hesap için Isp ve iki kütle gerekli: dolu kütle ve boş kütle. Örnek: 'roket denklemi isp 320 kütle 500 ton boş 150 ton'.",
                           "I need Isp and two masses: full and empty. Example: 'rocket equation isp 320 mass 500 t dry 150 t'."))
        m0, mf = max(masses[:2]), min(masses[:2])
        dv = P.tsiolkovsky(isp, m0, mf)
        reach = []
        for k, need in (("leo", 9400), ("tli", 9400 + 3150), ("moon", 9400 + 5900), ("mars", 9400 + 3600 + 4000)):
            if dv >= need:
                reach.append(k)
        names = {"leo": ("Dünya alçak yörüngesi", "low Earth orbit"), "tli": ("Ay'a transfer", "trans-lunar injection"),
                 "moon": ("Ay yüzeyi", "the lunar surface"), "mars": ("Mars yüzeyi (aerofrenle)", "the Martian surface (with aerobraking)")}
        tail = (self.L(("Tek kademeyle ulaşabileceğin en uzak nokta: ", "Farthest you could reach in one stage from Earth: ")) + self.L(names[reach[-1]]) + "."
                if reach else self.L(("Bu, Dünya'dan yörüngeye çıkmak için (~9,4 km/s) yetmez; kademe ekle.",
                                      "That isn't enough to reach Earth orbit (~9.4 km/s); add a stage.")))
        return self.L((f"Δv = {self._n(isp, 0)} s × 9,81 × ln({self._n(m0 / 1000, 1)} t / {self._n(mf / 1000, 1)} t) = {P.fmt_speed(dv, True)}. ",
                       f"Δv = {self._n(isp, 0)} s × 9.81 × ln({self._n(m0 / 1000, 1)} t / {self._n(mf / 1000, 1)} t) = {P.fmt_speed(dv, False)}. ")) + tail

    # ------------------------------------------------------------- oyun durumu
    def game_answer(self, intent):
        g = self.game
        if not g or not g.s:
            return self.L(("Önce bir ajans kurmalı ya da kayıtlı kampanyaya devam etmelisin; o zaman durumunu okuyabilirim.",
                           "Create an agency or continue a saved campaign first; then I can read your status."))
        br = self.brain
        T = i18n.tr
        if intent == "advice" and br:
            return T(br.advisor()[1])
        if intent == "suggest" and br:
            return T(br.suggest()[0])
        if intent == "forecast" and br:
            return T(br.forecast())
        if intent == "best_time" and br:
            return T(br.answer("best"))
        if intent == "colonies" and br:
            return T(br.answer("colonies"))
        if intent == "status" and br:
            return T(br.answer("status"))
        if intent == "money_now":
            return self.L((f"Kasanda {P.fmt_num(g.money, 0, True)} Para ve {P.fmt_num(g.rp, 0, True)} araştırma puanı var.",
                           f"You have {P.fmt_num(g.money, 0, False)} money and {P.fmt_num(g.rp, 0, False)} research points."))
        if intent == "score_now":
            from .. import online
            sc = online.score_of(g)
            rows = online.sorted_rows(online.local_load(), "score")
            me = online.campaign_id(g)
            rank = next((i + 1 for i, r in enumerate(rows) if r.get("id") == me), None)
            out = self.L((f"Skorun: {P.fmt_num(sc, 0, True)}.", f"Your score: {P.fmt_num(sc, 0, False)}."))
            if rank:
                out += self.L((f" Bu cihazdaki sıralamada {rank}. / {len(rows)}.", f" You are #{rank} of {len(rows)} on this device."))
            return out + self.L((" Çevrimiçi sıra için SIRALAMA ekranını aç.", " Open the LEADERBOARD screen for the online rank."))
        if intent == "game_time":
            return self.L((f"Oyun saati: {g.day}. gün, {g.time_label()}.", f"Game time: day {g.day}, {g.time_label()}."))
        return self.fallback("")

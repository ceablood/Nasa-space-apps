# -*- coding: utf-8 -*-
"""
AETHER-X // ORGANİZMALAR, EVRİM VE EKOSİSTEM
  MicrobialLifeEngine · FloraEvolutionEngine · FaunaEvolutionEngine · EvolutionEngine · EcosystemSimulationEngine

Model (oyun ölçeğinde, açıklanabilir):
  * Genom: sıcaklık optimumu/toleransı, basınç, kimyasal ve ışınım toleransı, metabolizma, beden boyu,
    hareket, algı, savunma, üreme hızı, beslenme, yaşam alanı, sosyallik.
  * Uygunluk (0..1): çevre koşulları genoma göre (Gauss sıcaklık eğrisi, eşik toleranslar, enerji erişimi).
  * Ekosistem: genelleştirilmiş Lotka–Volterra. Üreticiler taşıma kapasitesine kadar lojistik büyür,
    tüketiciler av biyokütlesinden verimle beslenir, ölen biyokütle döküntü havuzuna gider, ayrıştırıcılar
    döküntüyü besine çevirir. Karbon, azot, oksijen ve su havuzları bu akışlarla değişir.
  * Evrim: doğal seçilim (uygunluk eğimine doğru kayma), mutasyon, genetik sürüklenme (küçük popülasyonda
    büyük), darboğaz, coğrafi izolasyon (her biyom ayrı alt popülasyon) ve ayrışma eşiğini geçince türleşme;
    biyokütle eşik altına inince yok oluş.
Birimler: biyokütle "göreli birim"dir (biyom kapasitesi 100). Yıllar oyun yılıdır.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace

METABOLISM = ("fotosentez", "kemosentez", "anaerobik", "heterotrof")
DIET = ("üretici", "otçul", "etçil", "hepçil", "ayrıştırıcı")
HABITAT = ("su", "kara", "hava", "yeraltı", "buzaltı")
KINGDOM = ("mikrop", "bitki", "mantar", "hayvan")

# biyom -> kullanılabilir yaşam alanları ve taşıma kapasitesi çarpanı
BIOME_HABITATS = {
    "tropikal orman": ("kara", "hava", "su", "yeraltı"), "çöl": ("kara", "yeraltı", "hava"),
    "okyanus": ("su",), "resif": ("su",), "buzul": ("kara", "buzaltı", "su"), "buz altı okyanusu": ("buzaltı", "su"),
    "volkanik bölge": ("kara", "yeraltı"), "sıcak su kaynakları": ("su", "yeraltı"), "tuz ovası": ("kara",),
    "çorak ova": ("kara",), "yer altı mağaraları": ("yeraltı",), "toz ovası": ("kara", "yeraltı"),
    "kutup buzulu": ("buzaltı", "yeraltı"), "kanyon": ("kara", "yeraltı"), "regolit ovası": ("yeraltı",),
    "kalıcı gölgeli krater": ("yeraltı", "buzaltı"), "volkanik ova": ("kara",), "tessera yayla": ("kara",),
    "bulut kuşağı": ("hava",),
}
# biyomun gezegen ortalamasına göre sıcaklık farkı (°C; Dünya biyom iklimlerinin kaba ortalamaları)
BIOME_TEMP = {"tropikal orman": 12, "çöl": 15, "buzul": -30, "kutup buzulu": -40, "volkanik bölge": 45,
              "sıcak su kaynakları": 60, "resif": 10, "okyanus": 2, "tuz ovası": 10, "kalıcı gölgeli krater": -150}
BIOME_CAPACITY = {"tropikal orman": 1.6, "okyanus": 1.3, "resif": 1.5, "çöl": 0.35, "buzul": 0.3,
                  "buz altı okyanusu": 0.5, "volkanik bölge": 0.5, "sıcak su kaynakları": 0.8, "tuz ovası": 0.2}


@dataclass
class Genome:
    temp_opt: float = 20.0
    temp_tol: float = 25.0         # Gauss genişliği (°C)
    press_min: float = 0.3         # bar
    press_max: float = 5.0
    chem_tol: float = 0.3          # asit/tuz/kükürt dayanımı
    rad_tol: float = 0.2
    metabolism: str = "heterotrof"
    size: float = -5.0             # log10 metre (-6 bakteri, 0 = 1 m)
    speed: float = 0.0
    sense: float = 0.0
    defense: float = 0.2
    repro: float = 0.5
    diet: str = "üretici"
    habitat: str = "su"
    social: float = 0.0

    NUM = ("temp_opt", "temp_tol", "chem_tol", "rad_tol", "size", "speed", "sense", "defense", "repro", "social")
    SCALE = {"temp_opt": 60.0, "temp_tol": 40.0, "chem_tol": 1.0, "rad_tol": 1.0, "size": 6.0, "speed": 1.0,
             "sense": 1.0, "defense": 1.0, "repro": 1.0, "social": 1.0}

    def distance(self, o):
        """Normalize genetik uzaklık (türleşme ölçütü)."""
        d = sum(((getattr(self, k) - getattr(o, k)) / self.SCALE[k]) ** 2 for k in self.NUM)
        d += 0.5 * (self.metabolism != o.metabolism) + 0.5 * (self.diet != o.diet) + 0.3 * (self.habitat != o.habitat)
        return math.sqrt(d)

    def mutated(self, rng, rate=0.05):
        g = replace(self)
        for k in self.NUM:
            v = getattr(g, k) + rng.gauss(0, rate) * self.SCALE[k] * 0.25
            lo, hi = {"temp_opt": (-60, 130), "temp_tol": (3, 60), "size": (-6.5, 1.5)}.get(k, (0.0, 1.0))
            setattr(g, k, min(hi, max(lo, v)))
        return g


@dataclass
class Species:
    sid: int
    name: str
    kingdom: str
    genome: Genome
    biome: str
    biomass: float
    born_year: float = 0.0
    parent: int | None = None
    real: bool = False             # Dünya'da gerçekten var olan grup (temsilî özelliklerle)
    kurgusal: bool = False
    note: str = ""
    extinct_year: float | None = None
    discovered: bool = False
    lineage_genome: Genome | None = None      # türleşme ölçütü için ata genomu
    variance: float = 1.0                       # kalıtsal çeşitlilik (darboğazda düşer)

    @property
    def alive(self):
        return self.extinct_year is None

    @property
    def trophic(self):
        return {"üretici": 1, "ayrıştırıcı": 1, "otçul": 2, "hepçil": 2.5, "etçil": 3}[self.genome.diet]


def acidity(env, biome):
    """0..1 kimyasal stres: kükürt dioksit, tuz ve volkanik ortam."""
    return min(1.0, env.atmosphere.get("SO2", 0) * 50 + (0.6 if biome in ("tuz ovası", "volkanik bölge") else 0))


def local_temp(env, biome, habitat):
    """Yaşam alanının yerel sıcaklığı (°C): biyom iklimi + yer altı/buz altı/su tamponlaması."""
    T = env.temp_c + BIOME_TEMP.get(biome, 0) * (1.0 if env.pressure_bar and env.pressure_bar > 0.05 else 0.4)
    if habitat in ("yeraltı", "buzaltı"):
        T = max(T, -5.0 + env.internal_heat * 30) if T < 0 else min(T, 60 + env.internal_heat * 30)
    elif habitat == "su" and (env.oceans or env.surface_water > 0.05):
        T = max(-1.8, min(T, 35.0 if biome != "sıcak su kaynakları" else 80.0))
    if biome == "sıcak su kaynakları":
        T = 75.0
    return T


def fitness(g, env, biome):
    """0..1: bu genomun bu gezegen/biyomda yaşama ve çoğalma uygunluğu."""
    habs = BIOME_HABITATS.get(biome, ("kara",))
    if g.habitat not in habs:
        return 0.0
    T = local_temp(env, biome, g.habitat)
    ft = math.exp(-((T - g.temp_opt) / max(1.0, g.temp_tol)) ** 2)
    p = env.pressure_bar if env.pressure_bar is not None else 1.0
    if g.habitat in ("yeraltı", "buzaltı", "su"):
        p = max(p, 1.0)          # su/kaya altında basınç sıvı suyu korur
    fp = 1.0 if g.press_min <= p <= g.press_max else 0.15
    acid = acidity(env, biome)
    fc = 1.0 if g.chem_tol >= acid else max(0.0, 1.0 - (acid - g.chem_tol) * 2)
    rad = env.radiation * (0.15 if g.habitat in ("yeraltı", "buzaltı", "su") else 1.0)
    fr = 1.0 if g.rad_tol >= rad else max(0.0, 1.0 - (rad - g.rad_tol) * 2.5)
    fe = 1.0
    if g.diet == "üretici":
        light = min(1.0, env.irradiance / 400.0) * (0.05 if g.habitat in ("yeraltı", "buzaltı") else 1.0)
        chem = min(1.0, env.geology + env.internal_heat * 0.5) * (1.4 if biome in ("sıcak su kaynakları", "volkanik bölge") else 1.0)
        fe = {"fotosentez": light, "kemosentez": min(1.0, chem), "anaerobik": 0.4 + 0.3 * chem}.get(g.metabolism, 0.1)
        if g.metabolism == "fotosentez" and env.atmosphere.get("CO2", 0) < 1e-4 and not env.oceans:
            fe *= 0.3
    if g.metabolism == "heterotrof" and g.habitat != "su" and env.atmosphere.get("O2", 0) < 0.05 and g.size > -3:
        fe *= 0.25               # büyük, hareketli hayvanlar oksijenli solunuma dayanır
    return max(0.0, min(1.0, ft * fp * fc * fr * fe))


class Ecosystem:
    """Bir gezegendeki bütün biyomların besin ağı ve madde döngüleri."""

    def __init__(self, env, species, rng=None):
        self.env = env
        self.species = species                 # liste (tüm biyomlar)
        self.rng = rng or random.Random(7)
        self.detritus = {}                     # biyom -> döküntü biyokütlesi
        self.pools = {"karbon": 1.0, "azot": 1.0, "oksijen": env.atmosphere.get("O2", 0.0), "su": env.surface_water}
        self.flux = {"fotosentez": 0.0, "solunum": 0.0, "ayrıştırma": 0.0}

    def biomes(self):
        out = {}
        for s in self.species:
            if s.alive:
                out.setdefault(s.biome, []).append(s)
        return out

    def capacity(self, biome):
        return 100.0 * BIOME_CAPACITY.get(biome, 0.6) * (0.4 + 0.6 * min(1.0, self.pools["azot"]))

    def step(self, dt):
        """dt: yıl. Kararlılık için alt adımlarla tümleştirilir."""
        n = max(1, min(40, int(dt / 0.5) + 1))
        h = dt / n
        for _ in range(n):
            self._substep(h)

    def _substep(self, h):
        env = self.env
        photo = resp = decomp = 0.0
        for biome, sp in self.biomes().items():
            K = self.capacity(biome)
            prod = [s for s in sp if s.genome.diet == "üretici"]
            P = sum(s.biomass for s in prod)
            det = self.detritus.get(biome, 0.0)
            new_det = 0.0
            fit = {s.sid: fitness(s.genome, env, biome) for s in sp}
            # üreticiler: ortak kapasite için yarışan lojistik büyüme
            for s in prod:
                # farklı türler arası rekabet katsayısı 0,5 (<1): niş ayrımıyla birlikte yaşayabilirler
                crowd = s.biomass + 0.5 * (P - s.biomass)
                r = 0.6 * (0.3 + s.genome.repro) * fit[s.sid]
                g = r * s.biomass * (1 - crowd / max(1e-6, K))
                die = 0.05 * s.biomass + (0.4 * s.biomass if fit[s.sid] < 0.05 else 0)
                s.biomass += (g - die) * h
                new_det += die * h
                if s.genome.metabolism == "fotosentez":
                    photo += max(0.0, g) * h
            # tüketiciler: av seçimi beslenmeye göre; saldırı = algı+hız, av savunması azaltır
            cons = [s for s in sp if s.genome.diet in ("otçul", "etçil", "hepçil")]
            for c in cons:
                prey = [p for p in sp if p is not c and p.biomass > 0 and self._eats(c, p)]
                # Holling tip II: kişi başı alım doyar (avcı avı sınırsız tüketemez)
                # metabolik ölçekleme (Kleiber): küçük canlıların kütle başına alım ve ölüm hızı yüksektir ~ M^-1/4
                ks = 10 ** (-0.25 * c.genome.size)
                hunt = {"etçil": 5.0, "hepçil": 1.5}.get(c.genome.diet, 1.0)     # avcılar avını etkin arar
                a = 0.1 * ks * hunt * (0.5 + c.genome.sense + c.genome.speed) / 1.5
                cap = 1.0 * ks          # yılda en çok ~kendi kütlesi x ks kadar besin (tüketiciler üretimin küçük bir kısmını yer)
                # sığınak: avın küçük bir kısmı her zaman ulaşılmaz (ör. derinlik, gizlenme) -> av tükenmez
                # üreticilerin ~%40'ı (kök, tohum, derindeki hücreler) otlanamaz; hayvan avının %10'u + 0,5 birimi sığınakta
                vis = {p.sid: max(0.0, (0.6 * p.biomass - 2.0) if p.genome.diet == "üretici" else (0.9 * p.biomass - 0.5))
                       * (1.2 - p.genome.defense) for p in prey}
                avail = sum(vis.values())
                # Beddington–DeAngelis: doyma (kütleye göre üst sınır) + avcılar arası girişim (kalabalık avcı az yer)
                per = a * avail / (1 + a * avail / cap + 0.15 * c.biomass)
                want = per * c.biomass * h
                intake = 0.0
                for p in prey:
                    share = vis[p.sid] / max(1e-9, avail)
                    eaten = min(p.biomass * 0.3, want * share)
                    p.biomass -= eaten
                    intake += eaten
                gain = 0.12 * intake * (0.3 + 0.7 * fit[c.sid]) / max(1e-6, h)
                # yoğunluğa bağlı ölüm (tür içi rekabet, hastalık): kalabalık popülasyon kendini sınırlar
                mort = (0.04 * ks * (1 + 0.15 * c.biomass) + (0.5 if fit[c.sid] < 0.05 else 0)) * c.biomass
                c.biomass += (gain - mort) * h
                new_det += mort * h
                resp += intake * 0.88
            # ayrıştırıcılar döküntüyü besine (azot) çevirir
            decs = [s for s in sp if s.genome.diet == "ayrıştırıcı"]
            D = sum(s.biomass for s in decs)
            used = min(det, 0.02 * D * det * h) if D > 0 else det * 0.01 * h
            for s in decs:
                s.biomass += (0.3 * used * (s.biomass / max(1e-6, D)) - 0.04 * s.biomass * h) * fit[s.sid]
            decomp += used
            self.detritus[biome] = max(0.0, det + new_det - used)
            for s in sp:
                if s.biomass < 1e-3 and s.alive:
                    s.biomass = 0.0
        self.flux = {"fotosentez": photo, "solunum": resp, "ayrıştırma": decomp}
        # döngüler (göreli): fotosentez CO2 bağlar, O2 açar; solunum ve ayrıştırma tersine; ayrıştırma azotu geri döndürür
        self.pools["karbon"] = max(0.05, self.pools["karbon"] + (resp + decomp - photo) * 1e-4)
        self.pools["oksijen"] = max(0.0, min(0.35, self.pools["oksijen"] + (photo - resp - decomp) * 2e-6))
        self.pools["azot"] = max(0.05, min(1.5, self.pools["azot"] + decomp * 2e-4 - 1e-4 * sum(self.detritus.values()) * 1e-2))
        self.pools["su"] = self.env.surface_water

    @staticmethod
    def _eats(c, p):
        d = c.genome.diet
        if d == "otçul":
            return p.genome.diet == "üretici" and p.kingdom in ("bitki", "mikrop")
        if d == "etçil":
            return p.genome.diet in ("otçul", "hepçil") and p.genome.size <= c.genome.size + 0.5
        if d == "hepçil":       # meyve/tohum/yaprak (boydan bağımsız) + küçük otçullar
            return p.genome.diet == "üretici" or (p.genome.diet == "otçul" and p.genome.size <= c.genome.size + 0.3)
        return False

    def food_web(self):
        """(avcı, av) çiftleri: arayüzde besin ağı çizimi için."""
        out = []
        for biome, sp in self.biomes().items():
            for c in sp:
                for p in sp:
                    if p is not c and self._eats(c, p):
                        out.append((c.sid, p.sid))
        return out


class Evolution:
    """Nesiller boyu değişim. step(dt) evrimsel zaman ölçeğinde (binlerce–milyonlarca yıl) çağrılır."""

    SPECIATION_D = 0.55
    BOTTLENECK = 2.0

    def __init__(self, env, species, rng, namer):
        self.env, self.species, self.rng, self.namer = env, species, rng, namer
        self.next_id = max([s.sid for s in species] + [0]) + 1
        self.log = []                          # (olay, tür, veri)

    def step(self, dt_years, year):
        gens = dt_years / 1e4                  # oyun ölçeği: 10.000 yılda bir "nesil adımı"
        if gens <= 0:
            return
        for s in list(self.species):
            if not s.alive:
                continue
            if s.biomass <= 1e-3:
                s.extinct_year = year
                self.log.append(("yok_olus", s, {}))
                continue
            if s.real:
                continue                       # gerçek Dünya grupları değiştirilmez (temsilî, kurgusal evrim yok)
            # darboğaz: küçük popülasyonda çeşitlilik azalır, sürüklenme artar
            if s.biomass < self.BOTTLENECK and s.variance > 0.3:
                s.variance *= 0.6
                self.log.append(("darbogaz", s, {"biyokutle": s.biomass}))
            drift = 0.05 / math.sqrt(max(0.05, s.biomass))
            rate = min(0.5, 0.02 * gens * s.variance + drift * math.sqrt(gens) * 0.2)
            # doğal seçilim: birkaç mutant dener, uygunluğu en yüksek olana doğru kayar
            base = fitness(s.genome, self.env, s.biome)
            best, bf = s.genome, base
            neutral = []
            for _ in range(4):
                m = s.genome.mutated(self.rng, rate)
                f = fitness(m, self.env, s.biome) + self.rng.gauss(0, drift * 0.05)
                if f > bf:
                    best, bf = m, f
                elif f >= base * 0.97:
                    neutral.append(m)
            # nötr evrim: uygunluğu neredeyse aynı varyantlar sürüklenmeyle yayılabilir (optimumdaki türler de değişir)
            if best is s.genome and neutral and self.rng.random() < min(0.9, 0.35 + drift):
                best = self.rng.choice(neutral)
            s.genome = best
            s.variance = min(1.0, s.variance + 0.02 * gens)
            if s.lineage_genome is None:
                s.lineage_genome = replace(s.genome)
            if s.genome.distance(s.lineage_genome) > self.SPECIATION_D and s.biomass > 0.5:
                self._speciate(s, year)
        # coğrafi izolasyon: arada bir başka biyoma göç eden alt popülasyon ayrı evrilir
        for s in list(self.species):
            if s.alive and not s.real and s.biomass > 20 and self.rng.random() < min(0.3, 0.02 * gens):
                self._colonize(s, year)

    def _speciate(self, s, year):
        child = Species(self.next_id, self.namer(s), s.kingdom, replace(s.genome), s.biome, s.biomass * 0.4,
                        year, s.sid, False, True, f"{s.name} soyundan türleşme")
        self.next_id += 1
        child.lineage_genome = replace(child.genome)
        s.biomass *= 0.6
        s.lineage_genome = replace(s.genome)
        self.species.append(child)
        self.log.append(("turlesme", child, {"ata": s.name}))

    def _colonize(self, s, year):
        from .biology import BIOME_HABITATS as BH
        options = [b for b in self.env.biomes if b != s.biome and s.genome.habitat in BH.get(b, ())
                   and not any(o.alive and o.biome == b and o.parent == s.sid for o in self.species)]
        if not options:
            return
        b = self.rng.choice(options)
        if fitness(s.genome, self.env, b) < 0.1:
            return
        sub = Species(self.next_id, s.name, s.kingdom, replace(s.genome), b, 2.0, year, s.sid, False, True,
                      f"{s.biome} → {b} göçü (izole alt popülasyon)")
        sub.lineage_genome = replace(s.genome)
        sub.variance = 0.5
        self.next_id += 1
        s.biomass -= 2.0
        self.species.append(sub)
        self.log.append(("goc", sub, {"from": s.biome, "to": b}))

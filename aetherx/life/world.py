# -*- coding: utf-8 -*-
"""
AETHER-X // YAŞAYAN GEZEGEN (KOZMOGENİS LIFE ENGINE birleşimi)
  ProceduralLifeGenerator · EnvironmentalChangeEngine · PlanetaryTimelineEngine · LifeWorld

Gerçek / kurgu ayrımı:
  * Dünya: yaşam gerçektir. Gruplar (bakteriler, arkeler, siyanobakteriler, bitkiler, mantarlar, böcekler,
    balıklar, kuşlar, memeliler...) gerçek adlarıyla ve temsilî özelliklerle gelir; geçmiş zaman çizelgesi
    yayımlanmış jeolojik tarihlerdir (ör. Büyük Oksijenlenme ~2,4 milyar yıl önce, K-Pg ~66 milyon yıl önce).
  * Ay, Mars, Venüs, Jüpiter: NASA'ya göre yaşam bulunmamıştır. İsteğe bağlı "hipotetik senaryo" kurgusal
    mikrop toplulukları üretir ve hepsi "kurgusal" etiketlidir.
  * Kurgusal ötegezegenler: bütün canlılar prosedüreldir ve "kurgusal" etiketlidir.
"""
from __future__ import annotations

import math
import random

from . import environment as E
from . import habitability as H
from . import origin as O
from .biology import BIOME_HABITATS, Ecosystem, Evolution, Genome, Species, fitness, local_temp, acidity
from .events import EventBus

# --- Dünya: gerçek gruplar (temsilî genom) --------------------------------------
EARTH_GROUPS = [
    # ad, alem, biyom, genom alanları, biyokütle, not
    ("Siyanobakteriler", "mikrop", "okyanus", dict(metabolism="fotosentez", diet="üretici", habitat="su", size=-5.5, temp_opt=25, repro=0.9), 30,
     "Oksijenli fotosentezi başlatan bakteriler (gerçek grup)."),
    ("Kemosentetik arkeler", "mikrop", "volkanik bölge", dict(metabolism="kemosentez", diet="üretici", habitat="yeraltı", size=-6, temp_opt=80, temp_tol=25, chem_tol=0.9, repro=0.7), 12,
     "Hidrotermal ortamlarda kimyasal enerjiyle yaşar (gerçek grup)."),
    ("Ayrıştırıcı bakteriler", "mikrop", "tropikal orman", dict(metabolism="heterotrof", diet="ayrıştırıcı", habitat="kara", size=-6, repro=0.9), 15,
     "Ölü organik maddeyi parçalar, azotu döngüye geri katar (gerçek grup)."),
    ("Mantarlar", "mantar", "tropikal orman", dict(metabolism="heterotrof", diet="ayrıştırıcı", habitat="kara", size=-3, repro=0.6), 12,
     "Ayrıştırıcı ve bitkilerle ortak yaşayan (mikoriza) organizmalar (gerçek grup)."),
    ("Fitoplankton (algler)", "mikrop", "okyanus", dict(metabolism="fotosentez", diet="üretici", habitat="su", size=-4.5, temp_opt=18, repro=0.85), 40,
     "Okyanus besin ağının tabanı (gerçek grup)."),
    ("Tropikal ağaçlar", "bitki", "tropikal orman", dict(metabolism="fotosentez", diet="üretici", habitat="kara", size=1.4, temp_opt=27, temp_tol=12, repro=0.3), 70,
     "Kara bitkileri (gerçek grup)."),
    ("Kaktüsler ve kuraklık bitkileri", "bitki", "çöl", dict(metabolism="fotosentez", diet="üretici", habitat="kara", size=0, temp_opt=35, temp_tol=20, repro=0.3), 14,
     "Su depolayan çöl bitkileri (gerçek grup)."),
    ("Buz algleri", "mikrop", "buzul", dict(metabolism="fotosentez", diet="üretici", habitat="kara", size=-5, temp_opt=-5, temp_tol=15, repro=0.6), 8,
     "Kar ve buz üzerinde yaşayan algler (gerçek grup)."),
    ("Böcekler", "hayvan", "tropikal orman", dict(metabolism="heterotrof", diet="otçul", habitat="kara", size=-2.3, speed=0.5, sense=0.5, repro=0.9, social=0.6), 10,
     "En kalabalık hayvan grubu (gerçek grup)."),
    ("Zooplankton", "hayvan", "okyanus", dict(metabolism="heterotrof", diet="otçul", habitat="su", size=-3, speed=0.3, sense=0.3, repro=0.9), 12,
     "Fitoplanktonla beslenen küçük deniz hayvanları (gerçek grup)."),
    ("Balıklar", "hayvan", "okyanus", dict(metabolism="heterotrof", diet="hepçil", habitat="su", size=-0.7, speed=0.7, sense=0.6, repro=0.6, social=0.5), 5,
     "Deniz omurgalıları (gerçek grup)."),
    ("Kuşlar", "hayvan", "tropikal orman", dict(metabolism="heterotrof", diet="hepçil", habitat="hava", size=-1, speed=0.9, sense=0.8, repro=0.5, social=0.5), 2.5,
     "Uçan omurgalılar (gerçek grup)."),
    ("Kertenkeleler", "hayvan", "çöl", dict(metabolism="heterotrof", diet="etçil", habitat="kara", size=-1, speed=0.6, sense=0.6, repro=0.4), 1.2,
     "Sıcağa uyumlu sürüngenler (gerçek grup)."),
    ("Büyük memeliler (yırtıcı)", "hayvan", "tropikal orman", dict(metabolism="heterotrof", diet="etçil", habitat="kara", size=0.2, speed=0.8, sense=0.9, defense=0.6, repro=0.2, social=0.4), 0.8,
     "Kara yırtıcıları (gerçek grup)."),
    ("Köpekbalıkları", "hayvan", "okyanus", dict(metabolism="heterotrof", diet="etçil", habitat="su", size=0.4, speed=0.8, sense=0.9, defense=0.6, repro=0.15), 0.6,
     "Deniz yırtıcıları (gerçek grup)."),
    ("Kutup ayıları", "hayvan", "buzul", dict(metabolism="heterotrof", diet="etçil", habitat="kara", size=0.6, temp_opt=-10, temp_tol=20, speed=0.6, sense=0.8, repro=0.15), 0.2,
     "Buzul yırtıcısı (gerçek grup)."),
    ("Çöl kemirgenleri", "hayvan", "çöl", dict(metabolism="heterotrof", diet="otçul", habitat="kara", size=-1.3, temp_opt=30, temp_tol=18, speed=0.6, sense=0.6, repro=0.8), 2.5,
     "Tohumla beslenen küçük memeliler (gerçek grup)."),
    ("Kril", "hayvan", "buzul", dict(metabolism="heterotrof", diet="otçul", habitat="su", size=-1.7, temp_opt=0, temp_tol=12, speed=0.3, sense=0.3, repro=0.9, social=0.9), 4,
     "Buz algleriyle beslenen kabuklular (gerçek grup)."),
    ("Foklar", "hayvan", "buzul", dict(metabolism="heterotrof", diet="hepçil", habitat="su", size=0.2, temp_opt=0, temp_tol=15, speed=0.7, sense=0.7, repro=0.3, social=0.5), 0.8,
     "Kutup denizlerinin memelileri (gerçek grup)."),
    ("Termofil bakteriler", "mikrop", "volkanik bölge", dict(metabolism="anaerobik", diet="ayrıştırıcı", habitat="yeraltı", size=-6, temp_opt=70, temp_tol=25, chem_tol=0.8, repro=0.8), 6,
     "Sıcak kaynaklarda yaşayan bakteriler (gerçek grup)."),
]

# yayımlanmış jeolojik zaman çizelgesi (yıl önce; NASA Astrobiyoloji ve Uluslararası Stratigrafi Komisyonu tarihleri)
EARTH_TIMELINE = [
    (-4.54e9, "Dünya oluştu"), (-3.7e9, "En eski yaşam izleri (stromatolit ve izotop kanıtları, ~3,7 milyar yıl)"),
    (-2.4e9, "Büyük Oksijenlenme Olayı: siyanobakteriler atmosfere oksijen kattı"),
    (-1.6e9, "Çok hücreli yaşamın erken kanıtları"), (-5.38e8, "Kambriyen patlaması: hayvan çeşitliliği hızla arttı"),
    (-4.7e8, "Bitkiler karaya çıktı"), (-4.45e8, "Ordovisiyen–Silüriyen yok oluşu"),
    (-2.52e8, "Permiyen–Triyas yok oluşu (en büyük kitlesel yok oluş)"),
    (-6.6e7, "Kretase–Paleojen yok oluşu: Chicxulub çarpması, kuş olmayan dinozorlar yok oldu"),
    (-3.0e5, "Homo sapiens ortaya çıktı"),
]

SYL_A = ("ve", "lo", "ra", "thal", "ky", "zor", "mi", "ae", "qu", "ne", "sil", "vor", "ta", "phy", "lux", "dra")
SYL_B = ("ra", "nis", "tus", "lia", "xa", "ron", "mira", "pha", "lis", "ka", "vex", "dun", "oth", "sa")


class LifeWorld:
    """Bir gezegenin yaşayan dünyası. Bütün değişiklikler olay yoluna (EventBus) yayımlanır."""

    def __init__(self, key, bus=None, seed=None, scenario=False):
        self.key = key
        self.env = E.get(key)
        self.bus = bus or EventBus()
        self.rng = random.Random(seed if seed is not None else sum(map(ord, key)) * 7919)
        self.year = 0.0
        self.species = []
        self.timeline = []                 # (yıl, tür, metin, gerçek?)
        self.scenario = scenario           # Güneş Sistemi cisimleri için kurgusal "hipotetik yaşam" senaryosu
        self.weather = []                  # etkin hava olayları: dict(kind, strength, until)
        self.hab = H.evaluate(self.env)
        self.origin = O.plausible(self.env, include_fiction=self.env.kurgusal or scenario)
        self.network, self.origin_year = O.simulate_network(self.env)
        self._generate()
        self.eco = Ecosystem(self.env, self.species, self.rng)
        self.evo = Evolution(self.env, self.species, self.rng, self._name_child)
        self.discovered_biomes = set()
        self._last_pop = {}

    # ---------------------------------------------------------------- üretim
    def _name(self):
        r = self.rng
        g = (r.choice(SYL_A) + r.choice(SYL_B)).capitalize()
        s = r.choice(SYL_A) + r.choice(SYL_B) + r.choice(("is", "us", "a", "ensis", "oides"))
        return f"{g} {s}"

    def _name_child(self, parent):
        return parent.name.split(" ")[0] + " " + self.rng.choice(SYL_A) + self.rng.choice(SYL_B) + "us"

    def _add(self, name, kingdom, biome, genome, biomass, real=False, note=""):
        if not real:     # prosedürel canlılar yaşadıkları alanın yerel koşullarına uyumlu doğar
            env = self.env
            genome.temp_opt = local_temp(env, biome, genome.habitat)
            p = env.pressure_bar or 1.0
            genome.press_min = min(genome.press_min, p * 0.5)
            genome.press_max = max(genome.press_max, p * 2.0)
            genome.chem_tol = max(genome.chem_tol, min(1.0, acidity(env, biome) + 0.1))
            shield = 0.15 if genome.habitat in ("yeraltı", "buzaltı", "su") else 1.0
            genome.rad_tol = max(genome.rad_tol, min(1.0, env.radiation * shield + 0.1))
        s = Species(len(self.species) + 1, name, kingdom, genome, biome, biomass, self.year, None, real, not real, note)
        s.lineage_genome = Genome(**{k: getattr(genome, k) for k in genome.__dataclass_fields__})
        self.species.append(s)
        return s

    def _generate(self):
        env = self.env
        if env.known_life:          # Dünya: gerçek gruplar ve gerçek tarih
            for name, kingdom, biome, g, bm, note in EARTH_GROUPS:
                self._add(name, kingdom, biome, Genome(**g), bm, True, note)
            for y, txt in EARTH_TIMELINE:
                self.timeline.append((y, "tarih", txt, True))
            return
        if not env.kurgusal and not self.scenario:
            self.timeline.append((0.0, "bilgi", f"{env.name}: NASA'ya göre yaşam bulunmamıştır.", True))
            return
        # prosedürel (kurgusal) yaşam: her biyomda üretici -> tüketici -> ayrıştırıcı zinciri, ortama uyumlu genomlar
        T = env.temp_c
        hot = T > 50 or env.geology > 0.8
        cold = T < -20
        for biome in env.biomes:
            habs = BIOME_HABITATS.get(biome, ("kara",))
            hab0 = habs[0]
            micro_hab = "yeraltı" if "yeraltı" in habs else hab0
            # mikroplar: ortamın enerjisine göre metabolizma
            met = "kemosentez" if (hot or env.irradiance < 300 or micro_hab in ("yeraltı", "buzaltı")) else "fotosentez"
            if not env.kurgusal and self.scenario:
                met = "kemosentez"
                micro_hab = "yeraltı" if "yeraltı" in habs else ("buzaltı" if "buzaltı" in habs else hab0)
            topt = T if micro_hab not in ("yeraltı", "buzaltı") else max(T, 4.0)
            self._add(self._name(), "mikrop", biome,
                      Genome(temp_opt=topt, temp_tol=30, metabolism=met, diet="üretici", habitat=micro_hab, size=-5.8,
                             chem_tol=0.7 if hot else 0.3, rad_tol=min(0.95, env.radiation + 0.2), repro=0.85,
                             press_min=0.0, press_max=500), 25, note=f"kurgusal {met} mikrobu")
            self._add(self._name(), "mikrop", biome,
                      Genome(temp_opt=topt, temp_tol=30, metabolism="anaerobik", diet="ayrıştırıcı", habitat=micro_hab,
                             size=-6, chem_tol=0.6, rad_tol=min(0.95, env.radiation + 0.2), repro=0.8, press_min=0.0,
                             press_max=500), 8, note="kurgusal ayrıştırıcı")
            if not env.kurgusal:
                continue          # Güneş Sistemi hipotetik senaryosu: yalnız mikrobiyal
            if self.hab.score < 0.35:
                continue
            land = "kara" in habs
            pk = "bitki" if land else "mikrop"
            self._add(self._name(), pk, biome,
                      Genome(temp_opt=T, temp_tol=22, metabolism="fotosentez", diet="üretici", habitat="kara" if land else "su",
                             size=0.8 if land else -3.5, rad_tol=env.radiation + 0.1, repro=0.5), 50,
                      note="kurgusal üretici (" + ("kara bitkisi" if land else "alg benzeri") + ")")
            hab_a = "kara" if land else "su"
            herb = self._add(self._name(), "hayvan", biome,
                             Genome(temp_opt=T, temp_tol=20, diet="otçul", habitat=hab_a, size=-1.2, speed=0.5, sense=0.5,
                                    repro=0.8, social=0.7, rad_tol=env.radiation + 0.1), 8, note="kurgusal otçul (sürü)")
            if "hava" in habs:
                self._add(self._name(), "hayvan", biome,
                          Genome(temp_opt=T, temp_tol=20, diet="hepçil", habitat="hava", size=-1.6, speed=0.9, sense=0.7,
                                 repro=0.6, social=0.4), 2, note="kurgusal uçan hepçil")
            if self.hab.score > 0.5:
                self._add(self._name(), "hayvan", biome,
                          Genome(temp_opt=T, temp_tol=18, diet="etçil", habitat=hab_a, size=herb.genome.size + 0.9,
                                 speed=0.8, sense=0.85, defense=0.5, repro=0.3), 1.2, note="kurgusal yalnız avcı")
            self._add(self._name(), "mantar", biome,
                      Genome(temp_opt=T, temp_tol=25, metabolism="heterotrof", diet="ayrıştırıcı", habitat=hab_a, size=-3,
                             repro=0.6), 6, note="kurgusal mantar benzeri ayrıştırıcı")
        oy = self.origin_year
        self.timeline.append((0.0, "köken", "Prebiyotik ağ protohücre eşiğine " +
                              (f"{oy / 1e6:.0f} milyon yılda ulaştı (oyun modeli)" if oy else "ulaşamadı (oyun modeli)") +
                              " — kurgusal yaşam başlangıcı", False))

    # ---------------------------------------------------------- çevresel olay
    EVENTS = {
        "volkan": ("VolcanicEruption", "Volkanik patlama"), "meteor": ("MeteorImpact", "Meteor çarpması"),
        "kuraklik": ("Drought", "Kuraklık"), "buzul": ("IceAge", "Buzul dönemi"), "sicak": ("HeatWave", "Aşırı sıcaklık"),
        "atmosfer": ("AtmosphereChanged", "Atmosfer değişimi"), "deniz": ("SeaLevelChanged", "Deniz seviyesi değişimi"),
        "radyasyon": ("RadiationSpike", "Radyasyon artışı"), "yildiz": ("StellarFlare", "Yıldız patlaması (flare)"),
        "firtina": ("StormStarted", "Fırtına"),
    }

    def trigger(self, kind, strength=0.5, biome=None, pos=None):
        """Çevresel değişim olayı: çevreyi ve popülasyonları etkiler, olay yoluna yayımlanır, zaman çizelgesine yazılır."""
        env = self.env
        ev_name, label = self.EVENTS[kind]
        s = max(0.05, min(1.0, strength))
        hit = biome or (self.rng.choice(env.biomes) if env.biomes else None)
        kill = {}
        if kind == "volkan":
            env.temp_c += 1.5 * s
            env.atmosphere["CO2"] = env.atmosphere.get("CO2", 0) + 0.002 * s
            kill = {hit: 0.5 * s}
        elif kind == "meteor":
            env.temp_c -= 4 * s
            kill = {b: (0.9 * s if b == hit else 0.35 * s) for b in env.biomes}
        elif kind == "kuraklik":
            env.surface_water = max(0.0, env.surface_water - 0.05 * s)
            kill = {b: 0.3 * s for b in env.biomes if b in ("tropikal orman", "çöl", "tuz ovası")}
        elif kind == "buzul":
            env.temp_c -= 8 * s
            env.ice = min(1.0, env.ice + 0.3 * s)
        elif kind == "sicak":
            env.temp_c += 6 * s
        elif kind == "atmosfer":
            env.atmosphere["O2"] = max(0.0, env.atmosphere.get("O2", 0) - 0.03 * s)
            if env.pressure_bar:
                env.pressure_bar *= (1 - 0.1 * s)
        elif kind == "deniz":
            env.surface_water = min(1.0, env.surface_water + 0.04 * s)
            kill = {b: 0.2 * s for b in env.biomes if b in ("çöl", "tropikal orman")}
        elif kind == "radyasyon":
            env.radiation = min(1.0, env.radiation + 0.4 * s)
        elif kind == "yildiz":
            env.radiation = min(1.0, env.radiation + 0.25 * s)
            env.temp_c += 1.0 * s
        elif kind == "firtina":
            self.weather.append({"kind": "fırtına" if env.pressure_bar and env.pressure_bar > 0.1 else "toz fırtınası",
                                 "strength": s, "until": self.year + 2 + 10 * s, "biome": hit})
            kill = {hit: 0.08 * s}
        for s_ in self.species:
            k = kill.get(s_.biome, 0.0) * (0.5 if s_.genome.habitat in ("yeraltı", "su", "buzaltı") else 1.0)
            if s_.alive and k:
                s_.biomass *= (1 - k)
        self.hab = H.evaluate(env)
        self.timeline.append((self.year, "olay", f"{label} (şiddet %{s * 100:.0f}" + (f", {hit}" if hit else "") + ")", False))
        self.bus.publish(ev_name, planet=self.key, strength=s, biome=hit, pos=pos, label=label, year=self.year)
        if kind == "firtina":
            pass
        return label

    # ----------------------------------------------------------------- zaman
    def step(self, dt_years):
        """Simülasyonu ilerletir. Ekolojik zaman (yıllar) ekosistemi, evrimsel zaman (binlerce yıl+) evrimi sürer."""
        if not self.species:
            self.year += dt_years
            return
        before = {s.sid: s.alive for s in self.species}
        eco_dt = min(dt_years, 50.0)
        self.eco.step(eco_dt)
        self.year += dt_years
        if dt_years >= 1000:
            self.evo.step(dt_years, self.year)
            # çevre yavaşça dengesine döner (olay etkileri sönümlenir)
            base = E.get(self.key)
            k = min(1.0, dt_years / 2e5)
            self.env.temp_c += (base.temp_c - self.env.temp_c) * k
            self.env.radiation += (base.radiation - self.env.radiation) * k
        else:
            for s in self.species:
                if s.alive and s.biomass <= 1e-3:
                    s.extinct_year = self.year
                    self.evo.log.append(("yok_olus", s, {}))
        self.weather = [w for w in self.weather if w["until"] > self.year]
        if self.weather == [] and getattr(self, "_storm_on", False):
            self.bus.publish("StormEnded", planet=self.key)
        self._storm_on = bool(self.weather)
        self._flush_evolution_log()
        self._population_events()

    def _flush_evolution_log(self):
        for kind, s, data in self.evo.log:
            if kind == "yok_olus":
                self.timeline.append((self.year, "yok oluş", f"{s.name} ({s.biome}) yok oldu", s.real))
                self.bus.publish("SpeciesExtinction", planet=self.key, species=s.name, sid=s.sid, biome=s.biome,
                                 kurgusal=s.kurgusal, year=self.year)
            elif kind == "turlesme":
                self.timeline.append((self.year, "türleşme", f"{s.name}: {data['ata']} soyundan yeni tür", False))
                self.bus.publish("Speciation", planet=self.key, species=s.name, sid=s.sid, parent=data["ata"], year=self.year)
            elif kind == "goc":
                self.timeline.append((self.year, "göç", f"{s.name}: {data['from']} → {data['to']} (izole alt popülasyon)", False))
            elif kind == "darbogaz":
                self.timeline.append((self.year, "darboğaz", f"{s.name} popülasyon darboğazında", False))
        self.evo.log.clear()

    def _population_events(self):
        for biome, sp in self.eco.biomes().items():
            tot = sum(s.biomass for s in sp)
            old = self._last_pop.get(biome)
            self._last_pop[biome] = tot
            if old and abs(tot - old) / max(1e-6, old) > 0.25:
                self.bus.publish("EcosystemChanged", planet=self.key, biome=biome, biomass=tot, change=(tot - old) / old)

    # ------------------------------------------------------------ keşif / ses
    def discover(self, biome):
        """Oyuncu bir biyomu araştırır: biyom ve içindeki türler keşfedilir (olaylar ses motorunu tetikler)."""
        out = []
        if biome not in self.discovered_biomes:
            self.discovered_biomes.add(biome)
            self.bus.publish("NewBiomeDiscovered", planet=self.key, biome=biome)
        for s in self.species:
            if s.alive and s.biome == biome and not s.discovered:
                s.discovered = True
                out.append(s)
                self.bus.publish("LifeformDiscovered", planet=self.key, species=s.name, sid=s.sid, kingdom=s.kingdom,
                                 kurgusal=s.kurgusal, real=s.real)
        return out

    def soundscape(self, biome):
        """Ses motoruna biyomun yaşam yoğunluğu: grup -> 0..1 (popülasyon tabanlı ses katmanları)."""
        layers = {"böcek": 0.0, "kuş": 0.0, "kurbağa": 0.0, "memeli": 0.0, "deniz": 0.0, "bitki": 0.0}
        for s in self.species:
            if not s.alive or s.biome != biome:
                continue
            g = s.genome
            if s.kingdom == "bitki":
                layers["bitki"] += s.biomass / 80
            elif s.kingdom == "hayvan":
                if g.habitat == "su":
                    layers["deniz"] += s.biomass / 12
                elif g.habitat == "hava":
                    layers["kuş"] += s.biomass / 3
                elif g.size < -1.8:
                    layers["böcek"] += s.biomass / 10
                elif g.size < -0.5:
                    layers["kurbağa"] += s.biomass / 4
                else:
                    layers["memeli"] += s.biomass / 1.5
        return {k: min(1.0, v) for k, v in layers.items()}

    def stats(self):
        alive = [s for s in self.species if s.alive]
        return {"yıl": self.year, "tür": len(alive), "yok olan": len(self.species) - len(alive),
                "biyokütle": sum(s.biomass for s in alive), "döngüler": dict(self.eco.pools)}

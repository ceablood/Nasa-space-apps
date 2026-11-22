# -*- coding: utf-8 -*-
"""
AETHER-X // KOZMİK SES MOTORU (CAE) — ÇEKİRDEK
  AudioCore · AudioMixer · AudioSettingsManager · AudioAccessibilityManager · AudioAssetManager ·
  AudioPerformanceManager · SpatialAudioEngine · AudioEventManager · DynamicMusicEngine

Oyunun mevcut pygame ses altyapısı (aetherx.audio.Audio) korunur; CAE onun üstüne kanal ayırır.
Yaşam Motoru ile bağlantı yalnız ortak olay yolu (life.events.EventBus) üzerindendir.
Arayüz (pygame) olmadan da çalışır: testlerde ses "çalınmaz", kararlar ve günlükler doğrulanır.
"""
import math
import time
from collections import OrderedDict, deque

import numpy as np

from . import sounds as SD
from . import synth as S

CATEGORIES = ("ana", "ortam", "canlı", "atmosfer", "okyanus", "jeoloji", "uzay aracı", "arayüz", "müzik", "sinematik")
LICENSE = "Özgün — AETHER-X içinde prosedürel sentez (numpy); üçüncü taraf kayıt yok, lisans gerektirmez"


# ===================================================================== ayarlar
class AudioSettings:
    """AudioSettingsManager + AudioAccessibilityManager. Tercihler oyunun PREFS sözlüğünde saklanır."""

    DEFAULT = {"vol": {c: (0.8 if c != "ana" else 0.9) for c in CATEGORIES}, "mono": False, "headphones": True,
               "captions": True, "reduce_high": False, "limit_loud": True}

    def __init__(self, store=None):
        self.store = store if store is not None else {}
        cur = self.store.get("cae")
        self.d = {"vol": dict(self.DEFAULT["vol"]), **{k: v for k, v in self.DEFAULT.items() if k != "vol"}}
        if isinstance(cur, dict):
            self.d["vol"].update({k: float(v) for k, v in cur.get("vol", {}).items() if k in CATEGORIES})
            for k in ("mono", "headphones", "captions", "reduce_high", "limit_loud"):
                if k in cur:
                    self.d[k] = bool(cur[k])

    def save(self):
        self.store["cae"] = {"vol": dict(self.d["vol"]), **{k: self.d[k] for k in ("mono", "headphones", "captions",
                                                                                    "reduce_high", "limit_loud")}}

    def gain(self, cat):
        return self.d["vol"]["ana"] * self.d["vol"].get(cat, 1.0)

    def __getitem__(self, k):
        return self.d[k]

    def set(self, k, v):
        if k in CATEGORIES:
            self.d["vol"][k] = max(0.0, min(1.0, float(v)))
        else:
            self.d[k] = v
        self.save()

    def process(self, x):
        """Erişilebilirlik süzgeçleri sentez sırasında uygulanır (çalma sırasında ek yük yok)."""
        if self.d["reduce_high"]:
            x = S.fft_filter(x, None, 4000)
        if self.d["limit_loud"]:
            x = S.smooth_limit(x, 0.7)
        return x


# ================================================================ varlıklar
class AssetManager:
    """AudioAssetManager: her sesin künyesi (kategori klasörü, lisans, kaynak, biçim) + bellek bütçeli önbellek."""

    FOLDERS = {"ortam": "Audio/Ambience", "atmosfer": "Audio/Atmosphere", "canlı": "Audio/Biology/Fauna",
               "bitki": "Audio/Biology/Flora", "mikrop": "Audio/Biology/Microbial", "jeoloji": "Audio/Geological",
               "okyanus": "Audio/Ambience/Ocean", "uzay aracı": "Audio/Spacecraft", "arayüz": "Audio/Interface",
               "müzik": "Audio/Music", "sinematik": "Audio/Cinematics"}

    def __init__(self, budget_mb=48):
        self.meta = OrderedDict()
        self.cache = OrderedDict()          # anahtar -> (numpy, pygame.Sound ya da None)
        self.budget = budget_mb * 1024 * 1024
        self.bytes = 0
        self.evicted = 0

    def register(self, key, category, purpose, event=None, source="aetherx/cae/sounds.py", channels=1, label=None):
        self.meta[key] = {"dosya": f"{self.FOLDERS.get(category, 'Audio/Misc')}/{key}.pcm", "kategori": category,
                          "lisans": LICENSE, "kaynak": source, "biçim": "PCM 16-bit (bellekte üretilir)",
                          "örnekleme": S.SR, "kanal": channels, "amaç": purpose, "olay": event, "etiket": label}

    def get(self, key):
        v = self.cache.get(key)
        if v is not None:
            self.cache.move_to_end(key)
        return v

    def put(self, key, arr, snd=None):
        if key in self.cache:
            self.bytes -= self.cache[key][0].nbytes
        self.cache[key] = (arr, snd)
        self.cache.move_to_end(key)
        self.bytes += arr.nbytes
        while self.bytes > self.budget and len(self.cache) > 1:      # en uzun süredir kullanılmayanı çıkar
            k, (a, _) = self.cache.popitem(last=False)
            self.bytes -= a.nbytes
            self.evicted += 1


# ================================================================ konumsal
class Spatial:
    """SpatialAudioEngine: yön (eşit güçte stereo), uzaklık sönümü, engel, ortam profili (açık/mağara/su altı/kabin/vakum)."""

    PROFILES = {"açık": {"reverb": 0.0, "hi": None}, "mağara": {"reverb": 0.55, "hi": None},
                "su altı": {"reverb": 0.25, "hi": 900}, "kabin": {"reverb": 0.15, "hi": 3000}, "vakum": {"reverb": 0.0, "hi": 0}}

    def __init__(self):
        self.listener = (0.0, 0.0)
        self.profile = "açık"
        self.ref = 10.0             # m: tam şiddet yarıçapı
        self.max_dist = 400.0

    def params(self, pos, occlusion=0.0, mono=False):
        """-> (sol, sağ, uzaklık) kazanç. pos None ise merkezde (arayüz/kabin sesi)."""
        if pos is None:
            return 1.0, 1.0, 0.0
        dx, dy = pos[0] - self.listener[0], pos[1] - self.listener[1]
        d = math.hypot(dx, dy)
        g = 1.0 / (1.0 + max(0.0, d - self.ref) / self.ref) ** 1.2 * (1 - 0.7 * occlusion)
        if d > self.max_dist:
            g = 0.0
        if mono:
            return g * 0.75, g * 0.75, d
        pan = max(-1.0, min(1.0, dx / (abs(dx) + abs(dy) + 1e-6))) if d > 0.5 else 0.0
        a = (pan + 1) * math.pi / 4
        return g * math.cos(a), g * math.sin(a), d


# =================================================================== müzik
class DynamicMusic:
    """DynamicMusicEngine: oyun durumu -> müzik; ani geçiş yok (çapraz geçiş + en kısa kalma süresi)."""

    STATES = {"ana menü": "menu", "gezegen keşfi": "colony", "yaşam keşfi": "colony", "uzay yolculuğu": "space",
              "bilimsel araştırma": "base", "tehlikeli bölge": "storm", "büyük kozmik olay": "storm",
              "yeni tür keşfi": "colony", "ekosistem değişimi": "space", "sinematik sahne": "launch"}
    MIN_DWELL = 8.0

    def __init__(self, audio=None):
        self.audio = audio
        self.state = None
        self.since = -1e9
        self.pending = None
        self.log = deque(maxlen=30)

    def request(self, state, now, urgent=False):
        if state not in self.STATES or state == self.state:
            return False
        if not urgent and now - self.since < self.MIN_DWELL:
            self.pending = state
            return False
        self._switch(state, now)
        return True

    def update(self, now):
        if self.pending and now - self.since >= self.MIN_DWELL:
            st, self.pending = self.pending, None
            self._switch(st, now)

    def _switch(self, state, now):
        self.state, self.since = state, now
        self.log.append((now, state, self.STATES[state]))
        if self.audio:
            self.audio.music(self.STATES[state], fade=2600)


# ================================================================ olaylar
class EventManager:
    """AudioEventManager: yaşam/çevre olaylarını seslere bağlar. Öncelik, yineleme koruması, uzaklık ve ses bütçesi."""

    # olay -> (ses anahtarı, kategori, öncelik 0-9, bekleme sn, altyazı)
    RULES = {
        "LifeformDiscovered": ("keşif", "arayüz", 7, 1.5, "Yeni yaşam formu keşfedildi"),
        "NewBiomeDiscovered": ("biyom keşfi", "arayüz", 7, 3.0, "Yeni biyom keşfedildi"),
        "SpeciesExtinction": ("rapor", "arayüz", 5, 4.0, "Bilimsel rapor: bir tür yok oldu"),
        "Speciation": ("keşif", "arayüz", 3, 6.0, "Yeni tür ortaya çıktı"),
        "EcosystemChanged": (None, "ortam", 2, 5.0, "Ekosistem değişti: ortam sesleri güncellendi"),
        "VolcanicEruption": ("patlama", "jeoloji", 9, 4.0, "Volkanik patlama"),
        "MeteorImpact": ("çarpma", "jeoloji", 9, 4.0, "Meteor çarpması"),
        "Earthquake": ("patlama", "jeoloji", 8, 4.0, "Yer sarsıntısı"),
        "StormStarted": ("gök gürültüsü", "atmosfer", 6, 6.0, "Fırtına başladı"),
        "StormEnded": (None, "atmosfer", 1, 6.0, "Fırtına dindi"),
        "IceAge": ("buz çatlaması", "jeoloji", 5, 6.0, "Buzul dönemi başladı"),
        "OceanCurrentChanged": (None, "okyanus", 2, 6.0, "Okyanus akıntısı değişti"),
        "PlanetLanding": ("iniş takımı", "uzay aracı", 8, 3.0, "Gezegene iniş"),
        "EngineStart": ("motor", "uzay aracı", 6, 0.5, "Motor ateşlendi"),
        "RadiationSpike": ("rapor", "arayüz", 6, 5.0, "Radyasyon artışı uyarısı"),
        "StellarFlare": ("rapor", "arayüz", 6, 5.0, "Yıldız patlaması"),
        "Drought": (None, "ortam", 3, 6.0, "Kuraklık"), "HeatWave": (None, "ortam", 3, 6.0, "Aşırı sıcaklık"),
        "AtmosphereChanged": (None, "atmosfer", 3, 6.0, "Atmosfer değişti"),
        "SeaLevelChanged": (None, "okyanus", 3, 6.0, "Deniz seviyesi değişti"),
    }
    MAX_VOICES = 10

    def __init__(self, core):
        self.core = core
        self.last = {}                   # (olay, anahtar) -> zaman
        self.active = deque()            # (bitiş zamanı, öncelik)
        self.log = deque(maxlen=60)      # geliştirici modu: olay -> ses -> sonuç
        self.captions = deque(maxlen=4)  # (zaman, metin)

    def on_event(self, ev):
        name = ev["name"]
        rule = self.RULES.get(name)
        if not rule:
            return
        key, cat, prio, cool, cap = rule
        now = self.core.now()
        dedupe = (name, ev.get("biome") or ev.get("species") or "")
        if now - self.last.get(dedupe, -1e9) < cool:
            self.log.append((now, name, key, "yinelenen olay: atlandı"))
            return
        self.last[dedupe] = now
        while self.active and self.active[0][0] < now:
            self.active.popleft()
        if len(self.active) >= self.MAX_VOICES and prio < 6:
            self.log.append((now, name, key, "ses bütçesi dolu: düşük öncelik atlandı"))
            self.core.perf["dropped"] += 1
            return
        pos = ev.get("pos")
        result = "yalnız ortam güncellemesi"
        if key:
            dur = self.core.play_effect(key, cat, ev, pos)
            if dur is None:
                result = "duyulmaz (vakum/uzaklık) — yalnız altyazı"
            else:
                self.active.append((now + dur, prio))
                result = f"çalındı ({cat}, {dur:.1f} sn)"
        if name in ("EcosystemChanged", "StormStarted", "StormEnded", "Drought", "AtmosphereChanged", "SeaLevelChanged",
                    "OceanCurrentChanged"):
            self.core.refresh_ambience()
        self.log.append((now, name, key, result))
        if self.core.settings["captions"] and prio >= 3:      # arka plan güncellemeleri altyazı kalabalığı yapmasın
            extra = f": {ev['species']}" if ev.get("species") else (f" ({ev['biome']})" if ev.get("biome") else "")
            self.captions.append((now, f"[{cap}{extra}]"))
        mus = {"LifeformDiscovered": "yaşam keşfi", "VolcanicEruption": "büyük kozmik olay", "MeteorImpact": "büyük kozmik olay",
               "StormStarted": "tehlikeli bölge", "EcosystemChanged": "ekosistem değişimi", "Speciation": "yeni tür keşfi"}.get(name)
        if mus:
            self.core.music.request(mus, now, urgent=prio >= 9)


# ==================================================================== çekirdek
class CosmicAudio:
    """AudioCore + AudioMixer + PlanetaryAmbienceEngine birleşimi."""

    LAYERS = ("atmosfer", "okyanus", "jeoloji", "canlı", "bitki", "uzay aracı")

    def __init__(self, audio=None, bus=None, store=None, clock=None):
        self.audio = audio                          # aetherx.audio.Audio (pygame); None: sessiz (test) kip
        self.settings = AudioSettings(store)
        self.assets = AssetManager()
        self.spatial = Spatial()
        self.music = DynamicMusic(audio)
        self.events = EventManager(self)
        self.clock = clock or time.monotonic
        self.perf = {"synth_ms": 0.0, "builds": 0, "played": 0, "dropped": 0, "voices": 0}
        self.world = None
        self.biome = None
        self.layer_buf = {}                         # katman -> numpy döngü
        self.layer_cat = {"atmosfer": "atmosfer", "okyanus": "okyanus", "jeoloji": "jeoloji", "canlı": "canlı",
                          "bitki": "ortam", "uzay aracı": "uzay aracı"}
        self.layer_ch = {}
        self.label = ""
        self.bus = None
        if bus is not None:
            self.attach(bus)
        self._register_assets()

    def now(self):
        return self.clock()

    def attach(self, bus):
        self.bus = bus
        bus.subscribe("*", self.events.on_event)

    def _register_assets(self):
        A = self.assets
        for k, c, p, e in (("rüzgâr", "atmosfer", "atmosfer ortamı", "EcosystemChanged"), ("yağmur", "atmosfer", "yağmur", "StormStarted"),
                           ("gök gürültüsü", "atmosfer", "fırtına", "StormStarted"), ("dalga", "okyanus", "okyanus ortamı", None),
                           ("su altı", "okyanus", "su altı akustiği", None), ("yer titreşimi", "jeoloji", "jeolojik zemin", None),
                           ("patlama", "jeoloji", "volkan / sarsıntı", "VolcanicEruption"), ("çarpma", "jeoloji", "meteor", "MeteorImpact"),
                           ("buz çatlaması", "jeoloji", "buzul", "IceAge"), ("hışırtı", "bitki", "yaprak hareketi (yalnız rüzgârda)", None),
                           ("canlı katmanı", "canlı", "popülasyon tabanlı canlı sesleri", "EcosystemChanged"),
                           ("mikrobiyal temsil", "mikrop", "laboratuvar görsel-işitsel temsil (ölçüm değil)", None),
                           ("motor", "uzay aracı", "araç içi motor uğultusu (vakumda dışarıdan: sinematik)", "EngineStart"),
                           ("kabin", "uzay aracı", "kokpit iç ortamı", None), ("tarayıcı", "uzay aracı", "gezegen tarama", None),
                           ("iniş takımı", "uzay aracı", "iniş", "PlanetLanding"), ("keşif", "arayüz", "yeni yaşam formu", "LifeformDiscovered"),
                           ("biyom keşfi", "arayüz", "yeni biyom", "NewBiomeDiscovered"), ("rapor", "arayüz", "bilimsel rapor / uyarı", "SpeciesExtinction")):
            A.register(k, c, p, e, label="sinematik" if k == "motor" else None)

    # ----------------------------------------------------------- sentez yardımcıları
    def _synth(self, key, fn):
        hit = self.assets.get(key)
        if hit is not None:
            return hit[0]
        t0 = time.perf_counter()
        x = self.settings.process(fn())
        self.perf["synth_ms"] += (time.perf_counter() - t0) * 1000
        self.perf["builds"] += 1
        self.assets.put(key, x, None)
        return x

    def _sound(self, key, arr):
        hit = self.assets.get(key)
        if hit is not None and hit[1] is not None:
            return hit[1]
        if not (self.audio and getattr(self.audio, "ok", False)):
            return None
        try:
            snd = self.audio._to_sound(arr, key.startswith("loop:"))
        except Exception:
            return None
        self.assets.put(key, arr, snd)
        return snd

    # ----------------------------------------------------------------- ortam
    def set_scene(self, world, biome=None, profile=None):
        """Gezegen/biyom ortamını kur: atmosfer, okyanus, jeoloji, bitki ve canlı katmanları ayrı kanallarda."""
        self.world = world
        self.biome = biome or (world.env.biomes[0] if world.env.biomes else None)
        if profile is None:
            profile = "vakum" if SD.atmosphere_profile(world.env)["vacuum"] else "açık"
        self.spatial.profile = profile
        self.refresh_ambience()

    def layer_targets(self):
        """Ekosistem ve çevreden katman yoğunlukları (0..1) — arayüz ve testler için de kullanılır."""
        w = self.world
        if w is None:
            return {}
        env = w.env
        prof = SD.atmosphere_profile(env)
        sc = w.soundscape(self.biome) if self.biome else {}
        storm = max([x["strength"] for x in w.weather] + [0.0])
        wind = min(1.0, (sum(env.wind_ms) / 2.0) / 20.0 + storm * 0.8)
        ocean = 1.0 if self.biome in ("okyanus", "resif", "buz altı okyanusu") else (0.3 if env.oceans else 0.0)
        geo = env.geology if self.biome in ("volkanik bölge", "sıcak su kaynakları", "volkanik ova") else env.geology * 0.3
        life = max([v for k, v in sc.items() if k != "bitki"] + [0.0])
        return {"atmosfer": 0.0 if prof["vacuum"] else wind, "okyanus": 0.0 if prof["vacuum"] else ocean,
                "jeoloji": geo, "canlı": 0.0 if prof["vacuum"] else life, "bitki": 0.0 if prof["vacuum"] else sc.get("bitki", 0) * wind,
                "uzay aracı": 1.0 if self.spatial.profile in ("vakum", "kabin") else 0.0, "_storm": storm, "_wind": wind}

    def build_layers(self):
        w = self.world
        env = w.env
        tg = self.layer_targets()
        sc = w.soundscape(self.biome) if self.biome else {}
        uw = self.spatial.profile == "su altı"
        tag = f"{w.key}:{self.biome}"
        out = {}
        out["atmosfer"] = self._synth(f"rüzgâr:{tag}:{round(tg['_wind'], 1)}",
                                      lambda: SD.wind_layer(env, tg["_wind"]) + SD.rain_layer(env, tg["_storm"]))
        out["okyanus"] = self._synth(f"dalga:{tag}:{uw}", lambda: SD.ocean_layer(env, 0.4 + tg["_storm"] * 0.6, uw))
        out["jeoloji"] = self._synth(f"yer:{tag}", lambda: SD.geology_layer(env, tg["jeoloji"]))
        out["bitki"] = self._synth(f"hışırtı:{tag}:{round(tg['_wind'], 1)}", lambda: SD.rustle_layer(env, sc.get("bitki", 0), tg["_wind"]))
        voices = []
        for s in w.species:
            if s.alive and s.biome == self.biome and s.kingdom == "hayvan":
                grp = ("deniz" if s.genome.habitat == "su" else "kuş" if s.genome.habitat == "hava" else
                       "böcek" if s.genome.size < -1.8 else "kurbağa" if s.genome.size < -0.5 else "memeli")
                v = self._synth(f"ses:{s.name}:{'sürü' if s.genome.social > 0.6 else 'çağrı'}",
                                lambda s=s: SD.species_voice(s, "sürü" if s.genome.social > 0.6 else "çağrı"))
                voices.append((grp, v, min(1.0, sc.get(grp, 0))))
        dens = tuple(round(x[2], 1) for x in voices)
        out["canlı"] = self._synth(f"canlı:{tag}:{dens}", lambda: SD.fauna_layer(env, sc, voices))
        out["uzay aracı"] = self._synth("kabin", SD.cockpit_hum)
        if self.spatial.profile == "mağara":
            out = {k: S.reverb(v, 0.55, 1.6) for k, v in out.items()}
        if uw:
            out = {k: (S.fft_filter(v, None, 900) if k != "okyanus" else v) for k, v in out.items()}
        return out, tg

    def refresh_ambience(self):
        if self.world is None:
            return
        self.layer_buf, tg = self.build_layers()
        prof = SD.atmosphere_profile(self.world.env)
        self.label = prof["label"]
        if not (self.audio and getattr(self.audio, "ok", False) and self.audio.enabled):
            return
        import pygame
        for i, name in enumerate(self.LAYERS):
            arr = self.layer_buf.get(name)
            vol = tg.get(name, 0.0) * self.settings.gain(self.layer_cat[name]) * 0.6
            ch = self.layer_ch.get(name)
            if ch is None:
                try:
                    ch = pygame.mixer.Channel(4 + i)      # 4..9: CAE ortam katmanları (0..3 eski motorun)
                except Exception:
                    continue
                self.layer_ch[name] = ch
            if arr is None or vol < 0.01 or not np.any(arr):
                ch.fadeout(800)
                continue
            snd = self._sound(f"loop:{name}:{id(arr)}", arr)
            if snd:
                ch.play(snd, loops=-1, fade_ms=1200)
                ch.set_volume(vol)

    def apply_volumes(self):
        """Ayarlar değişince çalan ortam katmanlarının sesini yeniden sentez yapmadan güncelle."""
        tg = self.layer_targets() if self.world is not None else {}
        for name, ch in self.layer_ch.items():
            try:
                ch.set_volume(tg.get(name, 0.0) * self.settings.gain(self.layer_cat[name]) * 0.6)
            except Exception:
                pass

    def stop_ambience(self):
        for ch in self.layer_ch.values():
            try:
                ch.fadeout(900)
            except Exception:
                pass

    # ---------------------------------------------------------------- efekt
    def effect_array(self, key, ev=None):
        env = self.world.env if self.world else None
        s = (ev or {}).get("strength", 0.7)
        rec = {"keşif": lambda: SD.discovery_chime(bool((ev or {}).get("real") is False)),
               "biyom keşfi": lambda: SD.discovery_chime(True), "rapor": SD.report_tone,
               "patlama": lambda: SD.eruption(env, s), "çarpma": lambda: SD.impact(env, s),
               "gök gürültüsü": lambda: SD.thunder(env, 2.0 + (1 - s) * 6),
               "buz çatlaması": SD.ice_crack, "iniş takımı": SD.landing_gear,
               "motor": lambda: SD.engine_loop(1.0, env is not None and SD.atmosphere_profile(env)["vacuum"]),
               "tarayıcı": SD.scanner_sweep, "mikrobiyal temsil": SD.microbial_representation}
        fn = rec.get(key)
        if fn is None or (env is None and key in ("patlama", "çarpma", "gök gürültüsü")):
            return None
        x = fn()
        return None if x is None else x

    def play_effect(self, key, cat, ev=None, pos=None):
        """Efekti çalar; süreyi (sn) döner. Duyulmazsa None (vakumda gök gürültüsü, çok uzak kaynak)."""
        tag = f"fx:{key}:{(self.world.key if self.world else '-')}:{round((ev or {}).get('strength', 0.7), 1)}"
        arr = self.assets.get(tag)
        arr = arr[0] if arr is not None else None
        if arr is None:
            raw = self.effect_array(key, ev)
            if raw is None:
                return None
            arr = self._synth(tag, lambda: raw)
        l, r, d = self.spatial.params(pos, 0.0, self.settings["mono"])
        g = self.settings.gain(cat)
        if max(l, r) * g < 0.02:
            return None
        self.perf["played"] += 1
        if self.audio and getattr(self.audio, "ok", False) and self.audio.enabled:
            snd = self._sound(tag, arr)
            if snd:
                ch = snd.play()
                if ch:
                    ch.set_volume(l * g, r * g)
        return len(arr) / S.SR

    def call_of(self, species, kind="çağrı", pos=None):
        """FaunaAudioEngine: tek bir canlının konumlu çağrısı (oyuncu yaklaşınca belirginleşir)."""
        key = f"ses:{species.name}:{kind}"
        arr = self._synth(key, lambda: SD.species_voice(species, kind))
        l, r, d = self.spatial.params(pos, 0.0, self.settings["mono"])
        prof = SD.atmosphere_profile(self.world.env) if self.world else {"vacuum": False}
        if prof["vacuum"] or max(l, r) < 0.02:
            return None
        if self.audio and getattr(self.audio, "ok", False) and self.audio.enabled:
            snd = self._sound(key, arr)
            if snd:
                ch = snd.play()
                if ch:
                    g = self.settings.gain("canlı")
                    ch.set_volume(l * g, r * g)
        return (l, r, d)

    def update(self, dt):
        now = self.now()
        self.music.update(now)
        self.perf["voices"] = len(self.events.active)
        while self.events.captions and now - self.events.captions[0][0] > 6.0:
            self.events.captions.popleft()

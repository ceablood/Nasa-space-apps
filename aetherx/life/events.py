# -*- coding: utf-8 -*-
"""
AETHER-X // ORTAK OLAY SİSTEMİ
Yaşam Motoru (KLE) ile Kozmik Ses Motoru (CAE) birbirini doğrudan çağırmaz; ikisi de bu olay yolunu kullanır.
Yayıncı olayı adı ve verisiyle gönderir, aboneler kendi işini yapar. Geçmiş, gözlemevindeki
"hangi olay hangi sesi tetikledi" listesi için tutulur.
"""
from collections import deque

# Bilinen olay adları (yazım hatasıyla sessiz kalan olay olmasın diye yayın sırasında denetlenir)
EVENTS = {
    "LifeformDiscovered", "SpeciesExtinction", "Speciation", "EcosystemChanged", "PopulationBoom",
    "VolcanicEruption", "MeteorImpact", "Earthquake", "StormStarted", "StormEnded", "Drought", "IceAge",
    "HeatWave", "AtmosphereChanged", "SeaLevelChanged", "RadiationSpike", "StellarFlare",
    "OceanCurrentChanged", "PlanetLanding", "NewBiomeDiscovered", "TimelineEvent", "EngineStart", "EngineStop",
}


class EventBus:
    def __init__(self, history=200):
        self.subs = {}
        self.history = deque(maxlen=history)
        self.t = 0.0                    # olay saati (oyun saniyesi; yaşam motoru kendi yılını veride taşır)

    def subscribe(self, name, fn):
        if name != "*" and name not in EVENTS:
            raise ValueError(f"bilinmeyen olay: {name}")
        self.subs.setdefault(name, []).append(fn)

    def publish(self, name, **data):
        if name not in EVENTS:
            raise ValueError(f"bilinmeyen olay: {name}")
        ev = {"name": name, "t": self.t, **data}
        self.history.append(ev)
        for fn in self.subs.get(name, []) + self.subs.get("*", []):
            fn(ev)
        return ev

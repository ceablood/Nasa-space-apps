# -*- coding: utf-8 -*-
"""
KOZMOGENİS // OYUN VERİSİ
12 alanlık üs, roket parçaları (7 gövde, 6 motor, 5 elektrik, 4 anten, 4 yük),
araştırma ağacı, 5 astronot tipi, gezegenler, madenler, görev şablonları,
başarımlar, olaylar ve diplomasi ortakları.
"""

# ===========================================================================
# ÜS - 12 ALAN
# ===========================================================================
# costs[i] = Seviye i'ye çıkmanın bedeli
BUILDINGS = [
    {
        "key": "pads", "name": "Fırlatma Rampası", "short": "RAMPA", "icon": "rocket",
        "color": (255, 140, 50), "start": 1, "max": 3, "costs": {1: 0, 2: 1500, 3: 4000},
        "pos": (1000, 590), "size": (470, 270),
        "desc": "3 rampa: A küçük, B orta, C dev roketler için. Aynı anda 3 roket hazırlanabilir.",
        "levels": {1: "Rampa A açık (küçük roket)", 2: "Rampa B açık (orta roket)", 3: "Rampa C açık (dev roket)"},
    },
    {
        "key": "research", "name": "Araştırma Merkezi", "short": "AR-GE", "icon": "flask",
        "color": (90, 220, 255), "start": 0, "max": 3, "costs": {1: 1000, 2: 3000, 3: 7000},
        "pos": (1000, 250), "size": (240, 190),
        "desc": "Puan vermez. Araştırma süresini kısaltır ve para maliyetini düşürür.",
        "levels": {0: "Yok: 120 sn, indirim yok", 1: "60 sn, %20 para indirimi",
                   2: "40 sn, %40 para indirimi", 3: "24 sn, %60 para indirimi"},
    },
    {
        "key": "astro", "name": "Astronot Merkezi", "short": "ASTRONOT", "icon": "astro",
        "color": (70, 140, 255), "start": 1, "max": 3, "costs": {1: 0, 2: 1200, 3: 3000},
        "pos": (560, 250), "size": (230, 160),
        "desc": "Astronot alırsın, eğitirsin, dinlendirirsin. Uyku odaları, spor salonu, simülatör.",
        "levels": {1: "Kadro kapasitesi 5", 2: "Kadro 8, eğitim %25 hızlı", 3: "Kadro 12, eğitim %50 hızlı"},
    },
    {
        "key": "depot", "name": "Depo", "short": "DEPO", "icon": "box",
        "color": (255, 206, 84), "start": 1, "max": 3, "costs": {1: 0, 2: 800, 3: 2000},
        "pos": (640, 880), "size": (250, 150),
        "desc": "Madenler, Yıldız Tozu ve Tamir Kitleri burada saklanır. Madenler buradan satılır.",
        "levels": {1: "Kapasite 200 birim", 2: "Kapasite 500 birim", 3: "Kapasite 1200 birim"},
    },
    {
        "key": "board", "name": "Görev Tahtası", "short": "GÖREVLER", "icon": "chart",
        "color": (170, 255, 90), "start": 1, "max": 3, "costs": {1: 0, 2: 600, 3: 1600},
        "pos": (1400, 885), "size": (210, 130),
        "desc": "Günlük ve haftalık görevler dev dijital ekranda.",
        "levels": {1: "2 günlük + 1 haftalık", 2: "3 günlük + 2 haftalık", 3: "4 günlük + 3 haftalık"},
    },
    {
        "key": "nova", "name": "AI Kontrol Merkezi (NOVA)", "short": "NOVA", "icon": "nova",
        "color": (62, 230, 255), "start": 1, "max": 3, "costs": {1: 2000, 2: 5000, 3: 10000},
        "pos": (1390, 270), "size": (200, 175),
        "desc": "NOVA'nın evi. Roketini kontrol eder, uyarır, görev önerir, en iyi fırlatma saatini söyler.",
        "levels": {1: "Basit tavsiye", 2: "Detaylı, sayısal tavsiye", 3: "Geleceği tahmin eder (fırtına, en iyi saat)"},
    },
    {
        "key": "control", "name": "Görev Kontrol Merkezi", "short": "KONTROL", "icon": "eye",
        "color": (255, 70, 200), "start": 1, "max": 3, "costs": {1: 0, 2: 1000, 3: 2500},
        "pos": (1440, 570), "size": (240, 165),
        "desc": "Fırlatmadan sonra roket buradan takip edilir. Yakıt, oksijen, elektrik canlı görünür.",
        "levels": {1: "Canlı telemetri", 2: "Erken alarm, simülasyon %15 daha isabetli", 3: "Arıza tahmini, risk -%2"},
    },
    {
        "key": "fuel", "name": "Yakıt Deposu", "short": "YAKIT", "icon": "fuel",
        "color": (255, 120, 60), "start": 1, "max": 3, "costs": {1: 0, 2: 900, 3: 2200},
        "pos": (1020, 930), "size": (270, 140),
        "desc": "Yakıt burada üretilir; marketten almaktan çok daha ucuz.",
        "levels": {1: "Saatte 12 kg, tank 120 kg", 2: "Saatte 28 kg, tank 260 kg", 3: "Saatte 55 kg, tank 520 kg"},
    },
    {
        "key": "hangar", "name": "Montaj Hangarı", "short": "HANGAR", "icon": "wrench",
        "color": (200, 210, 230), "start": 1, "max": 3, "costs": {1: 0, 2: 1500, 3: 4500},
        "pos": (610, 570), "size": (250, 175),
        "desc": "Gövde + Motor + Panel + Anten burada birleştirilir.",
        "levels": {1: "Küçük roket", 2: "Orta roket", 3: "Dev roket"},
    },
    {
        "key": "comms", "name": "İletişim Kulesi", "short": "İLETİŞİM", "icon": "antenna",
        "color": (150, 100, 255), "start": 1, "max": 3, "costs": {1: 0, 2: 1200, 3: 3500},
        "pos": (1700, 360), "size": (160, 190),
        "desc": "Dünya ile roketler arasındaki bağlantı. Kule düşükse uzak gezegenlerle konuşamazsın.",
        "levels": {1: "Menzil: Ay", 2: "Menzil: Mars ve Venüs", 3: "Menzil: Jüpiter"},
    },
    {
        "key": "medical", "name": "Sağlık Merkezi", "short": "SAĞLIK", "icon": "medic",
        "color": (255, 90, 110), "start": 1, "max": 3, "costs": {1: 0, 2: 800, 3: 2000},
        "pos": (330, 450), "size": (180, 135),
        "desc": "Hastalanan astronotlar burada iyileşir.",
        "levels": {1: "İyileşme 4 saat", 2: "İyileşme 2 saat", 3: "İyileşme 1 saat"},
    },
    {
        "key": "rec", "name": "Eğlence ve Dinlenme Alanı", "short": "DİNLENME", "icon": "heart",
        "color": (70, 255, 160), "start": 0, "max": 3, "costs": {1: 600, 2: 1500, 3: 3000},
        "pos": (300, 780), "size": (230, 165),
        "desc": "Park, sinema, yemekhane. Dinlenen astronotun yorgunluğu gider, verimi artar.",
        "levels": {0: "Yok: dinlenme 6 saat", 1: "Dinlenme 3 saat", 2: "Dinlenme 2 saat", 3: "Dinlenme 1 saat"},
    },
]
BUILDING = {b["key"]: b for b in BUILDINGS}

RESEARCH_TIME = {0: 120, 1: 60, 2: 40, 3: 24}         # saniye
RESEARCH_DISCOUNT = {0: 0.0, 1: 0.2, 2: 0.4, 3: 0.6}
ASTRO_CAP = {0: 3, 1: 5, 2: 8, 3: 12}
TRAIN_SPEED = {0: 1.0, 1: 1.0, 2: 1.25, 3: 1.5}
DEPOT_CAP = {0: 100, 1: 200, 2: 500, 3: 1200}
BOARD_SLOTS = {0: (1, 0), 1: (2, 1), 2: (3, 2), 3: (4, 3)}
FUEL_RATE = {0: 4, 1: 12, 2: 28, 3: 55}               # kg / oyun saati
FUEL_CAP = {0: 50, 1: 120, 2: 260, 3: 520}
COMMS_RANGE = {0: 0, 1: 1, 2: 2, 3: 3}
HEAL_HOURS = {0: 8, 1: 4, 2: 2, 3: 1}
REST_HOURS = {0: 6, 1: 3, 2: 2, 3: 1}
ROCKET_SIZE_NAME = {1: "Küçük", 2: "Orta", 3: "Dev"}
PAD_NAME = {1: "Rampa A", 2: "Rampa B", 3: "Rampa C"}
PAD_FEE = {1: 120, 2: 320, 3: 750}                     # fırlatma aracı bedeli
PAD_LIFT = {1: 260, 2: 480, 3: 900}                    # kg, ana roketin kaldırma gücü
PAD_PREP_SEC = {1: 6, 2: 10, 3: 16}                    # rampada hazırlık süresi

# ===========================================================================
# ROKET PARÇALARI
# ===========================================================================
DUR_LABEL = {1: "Düşük", 2: "Orta", 3: "Yüksek", 4: "Çok Yüksek"}
SPEED_LABEL = [(1.3, "Çok Hızlı"), (1.15, "Hızlı"), (0.95, "Orta"), (0.78, "Yavaş"), (0.0, "Çok Yavaş")]


def speed_label(v):
    for th, lab in SPEED_LABEL:
        if v >= th:
            return lab
    return "Çok Yavaş"


HULLS = [
    {"key": "probe", "name": "Küçük Sonda", "capacity": 50, "dur": 1, "speed": 1.35, "seats": 0,
     "tank": 22, "o2": 0, "land": False, "size": 1, "mass": 20, "cost": 150, "cargo": 6, "research": None,
     "desc": "Hafif ve çok hızlı. İnsansız keşif için.", "color": (200, 210, 230)},
    {"key": "orbiter", "name": "Orbiter Gövdesi", "capacity": 120, "dur": 2, "speed": 1.2, "seats": 0,
     "tank": 48, "o2": 0, "land": False, "size": 1, "mass": 45, "cost": 320, "cargo": 12, "research": None,
     "desc": "Yörünge görevleri için dengeli insansız gövde.", "color": (180, 200, 240)},
    {"key": "capsule", "name": "Kapsül Gövdesi", "capacity": 100, "dur": 3, "speed": 1.0, "seats": 3,
     "tank": 40, "o2": 110, "land": True, "size": 1, "mass": 60, "cost": 450, "cargo": 18, "research": None,
     "desc": "3 kişilik sağlam kapsül. Ay'a iniş yapabilir.", "color": (230, 230, 240)},
    {"key": "lander", "name": "İniş Modülü", "capacity": 150, "dur": 3, "speed": 0.85, "seats": 3,
     "tank": 58, "o2": 140, "land": True, "size": 2, "mass": 85, "cost": 700, "cargo": 45, "research": "lander",
     "desc": "Ayaklı iniş modülü. Yüzeyden bol maden getirir.", "color": (220, 200, 120)},
    {"key": "station", "name": "İstasyon Modülü", "capacity": 300, "dur": 2, "speed": 0.7, "seats": 3,
     "tank": 95, "o2": 260, "land": True, "size": 3, "mass": 150, "cost": 1200, "cargo": 70, "research": "station",
     "desc": "Koloni kurulumu için dev yaşam modülü.", "color": (200, 230, 255)},
    {"key": "cargo", "name": "Kargo Gövdesi", "capacity": 400, "dur": 2, "speed": 0.85, "seats": 2,
     "tank": 85, "o2": 170, "land": True, "size": 3, "mass": 170, "cost": 1000, "cargo": 160, "research": "cargo",
     "desc": "Devasa ambar. Madencilik ve koloni ikmali için.", "color": (240, 190, 120)},
    {"key": "armored", "name": "Ağır Zırhlı Gövde", "capacity": 250, "dur": 4, "speed": 1.0, "seats": 3,
     "tank": 65, "o2": 190, "land": True, "size": 2, "mass": 120, "cost": 1600, "cargo": 55, "research": "armor",
     "desc": "Çok yüksek dayanıklılık. Isı kalkanı dahil.", "color": (150, 160, 180), "heat_shield": True},
]

ENGINES = [
    {"key": "solid", "name": "Katı Yakıtlı", "lift": 1.35, "burn": 1.55, "speed": 1.0, "draw": 0.15,
     "mass": 30, "cost": 200, "research": None, "flame": "fire", "shake": 1.0,
     "desc": "Güçlü kalkış, çok yakar. Turuncu dev alev, ekran sarsılır."},
    {"key": "liquid", "name": "Sıvı Yakıtlı", "lift": 1.15, "burn": 1.0, "speed": 1.05, "draw": 0.25,
     "mass": 25, "cost": 300, "research": None, "flame": "blue", "shake": 0.5,
     "desc": "Dengeli. Mavi-beyaz alev."},
    {"key": "ion", "name": "İyon Motoru", "lift": 0.8, "burn": 0.15, "speed": 0.75, "speed_max": 1.7, "draw": 2.0,
     "mass": 12, "cost": 800, "research": "ion", "flame": "ion", "shake": 0.1,
     "desc": "Kalkışta zayıf, uzayda hızlanır, neredeyse yakıt yakmaz. Bol elektrik ister."},
    {"key": "nuclear", "name": "Nükleer Termal", "lift": 1.1, "burn": 0.45, "speed": 1.45, "draw": 0.5,
     "mass": 45, "cost": 1400, "research": "fission", "flame": "purple", "shake": 0.7, "radiation": True,
     "desc": "Çok hızlı, az yakar. Mor alev. Radyasyon verir: Doktor lazım."},
    {"key": "sail", "name": "Güneş Yelkeni", "lift": 0.75, "burn": 0.0, "speed": 1.6, "draw": 0.1,
     "mass": 15, "cost": 900, "research": "sail", "flame": "sail", "shake": 0.0, "solar": True,
     "desc": "0 yakıt. Güneş'e yakınken hızlı, uzakta yavaş. Dev gümüş yelken."},
    {"key": "plasma", "name": "Plazma Motoru", "lift": 1.2, "burn": 0.3, "speed": 1.9, "draw": 1.6,
     "mass": 35, "cost": 2500, "research": "plasma", "flame": "plasma", "shake": 0.6,
     "desc": "En güçlüsü. Mor-mavi plazma topu, elektrik kıvılcımları."},
]

POWERS = [
    {"key": "battery", "name": "Küçük Batarya", "cap": 12, "gen": 0.0, "kind": "battery", "mass": 5, "cost": 80,
     "research": None, "desc": "Yaklaşık 10 saniye gider. Şarj olmaz."},
    {"key": "solar", "name": "Güneş Paneli", "cap": 10, "gen": 2.1, "kind": "solar", "mass": 8, "cost": 200,
     "research": None, "desc": "Güneş varken sonsuz, karanlıkta 0. 2 kanat, mavi hücreli."},
    {"key": "big_solar", "name": "Büyük Güneş Paneli", "cap": 14, "gen": 4.4, "kind": "solar", "mass": 16, "cost": 600,
     "research": "bigsolar", "desc": "4 kanat, devasa, altın çerçeve."},
    {"key": "rtg", "name": "RTG Nükleer Pil", "cap": 12, "gen": 2.8, "kind": "rtg", "mass": 20, "cost": 1200,
     "research": "rtg", "desc": "Her zaman sabit; karanlıkta da çalışır."},
    {"key": "fuelcell", "name": "Yakıt Hücresi", "cap": 12, "gen": 3.2, "kind": "fuelcell", "mass": 12, "cost": 700,
     "research": "fuelchem", "fuel_use": 0.07, "desc": "Yakıt varsa elektrik üretir, su buharı çıkarır."},
]

ANTENNAS = [
    {"key": "low", "name": "Düşük Kazançlı Anten", "range": 1, "mass": 2, "draw": 0.1, "cost": 50, "research": None,
     "desc": "Ay'a kadar. Küçük çubuk."},
    {"key": "high", "name": "Yüksek Kazançlı Anten", "range": 2, "mass": 6, "draw": 0.25, "cost": 250, "research": None,
     "desc": "Mars'a kadar. Büyük çanak, Dünya'yı takip eder."},
    {"key": "laser", "name": "Lazer İletişim", "range": 3, "mass": 8, "draw": 0.35, "cost": 900, "research": "laser",
     "desc": "Jüpiter'e kadar. İnce kırmızı lazer."},
    {"key": "dsn", "name": "Derin Uzay Ağı", "range": 4, "mass": 14, "draw": 0.5, "cost": 2000, "research": "dsn",
     "desc": "Her yere. 3 anten, mavi halka."},
]
RANGE_NAME = {0: "Yok", 1: "Ay", 2: "Mars", 3: "Jüpiter", 4: "Her yer"}

PAYLOADS = [
    {"key": "camera", "name": "Kamera Sistemi", "mass": 4, "draw": 0.1, "cost": 120, "icon": "camera",
     "desc": "Fotoğraf çeker: her fotoğraf +20 Puan. Flaş patlar."},
    {"key": "spectro", "name": "Spektrometre", "mass": 6, "draw": 0.2, "cost": 250, "icon": "prism",
     "desc": "Asteroit içini gösterir; madenli asteroiti bulur. Gökkuşağı ışık."},
    {"key": "magneto", "name": "Manyetometre", "mass": 3, "draw": 0.1, "cost": 200, "icon": "magnet",
     "desc": "Güneş Fırtınası'nı önceden haber verir. İbre döner."},
    {"key": "biolab", "name": "Biyoloji Laboratuvarı", "mass": 10, "draw": 0.3, "cost": 350, "icon": "flask",
     "desc": "Astronot sağlığını ölçer. Cam fanusta bitki solar/canlanır."},
]
MAX_PAYLOADS = 3

PARTS = {"hull": HULLS, "engine": ENGINES, "power": POWERS, "antenna": ANTENNAS, "payload": PAYLOADS}
PART = {slot: {p["key"]: p for p in lst} for slot, lst in PARTS.items()}
BASE_DRAW = 1.0          # sistemlerin temel elektrik tüketimi / sn
CREW_MASS = 0            # koltuklar gövdeye dahil
LASER_COST_E = 1.4
PHOTO_COST_E = 0.8

# ===========================================================================
# ARAŞTIRMA
# ===========================================================================
# req: ("visit", gezegen, kez)
RESEARCH = [
    {"key": "fuelchem", "name": "Yakıt Kimyası", "rp": 150, "money": 300, "req": None,
     "effect": "Yakıt tüketimi -%10, Yakıt Hücresi açılır", "icon": "fuel"},
    {"key": "bigsolar", "name": "Büyük Güneş Paneli", "rp": 250, "money": 600, "req": None,
     "effect": "4 kanatlı Büyük Güneş Paneli açılır", "icon": "sun"},
    {"key": "aero", "name": "Gelişmiş Aerodinamik", "rp": 200, "money": 500, "req": ("visit", "moon", 1),
     "effect": "Kaldırma +%10, risk -%3", "icon": "rocket"},
    {"key": "lander", "name": "İniş Modülü Gövdesi", "rp": 300, "money": 700, "req": ("visit", "moon", 1),
     "effect": "İniş Modülü gövdesi açılır", "icon": "planet"},
    {"key": "sail", "name": "Güneş Yelkeni", "rp": 400, "money": 900, "req": ("visit", "moon", 2),
     "effect": "Güneş Yelkeni motoru açılır", "icon": "sun"},
    {"key": "ion", "name": "İyon İtki", "rp": 350, "money": 800, "req": ("visit", "mars", 1),
     "effect": "İyon Motoru açılır", "icon": "bolt"},
    {"key": "fission", "name": "Nükleer Fizyon", "rp": 500, "money": 1000, "req": ("visit", "mars", 1),
     "effect": "Nükleer Termal motor açılır", "icon": "warning"},
    {"key": "rtg", "name": "RTG Nükleer Pil", "rp": 600, "money": 1200, "req": ("visit", "mars", 1),
     "effect": "RTG Nükleer Pil açılır", "icon": "bolt"},
    {"key": "laser", "name": "Lazer İletişim", "rp": 450, "money": 1000, "req": ("visit", "mars", 1),
     "effect": "Lazer anten açılır (Jüpiter menzili)", "icon": "antenna"},
    {"key": "station", "name": "İstasyon Modülü Gövdesi", "rp": 700, "money": 1500, "req": ("visit", "mars", 1),
     "effect": "İstasyon Modülü gövdesi açılır", "icon": "home"},
    {"key": "cargo", "name": "Kargo Gövdesi", "rp": 800, "money": 1800, "req": ("visit", "mars", 1),
     "effect": "Kargo Gövdesi açılır", "icon": "box"},
    {"key": "heatshield", "name": "Sıcaklık Kalkanı", "rp": 600, "money": 1500, "req": ("visit", "mars", 1),
     "effect": "Tüm gövdelere ısı kalkanı: Venüs'e iniş", "icon": "storm"},
    {"key": "plasma", "name": "Plazma İtki", "rp": 1000, "money": 3000, "req": ("visit", "jupiter", 1),
     "effect": "Plazma Motoru açılır", "icon": "star"},
    {"key": "dsn", "name": "Derin Uzay Ağı", "rp": 900, "money": 2500, "req": ("visit", "jupiter", 1),
     "effect": "Derin Uzay Ağı anteni açılır", "icon": "satellite"},
    {"key": "armor", "name": "Ağır Zırhlı Gövde", "rp": 1200, "money": 4000, "req": ("visit", "jupiter", 1),
     "effect": "Ağır Zırhlı Gövde açılır", "icon": "box"},
]
RESEARCH_BY_KEY = {r["key"]: r for r in RESEARCH}

# ===========================================================================
# ASTRONOTLAR
# ===========================================================================
CREW_TYPES = [
    {"key": "pilot", "name": "Pilot", "color_name": "Mavi", "hire": 400, "salary": 0,
     "desc": "Pilotsuz roket yavaş gider, kaçamaz. Pilot varsa risk %20 düşer."},
    {"key": "engineer", "name": "Mühendis", "color_name": "Turuncu", "hire": 450, "salary": 0,
     "desc": "Bozulan parçayı tamir eder. Tamir 5 saniye sürer."},
    {"key": "scientist", "name": "Bilim İnsanı", "color_name": "Yeşil", "hire": 400, "salary": 0,
     "desc": "Yolculuk sonunda +50 Puan."},
    {"key": "doctor", "name": "Doktor", "color_name": "Beyaz", "hire": 500, "salary": 0,
     "desc": "Hastalanmayı iyileştirir. Nükleer motor kullanırsan lazım."},
    {"key": "miner", "name": "Madenci", "color_name": "Kahverengi", "hire": 350, "salary": 0,
     "desc": "Asteroit kırarsa 2 kat maden alır."},
]
CREW_TYPE = {c["key"]: c for c in CREW_TYPES}
TRAIN_COST = 300
TRAIN_SEC = 45
MAX_RANK = 3

FIRST_NAMES = ["Deniz", "Ece", "Kaan", "Mira", "Arda", "Zeynep", "Efe", "Lara", "Toprak", "Nil",
               "Alp", "Defne", "Yağız", "Elif", "Bora", "Ada", "Kerem", "Sena", "Emir", "Asya",
               "Leo", "Yuki", "Aria", "Ravi", "Noor", "Ivan", "Sofia", "Kai", "Amara", "Luca"]
LAST_NAMES = ["Yıldız", "Kaya", "Aydın", "Demir", "Şahin", "Çelik", "Arslan", "Koç", "Kurt", "Öztürk",
              "Tanaka", "Okafor", "Novak", "Rossi", "Patel", "Kim", "Silva", "Berg", "Moreau", "Haddad"]

# ===========================================================================
# GEZEGENLER
# ===========================================================================
# dist: yolculuk mini-oyunu süresi (sn, hız 1.0'da)
# sun : güneş yoğunluğu (panel ve yelken)
# zones: (başlangıç, bitiş, tür)
PLANETS = [
    {
        "key": "moon", "name": "Ay", "distance": "Çok yakın", "difficulty": "Kolay", "diff": 1,
        "mineral": "moon_rock", "special": "Başlangıç kolonisi", "dist": 42, "sun": 1.0, "range": 1,
        "risk": 0.06, "colony_cost": 800, "unlock": None, "gravity": "1,62 m/s² (0,17 g)",
        "color": (200, 200, 210), "color2": (120, 120, 135), "glow": (180, 200, 255),
        "zones": [(0.0, 0.18, "debris"), (0.35, 0.6, "asteroids"), (0.6, 0.72, "stardust")],
        "desc": "Dünya'nın uydusu. Ay Taşı bakımından zengin. İlk koloni için ideal.",
    },
    {
        "key": "mars", "name": "Mars", "distance": "Orta", "difficulty": "Orta", "diff": 2,
        "mineral": "red_ore", "special": "İlk gerçek koloni", "dist": 72, "sun": 0.62, "range": 2,
        "risk": 0.13, "colony_cost": 2200, "unlock": ("visit", "moon", 1), "gravity": "3,71 m/s² (0,38 g)",
        "color": (220, 100, 60), "color2": (130, 50, 30), "glow": (255, 140, 90),
        "zones": [(0.0, 0.12, "debris"), (0.25, 0.45, "asteroids"), (0.45, 0.55, "dark"),
                  (0.6, 0.75, "stardust"), (0.75, 0.92, "asteroids")],
        "desc": "Kızıl gezegen. Kızıl Maden ve ilk gerçek koloni.",
    },
    {
        "key": "venus", "name": "Venüs", "distance": "Orta", "difficulty": "Zor - Sıcak", "diff": 3,
        "mineral": "sulfur", "special": "Sıcaklık kalkanı lazım", "dist": 66, "sun": 1.9, "range": 2,
        "risk": 0.18, "colony_cost": 3200, "unlock": ("visit", "mars", 1), "gravity": "8,87 m/s² (0,90 g)", "hot": True,
        "color": (240, 200, 110), "color2": (170, 120, 50), "glow": (255, 220, 140),
        "zones": [(0.0, 0.12, "debris"), (0.2, 0.4, "stardust"), (0.45, 0.7, "heat"), (0.7, 0.9, "asteroids")],
        "desc": "Kavurucu sıcaklık ve asit bulutları. Sülfür çıkarılır.",
    },
    {
        "key": "jupiter", "name": "Jüpiter", "distance": "Çok uzak", "difficulty": "Çok Zor", "diff": 4,
        "mineral": "gas", "special": "Final hedefi", "dist": 115, "sun": 0.16, "range": 3,
        "risk": 0.24, "colony_cost": 6000, "unlock": ("visit", "mars", 2), "gravity": "24,79 m/s² (2,53 g)",
        "color": (220, 170, 120), "color2": (150, 100, 70), "glow": (255, 190, 140), "bands": True,
        "zones": [(0.0, 0.08, "debris"), (0.15, 0.4, "belt"), (0.4, 0.5, "dark"), (0.5, 0.62, "stardust"),
                  (0.62, 0.8, "belt"), (0.85, 1.0, "radiation")],
        "desc": "Gaz devi. Gaz Madeni çok değerli. Burada dev koloni kurmak nihai hedef.",
    },
]
PLANET = {p["key"]: p for p in PLANETS}

# ===========================================================================
# NASA VERİLERİ — NASA NSSDC Gezegen Bilgi Tablosu (nssdc.gsfc.nasa.gov/planetary/factsheet)
# Jüpiter yerçekimi: NASA Jüpiter bilgi tablosu (1 bar, ekvator). Oyun bu değerleri kullanır ve gösterir.
# ===========================================================================
NASA = {
    "earth":   {"name": "Dünya", "g": 9.80, "rot_h": 23.9, "diam_km": 12756, "day_h": 24.0, "temp_c": 15, "bar": 1.0,
                "sun_mkm": 149.6, "escape": 11.2, "moons": 1, "year_d": 365.2},
    "moon":    {"name": "Ay", "g": 1.62, "rot_h": 655.7, "diam_km": 3475, "day_h": 708.7, "temp_c": -20, "bar": 0.0,
                "earth_km": 384400, "escape": 2.4, "moons": 0, "year_d": 27.3},
    "mars":    {"name": "Mars", "g": 3.71, "rot_h": 24.6, "diam_km": 6792, "day_h": 24.7, "temp_c": -65, "bar": 0.01,
                "sun_mkm": 228.0, "escape": 5.0, "moons": 2, "year_d": 687.0},
    "venus":   {"name": "Venüs", "g": 8.87, "rot_h": -5832.5, "diam_km": 12104, "day_h": 2802.0, "temp_c": 464, "bar": 92.0,
                "sun_mkm": 108.2, "escape": 10.4, "moons": 0, "year_d": 224.7},
    "jupiter": {"name": "Jüpiter", "g": 24.79, "rot_h": 9.9, "diam_km": 142984, "day_h": 9.9, "temp_c": -110, "bar": None,
                "sun_mkm": 778.5, "escape": 59.5, "moons": 95, "year_d": 4331},
}
NASA_SOURCE = "NASA NSSDC Gezegen Bilgi Tablosu"

# yükleme ekranlarında dönen bilgiler: (metin, kaynak) — hepsi NASA yayınlarından
NASA_FACTS = [
    ("Ay'da yerçekimi 1,62 m/s²: Dünya'daki ağırlığının yalnızca %17'sini hissedersin.", "NASA NSSDC Ay Bilgi Tablosu"),
    ("Venüs'te yüzey basıncı 92 bar, ortalama sıcaklık 464 °C: Merkür'den bile sıcak.", "NASA NSSDC Gezegen Bilgi Tablosu"),
    ("Venüs'te bir gün (2.802 saat) bir yıldan (224,7 gün) uzundur ve gezegen ters yönde döner.", "NASA NSSDC"),
    ("Mars'ın yüzey basıncı Dünya'nınkinin yaklaşık %1'i; bir Mars günü 24,7 saat sürer.", "NASA NSSDC Mars Bilgi Tablosu"),
    ("Olympus Mons yaklaşık 22 km yüksekliğiyle Güneş Sistemi'nin en yüksek yanardağıdır.", "NASA Science · Mars"),
    ("Jüpiter'in kütlesi öteki bütün gezegenlerin toplamının iki katından fazladır.", "NASA Science · Jüpiter"),
    ("Jüpiter'de bir gün yalnızca 9,9 saat sürer: Güneş Sistemi'nin en hızlı dönen gezegeni.", "NASA NSSDC"),
    ("Ay, Dünya'dan ortalama 384.400 km uzaktadır; ışık bu yolu 1,3 saniyede alır.", "NASA NSSDC Ay Bilgi Tablosu"),
    ("Apollo 11 Ay modülü Eagle 20 Temmuz 1969'da Huzur Denizi'ne indi.", "NASA History Office"),
    ("Dünya'dan kaçış hızı 11,2 km/s, Ay'dan 2,4 km/s, Jüpiter'den 59,5 km/s.", "NASA NSSDC Gezegen Bilgi Tablosu"),
    ("Bu oyundaki Dünya NASA Blue Marble, Ay LRO, Mars Viking, Jüpiter Cassini görüntüleriyle çizilir.", "NASA SVS · NASA Mars Trek · NASA/JPL"),
    ("Perseverance gezgini 18 Şubat 2021'de Mars'taki Jezero Krateri'ne indi.", "NASA/JPL"),
    ("DART aracı 2022'de Dimorphos'a çarparak yörünge periyodunu yaklaşık 33 dakika kısalttı.", "NASA / JHU APL"),
    ("Uluslararası Uzay İstasyonu Dünya'nın çevresini yaklaşık 90 dakikada bir dolaşır.", "NASA ISS"),
]
PLANET_ORDER = ["moon", "mars", "venus", "jupiter"]
TO = {"moon": "Ay'a", "mars": "Mars'a", "venus": "Venüs'e", "jupiter": "Jüpiter'e", "earth": "Dünya'ya"}
AT = {"moon": "Ay'da", "mars": "Mars'ta", "venus": "Venüs'te", "jupiter": "Jüpiter'de", "earth": "Dünya'da"}

# ===========================================================================
# MADENLER / EŞYALAR
# ===========================================================================
MINERALS = [
    {"key": "moon_rock", "name": "Ay Taşı", "price": 10, "color": (200, 200, 215)},
    {"key": "red_ore", "name": "Kızıl Maden", "price": 50, "color": (230, 90, 60)},
    {"key": "sulfur", "name": "Sülfür", "price": 80, "color": (240, 220, 80)},
    {"key": "gas", "name": "Gaz Madeni", "price": 200, "color": (255, 170, 110)},
    {"key": "astro_ore", "name": "Asteroit Cevheri", "price": 35, "color": (255, 200, 90)},
]
MINERAL = {m["key"]: m for m in MINERALS}
ITEMS = {
    "stardust": {"name": "Yıldız Tozu", "color": (150, 220, 255)},
    "repair_kit": {"name": "Tamir Kiti", "color": (255, 160, 60)},
}

# ===========================================================================
# KOLONİ
# ===========================================================================
COLONY_BUILDINGS = [
    {"key": "house", "name": "Ev", "cost": 300, "level_req": 1, "icon": "home",
     "desc": "Nüfus kapasitesi +6."},
    {"key": "mine", "name": "Maden", "cost": 400, "level_req": 1, "icon": "pickaxe",
     "desc": "Saatte maden üretir."},
    {"key": "hut", "name": "Araştırma Kulübesi", "cost": 350, "level_req": 1, "icon": "flask",
     "desc": "Saatte Araştırma Puanı üretir."},
    {"key": "gym", "name": "Spor Salonu", "cost": 450, "level_req": 1, "icon": "heart",
     "desc": "Mutluluk +8 (kalıcı)."},
    {"key": "hospital", "name": "Hastane", "cost": 700, "level_req": 2, "icon": "medic",
     "desc": "Mutluluk +6, nüfus kaybını önler."},
    {"key": "school", "name": "Okul", "cost": 650, "level_req": 2, "icon": "star",
     "desc": "Araştırma üretimi +%40."},
    {"key": "park", "name": "Park", "cost": 500, "level_req": 3, "icon": "sun",
     "desc": "Mutluluk +10."},
]
COLONY_BUILDING = {b["key"]: b for b in COLONY_BUILDINGS}
COLONY_ACTIONS = [
    {"key": "food", "name": "Yemek Gönder", "cost": 150, "happy": 12, "icon": "box",
     "desc": "Taze yemek kargosu: mutluluk +12"},
    {"key": "movie", "name": "Film Gecesi", "cost": 80, "happy": 7, "icon": "camera",
     "desc": "Kolonide film gecesi: mutluluk +7"},
]
COLONY_LEVEL_POP = {1: 0, 2: 14, 3: 30, 4: 60}
COLONY_PLANET_MULT = {"moon": 1.0, "mars": 1.25, "venus": 1.5, "jupiter": 2.2}

# ===========================================================================
# GÖREVLER (günlük / haftalık)
# ===========================================================================
# event anahtarları: launch, photo, asteroid, stardust, rescue, visit, land, colony, sell, research, flawless
DAILY_TEMPLATES = [
    {"id": "d_moon_photo", "text": "Ay'a git, 3 fotoğraf çek", "event": "photo", "planet": "moon", "n": 3,
     "money": 100, "rp": 20},
    {"id": "d_launch2", "text": "2 fırlatma yap", "event": "launch", "n": 2, "money": 120, "rp": 15},
    {"id": "d_ast5", "text": "5 asteroit kır", "event": "asteroid", "n": 5, "money": 110, "rp": 20},
    {"id": "d_dust8", "text": "8 Yıldız Tozu topla", "event": "stardust", "n": 8, "money": 90, "rp": 25},
    {"id": "d_rescue", "text": "1 uydu kurtar", "event": "rescue", "n": 1, "money": 150, "rp": 30},
    {"id": "d_sell", "text": "Maden satıp 300 Para kazan", "event": "sell", "n": 300, "money": 100, "rp": 10},
    {"id": "d_moon_land", "text": "Ay'a iniş yap", "event": "land", "planet": "moon", "n": 1, "money": 140, "rp": 20},
    {"id": "d_mars_visit", "text": "Mars'a ulaş", "event": "visit", "planet": "mars", "n": 1, "money": 220, "rp": 40,
     "req": ("visit", "moon", 1)},
    {"id": "d_flawless", "text": "Hasar almadan görev tamamla", "event": "flawless", "n": 1, "money": 160, "rp": 25},
    {"id": "d_photo5", "text": "Herhangi bir yerde 5 fotoğraf çek", "event": "photo", "n": 5, "money": 120, "rp": 25},
]
WEEKLY_TEMPLATES = [
    {"id": "w_mars_colony", "text": "Mars'ta koloni kur", "event": "colony", "planet": "mars", "n": 1,
     "money": 1000, "rp": 100, "req": ("visit", "moon", 1)},
    {"id": "w_ast40", "text": "40 asteroit kır", "event": "asteroid", "n": 40, "money": 700, "rp": 80},
    {"id": "w_launch8", "text": "8 fırlatma yap", "event": "launch", "n": 8, "money": 800, "rp": 90},
    {"id": "w_dust50", "text": "50 Yıldız Tozu topla", "event": "stardust", "n": 50, "money": 650, "rp": 120},
    {"id": "w_research3", "text": "3 araştırma tamamla", "event": "research", "n": 3, "money": 900, "rp": 60},
    {"id": "w_sell2000", "text": "Maden satıp 2000 Para kazan", "event": "sell", "n": 2000, "money": 800, "rp": 60},
    {"id": "w_moon_colony", "text": "Ay'da koloni kur", "event": "colony", "planet": "moon", "n": 1,
     "money": 600, "rp": 60},
    {"id": "w_jupiter", "text": "Jüpiter'e ulaş", "event": "visit", "planet": "jupiter", "n": 1,
     "money": 2500, "rp": 200, "req": ("visit", "mars", 1)},
]

# ===========================================================================
# BAŞARIMLAR
# ===========================================================================
ACHIEVEMENTS = [
    {"key": "first_launch", "name": "İlk Fırlatma", "desc": "İlk roketini fırlat.", "money": 200, "icon": "rocket"},
    {"key": "moon_landing", "name": "Ay'a Ayak Bas", "desc": "Ay'a ilk iniş.", "money": 400, "icon": "flag"},
    {"key": "asteroid_100", "name": "100 Asteroit Kır", "desc": "Toplam 100 asteroit kır.", "money": 800, "icon": "pickaxe"},
    {"key": "mars_arrival", "name": "Kızıl Ufuk", "desc": "Mars'a ilk varış.", "money": 600, "icon": "planet"},
    {"key": "mars_colony", "name": "Mars Kolonisi", "desc": "Mars'ta koloni kur.", "money": 1500, "icon": "home"},
    {"key": "venus_land", "name": "Cehennemden Dönüş", "desc": "Venüs'e iniş yap.", "money": 1200, "icon": "storm"},
    {"key": "jupiter_arrival", "name": "Jüpiter'e İlk Varış", "desc": "Jüpiter'e ulaş.", "money": 2500, "icon": "star"},
    {"key": "jupiter_colony", "name": "Dev Koloni", "desc": "Jüpiter kolonisini Seviye 3 yap.", "money": 5000, "icon": "trophy"},
    {"key": "nova3", "name": "Kehanet Makinesi", "desc": "NOVA'yı Seviye 3'e yükselt.", "money": 1000, "icon": "nova"},
    {"key": "flawless", "name": "Kusursuz Uçuş", "desc": "Hiç hasar almadan görev tamamla.", "money": 300, "icon": "check"},
    {"key": "rescue_10", "name": "Kurtarıcı", "desc": "10 uydu kurtar.", "money": 700, "icon": "satellite"},
    {"key": "dust_500", "name": "Yıldız Tozu Avcısı", "desc": "500 Yıldız Tozu topla.", "money": 900, "icon": "dust"},
    {"key": "rich", "name": "Uzay Baronu", "desc": "Kasada 20.000 Para biriktir.", "money": 0, "icon": "money"},
    {"key": "all_research", "name": "Bilgi Çağı", "desc": "Tüm araştırmaları tamamla.", "money": 3000, "icon": "flask"},
    {"key": "full_crew", "name": "Tam Kadro", "desc": "5 tipin hepsinden astronotun olsun.", "money": 400, "icon": "astro"},
    {"key": "max_base", "name": "Dev Üs", "desc": "Tüm binaları Seviye 3 yap.", "money": 4000, "icon": "home"},
    {"key": "photographer", "name": "Kozmik Fotoğrafçı", "desc": "Toplam 50 fotoğraf çek.", "money": 500, "icon": "camera"},
    {"key": "four_colonies", "name": "Güneş Sistemi İmparatorluğu", "desc": "4 gezegende koloni kur.", "money": 6000, "icon": "flag"},
]
ACHIEVEMENT = {a["key"]: a for a in ACHIEVEMENTS}

# ===========================================================================
# RASTGELE OLAYLAR (ajans kararları)
# ===========================================================================
EVENTS = [
    {"id": "sponsor", "title": "Sponsorluk Teklifi",
     "text": "Bir içecek markası, rokete logosunu basmak için para teklif ediyor.",
     "choices": [{"label": "Kabul et (+600 Para, -3 İtibar)", "effects": {"money": 600, "rep": -3}},
                 {"label": "Reddet (+2 İtibar)", "effects": {"rep": 2}}]},
    {"id": "university", "title": "Üniversite Ortaklığı",
     "text": "Bir üniversite, araştırma verilerini paylaşmak karşılığında bilim insanı göndermek istiyor.",
     "choices": [{"label": "Ortaklık kur (+80 Puan)", "effects": {"rp": 80}},
                 {"label": "Veri sat (+300 Para)", "effects": {"money": 300}}]},
    {"id": "strike", "title": "Tedarikçi Grevi",
     "text": "Yakıt tedarikçisi grevde. Depo üretimi aksayabilir.",
     "choices": [{"label": "Ek ücret öde (-250 Para)", "effects": {"money": -250}},
                 {"label": "Bekle (yakıt stoku -40 kg)", "effects": {"fuel": -40}}]},
    {"id": "media", "title": "Canlı Yayın Daveti",
     "text": "Ulusal kanal, ajansın başkanını canlı yayına çağırıyor.",
     "choices": [{"label": "Katıl (+5 İtibar, +120 XP)", "effects": {"rep": 5, "xp": 120}},
                 {"label": "Teşekkür et ve geç", "effects": {}}]},
    {"id": "meteor_shower", "title": "Meteor Yağmuru",
     "text": "Gökyüzünde muhteşem bir meteor yağmuru var. Gözlem yapmak ister misin?",
     "choices": [{"label": "Gözlem yap (+40 Puan, +5 Yıldız Tozu)", "effects": {"rp": 40, "stardust": 5}},
                 {"label": "Halka açık etkinlik (+200 Para, +2 İtibar)", "effects": {"money": 200, "rep": 2}}]},
    {"id": "investor", "title": "Melek Yatırımcı",
     "text": "Bir yatırımcı ajansa fon vermek istiyor ama kâr payı bekliyor.",
     "choices": [{"label": "Fonu al (+1200 Para, günlük gelir -30)", "effects": {"money": 1200, "income": -30}},
                 {"label": "Reddet (+3 İtibar)", "effects": {"rep": 3}}]},
    {"id": "patent", "title": "Patent Başvurusu",
     "text": "Mühendislerin yeni bir yakıt valfi tasarladı. Patent alınsın mı?",
     "choices": [{"label": "Patent al (-200 Para, günlük +40 Para)", "effects": {"money": -200, "income": 40}},
                 {"label": "Açık kaynak yap (+6 İtibar)", "effects": {"rep": 6}}]},
    {"id": "flu", "title": "Grip Salgını",
     "text": "Üste grip salgını var. Astronotlar risk altında.",
     "choices": [{"label": "Aşı kampanyası (-180 Para)", "effects": {"money": -180}},
                 {"label": "Riski göze al (1 astronot hastalanır)", "effects": {"sick": 1}}]},
    {"id": "school_visit", "title": "Okul Gezisi",
     "text": "Bir ilkokul üssü ziyaret etmek istiyor.",
     "choices": [{"label": "Kapıları aç (+4 İtibar, +60 XP)", "effects": {"rep": 4, "xp": 60}},
                 {"label": "Güvenlik gereği reddet", "effects": {}}]},
    {"id": "supply", "title": "Ucuz Tamir Kiti",
     "text": "Bir tedarikçi stok fazlası tamir kitlerini indirimli satıyor.",
     "choices": [{"label": "3 kit al (-250 Para)", "effects": {"money": -250, "repair_kit": 3}},
                 {"label": "Gerek yok", "effects": {}}]},
]

# ===========================================================================
# DİPLOMASİ (eski koddan korunan sistem)
# ===========================================================================
PARTNERS = [
    {"key": "NASA", "name": "NASA", "relation": 40, "cost": 1500, "perk": "Görev Puanı +%10",
     "color": (70, 140, 255)},
    {"key": "ESA", "name": "ESA", "relation": 45, "cost": 1200, "perk": "Araştırma süresi -%10",
     "color": (62, 230, 255)},
    {"key": "JAXA", "name": "JAXA", "relation": 35, "cost": 1300, "perk": "Tamir süresi -%30",
     "color": (255, 70, 120)},
    {"key": "ISRO", "name": "ISRO", "relation": 50, "cost": 1000, "perk": "Fırlatma bedeli -%10",
     "color": (255, 160, 60)},
    {"key": "TUA", "name": "TUA", "relation": 55, "cost": 900, "perk": "Görev Parası +%10",
     "color": (255, 64, 84)},
]
PARTNER = {p["key"]: p for p in PARTNERS}
RELATION_COST = 200
PACT_MIN = 70

# ===========================================================================
# ASTRONOT KIYAFETİ (başlangıçta seçilir, Araştırma Merkezi'nde geliştirilir)
# ===========================================================================
SUITS = [
    {"key": "armored", "name": "Zırhlı Kıyafet", "dur": 4, "mob": 1, "color": (150, 160, 180),
     "desc": "Dayanıklı ama hantal: radyasyona ve çarpmalara karşı güçlü koruma sağlar; tamir ve yüzey çalışması yavaştır."},
    {"key": "agile", "name": "Çevik Kıyafet", "dur": 1, "mob": 4, "color": (70, 255, 160),
     "desc": "Hafif ve esnek: tamir ve maden toplama hızlıdır; radyasyona ve çarpmalara karşı zayıftır."},
    {"key": "balanced", "name": "Dengeli Kıyafet", "dur": 2, "mob": 2, "color": (62, 230, 255),
     "desc": "Ne çok ağır ne çok hafif: belirgin bir zayıflığı yoktur, belirgin bir üstünlüğü de."},
]
SUIT = {x["key"]: x for x in SUITS}
SUIT_TRACKS = [
    {"key": "dur", "name": "Zırh Katmanı", "icon": "box", "max": 4,
     "desc": "Dayanıklılık +1: hastalanma ve yaralanma riski azalır, zorlu yüzeylere iniş güvenli olur."},
    {"key": "mob", "name": "Eklem Mekaniği", "icon": "gear", "max": 4,
     "desc": "Hareket kabiliyeti +1: tamir hızlanır, yüzeyden daha çok maden toplanır."},
    {"key": "life", "name": "Yaşam Destek", "icon": "o2", "max": 4,
     "desc": "Oksijen süresi +%12: uzun yolculuklarda nefes payı artar."},
]
SUIT_TRACK = {x["key"]: x for x in SUIT_TRACKS}

# Ajans odağı (başlangıçta seçilir)
FOCUS = [
    {"key": "science", "name": "Bilim Odaklı", "icon": "flask", "color": (62, 230, 255),
     "desc": "Görevlerden kazanılan Araştırma Puanı +%20."},
    {"key": "commerce", "name": "Ticaret Odaklı", "icon": "money", "color": (255, 206, 84),
     "desc": "Maden satış geliri +%15."},
    {"key": "explore", "name": "Keşif Odaklı", "icon": "rocket", "color": (255, 140, 50),
     "desc": "Rampa (fırlatma) bedeli −%15."},
]
FOCUS_BY_KEY = {x["key"]: x for x in FOCUS}

# Seviye rozetleri
BADGES = [
    (1, "Çaylak Ajans"), (3, "Yörünge Kaşifi"), (6, "Ay Öncüsü"), (10, "Gezegenler Arası"),
    (15, "Derin Uzay Komutanlığı"), (22, "Güneş Sistemi Lideri"), (30, "Yıldızların Efendisi"),
]


def xp_needed(level):
    return int(120 + level * 70 + level ** 1.6 * 6)

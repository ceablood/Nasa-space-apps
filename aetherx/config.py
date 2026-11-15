# -*- coding: utf-8 -*-
"""
AETHER-X // AYARLAR
Ekran boyutu, renk paleti, zaman ölçeği ve kayıt yolları.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# EKRAN
# ---------------------------------------------------------------------------
TITLE = "AETHER-X  //  Uzay Ajansı Komuta Simülasyonu"
W, H = 1600, 900            # mantıksal çözünürlük (SCALED ile pencereye sığar)
FPS = 60
TOPBAR_H = 64

# ---------------------------------------------------------------------------
# ZAMAN
# ---------------------------------------------------------------------------
# 1 gerçek saniye = 2 oyun dakikası  ->  "2 saat" = 60 gerçek saniye
GAME_MIN_PER_SEC = 2.0
MIN_PER_HOUR = 60
MIN_PER_DAY = 24 * 60
AUTOSAVE_SEC = 30.0

# ---------------------------------------------------------------------------
# KAYIT
# ---------------------------------------------------------------------------
SAVE_DIR = Path.home() / ".aetherx"
SAVE_FILE = SAVE_DIR / "kampanya.json"
SETTINGS_FILE = SAVE_DIR / "ayarlar.json"
SAVE_VERSION = 4

# ---------------------------------------------------------------------------
# EKONOMİ
# ---------------------------------------------------------------------------
START_MONEY = 1000
START_RP = 0
RENAME_COST = 500
MARKET_FUEL_PRICE = 4          # Para / kg  (Yakıt Deposu üretimi bedava)
REPAIR_KIT_PRICE = 150
STARDUST_TO_RP = 10

# ---------------------------------------------------------------------------
# RENKLER  (AAA neon / derin uzay paleti)
# ---------------------------------------------------------------------------
C = {
    "void":       (3, 5, 14),
    "deep":       (6, 10, 28),
    "abyss":      (10, 6, 30),
    "ink":        (14, 20, 44),
    "panel":      (16, 26, 54),
    "panel_hi":   (30, 48, 92),
    "glass":      (120, 180, 255),
    "text":       (255, 255, 255),
    "text_dim":   (216, 226, 242),
    "text_mute":  (150, 166, 194),
    "cyan":       (62, 230, 255),
    "blue":       (70, 140, 255),
    "violet":     (150, 100, 255),
    "magenta":    (255, 70, 200),
    "pink":       (255, 120, 170),
    "gold":       (255, 206, 84),
    "orange":     (255, 140, 50),
    "red":        (255, 64, 84),
    "green":      (70, 255, 160),
    "lime":       (170, 255, 90),
    "white":      (255, 255, 255),
    "black":      (0, 0, 0),
    "steel":      (150, 166, 190),
    "brown":      (170, 110, 60),
}

AGENCY_COLORS = [
    (62, 230, 255), (255, 70, 200), (255, 206, 84), (70, 255, 160),
    (150, 100, 255), (255, 140, 50), (255, 64, 84), (120, 200, 255),
]

# Astronot üniformaları
CREW_COLORS = {
    "pilot":     (70, 140, 255),    # mavi
    "engineer":  (255, 140, 50),    # turuncu
    "scientist": (70, 220, 120),    # yeşil
    "doctor":    (240, 244, 255),   # beyaz
    "miner":     (160, 105, 60),    # kahverengi
}

FONT_CANDIDATES = "segoeui,dejavusans,ubuntu,notosans,arial,helvetica,freesans"
MONO_CANDIDATES = "consolas,dejavusansmono,ubuntumono,menlo,couriernew"

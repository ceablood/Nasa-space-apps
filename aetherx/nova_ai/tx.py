# -*- coding: utf-8 -*-
"""
NOVA ÇEVİRİ KATMANI — Almanca, Fransızca, İspanyolca, Rusça.
NOVA her cümleyi Türkçe/İngilizce çift olarak üretir. Oyun dili de/fr/es/ru ise İngilizce cümle:
  1) tx_engine / tx_kb tablolarında birebir varsa doğrudan çevrilir;
  2) yoksa yer tutuculu kalıplarla eşleştirilir ({0}, {1}…), yakalanan değerler hedef dilde yerine konur;
  3) hiçbiri tutmazsa İngilizce kalır ve eksik listesine yazılır (testler bu listeyi denetler).
Sayılar kaynakta İngilizce biçimde üretilir ve yalnız burada, bir kez, hedef dilin biçimine çevrilir
(de/es 1.234,5 · fr 1 234,5 · ru 1 234,5) — iki kez biçimlendirme hatası olmaz.
"""
import re

from .. import i18n

LANGS = ("de", "fr", "es", "ru")
_IDX = {l: i for i, l in enumerate(LANGS)}
_TABLE = None
_TPL = None
MISSES = set()

NAMES = {   # gök cismi adları (de, fr, es, ru)
    "sun": ("Sonne", "Soleil", "Sol", "Солнце"), "mercury": ("Merkur", "Mercure", "Mercurio", "Меркурий"),
    "venus": ("Venus", "Vénus", "Venus", "Венера"), "earth": ("Erde", "Terre", "Tierra", "Земля"),
    "moon": ("Mond", "Lune", "Luna", "Луна"), "mars": ("Mars", "Mars", "Marte", "Марс"),
    "phobos": ("Phobos", "Phobos", "Fobos", "Фобос"), "deimos": ("Deimos", "Déimos", "Deimos", "Деймос"),
    "ceres": ("Ceres", "Cérès", "Ceres", "Церера"), "jupiter": ("Jupiter", "Jupiter", "Júpiter", "Юпитер"),
    "io": ("Io", "Io", "Ío", "Ио"), "europa": ("Europa", "Europe", "Europa", "Европа"),
    "ganymede": ("Ganymed", "Ganymède", "Ganímedes", "Ганимед"), "callisto": ("Kallisto", "Callisto", "Calisto", "Каллисто"),
    "saturn": ("Saturn", "Saturne", "Saturno", "Сатурн"), "titan": ("Titan", "Titan", "Titán", "Титан"),
    "enceladus": ("Enceladus", "Encelade", "Encélado", "Энцелад"), "uranus": ("Uranus", "Uranus", "Urano", "Уран"),
    "neptune": ("Neptun", "Neptune", "Neptuno", "Нептун"), "triton": ("Triton", "Triton", "Tritón", "Тритон"),
    "pluto": ("Pluto", "Pluton", "Plutón", "Плутон"),
}


def _body_en():
    from .facts import BODIES
    return {b["name"][1]: k for k, b in BODIES.items() if k in NAMES}


_BODY_EN = _body_en()
_UNITS_RX = re.compile(r"m/s²|km/s|m/s|W/m²|°C|\bkm\b|\bkg\b|\bAU\b|\bmin\b|\bh\b|\bs\b|\bm\b|\bK\b")


def lang():
    return i18n.LANG


def active():
    return i18n.LANG in _IDX


def body_name(key, default):
    n = NAMES.get(key)
    return n[_IDX[i18n.LANG]] if (n and i18n.LANG in _IDX) else default


# ------------------------------------------------------------------ sayı biçimi
_NUM = re.compile(r"(?<![\w.,])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d+)(?![\d])")
_SEP = {"de": (".", ","), "es": (".", ","), "fr": (" ", ","), "ru": (" ", ",")}


def localize_num(s, lg=None):
    """İngilizce biçimli sayıları (1,234.5 / 3.70) hedef dile çevirir; diğer metne dokunmaz."""
    lg = lg or i18n.LANG
    if lg not in _SEP:
        return s
    th, dec = _SEP[lg]

    def rep(m):
        t = m.group(1)
        ip, _, fp = t.partition(".")
        ip = ip.replace(",", th)
        return ip + (dec + fp if fp else "")
    out = _NUM.sub(rep, s)
    if lg == "ru":                                     # Rusçada birimler Kiril
        for a, b in _RU_UNITS:
            out = out.replace(a, b)
    return out


_RU_UNITS = ((" km/s", " км/с"), (" m/s²", " м/с²"), (" m/s", " м/с"), (" km", " км"), (" kg", " кг"), (" W/m²", " Вт/м²"),
             (" AU", " а. е."), (" bar", " бар"), (" t ", " т "))


# ------------------------------------------------------------------ tablolar
def _load():
    global _TABLE, _TPL
    if _TABLE is not None:
        return
    from . import tx_engine, tx_kb
    _TABLE = {}
    _TABLE.update(tx_kb.T)
    _TABLE.update(tx_engine.T)
    _TPL = []
    for en, tgt in _TABLE.items():
        if "{0}" not in en:
            continue
        parts = re.split(r"(\{\d+\})", en)
        rx, order = "", []
        for p in parts:
            m = re.fullmatch(r"\{(\d+)\}", p)
            if m:
                order.append(int(m.group(1)))
                rx += "(.*?)"
            else:
                rx += re.escape(p)
        lit = max((p for p in parts if not re.fullmatch(r"\{\d+\}", p)), key=len, default="")
        _TPL.append((lit, re.compile(rx + r"\Z", re.S), order, tgt))
    _TPL.sort(key=lambda x: -len(x[0]))          # en uzun sabit parçası olan kalıp önce


def _conv(v, i):
    """Yakalanan değer: tabloda birebir varsa çevrilir, yoksa yalnız sayıları yerelleştirilir."""
    if v in _TABLE:
        return _TABLE[v][i]
    st = v.strip()
    if st and st in _TABLE:
        return v.replace(st, _TABLE[st][i])
    return localize_num(v)


def translate(en):
    """İngilizce NOVA cümlesini oyun diline (de/fr/es/ru) çevirir; dil Türkçe/İngilizce ise dokunmaz."""
    if not en or i18n.LANG not in _IDX:
        return en
    _load()
    i = _IDX[i18n.LANG]
    if en in _TABLE:
        return _TABLE[en][i]
    if not re.search(r"[A-Za-z]", _UNITS_RX.sub("", en)):    # yalnız sayı/simge/birim: çeviri gerekmez
        return localize_num(en)
    bk = _BODY_EN.get(en.strip())
    if bk:                                             # İngilizce gök cismi adı
        return en.replace(en.strip(), NAMES[bk][i])
    st = en.strip()
    if st != en and st in _TABLE:
        return en.replace(st, _TABLE[st][i])
    for lit, rx, order, tgt in _TPL:
        if lit and lit not in en:
            continue
        m = rx.match(en)
        if m:
            vals = {}
            for gi, ph in enumerate(order):
                vals[ph] = _conv(m.group(gi + 1), i)
            out = tgt[i]
            for ph, val in vals.items():
                out = out.replace("{%d}" % ph, val)
            return out
    MISSES.add(en)
    return localize_num(en)


def pick(tr_, tr_text, en_text):
    """(tr if tr_ else en) yerine: İngilizce dal oyun diline çevrilir."""
    return tr_text if tr_ else translate(en_text)


def loc(text):
    """Çeviri gerektirmeyen ama sayı içeren birleşik satırlar (karşılaştırma tablosu vb.) için yalnız sayı biçimi."""
    return localize_num(text) if i18n.LANG in _IDX else text

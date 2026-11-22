# -*- coding: utf-8 -*-
"""
KOZMOGENİS // DİL MOTORU (Türkçe / English / Deutsch)

Oyunun kaynak dili Türkçedir. Metinler ekrana çizilmeden hemen önce
tr() ile seçili dile çevrilir:

  1) tam eşleşme            "Depo"                       -> "Depot"
  2) şablon eşleşmesi       "{0} Tamir Kiti alındı"      -> "{0} repair kits purchased"
  3) parçalı çeviri         "A · B", "Cümle 1. Cümle 2." -> parçalar ayrı ayrı

Çeviriler lang/en.py ve lang/de.py içinde {Türkçe kaynak: çeviri} sözlükleridir.
tools/extract_strings.py tüm ekran metinlerini lang/keys.json'a çıkarır; testler
eksik çeviri olup olmadığını bu listeye göre denetler.
"""
import json
import re
import sys
from pathlib import Path

from .config import SETTINGS_FILE, SAVE_DIR

LANGS = [("tr", "Türkçe"), ("en", "English"), ("de", "Deutsch"), ("fr", "Français"), ("es", "Español"),
         ("ru", "Русский")]
LANG = "en"
PREFS_VERSION = 2       # 2: varsayılan dil İngilizce, 4 kademeli grafik (low/medium/high/ultra)
PREFS = {"lang": "en", "quality": "high", "lang_chosen": True, "cinematic": True, "prefs_version": PREFS_VERSION}
if sys.platform == "emscripten":         # tarayıcıda (WebAssembly) hız için bir kademe düşük başla
    PREFS["quality"] = "medium"
# Grafik kademeleri. tex: gezegen dokusu yüksekliği (NASA haritaları en çok 1024 = 2048x1024 piksel),
# ss: 3B koloni süper örnekleme, stars/rocks: yıldız ve halka parçacığı sayısı, bloom: parlama şiddeti
# (0 = kapalı), motes: süzülen toz zerresi, fx: parçacık çarpanı, cine: sinematik ışık/pus geçişleri,
# live_tex: ana menüdeki canlı gezegen dokusu, live_every: canlı gezegenin kaç karede bir yeniden çizildiği.
QUALITY = {
    "low":    {"tex": 256, "ss": 1.0, "stars": 250, "rocks": 200, "bloom": 0.0, "motes": 0, "fx": 0.5,
               "cine": False, "live_tex": 256, "live_every": 3},
    "medium": {"tex": 512, "ss": 1.2, "stars": 500, "rocks": 600, "bloom": 0.5, "motes": 20, "fx": 0.8,
               "cine": True, "live_tex": 512, "live_every": 2},
    "high":   {"tex": 1024, "ss": 1.5, "stars": 900, "rocks": 1300, "bloom": 0.75, "motes": 38, "fx": 1.0,
               "cine": True, "live_tex": 512, "live_every": 1},
    "ultra":  {"tex": 2048, "ss": 2.0, "stars": 1500, "rocks": 2600, "bloom": 0.95, "motes": 64, "fx": 1.5,
               "cine": True, "live_tex": 1024, "live_every": 1},
}
QUALITY_ORDER = ("low", "medium", "high", "ultra")
QUALITY_LABEL = {
    "low": ("1 · DÜŞÜK", "Basit ayarlar: 256 piksel gezegen dokusu, parlama ve sinematik ışık kapalı, az parçacık. Zayıf cihazlar için."),
    "medium": ("2 · ORTA", "Ortalama: 512 piksel doku, hafif parlama, az toz zerresi, 1,2x süper örnekleme."),
    "high": ("3 · YÜKSEK", "Yüksek ayarlar: NASA haritalarının tam çözünürlüğü (2048x1024), tam sinematik ışık, 1,5x süper örnekleme."),
    "ultra": ("4 · ULTRA", "Mümkün olan en yüksek grafik: en büyük doku önbelleği, en güçlü parlama, en çok yıldız/parçacık, "
                            "2x süper örnekleme, menüde yüksek çözünürlüklü canlı gezegenler."),
}
_OLD_QUALITY = {"standard": "low", "high": "medium", "ultra": "high", "max": "ultra"}   # sürüm 1 adları

_exact, _upper, _lower = {}, {}, {}
_templates = []          # (regex, hedef, n_grup)
_cache, _skel = {}, {}
protected = set()
misses = set()
_NUM = re.compile(r"\d+(?:[.,:]\d+)*")
_PH = re.compile(r"\{(\d+)\}")
_SENT = re.compile(r"(?<=[.!?])\s+")
_DIR = Path(__file__).parent / "lang"


def quality():
    return QUALITY.get(PREFS.get("quality"), QUALITY["high"])


def quality_level():
    """0 düşük .. 3 ultra"""
    q = PREFS.get("quality")
    return QUALITY_ORDER.index(q) if q in QUALITY_ORDER else 2


# ---------------------------------------------------------------- tercihler
def load_prefs():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            PREFS.update({k: d[k] for k in ("lang", "quality", "lang_chosen", "cinematic", "cae", "keys", "prefs_version") if k in d})
            if d.get("prefs_version", 1) < 2:          # eski kayıt: bir kez İngilizceye geç, kalite adlarını taşı
                PREFS["lang"] = "en"
                PREFS["lang_chosen"] = True
                PREFS["quality"] = _OLD_QUALITY.get(PREFS.get("quality"), "high")
                PREFS["prefs_version"] = PREFS_VERSION
    except Exception:
        pass
    # Oyun her açılışta İngilizce başlar (giriş ekranı, menü, NOVA). Oyuncu oturum içinde dili değiştirebilir;
    # bir sonraki açılışta yine İngilizce gelir.
    PREFS["lang"] = "en"
    PREFS["lang_chosen"] = True
    if PREFS.get("quality") not in QUALITY:
        PREFS["quality"] = _OLD_QUALITY.get(PREFS.get("quality"), "high")
    if PREFS["lang"] not in [c for c, _ in LANGS]:
        PREFS["lang"] = "en"
    set_lang(PREFS["lang"])
    return PREFS


def save_prefs():
    try:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(PREFS, f, ensure_ascii=False)
    except Exception:
        pass


# ------------------------------------------------------------------- yükleme
def _compile(tpl):
    parts = _PH.split(tpl)
    rx, seen, lit = "", set(), 0
    for i, p in enumerate(parts):
        if i % 2 == 0:
            rx += re.escape(p)
            lit += len(p)
        elif p in seen:
            rx += f"(?P=g{p})"
        else:
            seen.add(p)
            rx += f"(?P<g{p}>.+?)"
    return re.compile("^" + rx + "$", re.S), lit


def set_lang(code):
    global LANG
    LANG = code
    PREFS["lang"] = code
    _exact.clear(); _upper.clear(); _lower.clear(); _cache.clear(); _skel.clear()
    del _templates[:]
    if code == "tr":
        return
    try:
        mod = __import__(f"aetherx.lang.{code}", fromlist=["T"])
        table = mod.T                          # {türkçe kaynak: çeviri}
    except Exception:
        return
    tpls = []
    for k, t in table.items():
        if _PH.search(k):
            rx, lit = _compile(k)
            tpls.append((lit, rx, t))
        else:
            _exact[k] = t
            _upper.setdefault(k.upper(), t)
            _lower.setdefault(k.lower(), t)
    tpls.sort(key=lambda x: -x[0])
    _templates.extend((rx, t) for _, rx, t in tpls)


# -------------------------------------------------------------------- çeviri
def _apply(rx, target, s):
    m = rx.match(s)
    if not m:
        return None
    gd = m.groupdict()

    def sub(mm):
        v = gd.get("g" + mm.group(1), "")
        return _core(v)[0]
    return _PH.sub(sub, target)


def _lookup(s):
    t = _exact.get(s)
    if t is not None:
        return t
    if s.isupper():
        t = _upper.get(s)
        if t is not None:
            return t.upper()
    t = _lower.get(s.lower())
    if t is not None:
        if not s.isupper() and t.isupper() and len(t) > 3:
            t = t.capitalize()
        if s[:1].isupper() and t[:1].islower():
            t = t[:1].upper() + t[1:]
        return t
    return None


def _core(s):
    """(çeviri, bulundu_mu)"""
    if not s or s in protected or not any(c.isalpha() for c in s):
        return s, True
    c = _cache.get(s)
    if c is not None:
        return c
    out = _lookup(s)
    if out is None:
        sk = _NUM.sub("#", s)
        hit = _skel.get(sk)
        if hit is not None and hit is not False:
            out = _apply(hit[0], hit[1], s)
        if out is None and hit is not False:
            for rx, target in _templates:
                out = _apply(rx, target, s)
                if out is not None:
                    _skel[sk] = (rx, target)
                    break
            else:
                _skel[sk] = False
    found = out is not None
    if not found:
        out = _pieces(s)
        found = out is not None
        if not found:
            out = s
            misses.add(s)
    if len(_cache) > 30000:
        _cache.clear()
    _cache[s] = (out, found)
    return out, found


def _pieces(s):
    for sep in (" · ", "\n"):
        if sep in s:
            parts = [_core(p) for p in s.split(sep)]
            if any(f for _, f in parts):
                return sep.join(p for p, _ in parts)
    sents = _SENT.split(s)
    if len(sents) > 1:
        parts = [_core(p) for p in sents]
        if any(f and p != o for (p, f), o in zip(parts, sents)):
            return " ".join(p for p, _ in parts)
    for sep in (" (", ": ", " - ", ", "):
        i = s.find(sep)
        if 0 < i < len(s) - len(sep):
            a, fa = _core(s[:i])
            if fa and a != s[:i]:
                rest = s[i + len(sep):]
                tail = ")" if sep == " (" and rest.endswith(")") else ""
                if tail:
                    rest = rest[:-1]
                return a + sep + _core(rest)[0] + tail
    return None


def tr(s):
    if LANG == "tr" or not isinstance(s, str):
        return s
    return _core(s)[0]


def pct(v):
    """Yüzde: tr '%5', en '5%', de '5 %'."""
    v = int(round(v))
    if LANG == "tr":
        return f"%{v}"
    if LANG == "en":
        return f"{v}%"
    return f"{v}\u202f%" if LANG in ("fr", "ru") else f"{v} %"


def num(v, d=0):
    """Dile göre sayı biçimi: en 1,234.5 · tr/de/es 1.234,5 · fr/ru 1 234,5"""
    t = f"{v:,.{d}f}"
    if LANG == "en":
        return t
    sep = "\u202f" if LANG in ("fr", "ru") else "."
    return t.replace(",", "§").replace(".", ",").replace("§", sep)


def pick(d):
    """{'tr':..,'en':..,'de':..} sözlüğünden seçili dili döndürür."""
    if isinstance(d, dict):
        v = d.get(LANG)
        if v:
            return v
        en = d.get("en") or ""
        if LANG in _XTRA_LANGS and en:
            row = _atlas_x().get(en)
            if row:
                return row[_XTRA_LANGS.index(LANG)]
        return en or d.get("tr") or ""
    if isinstance(d, str) and LANG in _XTRA_LANGS:
        row = _atlas_names().get(d)
        if row:
            return row[_XTRA_LANGS.index(LANG)]
    return d


_XTRA_LANGS = ("fr", "es", "ru")
_ATLAS_X = None


def _atlas_x():
    """Atlas metinlerinin fr/es/ru çevirileri: İngilizce metin -> (fr, es, ru)."""
    global _ATLAS_X
    if _ATLAS_X is None:
        try:
            from .lang import atlas_x
            _ATLAS_X = atlas_x.T
        except Exception:
            _ATLAS_X = {}
    return _ATLAS_X


_NAMES_X = None


def _atlas_names():
    global _NAMES_X
    if _NAMES_X is None:
        try:
            from .lang import atlas_x
            _NAMES_X = atlas_x.NAMES
        except Exception:
            _NAMES_X = {}
    return _NAMES_X

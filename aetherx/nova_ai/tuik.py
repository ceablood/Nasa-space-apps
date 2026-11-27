# -*- coding: utf-8 -*-
"""
NOVA — TÜİK VERİSİ (gerçek, resmî)
Kaynak: TÜİK Nüfus İstatistikleri Portalı (nip.tuik.gov.tr) il düzeyi göstergeleri, 2026-11-27'de indirildi
(data/tuik_il.json). Değerler dosyadan okunur; hiçbiri elle yazılmamıştır.
  * Sayım göstergeleri (nüfus, ölüm, boşanma, hanehalkı, yabancı nüfus) için Türkiye değeri = 81 ilin toplamı.
  * Oran göstergeleri (ortanca yaş, doğurganlık, bebek ölüm hızı, yoğunluk…) il bazındadır; Türkiye geneli için portal
    dosyası olmadığından il değerlerinden ulusal oran UYDURULMAZ. Yalnız nüfus artış hızı, TÜİK'in formülüyle
    (r = ln(Pt / Pt-1) × 1000) il toplamlarından hesaplanır ve "hesaplandı" diye belirtilir.
  * Erkek/kadın nüfusu portal dosyasında tutarsız olduğu için pakete alınmadı (bkz. dosyadaki "excluded").
"""
import json
import math
import os

from . import lexicon as LX

_PATH = os.path.join(os.path.dirname(__file__), "data", "tuik_il.json")
_D = None

COUNT = {"NufusToplam", "Olum", "Bosanma", "HanehalkiSayisi", "YabanciNufusBuyuklugu"}

# gösterge -> (anahtar sözcükler (normalize), (tr ad, en ad), tr birim, en birim)
IND = {
    "NufusToplam": (("nufus", "nufusu", "population", "kac kisi", "kalabalik", "kisi yasiyor", "insan yasiyor"),
                    ("nüfus", "population"), "kişi", "people"),
    "OrtancaYas": (("ortanca yas", "medyan yas", "median age", "yas ortalamasi", "ortalama yas", "yasli mi", "genc mi"),
                   ("ortanca yaş", "median age"), "yaş", "years"),
    "NufusArtisHizi": (("artis hizi", "nufus artisi", "growth rate", "population growth", "buyume hizi", "artiyor mu"),
                       ("nüfus artış hızı", "population growth rate"), "‰", "‰"),
    "NufusYogunlugu": (("yogunluk", "yogunlugu", "density", "km2", "kilometrekare"),
                       ("nüfus yoğunluğu", "population density"), "kişi/km²", "people/km²"),
    "ToplamDogurganlikHizi": (("dogurganlik", "fertility", "cocuk sayisi", "kadin basina"),
                              ("toplam doğurganlık hızı", "total fertility rate"), "çocuk/kadın", "children per woman"),
    "BebekOlumHizi": (("bebek olum", "infant mortality", "bebek olumu"),
                      ("bebek ölüm hızı", "infant mortality rate"), "‰", "per 1,000 live births"),
    "Olum": (("olum sayisi", "olen", "deaths", "kac kisi oldu", "olum"),
             ("ölüm sayısı", "number of deaths"), "kişi", "people"),
    "Bosanma": (("bosanma", "divorce"), ("boşanma sayısı", "number of divorces"), "", ""),
    "HanehalkiSayisi": (("hanehalki sayisi", "hane sayisi", "households", "kac hane"),
                        ("hanehalkı sayısı", "number of households"), "", ""),
    "OrtalamaHanehalkiBuyuklugu": (("hanehalki buyuklugu", "hane buyuklugu", "household size", "evde kac kisi"),
                                   ("ortalama hanehalkı büyüklüğü", "average household size"), "kişi", "people"),
    "YabanciNufusBuyuklugu": (("yabanci nufus", "yabanci", "foreign", "gocmen"),
                              ("yabancı nüfus", "foreign population"), "kişi", "people"),
}

TR_WORDS = ("turkiye", "turkey", "ulke", "ulkemiz", "memleket", "tuik")


def data():
    global _D
    if _D is None:
        with open(_PATH, encoding="utf-8") as fh:
            _D = json.load(fh)
        _D["_norm"] = [LX.normalize(n) for n in _D["provinces"]]
    return _D


def source_line(tr_):
    d = data()
    return (f"Kaynak: TÜİK Nüfus İstatistikleri Portalı, {d['fetched']} tarihli veri."
            if tr_ else f"Source: TurkStat (TÜİK) Population Statistics Portal, data retrieved {d['fetched']}.")


# il adından sonra izin verilen ekler (aksansız): İstanbul'da, Ankara'nın, İzmir'e, Bursalı …
_SUFFIX = {"", "da", "de", "ta", "te", "dan", "den", "tan", "ten", "in", "un", "nin", "nun", "a", "e", "ya", "ye", "i", "u",
           "yi", "yu", "daki", "deki", "taki", "teki", "li", "lu", "lilar", "liler", "n", "nda", "nde", "ndaki", "ndeki"}


_BLOCK = {"karsi", "karsin", "karsiya", "karsida", "karsidan", "ordu", "orduda"}   # "karşı" ≠ Kars; "ordu" (asker) belirsiz


def find_province(norm):
    """Metindeki il (plaka sırası 0..80) ya da None. Ekli biçimleri de yakalar: istanbulda, ankaranin, izmir in."""
    d = data()
    toks = LX.tokens(norm)
    best = None
    for i, pn in enumerate(d["_norm"]):
        if " " in pn:
            if pn in norm:
                return i
            continue
        for t in toks:
            if t in _BLOCK and not (pn == "ordu" and LX.has_any(norm, ("ili", "ilinin", "ilinde", "sehri", "province"))):
                continue
            if t.startswith(pn) and t[len(pn):] in _SUFFIX:
                if best is None or len(pn) > len(d["_norm"][best]):
                    best = i
    return best


def find_indicator(norm):
    best, n = None, 0
    for k, (kws, *_rest) in IND.items():
        for kw in kws:
            hit = (kw in norm) if " " in kw else (kw in LX.tokens(norm) or any(t.startswith(kw) for t in LX.tokens(norm) if len(kw) >= 5))
            if hit and len(kw) > n:
                best, n = k, len(kw)
    return best


def wants_tuik(norm):
    return find_indicator(norm) is not None and (find_province(norm) is not None or LX.has_any(norm, TR_WORDS + ("il", "iller", "sehir", "province", "city")))


def series(ind, prov=None):
    """(yıllar, değerler) — prov None ise Türkiye (yalnız sayım göstergeleri ve hesaplanan artış hızı)."""
    d = data()
    I = d["indicators"][ind]
    years = I["years"]
    if prov is not None:
        return years, I["values"][prov]
    if ind in COUNT:
        return years, [sum(v[j] for v in I["values"]) for j in range(len(years))]
    if ind == "NufusArtisHizi":
        y, p = series("NufusToplam")
        return y[1:], [round(math.log(p[j] / p[j - 1]) * 1000, 1) for j in range(1, len(p))]
    return years, None


def fmt(x, tr_, dec=None):
    if x is None:
        return "?"
    if dec is None:
        dec = 0 if float(x).is_integer() else 1
    s = f"{x:,.{dec}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".") if tr_ else s


def answer(norm, tr_):
    """Doğal dilde TÜİK yanıtı ya da None. (metin, güven 0..1)"""
    ind = find_indicator(norm)
    if ind is None:
        return None
    d = data()
    prov = find_province(norm)
    names = d["provinces"]
    kws, (n_tr, n_en), u_tr, u_en = IND[ind]
    name = n_tr if tr_ else n_en
    unit = u_tr if tr_ else u_en
    rank_q = LX.has_any(norm, ("en", "most", "highest", "lowest", "en dusuk", "en yuksek", "en kalabalik", "en az", "en cok",
                               "hangi il", "which province", "siralama", "ranking"))
    trend_q = LX.has_any(norm, ("degisim", "trend", "artti", "azaldi", "yillar", "since", "2008", "gecmis", "change", "over time"))
    I = d["indicators"][ind]
    yrs = I["years"]
    last = yrs[-1]
    if rank_q and prov is None:
        vals = [v[-1] for v in I["values"]]
        low = LX.has_any(norm, ("en dusuk", "en az", "lowest", "least", "en kucuk", "en genc", "en seyrek"))
        order = sorted(range(81), key=lambda i: vals[i], reverse=not low)[:5]
        head = (f"{last} yılında {name} {'en düşük' if low else 'en yüksek'} 5 il: " if tr_ else
                f"Provinces with the {'lowest' if low else 'highest'} {name} in {last}: ")
        body = ", ".join(f"{names[i]} ({fmt(vals[i], tr_, I.get('decimals'))}{(' ' + unit) if unit else ''})" for i in order)
        return head + body + ". " + source_line(tr_), 0.97
    ys, vs = series(ind, prov)
    where = names[prov] if prov is not None else ("Türkiye" if tr_ else "Türkiye")
    if vs is None:
        return ((f"{name.capitalize()} için portalda Türkiye geneli dosyası yok; il değerlerinden ulusal oran uydurmam. "
                 f"Bir il sorarsan söyleyebilirim (ör. 'Ankara'nın {name}').") if tr_ else
                (f"The portal has no national file for {name}; I won't invent a national rate from province values. "
                 f"Ask about a province, e.g. 'median age in Ankara'.")), 0.9
    v = vs[-1]
    dec = 1 if (prov is None and ind == "NufusArtisHizi") else I.get("decimals")
    out = (f"{where}: {name} {ys[-1]} yılında {fmt(v, tr_, dec)}{(' ' + unit) if unit else ''}." if tr_ else
           f"{where}: {name} in {ys[-1]} was {fmt(v, tr_, dec)}{(' ' + unit) if unit else ''}.")
    if prov is None and ind == "NufusArtisHizi":
        out += " (81 ilin nüfus toplamından TÜİK formülüyle hesaplandı.)" if tr_ else " (Computed from the 81-province totals with TurkStat's formula.)"
    elif prov is None and ind in COUNT:
        out += " (81 ilin toplamı.)" if tr_ else " (Sum of all 81 provinces.)"
    if len(vs) >= 2 and vs[-2] is not None:
        if ind in COUNT:
            ch = (v - vs[-2]) / abs(vs[-2]) * 100 if vs[-2] else 0
            if abs(ch) < 0.05:
                out += " Bir önceki yıla göre neredeyse değişmedi." if tr_ else " Almost unchanged on the previous year."
            else:
                out += (f" Bir önceki yıla göre %{fmt(abs(ch), tr_, 1)} {'artış' if ch >= 0 else 'azalış'}." if tr_ else
                        f" That is {fmt(abs(ch), tr_, 1)}% {'up' if ch >= 0 else 'down'} on the previous year.")
        else:                                        # oranlarda yüzde değişim yanıltıcı: önceki yılın değerini ver
            out += (f" Bir önceki yıl ({ys[-2]}): {fmt(vs[-2], tr_, dec)}." if tr_ else f" Previous year ({ys[-2]}): {fmt(vs[-2], tr_, dec)}.")
    if trend_q and len(vs) > 2:
        out += (f" {ys[0]} yılında {fmt(vs[0], tr_, dec)} idi." if tr_ else f" In {ys[0]} it was {fmt(vs[0], tr_, dec)}.")
    if prov is not None and ind in COUNT:
        tot = series(ind)[1][-1]
        if tot:
            pv = fmt(v / tot * 100, tr_, 1)
            out += (f" Türkiye toplamının %{pv}'{LX.num_ek(pv)}." if tr_ else f" That's {fmt(v / tot * 100, tr_, 1)}% of the national total.")
    if prov is not None and ind not in COUNT:
        vals = [x[-1] for x in I["values"]]
        rk = sorted(range(81), key=lambda i: -vals[i]).index(prov) + 1
        out += (f" 81 il arasında {rk}. sırada (yüksekten düşüğe)." if tr_ else f" It ranks #{rk} of 81 provinces (high to low).")
    return out + " " + source_line(tr_), 0.96

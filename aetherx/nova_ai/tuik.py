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
from .tx import pick as _pick

_PATH = os.path.join(os.path.dirname(__file__), "data", "tuik_il.json")
_D = None

COUNT = {"NufusToplam", "Olum", "Bosanma", "HanehalkiSayisi", "YabanciNufusBuyuklugu", "Evlilik", "AlinanGoc", "VerilenGoc",
         "Dogum", "YurtdisindanGelenGoc", "YurtdisinaGidenGoc", "YabanciNufusErkek", "YabanciNufusKadin"}
DERIVED = {"NetGoc": ("AlinanGoc", "VerilenGoc")}       # il bazında aldığı - verdiği göç (hesaplanır)

# gösterge -> (anahtar sözcükler (normalize), (tr ad, en ad), tr birim, en birim)
IND = {
    "NufusToplam": (("nufus", "nufusu", "population", "bevolkerung", "einwohner", "habitants", "poblacion", "habitantes", "населени", "жителей", "kac kisi", "kalabalik", "kisi yasiyor", "insan yasiyor"),
                    ("nüfus", "population"), "kişi", "people"),
    "OrtancaYas": (("ortanca yas", "medianalter", "age median", "edad mediana", "медианный возраст", "medyan yas", "median age", "yas ortalamasi", "ortalama yas", "yasli mi", "genc mi"),
                   ("ortanca yaş", "median age"), "yaş", "years"),
    "NufusArtisHizi": (("artis hizi", "bevolkerungswachstum", "croissance demographique", "crecimiento de la poblacion", "прирост населения", "nufus artisi", "growth rate", "population growth", "buyume hizi", "artiyor mu"),
                       ("nüfus artış hızı", "population growth rate"), "‰", "‰"),
    "NufusYogunlugu": (("yogunluk", "bevolkerungsdichte", "densite", "densidad", "плотност", "yogunlugu", "density", "km2", "kilometrekare"),
                       ("nüfus yoğunluğu", "population density"), "kişi/km²", "people/km²"),
    "ToplamDogurganlikHizi": (("dogurganlik", "fruchtbarkeit", "geburtenrate", "fecondite", "fecundidad", "natalidad", "рождаемост", "fertility", "cocuk sayisi", "kadin basina"),
                              ("toplam doğurganlık hızı", "total fertility rate"), "çocuk/kadın", "children per woman"),
    "BebekOlumHizi": (("bebek olum", "sauglingssterblichkeit", "mortalite infantile", "mortalidad infantil", "младенческ", "infant mortality", "bebek olumu"),
                      ("bebek ölüm hızı", "infant mortality rate"), "‰", "per 1,000 live births"),
    "Olum": (("olum sayisi", "todesfalle", "sterbefalle", "deces", "defunciones", "смертност", "смертей", "olen", "deaths", "kac kisi oldu", "olum"),
             ("ölüm sayısı", "number of deaths"), "kişi", "people"),
    "Bosanma": (("bosanma", "divorce", "scheidung", "scheidungen", "divorces", "divorcio", "divorcios", "развод"), ("boşanma sayısı", "number of divorces"), "", ""),
    "HanehalkiSayisi": (("hanehalki sayisi", "haushalte", "menages", "hogares", "домохозяйств", "hane sayisi", "households", "kac hane"),
                        ("hanehalkı sayısı", "number of households"), "", ""),
    "OrtalamaHanehalkiBuyuklugu": (("hanehalki buyuklugu", "haushaltsgrosse", "taille des menages", "tamano del hogar", "размер домохозяйства", "hane buyuklugu", "household size", "evde kac kisi"),
                                   ("ortalama hanehalkı büyüklüğü", "average household size"), "kişi", "people"),
    "Dogum": (("dogum sayisi", "canli dogum", "kac bebek", "births", "live births", "geburten", "naissances", "nacimientos",
               "рождени", "родилось"), ("canlı doğum sayısı", "number of live births"), "", ""),
    "BagimlilikCocuk": (("cocuk bagimlilik", "child dependency", "jugendquotient", "dependance des jeunes",
                         "dependencia infantil", "нагрузка детьми"), ("çocuk bağımlılık oranı", "child dependency ratio"), "%", "%"),
    "YurtdisindanGelenGoc": (("yurtdisindan gelen", "yurt disindan gelen", "from abroad", "aus dem ausland", "venant de l etranger",
                              "del extranjero", "из-за рубежа", "из-за границы"),
                             ("yurt dışından gelen göç", "migration from abroad"), "kişi", "people"),
    "YurtdisinaGidenGoc": (("yurtdisina giden", "yurt disina giden", "to abroad", "emigration", "ins ausland", "vers l etranger",
                            "al extranjero", "за рубеж", "уехали за границу"),
                           ("yurt dışına giden göç", "migration abroad"), "kişi", "people"),
    "YabanciNufusErkek": (("yabanci erkek", "foreign men", "auslandische manner", "hommes etrangers", "hombres extranjeros",
                           "иностранцы мужчины"), ("yabancı erkek nüfus", "foreign male population"), "kişi", "people"),
    "YabanciNufusKadin": (("yabanci kadin", "foreign women", "auslandische frauen", "femmes etrangeres", "mujeres extranjeras",
                           "иностранки"), ("yabancı kadın nüfus", "foreign female population"), "kişi", "people"),
    "Evlilik": (("evlenme", "evlilik", "marriage", "marriages", "heirat", "eheschliessung", "mariage", "matrimonio", "брак"),
                ("evlenme sayısı", "number of marriages"), "", ""),
    "OkumaYazmaOran": (("okuma yazma", "okuryazar", "literacy", "alphabetisierung", "alphabetisation", "alfabetizacion",
                        "грамотност"), ("okuma yazma bilen oranı", "literacy rate"), "%", "%"),
    "NetGoc": (("net goc", "net migration", "nettomigration", "migration nette", "migracion neta", "чистая миграция",
                "goc veren", "goc alan"), ("net göç", "net migration"), "kişi", "people"),
    "AlinanGoc": (("aldigi goc", "goc aldi", "in-migration", "zuwanderung", "immigration interne", "inmigracion",
                   "прибывшие", "приток мигрантов"), ("aldığı göç", "in-migration (received)"), "kişi", "people"),
    "VerilenGoc": (("verdigi goc", "goc verdi", "out-migration", "abwanderung", "emigration interne", "emigracion",
                    "выбывшие", "отток"), ("verdiği göç", "out-migration (given)"), "kişi", "people"),
    "BagimlilikToplam": (("bagimlilik", "bagimlilik orani", "dependency ratio", "abhangigkeitsquote", "taux de dependance",
                          "tasa de dependencia", "коэффициент нагрузки"), ("toplam yaş bağımlılık oranı", "total age dependency ratio"), "%", "%"),
    "BagimlilikYasli": (("yasli bagimlilik", "old-age dependency", "altenquotient", "dependance des personnes agees",
                         "dependencia de mayores", "нагрузка пожилыми"), ("yaşlı bağımlılık oranı", "old-age dependency ratio"), "%", "%"),
    "YabanciNufusBuyuklugu": (("yabanci nufus", "auslander", "etrangers", "extranjeros", "иностранц", "yabanci", "foreign", "gocmen"),
                              ("yabancı nüfus", "foreign population"), "kişi", "people"),
}

TR_WORDS = ("turkiye", "turkey", "ulke", "ulkemiz", "memleket", "tuik", "turkei", "turquie", "turquia", "турция", "турции",
            "provinz", "provinzen", "provinces", "provincia", "provincias", "провинци")
# başka dillerdeki il adları (normalize): plaka sırası 0..80
EXONYMS = {"стамбул": 33, "estambul": 33, "анкара": 5, "измир": 34, "esmirna": 34, "smyrne": 34, "анталья": 6,
           "бурса": 15, "трабзон": 60, "конья": 41, "eskisehir": 25}


def data():
    global _D
    if _D is None:
        with open(_PATH, encoding="utf-8") as fh:
            _D = json.load(fh)
        _D["_norm"] = [LX.normalize(n) for n in _D["provinces"]]
    return _D


def source_line(tr_):
    d = data()
    return (_pick(tr_, f"Kaynak: TÜİK Nüfus İstatistikleri Portalı, {d['fetched']} tarihli veri.", f"Source: TurkStat (TÜİK) Population Statistics Portal, data retrieved {d['fetched']}."))


# il adından sonra izin verilen ekler (aksansız): İstanbul'da, Ankara'nın, İzmir'e, Bursalı …
_SUFFIX = {"", "da", "de", "ta", "te", "dan", "den", "tan", "ten", "in", "un", "nin", "nun", "a", "e", "ya", "ye", "i", "u",
           "yi", "yu", "daki", "deki", "taki", "teki", "li", "lu", "lilar", "liler", "n", "nda", "nde", "ndaki", "ndeki"}


_BLOCK = {"karsi", "karsin", "karsiya", "karsida", "karsidan", "ordu", "orduda"}   # "karşı" ≠ Kars; "ordu" (asker) belirsiz


def find_province(norm):
    """Metindeki il (plaka sırası 0..80) ya da None. Ekli biçimleri de yakalar: istanbulda, ankaranin, izmir in."""
    d = data()
    toks = LX.tokens(norm)
    for t in toks:
        for ex, idx in EXONYMS.items():
            if t == ex or (t.startswith(ex) and len(t) - len(ex) <= 2) or \
                    (len(ex) >= 5 and t[:len(ex) - 1] == ex[:-1] and 0 <= len(t) - len(ex) <= 2):   # Rusça çekim: Анкаре, Стамбуле
                return idx
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


def indicator(ind):
    """Gösterge sözlüğü; türetilmişse (net göç) iki göstergeden hesaplanır."""
    d = data()
    if ind in d["indicators"]:
        return d["indicators"][ind]
    a, b = (d["indicators"][k] for k in DERIVED[ind])
    return {"title": "Net Göç (hesaplanan)", "unit": "", "years": a["years"], "decimals": 0,
            "values": [[x - y for x, y in zip(va, vb)] for va, vb in zip(a["values"], b["values"])]}


def series(ind, prov=None):
    """(yıllar, değerler) — prov None ise Türkiye (yalnız sayım göstergeleri ve hesaplanan artış hızı)."""
    I = indicator(ind)
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


def withunit(num, unit, tr_):
    """Sayı + birim: Türkçede yüzde önde (%43,9), İngilizcede bitişik (43.9%), diğerlerinde boşluklu."""
    if not unit:
        return num
    if unit == "%":
        return "%" + num if tr_ else num + "%"
    return f"{num} {unit}"


def answer(norm, tr_):
    """Doğal dilde TÜİK yanıtı ya da None. (metin, güven 0..1)"""
    ind = find_indicator(norm)
    if ind is None:
        return None
    d = data()
    prov = find_province(norm)
    names = d["provinces"]
    kws, (n_tr, n_en), u_tr, u_en = IND[ind]
    name = _pick(tr_, n_tr, n_en)
    unit = _pick(tr_, u_tr, u_en)
    rank_q = LX.has_any(norm, ("en", "most", "highest", "lowest", "en dusuk", "en yuksek", "en kalabalik", "en az", "en cok",
                               "hangi il", "which province", "siralama", "ranking"))
    trend_q = LX.has_any(norm, ("degisim", "trend", "artti", "azaldi", "yillar", "since", "2008", "gecmis", "change", "over time"))
    I = indicator(ind)
    yrs = I["years"]
    last = yrs[-1]
    if rank_q and prov is None:
        vals = [v[-1] for v in I["values"]]
        low = LX.has_any(norm, ("en dusuk", "en az", "lowest", "least", "en kucuk", "en genc", "en seyrek"))
        order = sorted(range(81), key=lambda i: vals[i], reverse=not low)[:5]
        head = (_pick(tr_, f"{last} yılında {name} {'en düşük' if low else 'en yüksek'} 5 il: ", f"Provinces with the {'lowest' if low else 'highest'} {name} in {last}: "))
        unit_l = unit                                    # (birim yukarıda zaten oyun diline çevrildi)
        body = ", ".join(f"{names[i]} ({withunit(fmt(vals[i], tr_, I.get('decimals')), unit_l, tr_)})" for i in order)
        if not tr_:
            from .tx import loc as _loc
            body = _loc(body)
        return head + body + ". " + source_line(tr_), 0.97
    if ind == "NetGoc" and prov is None:
        ys_, moved = series("AlinanGoc")
        return ((f"İller arası göçte ülke toplamında net göç sıfırdır: bir ilin aldığı göç, başka bir ilin verdiği göçtür. "
                 f"{ys_[-1]} yılında {fmt(moved[-1], tr_)} kişi il değiştirdi. " if tr_ else
                 _pick(False, "", f"For migration between provinces, national net migration is zero by definition: one province's "
                                  f"in-migration is another's out-migration. In {ys_[-1]}, {fmt(moved[-1], tr_)} people changed province. "))
                + source_line(tr_)), 0.95
    ys, vs = series(ind, prov)
    where = names[prov] if prov is not None else (_pick(tr_, "Türkiye", "Türkiye"))
    if vs is None:
        return (_pick(tr_, f"{name.capitalize()} için portalda Türkiye geneli dosyası yok; il değerlerinden ulusal oran uydurmam. "
                 f"Bir il sorarsan söyleyebilirim (ör. 'Ankara'nın {name}').", f"The portal has no national file for {name}; I won't invent a national rate from province values. "
                 f"Ask about a province, e.g. 'median age in Ankara'.")), 0.9
    v = vs[-1]
    dec = 1 if (prov is None and ind == "NufusArtisHizi") else I.get("decimals")
    vu = withunit(fmt(v, tr_, dec), unit, tr_)
    num_s = fmt(v, tr_, dec)
    unit_s = ("%" if unit == "%" else (" " + unit if unit else ""))
    out = (_pick(tr_, f"{where}: {name} {ys[-1]} yılında {vu}.", f"{where}: {name} in {ys[-1]} was {num_s}{unit_s}."))
    if prov is None and ind == "NufusArtisHizi":
        out += _pick(tr_, " (81 ilin nüfus toplamından TÜİK formülüyle hesaplandı.)", " (Computed from the 81-province totals with TurkStat's formula.)")
    elif prov is None and ind in COUNT:
        out += _pick(tr_, " (81 ilin toplamı.)", " (Sum of all 81 provinces.)")
    if len(vs) >= 2 and vs[-2] is not None:
        if ind in COUNT:
            ch = (v - vs[-2]) / abs(vs[-2]) * 100 if vs[-2] else 0
            if abs(ch) < 0.05:
                out += _pick(tr_, " Bir önceki yıla göre neredeyse değişmedi.", " Almost unchanged on the previous year.")
            else:
                out += (_pick(tr_, f" Bir önceki yıla göre %{fmt(abs(ch), tr_, 1)} {'artış' if ch >= 0 else 'azalış'}.", f" That is {fmt(abs(ch), tr_, 1)}% {'up' if ch >= 0 else 'down'} on the previous year."))
        else:                                        # oranlarda yüzde değişim yanıltıcı: önceki yılın değerini ver
            out += (_pick(tr_, f" Bir önceki yıl ({ys[-2]}): {fmt(vs[-2], tr_, dec)}.", f" Previous year ({ys[-2]}): {fmt(vs[-2], tr_, dec)}."))
    if trend_q and len(vs) > 2:
        out += (_pick(tr_, f" {ys[0]} yılında {fmt(vs[0], tr_, dec)} idi.", f" In {ys[0]} it was {fmt(vs[0], tr_, dec)}."))
    if ind == "NetGoc":
        out += (" (Hesaplandı: aldığı göç − verdiği göç; eksi değer, ilin net göç verdiğini gösterir.)" if tr_ else
                _pick(False, "", " (Computed: in-migration minus out-migration; a negative value means the province lost people.)"))
    if prov is not None and ind in COUNT:
        tot = series(ind)[1][-1]
        if tot:
            pv = fmt(v / tot * 100, tr_, 1)
            out += (_pick(tr_, f" Türkiye toplamının %{pv}'{LX.num_ek(pv)}.", f" That's {fmt(v / tot * 100, tr_, 1)}% of the national total."))
    if prov is not None and ind not in COUNT:
        vals = [x[-1] for x in I["values"]]
        rk = sorted(range(81), key=lambda i: -vals[i]).index(prov) + 1
        out += (_pick(tr_, f" 81 il arasında {rk}. sırada (yüksekten düşüğe).", f" It ranks #{rk} of 81 provinces (high to low)."))
    return out + " " + source_line(tr_), 0.96

# -*- coding: utf-8 -*-
"""
NOVA DİL İŞLEME — normalizasyon, sözcük ayırma, Türkçe ek sıyırma, varlık (gök cismi, sayı, birim) çıkarımı.
Bağımsız: ağ ya da büyük model kullanmaz; kurallar ve sözlüklerle çalışır.
"""
import re

FOLD = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o",
                      "ç": "c", "Ç": "c", "â": "a", "î": "i", "û": "u", "é": "e", "è": "e", "ê": "e", "à": "a", "ñ": "n",
                      "ä": "a", "ß": "ss", "ó": "o", "í": "i", "á": "a", "ú": "u", "’": "'", "‘": "'"})


def normalize(text):
    """Küçük harf + aksan katlama + noktalama temizliği (kesme işareti sözcüğü böler: Mars'a -> mars a)."""
    t = text.translate(FOLD).lower().translate(FOLD)
    t = re.sub(r"[\"“”!?¿¡;:()\[\]{}<>…]", " ", t)
    t = t.replace("'", " ").replace("’", " ")
    t = re.sub(r"(?<!\d)[.,](?!\d)", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Türkçe çekim ekleri (uzundan kısaya); kök en az 3 harf kalmalı.
SUFFIXES = sorted(set("""
lerinden larindan lerinde larinda lerine larina lerini larini lerin larin leri lari
inden indan unden undan nden ndan inde inda unde unda nde nda ine ina une una
ini ini unu unu nin nun in un ler lar den dan ten tan de da te ta ye ya e a i u
yi yu si su mi mu mu misin musun miyim muyum dir dur tir tur
""".split()), key=len, reverse=True)


def stem(word):
    if len(word) <= 4 or word.isdigit():
        return word
    for s in SUFFIXES:
        if word.endswith(s) and len(word) - len(s) >= 3:
            r = word[: -len(s)]
            return r[:-1] + "k" if r.endswith("g") and len(r) >= 5 else r      # ünsüz yumuşaması: uzaklığı -> uzaklık
    return word


def ek(name, case):
    """Türkçe özel ad eki (ünlü uyumu + ünsüz benzeşmesi): case = 'da' (bulunma), 'a' (yönelme), 'dan' (ayrılma), 'in' (ilgi)."""
    low = name.lower()
    vow = [c for c in low if c in "aıoueiöü"]
    last = vow[-1] if vow else "e"
    back = last in "aıou"
    ends_v = low[-1] in "aıoueiöü"
    hard = low[-1] in "fstkçşhp"
    if case == "da":
        return name + "'" + ("t" if hard else "d") + ("a" if back else "e")
    if case == "dan":
        return name + "'" + ("t" if hard else "d") + ("an" if back else "en")
    if case == "a":
        return name + "'" + ("y" if ends_v else "") + ("a" if back else "e")
    if case == "in":
        h = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[last]
        return name + "'" + ("n" if ends_v else "") + h + "n"
    return name


def tokens(norm):
    return [w for w in norm.split() if w]


def stems(norm):
    return [stem(w) for w in tokens(norm)]


# Gök cisimleri: farklı dillerdeki adlar (normalize edilmiş). Oyunun desteklediği 6 dil + yaygın yazımlar.
BODY_ALIASES = {
    "sun": ("gunes", "sun", "sonne", "soleil", "sol", "solntse", "солнце"),
    "mercury": ("merkur", "mercury", "mercure", "mercurio", "меркурий"),
    "venus": ("venus", "venera", "венера"),
    "earth": ("dunya", "earth", "erde", "terre", "tierra", "zemlya", "земля", "yerkure"),
    "moon": ("ay", "moon", "mond", "lune", "luna", "луна", "ayda", "aya", "ayi", "aydaki", "ayin"),
    "mars": ("mars", "марс", "kizil gezegen", "red planet"),
    "phobos": ("phobos", "fobos"),
    "deimos": ("deimos",),
    "ceres": ("ceres", "seres"),
    "jupiter": ("jupiter", "юпитер", "jupiter"),
    "io": ("io",),
    "europa": ("europa", "avrupa uydusu", "europe moon"),
    "ganymede": ("ganymede", "ganimede", "ganymed", "ganimedes"),
    "callisto": ("callisto", "kallisto", "calisto"),
    "saturn": ("saturn", "saturne", "saturno", "сатурн"),
    "titan": ("titan", "титан"),
    "enceladus": ("enceladus", "enselados", "encelade", "encelado"),
    "uranus": ("uranus", "uranus", "urano", "уран"),
    "neptune": ("neptun", "neptune", "neptuno", "нептун"),
    "triton": ("triton",),
    "pluto": ("pluton", "pluto", "плутон"),
}
# "ay" Türkçede "month" da demek; yalnız gök cismi bağlamında (ya da ekli biçimde) kabul et.
_AMBIG = {"ay", "sol", "io", "luna"}
_ALIAS_INDEX = sorted(((a, k) for k, al in BODY_ALIASES.items() for a in al), key=lambda x: -len(x[0]))


def find_bodies(norm):
    """Metinde geçen gök cisimleri (sırasıyla, tekrarsız)."""
    words = tokens(norm)
    found = []
    used = set()
    for alias, key in _ALIAS_INDEX:
        if " " in alias:
            i = norm.find(alias)
            if i >= 0 and key not in found:
                found.append((i, key))
            continue
        for wi, w in enumerate(words):
            if wi in used:
                continue
            ok = w == alias or (len(alias) >= 4 and stem(w) == alias) or (len(alias) >= 5 and w.startswith(alias))
            if ok and alias in _AMBIG and not _ambig_ok(alias, words, wi):
                continue
            if ok:
                used.add(wi)
                if key not in [k for _, k in found]:
                    found.append((norm.find(w), key))
    found.sort()
    return [k for _, k in found]


def _ambig_ok(alias, words, wi):
    ctx = set(words[max(0, wi - 3): wi + 4])
    space = {"gezegen", "uydu", "yuzey", "yercekimi", "cekim", "git", "gidis", "inis", "koloni", "us", "gravity", "surface",
             "land", "orbit", "yorunge", "kac", "ne", "nasil", "uzak", "uzaklik", "distance", "sicaklik", "temperature",
             "mission", "gorev", "transfer", "the", "dunya", "earth", "mars", "about", "hakkinda", "anlat", "tell",
             "facts", "bilgi", "gun", "day", "agirlik", "weight", "atmosfer", "atmosphere", "km", "radyo", "gecikme",
             "kacis", "hizi", "buyuk", "yaricap", "kutle", "kutlesi", "cap", "su", "buz", "gorevler", "tehlike", "apollo", "artemis"}
    if alias == "ay":
        return bool(ctx & space) or len(words) <= 2
    if alias == "sol":
        return False
    return bool(ctx & space) or len(words) <= 2


NUM_RX = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*(ton|t|kg|km/s|m/s|km|m|s|sn|saniye|seconds?|n|kn|mn)?\b")


def numbers(norm):
    """Sayılar ve (varsa) birimleri: [(değer, birim, önceki sözcük)]."""
    out = []
    for m in NUM_RX.finditer(norm):
        raw = m.group(1).replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            continue
        unit = m.group(2) or ""
        prev = norm[: m.start()].split()[-1:] or [""]
        out.append((v, unit, prev[0]))
    return out


def has_any(norm, words):
    tk = set(tokens(norm))
    st = set(stem(w) for w in tk)
    for w in words:
        if " " in w:
            if w in norm:
                return True
        elif w in tk or w in st:
            return True
    return False

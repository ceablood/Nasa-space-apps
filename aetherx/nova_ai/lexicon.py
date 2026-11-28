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
    "sun": ("gunes", "sun", "sonne", "soleil", "sol", "solntse", "солнце", "солнца"),
    "mercury": ("merkur", "mercury", "mercure", "mercurio", "меркурий", "меркурии", "меркурия"),
    "venus": ("venus", "venuskolonie", "venera", "венера", "венере", "венеры"),
    "earth": ("dunya", "earth", "erde", "terre", "tierra", "zemlya", "земля", "земли", "земле", "yerkure"),
    "moon": ("ay", "moon", "mond", "mondkolonie", "mondbasis", "lune", "luna", "луна", "луне", "луны", "ayda", "aya", "ayi", "aydaki", "ayin"),
    "mars": ("mars", "marskolonie", "марс", "марсе", "марса", "marte", "kizil gezegen", "red planet", "roter planet", "planete rouge", "planeta rojo",
             "красная планета"),
    "phobos": ("phobos", "fobos", "фобос"),
    "deimos": ("deimos", "деймос"),
    "ceres": ("ceres", "seres", "церер"),
    "jupiter": ("jupiter", "jupiterkolonie", "юпитер", "юпитере", "юпитера"),
    "io": ("io", "ио"),
    "europa": ("europa", "avrupa uydusu", "europe moon", "европа"),
    "ganymede": ("ganymede", "ganimede", "ganymed", "ganimedes", "ганимед"),
    "callisto": ("callisto", "kallisto", "calisto", "каллисто"),
    "saturn": ("saturn", "saturne", "saturno", "сатурн", "сатурне", "сатурна"),
    "titan": ("titan", "титан", "титане", "титана"),
    "enceladus": ("enceladus", "enselados", "encelade", "encelado", "энцелад"),
    "uranus": ("uranus", "urano", "уран", "уране", "урана"),
    "neptune": ("neptun", "neptune", "neptuno", "нептун", "нептуне", "нептуна"),
    "triton": ("triton", "тритон"),
    "pluto": ("pluton", "pluto", "плутон", "плутоне", "плутона"),
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
    if alias == "luna":                                  # İspanyolca/İtalyanca "la luna", "de la luna"
        return (wi > 0 and words[wi - 1] in ("la", "de", "del", "a")) or bool(ctx & space) or len(words) <= 2
    if alias == "sol":                                   # İspanyolca "el sol / del sol" (Güneş); Mars günü "sol" değil
        return wi > 0 and words[wi - 1] in ("el", "del", "al")
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


_DIGIT_EK = {"0": "ı", "1": "i", "2": "si", "3": "ü", "4": "ü", "5": "i", "6": "sı", "7": "si", "8": "i", "9": "u"}
_TENS_EK = {"1": "u", "2": "si", "3": "u", "4": "ı", "5": "si", "6": "ı", "7": "i", "8": "i", "9": "ı"}


def num_ek(num_text):
    """Türkçe sayı okunuşuna göre iyelik eki (3. tekil): '0,9' -> 'u' (dokuzu), '18,3' -> 'ü', '0,2' -> 'si', '40' -> 'ı'."""
    t = num_text.strip().replace(".", "")
    if "," in t:
        frac = t.split(",")[1].rstrip("0")
        if frac:
            return _DIGIT_EK[frac[-1]]
        t = t.split(",")[0]
    t = t.lstrip("-") or "0"
    if t.endswith("000"):
        return "i"                                   # bin
    if t.endswith("00") and len(t) > 2:
        return "ü"                                   # yüz
    if t[-1] != "0" or len(t) == 1:
        return _DIGIT_EK[t[-1]]
    return _TENS_EK[t[-2]]

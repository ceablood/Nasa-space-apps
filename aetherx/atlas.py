# -*- coding: utf-8 -*-
"""
AETHER-X // GEZEGEN ATLASI VERİSİ
Güneş, 8 gezegen, uydular (Satürn için 19 uydu ayrıntılı) ve Dünya'nın yapay
uyduları. Uzun bilgi metinleri üç dilde doğrudan burada tutulur.

Not: Uydu sayıları yeni keşiflerle sürekli değişir; buradaki değerler
2025 duyurularına dayanır ("+" işareti "en az" anlamındadır).
"""
import math

LANG_ORDER = ("tr", "en", "de", "fr", "es", "ru")
UNITS = {"km": ("km", "km", "km", "km", "km", "км"),
         "mkm": ("milyon km", "million km", "Mio. km", "millions de km", "millones de km", "млн км"),
         "bkm": ("milyar km", "billion km", "Mrd. km", "milliards de km", "miles de millones de km", "млрд км"),
         "d": ("gün", "days", "Tage", "jours", "días", "сут"),
         "y": ("yıl", "years", "Jahre", "ans", "años", "лет"),
         "h": ("saat", "hours", "Stunden", "heures", "horas", "ч"),
         "c": ("°C", "°C", "°C", "°C", "°C", "°C"),
         "g": ("m/s²", "m/s²", "m/s²", "m/s²", "m/s²", "м/с²"),
         "min": ("dakika", "minutes", "Minuten", "minutes", "minutos", "мин")}


def _fmt(v, dec, lang):
    s = f"{v:,.{dec}f}"
    if lang == "en":
        return s
    sep = "\u202f" if lang in ("fr", "ru") else "."            # fr/ru: ince boşluk; tr/de/es: nokta
    return s.replace(",", "§").replace(".", ",").replace("§", sep)


def U(v, unit, dec=0, suffix=None):
    out = {}
    for i, lang in enumerate(LANG_ORDER):
        out[lang] = f"{_fmt(v, dec, lang)} {UNITS[unit][i]}"
        if suffix:
            out[lang] += " " + suffix[i]
    return out


RETRO = ("(ters yönde)", "(retrograde)", "(rückläufig)", "(rétrograde)", "(retrógrado)", "(обратное)")
CATS = [("star", "YILDIZ"), ("rocky", "KAYAÇ GEZEGENLER"), ("gas", "GAZ GEZEGENLER")]


def M(key, name, tex, d, a, p, disp, rpx, year, by, info, inc=0.0, ph=0.0, lead=None, d_dec=0):
    """Uydu kaydı. disp: gezegen yarıçapı biriminde görüntü uzaklığı, rpx: görüntü yarıçapı (px)."""
    return {"key": key, "name": name, "tex": tex, "d": d, "a": a, "p": p, "disp": disp, "rpx": rpx, "year": year,
            "by": by, "info": info, "inc": inc, "ph": ph, "lead": lead, "kind": "moon"}


def S(key, name, disp, inc, p_min, alt, info, ph=0.0, n=1):
    """Yapay uydu kaydı."""
    return {"key": key, "name": name, "disp": disp, "inc": inc, "p": p_min / 1440.0, "alt": alt, "info": info,
            "ph": ph, "kind": "sat", "n": n, "rpx": 3}


SATURN_MOONS = [
    M("pan", "Pan", "ice", 28, 133584, 0.575, 2.216, 3, 1990, "Mark Showalter (Voyager 2)", {
        "tr": "Halkaların içindeki Encke Boşluğu'nda döner ve çekimiyle bu 325 km'lik boşluğu açık tutar; bu yüzden 'çoban uydu' denir. Ekvatorunda halka maddesinden biriken çıkıntı ona mantıya ya da cevize benzeyen bir görünüm verir.",
        "en": "Orbits inside the Encke Gap within the rings and keeps this 325 km wide gap open with its gravity, which makes it a 'shepherd moon'. A ridge of ring material piled up along its equator gives it a ravioli or walnut look.",
        "de": "Kreist in der Encke-Teilung inmitten der Ringe und hält diese 325 km breite Lücke durch seine Schwerkraft offen, weshalb er als „Hirtenmond“ gilt. Ein am Äquator aus Ringmaterial aufgeschütteter Wulst verleiht ihm das Aussehen einer Ravioli oder Walnuss."}),
    M("daphnis", "Daphnis", "ice", 8, 136505, 0.594, 2.265, 2, 2005, "Cassini", {
        "tr": "Yalnızca 8 km çapındadır ve A halkasının dış kenarına yakın Keeler Boşluğu'nda döner. Geçerken boşluğun kenarlarındaki halka maddesini dalgalandırır; bu dalgalar yaklaşık 1,5 km yüksekliğe ulaşır.",
        "en": "Only 8 km across, it orbits in the Keeler Gap near the outer edge of the A ring. As it passes, it raises waves along the edges of the gap that reach about 1.5 km in height.",
        "de": "Mit lediglich 8 km Durchmesser zieht er in der Keeler-Lücke nahe dem Außenrand des A-Rings seine Bahn. Im Vorüberziehen wirft er an den Rändern der Lücke Wellen auf, die rund 1,5 km hoch aufragen."}),
    M("atlas", "Atlas", "ice", 30, 137670, 0.602, 2.285, 3, 1980, "Voyager 1", {
        "tr": "A halkasının hemen dış kenarında döner. Ekvatorundaki geniş toz ve buz eteği ona uçan daireyi andıran bir biçim kazandırır.",
        "en": "Orbits just outside the A ring. A broad skirt of dust and ice around its equator gives it a flying-saucer shape.",
        "de": "Umläuft den Saturn unmittelbar außerhalb des A-Rings. Ein breiter Saum aus Staub und Eis entlang des Äquators verleiht ihm die Gestalt einer fliegenden Untertasse."}),
    M("prometheus", "Prometheus", "rock", 86, 139380, 0.613, 2.305, 4, 1980, "Voyager 1", {
        "tr": "İnce F halkasının iç çoban uydusudur. Her turda halkaya yaklaşıp içinden madde koparır ve halkada kanallar, düğümler bırakır.",
        "en": "The inner shepherd of the narrow F ring. On each orbit it approaches the ring, pulls material out of it and leaves channels and knots behind.",
        "de": "Der innere Hirtenmond des schmalen F-Rings. Bei jedem Umlauf nähert er sich dem Ring, entreißt ihm Material und hinterlässt darin Kanäle und Knoten."}),
    M("pandora", "Pandora", "ice", 81, 141720, 0.629, 2.36, 4, 1980, "Voyager 1", {
        "tr": "F halkasının hemen dışında döner. Uzun süre halkayı Prometheus ile birlikte çobanladığı düşünülmüştür; yüzeyi ince bir toz tabakasıyla örtülü olduğundan kraterleri yumuşak görünür.",
        "en": "Orbits just outside the F ring. It was long thought to shepherd the ring together with Prometheus; a fine blanket of dust softens the look of its craters.",
        "de": "Kreist knapp außerhalb des F-Rings. Lange nahm man an, er hüte den Ring gemeinsam mit Prometheus; eine feine Staubdecke lässt seine Krater weich gezeichnet erscheinen."}),
    M("epimetheus", "Epimetheus", "rock", 116, 151410, 0.694, 2.51, 4, 1966, "Richard Walker", {
        "tr": "Janus ile neredeyse aynı yörüngeyi paylaşır. İki uydu yaklaşık dört yılda bir birbirine yaklaşır, çekim etkisiyle yörüngelerini değiş tokuş eder ve çarpışmadan uzaklaşır.",
        "en": "Shares almost the same orbit as Janus. About every four years the two approach each other, swap orbits through their mutual gravity and move apart without colliding.",
        "de": "Teilt sich nahezu dieselbe Bahn mit Janus. Etwa alle vier Jahre nähern sich die beiden einander, tauschen infolge ihrer wechselseitigen Anziehung die Bahnen und entfernen sich wieder, ohne zu kollidieren."}, ph=2.6),
    M("janus", "Janus", "rock", 179, 151460, 0.695, 2.52, 5, 1966, "Audouin Dollfus", {
        "tr": "Epimetheus'un yörünge ortağıdır ve ikisinden büyük olanıdır. Yoğun biçimde kraterlidir; iki uydunun, parçalanmış tek bir cismin kalıntıları olduğu düşünülür.",
        "en": "The co-orbital partner of Epimetheus and the larger of the pair. It is heavily cratered; the two are thought to be remnants of a single body that broke apart.",
        "de": "Der koorbitale Partner des Epimetheus und der größere der beiden. Er ist dicht von Kratern bedeckt; man vermutet, dass beide Bruchstücke eines einzigen zerbrochenen Körpers sind."}),
    M("mimas", "Mimas", "mimas", 396, 185540, 0.942, 2.78, 7, 1789, "William Herschel", {
        "tr": "130 km çapındaki dev Herschel krateri yüzünden 'Ölüm Yıldızı'na benzetilir. Çekimi, halkalardaki Cassini Bölümü'nü temizler. Yörünge hareketindeki salınımlar, buz kabuğunun altında genç bir okyanus bulunabileceğine işaret eder.",
        "en": "Its giant 130 km Herschel crater earns it comparisons with the 'Death Star'. Its gravity clears the Cassini Division in the rings. Wobbles in its orbital motion suggest a young ocean may lie beneath its icy shell.",
        "de": "Der gewaltige, 130 km messende Herschel-Krater trägt ihm den Vergleich mit dem „Todesstern“ ein. Seine Schwerkraft fegt die Cassinische Teilung in den Ringen frei. Schwankungen seiner Bahnbewegung deuten darauf hin, dass sich unter dem Eispanzer ein junger Ozean verbergen könnte."}),
    M("enceladus", "Enceladus", "enceladus", 504, 238040, 1.370, 2.98, 8, 1789, "William Herschel", {
        "tr": "Güneş Sistemi'nin en parlak cisimlerindendir; üzerine düşen ışığın neredeyse tamamını yansıtır. Güney kutbundaki 'kaplan çizgileri'nden uzaya su buharı ve buz taneleri fışkırır; bu gayzerler E halkasını besler. Buz kabuğunun altındaki tuzlu okyanus, yaşam arayışının başlıca hedeflerindendir.",
        "en": "One of the brightest bodies in the Solar System, reflecting almost all the light that reaches it. Water vapour and ice grains erupt into space from the 'tiger stripes' at its south pole; these geysers feed the E ring. The salty ocean beneath its ice shell is a prime target in the search for life.",
        "de": "Einer der hellsten Körper des Sonnensystems, der nahezu das gesamte auftreffende Licht zurückwirft. Aus den „Tigerstreifen“ an seinem Südpol schießen Wasserdampf und Eispartikel ins All; diese Geysire speisen den E-Ring. Der salzhaltige Ozean unter seinem Eispanzer zählt zu den vorrangigen Zielen bei der Suche nach Leben."}),
    M("tethys", "Tethys", "ice", 1062, 294670, 1.888, 3.2, 10, 1684, "Giovanni Cassini", {
        "tr": "Neredeyse tamamen su buzundan oluşur. 445 km çapındaki Odysseus krateri ve uydunun dörtte üçünü dolanan 2.000 km uzunluğundaki Ithaca Chasma kanyonu en belirgin yüzey şekilleridir. Yörüngesini Telesto ve Calypso ile paylaşır.",
        "en": "Made almost entirely of water ice. The 445 km Odysseus crater and Ithaca Chasma, a 2,000 km canyon running three quarters of the way around the moon, are its most striking features. It shares its orbit with Telesto and Calypso.",
        "de": "Besteht nahezu vollständig aus Wassereis. Der 445 km große Odysseus-Krater und Ithaca Chasma, eine 2.000 km lange Schlucht, die drei Viertel des Mondes umspannt, sind seine markantesten Oberflächenformen. Seine Bahn teilt er sich mit Telesto und Calypso."}),
    M("telesto", "Telesto", "ice", 25, 294619, 1.888, 3.2, 3, 1980, "Smith, Reitsema, Larson, Fountain", {
        "tr": "Tethys'in yörüngesinde, ondan 60° önde (L4 Lagrange noktasında) döner; bu yüzden 'Truva uydusu' denir. Yüzeyi ince buz tozuyla kaplı olduğundan şaşırtıcı derecede pürüzsüzdür.",
        "en": "Travels along Tethys's orbit 60° ahead of it, at the L4 Lagrange point, which makes it a 'Trojan moon'. A coating of fine icy dust leaves its surface surprisingly smooth.",
        "de": "Läuft auf der Bahn der Tethys 60° vor ihr her, im Lagrange-Punkt L4, und gilt daher als „Trojanermond“. Eine Schicht feinen Eisstaubs lässt seine Oberfläche erstaunlich glatt erscheinen."},
      lead=("tethys", math.pi / 3)),
    M("calypso", "Calypso", "ice", 21, 294619, 1.888, 3.2, 3, 1980, "Pascu, Seidelmann, Baum, Currie", {
        "tr": "Tethys'in yörüngesinde, ondan 60° geride (L5 noktasında) döner. Telesto gibi pürüzsüz ve çok parlak bir yüzeyi vardır; E halkasından yağan buz taneleriyle kaplandığı düşünülür.",
        "en": "Travels along Tethys's orbit 60° behind it, at the L5 point. Like Telesto it has a smooth, very bright surface, thought to be coated by ice grains raining down from the E ring.",
        "de": "Folgt der Tethys auf deren Bahn im Abstand von 60°, im Punkt L5. Wie Telesto besitzt er eine glatte, überaus helle Oberfläche, die vermutlich von aus dem E-Ring herabrieselnden Eispartikeln überzogen ist."},
      lead=("tethys", -math.pi / 3)),
    M("dione", "Dione", "ice", 1123, 377420, 2.737, 3.45, 10, 1684, "Giovanni Cassini", {
        "tr": "Yoğun bir buz ve kaya karışımıdır. Arka yarım küresindeki parlak çizgiler, yüzlerce metre yüksekliğindeki buz yarlarıdır. İnce bir oksijen iyonu atmosferi saptanmıştır ve yüzeyinin altında okyanus bulunabileceği düşünülmektedir.",
        "en": "A dense mixture of ice and rock. The bright wisps on its trailing hemisphere are ice cliffs hundreds of metres high. A thin atmosphere of oxygen ions has been detected, and an ocean may lie beneath its surface.",
        "de": "Ein dichtes Gemenge aus Eis und Gestein. Die hellen Schlieren auf der rückwärtigen Hemisphäre sind mehrere hundert Meter hohe Eisklippen. Eine dünne Atmosphäre aus Sauerstoffionen wurde nachgewiesen, und unter der Oberfläche könnte ein Ozean liegen."}, ph=1.2),
    M("helene", "Helene", "ice", 35, 377396, 2.737, 3.45, 3, 1980, "Pierre Laques, Jean Lecacheux", {
        "tr": "Dione'nin yörüngesinde, ondan 60° önde döner. Yüzeyinde toz akıntılarının oluşturduğu oluklar görülür.",
        "en": "Travels along Dione's orbit 60° ahead of it. Its surface shows gullies carved by flows of dust.",
        "de": "Läuft auf der Bahn der Dione 60° vor ihr her. Seine Oberfläche zeigt Rinnen, die von Staubströmen gegraben wurden."},
      lead=("dione", math.pi / 3)),
    M("rhea", "Rhea", "ice", 1527, 527070, 4.518, 3.75, 12, 1672, "Giovanni Cassini", {
        "tr": "Satürn'ün ikinci büyük uydusudur. Yoğun kraterli, buzlu bir dünyadır; çevresinde oksijen ve karbondioksitten oluşan son derece ince bir atmosfer saptanmıştır.",
        "en": "Saturn's second-largest moon. A heavily cratered icy world around which an extremely thin atmosphere of oxygen and carbon dioxide has been detected.",
        "de": "Der zweitgrößte Mond des Saturn. Eine dicht verkraterte Eiswelt, in deren Umgebung eine äußerst dünne Atmosphäre aus Sauerstoff und Kohlendioxid nachgewiesen wurde."}, ph=4.0),
    M("titan", "Titan", "titan", 5150, 1221870, 15.945, 4.3, 20, 1655, "Christiaan Huygens", {
        "tr": "Güneş Sistemi'nin ikinci büyük uydusudur ve Merkür'den büyüktür. Kalın bir atmosferi olan tek uydudur: yüzey basıncı Dünya'dakinin 1,5 katıdır ve atmosfer büyük oranda azottan oluşur. Yüzeyinde sıvı metan ve etandan göller, denizler ve nehirler vardır. 2005'te Huygens sondası yüzeyine inmiştir; NASA'nın Dragonfly döner kanatlı aracı da buraya gönderilecektir.",
        "en": "The second-largest moon in the Solar System, bigger than Mercury. It is the only moon with a thick atmosphere: surface pressure is 1.5 times Earth's and the air is mostly nitrogen. Lakes, seas and rivers of liquid methane and ethane lie on its surface. The Huygens probe landed there in 2005, and NASA's Dragonfly rotorcraft is to be sent there as well.",
        "de": "Der zweitgrößte Mond des Sonnensystems, größer als der Merkur. Als einziger Mond besitzt er eine dichte Atmosphäre: Der Bodendruck beträgt das 1,5-Fache des irdischen, und die Lufthülle besteht überwiegend aus Stickstoff. Auf seiner Oberfläche finden sich Seen, Meere und Flüsse aus flüssigem Methan und Ethan. 2005 setzte die Sonde Huygens dort auf; auch der Drehflügler Dragonfly der NASA soll dorthin entsandt werden."}, ph=2.0),
    M("hyperion", "Hyperion", "rust", 270, 1481010, 21.28, 4.75, 6, 1848, "W. Bond, G. Bond, W. Lassell", {
        "tr": "Süngeri andıran, derin ve keskin kenarlı kraterlerle kaplı düzensiz bir cisimdir. Çok gözenekli olduğundan yoğunluğu suyun yaklaşık yarısı kadardır. Dönüşü kaotiktir: ekseni öngörülemez biçimde yalpalar.",
        "en": "An irregular body that looks like a sponge, covered in deep, sharp-rimmed craters. It is so porous that its density is about half that of water. Its rotation is chaotic: its axis tumbles unpredictably.",
        "de": "Ein unregelmäßig geformter Körper, der einem Schwamm gleicht und von tiefen, scharfkantigen Kratern übersät ist. Er ist derart porös, dass seine Dichte nur etwa die Hälfte jener des Wassers erreicht. Seine Rotation ist chaotisch: Die Achse taumelt auf unvorhersehbare Weise."}, ph=5.1),
    M("iapetus", "Iapetus", "iapetus", 1469, 3560820, 79.33, 5.35, 12, 1671, "Giovanni Cassini", {
        "tr": "İki yüzlü uydu: öndeki yarım küresi kömür gibi koyu, arkadaki yarım küresi kar gibi parlaktır. Ekvatoru boyunca uzanan ve yer yer 13 km'yi aşan sırt, ona ceviz görünümü verir.",
        "en": "The two-faced moon: its leading hemisphere is coal-dark while its trailing hemisphere is snow-bright. A ridge running along the equator, in places more than 13 km high, gives it a walnut shape.",
        "de": "Der Mond mit den zwei Gesichtern: Seine vorauseilende Hemisphäre ist kohlschwarz, die nachfolgende schneehell. Ein entlang des Äquators verlaufender, stellenweise über 13 km hoher Gebirgsrücken verleiht ihm die Gestalt einer Walnuss."}, inc=15.5, ph=0.7),
    M("phoebe", "Phoebe", "dark", 213, 12947780, -550.3, 6.1, 5, 1899, "William Pickering", {
        "tr": "Satürn'ün çevresinde ters yönde ve çok eğik bir yörüngede döner. Bu yüzden başka bir yerde oluşup sonradan Satürn'ün çekimine yakalandığı düşünülür. Yüzeyinden kopan koyu toz, dev ve soluk Phoebe halkasını oluşturur ve Iapetus'un ön yüzünü karartır.",
        "en": "Orbits Saturn backwards on a steeply tilted path, so it is thought to have formed elsewhere and been captured later by Saturn's gravity. Dark dust knocked off its surface forms the vast, faint Phoebe ring and darkens the leading face of Iapetus.",
        "de": "Umrundet den Saturn rückläufig auf stark geneigter Bahn; daher nimmt man an, dass er andernorts entstand und erst später von der Schwerkraft des Saturn eingefangen wurde. Von seiner Oberfläche abgeschlagener dunkler Staub bildet den riesigen, lichtschwachen Phoebe-Ring und schwärzt die Vorderseite des Iapetus."}, inc=28.0, ph=3.3),
]

EARTH_ORBITERS = [
    S("iss", {"tr": "UUİ (ISS)", "en": "ISS", "de": "ISS"}, 1.16, 51.6, 92.9, 420, {
        "tr": "Uluslararası Uzay İstasyonu. Yaklaşık 420 km yükseklikte, saatte 27.600 km hızla döner ve Dünya'nın çevresini 93 dakikada tamamlar; içinde 2000 yılından beri kesintisiz insan yaşıyor.",
        "en": "The International Space Station. At about 420 km altitude it travels at 27,600 km/h and circles Earth every 93 minutes; it has been continuously crewed since 2000.",
        "de": "Die Internationale Raumstation. In rund 420 km Höhe bewegt sie sich mit 27.600 km/h und umrundet die Erde in 93 Minuten; seit dem Jahr 2000 ist sie ununterbrochen bemannt."}),
    S("hubble", {"tr": "Hubble", "en": "Hubble", "de": "Hubble"}, 1.24, 28.5, 95, 525, {
        "tr": "Hubble Uzay Teleskobu. 1990'dan beri atmosferin üzerinden evreni gözlemliyor.",
        "en": "The Hubble Space Telescope. It has observed the universe from above the atmosphere since 1990.",
        "de": "Das Hubble-Weltraumteleskop. Seit 1990 beobachtet es das Universum von oberhalb der Atmosphäre."}, ph=2.0),
    S("imece", {"tr": "İMECE", "en": "İMECE", "de": "İMECE"}, 1.3, 98.0, 98, 680, {
        "tr": "Türkiye'nin yerli yer gözlem uydusu (2023). Kutuplardan geçen Güneş'e eş zamanlı yörüngede döner; böylece her bölgeyi hep aynı yerel saatte görüntüler.",
        "en": "Türkiye's domestically built Earth-observation satellite (2023). It flies a Sun-synchronous polar orbit, so it images each region at the same local time.",
        "de": "Der in der Türkei entwickelte Erdbeobachtungssatellit (2023). Er fliegt auf einer sonnensynchronen Polarbahn und nimmt daher jede Region stets zur selben Ortszeit auf."}, ph=4.0),
    S("gps", {"tr": "GPS uyduları", "en": "GPS satellites", "de": "GPS-Satelliten"}, 2.05, 55.0, 718, 20200, {
        "tr": "Konum belirleme uyduları. 20.200 km yükseklikte, Dünya'yı günde iki kez dolanırlar; telefonunuz en az dört uydudan sinyal alarak yerini hesaplar.",
        "en": "Navigation satellites. At 20,200 km altitude they circle Earth twice a day; your phone works out its position from the signals of at least four of them.",
        "de": "Navigationssatelliten. In 20.200 km Höhe umrunden sie die Erde zweimal täglich; Ihr Telefon errechnet seinen Standort aus den Signalen von mindestens vier Satelliten."}, n=4),
    S("turksat", {"tr": "Türksat 6A", "en": "Türksat 6A", "de": "Türksat 6A"}, 2.75, 0.0, 1436, 35786, {
        "tr": "Türkiye'nin ilk yerli haberleşme uydusu (2024). 35.786 km yükseklikteki yer sabit yörüngede Dünya ile aynı hızda döner; bu yüzden gökyüzünde hep aynı noktada durur.",
        "en": "Türkiye's first domestically built communications satellite (2024). In geostationary orbit at 35,786 km it turns at the same rate as Earth, so it stays fixed at one point in the sky.",
        "de": "Der erste in der Türkei gebaute Kommunikationssatellit (2024). Auf der geostationären Bahn in 35.786 km Höhe läuft er synchron mit der Erdrotation um und verharrt daher scheinbar an einem festen Punkt am Himmel."}, n=3),
]


def _moon(key, name, tex, d, a, p, disp, rpx, year, by, tr, en, de, **kw):
    return M(key, name, tex, d, a, p, disp, rpx, year, by, {"tr": tr, "en": en, "de": de}, **kw)


MOON = _moon("moon", {"tr": "Ay", "en": "Moon", "de": "Mond"}, "moon", 3474, 384400, 27.32, 4.4, 20, None, None,
             "Dünya'nın tek doğal uydusu ve gelgitlerin başlıca nedenidir. Dünya'ya hep aynı yüzünü gösterir. 1969-1972 arasında on iki insan yüzeyinde yürümüştür.",
             "Earth's only natural satellite and the main cause of the tides. It always shows the same face to Earth. Twelve people walked on its surface between 1969 and 1972.",
             "Der einzige natürliche Satellit der Erde und Hauptursache der Gezeiten. Er wendet der Erde stets dieselbe Seite zu. Zwischen 1969 und 1972 betraten zwölf Menschen seine Oberfläche.", inc=5.1)

OTHER_MOONS = {
    "mars": [
        _moon("phobos", "Phobos", "rock", 22, 9376, 0.319, 2.2, 5, 1877, "Asaph Hall",
              "Mars'a çok yakın döner ve her yüzyılda yaklaşık 2 metre alçalır; on milyonlarca yıl sonra parçalanıp bir halka oluşturması beklenir.",
              "Orbits very close to Mars and sinks about 2 metres each century; in tens of millions of years it is expected to break up into a ring.",
              "Umkreist den Mars in großer Nähe und sinkt je Jahrhundert um rund 2 Meter; in einigen zehn Millionen Jahren dürfte er zu einem Ring zerfallen."),
        _moon("deimos", "Deimos", "rock", 12, 23460, 1.263, 3.4, 4, 1877, "Asaph Hall",
              "Mars'ın küçük ve uzak uydusu. Yüzeyi kalın bir toz tabakasıyla örtülü olduğundan pürüzsüz görünür.",
              "The smaller, more distant moon of Mars. A thick layer of dust makes its surface look smooth.",
              "Der kleinere, fernere Marsmond. Eine mächtige Staubschicht lässt seine Oberfläche glatt erscheinen.", ph=2.5),
    ],
    "jupiter": [
        _moon("io", "Io", "io", 3643, 421700, 1.769, 2.3, 11, 1610, "Galileo Galilei",
              "Güneş Sistemi'nin volkanik olarak en etkin cismi: 400'den fazla etkin yanardağı vardır. Jüpiter'in gelgit kuvvetleri içini sürekli ısıtır.",
              "The most volcanically active body in the Solar System, with more than 400 active volcanoes. Jupiter's tidal forces constantly heat its interior.",
              "Der vulkanisch aktivste Körper des Sonnensystems mit über 400 tätigen Vulkanen. Die Gezeitenkräfte des Jupiter heizen sein Inneres unablässig auf."),
        _moon("europa", "Europa", "europa", 3122, 671000, 3.551, 3.0, 10, 1610, "Galileo Galilei",
              "Çatlaklarla kaplı buz kabuğunun altında Dünya'daki bütün okyanuslardan daha fazla su bulunduğu düşünülür. NASA'nın Europa Clipper aracı onu incelemek üzere yoldadır.",
              "Beneath its cracked ice shell there is thought to be more water than in all of Earth's oceans. NASA's Europa Clipper spacecraft is on its way to study it.",
              "Unter seinem von Rissen durchzogenen Eispanzer wird mehr Wasser vermutet als in sämtlichen Ozeanen der Erde. Die NASA-Sonde Europa Clipper ist zu seiner Erforschung unterwegs.", ph=1.5),
        _moon("ganymede", "Ganymede", "ganymede", 5268, 1070400, 7.155, 3.8, 15, 1610, "Galileo Galilei",
              "Güneş Sistemi'nin en büyük uydusudur; Merkür'den büyüktür ve kendi manyetik alanı olan tek uydudur.",
              "The largest moon in the Solar System, bigger than Mercury, and the only moon with its own magnetic field.",
              "Der größte Mond des Sonnensystems, größer als der Merkur, und der einzige Mond mit eigenem Magnetfeld.", ph=3.2),
        _moon("callisto", "Callisto", "callisto", 4821, 1882700, 16.689, 4.7, 14, 1610, "Galileo Galilei",
              "Güneş Sistemi'nin en yoğun kraterli yüzeylerinden birine sahiptir; yüzeyi yaklaşık 4 milyar yıldır neredeyse hiç değişmemiştir.",
              "It has one of the most heavily cratered surfaces in the Solar System, almost unchanged for about 4 billion years.",
              "Er besitzt eine der am dichtesten verkraterten Oberflächen des Sonnensystems, die seit rund 4 Milliarden Jahren nahezu unverändert geblieben ist.", ph=5.0),
    ],
    "uranus": [
        _moon("miranda", "Miranda", "ice", 472, 129900, 1.413, 2.5, 5, 1948, "Gerard Kuiper",
              "Yüzeyi yamalı bir bohça gibidir; 20 km yüksekliğindeki Verona Rupes, Güneş Sistemi'nin bilinen en yüksek uçurumudur.",
              "Its surface looks like a patchwork; the 20 km high Verona Rupes is the tallest known cliff in the Solar System.",
              "Seine Oberfläche gleicht einem Flickenteppich; die 20 km hohe Verona Rupes ist die höchste bekannte Steilwand des Sonnensystems."),
        _moon("ariel", "Ariel", "ice", 1158, 190900, 2.52, 3.0, 8, 1851, "William Lassell",
              "Uranüs'ün en parlak ve jeolojik olarak en genç yüzeyli büyük uydusudur.",
              "The brightest of Uranus's large moons, with the geologically youngest surface.",
              "Der hellste der großen Uranusmonde mit der geologisch jüngsten Oberfläche.", ph=1.0),
        _moon("umbriel", "Umbriel", "dark", 1169, 266000, 4.144, 3.5, 8, 1851, "William Lassell",
              "Uranüs'ün büyük uyduları arasında en koyu olanıdır; yüzeyi çok eski ve kraterlidir.",
              "The darkest of Uranus's large moons, with a very old, cratered surface.",
              "Der dunkelste der großen Uranusmonde mit einer sehr alten, verkraterten Oberfläche.", ph=2.2),
        _moon("titania", "Titania", "ice", 1577, 436300, 8.706, 4.1, 10, 1787, "William Herschel",
              "Uranüs'ün en büyük uydusudur; yüzeyinde dev kanyonlar ve fay hatları bulunur.",
              "The largest moon of Uranus; huge canyons and fault lines cross its surface.",
              "Der größte Uranusmond; gewaltige Schluchten und Verwerfungen durchziehen seine Oberfläche.", ph=3.6),
        _moon("oberon", "Oberon", "rust", 1523, 583500, 13.463, 4.7, 10, 1787, "William Herschel",
              "Uranüs'ün en dıştaki büyük uydusudur; eski, kraterli yüzeyinde koyu tabanlı kraterler görülür.",
              "The outermost large moon of Uranus; its old, cratered surface shows craters with dark floors.",
              "Der äußerste der großen Uranusmonde; seine alte, verkraterte Oberfläche weist Krater mit dunklen Böden auf.", ph=5.2),
    ],
    "neptune": [
        _moon("proteus", "Proteus", "dark", 420, 117600, 1.122, 2.4, 5, 1989, "Voyager 2",
              "Neptün'ün ikinci büyük uydusu; küre biçimini alamayacak kadar küçük, koyu ve köşeli bir cisimdir.",
              "Neptune's second-largest moon, a dark, angular body just too small to pull itself into a sphere.",
              "Der zweitgrößte Neptunmond, ein dunkler, kantiger Körper, der gerade zu klein ist, um Kugelgestalt anzunehmen."),
        _moon("triton", "Triton", "triton", 2707, 354800, -5.877, 3.4, 13, 1846, "William Lassell",
              "Büyük uydular arasında gezegeninin dönüşüne ters yönde dolanan tek uydudur; Kuiper Kuşağı'ndan yakalandığı düşünülür. Yüzeyinde azot gayzerleri vardır ve sıcaklık −235 °C'dir.",
              "The only large moon that orbits against its planet's rotation; it is thought to have been captured from the Kuiper Belt. Nitrogen geysers erupt on its surface, where the temperature is −235 °C.",
              "Der einzige große Mond, der entgegen der Rotation seines Planeten umläuft; vermutlich wurde er aus dem Kuipergürtel eingefangen. Auf seiner −235 °C kalten Oberfläche brechen Stickstoffgeysire aus.", inc=23.0, ph=1.4),
        _moon("nereid", "Nereid", "ice", 340, 5513800, 360.1, 4.9, 4, 1949, "Gerard Kuiper",
              "Güneş Sistemi'ndeki uydular arasında en basık yörüngelerden birine sahiptir: Neptün'e uzaklığı 1,4 ile 9,6 milyon km arasında değişir.",
              "It has one of the most elongated orbits of any moon: its distance from Neptune varies between 1.4 and 9.6 million km.",
              "Er besitzt eine der exzentrischsten Bahnen aller Monde: Sein Abstand zum Neptun schwankt zwischen 1,4 und 9,6 Millionen km.", inc=7.0, ph=4.0),
    ],
}


def B(key, name, cat, R, au, period, rot_h, tilt, obl, facts, info, moons=(), ring=None, count=None):
    """R: genel görünümde yarıçap (px), au: Güneş'e uzaklık, period: yıl, rot_h: dönüş (saat, eksi=ters)."""
    return {"key": key, "name": name, "cat": cat, "R": R, "au": au, "period": period, "rot": rot_h, "tilt": tilt,
            "obl": obl, "facts": facts, "info": info, "moons": list(moons), "ring": ring, "count": count}


BODIES = [
    B("sun", {"tr": "Güneş", "en": "Sun", "de": "Sonne"}, "star", 34, 0, 0, 609, 7.25, 1.0, [
        ("Tür", {"tr": "G2V sarı cüce yıldız", "en": "G2V yellow dwarf star", "de": "Gelber Zwergstern (G2V)"}),
        ("Çap", U(1392700, "km")), ("Yüzey sıcaklığı", U(5500, "c")),
        ("Çekirdek sıcaklığı", {"tr": "15 milyon °C", "en": "15 million °C", "de": "15 Mio. °C"}),
        ("Yaş", {"tr": "4,6 milyar yıl", "en": "4.6 billion years", "de": "4,6 Mrd. Jahre"}),
        ("Dönüş süresi", U(25.4, "d", 1))], {
        "tr": "Güneş, Güneş Sistemi'nin merkezindeki G tipi bir yıldızdır ve sistemin toplam kütlesinin %99,86'sını tek başına oluşturur. Çekirdeğinde her saniye yaklaşık 600 milyon ton hidrojen helyuma dönüşür; açığa çıkan enerji bütün gezegenleri aydınlatır ve ısıtır. Işığının Dünya'ya ulaşması yaklaşık 8 dakika 20 saniye sürer.",
        "en": "The Sun is a G-type star at the centre of the Solar System and holds 99.86% of the system's total mass. Every second its core fuses about 600 million tonnes of hydrogen into helium; the energy released lights and warms every planet. Its light takes about 8 minutes 20 seconds to reach Earth.",
        "de": "Die Sonne ist ein Stern des Spektraltyps G im Zentrum des Sonnensystems und vereint 99,86 % der Gesamtmasse des Systems auf sich. In ihrem Kern verschmelzen in jeder Sekunde rund 600 Millionen Tonnen Wasserstoff zu Helium; die dabei freigesetzte Energie erhellt und erwärmt sämtliche Planeten. Ihr Licht benötigt etwa 8 Minuten und 20 Sekunden bis zur Erde."}),
    B("mercury", {"tr": "Merkür", "en": "Mercury", "de": "Merkur"}, "rocky", 6, 0.387, 0.241, 1407.6, 0.03, 1.0, [
        ("Çap", U(4879, "km")), ("Güneş'e uzaklık", U(57.9, "mkm", 1)), ("Yörünge süresi", U(88, "d")),
        ("Dönüş süresi", U(58.6, "d", 1)), ("Uydu sayısı", "0"),
        ("Sıcaklık", {"tr": "−180 … 430 °C", "en": "−180 to 430 °C", "de": "−180 bis 430 °C"}),
        ("Yerçekimi", U(3.7, "g", 2))], {
        "tr": "Güneş'e en yakın ve en küçük gezegendir. Neredeyse hiç atmosferi olmadığından gündüz 430 °C'ye kadar ısınır, gece −180 °C'ye kadar soğur. Yüzeyi Ay'a benzer biçimde kraterlerle kaplıdır; 1.550 km çapındaki Caloris Havzası en büyük çarpma izidir.",
        "en": "The smallest planet and the closest to the Sun. With almost no atmosphere, it heats to 430 °C by day and cools to −180 °C at night. Its surface is cratered like the Moon; the 1,550 km wide Caloris Basin is its largest impact scar.",
        "de": "Der kleinste und sonnennächste Planet. Da er nahezu keine Atmosphäre besitzt, heizt er sich tagsüber auf bis zu 430 °C auf und kühlt nachts auf −180 °C ab. Seine Oberfläche ist, dem Mond vergleichbar, von Kratern übersät; das 1.550 km messende Caloris-Becken ist die größte Einschlagstruktur."}),
    B("venus", {"tr": "Venüs", "en": "Venus", "de": "Venus"}, "rocky", 10, 0.723, 0.615, -5832.5, 177.4, 1.0, [
        ("Çap", U(12104, "km")), ("Güneş'e uzaklık", U(108.2, "mkm", 1)), ("Yörünge süresi", U(224.7, "d", 1)),
        ("Dönüş süresi", U(243, "d", 0, RETRO)), ("Uydu sayısı", "0"), ("Sıcaklık", U(465, "c")),
        ("Yerçekimi", U(8.87, "g", 2))], {
        "tr": "Boyutça Dünya'nın ikizi sayılır, ancak yoğun karbondioksit atmosferi denetimsiz bir sera etkisi yaratır: 465 °C'lik yüzey sıcaklığıyla Güneş Sistemi'nin en sıcak gezegenidir. Yüzey basıncı Dünya'dakinin 92 katıdır. Kendi ekseni etrafında ters yönde ve çok yavaş döner; bir günü bir yılından uzundur.",
        "en": "Often called Earth's twin in size, but its dense carbon dioxide atmosphere drives a runaway greenhouse effect: at 465 °C it is the hottest planet in the Solar System. Surface pressure is 92 times that of Earth. It spins backwards and very slowly, so its day is longer than its year.",
        "de": "Der Größe nach gilt sie als Zwilling der Erde, doch ihre dichte Kohlendioxidatmosphäre bewirkt einen galoppierenden Treibhauseffekt: Mit 465 °C ist sie der heißeste Planet des Sonnensystems. Der Druck am Boden beträgt das 92-Fache des irdischen. Sie rotiert rückläufig und äußerst langsam, sodass ein Venustag länger währt als ein Venusjahr."}),
    B("earth", {"tr": "Dünya", "en": "Earth", "de": "Erde"}, "rocky", 11, 1.0, 1.0, 23.93, 23.44, 1.0, [
        ("Çap", U(12742, "km")), ("Güneş'e uzaklık", U(149.6, "mkm", 1)), ("Yörünge süresi", U(365.25, "d", 2)),
        ("Dönüş süresi", {"tr": "23 saat 56 dakika", "en": "23 h 56 min", "de": "23 Std. 56 Min."}),
        ("Uydu sayısı", {"tr": "1 doğal, binlerce yapay", "en": "1 natural, thousands artificial",
                         "de": "1 natürlicher, Tausende künstliche"}),
        ("Ortalama sıcaklık", U(15, "c")), ("Yerçekimi", U(9.81, "g", 2))], {
        "tr": "Yüzeyinde sıvı su ve yaşam bulunduğu bilinen tek gezegendir. Yüzeyinin %71'i okyanuslarla kaplıdır; azot ve oksijenden oluşan atmosferi ile manyetik alanı canlıları zararlı ışınımdan korur. Çevresinde tek doğal uydusu Ay'ın yanı sıra binlerce yapay uydu döner.",
        "en": "The only planet known to have liquid water on its surface and life. Oceans cover 71% of it; its nitrogen-oxygen atmosphere and magnetic field shield living things from harmful radiation. Besides its one natural moon, thousands of artificial satellites orbit it.",
        "de": "Der einzige Planet, von dem flüssiges Wasser an der Oberfläche und Leben bekannt sind. Ozeane bedecken 71 % seiner Oberfläche; die Stickstoff-Sauerstoff-Atmosphäre und das Magnetfeld schirmen die Lebewesen vor schädlicher Strahlung ab. Neben dem einzigen natürlichen Mond umkreisen ihn Tausende künstlicher Satelliten."},
      moons=EARTH_ORBITERS + [MOON]),
    B("mars", {"tr": "Mars", "en": "Mars", "de": "Mars"}, "rocky", 8, 1.524, 1.881, 24.62, 25.19, 1.0, [
        ("Çap", U(6779, "km")), ("Güneş'e uzaklık", U(227.9, "mkm", 1)), ("Yörünge süresi", U(687, "d")),
        ("Dönüş süresi", {"tr": "24 saat 37 dakika", "en": "24 h 37 min", "de": "24 Std. 37 Min."}),
        ("Uydu sayısı", "2"), ("Ortalama sıcaklık", U(-63, "c")), ("Yerçekimi", U(3.71, "g", 2))], {
        "tr": "Kızıl rengini yüzeyindeki demir oksitten alır. Güneş Sistemi'nin en yüksek yanardağı Olympus Mons (yaklaşık 22 km) ve 4.000 km uzunluğundaki Valles Marineris kanyonu buradadır. İnce atmosferinde zaman zaman bütün gezegeni saran toz fırtınaları çıkar. Kutuplarında su ve karbondioksit buzu bulunur.",
        "en": "Its red colour comes from iron oxide on the surface. It hosts Olympus Mons, the tallest volcano in the Solar System (about 22 km), and the 4,000 km long Valles Marineris canyon. Dust storms in its thin atmosphere sometimes engulf the whole planet. Its poles hold water and carbon dioxide ice.",
        "de": "Seine rote Färbung verdankt er dem Eisenoxid an der Oberfläche. Hier erheben sich Olympus Mons, der höchste Vulkan des Sonnensystems (rund 22 km), und das 4.000 km lange Canyonsystem Valles Marineris. In der dünnen Atmosphäre entstehen zuweilen Staubstürme, die den gesamten Planeten einhüllen. An den Polen lagern Wasser- und Kohlendioxideis."},
      moons=OTHER_MOONS["mars"]),
    B("jupiter", {"tr": "Jüpiter", "en": "Jupiter", "de": "Jupiter"}, "gas", 26, 5.203, 11.86, 9.93, 3.13, 0.935, [
        ("Çap", U(139820, "km")), ("Güneş'e uzaklık", U(778.5, "mkm", 1)), ("Yörünge süresi", U(11.86, "y", 2)),
        ("Dönüş süresi", {"tr": "9 saat 56 dakika", "en": "9 h 56 min", "de": "9 Std. 56 Min."}),
        ("Uydu sayısı", "115"), ("Bulut tepesi sıcaklığı", U(-145, "c")), ("Yerçekimi", U(24.79, "g", 2))], {
        "tr": "Güneş Sistemi'nin en büyük gezegenidir; kütlesi diğer bütün gezegenlerin toplamının iki katından fazladır. Hidrojen ve helyumdan oluşur, katı bir yüzeyi yoktur. Büyük Kırmızı Leke, en az 190 yıldır süren ve Dünya'dan büyük bir fırtınadır. Güçlü çekimi pek çok asteroiti yörüngesine hapseder (Truva asteroitleri).",
        "en": "The largest planet in the Solar System, with more than twice the mass of all the other planets combined. It is made of hydrogen and helium and has no solid surface. The Great Red Spot is a storm larger than Earth that has raged for at least 190 years. Its strong gravity traps many asteroids along its orbit (the Trojans).",
        "de": "Der größte Planet des Sonnensystems; seine Masse übertrifft die aller übrigen Planeten zusammen um mehr als das Doppelte. Er besteht aus Wasserstoff und Helium und besitzt keine feste Oberfläche. Der Große Rote Fleck ist ein Sturm, der größer als die Erde ist und seit mindestens 190 Jahren tobt. Seine gewaltige Schwerkraft bindet zahlreiche Asteroiden an seine Bahn (die Trojaner)."},
      moons=OTHER_MOONS["jupiter"]),
    B("saturn", {"tr": "Satürn", "en": "Saturn", "de": "Saturn"}, "gas", 22, 9.537, 29.45, 10.66, 26.73, 0.902, [
        ("Çap", U(116460, "km")), ("Güneş'e uzaklık", U(1.43, "bkm", 2)), ("Yörünge süresi", U(29.45, "y", 2)),
        ("Dönüş süresi", {"tr": "10 saat 33 dakika", "en": "10 h 33 min", "de": "10 Std. 33 Min."}),
        ("Uydu sayısı", "293"), ("Halka genişliği", U(280000, "km")), ("Bulut tepesi sıcaklığı", U(-178, "c")),
        ("Yerçekimi", U(10.44, "g", 2))], {
        "tr": "Halkalarıyla tanınan gaz devi. Halkalar, toz tanesinden ev büyüklüğüne kadar değişen milyarlarca buz ve kaya parçasından oluşur; her parça gezegenin çevresinde kendi yörüngesinde döner. Genişlikleri 280.000 km'yi bulsa da kalınlıkları çoğu yerde yalnızca onlarca metredir. Satürn'ün ortalama yoğunluğu sudan düşüktür. 2025'te 128, 2026'da onlarca yeni uydu duyurulmuş; Ağustos 2026 itibarıyla doğrulanmış uydu sayısı 293'tür.",
        "en": "The gas giant famous for its rings. The rings consist of billions of pieces of ice and rock, from dust grains to house-sized blocks, each on its own orbit around the planet. They span about 280,000 km yet are mostly only tens of metres thick. Saturn's average density is lower than that of water. After 128 new moons in 2025 and dozens more in 2026, it has 293 confirmed moons as of August 2026.",
        "de": "Der für seine Ringe berühmte Gasriese. Die Ringe bestehen aus Milliarden von Eis- und Gesteinsbrocken, vom Staubkorn bis zum hausgroßen Block, deren jeder den Planeten auf eigener Bahn umläuft. Sie erstrecken sich über rund 280.000 km, sind jedoch vielerorts nur einige Dutzend Meter dick. Die mittlere Dichte des Saturn liegt unter jener des Wassers. Nach 128 Neuentdeckungen im Jahr 2025 und Dutzenden weiteren 2026 zählt er mit Stand August 2026 insgesamt 293 bestätigte Monde."},
      moons=SATURN_MOONS, ring="saturn"),
    B("uranus", {"tr": "Uranüs", "en": "Uranus", "de": "Uranus"}, "gas", 15, 19.19, 84.02, -17.24, 97.77, 0.977, [
        ("Tür", {"tr": "Gaz gezegen (buz devi)", "en": "Gas planet (ice giant)", "de": "Gasplanet (Eisriese)"}),
        ("Çap", U(50724, "km")), ("Güneş'e uzaklık", U(2.87, "bkm", 2)), ("Yörünge süresi", U(84, "y")),
        ("Dönüş süresi", {"tr": "17 saat 14 dakika (ters yönde)", "en": "17 h 14 min (retrograde)",
                          "de": "17 Std. 14 Min. (rückläufig)"}),
        ("Uydu sayısı", "29"), ("Sıcaklık", U(-197, "c")), ("Yerçekimi", U(8.69, "g", 2))], {
        "tr": "Ekseni yaklaşık 98° yatık olduğundan yörüngesinde adeta yan yatmış olarak döner; kutupları 42 yıl gündüz, 42 yıl gece yaşar. Atmosferindeki metan ona soluk mavi-yeşil rengini verir. Gaz gezegenler arasında yer alır; su, amonyak ve metan buzları bakımından zengin olduğu için 'buz devi' olarak da adlandırılır. İnce ve koyu 13 halkası vardır.",
        "en": "Its axis is tilted about 98°, so it orbits practically on its side; each pole gets 42 years of daylight followed by 42 years of night. Methane in its atmosphere gives it a pale blue-green colour. It is grouped with the gas planets and, being rich in water, ammonia and methane ices, is also called an 'ice giant'. It has 13 thin, dark rings.",
        "de": "Seine Achse ist um rund 98° geneigt, sodass er gleichsam auf der Seite liegend um die Sonne läuft; an den Polen folgen auf 42 Jahre Tag 42 Jahre Nacht. Das Methan seiner Atmosphäre verleiht ihm die blassblaugrüne Färbung. Er zählt zu den Gasplaneten und wird, da er reich an Wasser-, Ammoniak- und Methaneis ist, auch als „Eisriese“ bezeichnet. Ihn umgeben 13 schmale, dunkle Ringe."},
      moons=OTHER_MOONS["uranus"], ring="uranus"),
    B("neptune", {"tr": "Neptün", "en": "Neptune", "de": "Neptun"}, "gas", 15, 30.07, 164.8, 16.11, 28.32, 0.983, [
        ("Tür", {"tr": "Gaz gezegen (buz devi)", "en": "Gas planet (ice giant)", "de": "Gasplanet (Eisriese)"}),
        ("Çap", U(49244, "km")), ("Güneş'e uzaklık", U(4.5, "bkm", 2)), ("Yörünge süresi", U(164.8, "y", 1)),
        ("Dönüş süresi", {"tr": "16 saat 6 dakika", "en": "16 h 6 min", "de": "16 Std. 6 Min."}),
        ("Uydu sayısı", "16"), ("Sıcaklık", U(-201, "c")), ("Yerçekimi", U(11.15, "g", 2))], {
        "tr": "Güneş'e en uzak gezegendir ve çıplak gözle görülemez; 1846'da yeri matematiksel hesaplarla öngörülerek keşfedilmiştir. Saatte 2.100 km'ye ulaşan rüzgârlarıyla Güneş Sistemi'nin en şiddetli fırtınalarına sahiptir. Uranüs gibi gaz gezegenler arasında sayılır ve 'buz devi' olarak da anılır. En büyük uydusu Triton ters yönde dolanır.",
        "en": "The most distant planet from the Sun and invisible to the naked eye; it was discovered in 1846 after its position was predicted mathematically. With winds reaching 2,100 km/h it has the fiercest storms in the Solar System. Like Uranus it is counted among the gas planets and is also known as an 'ice giant'. Its largest moon, Triton, orbits backwards.",
        "de": "Der sonnenfernste Planet, mit bloßem Auge nicht zu erkennen; er wurde 1846 entdeckt, nachdem man seine Position rechnerisch vorhergesagt hatte. Mit Windgeschwindigkeiten von bis zu 2.100 km/h weist er die heftigsten Stürme des Sonnensystems auf. Wie Uranus wird er den Gasplaneten zugerechnet und überdies als „Eisriese“ geführt. Sein größter Mond Triton umläuft ihn rückläufig."},
      moons=OTHER_MOONS["neptune"], ring="neptune"),
]
BODY = {b["key"]: b for b in BODIES}


def moon_facts(m):
    """Uydu / yapay uydu için bilgi satırları."""
    if m["kind"] == "sat":
        per = m["p"] * 1440
        return [("Yükseklik", U(m["alt"], "km")),
                ("Tur süresi", U(per, "min") if per < 200 else U(per / 60, "h", 1)),
                ("Yörünge eğikliği", f"{m['inc']:.1f}°")]
    rows = [("Çap", U(m["d"], "km")), ("Gezegene uzaklık", U(m["a"], "km")),
            ("Tur süresi", U(abs(m["p"]), "d", 2 if abs(m["p"]) < 10 else 1, RETRO if m["p"] < 0 else None))]
    if m.get("year"):
        rows.append(("Keşfedilme", f"{m['year']}, {m['by']}"))
    return rows

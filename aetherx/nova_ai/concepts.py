# -*- coding: utf-8 -*-
"""
NOVA SÖZLÜĞÜ — uzay ve roket kavramları (tr, en).
Her kavram: anahtar sözcükler (normalize edilmiş, aksansız küçük harf) + kısa açıklama + oyundaki karşılığı.
"""

# key: (anahtar sözcükler, (tr, en) açıklama, (tr, en) oyundaki karşılık ya da None)
CONCEPTS = {
    "delta_v": (("delta v", "deltav", "delta-v", "dv", "hiz degisimi", "hiz butcesi", "velocity change"),
                ("Delta-v (Δv), bir aracın motorlarıyla yapabileceği toplam hız değişimidir. Görev planlamanın para birimidir: "
                 "Dünya'dan alçak yörüngeye ~9,4 km/s, oradan Ay yüzeyine ~5,9 km/s gerekir.",
                 "Delta-v (Δv) is the total change in velocity a vehicle's engines can deliver. It is the currency of mission "
                 "planning: ~9.4 km/s from Earth to low orbit, then ~5.9 km/s more to the lunar surface."),
                ("Tasarım ekranındaki menzil ve yakıt değerleri bu fikre dayanır: daha fazla yakıt ve daha iyi motor = daha uzak hedef.",
                 "The range and fuel values in the rocket designer follow this idea: more fuel and a better engine reach farther targets.")),
    "isp": (("isp", "ozgul itki", "specific impulse", "verim motor"),
            ("Özgül itki (Isp), motorun yakıt verimidir; saniye cinsinden verilir. Kimyasal motorlar 250-450 s, iyon motorları "
             "1.500-4.000 s düzeyindedir. Isp ne kadar yüksekse aynı yakıtla o kadar çok Δv elde edilir.",
             "Specific impulse (Isp) measures engine fuel efficiency, in seconds. Chemical engines reach 250-450 s, ion "
             "thrusters 1,500-4,000 s. Higher Isp means more Δv from the same propellant."), None),
    "rocket_equation": (("roket denklemi", "tsiolkovsky", "ciolkovski", "rocket equation", "kutle orani", "mass ratio"),
                        ("Tsiolkovsky roket denklemi: Δv = Isp · g₀ · ln(m₀/m_f). m₀ dolu kütle, m_f boş kütledir. "
                         "Logaritma yüzünden Δv'yi ikiye katlamak, kütle oranının karesini almayı gerektirir; bu yüzden roketler kademelidir.",
                         "Tsiolkovsky rocket equation: Δv = Isp · g₀ · ln(m₀/m_f), with m₀ the full mass and m_f the dry mass. "
                         "Because of the logarithm, doubling Δv squares the required mass ratio, which is why rockets use stages."),
                        ("'Roket denklemi hesapla Isp 300 kütle 100 ton boş 30 ton' gibi sorarsan hesaplarım.",
                         "Ask e.g. 'rocket equation isp 300 mass 100 dry 30' and I will compute it.")),
    "twr": (("twr", "itki agirlik", "thrust to weight", "itki/agirlik", "kalkis gucu"),
            ("İtki/ağırlık oranı (TWR) 1'den büyük olmalı ki roket yerden kalksın. Fırlatmada genelde 1,2-1,5 seçilir; "
             "çok yüksek TWR aerodinamik yükleri artırır.",
             "Thrust-to-weight ratio (TWR) must exceed 1 to lift off. Launchers usually start at 1.2-1.5; a very high TWR "
             "raises aerodynamic loads."),
            ("Tasarım ekranında motor gücü yetersizse roket 'kalkamaz' uyarısı verir.",
             "In the designer, an underpowered engine triggers a 'cannot lift off' warning.")),
    "staging": (("kademe", "kademeleme", "staging", "stage", "ayrilma"),
                ("Kademeleme: boşalan yakıt tanklarını ve motorları atarak taşınan ölü kütleyi azaltmak. Saturn V üç, Falcon 9 iki kademelidir.",
                 "Staging: dropping empty tanks and engines to shed dead mass. Saturn V had three stages, Falcon 9 has two."), None),
    "max_q": (("max q", "maxq", "dinamik basinc", "dynamic pressure"),
              ("Max-Q, fırlatmada aerodinamik yükün en yüksek olduğu andır (genelde 10-14 km irtifa). Motorlar kısa süre kısılır.",
               "Max-Q is the moment of peak aerodynamic stress during launch (usually 10-14 km altitude). Engines are briefly throttled down."), None),
    "orbit": (("yorunge nedir", "yorunge", "orbit", "orbital", "yorungeye", "dolanma"),
              ("Yörünge, sürekli düşen ama yere hiç değmeyen bir harekettir: yatay hız, yere doğru düşüşü telafi edecek kadar büyüktür. "
               "Dünya'da 400 km'de bu hız ~7,7 km/s'dir.",
               "An orbit is continuous free fall that never hits the ground: horizontal speed matches the curvature of the drop. "
               "At 400 km above Earth that speed is ~7.7 km/s."), None),
    "escape": (("kacis hizi", "kacis", "escape velocity", "escape"),
               ("Kaçış hızı, bir cismin çekiminden itkisiz kurtulmak için gereken hızdır: v = √(2μ/r). Dünya'da 11,2 km/s, Ay'da 2,4 km/s.",
                "Escape velocity is the speed needed to leave a body's gravity without further thrust: v = √(2μ/r). 11.2 km/s on Earth, 2.4 km/s on the Moon."),
               None),
    "hohmann": (("hohmann", "transfer yorungesi", "transfer orbit", "gecis yorungesi"),
                ("Hohmann transferi, iki dairesel yörünge arasında en az yakıtlı iki ateşlemeli geçiştir. Dünya'dan Mars'a ~259 gün sürer.",
                 "A Hohmann transfer is the two-burn, minimum-fuel path between two circular orbits. Earth to Mars takes about 259 days."),
                ("'Dünya'dan Mars'a transfer' diye sorarsan süreyi ve Δv'yi hesaplarım.",
                 "Ask 'transfer Earth to Mars' and I will compute the time and Δv.")),
    "launch_window": (("firlatma penceresi", "pencere", "launch window", "window"),
                      ("Fırlatma penceresi, gezegenlerin doğru dizildiği ve transferin en ucuz olduğu dönemdir. Dünya-Mars pencereleri ~26 ayda bir açılır (sinodik dönem).",
                       "A launch window is when planets line up for the cheapest transfer. Earth-Mars windows open about every 26 months (the synodic period)."),
                      ("Oyunda fırlatma saati önemlidir: güneş fırtınası sırasında risk artar. 'En iyi fırlatma saati' sorusunu sorabilirsin.",
                       "In the game launch timing matters: risk rises during solar storms. Ask me for the best launch time.")),
    "gravity_assist": (("kutle cekim yardimi", "sapan", "gravity assist", "slingshot", "flyby"),
                       ("Kütle çekim yardımı: bir gezegenin yanından geçerken onun yörünge hızından pay alarak yakıtsız hız kazanmak. Voyager'lar dört gezegeni böyle dolaştı.",
                        "Gravity assist: stealing some of a planet's orbital momentum during a flyby to gain speed without fuel. The Voyagers toured four planets this way."),
                       None),
    "lagrange": (("lagrange", "l1", "l2", "lagrange noktasi"),
                 ("Lagrange noktaları, iki büyük cismin çekimlerinin dengelendiği beş noktadır. James Webb Teleskobu Güneş-Dünya L2'de, 1,5 milyon km uzaktadır.",
                  "Lagrange points are five spots where two large bodies' gravity balances. The James Webb Space Telescope sits at Sun-Earth L2, 1.5 million km away."),
                 None),
    "solar_flare": (("gunes firtinasi", "gunes patlamasi", "firtina", "solar flare", "solar storm", "cme", "koronal", "uzay havasi", "space weather"),
                    ("Güneş patlamaları saniyeler içinde X-ışını, koronal kütle atımları (CME) ise 1-3 günde Dünya'ya ulaşan yüklü parçacık bulutları gönderir. Uydu elektroniğine ve astronotlara zarar verebilir.",
                     "Solar flares deliver X-rays within minutes, while coronal mass ejections (CMEs) send charged particle clouds that reach Earth in 1-3 days. They can damage satellite electronics and harm astronauts."),
                    ("Oyunda fırtına sırasında fırlatmak riski artırır; NOVA Seviye 3 fırtınaları önceden gösterir.",
                     "In the game, launching during a storm raises risk; NOVA level 3 shows storms in advance.")),
    "radiation": (("radyasyon", "radiation", "isinim", "kozmik isin", "cosmic ray", "sievert"),
                  ("Uzayda iki ana radyasyon kaynağı vardır: galaktik kozmik ışınlar ve güneş parçacık olayları. ISS'teki astronotlar yılda ~150-250 mSv alır; Dünya'da ortalama ~3 mSv.",
                   "Space radiation comes mainly from galactic cosmic rays and solar particle events. ISS astronauts receive ~150-250 mSv per year, versus ~3 mSv on Earth."),
                  ("Kolonilerde sağlık ve sığınak binaları bu riski azaltır.",
                   "Medical and shelter buildings in colonies reduce this risk.")),
    "regolith": (("regolit", "regolith", "toprak", "toz"),
                 ("Regolit, kayalık yüzeyleri örten gevşek toz ve kırıntı katmanıdır. Ay regoliti keskin ve yapışkandır; radyasyon kalkanı ya da 3B baskı malzemesi olarak kullanılabilir.",
                  "Regolith is the loose dust and rubble covering rocky surfaces. Lunar regolith is sharp and clingy; it can serve as radiation shielding or 3D-printing feedstock."),
                 None),
    "isru": (("isru", "yerinde kaynak", "in situ", "kaynak kullanimi", "yerinde uretim"),
             ("ISRU (yerinde kaynak kullanımı): yakıtı, suyu, oksijeni hedefte üretmek. Örn. Mars'ta CO₂ + H₂O'dan metan ve oksijen (Sabatier süreci).",
              "ISRU (in-situ resource utilisation): making propellant, water and oxygen at the destination, e.g. methane and oxygen from Martian CO₂ and water (Sabatier process)."),
             ("Oyunda madenler (Ay Taşı, Kızıl Maden, Sülfür, Gaz) kolonilerde çıkarılıp depoya gelir ve satılabilir.",
              "In the game, minerals (Moon rock, red ore, sulfur, gas) are mined at colonies, stored and can be sold.")),
    "life_support": (("yasam destek", "life support", "eclss", "oksijen", "oxygen", "su geri donusum", "co2"),
                     ("Yaşam destek sistemleri havayı, suyu ve sıcaklığı yönetir. ISS suyun ~%98'ini geri kazanır; oksijen suyun elektroliziyle üretilir.",
                      "Life support manages air, water and temperature. The ISS recovers ~98% of its water; oxygen comes from electrolysing water."),
                     ("Kolonideki oksijen ve mutluluk değerleri bu sistemi temsil eder.",
                      "Colony oxygen and happiness values stand in for this system.")),
    "microgravity": (("mikro yercekimi", "agirliksizlik", "microgravity", "weightless", "kemik", "kas"),
                     ("Uzun süre ağırlıksızlıkta kemik ayda ~%1-1,5 yoğunluk kaybeder, kaslar zayıflar, görme bozulabilir. Astronotlar günde ~2 saat egzersiz yapar.",
                      "In long-term weightlessness bones lose ~1-1.5% density per month, muscles weaken and vision can change. Astronauts exercise about 2 hours a day."),
                     None),
    "reentry": (("geri donus", "atmosfere giris", "reentry", "re-entry", "isi kalkani", "heat shield"),
                ("Atmosfere girişte araç ~7,8 km/s hızını sürtünmeyle ısıya çevirir; ısı kalkanı 1.500 °C'nin üzerine çıkar. Ay dönüşlerinde hız ~11 km/s'dir.",
                 "During re-entry a vehicle turns ~7.8 km/s of speed into heat; the heat shield exceeds 1,500 °C. Lunar returns arrive at ~11 km/s."), None),
    "landing": (("inis", "landing", "suicide burn", "hover", "yumusak inis", "lander"),
                ("Havasız cisimlere iniş tamamen motorla yapılır: önce yörünge hızı öldürülür, sonra son metrelerde dikey hız sıfıra çekilir. "
                 "Mars'ta ince hava paraşüte yeter ama tek başına yetmez; Curiosity 'gökyüzü vinci' kullandı.",
                 "Landing on airless bodies is fully propulsive: first kill orbital speed, then null vertical speed in the last metres. "
                 "On Mars thin air helps a parachute but not enough; Curiosity used a 'sky crane'."),
                ("Oyundaki iniş modülünde dikey hızı 3 m/s'nin altında tut, eğimi düz tut ve yakıtı son metrelere sakla.",
                 "In the game's landing module, keep vertical speed under 3 m/s, stay level and save fuel for the final metres.")),
    "light_year": (("isik yili", "light year", "astronomik birim", "au", "parsek", "parsec"),
                   ("1 AU (astronomik birim) Dünya-Güneş ortalama uzaklığıdır: 149,6 milyon km. Işık yılı ~9,46 trilyon km'dir; parsek ~3,26 ışık yılı.",
                    "1 AU (astronomical unit) is the mean Earth-Sun distance: 149.6 million km. A light year is ~9.46 trillion km; a parsec ~3.26 light years."),
                   None),
    "exoplanet": (("otegezegen", "ote gezegen", "exoplanet", "habitable zone", "yasanabilir bolge", "kepler", "tess"),
                  ("Güneş dışındaki yıldızların gezegenlerine ötegezegen denir; 2024 itibarıyla 5.500'den fazlası doğrulandı. Yaşanabilir bölge, yüzeyde sıvı suyun mümkün olduğu uzaklık aralığıdır.",
                   "Planets orbiting other stars are exoplanets; over 5,500 were confirmed by 2024. The habitable zone is the distance range where surface liquid water is possible."),
                  None),
    "black_hole": (("kara delik", "black hole", "olay ufku", "event horizon"),
                   ("Kara delik, ışığın bile kaçamadığı kadar yoğun bir kütledir. 2019'da M87*'nin, 2022'de Samanyolu'nun merkezindeki Sgr A*'nın görüntüsü alındı (Event Horizon Telescope).",
                    "A black hole is mass so dense that not even light escapes. Images of M87* (2019) and the Milky Way's Sgr A* (2022) were captured by the Event Horizon Telescope."),
                   None),
    "ion_engine": (("iyon motoru", "ion engine", "ion thruster", "elektrikli itki", "hall"),
                   ("İyon motorları çok az itki ama çok yüksek verim (Isp 1.500-4.000 s) sağlar; aylarca çalışarak büyük Δv biriktirir. Dawn ~11 km/s Δv'yi böyle topladı.",
                    "Ion engines give tiny thrust but very high efficiency (Isp 1,500-4,000 s), running for months to build up large Δv. Dawn accumulated ~11 km/s this way."),
                   None),
    "nuclear": (("nukleer", "nuclear", "rtg", "radyoizotop", "fisyon", "kilopower"),
                ("RTG'ler plütonyum-238 bozunmasından elektrik üretir; Voyager, Curiosity ve Perseverance böyle çalışır. Nükleer termal roketler kimyasalın yaklaşık iki katı Isp hedefler.",
                 "RTGs turn plutonium-238 decay heat into electricity; Voyager, Curiosity and Perseverance run on them. Nuclear thermal rockets aim for about twice chemical Isp."),
                None),
    "solar_power": (("gunes paneli", "gunes enerjisi", "solar panel", "solar power", "enerji", "power"),
                    ("Güneş ışınımı uzaklığın karesiyle azalır: Dünya'da 1.361 W/m², Mars'ta ~590, Jüpiter'de ~50 W/m². Bu yüzden dış gezegenlerde nükleer güç tercih edilir.",
                     "Sunlight falls with the square of distance: 1,361 W/m² at Earth, ~590 at Mars, ~50 W/m² at Jupiter. That is why outer-planet missions prefer nuclear power."),
                    ("Oyunda gezegenin 'güneş' değeri panel verimini belirler; Jüpiter'de paneller zayıftır.",
                     "In the game a planet's 'sun' value sets panel output; panels are weak at Jupiter.")),
    "terraforming": (("terraform", "dunyalastirma", "terraforming"),
                     ("Dünyalaştırma, bir gezegeni insan için yaşanabilir kılma fikridir. Mars için atmosferi kalınlaştırmak gerekir ama bilinen CO₂ kaynakları bunun için yetersiz görünüyor (NASA, 2018).",
                      "Terraforming means making a planet habitable for humans. Mars would need a thicker atmosphere, but known CO₂ reservoirs appear insufficient (NASA, 2018)."),
                     None),
    "spacesuit": (("uzay giysisi", "spacesuit", "space suit", "eva", "uzay yuruyusu", "spacewalk"),
                  ("Uzay giysisi küçük bir uzay aracıdır: basınç, oksijen, soğutma ve mikrometeor koruması sağlar. ISS'teki EMU ~0,3 bar saf oksijenle çalışır.",
                   "A spacesuit is a small spacecraft providing pressure, oxygen, cooling and micrometeoroid protection. The ISS EMU runs at ~0.3 bar of pure oxygen."),
                  ("Oyunda AR-GE ekranındaki giysi geliştirmeleri hastalık ve yaralanma riskini azaltır.",
                   "In the game, suit upgrades in R&D lower sickness and injury risk.")),
    "astrobiology": (("yasam", "uzayli", "life", "alien", "astrobiyoloji", "astrobiology", "mikrop", "biyoimza"),
                     ("Henüz Dünya dışında yaşam bulunmadı. En güçlü adaylar: Mars'ın eski gölleri, Europa ve Enceladus'un yeraltı okyanusları, Titan'ın organik kimyası.",
                      "No life beyond Earth has been found yet. Top candidates: Mars' ancient lakes, the subsurface oceans of Europa and Enceladus, and Titan's organic chemistry."),
                     ("YAŞAM ekranındaki evrim simülasyonu bir oyun modelidir, gerçek bir bulguyu temsil etmez.",
                      "The evolution simulation on the LIFE screen is a game model, not a real discovery.")),
    "asteroid": (("asteroit", "asteroid", "kuyrukluyildiz", "comet", "meteor", "goktasi"),
                 ("Asteroitler kayalık, kuyrukluyıldızlar buzlu küçük cisimlerdir. DART (2022) bir asteroidin yörüngesini çarparak değiştirdi; OSIRIS-REx 2023'te Bennu'dan örnek getirdi.",
                  "Asteroids are rocky and comets icy small bodies. DART (2022) changed an asteroid's orbit by impact; OSIRIS-REx returned samples from Bennu in 2023."),
                 ("Uçuşta asteroit kuşakları ve enkaz bölgeleri hasar riski taşır.",
                  "During flight, asteroid belts and debris zones carry damage risk.")),
    "telescope": (("teleskop", "telescope", "james webb", "jwst", "hubble"),
                  ("Hubble 1990'dan beri yörüngede; James Webb 2021'de fırlatıldı ve kızılötesinde ilk gökadaları inceliyor.",
                   "Hubble has orbited since 1990; James Webb launched in 2021 and studies the first galaxies in infrared."), None),
    "reusable": (("yeniden kullanilabilir", "reusable", "booster inis", "falcon", "starship"),
                 ("Yeniden kullanılabilir roketler birinci kademeyi dikey indirip tekrar uçurarak maliyeti düşürür. Falcon 9 kademeleri 20'den fazla kez uçtu.",
                  "Reusable rockets land the first stage vertically and fly it again to cut cost. Falcon 9 boosters have flown more than 20 times."), None),
}


def find(norm_text):
    """Normalize edilmiş metinde geçen en uygun kavram (en uzun eşleşme)."""
    best, best_len = None, 0
    for key, (kws, _, _) in CONCEPTS.items():
        for kw in kws:
            if len(kw) > best_len and _contains(norm_text, kw):
                best, best_len = key, len(kw)
    return best


def _contains(text, kw):
    if " " in kw or len(kw) > 4:
        return kw in text
    return kw in text.split()

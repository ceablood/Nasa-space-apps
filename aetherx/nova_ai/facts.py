# -*- coding: utf-8 -*-
"""
NOVA BİLGİ TABANI — GÖK CİSİMLERİ (gerçek veri)
Kaynak: NASA Goddard "Planetary Fact Sheet" (nssdc.gsfc.nasa.gov/planetary/factsheet) ve ilgili uydu sayfaları.
Uydu sayıları zamanla değişir; değerler 2024 itibarıyla kabul edilmiş sayılardır.
Oyundaki gezegen verileri (data.py: risk, maden, koloni maliyeti) OYUN KURALIDIR; burası gerçek astronomidir.

Alanlar:
  mass      kütle (10^24 kg)              radius   ortalama yarıçap (km)
  g         yüzey çekimi (m/s²)           esc      kaçış hızı (km/s)
  day       güneş günü (saat)             year     yörünge periyodu (Dünya günü)
  a_au      Güneş'e ortalama uzaklık (AU) — uydularda ana gezegeninki
  temp      ortalama yüzey/bulut tepesi sıcaklığı (°C)
  p_bar     yüzey basıncı (bar; gaz devlerinde None)
  moons     bilinen doğal uydu sayısı
  atm       atmosfer bileşimi (tr, en)
  parent    uydular için ana gezegen
"""

BODIES = {
    "sun": dict(name=("Güneş", "Sun"), kind="star", mass=1988500.0, radius=695700.0, g=274.0, esc=617.6, day=609.12,
                year=None, a_au=0.0, temp=5500, p_bar=None, moons=0,
                atm=("%73 hidrojen, %25 helyum (kütlece)", "73% hydrogen, 25% helium (by mass)")),
    "mercury": dict(name=("Merkür", "Mercury"), kind="planet", mass=0.330, radius=2439.7, g=3.7, esc=4.3, day=4222.6,
                    year=88.0, a_au=0.387, temp=167, p_bar=0.0, moons=0,
                    atm=("Neredeyse yok (çok ince ekzosfer: O, Na, H, He)", "Almost none (thin exosphere: O, Na, H, He)")),
    "venus": dict(name=("Venüs", "Venus"), kind="planet", mass=4.87, radius=6051.8, g=8.9, esc=10.4, day=2802.0,
                  year=224.7, a_au=0.723, temp=464, p_bar=92.0, moons=0,
                  atm=("%96,5 karbondioksit, %3,5 azot; sülfürik asit bulutları", "96.5% carbon dioxide, 3.5% nitrogen; sulfuric acid clouds")),
    "earth": dict(name=("Dünya", "Earth"), kind="planet", mass=5.97, radius=6371.0, g=9.8, esc=11.2, day=24.0,
                  year=365.2, a_au=1.0, temp=15, p_bar=1.0, moons=1,
                  atm=("%78 azot, %21 oksijen, %0,9 argon", "78% nitrogen, 21% oxygen, 0.9% argon")),
    "moon": dict(name=("Ay", "Moon"), kind="moon", parent="earth", mass=0.073, radius=1737.4, g=1.6, esc=2.4, day=708.7,
                 year=27.3, a_au=1.0, temp=-20, p_bar=0.0, moons=0, orbit_km=384400,
                 atm=("Yok denecek kadar ince ekzosfer", "Practically none (tenuous exosphere)")),
    "mars": dict(name=("Mars", "Mars"), kind="planet", mass=0.642, radius=3389.5, g=3.7, esc=5.0, day=24.7,
                 year=687.0, a_au=1.524, temp=-65, p_bar=0.006, moons=2,
                 atm=("%95 karbondioksit, %2,8 azot, %2 argon; çok ince", "95% carbon dioxide, 2.8% nitrogen, 2% argon; very thin")),
    "phobos": dict(name=("Phobos", "Phobos"), kind="moon", parent="mars", mass=1.07e-8, radius=11.1, g=0.0057, esc=0.011,
                   day=7.65, year=0.319, a_au=1.524, temp=-40, p_bar=0.0, moons=0, orbit_km=9376,
                   atm=("Yok", "None")),
    "deimos": dict(name=("Deimos", "Deimos"), kind="moon", parent="mars", mass=1.5e-9, radius=6.2, g=0.003, esc=0.0056,
                   day=30.3, year=1.263, a_au=1.524, temp=-40, p_bar=0.0, moons=0, orbit_km=23463,
                   atm=("Yok", "None")),
    "ceres": dict(name=("Ceres", "Ceres"), kind="dwarf", mass=0.000939, radius=469.7, g=0.28, esc=0.51, day=9.07,
                  year=1682.0, a_au=2.77, temp=-105, p_bar=0.0, moons=0,
                  atm=("Yok (geçici su buharı izleri)", "None (transient water vapour traces)")),
    "jupiter": dict(name=("Jüpiter", "Jupiter"), kind="planet", mass=1898.0, radius=69911.0, g=23.1, esc=59.5, day=9.9,
                    year=4331.0, a_au=5.203, temp=-110, p_bar=None, moons=95,
                    atm=("%90 hidrojen, %10 helyum; amonyak bulutları", "90% hydrogen, 10% helium; ammonia clouds")),
    "io": dict(name=("İo", "Io"), kind="moon", parent="jupiter", mass=0.0893, radius=1821.6, g=1.80, esc=2.56, day=42.5,
               year=1.77, a_au=5.203, temp=-143, p_bar=0.0, moons=0, orbit_km=421700,
               atm=("Çok ince kükürt dioksit", "Very thin sulfur dioxide")),
    "europa": dict(name=("Europa", "Europa"), kind="moon", parent="jupiter", mass=0.0480, radius=1560.8, g=1.31, esc=2.03,
                   day=85.2, year=3.55, a_au=5.203, temp=-160, p_bar=0.0, moons=0, orbit_km=671100,
                   atm=("Çok ince oksijen", "Very thin oxygen")),
    "ganymede": dict(name=("Ganymede", "Ganymede"), kind="moon", parent="jupiter", mass=0.148, radius=2634.1, g=1.43, esc=2.74,
                     day=171.7, year=7.15, a_au=5.203, temp=-163, p_bar=0.0, moons=0, orbit_km=1070400,
                     atm=("Çok ince oksijen", "Very thin oxygen")),
    "callisto": dict(name=("Kallisto", "Callisto"), kind="moon", parent="jupiter", mass=0.108, radius=2410.3, g=1.24, esc=2.44,
                     day=400.5, year=16.7, a_au=5.203, temp=-139, p_bar=0.0, moons=0, orbit_km=1882700,
                     atm=("Çok ince karbondioksit", "Very thin carbon dioxide")),
    "saturn": dict(name=("Satürn", "Saturn"), kind="planet", mass=568.0, radius=58232.0, g=9.0, esc=35.5, day=10.7,
                   year=10747.0, a_au=9.537, temp=-140, p_bar=None, moons=146,
                   atm=("%96 hidrojen, %3 helyum", "96% hydrogen, 3% helium")),
    "titan": dict(name=("Titan", "Titan"), kind="moon", parent="saturn", mass=0.1345, radius=2574.7, g=1.35, esc=2.64, day=382.7,
                  year=15.9, a_au=9.537, temp=-179, p_bar=1.5, moons=0, orbit_km=1221870,
                  atm=("%95 azot, %5 metan; kalın turuncu pus", "95% nitrogen, 5% methane; thick orange haze")),
    "enceladus": dict(name=("Enceladus", "Enceladus"), kind="moon", parent="saturn", mass=0.000108, radius=252.1, g=0.113,
                      esc=0.239, day=32.9, year=1.37, a_au=9.537, temp=-198, p_bar=0.0, moons=0, orbit_km=237948,
                      atm=("Güney kutbundan su buharı püskürmeleri", "Water vapour plumes from the south pole")),
    "uranus": dict(name=("Uranüs", "Uranus"), kind="planet", mass=86.8, radius=25362.0, g=8.7, esc=21.3, day=17.2,
                   year=30589.0, a_au=19.19, temp=-195, p_bar=None, moons=28,
                   atm=("%83 hidrojen, %15 helyum, %2 metan", "83% hydrogen, 15% helium, 2% methane")),
    "neptune": dict(name=("Neptün", "Neptune"), kind="planet", mass=102.0, radius=24622.0, g=11.0, esc=23.5, day=16.1,
                    year=59800.0, a_au=30.07, temp=-200, p_bar=None, moons=16,
                    atm=("%80 hidrojen, %19 helyum, %1,5 metan", "80% hydrogen, 19% helium, 1.5% methane")),
    "triton": dict(name=("Triton", "Triton"), kind="moon", parent="neptune", mass=0.0214, radius=1353.4, g=0.78, esc=1.46,
                   day=141.0, year=5.88, a_au=30.07, temp=-235, p_bar=0.000014, moons=0, orbit_km=354759,
                   atm=("Çok ince azot", "Very thin nitrogen")),
    "pluto": dict(name=("Plüton", "Pluto"), kind="dwarf", mass=0.0130, radius=1188.3, g=0.62, esc=1.21, day=153.3,
                  year=90560.0, a_au=39.48, temp=-225, p_bar=0.00001, moons=5,
                  atm=("Çok ince azot, metan, karbonmonoksit", "Very thin nitrogen, methane, carbon monoxide")),
}

# Öne çıkan bilgiler (tr, en) — her biri doğrulanabilir genel bilgi.
NOTES = {
    "sun": [("Güneş, Güneş Sistemi'nin kütlesinin yaklaşık %99,86'sını taşır.", "The Sun holds about 99.86% of the Solar System's mass."),
            ("Işığı Dünya'ya yaklaşık 8 dakika 20 saniyede ulaşır.", "Its light reaches Earth in about 8 minutes 20 seconds."),
            ("Güneş patlamaları ve koronal kütle atımları uzay havasının kaynağıdır.", "Solar flares and coronal mass ejections drive space weather.")],
    "mercury": [("Güneş'e en yakın ve en küçük gezegendir.", "It is the smallest planet and the closest to the Sun."),
                ("Bir Merkür günü (güneş doğuşundan doğuşa) 176 Dünya günü sürer; yılından uzundur.", "One solar day on Mercury lasts 176 Earth days, longer than its year."),
                ("Kutuplardaki kalıcı gölgeli kraterlerde su buzu bulunur (MESSENGER).", "Permanently shadowed polar craters hold water ice (MESSENGER).")],
    "venus": [("Yüzeyi kurşunu eritecek kadar sıcaktır: ~464 °C; sera etkisinin uç örneğidir.", "Its surface is hot enough to melt lead: ~464 °C, an extreme greenhouse effect."),
              ("Yüzey basıncı Dünya'nın ~92 katıdır, okyanusta ~900 m derinliğe eşdeğer.", "Surface pressure is ~92 times Earth's, like being ~900 m under the ocean."),
              ("Çoğu gezegenin tersine, ters yönde (retrograd) döner.", "It spins backwards (retrograde) compared with most planets."),
              ("Yaklaşık 50 km yükseklikte sıcaklık ve basınç Dünya'ya benzer; bulut şehri fikirleri buradan gelir.", "At about 50 km altitude temperature and pressure are Earth-like, which inspires cloud-city concepts.")],
    "earth": [("Yüzeyinde sıvı su ve bilinen tek yaşam barındıran gezegendir.", "The only known world with surface liquid water and life."),
              ("Manyetik alanı Güneş rüzgârını saptırır.", "Its magnetic field deflects the solar wind.")],
    "moon": [("Hep aynı yüzünü gösterir (kütleçekimsel kilitlenme).", "It always shows the same face (tidally locked)."),
             ("Apollo 11 ile 1969'da insanlar ilk kez Ay'a yürüdü.", "Humans first walked on the Moon with Apollo 11 in 1969."),
             ("Güney kutbu kraterlerindeki su buzu gelecekteki üsler için kritik kaynaktır.", "Water ice in south-polar craters is a key resource for future bases."),
             ("Gece-gündüz sıcaklığı yaklaşık +120 °C ile −130 °C arasında değişir.", "Surface temperature swings from about +120 °C by day to −130 °C at night.")],
    "mars": [("Olympus Mons ~22 km yüksekliğiyle Güneş Sistemi'nin en büyük yanardağıdır.", "Olympus Mons, ~22 km high, is the largest volcano in the Solar System."),
             ("Gün uzunluğu Dünya'ya çok yakındır: 24 saat 37 dakika (sol).", "Its day is very close to Earth's: 24 h 37 min (a sol)."),
             ("Kutuplarında su buzu ve kuru buz (CO₂) vardır.", "Its polar caps contain water ice and dry ice (CO₂)."),
             ("Perseverance'ın MOXIE deneyi Mars havasından oksijen üretti (2021-2023).", "Perseverance's MOXIE experiment produced oxygen from Martian air (2021-2023)."),
             ("Küresel toz fırtınaları güneş panellerini aylarca karartabilir.", "Global dust storms can dim solar panels for months.")],
    "phobos": [("Mars'a yaklaşıyor; on milyonlarca yıl içinde parçalanıp halka olabilir.", "It is spiralling inward and may break into a ring within tens of millions of years.")],
    "deimos": [("Mars'ın iki uydusundan küçük ve dış olanıdır.", "The smaller and outer of Mars' two moons.")],
    "ceres": [("Asteroit kuşağının en büyük cismi ve bir cüce gezegendir.", "The largest object in the asteroid belt and a dwarf planet."),
              ("Occator kraterindeki parlak lekeler tuz (sodyum karbonat) birikintisidir (Dawn).", "Bright spots in Occator crater are salt (sodium carbonate) deposits (Dawn).")],
    "jupiter": [("En büyük gezegendir; diğer tüm gezegenlerin toplam kütlesinin 2,5 katıdır.", "The largest planet, 2.5 times the mass of all other planets combined."),
                ("Büyük Kırmızı Leke, Dünya'dan büyük, yüzyıllardır süren bir fırtınadır.", "The Great Red Spot is a storm larger than Earth that has lasted for centuries."),
                ("Çevresindeki radyasyon kuşakları insanlı görevler için ölümcüldür.", "Its radiation belts are lethal for crewed missions."),
                ("Katı bir yüzeyi yoktur; 'iniş' ancak uydularına yapılabilir.", "It has no solid surface; landings are only possible on its moons.")],
    "io": [("Güneş Sistemi'nin volkanik olarak en etkin cismidir; 400'den fazla aktif yanardağ.", "The most volcanically active body in the Solar System, with over 400 active volcanoes.")],
    "europa": [("Buz kabuğunun altında Dünya okyanuslarından fazla su içeren tuzlu bir okyanus olduğu düşünülüyor.", "A salty ocean holding more water than Earth's oceans is thought to lie beneath its ice shell."),
               ("Europa Clipper Ekim 2024'te fırlatıldı; 2030'da varması bekleniyor.", "Europa Clipper launched in October 2024 and is due to arrive in 2030.")],
    "ganymede": [("Güneş Sistemi'nin en büyük uydusudur, Merkür'den büyüktür ve kendi manyetik alanı vardır.", "The largest moon in the Solar System, bigger than Mercury, with its own magnetic field.")],
    "callisto": [("Yüzeyi Güneş Sistemi'nin en yoğun kraterli yüzeylerinden biridir.", "Its surface is one of the most heavily cratered in the Solar System."),
                 ("Jüpiter'in radyasyon kuşaklarının dışında kaldığı için üs adayı olarak önerilir.", "It lies outside Jupiter's main radiation belts, so it is proposed as a base site.")],
    "saturn": [("Yoğunluğu sudan düşüktür (~0,69 g/cm³).", "Its density is lower than water (~0.69 g/cm³)."),
               ("Halkaları çoğunlukla su buzundan oluşur ve ~280.000 km genişliğe yayılır.", "Its rings are mostly water ice and span about 280,000 km."),
               ("Cassini 2004-2017 arasında Satürn'ün yörüngesinde kaldı.", "Cassini orbited Saturn from 2004 to 2017.")],
    "titan": [("Yoğun atmosferi olan tek uydudur; yüzey basıncı Dünya'nın ~1,5 katıdır.", "The only moon with a dense atmosphere; surface pressure is ~1.5 times Earth's."),
              ("Yüzeyinde sıvı metan ve etandan göller ve denizler vardır.", "It has lakes and seas of liquid methane and ethane."),
              ("Huygens sondası 2005'te Titan'a indi; Dragonfly helikopteri 2028'de fırlatılacak.", "The Huygens probe landed on Titan in 2005; the Dragonfly rotorcraft is set to launch in 2028."),
              ("Düşük çekim ve kalın hava sayesinde insan kanat takıp uçabilir.", "Low gravity and thick air mean a person could fly with strapped-on wings.")],
    "enceladus": [("Güney kutbundaki çatlaklardan uzaya su buzu püskürür (Cassini, 2005).", "Water-ice plumes erupt into space from cracks at its south pole (Cassini, 2005)."),
                  ("Püskürmelerde tuz, silika ve organik moleküller bulundu; yaşanabilirlik adayıdır.", "The plumes contain salts, silica and organic molecules; it is a habitability candidate.")],
    "uranus": [("Ekseni ~98° eğiktir; adeta yan yatarak döner.", "Its axis is tilted about 98°, so it rolls on its side."),
               ("Yalnızca Voyager 2 (1986) ziyaret etti.", "Only Voyager 2 has visited it (1986).")],
    "neptune": [("Güneş Sistemi'nin en hızlı rüzgârları buradadır: ~2.100 km/sa.", "It has the fastest winds in the Solar System: ~2,100 km/h."),
                ("Matematiksel hesapla bulunan ilk gezegendir (1846).", "The first planet found by mathematical prediction (1846).")],
    "triton": [("Gezegeninin dönüşüne ters yönde dolanır; muhtemelen yakalanmış bir Kuiper kuşağı cismidir.", "It orbits backwards and is probably a captured Kuiper Belt object."),
               ("Voyager 2 yüzeyinde azot gayzerleri gördü.", "Voyager 2 saw nitrogen geysers on its surface.")],
    "pluto": [("2006'da cüce gezegen olarak yeniden sınıflandırıldı.", "It was reclassified as a dwarf planet in 2006."),
              ("New Horizons 2015'te yanından geçti; kalp biçimli azot buzu ovası Sputnik Planitia'yı görüntüledi.", "New Horizons flew by in 2015 and imaged Sputnik Planitia, a heart-shaped plain of nitrogen ice.")],
}

# Önemli görevler: (yıl, ad, (tr açıklama, en açıklama))
MISSIONS = {
    "sun": [(2018, "Parker Solar Probe", ("Güneş'e en çok yaklaşan araç; 2024'te koronanın 6,1 milyon km yakınından geçti.", "The closest spacecraft to the Sun; passed 6.1 million km from it in 2024.")),
            (2020, "Solar Orbiter", ("Güneş'in kutup bölgelerini ilk kez görüntüleyen ESA/NASA görevi.", "ESA/NASA mission that imaged the Sun's polar regions for the first time.")),
            (1995, "SOHO", ("Güneş'i kesintisiz gözleyen ve binlerce kuyrukluyıldız keşfeden gözlemevi.", "Observatory watching the Sun continuously; discovered thousands of comets."))],
    "mercury": [(1974, "Mariner 10", ("Merkür'ün yanından geçen ilk araç.", "First spacecraft to fly past Mercury.")),
                (2011, "MESSENGER", ("Merkür yörüngesine giren ilk araç (2011-2015).", "First spacecraft to orbit Mercury (2011-2015).")),
                (2018, "BepiColombo", ("ESA/JAXA görevi; Merkür yörüngesine girişi 2026 sonu olarak planlandı.", "ESA/JAXA mission; Mercury orbit insertion planned for late 2026."))],
    "venus": [(1970, "Venera 7", ("Başka bir gezegenin yüzeyinden veri gönderen ilk araç.", "First craft to send data from another planet's surface.")),
              (1982, "Venera 13", ("Venüs yüzeyinden ilk renkli fotoğraflar; 127 dakika dayandı.", "First colour pictures from Venus' surface; survived 127 minutes.")),
              (1990, "Magellan", ("Venüs'ün %98'ini radarla haritaladı.", "Mapped 98% of Venus with radar.")),
              (2006, "Venus Express", ("ESA'nın atmosfer ve iklim görevi.", "ESA's atmosphere and climate mission."))],
    "earth": [(1957, "Sputnik 1", ("İlk yapay uydu.", "The first artificial satellite.")),
              (1961, "Vostok 1", ("Yuri Gagarin, uzaya çıkan ilk insan.", "Yuri Gagarin, the first human in space.")),
              (1998, "ISS", ("Uluslararası Uzay İstasyonu; 2000'den beri sürekli insanlı.", "International Space Station; continuously crewed since 2000."))],
    "moon": [(1959, "Luna 2", ("Ay'a ulaşan ilk insan yapımı cisim.", "The first human-made object to reach the Moon.")),
             (1969, "Apollo 11", ("Neil Armstrong ve Buzz Aldrin Ay'a ilk iniş.", "Neil Armstrong and Buzz Aldrin made the first crewed landing.")),
             (2019, "Chang'e 4", ("Ay'ın uzak yüzüne ilk yumuşak iniş.", "First soft landing on the Moon's far side.")),
             (2022, "Artemis I", ("Orion kapsülünün insansız Ay turu.", "Uncrewed lunar flight of the Orion capsule.")),
             (2023, "Chandrayaan-3", ("Güney kutbu yakınına ilk başarılı iniş.", "First successful landing near the south pole."))],
    "mars": [(1965, "Mariner 4", ("Mars'ın yakın fotoğraflarını çeken ilk araç.", "First close-up pictures of Mars.")),
             (1976, "Viking 1", ("Mars'ta uzun süre çalışan ilk iniş aracı.", "First long-lived Mars lander.")),
             (1997, "Mars Pathfinder / Sojourner", ("Mars'taki ilk tekerlekli gezgin.", "First wheeled rover on Mars.")),
             (2012, "Curiosity", ("Gale kraterinde eski göl izleri buldu; hâlâ çalışıyor.", "Found ancient lake beds in Gale crater; still operating.")),
             (2021, "Perseverance + Ingenuity", ("Örnek toplayan gezgin ve başka bir gezegende ilk motorlu uçuş.", "Sample-caching rover and the first powered flight on another planet.")),
             (2021, "Zhurong", ("Çin'in ilk Mars gezgini.", "China's first Mars rover."))],
    "ceres": [(2015, "Dawn", ("Ceres yörüngesine giren ilk araç; daha önce Vesta'yı inceledi.", "First spacecraft to orbit Ceres; studied Vesta before."))],
    "jupiter": [(1973, "Pioneer 10", ("Jüpiter'in yanından geçen ilk araç.", "First spacecraft to fly past Jupiter.")),
                (1995, "Galileo", ("Jüpiter yörüngesine giren ilk araç; atmosfere sonda bıraktı.", "First Jupiter orbiter; dropped a probe into the atmosphere.")),
                (2016, "Juno", ("Kutup yörüngesinden Jüpiter'in iç yapısını inceliyor.", "Studies Jupiter's interior from a polar orbit.")),
                (2023, "JUICE", ("ESA'nın buzlu uydular görevi; 2031'de varacak.", "ESA's icy moons explorer; arrives in 2031."))],
    "europa": [(2024, "Europa Clipper", ("Europa'nın yaşanabilirliğini araştıracak; 2030'da varış.", "Will assess Europa's habitability; arrives 2030."))],
    "saturn": [(1979, "Pioneer 11", ("Satürn'ün yanından geçen ilk araç.", "First spacecraft to fly past Saturn.")),
               (2004, "Cassini", ("13 yıl Satürn yörüngesinde; 2017'de atmosfere dalarak görevini bitirdi.", "13 years in Saturn orbit; ended by diving into the atmosphere in 2017."))],
    "titan": [(2005, "Huygens", ("Dış Güneş Sistemi'nde bir cisme yapılan ilk iniş.", "First landing on a body in the outer Solar System.")),
              (2028, "Dragonfly", ("Titan'da uçacak nükleer güçlü helikopter (planlanan fırlatma).", "Nuclear-powered rotorcraft to fly on Titan (planned launch)."))],
    "enceladus": [(2005, "Cassini", ("Güney kutbu su püskürmelerini keşfetti ve içinden geçti.", "Discovered and flew through the south-polar plumes."))],
    "uranus": [(1986, "Voyager 2", ("Uranüs'ü ziyaret eden tek araç.", "The only spacecraft to visit Uranus."))],
    "neptune": [(1989, "Voyager 2", ("Neptün'ü ve Triton'u ziyaret eden tek araç.", "The only spacecraft to visit Neptune and Triton."))],
    "triton": [(1989, "Voyager 2", ("Azot gayzerlerini görüntüledi.", "Imaged nitrogen geysers."))],
    "pluto": [(2015, "New Horizons", ("Plüton'un yanından geçen ilk araç.", "First spacecraft to fly past Pluto."))],
    "phobos": [(2026, "MMX", ("JAXA'nın Phobos'tan örnek getirme görevi (planlanan fırlatma).", "JAXA's Phobos sample-return mission (planned launch)."))],
}

# Oyunda gidilebilen hedefler (data.PLANET anahtarları)
GAME_TARGETS = ("moon", "mars", "venus", "jupiter")

# Koloni için gerçek zorluklar (tr, en) — oyun tasarımı bunları basitleştirir.
HAZARDS = {
    "moon": [("Keskin, elektrostatik regolit tozu ekipmanı ve ciğerleri yıpratır.", "Sharp, electrostatically charged regolith dust wears out equipment and lungs."),
             ("Atmosfer ve manyetik alan yok: kozmik ışın ve güneş parçacıkları doğrudan gelir.", "No atmosphere or magnetic field: cosmic rays and solar particles arrive unshielded."),
             ("Ekvatorda gece ~14 Dünya günü sürer; güneş enerjisi için depolama ya da kutup bölgesi gerekir.", "Night lasts ~14 Earth days at the equator; solar power needs storage or a polar site.")],
    "mars": [("Basınç Dünya'nın ~%0,6'sı; basınçlı habitat ve giysi şart.", "Pressure is ~0.6% of Earth's; pressurised habitats and suits are mandatory."),
             ("Toprakta perklorat tuzları var; bitki yetiştirmeden önce arıtılmalı.", "The soil contains perchlorate salts that must be removed before growing plants."),
             ("Haberleşme gecikmesi 3 ile 22 dakika arasındadır.", "Communication delay ranges from 3 to 22 minutes."),
             ("Ortalama radyasyon dozu Dünya yüzeyindekinin onlarca katı.", "Average radiation dose is tens of times that on Earth's surface.")],
    "venus": [("Yüzey ~464 °C ve 92 bar; en dayanıklı araç bile birkaç saat dayandı.", "Surface is ~464 °C and 92 bar; the toughest landers lasted only hours."),
              ("Bulutlar sülfürik asit içerir; malzemeler asite dayanıklı olmalı.", "Clouds contain sulfuric acid; materials must resist acid.")],
    "jupiter": [("Radyasyon Europa yakınında günde ~5 Sv'e ulaşabilir; korunmasız insan için ölümcül.", "Radiation near Europa can reach ~5 Sv per day, lethal to an unshielded person."),
                ("Güneş ışığı Dünya'dakinin ~%4'ü; güneş paneli verimi çok düşer.", "Sunlight is ~4% of Earth's; solar panel output drops sharply."),
                ("Katı yüzey yok; koloniler gerçekte uydularda (Kallisto gibi) düşünülür.", "No solid surface; real colony concepts target moons such as Callisto.")],
}


def lang_idx(lang):
    return 0 if lang == "tr" else 1


def name(key, lang="en"):
    b = BODIES.get(key)
    return b["name"][lang_idx(lang)] if b else key

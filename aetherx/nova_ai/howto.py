# -*- coding: utf-8 -*-
"""
NOVA OYUN REHBERİ — "nasıl yapılır" yanıtları (tr, en). Yalnız oyunda gerçekten var olan özellikleri anlatır.
"""

HOWTO = {
    "money": (("para", "kazan", "money", "earn", "gelir", "income", "zengin", "cash"),
              ("Para kazanmanın yolları: görevleri başarıyla tamamlamak, DEPO'da madenleri satmak, koloni ticaretini açmak ve "
               "günlük/haftalık görev ödüllerini almak. Kolonilerin seviyesi yükseldikçe üretim de artar.",
               "Ways to earn money: complete missions successfully, sell minerals in the DEPOT, enable colony trade and claim "
               "daily/weekly quest rewards. Higher colony levels produce more.")),
    "research": (("arastirma", "ar-ge", "arge", "research", "teknoloji", "tech", "rp", "puan"),
                 ("AR-GE ekranında bir teknoloji seçip altın renkli ARAŞTIR düğmesine bas. Araştırma oyun saatinde ilerler; "
                  "Araştırma binasını yükseltmek süreyi kısaltır ve maliyeti düşürür. Araştırma puanı (RP) görevlerden ve kolonilerden gelir.",
                  "On the R&D screen pick a technology and press the gold RESEARCH button. Research advances in game time; "
                  "upgrading the Research building shortens it and lowers the cost. Research points (RP) come from missions and colonies.")),
    "colony": (("koloni", "colony", "us", "base", "yerlesim", "settlement"),
               ("Koloni kurmak için önce hedefe başarılı iniş yap; sonra KOLONİLER ekranından kuruluş bedelini öde. "
                "Binalar ekleyip seviye atlatarak nüfusu, üretimi ve mutluluğu artırırsın. Mutsuz koloni daha az çalışır.",
                "To found a colony, first land successfully at the target, then pay the founding cost on the COLONIES screen. "
                "Add buildings and level it up to grow population, output and happiness. Unhappy colonies work less.")),
    "crew": (("murettebat", "ekip", "astronot", "crew", "astronaut", "egit", "train", "ise al", "hire", "calisan"),
             ("UZAY ÇALIŞANLARI ekranında İŞE AL ile yeni üye alır, EĞİT ile seviyelerini yükseltirsin. Yorgun ya da hasta "
              "ekip üyesini dinlendir; giysi geliştirmeleri hastalık ve yaralanma riskini düşürür. Merkez yükseltmeleri kapasiteyi artırır.",
              "On the SPACE CREW screen use HIRE to add members and TRAIN to level them up. Rest tired or sick members; suit "
              "upgrades lower sickness and injury risk. Centre upgrades raise capacity.")),
    "rocket": (("roket", "rocket", "tasarim", "design", "motor", "engine", "yakit", "fuel", "parca", "part"),
               ("TASARIM ekranında gövde, motor, yakıt ve kalkan parçalarını seç. Menzil hedefe yetmeli, itki kütleyi kaldırmalı; "
                "Venüs için ısı kalkanı şarttır. Yakıtı HANGAR'dan alabilirsin. Kilitli parçalar araştırmayla açılır.",
                "In the DESIGN screen choose hull, engine, fuel and shield parts. Range must reach the target and thrust must lift the mass; "
                "Venus needs a heat shield. Buy fuel in the HANGAR. Locked parts unlock through research.")),
    "landing": (("inis", "landing", "land", "indir", "iniyor", "inilir", "inmek", "inerim", "inebilirim"),
                ("İnişte dikey hızı 3 m/s'nin altına indir, aracı dik tut ve yakıtı son yüz metreye sakla. Ay'da hava yok, "
                 "Mars'ta ince, Venüs'te çok yoğun; frenleme ona göre değişir.",
                 "When landing, bring vertical speed under 3 m/s, keep the craft upright and save fuel for the last hundred metres. "
                 "The Moon has no air, Mars thin air, Venus very dense air, so braking differs.")),
    "storm": (("firtina", "storm", "uzay havasi", "space weather", "risk"),
              ("Güneş fırtınası sırasında fırlatma riski artar. NOVA Seviye 2 bir sonraki fırtınayı kabaca, Seviye 3 tam "
               "zamanlamasını gösterir; 'en iyi fırlatma saati' diye sorabilirsin.",
               "Launch risk rises during a solar storm. NOVA level 2 roughly predicts the next storm, level 3 shows exact timing; "
               "you can ask me for the best launch time.")),
    "leaderboard": (("siralama", "leaderboard", "skor", "score", "rank", "liderlik"),
                    ("SIRALAMA ekranı skoru, parayı ve seviyeyi sıralar. Çevrimiçi sıralama için AYARLAR > OYUN'a sunucu adresi "
                     "girilmelidir; adres yoksa bu cihazdaki kampanyalar sıralanır. Skor = seviye×1000 + para/10 + koloni×2000 + "
                     "başarım×300 + başarılı görev×150 + koloni seviyesi×500.",
                     "The LEADERBOARD screen ranks score, money and level. Online ranking needs a server address in SETTINGS > GAME; "
                     "without one, campaigns on this device are ranked. Score = level×1000 + money/10 + colonies×2000 + "
                     "achievements×300 + successful missions×150 + colony levels×500.")),
    "save": (("kayit", "kaydet", "save", "load", "yukle", "devam"),
             ("Oyun önemli olaylarda ve AYARLAR'daki aralıkla otomatik kaydeder. Açılışta 'KAYITTAN DEVAM ET' ile son kampanyana dönersin.",
              "The game autosaves on key events and at the interval set in SETTINGS. On start, 'CONTINUE FROM SAVE' returns you to your campaign.")),
    "settings": (("ayar", "settings", "grafik", "graphics", "fps", "ses", "sound", "dil", "language"),
                 ("AYARLAR ekranında grafik kalitesi, FPS sınırı, ses seviyeleri, dil, erişilebilirlik ve sıralama sunucusu ayarlanır.",
                  "The SETTINGS screen controls graphics quality, FPS cap, volume levels, language, accessibility and the leaderboard server.")),
    "quests": (("gorev listesi", "quest", "gunluk", "daily", "haftalik", "weekly", "basarim", "achievement"),
               ("Günlük ve haftalık görevler belirli işleri (fırlatma, araştırma, satış) istemenle ilerler; tamamlanınca ödülü almayı unutma. "
                "Başarımlar skora da katkı sağlar.",
                "Daily and weekly quests progress as you do certain things (launches, research, sales); claim the reward when done. "
                "Achievements also add to your score.")),
    "level": (("seviye", "level", "xp", "deneyim", "kademe", "rozet", "badge"),
              ("Ajans seviyesi deneyim puanıyla (XP) yükselir: görevler, araştırmalar ve koloni işleri XP verir. Yeni seviyeler yeni hedefleri ve parçaları açar.",
               "Agency level rises with experience (XP): missions, research and colony work grant XP. New levels unlock targets and parts.")),
}


def find(norm, how_words=True):
    best, n = None, 0
    for key, (kws, _) in HOWTO.items():
        for kw in kws:
            if (" " in kw and kw in norm) or kw in norm.split() or any(w.startswith(kw) for w in norm.split() if len(kw) >= 4):
                if len(kw) > n:
                    best, n = key, len(kw)
    return best

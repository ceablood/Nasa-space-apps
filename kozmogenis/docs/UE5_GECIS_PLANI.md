# KOZMOGENİS — Unreal Engine 5 Geçiş Analizi ve Planı

Bu belge "UE5 tam geçiş ve Windows EXE" talimatının **2. bölümünü** (mevcut çalışmaların analizi) karşılar.
Tarih: 20 Kasım 2026. Durum etiketleri: ✅ çalışıyor ve test edildi · 🟡 var ama UE5'e taşınmalı ·
🧱 UE5 kodu yazıldı, **derlenmedi** · ❌ yok.

## 1. Adım 1 sonucu: ortam kontrolü

| Gereksinim | Durum |
|---|---|
| Unreal Engine 5 kurulumu | ❌ Geliştirme ortamında (Linux bulut kapsayıcısı) yok; kurulamaz (Epic hesabı, Windows, ~60-150 GB) |
| Windows + Visual Studio 2022 | ❌ Yok. Kullanıcının elinde yalnızca tablet var |
| C++ derleyici (MSVC) | ✅ GitHub Actions Windows makinesinde KozmoCore MSVC ile derlenip test ediliyor |

**Sonuç:** Talimatın 3-10. aşamalarındaki derleme, oynatma testi ve paketleme (KOZMOGENIS.exe) UE5 kurulu bir
Windows makinesi olmadan yapılamaz. Bu belge yapılabilen kısımları ve o makine gelince izlenecek sırayı tanımlar.

## 2. Mevcut çalışmaların envanteri

| Kod tabanı | Dil / satır | İçerik |
|---|---|---|
| **AETHER-X** (`aetherx/`) | Python/pygame, ~17.800 satır | 16 ekran: menü, fırlatma üssü (3B binalar), hangar (parça tabanlı roket tasarımı), fırlatma, yolculuk mini oyunu, sonuçlar, AR-GE, ekip, depo, görevler, NOVA odası, görev kontrol, koloni (2B + yazılım 3B), ajans, ATLAS (3B Güneş Sistemi). 6 dil, prosedürel ses, prosedürel gezegen dokuları, sinematik efektler. Tarayıcıda yayında. |
| **KozmoCore** (`kozmogenis/core`) | C++17, ~2.000 satır + ~550 test | NASA verili astronomi + yörünge mekaniği, roket mühendisliği, ekonomi, koloni + NPC yaşam simülasyonu, araştırma, kayıt, olay yolu. 32 test, GCC/Clang/MSVC. |
| **UE5 istemcisi** (`kozmogenis/unreal`) | UE C++, ~730 satır | Alt sistem (KozmoCore sarmalayıcı), NASA verili 3B Güneş Sistemi, Slate görev kontrol paneli, serbest kamera. **Derlenmedi.** |

## 3. Çakışmalar

1. **İki ayrı oyun mantığı:** AETHER-X `game.py` (oyun dengeli: para, kg cinsinden kaldırma, parça kataloğu, saniye bazlı araştırma) ile KozmoCore (fiziksel: ton, delta-v, gerçek motor sınıfları, gün bazlı simülasyon) aynı kavramları farklı birimlerle modelliyor.
   **Karar:** KozmoCore tek doğruluk kaynağı olur. AETHER-X'te olup çekirdekte olmayan mekanikler (aşağıda) C++'a taşınır; birimler SI'ya çevrilir.
2. **İki koloni modeli:** AETHER-X kolonisi (mutluluk/nüfus/bina seviyesi) ile KozmoCore kolonisi (enerji, yaşam desteği, NPC ihtiyaçları). Çekirdek modeli korunur; AETHER-X'in bina türleri (ev, maden, sera, hastane, okul, park, spor salonu) çekirdek modül türlerine eşlenir.
3. **Zaman ölçeği:** AETHER-X'te 1 gerçek saniye = 2 oyun dakikası; çekirdekte serbest hız (gün/sn). UE5'te çekirdek ölçeği kullanılır, oyuncu seçer.

## 4. UE5 ile uyumsuz kod ve karşılıkları

| AETHER-X bileşeni | Neden doğrudan aktarılamaz | UE5 karşılığı |
|---|---|---|
| pygame çizim, UI (`ui.py`, sahneler) | Yazılım rendering | **UMG** widget'ları (C++ tabanlı) |
| Prosedürel gezegen dokuları (`space3d.py`, numpy) | Çalışma anında CPU'da üretim | **Yeniden kullanılır:** Python aracıyla 2048×4096 doku olarak önceden üretilip UE'ye içe aktarılır; atmosfer/bulut için malzeme + gerekirse HLSL |
| Yazılım 3B koloni (`colony3d.py`) | Kendi rasterleştiricisi | UE aktörleri + Instanced Static Mesh, Navmesh, Chaos |
| Sinematik efektler (`cinema.py`) | 2B sonradan işleme | Post Process Volume, Lumen, volumetrik sis, **Niagara** toz/parçacık |
| Prosedürel ses (`audio.py`, numpy) | Çalışma anında sentez | **MetaSounds** |
| 3B üs binaları (`archviz.py`) | 2B eğik izdüşüm | Gerçek 3B mesh'ler (modüler kit) |
| pygbag web sürümü | WebAssembly | Pixel Streaming (ücretli GPU sunucusu) ya da indirilebilir EXE |
| 6 dil (`i18n.py`, `lang/`) | Python sözlükleri | **Yeniden kullanılır:** Python aracıyla UE String Table / `.po` dosyalarına dönüştürülür |
| NASA atlas verisi (`atlas.py`) | — | Zaten KozmoCore'da; uydu/yapay uydu listesi DataTable'a aktarılır |

## 5. 21 sistem — mevcut durum ve eksikler

| # | Sistem | Mevcut | Eksik (UE5'te yapılacak) |
|---|---|---|---|
| 1 | GARE Runtime Engine | ❌ — terim bu projede tanımlanmadı | Tanım gerekli (kullanıcıdan bekleniyor) |
| 2 | Graphics Engine | 🟡 AETHER-X 2B/yazılım 3B; 🧱 UE temel sahne | PBR malzemeler, Lumen, Nanite, ölçeklenebilirlik profilleri |
| 3 | Advanced Cockpit Graphics | ❌ | Kokpit mesh'i, göstergeler (UMG 3D widget), HUD |
| 4 | Physics Engine | ✅ çekirdek: yörünge, roket denklemi | Chaos ile 6 serbestlik dereceli araç fiziği, çarpışma |
| 5 | Planet Engine | 🟡 prosedürel dokular, ✅ NASA verisi | Küre LOD/arazi, atmosfer saçılması, bulut katmanı |
| 6 | Procedural Universe | ❌ (yalnızca Güneş Sistemi) | Yıldız/galaksi üretimi (tohumlu) |
| 7 | Open World Exploration | ❌ | World Partition, gezegen yüzeyi akışı |
| 8 | Character Engine | ❌ (2B astronot çizimi var) | Karakter mesh'i, animasyon, kıyafet sistemi |
| 9 | NPC Living Universe | ✅ çekirdek: ihtiyaçlar, meslek, rutin, ölçeklenebilir sim. | UE aktör temsili, LOD |
| 10 | Advanced NPC AI | ✅ fayda tabanlı karar; 🟡 A* yürüme (Python) | Behavior Tree / State Tree, Navmesh |
| 11 | NOVA AI | 🟡 AETHER-X kural tabanlı danışman (`nova.py`) | C++'a taşıma (çevrimdışı), isteğe bağlı çevrimiçi model entegrasyonu |
| 12 | Space Agency & Rocket Engineering | ✅ çekirdek mühendislik; 🟡 AETHER-X parça kataloğu/hangar | UMG hangar, 3B montaj |
| 13 | Rocket Flight & Spacecraft Control | 🟡 2B fırlatma + yolculuk mini oyunu | Gerçek zamanlı uçuş, yanma planlama, kontrol |
| 14 | Stations, Colonies, Industry & Logistics | ✅ çekirdek koloni/üretim; 🟡 AETHER-X ticaret yolu | İstasyonlar, lojistik rotaları, 3B inşa |
| 15 | Science, Research & Mission Control | ✅ araştırma ağacı; 🟡 görevler/başarımlar (Python) | Görev sistemi C++'a, görev kontrol ekranı |
| 16 | Orbital Mechanics, Galaxy & Civilization | ✅ yörünge mekaniği, pencereler | Medeniyet/galaksi ilerlemesi |
| 17 | Ecosystem, Environment, Events & Defense | 🟡 AETHER-X olaylar, güneş fırtınaları, Mars toz fırtınası | C++'a taşıma, ekosistem, savunma |
| 18 | Audio, UI, Accessibility, Save & Multiplayer | ✅ kayıt (JSON); 🟡 ses, 6 dil, UI | MetaSounds, UMG, erişilebilirlik ayarları, çok oyunculu (yok) |
| 19 | Backend, Web Portal, Pixel Streaming & Security | 🟡 GitHub Pages (tarayıcı sürümü) | Pixel Streaming sunucusu (ücretli), backend yok |
| 20 | Optimization, QA, Scientific Validation & Release | ✅ çekirdek testleri + bilimsel doğrulama, CI; ölçümlü optimizasyon (AETHER-X) | UE profil (Unreal Insights), paketleme, temiz Windows testi |
| 21 | Team, Rights & Project Governance | ❌ | Lisans, katkı kuralları, varlık hakları |

**AETHER-X'te olup KozmoCore'a henüz taşınmamış mekanikler:** astronot tipleri/rütbe/eğitim/yorgunluk/hastalık,
astronot kıyafeti (zırh/eklem/yaşam desteği), depo ve yakıt deposu, günlük/haftalık görevler, 18 başarım,
ajans seviyesi/XP/itibar, diplomasi (ajanslar arası anlaşmalar), rastgele ajans olayları, güneş fırtınası
tahmini, rampa hazırlığı, yolculuk mini oyunu (asteroit, yakıt istasyonu, uydu kurtarma).

## 6. Aşama planı (talimatın 7. bölümü)

| Aşama | İş | Bu ortamda yapılabilir mi? |
|---|---|---|
| 1 | Ortam kontrolü | ✅ yapıldı (bkz. §1) |
| 2 | C++ proje iskeleti | 🧱 yazıldı, derleme Windows'ta |
| 3 | Temel oyun sistemleri | ✅ çekirdekte; AETHER-X mekaniklerinin C++'a taşınması **burada yapılabilir ve test edilebilir** |
| 4 | Roket + fizik prototipi | Çekirdek ✅; UE görsel/kontrol tarafı Windows'ta |
| 5 | Gezegen + keşif | Doku üretim aracı burada; UE sahnesi Windows'ta |
| 6 | Koloni + NPC | Çekirdek ✅; UE temsili Windows'ta |
| 7 | NOVA AI | Çevrimdışı motor C++'ta **burada yapılabilir** |
| 8 | Grafik + ses | Windows + UE5 gerekli |
| 9 | Optimizasyon + test | Çekirdek burada; UE profil Windows'ta |
| 10 | Paketleme → KOZMOGENIS.exe, temiz Windows'ta deneme | Windows + UE5 gerekli |

## 7. Windows makinesi gelince

Claude masaüstü uygulaması o bilgisayarda açılıp Remote Control ile proje klasörü bu oturuma bağlanırsa
derleme → hata düzeltme → paketleme → test döngüsü doğrudan o makinede yürütülebilir. Fiziksel PC yoksa
bulut Windows bilgisayarı (GPU'lu, saatlik/aylık ücretli) da aynı şekilde kullanılabilir.
Ayrıntılı kurulum: [UNREAL_KURULUM.md](UNREAL_KURULUM.md).

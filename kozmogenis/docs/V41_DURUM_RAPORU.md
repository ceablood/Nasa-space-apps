# KOZMOGENİS V41 — İlerleme raporu (V30 §30.3 biçimi)

PROJE: KOZMOGENİS · SÜRÜM: V41.1 (dikey dilim + geliştirme) · Tarih: 21 Kasım 2026 · Ortam: Linux bulut kapsayıcısı (UE5 yok)

## Dikey dilim (V41 §10) — çekirdekte uçtan uca çalışan ve test edilen akış

`kozmo_cli --dilim` ve `tests/test_world.cpp`:

1. Oyuncu kabinde, kokpite oturur (oturmadan motor çalışmaz; manuel uçuşta koltuktan kalkılamaz).
2. Ay'a iniş: Apollo motorlu iniş başlangıcı (15 km, 1.65 km/s) → iniş desteği → **1.25 m/s temas**, ~1.8 km/s delta-v (Apollo LM bütçesi ~2.0 km/s).
3. Araçtan çıkış (yörüngede/inmeden/giysisiz çıkılamaz), gezegene özgü zorluk raporu (vakum, −50 °C sabah, 1.37 mSv/gün).
4. 18 bölgeli koloniye yürüyüş (Ay'da Froude yürüyüşü ~0.6 m/s), binaya giriş, konsollar (nüfus, harita, ekonomi, güvenlik, görevler, NOVA, mikroskop, enerji paneli).
5. NPC'ler kendi programlarını yürütür (vardiya, yemek, uyku, devriye, araştırma); konuşma ihtiyaç/iş/hafızayı yansıtır.
6. NOVA: koloni durumu, gezegen riski (kaynaklı), araç durumu, "neden üretim yavaşladı?" teşhisi, **onaysız yapılmayan** tahliye.
7. Acil durum (§7.3): enerji tesisi arızası → mühendisler enerji merkezine, siviller sığınağa → oyuncu panelden onarır → alarm kalkar.
8. İkinci gezegen Mars: iniş, farklı çevre profili, toz fırtınaları (araçta güvenle bekleme).
9. Kayıt/yükleme: araç, oyuncu, NPC hafızası/ilişkileri.

## V41.1 eklemeleri (test edildi)

* **§4.6 Modüler inşaat** (`construction`): 13 yapı parçası (temel, duvar, tavan, kapı, pencere, koridor, hava kilidi, merdiven, asansör, enerji/su/oksijen/veri hattı); her birinin demir+kredi maliyeti, emek-saati, işletme gücü, bakım yükü, dayanımı, kapasitesi. Modül şablonları ve **bağlantı sırası** (habitat enerji kaynağı olmadan bağlanmaz). İşçiliği NPC mühendisler sahada çalışarak üretir.
* **Su geri dönüşüm sistemi** modülü: temel %85 geri kazanımı ISS 2023 düzeyine (%98) çeker.
* **§7.1 Mars'ta sıfırdan koloni** (`kozmo_cli --kurulum`): iniş (1.23 m/s) → su taraması (yeraltı buzu) → NOVA onaylı kuruluş (4 kişi, iniş kampı) → NOVA onaylı güneş dizisi + habitat + su geri dönüşüm inşaatı (~182 emek-saat, ~10 gün) → toz fırtınası, NPC'ler sığınağa → fırtına hasarı → NOVA hasar raporu → güçlendirme (sonraki hasar %70 azalır).
* **§7.2 Titan buz araştırması**: Huygens benzeri paraşüt sonrası iniş, termal giysi gereksinimi (−179 °C < EMU sınırı −157 °C), numune, araç laboratuvarında analiz (araştırma ağacına puan); termal giysisiz çıkış zarar verir.
* **§6.3 Görevlendirme**: NOVA onayla genel emir verir; NPC sağlığı/yorgunluğu/dozu/mevcut görevi uygunsa kabul eder, değilse nedenini bildirir; görev bitince kendi programına döner.
* **§2.5 Kalkış ve kenetlenme**: Ay'dan 15 km yörüngeye otomatik kalkış ~1.81 km/s (Apollo LM yükselişi ~1.85 km/s); aynı araç Mars'tan yörüngeye **çıkamaz** (~4 km/s gerekir, aracın bütçesi 3.5 km/s — model doğru olarak başarısız). RCS ile istasyona kenetlenme desteği (temas ≤0.15 m/s), manuel hızlı yaklaşmada çarpışma hasarı.
* **§2.1/§2.3 Araç kataloğu**: 19 hazır araç, 6 sınıfın tamamı; V1–V4 sürümü parçalardan türetilir (etiket değil); kurgusal füzyon motoru ayrı işaretli, NERVA sınıfı gerçek.
* **§8 NOVA veri doğrulama**: kaydı olmayan stok "? (kayıt yok)", tutarsız değer "? (tutarsız veri)", ölçüm yerine tahmin olan radyasyon değerleri "VERİ UYARISI" ile bildirilir.
* UE: HUD'a su ara / koloni kur / inşa / güçlendir / hasar raporu / araç lab / yörüngeye kalk / kenetlen düğmeleri; inşaat ilerledikçe 3B koloni yeniden kurulur (arsa kazıkları, yükselen iskele ve duvarlar, ilerleme etiketi); Titan turuncu puslu gökyüzü; ana panelde Mars ve Titan seferleri. **Derlenmedi.**

## Sistem durumu

| V41 bölümü | Çekirdek (C++, test edildi) | Unreal (yazıldı, **derlenmedi**) |
|---|---|---|
| §1 Kokpit V20 | Kokpit V1–V4 işlev kapıları, 12 canlı gösterge, 9 arıza + müdahale, uçuş modları | `AKozmogenisCockpitActor`: 3B koltuk/konsol/kollar, canlı gösterge metinleri, uyarı lambaları, fiziksel düğmeler, kabin ışığı; kamera sarsıntısı ayarlı |
| §2 Uzay aracı V20 | 30 parça, türetilmiş özellikler (kütle, yakıt, itki, delta-v, güç, mürettebat, kargo, boyut), hasar → davranış, yaşam desteği, iniş güdümü, kayıt | `AKozmogenisSpacecraft` pawn: parçalardan gövde, alev, kontroller |
| §3 Gezegen zorlukları | 9 gerçek gövde, 8 sınıf, 10 kategori, ekipmanla dinamik zorluk, parametrelerden hava olayları, EVA hayatta kalma | `AKozmoExpeditionScene`: Ay kara gök / Mars tozlu SkyAtmosphere, fırtına → sis/ışık |
| §4 3D koloni | 18 bölge, iç mekân odaları/konsolları, yerleşim tipi (yer altı/kubbe/kutup/okyanus/yörünge), yollar | `AKozmogenisColony`: duvarlar, kapı boşlukları, kubbe/regolit örtüsü, konsollar; `AKozmogenisCharacter` yürüyüş |
| §5 NPC | Kişilik (9 eksen), ihtiyaçlar, vardiya, 5 katmanlı karar, meslekler, hafıza (sınırlı, önem sıralı), ilişkiler, sosyal etkileşim, olay tepkileri, LOD | `AKozmogenisNPC`: gövde/etiket, yürüme |
| §6 NOVA | Sefer bağlantısı, 4 yeni niyet, onaylı tahliye | HUD NOVA kutusu |

Toplam: **97 test, 60.606 kontrol, 0 başarısız** (V41 için 33 test). ASan+UBSan temiz; UE kısıtlarıyla (C++20, RTTI/istisna kapalı) tek birim derleme 0 hata / 0 uyarı.

## Dürüst sınırlar

* Unreal kodu bu ortamda derlenmedi/çalıştırılmadı. Behavior Tree, State Tree, EQS, Smart Objects, Mass, GAS, World Partition, HLOD, Nanite ve iskelet animasyonu **planlandı**; bu dilimde karar mantığı test edilmiş çekirdekte, 3B görünüm temel şekillerle.
* Uçuş 2B (irtifa + yatay), düz zemin üstünde; Mars tam atmosfer girişinden bu aracın motorsuz yavaşlaması mümkün değil (model bunu gösteriyor), dilim paraşüt sonrası 10 km'den başlar.
* NASA tablosunda Mars yüzey yoğunluğu 0.020 kg/m³; ideal gazla 0.636 kPa / 208 K'den 0.016 çıkıyor — test ideal gaz değerini kullanır.
* Zorluk ağırlıkları, ekipman katsayıları, NPC davranış katsayıları oyun varsayımıdır.

## SONRAKİ AŞAMA

Hedef Windows PC'de UE5 ilk derleme, derleme hatalarının düzeltilmesi, dikey dilimin oyun içinde oynanması ve FPS ölçümü.

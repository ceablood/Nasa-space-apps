# AETHER-X · Uzay Ajansı Komuta Simülasyonu

## ▶ Tarayıcıda oyna: https://ceablood.github.io/Nasa-space-apps/

Site tek bir oyundur: AETHER-X (Python/pygame, tarayıcıda WebAssembly). Ayrı 3D web sürümü kaldırıldı; ayrıntı ve geri
dönüş noktası: [`docs/AYRI_3D_SURUM_KALDIRILDI.md`](docs/AYRI_3D_SURUM_KALDIRILDI.md). Unreal Engine 5 sürümü ve C++ çekirdeği:
[`kozmogenis/`](kozmogenis/) (UE5 istemcisi henüz derlenmedi).

## Sürüm 3.12 — NOVA altı dilde, genişletilmiş TÜİK verisi, kolonide 45 FPS koruması

**NOVA: Almanca, Fransızca, İspanyolca, Rusça**
- NOVA'nın ürettiği her cümle bu dillere çevrildi: gezegen bilgileri, görevler, kavramlar, oyun rehberi, oyun durumu,
  TÜİK ve NASA yanıtları, yarışma soruları, duygu cümleleri. Toplam ~440 metin ve kalıp, 4 dil
  (`aetherx/nova_ai/tx_engine.py`, `tx_kb.py`).
- Yer tutuculu kalıplarla değişken parçalar (sayı, gezegen adı) yerine konur.
  - Sayılar dile göre biçimlenir: de/es 1.234,5 · fr 1 234,5 · ru 1 234,5.
  - Rusçada birimler Kiril (км/с, м/с²).
  - Gök cismi adları her dilde.
- NOVA bu dillerde yazılan soruları da anlar: niyet, kavram, gök cismi ve TÜİK göstergesi anahtar sözcükleri, Rusça çekimler
  (на Марсе, в Анкаре), sinir ağı bu sözcüklerle de eğitilir.
- Otomatik test dört dilde bütün gök cisimleri × bütün soru türleri, TÜİK, NASA, oyun durumu ve yarışma yanıtlarını üretir;
  çevrilmeden kalan cümle sayısı 0'dır.

**TÜİK verisi (nip.tuik.gov.tr, 28.11.2026)**
- Portalın 31 sayfası gerçek tarayıcıyla taranıp gösterge listesi çıkarıldı.
- Pakette olan 11 gösterge yeniden indirildi ve portalla birebir aynı çıktı (en son yayımlanan yıllar 2024–2025 zaten içerideydi).
- 12 gösterge eklendi:
  - canlı doğum, evlenme, okuryazarlık oranı;
  - iller arası alınan ve verilen göç, il bazında hesaplanan net göç;
  - yurt dışından gelen ve yurt dışına giden göç;
  - toplam, çocuk ve yaşlı bağımlılık oranları;
  - yabancı nüfusun erkek ve kadın dağılımı.
- Eklemeden önce tutarlılık denetlendi:
  - iller arası alınan göç = verilen göç (her yıl);
  - toplam bağımlılık = çocuk + yaşlı (her ilde);
  - yabancı erkek + kadın = yabancı toplam (her ilde).
- Genel erkek/kadın nüfus dosyaları hâlâ tutarsız (81 ilde aynı değerler), kullanılmadı.

**Koloni performansı**
- Görüntüyü değiştirmeyen iyileştirmeler:
  - binaların zemine düşen gölge geometrisi güneş değişene kadar önbellekte;
  - kolonist modelleri karede bir kez kuruluyor;
  - poligon noktaları numpy'den hazır liste;
  - küçültme ve tilt-shift kalıcı hedef yüzeylere yazıyor;
  - uzay arka planı, 3B görünümün kapattığı alana kopyalanmıyor;
  - üst çubuk degradesi önbellekte.
  - Bu değişikliklerin her biri önceki sürümle piksel piksel karşılaştırıldı.
- **Hareketli kamerada 45 FPS koruması** (AYARLAR > PERFORMANS, varsayılan açık):
  - Yalnız kamera hareket ederken ve ölçülen kare süresi 22,2 ms'yi aşarsa 3B süper örnekleme ×2'den ×1,5'e iner.
  - Kamera durduğu karede tam kaliteye döner; durağan görüntü değişmez.
  - Hızlı cihazlarda hiç devreye girmez.
- Not: 3.11'de eklenen bölgesel gölge önbelleği, önbellekli ve baştan çizilen kareyi piksel piksel aynı üretir. Önceki tek geçişli
  yönteme göre ise gölge kenarlarında birkaç yüz pikselde görünmez yuvarlama farkı vardır (bulanıklık bölge boyutuna göre örneklenir).

## Sürüm 3.11 — NOVA gerçek verilere bağlı, sinir ağı ve duygular; 45+ FPS; yeni ajans görünümü

**NOVA: gerçek veri**
- **TÜİK:** Nüfus İstatistikleri Portalı'nın (nip.tuik.gov.tr) il düzeyi resmî dosyalarından 11 gösterge, 2008–2025:
  - nüfus, artış hızı, yoğunluk, ortanca yaş, doğurganlık, bebek ölüm hızı;
  - ölüm, boşanma, hanehalkı sayısı ve büyüklüğü, yabancı nüfus.
  - Veri oyunla gelir (`aetherx/nova_ai/data/tuik_il.json`, 27.11.2026); sorularda kaynak ve tarih yazılır.
  - Sayımlar için Türkiye değeri 81 ilin toplamı. Oranlar için ulusal değer uydurulmaz.
  - Portalın erkek/kadın dosyaları tutarsız çıktığı (81 ilde değerler aynı) için kullanılmadı.
- **NASA (anahtarsız):**
  - JPL yakın geçişler: tarih, uzaklık, hız ve parlaklıktan çap aralığı.
  - Ötegezegen Arşivi: doğrulanmış gezegen sayısı.
  - EONET: Dünya'daki açık doğa olayları.
  - Masaüstünde canlı çekilir. Tarayıcıda yalnız EONET canlı (CORS); diğerleri oyunla gelen tarihli anlık görüntüden gelir.
  - Yanıt hangisinin kullanıldığını açıkça söyler.

**NOVA: zihin**
- **Sinir ağı:** numpy ile yazılmış küçük bir ağ (1024 özellik → 48 nöron → 51 niyet).
  - Oyun içinde, sabit tohumla eğitilir; masaüstünde ~1 sn, arka planda.
  - Kurallarla birlikte karar verir; tanımadığı sözcüklerden oluşan girdiyi tahmine zorlamaz.
  - Gizli katmanın gerçek etkinliği AI Kontrol Merkezi'nde yüzün çevresinde nöron olarak görünür.
- **Duygular:** neşe, merak, endişe, gurur, hüzün.
  - Oyundaki gerçek olaylardan (görev sonucu, fırtına, hasta ekip, para, koloni mutluluğu) ve sohbetten beslenir; zamanla söner.
  - Yüzün rengini ve konuşma tonunu belirler, ekranda çubuklarla gösterilir. Bu bir benzetimdir.
- **Düşünme:** NOVA yanıt vermeden önce sorunun ağırlığına göre 0,6–3 sn düşünür, sonra yanıtı harf harf yazar.
- **Olasılık ve güven:**
  - Emin değilse yüzdesiyle söyler ("Sanırım… %78 eminim").
  - "Başarır mıyım?" sorusunu tasarım analizinin gerçek risk hesabıyla, yorum katarak yanıtlar.
- **Türkçe:** yüzde ve sayı ekleri ("%18,3'ü", "%0,9'u"), il adlarında hal ekleri ("İstanbul'da", "Ankara'nın").

**Performans (ölçüm: bu geliştirme ortamı, Ultra, 2× süper örnekleme)**
- **Koloni:** manzara, arazi ve bina gölgeleri kamera ve güneş değişmedikçe önbellekten gelir. Her karede yalnız kolonistlerin çevresi yenilenir.
  - Üst üste binen gölgeler yine tek kat kararır; önbellekli ve tam çizim piksel piksel aynıdır.
  - Kamera hareketliyken önbelleğe yazılmaz, tek geçişte çizilir.
  - Sonuç: sabit kamerada ~19 ms (~52 FPS), kolonist takibinde ~22–24 ms (~42–45 FPS).
- **Uzay arka planı:** huzme ve fırça×vinyet katmanı önbelleğe işlenir. Yıldız ve zerreler bu katmanı kendi konumlarında örnekler.
  - Görüntü aynı (ortalama piksel farkı 0,002); her ekranda bir tam ekran karışımı eksik.
- **Diğer ekranlar:** üs ~10 ms, ajans ~11, NOVA ~9, Güneş Sistemi ~14, Yaşam ~14, uçuş/iniş ~8–12 ms.

**Ajans ekranı**
- Dönen 3B Dünya (ajans merkezi; 60 karelik dönüş bir kez, arka planda hesaplanır), seviye halkası ve yörüngede ajans roketi.
- Görev sonuçları halka grafiği ve başarı oranı; ikonlu istatistik kutuları.
- Zafer yolunda "sıradaki" adımın vurgusu.
- Karne şeridi: skor, bu cihazdaki sıra, kasa, RP, koloni, ekip.

## Sürüm 3.10 — Sakin sesler, NOVA sohbet motoru, canlı sıralama, gerçekçi ışık ve gölge

**Sesler**
- Baş ağrıtan sesler kaldırıldı: üzerine gelme sesi yok; tık, yazı ve uyarı sesleri yumuşak, alçak frekanslı tonlar;
  hangarın tekrar eden alarmı ve ortam bip/parıltıları kapalı; NOVA'nın konuşma sesi seyrek ve kısık.

**Arayüz**
- Tıklanabilir eylem düğmeleri altın sarısı: ARAŞTIR, GELİŞTİR, YÜKSELT, EĞİT, İŞE AL, NOVA yükseltmesi, SIRALAMA, SOR.
- Ajans kurma ekranında **KAYITTAN DEVAM ET** (kayıt varsa; ajans adı ve seviyesi görünür).

**Canlı sıralama (SIRALAMA ekranı)**
- Skor, para ve seviyeye göre sıralama; ilk üçe madalya, kendi satırın altın renkli.
- Skor = seviye×1000 + para/10 + koloni×2000 + başarım×300 + başarılı görev×150 + koloni seviyesi×500.
- **Bu cihaz:** kampanyalar otomatik olarak yerel listeye yazılır.
- **Çevrimiçi:** `server/leaderboard_server.py` (anahtarsız, CORS açık, doğrulama + hız sınırı) bir sunucuda çalıştırılıp
  adresi AYARLAR > OYUN'a girilir; tablo 20 sn'de bir yenilenir ve skor açılışta gönderilir. Oyun dosyasında API anahtarı yoktur.
  Tarayıcı sürümü (GitHub Pages, HTTPS) yalnız **HTTPS** sunucuya bağlanabilir; düz HTTP adresi tarayıcı tarafından engellenir.
  Varsayılan olarak hiçbir sunucu ayarlı değildir; ayarlanana kadar sıralama yalnız bu cihazdadır.

**NOVA yapay zekâ (AI KONTROL MERKEZİ'nde yazılı soru kutusu)** — `aetherx/nova_ai/`
- Serbest metinli Türkçe/İngilizce sorular (diğer dillerde yanıtlar İngilizce). İnternete ya da dil modeline bağlı değildir;
  kurallar, sözlükler ve gerçek verilerle çalışır, bilmediğini uydurmaz.
- Bilgi tabanı: Güneş, 8 gezegen, Ay, Phobos, Deimos, Ceres, Galileo uyduları, Titan, Enceladus, Triton, Plüton —
  NASA Planetary Fact Sheet değerleri, öne çıkan bilgiler, gerçek görevler (Apollo 11'den Europa Clipper'a), koloni tehlikeleri.
- Hesaplar: Hohmann transfer süresi ve Δv, fırlatma pencereleri (sinodik dönem), sinyal gecikmesi, kaçış ve yörünge hızı,
  roket denklemi (Isp + kütleler), başka gezegende ağırlık ve zıplama, güneş ışınımı, birim çevirme.
- Oyun durumu: depo, yakıt, ekip sağlığı, sıradaki araştırma önerisi, son roket tasarımının kontrolü, bir hedefe gitmek için
  gerekenler, koloni ayrıntıları, skor ve yerel sıra.
- Sözlük (30+ kavram: delta-v, Isp, TWR, Max-Q, Lagrange, ISRU…), oyun rehberi, bilgi yarışması, bağlam belleği
  ("peki ya Venüs?"), Türkçe ek uyumu (Mars'ta, Venüs'e, Dünya'nın).

**Grafik**
- Gezegen parlaması fiziksel atmosfer halesi: üstel yoğunluk, aydınlık tarafa ağırlık, terminatörde gün batımı tonu;
  havasız cisimlerde hale yok.
- Havasız cisimler (Ay, Merkür…) için Ay-Lambert yansıma modeli: gerçek fotoğraflardaki gibi keskin terminatör, dolunayda
  kenar kararması yok. Dünya'da bulutlar yüzeye gölge düşürür.
- Kolonide gerçek gölgeler: binalar ve kolonistler güneşe göre zemine izdüşülür, yumuşak kenarlı.

**Optimizasyon**
- Gölge yumuşatma yalnız gölgelerin kapladığı bölgede; kararmış manzara önbellekte; toz zerreleri numpy ile toplu
  hesaplanıp tek `blits` çağrısıyla çiziliyor (zerre çizimi ~4 kat hızlı). Koloni ekranı ~%5 daha hızlı.

## Sürüm 3.9 — Gerçekçi 3B hayvanlar, gerçekçi iniş, daha fazla para, optimizasyon

* **Başlangıç parası:** 1.000 yerine 10.000.
* **Görülen hayvanların 3B çizimleri** ([`aetherx/creature3d.py`](aetherx/creature3d.py)):
  * Keşfedilen her hayvan genomundan 3B olarak kurulur.
  * Gövde planları: dört ayaklı, ayı, kertenkele, kuş, balık, köpekbalığı, fok, böcek, kril/plankton.
  * Çizim: piksel başına ışık, parlama, kenar ışığı, ortam gölgesi, desen (çizgi, benek, pul, kürk), zemin gölgesi, 2x süper örnekleme.
  * YAŞAM'daki yeni **GÖRÜLEN HAYVANLAR** sekmesinde bütün keşfedilenler 3B kartlarda; seçilen tür dönen büyük
    görünümde, evrimle çıkanların atası da yazılı.
  * Biyom kesitinde ve tür ayrıntısında da 3B hayvanlar kullanılır.
* **Daha gerçekçi YAŞAM görselleri:** hava perspektifli katmanlı dağlar, bulutlar, ufuk pusu, dokulu zemin ve çakıllar,
  gölgeli ağaçlar.
* **Daha gerçekçi iniş modülü:**
  * Fizik: yakıt yandıkça araç hafifler (Tsiolkovsky, Isp ≈ 311 s); motor ~0,25 s gecikmeyle tepki verir.
  * Apollo'daki gibi 1,7 m'de "temas ışığı"; iniş bacakları amortisörlü, ayak tabanlı ve temas sondalı.
  * Güneş yönüne düşen gölge; vakumda geniş ve soluk, atmosferde görünür egzoz.
  * Toz: Ay'da havasız ortamda düz uçan toz, Mars ve Venüs'te kabaran toz.
  * Zemin: aydınlatılmış yüzey, gölgeli kayalar.
* **AJANS > DAHA FAZLA:** kaynaklar ve eklenemeyenler; Türkçe, İngilizce, Almanca, Fransızca, İspanyolca ve Rusça.
* **Optimizasyon (görüntü kısılmadan):**
  * Yıldız alanı ve Atlas kaya kuşağı numpy ile toplu çiziliyor; yörünge renkleri toplu hesaplanıyor.
  * Koloni 3B'de ekran dışı ve görünmeyen (piksel altı) yüzler atlanıyor.
  * Atlas ekranı: kare süresi 28,5 → 21,5 ms.

## Sürüm 3.8 — Yaşayan NPC'ler

* **Kimlik:** her NPC'nin kalıcı adı, kişilik özelliği, boyu, ten ve saç rengi, aksesuarı var ([`aetherx/npc.py`](aetherx/npc.py)).
  * Özellikler: çalışkan, meraklı, sakin, neşeli, titiz, uykucu, sosyal, cesur.
  * Kişilik yürüme hızını, çalışma süresini ve mola sıklığını etkiler.
* **Kıyafet ve kask:** astronotlar kask takar (vizör yansıması, kask kenarı, sırt çantası, eldiven, çizme). Kıyafet yere göre değişir:
  * Ay: beyaz kıyafet, altın vizör.
  * Mars: pas tonlu, tozlu kıyafet.
  * Venüs: gümüş ısı kıyafeti.
  * Jüpiter istasyonu: lacivert-altın üniforma, şeffaf kask ve ışıklı rozet.
* **Ajans üssü:** binaların önünde personel çalışır ve yaya yolunda yürür.
  * Araştırma merkezinde araştırmacılar teleskop, tezgâh ve tabletle araştırma yapar.
  * Hangarda kaynak ve bakım, depodan hangara sandık taşıma, yakıt deposunda bakım yapılır.
  * Mola verip başka binalara uğrarlar; gece yalnızca vardiya çalışır.
* **Bina içi:** bir binaya tıklayınca panelin arka planında, yarı saydam olarak içeride çalışan NPC'ler görünür.
* **Koloni:** kolonistler rollerine göre iş seçer ve elde aletle çalışır.
  * İşler: madende kazma ve maden taşıma, kulübede tabletle araştırma, parkta bitki sulama, spor salonunda antrenman,
    hastanede muayene, okulda ders, yapımı süren binada çekiçle inşaat.
  * Bir kolonist seçilince adı, kişiliği ve o anki işi görünür.

## Sürüm 3.7 — Açılışta Ultra + sınırsız FPS, genişletilmiş ayarlar

* Oyun her açılışta **Ultra** kalite ve **sınırsız FPS** ile başlar.
  * Kapatmak için: AYARLAR > PERFORMANS > "Açılışta en yüksek ayar".
* **Yeni PERFORMANS kategorisi:**
  * Hazır ayarlar: Performans, Dengeli, Yüksek, Ultra.
  * FPS sınırı: 30, 60, 120, 144 ya da sınırsız.
  * Dinamik kalite: FPS 6 saniye 30'un altında kalırsa kalite bir kademe düşer; varsayılan olarak kapalı.
  * 3B süper örnekleme, FPS göstergesi, kare süresi grafiği.
* **Diğer kategorilere eklenenler:**
  * Görüntü: parlaklık.
  * Oyun: oyun hızı (×0,5 – ×4), bildirim süresi.
  * Erişilebilirlik: yüksek kontrastlı paneller.
* Her kategoride "Bu kategoriyi sıfırla" düğmesi var.

## Sürüm 3.6 — Görsel YAŞAM ekranı, temiz ses, ayrıntılı ayarlar

* **YAŞAM görselleri** ([`aetherx/life_art.py`](aetherx/life_art.py)), hepsi Yaşam Motoru verisinden prosedürel çizilir:
  * **Gezegen sekmesi:** NASA dokulu dönen küre (kurgusal gezegenlerde temsilî), atmosfer halesi, biyosfer halkası, kutup ışıkları,
    yaşanabilirlik radar grafiği ve kökeni anlatan zincir diyagramı (amino asit → protohücre).
  * **Yaşam sekmesi:** hareketli biyom dioraması. Gökyüzü atmosferden, zemin biyomdan gelir; canlı sayısı biyokütleyle orantılı.
    Gün-gece döngüsü ve fırtına var. Her türün genomundan bir figürü, seçili tür için büyük portre, figürlü besin ağı.
  * **Zaman çizelgesi:** Dünya'nın resimli jeolojik şeridi (yayımlanmış tarihler) ve alemlere göre yığılmış tür grafiği.
  * **Olaylar:** olay simgeleri ve canlandırma (meteor, volkan, buzul, kuraklık, fırtına, radyasyon...).
  * **Ses gözlemevi:** katmanların gerçek dalga biçimleri.
* **Ses temizliği:**
  * Bütün seslerden geçen ortak bir son işleme zinciri var. DC kayması ve 25 Hz altı uğultuyu temizler, 14 kHz üstü tıslamayı
    yumuşakça keser. Başta ve sonda kısa geçiş yaptığı için tık kalmaz; tanh doyumu (bozulma) kaldırıldı.
  * Ham beyaz gürültü yerine bant sınırlı gürültü kullanılıyor; fırlatmadaki rastgele çatırtı dürtüleri kaldırıldı.
  * Kare ve testere dalgaları bant sınırlı yapıldı (örtüşme yok).
  * Yankı artık FFT evrişimiyle üretiliyor; metalik çınlama yok.
  * Müzik döngülerinde kuyruklar başa sarılıyor, döngü dikişi tıksız.
  * Kanallar toplanınca kırpılma olmasın diye karıştırma payı bırakıldı.
  * Bozulmasız bir "ani yüksek sesleri sınırla" eklendi.
  * Test: [`tests/test_audio_clean.py`](tests/test_audio_clean.py).
* **AYARLAR ekranı:** ana menüden ve AJANS'tan açılır, tercih dosyasında saklanır.
  * Görüntü: kalite kademesi, parlama, toz zerreleri, yıldız yoğunluğu, parçacık miktarı, sinematik efektler, FPS sınırı,
    FPS göstergesi, tam ekran.
  * Ses: ana ses, müzik, efekt, ortam, arayüz ve NOVA sesi; arka planda susturma; ses testi.
  * Oyun: NOVA ipuçları, otomatik kayıt aralığı, açıklama balonları.
  * Erişilebilirlik: hareketi azalt, ekran sarsıntısı, altyazı, mono, tiz azaltma, ses sınırlayıcı, oyun imleci.
  * Dil, kontrol listesi ve veri (kaydet, sıfırla, sil).

## Sürüm 3.4 — Yaşayan Gezegenler ve Kozmik Ses Motoru

Yeni **YAŞAM** ekranı (üst menü). Kod: [`aetherx/life/`](aetherx/life/) (KOZMOGENİS Life Engine),
[`aetherx/cae/`](aetherx/cae/) (Cosmic Audio Engine), arayüz [`aetherx/scenes/life.py`](aetherx/scenes/life.py),
testler [`tests/test_life_audio.py`](tests/test_life_audio.py) (25 test; CI: `AETHER-X testleri`).

- **Cızırtı giderildi.** Ortam seslerinin tabanı beyaz gürültüydü; kayan ortalama süzgeç tizleri geçirdiği için
  sürekli tıslama vardı (ör. koloni sesinde enerjinin %1,9'u 8 kHz üstünde). Gürültü artık frekans uzayında bant
  sınırlı üretiliyor (%0,00), döngüler dikişsiz; ses tamponu 512 → 2048 (tarayıcıda 4096) örnek ve `pre_init`
  artık `pygame.init()`'ten önce; sert kırpma yerine yumuşak sınırlayıcı; iniş motoru 0,09 sn'de bir çalan
  "vuruş" yerine sürekli motor döngüsü.
- **Gezegen çevresi (NASA):** NSSDC bilgi tablolarından kütle, yarıçap, yerçekimi, dönüş/yörünge, Güneş ışınımı,
  manyetik alan, basınç, **atmosfer bileşimi** (Mars CO₂ %95,1 · N₂ %2,59 · Ar %1,94; Venüs CO₂ %96,5; Dünya N₂ %78,08 ·
  O₂ %20,95; Jüpiter H₂ %89,8 · He %10,2), sıcaklık. Ses hızı ideal gaz yasasından: Dünya 341 m/s, Mars 232 m/s
  (Perseverance ölçümü ~240 m/s), Ay'da vakum.
- **Yaşanabilirlik ≠ yaşam:** 5 sınıf (elverişli / olası / aşırı / elverişsiz / yetersiz veri) ve gerekçeleri;
  "yaşam bulundu mu" ayrı tutulur (NASA: yalnız Dünya).
- **Yaşamın kökeni:** bilimsel hipotezler (hidrotermal baca, RNA dünyası, lipit kesecikleri, gölcükler, panspermi)
  ile kurgusal senaryolar ayrı etiketli; küçük prebiyotik tepkime ağı (oyun modeli).
- **Mikrop, bitki, hayvan, evrim, ekosistem:** genomlu türler; Lotka–Volterra besin ağı (Holling doyması, avcı
  girişimi, Kleiber metabolik ölçeklemesi), döküntü ve ayrıştırıcılar, karbon/azot/oksijen/su döngüleri;
  mutasyon, doğal seçilim, nötr sürüklenme, darboğaz, göçle izolasyon, türleşme, yok oluş.
- **Dünya gerçek:** 20 gerçek canlı grubu (temsilî özelliklerle) ve yayımlanmış jeolojik tarihler (3,7 milyar yıl
  önce ilk izler, Büyük Oksijenlenme, Kambriyen, 5 büyük yok oluş, K-Pg). Ay/Mars/Venüs/Jüpiter: "yaşam
  bulunmamıştır"; isteğe bağlı kurgusal mikrobiyal senaryo. 6 kurgusal ötegezegen (Dünya benzeri, okyanus, buz,
  volkanik, kurak, radyasyonlu) — bütün canlılar **KURGUSAL** etiketli.
- **Çevresel olaylar:** volkan, meteor, kuraklık, buzul dönemi, aşırı sıcak, atmosfer, deniz seviyesi, radyasyon,
  yıldız patlaması, fırtına → çevre + popülasyon + zaman çizelgesi + ses. Zaman ×1 yıl/sn … ×1 milyon yıl/sn.
- **Kozmik Ses Motoru:** atmosfere göre rüzgâr/yağmur/gök gürültüsü (Mars ~20 dB kısık, tizleri sönük; Venüs yoğun
  alçak frekans; Ay'da dış ses yok, yalnız araç içi), okyanus ve su altı, jeoloji, yalnız rüzgârda yaprak hışırtısı,
  **popülasyon tabanlı canlı katmanı** ve türün biyolojisinden türetilen sesler (büyük beden = alçak ses), mikrobiyal
  sesler "görsel-işitsel temsil" etiketli, motor sesi vakumda "sinematik" etiketli. Konumsal ses (yön, uzaklık,
  mağara/su altı/kabin profili), olay yöneticisi (öncelik, yineleme koruması, ses bütçesi), dinamik müzik (yumuşak
  geçiş, en kısa kalma süresi), 10 kategori ses ayarı, mono, kulaklık, altyazı, yüksek frekans azaltma, ani ses
  sınırlama (ayarlar kaydedilir), bellek bütçeli önbellek, performans sayaçları.
- **Ses Gözlemevi:** ortam katmanları, akustik profil, konumsal ses testi, olay → ses günlüğü (geliştirici),
  performans ve ses varlığı künyeleri (hepsi özgün prosedürel sentez; lisans gerektiren kayıt yok).

## Sürüm 3.3 yenilikleri

- **Yeni isim: AETHER-X.**
- **NASA görüntüleriyle gezegenler:** Dünya NASA Blue Marble (gündüz) + Black Marble 2023 (gece ışıkları),
  Ay NASA LRO renkli mozaiği, Mars NASA Mars Trek Viking MDIM 2.1 mozaiği, Jüpiter NASA/JPL Cassini haritası
  (PIA07782). Bütün 3B gezegen çizimleri (menü, atlas, yolculuk, koloni) bu dokuları kullanır; dosya yoksa eski
  prosedürel dokuya dönülür. İndirme aracı ve kaynaklar: [`tools/fetch_nasa_maps.py`](tools/fetch_nasa_maps.py).
  Venüs'ün görünür ışıkta yüzeyi görünmez; bulut örtüsü prosedürel kalır.
- **NASA verileri:** Yerçekimi, çap, kaçış hızı, sıcaklık, dönüş süresi, gün uzunluğu, basınç, uydu sayısı,
  yörünge süresi ve uzaklık NASA NSSDC Gezegen Bilgi Tablosu'ndan (`aetherx/data.py` → `NASA`).
  Gezegen kartlarındaki yerçekimi değerleri gerçek m/s² oldu (Jüpiter 2,5 g yerine 24,79 m/s² · 2,53 g).
- **Yeni ana menü:** Solda kampanya düğmeleri, sağda **canlı Güneş Sistemi**: Ay, Venüs, Mars ve Jüpiter NASA
  dokularıyla, NASA dönüş sürelerine oranla (×890 hızlandırılmış) gerçekten döner; Mars'ta toz fırtınaları
  kabarır, Venüs ters yönde döner. Bir gezegene tıklayınca NASA bilgi kartı açılır.
- **Yükleme ekranları:** Tarayıcıda oyun inerken NASA haritalarıyla dönen gezegenler, gerçek indirme aşamaları
  ve kaynaklı NASA bilgileri (eski gri pygbag sayfası yerine). Oyun içi yüklemede her gezegen NASA dokusu hazır
  olunca belirir.

## Sürüm 3.2 yenilikleri

- **Motorlu iniş (yeni mini oyun):** Ay, Mars ve Venüs'e inen görevlerde yolculuktan sonra iniş aracını sen
  indiriyorsun. Motoru yak (W / SPACE / basılı tut), aracı eğ (A-D / ekrana dokun), iniş alanına yumuşakça kon.
  Yerçekimleri gerçek (1,62 · 3,71 · 8,87 m/s²); Mars'ta ince, Venüs'te kalın atmosfer düşüşü etkiler.
  Göstergeler: irtifa, dikey/yatay hız, eğim, hedefe mesafe, yakıt (Δv) ve güvenli bandı gösteren düşüş şeridi.
  NOVA 1000/500/100/30 metrede seslenir, "motoru yak" uyarısı verir; **L** ile NOVA iniş desteği aracı kendisi
  indirir (bir tuşa basınca kumandayı sana bırakır). Koloni varsa koloninin iniş alanına inilir.
  Sonuçlar: yumuşak iniş · hassas iniş (alanın içine) ek kargo · sert iniş (gövde hasarı) · başarısız iniş
  (acil kalkışla yörüngeye dönüş, yüzey madenciliği yok) · **X** ile iniş iptali. Yakıt bütçesi, NOVA güdümünün
  o arazide harcayacağı Δv'ye ve yolculuktan kalan yakıta göre hesaplanır. Jüpiter (gaz devi) için iniş yok.

## Tarayıcı prototipi (Python / pygame, eski adı AETHER-X)

## ▶ Tarayıcıda oyna

**https://ceablood.github.io/Nasa-space-apps/**

Kurulum gerekmez. Sayfa açılınca yükleme ekranı gelir: Python, pygame ve numpy tarayıcıya iner (ilk açılışta
~20 MB), sonra oyunun görselleri hazırlanır ve oyun başlar. Ses için ekrana bir kez tıklaman istenir.
Tarayıcı sürümü varsayılan olarak YÜKSEK kalitede başlar; güçlü bir bilgisayarda AJANS → Ayarlar'dan
ULTRA'ya alabilirsin. Kayıt tarayıcı sekmesi açık kaldığı sürece tutulur; kalıcı kayıt için masaüstü
sürümünü kullan.

Ekran görüntüleri: [`screenshots/`](screenshots/) · Tanıtım görseli promptu: [`KEY_ART_PROMPT.md`](KEY_ART_PROMPT.md)

Kendi uzay ajansını kur, 12 alanlı fırlatma üssünü büyüt, roket tasarla,
fırlat, yolculuğu yönet, gezegenlere in, koloni kur ve en sonunda
**Jüpiter'de dev koloniyi** kur.

## Sürüm 3.1 yenilikleri

- **Gerçekçi fırlatma üssü:** Üs binaları artık üç çeyrek bakışta gerçek 3B modeller: beton/çelik/cam
  malzemeler, panel derzleri, pencere bantları, çatı üniteleri, yere düşen gölge, gece yanan pencereler.
  Montaj Hangarı dev kapılı Araç Montaj Binası tarzında; kilitli binalar iskeleli inşaat alanı olarak görünür.
  Zemin dokulu çim, asfalt yollar ve derzli beton rampa sahası.
- **Uyumlu renk paleti:** Saf beyazlar kırık beyaza ve sıcak açık griye çekildi; aşırı parlayan yüzey yok.
- **Optimizasyon:** Masaüstünde ekranlar 2–5 kat hızlı; tarayıcıda menü ~2×, fırlatma ~4× hızlı
  (piksel formatı uyumu, opak sinematik katmanlar, önbellekli arka plan/ufuk/huzme, 3B koloni paketleme).
- **NASA verileri:** Uydu sayıları NASA'nın Ekim 2026 toplamıyla (461) uyumlu.

## Sürüm 3 yenilikleri

- **Tarayıcı sürümü:** Oyun pygbag ile WebAssembly'ye derlenip GitHub Pages'te yayınlanır (`.github/workflows/pages.yml`).
- **Sinematik katman her yerde:** Hacimsel ışık huzmeleri, pus, toz zerreleri, fırça dokusu ve tamamlayıcı
  renk uyumu artık bütün ekranlarda (hangar, AR-GE, ekip, görevler, depo, görev kontrol, ajans, yolculuk, üs,
  NOVA odası). Tüm ekrana yumuşak parlama (bloom). Roket, güçlendirici ve asteroitlerde renkli kenar ışığı,
  mor gölge kenarı ve fırça dokusu. Ayrıntılar: [`KEY_ART_PROMPT.md`](KEY_ART_PROMPT.md).
- **Daha yüksek grafik:** Varsayılan kalite ULTRA; 3B kolonide kaliteye bağlı süper örnekleme; daha çok halka parçacığı.
- **Pürüzsüz Dünya kıyıları:** Ana menüdeki Dünya'da basamaklı kıyı çizgileri giderildi.
- **Düzeltme:** SİNEMATİK EFEKTLER ayarı artık yeniden açılışta hatırlanıyor.

## Sürüm 2 yenilikleri

- **Dil profili:** İlk açılışta Türkçe / English / Deutsch / Français / Español / Русский seçilir; seçilen dilde menüler, NOVA, olaylar, atlas bilgileri dahil tüm metinler gelir. Ayarlar ekranından (AJANS) dil anında değiştirilebilir.
- **Astronot kıyafeti:** Başlangıçta Zırhlı (dayanıklı, hareketi zor), Çevik (hareketli, kırılgan) veya Dengeli seçilir. AR-GE → ASTRONOT KIYAFETİ sekmesinde Zırh Katmanı, Eklem Mekaniği ve Yaşam Destek geliştirilir. Kıyafet; hastalanma, yaralanma, tamir hızı, maden toplama ve oksijen süresini etkiler.
- **ATLAS (3B Güneş Sistemi):** Güneş merkezde, gezegenler gerçek periyotlarıyla Kepler yörüngelerinde döner. Fareyle sürükle = döndür, tekerlek = yakınlaştır, hız 0/1/5/25/100×. Asteroit kuşağı (Kirkwood boşlukları, toplu aileler), Jüpiter Truva asteroitleri ve Kuiper kuşağı.
- **Gezegen görünümü:** Güneş ışığıyla aydınlanan dönen küreler, gece/gündüz sınırı, Dünya'da kıta haritası, şehir ışıkları, bulutlar ve yapay uydular (ISS, Hubble, İMECE, GPS, Türksat 6A). Satürn'de C/B/A halkaları, Cassini boşluğu, halka gölgesi ve yörüngede dönen kaya parçaları; 19 Satürn uydusu ayrıntılı bilgiyle. Uranüs ve Neptün gaz gezegenleri arasında.
- **3B koloni görünümü (KOLONİ ekranı):** Koloniler artık gerçek zamanlı 3B sahnede. Kamera: tekerlekle yakınlaştırma (yaklaştıkça ufka eğilir), orta/sağ tık sürükleyerek 360° yörünge ve 20°–80° eğim, WASD/ok tuşları ve ekran kenarıyla kameranın baktığı yöne göre kaydırma, Q/E ile döndürme; bir kolonisti tıklayınca kamera onu takip eder (F: odakla). Binalar modüler 3B modeller (kubbe, kule, beşik çatı, pencereler, baca/anten, varil ve sandıklar); inşa ederken önce yeşil/kırmızı hayalet önizleme çıkar (R: 90° döndür), sonra Plan → Temel ve iskele → Çerçeve → Son dokunuşlar aşamalarıyla yükselir. Kolonistler A* yol bulmayla yürür, madende çalışır, sandık taşır, gece evlere dönüp uyur; seçilen kolonistin altında halka, üstünde durum ve can çubuğu görünür. Gece/gündüz güneşi, yumuşak gölgeler, gece pencere ve fener ışıkları, ACES renk tonu ve minyatür etkisi veren tilt-shift bulanıklığı eklendi. "2B GÖRÜNÜM" düğmesiyle eski görünüme dönülebilir.
- **Sinematik görüntü katmanı (AJANS → Ayarlar → SİNEMATİK EFEKTLER):** Elle boyanmış stilize bir görünüm için menüde, 3B kolonide, atlasta ve fırlatmada hacimsel ışık huzmeleri, havada süzülen toz, ufka doğru pus, fırça ve tuval dokusu, sıcak ışık / soğuk-mor gölge renk uyumu ve vinyet. 3B kolonide ayrıca süper örneklemeyle kenar yumuşatma, mürekkep konturları, renkli kenar (rim) ışığı, temas gölgesi (AO), zeminden sıçrayan ışık ve yapraklarda ışık geçirgenliği (SSS). Gezegenlerde siluet ayıran kenar ışığı. Yavaş bilgisayarlarda kapatılabilir; arayüz yazıları bu efektlerden etkilenmez.
- **Fırlatma:** Rampa ve kule yerde kalır; roket bulutları, Max-Q yoğuşmasını, kademe ayrılmasını ve kaporta atımını geçip eğrisi görünen Dünya'nın üstünde uzaya çıkar.
- **Boyalı arka planlar:** Ana menüde yörüngeden şafak, kolonilerde Ay, Mars, Venüs ve Jüpiter manzaraları; fotogerçekçi ama elle boyanmış görünümlü, yazısız (her dilde aynı).
- **Mars toz fırtınaları:** Zaman zaman yükselen, hareket eden renkli toz bulutları.
- **Ses:** Her ekranın kendi ortam sesi (üs, hangar, kontrol, uzay, koloni, laboratuvar) ve yeni efektler.
- **Görüntü kalitesi:** AJANS → Ayarlar'da STANDART / YÜKSEK / ULTRA / MAKSİMUM (varsayılan: ULTRA; kalite arttıkça 3B kolonide kenar yumuşatma, yıldız ve halka parçacığı sayısı da artar). MAKSİMUM 2048×4096 piksel gezegen dokuları kullanır; ilk açılışta her doku bir kez üretilir (10-30 sn) ve ~/.aetherx/tex klasörüne kaydedilip sonraki açılışlarda anında yüklenir. Gezegenler sinema tipi ton eşleme (ACES), yumuşak gün/gece geçişi ve hafif ortam ışığıyla çizilir; küçük çizimlerde kumlanmayı önlemek için düşük çözünürlüklü doku seviyesine (mip) inilir. Oyun 1600×900 tuvalde çizilip tam ekranda ekran çözünürlüğüne (4K dahil) ölçeklenir; pygame ile gerçek 8K iç çizim pratik değildir.

## Kurulum ve çalıştırma

1. Zip dosyasını önce bir klasöre **çıkar** (zip'in içinden çalıştırma).
2. **Windows:** `BASLAT.bat` dosyasına çift tıkla.
   **macOS / Linux:** klasörde terminal aç, `sh baslat.sh` yaz.
3. İlk açılışta eksik kütüphaneler (pygame-ce, numpy) otomatik kurulur (internet gerekir)
   ve görseller bir kez hazırlanır (yükleme ekranı, ~10-15 sn). Sonraki açılışlar hızlıdır.

Elle kurmak istersen:

```bash
python -m pip install -r requirements.txt
python main.py
```

- Python 3.8 veya üstü gerekir (3.14 ve 3.15 dahil). Python yoksa: https://www.python.org/downloads/
  (Windows'ta kurarken **"Add python.exe to PATH"** kutusunu işaretle.)
- **Neden pygame-ce?** Klasik `pygame` paketinin Python 3.14 ve sonrası için hazır kurulumu yok;
  `pip install pygame` bu sürümlerde başarısız olur. `pygame-ce` aynı arayüzü sunar ve her sürümde kurulur.
  Python 3.13 veya altında klasik pygame kuruluysa oyun onu da kullanabilir.
- Hiçbir resim ya da ses dosyası gerekmez; bütün görseller ve sesler kodla üretilir.
- Kayıt: `~/.aetherx/kampanya.json` (otomatik kaydedilir). Doku ve boyalı arka plan önbelleği: `~/.aetherx/tex`, `~/.aetherx/paint`.

### Oyun açılmazsa

- Oyun bir hatayla kapanırsa ekranda neden gösterilir ve oyun klasörüne `aetherx_hata.txt` yazılır.
  Bu dosyayı paylaşırsan sorun hemen bulunur.
- "pygame kurulamadı" hatası: komut satırında `python -m pip install pygame-ce numpy` çalıştır.
- Hem `pygame` hem `pygame-ce` kuruluysa çakışabilirler: `python -m pip uninstall -y pygame pygame-ce`
  ve ardından `python -m pip install pygame-ce numpy`.
- Bilgisayar yavaşsa: AJANS → Ayarlar'da **SİNEMATİK EFEKTLER: KAPALI** ve **GÖRÜNTÜ KALİTESİ: STANDART** seç.
  3B koloni yavaş çalışırsa kenar yumuşatmayı kendiliğinden kapatır.

## Oyun döngüsü

Ajans adını seç → Fırlatma Üssü → Montaj Hangarı'nda roket tasarla →
Rampadan fırlat → Görev Kontrol'den takip et → Yolculuk (mini oyun) →
Gezegene in / koloni kur → Maden topla → Dünya'ya dön → Para ve Araştırma
Puanı kazan → Araştır → NOVA'ya sor → Daha iyi roket tasarla → Daha uzağa git

## Kontroller

| Nerede | Tuş | İşlev |
|---|---|---|
| Her yer | Fare | Butonlar, kartlar, binalar |
| Her yer | F11 / F3 | Tam ekran / FPS göstergesi |
| Her yer | ESC | Geri dön / duraklat |
| Hangar | SPACE | Fırlat |
| Hangar | N | NOVA'ya sor |
| Yolculuk | Fare veya W-S | Roketi yukarı-aşağı oynat |
| Yolculuk | SPACE / sol tık | Lazer ile asteroit kır |
| Yolculuk | A / D | Yavaşla / hızlan |
| Yolculuk | R | Tamir et (Mühendis gerekir) |
| Yolculuk | F | Fotoğraf çek (Kamera gerekir) |
| Yolculuk | N | NOVA'ya sor |
| Yolculuk | TAB | Büyük Görev Kontrol haritası |

## Sistemler

- **Ajans adı:** NOVA sana kişisel adınla değil, ajansının adıyla
  seslenir. Ajans adı üs tabelasında, roket gövdesinde, Görev Kontrol'de,
  koloni bayrağında ve başarım mesajlarında görünür. Ayarlar'dan 500 Para
  karşılığında değiştirilebilir.
- **12 alanlı üs:** 3 rampa (A küçük, B orta, C dev roket), Araştırma
  Merkezi, Astronot Merkezi, Depo, Görev Tahtası, AI Kontrol Merkezi
  (NOVA), Görev Kontrol, Yakıt Deposu, Montaj Hangarı, İletişim Kulesi,
  Sağlık Merkezi ve Eğlence Alanı. Üs gece-gündüz döngüsüne sahiptir.
  Yollarda araçlar dolaşır; bir binaya tıklayınca kamera yakınlaşır ve
  bina paneli açılır.
- **Roket tasarımı:** 7 gövde, 6 motor, 5 elektrik kaynağı, 4 anten ve
  4 araştırma yükü var (bunların 3'ü seçilir). Yakıt kaydırıcısı, 3 barlı
  risk paneli, 5 saniyelik simülasyon ve NOVA yorumu bulunur. NOVA sorunlu
  parçayı kırmızı daireyle gösterir.
- **Yolculuk:** Yakıt, Oksijen ve Elektrik barları ile Parça Durumu
  (Motor, Panel, Anten) izlenir; can barı yoktur. Yolda asteroitler
  (normal, dev, altın, buz, madenli), uzay çöpü, Güneş Fırtınası, yakıt
  istasyonu, kayıp uydular, Yıldız Tozu ve fotoğraf fırsatları çıkar.
  Rotada karanlık bölge, ısı ve radyasyon kuşakları vardır.
- **5 astronot tipi:** Pilot, Mühendis, Bilim İnsanı, Doktor ve Madenci.
  Astronotlar yorulur, hastalanır ve dinlenir. Eğitimle rütbeleri artar.
- **Araştırma:** Plandaki 14 araştırma ve Venüs için Sıcaklık Kalkanı.
  Araştırma Merkezi'nin seviyesi araştırma süresini (120 / 60 / 40 / 24 sn)
  ve para maliyetini (%0 / 20 / 40 / 60 indirim) belirler.
- **Gezegenler ve koloniler:** Ay, Mars, Venüs ve Jüpiter. Koloniler
  mutluluk, nüfus, yemek ve seviye değerlerine sahiptir. Hastane, Okul ve
  Park gibi binalar açılır. Ay ile Mars arasında ticaret yolu kurulabilir.
- **Madenler:** Ay Taşı 10, Kızıl Maden 50, Sülfür 80, Gaz Madeni 200 ve
  Asteroit Cevheri 35 Para eder. Madenci varsa asteroitten 2 kat maden
  gelir.
- **Görevler ve başarımlar:** Günlük ve haftalık görevler, 18 başarım ve
  NOVA'nın özel görev önerileri.
- **Eski koddan korunan sistemler:** Ajans seviyesi ve XP, rozetler,
  itibar, rastgele ajans kararları (olaylar), diplomasi (NASA, ESA, JAXA,
  ISRO, TUA ile anlaşmalar), günlük ve kayıt/yükleme.
- **Ses:** Fırlatma gürültüsü, uzay ambiyansı, fırtına müziği, neşeli
  koloni müziği, NOVA'nın robot sesi, butonlarda "tık" ve parça takarken
  metal "tak" sesi.

## Zaman

1 gerçek saniye, oyunda 2 dakikaya denk gelir. Yani oyundaki "2 saat",
gerçekte 60 saniyedir. Günlük gelir, koloni üretimi, yakıt üretimi, iyileşme
ve dinlenme bu oyun saatine göre işler.

## Dosya yapısı

```
main.py                  giriş noktası (bağımlılık kontrolü, otomatik kurulum, hata günlüğü)
BASLAT.bat / baslat.sh   tek tıkla başlatıcılar
requirements.txt         pygame-ce, numpy
aetherx/config.py        ekran, renkler, zaman, kayıt yolları
aetherx/data.py          binalar, parçalar, araştırma, gezegenler, görevler
aetherx/game.py          oyun mantığı (pygame'siz, test edilebilir)
aetherx/rocket.py        tasarım analizi, risk, simülasyon
aetherx/nova.py          NOVA diyalogları, yüzü ve konuşma balonu
aetherx/fx.py            nebula, yıldızlar, parçacıklar, sarsıntı, geçişler
aetherx/ui.py            cam/neon butonlar, paneller, barlar, ikonlar
aetherx/art.py           roket, gezegen, asteroit, astronot çizimleri
aetherx/audio.py         prosedürel ses efektleri ve müzik
aetherx/app.py           ana döngü, üst bar, olay pencereleri
aetherx/i18n.py          çeviri sistemi (6 dil), sayı/birim biçimleri, kalite ayarları
aetherx/lang/            çeviri tabloları (t_*: tr/en/de, x_*: fr/es/ru, atlas_x: atlas metinleri)
aetherx/space3d.py       3B gezegen çizici, prosedürel dokular, halkalar, doku önbelleği
aetherx/atlas.py         gezegen, uydu ve yapay uydu verileri (6 dilde bilgi)
aetherx/colony3d.py      3B koloni: kamera, arazi, modüler binalar, inşaat, kolonist ajanları
aetherx/paint.py         boyalı fotogerçekçi arka planlar (menü ve koloniler)
aetherx/cinema.py        sinematik katman: ışık huzmeleri, toz, pus, fırça dokusu, renk uyumu
aetherx/scenes/*.py      15 ekran (ATLAS dahil)
```

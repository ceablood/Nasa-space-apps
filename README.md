# AETHER-X · Uzay Ajansı Komuta Simülasyonu (Python / pygame)

Kendi uzay ajansını kur, 12 alanlı fırlatma üssünü büyüt, roket tasarla,
fırlat, yolculuğu yönet, gezegenlere in, koloni kur ve en sonunda
**Jüpiter'de dev koloniyi** kur.

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
- **Görüntü kalitesi:** AJANS → Ayarlar'da STANDART / YÜKSEK / ULTRA / MAKSİMUM. MAKSİMUM 2048×4096 piksel gezegen dokuları kullanır; ilk açılışta her doku bir kez üretilir (10-30 sn) ve ~/.aetherx/tex klasörüne kaydedilip sonraki açılışlarda anında yüklenir. Gezegenler sinema tipi ton eşleme (ACES), yumuşak gün/gece geçişi ve hafif ortam ışığıyla çizilir; küçük çizimlerde kumlanmayı önlemek için düşük çözünürlüklü doku seviyesine (mip) inilir. Oyun 1600×900 tuvalde çizilip tam ekranda ekran çözünürlüğüne (4K dahil) ölçeklenir; pygame ile gerçek 8K iç çizim pratik değildir.

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

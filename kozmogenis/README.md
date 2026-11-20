# KOZMOGENİS

Gerçekçi uzay ajansı, roket mühendisliği, koloni ve NPC yaşam simülasyonu.
İki katmandan oluşur:

| Katman | Dil | Durum |
|---|---|---|
| **KozmoCore** (`core/`) — tüm oyun mantığı | Standart C++17, bağımlılıksız | **Derleniyor ve test ediliyor**: GCC, Clang, MSVC (CI), RTTI/istisna kapalı mod, AddressSanitizer + UBSan |
| **Unreal Engine 5 istemcisi** (`unreal/Kozmogenis/`) — 3B sahne + arayüz | UE 5.4 C++ (Slate) | **Henüz derlenmedi** — UE5 kurulu Windows makine gerekiyor (bkz. [docs/UNREAL_KURULUM.md](docs/UNREAL_KURULUM.md)) |

Tarayıcıda hemen oynanan sürüm (AETHER-X, Python/pygame) ayrıdır: https://ceablood.github.io/Nasa-space-apps/

## Çekirdeği derle, test et, oyna

```bash
cmake -S kozmogenis -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure     # 59 test
./build/kozmo_cli --demo                        # uçtan uca otomatik oyun
./build/kozmo_cli                               # terminalde etkileşimli oyun ("yardim")
```

## Sistemler

| Modül | İçerik | Veri / model türü |
|---|---|---|
| `core` | Sonuç/hata türü, günlük, **ortak olay yolu** (tüm sistemler bununla haberleşir), deterministik RNG | — |
| `astro` | 10 gök cismi, Kepler, vis-viva, Hohmann transferi, sinodik periyot, faz açısı, fırlatma pencereleri, görev delta-v bütçesi | **NASA NSSDC Planetary Fact Sheet** (13 Kasım 2026); LEO bütçesi mühendislik yaklaşımı |
| `propulsion` | Motor sınıfları (Merlin/RL10/Raptor/NERVA/iyon sınıfı), çok kademeli Tsiolkovsky, itki/ağırlık, yanma süresi, motor kaybı toleranslı güvenilirlik | Mühendislik yaklaşımı; risk ve maliyet oyun varsayımı |
| `economy` | Arz-talebe duyarlı piyasa fiyatları, kayma ve makas, cüzdan ve hesap defteri | Oyun varsayımı |
| `colony` | Enerji dengesi + batarya, gece/gündüz güneşi (1/r²), üretim zincirleri, yaşam desteği, bakım, nüfus | Fizik + NASA yaşam destek mertebeleri + oyun varsayımı |
| NPC | Kolonist ihtiyaçları (açlık, yorgunluk, moral, sağlık), meslek, fayda tabanlı yapay zekâ, uyku düzeni, beceri gelişimi; **ölçeklenebilir** tam/kaba simülasyon | Oyun varsayımı |
| `gare` | Çalışma zamanı: modül kaydı/bağımlılık, sabit-değişken adım, zaman hızlandırma, olay kuyruğu, servisler, ayarlar, tanılama | — |
| `flight` | Fırlatma fiziği: RK4, USSA 1976 atmosfer, sürüklenme, yerçekimi dönüşü, kademe, motor kısma, yörüngeye giriş | Fizik + mühendislik yaklaşımı |
| `nova` | NOVA çevrimdışı çekirdeği: Türkçe komut, kaynaklı bilgi, tavsiye, onay zorunlu eylemler, isteğe bağlı çevrimiçi bağlayıcı | — |
| `universe` | Tohumlu prosedürel galaksi: yıldız fiziği, yaşanabilir bölge, gezegen türleri, atmosfer tutma, koloni puanı, A* rota | Astrofizik bağıntılar + oyun varsayımı (dağılımlar) |
| `environment` | Uzay havası ve radyasyon: ölçülmüş doz oranları, NASA kariyer sınırı, güneş fırtınası, Mars toz fırtınası, mikrometeoroid | Ölçümler (Chang'e-4, Curiosity RAD, MSL) + oyun varsayımı (sıklık) |
| `research` | Önkoşullu teknoloji ağacı; **kurgusal teknoloji açıkça işaretli** (He-3 füzyon) | Oyun varsayımı |
| `json` + `game` | Görev akışı, fırlatma penceresi zorunluluğu, varışta koloni kurma, yerinde inşa, ticaret, tam kayıt/yükleme (deterministik tekrar) | — |

### Doğrulanan gerçek değerler (testler)

* Falcon 9 sınıfı roket: kalkış ~571 t, itki/ağırlık 1.33, LEO için ~9.4 km/s, 1. kademe ~162 s yanma
* Fizik tabanlı fırlatma simülasyonunda Falcon 9 sınıfı LEO kapasitesi ~23 t (gerçek 22.8 t), Max-Q ~11 km
* Dünya→Mars Hohmann: ~259 gün, v∞ 2.94 km/s, faz açısı 44°, LEO'dan ~3.6 km/s, sinodik periyot ~780 gün
* Dünya→Ay transfer yanması ~3.1 km/s, yolculuk ~5 gün
* NASA tablosundaki yerçekimi ve kaçış hızları kütle/çaptan hesaplananla tutarlı (gaz devlerinde dönüşün merkezkaç etkisi dahil)
* Güneş ışınımı: Dünya 1361, Mars ~586, Jüpiter ~50 W/m²

## Dürüst durum

* Unreal katmanı yazıldı ama **derlenmedi**; ilk derlemede düzeltme gerekebilir. Bu ortamda UE5 yoktur.
* V30 ilerleme raporu: [docs/V30_DURUM_RAPORU.md](docs/V30_DURUM_RAPORU.md) · Cumartesi hazırlığı: [docs/CUMARTESI_HAZIRLIK.md](docs/CUMARTESI_HAZIRLIK.md)
* UE5 geçiş analizi (21 sistem, çakışmalar, eksikler, aşamalar): [docs/UE5_GECIS_PLANI.md](docs/UE5_GECIS_PLANI.md)
* Sitedeki "Windows için indir" düğmesi, `.exe` gerçekten üretilene kadar **eklenmeyecek** (sahte düğme yok).
* Şemadaki 200.000 satırlık hedefe ulaşılmadı. Satır sayısı için dolgu kod yazılmaz; her ekleme test edilerek ilerler.

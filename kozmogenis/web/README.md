# KOZMOGENİS — tarayıcı sürümü (WebAssembly + Three.js)

Unreal Engine 5 istemcisinin kullandığı **aynı C++ çekirdeği** (KozmoCore) Emscripten ile WebAssembly'ye derlenir.
Fizik, iniş güdümü, NPC yaşamı, NOVA, inşaat, görevler, ajans yönetimi ve kayıt formatı tarayıcıda gerçek kodla çalışır.
3B görüntü Three.js (0.169.0, `vendor/`) ile çizilir. Deneysel sürüm; yayın adresi: https://ceablood.github.io/Nasa-space-apps/3d/ (ana oyun sitenin kökündeki Python sürümüdür).

| Dosya | Unreal karşılığı | Görev |
|---|---|---|
| `src/kozmo_web.cpp` | `UKozmoSubsystem` | C ABI köprüsü: `kz_new/tick/state/cmd/...`, arazi mesh tamponları |
| `js/core.js` | — | wasm'ı akışla indirir (gerçek bayt ilerlemesi), JSON komut sarmalayıcıları |
| `js/scene.js` | `AKozmoExpeditionScene`, `AKozmoTerrainActor`, `AKozmogenisColony`, `AKozmogenisNPC` | Arazi (çekirdek yükseklik haritası), gökyüzü, koloni binaları, NPC'ler, iniş aracı, alev/toz |
| `js/hud.js` | `SKozmoCockpitHUD`, NOVA ve yönetim panelleri | 12 göstergeli kokpit, yaşamsal değerler, mini harita, NOVA, diyalog, bina içi, görevler, yönetim (porkchop dahil) |
| `js/main.js` | GameMode + PlayerController | Yükleme sekansı, menü, klavye/fare/dokunmatik, sabit döngü, kayıt |
| `js/loading.js` | — | Sinematik yükleme/menü arka planı (warp yıldız alanı, piksel başına gezegen) |

## Derleme

```bash
# emsdk kurulu ve etkin olmalı (emsdk activate latest)
./web/build.sh          # kozmogenis/ klasöründen çalıştır -> web/dist/kozmo.{js,wasm}
python3 -m http.server -d web 8765   # http://localhost:8765
```

`dist/` depoya işlenir; Pages iş akışı yeniden derlemez, yalnız dosyaların ve wasm başlığının geçerliliğini denetler.

## Test edilenler (headless Chromium, yazılımsal WebGL)

* Yükleme: 6 aşama (arayüz, wasm indirme, çekirdek, WebGL, fizik öz-sınaması, NOVA) — konsol hatası yok.
* Ay: yörüngeden (15 km, 1,67 km/s) iniş desteğiyle iniş, temas 1,3 m/s; araçtan çıkış, bina kapısı, NPC diyaloğu, NOVA,
  yönetim sekmeleri, porkchop (en iyi Mars C3 8,9 km²/s², 260 gün), kayıt (14 KB) ve geri yükleme.
* Mars (125 km atmosfer girişi) ve Titan inişleri: temas 1,3 / 1,2 m/s.
* iPad Pro 11 öykünmesi: dokunmatik algılandı, düşük kalite seçildi, sanal joystick oyuncuyu yürüttü.
* Performans ölçümü: çekirdek `tick` 0,02 ms, `state` 0,22 ms, HUD 0,8 ms. HUD'daki `backdrop-filter` ve her karede
  `innerHTML` yazımı kaldırıldı; bina başına nokta ışığı kaldırıldı; gölgelendiriciler yüklemede derlenir;
  uyarlanabilir çözünürlük kare süresine göre piksel oranını ayarlar.

## Sınırlar (dürüst durum)

* Gerçek bir tablette/GPU'da kare hızı ölçülmedi (test ortamı yazılımsal GPU).
* Ayrıntılı arazi koloni çevresindeki 1,6 km'lik yamadır; dışı tekrar eden dokulu düzlemdir.
* Bina içleri basit kutulardır; konsollar panelden kullanılır. Gün-gece döngüsü görüntüde yoktur (güneş sabit).
* Ses yok.

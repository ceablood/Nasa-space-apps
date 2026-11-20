# Cumartesi — Unreal Engine 5 oturumu hazırlığı

Hedef bilgisayar (V30 §27): AMD Ryzen 5, 16 GB RAM, **dahili** AMD Radeon, ~198 GB boş disk, Windows 10/11 64-bit.

## Önceden kurulacaklar (internet hızına göre birkaç saat sürer — Cumartesiden önce başlat)

| # | Kurulum | Boyut (yaklaşık) | Not |
|---|---|---|---|
| 1 | Epic Games Launcher → **Unreal Engine 5.4** | 40-60 GB | Kurulum seçeneklerinde yalnızca "Windows" hedefi yeterli; diğer platformları kaldırarak yer kazan |
| 2 | **Visual Studio 2022 Community** | 15-25 GB | İş yükleri: *Desktop development with C++*, *Game development with C++*; bileşen: Windows 10/11 SDK, MSVC v143 |
| 3 | **Git for Windows** | 0.3 GB | |
| 4 | **Claude masaüstü uygulaması** | — | Aynı hesapla giriş yap |
| 5 | Repo klonu | — | `git clone https://github.com/ceablood/Nasa-space-apps` (ör. `C:\Projeler\`) |

Toplam ~80-90 GB; 198 GB boş alan yeterli (derleme ara dosyaları için ~30 GB pay kalır).

## Oturumu bu sohbete bağlama

1. Claude masaüstü uygulaması → **Settings → Claude Code → Remote Control** → proje klasörünü (`Nasa-space-apps`) ekle.
2. Bu sohbete dön ve "bağladım" yaz. Klasöre erişim isteği çıkınca onayla.
3. Bundan sonra derleme, hata düzeltme, paketleme ve testleri doğrudan o bilgisayarda yürütürüm.

## Cumartesi akışı (V30 aşamaları)

1. **Phase 0 denetim:** UE sürümü, VS/MSVC, Windows SDK, disk, Git kontrolü → kurulum raporu.
2. **Phase 1:** `Kozmogenis.uproject` için proje dosyaları üret, ilk derleme, hataları düzelt, editörde aç.
3. Çekirdek testleri o bilgisayarda MSVC ile (CI zaten geçiyor).
4. **Phase 2 başlangıcı:** Güneş Sistemi sahnesi, kontrol paneli, NOVA kutusu, fırlatma simülasyonu editörde çalışıyor mu?
5. **Phase 9 öncesi deneme paketi:** Development Win64 paketi → `KOZMOGENIS.exe` editör dışında açılış, kayıt/yükleme testi.

## Dahili ekran kartı için gerçekçi beklenti

* Editör açılır ve çalışır, ancak shader derlemesi ilk açılışta uzun sürer (30-90 dk olabilir).
* Proje, Lumen/sanal gölge/ışın izleme **kapalı** başlar (`Config/DefaultEngine.ini`). Performans ölçülmeden açılmaz.
* Hedef: geliştirme sahnesinde 30-60 FPS (Low/Medium). Ölçüm sonucu rapora yazılacak; ölçülmeden iddia yok.

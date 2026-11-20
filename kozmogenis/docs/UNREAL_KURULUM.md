# KOZMOGENİS Unreal sürümünü derleme

Bu adımlar **Windows 10/11** ve iyi bir ekran kartı (DirectX 12) gerektirir. Tablette yapılamaz.

## 1. Kurulumlar (ücretsiz)

1. **Epic Games Launcher** → Unreal Engine → **5.4** kur (~60 GB).
2. **Visual Studio 2022 Community**: "Desktop development with C++" ve "Game development with C++" iş yükleri,
   Windows 10/11 SDK.
3. **Git** ve bu reponun klonu.

## 2. Projeyi aç

1. `kozmogenis\unreal\Kozmogenis\Kozmogenis.uproject` dosyasına sağ tık → **Generate Visual Studio project files**.
2. `.uproject` dosyasına çift tık → "modüller yeniden derlensin mi?" → **Evet**.
3. Derleme hata verirse hata metnini paylaş; düzeltmeyi repoya gönderirim.
4. Editör açılınca **Play**: Güneş Sistemi sahnesi ve sol üstte KOZMOGENİS kontrol paneli gelir.
   Kamera: WASD + fare (sağ tık basılıyken bak), Q/E aşağı/yukarı.

## 3. Tıklayınca açılan .exe

Editörde **Platforms → Windows → Package Project**. Çıkan klasördeki `Kozmogenis.exe` çift tıkla açılır.

## 4. Otomatik derleme ve siteye bağlama (isteğe bağlı)

Bilgisayarını GitHub'a derleme makinesi olarak bağlarsan, her güncellemede `.exe` otomatik üretilip
GitHub Releases'a yüklenir; sitedeki indirme düğmesi ancak o zaman eklenir.

1. GitHub → repo → Settings → Actions → Runners → **New self-hosted runner** (Windows) adımlarını uygula.
2. Runner'a şu etiketleri ver: `self-hosted`, `windows`, `unreal`.
3. Actions → **KOZMOGENİS Unreal paketleme** → Run workflow.

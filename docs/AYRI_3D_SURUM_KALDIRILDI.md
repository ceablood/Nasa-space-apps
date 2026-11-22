# Ayrı 3D web sürümü kaldırıldı (V3.0 kritik güncelleme)

**Geri dönüş noktası:** commit `c253411` (dal `claude/github-game-code-8eqf8g`). Bu commit'te ayrı 3D web istemcisi
(`kozmogenis/web/`, siteye `/3d/` olarak yayınlanıyordu) eksiksiz durur. Geri almak için:
`git checkout c253411 -- kozmogenis/web` ve `.github/workflows/pages.yml` içindeki `/3d/` kopyalama adımı.

## Ne kaldırıldı
- `kozmogenis/web/` (Three.js istemcisi, WebAssembly köprüsü `kozmo_web.cpp`, derlenmiş `dist/kozmo.wasm`, vendor Three.js).
- Sitedeki `/3d/` yayını ve yükleme sayfasındaki "deneysel 3B sürüm" bağlantısı; README bağlantıları.

## Ne korundu / ana oyuna taşındı
- **C++ çekirdek (KozmoCore) ve Unreal istemcisi** yerinde duruyor (`kozmogenis/core`, `kozmogenis/unreal`): 3D sürüm bu
  çekirdeğin yalnız bir tarayıcı kabuğuydu; çekirdek UE5 sürümünün temeli olarak kalır.
- **Rover modeli:** `core/rover.hpp` / `rover.cpp` C++ çekirdekte duruyor. Bir süre Python'a taşınıp ana oyunda ROVER
  ekranı olarak yer aldı; oyuncu isteğiyle ROVER ekranı oyundan çıkarıldı (bkz. `docs/ROVER_KALDIRILDI.md`).
- **İniş, kokpit göstergeleri, NOVA, yaşayan NPC/koloni, gezegen verileri** ana oyunda zaten kendi biçimiyle var
  (motorlu iniş, YAŞAM ekranı, koloni 3B). JavaScript/Three.js kodu Python'a satır satır taşınamayacağı için silindi;
  davranışlar ana oyunun motoruyla yeniden yazıldı.

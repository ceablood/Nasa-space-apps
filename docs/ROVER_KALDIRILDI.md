# ROVER ekranı oyundan çıkarıldı

Oyuncu isteğiyle gezegen aracı sürüşü (ROVER ekranı) ana oyundan kaldırıldı.

**Geri dönüş noktası:** commit `d0773627ec9f64d1fa0e1ccd07de66f1b7b3dcd6` (main). Geri almak için:

    git checkout d0773627ec9f64d1fa0e1ccd07de66f1b7b3dcd6 -- aetherx/vehicles aetherx/scenes/rover.py aetherx/lang/t_rover.py tests/test_vehicles.py

ve `aetherx/app.py` içindeki SCENES / NAV satırları ile dil dosyalarındaki `t_rover` içe aktarmaları.

## Kaldırılanlar
- `aetherx/scenes/rover.py` (ROVER ekranı), üst menüdeki ROVER düğmesi.
- `aetherx/vehicles/` (sürüş fiziği, arazi, 3B arazi çizici, kontroller, sürüş görevleri, ayrı uzay aracı modeli).
- `aetherx/lang/t_rover.py` çevirileri (giriş ekranı satırları `t_v34.py` içine taşındı), `tests/test_vehicles.py`.

## Kalanlar
- Motorlu iniş ekranındaki RCS açısal dinamiği (`aetherx/scenes/landing.py`) ana oyunun parçası olarak duruyor.
- C++ çekirdekteki rover modeli (`kozmogenis/core`) değişmedi.

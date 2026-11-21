// KozmoCore — güneş etkinliği döngüsü (V30 §6.3 uzay havası): ~11 yıllık lekeler döngüsü, F10.7 akısı,
// termosfer yoğunluğu çarpanı (istasyon alçalması) ve güneş parçacık olayı sıklığı.
//
// Gerçek / yaklaşık:
//   * Döngü uzunluğu ~11 yıl; Döngü 25 en yüksek değerine ~2024-2025'te ulaştı (NOAA SWPC; aylık ortalama
//     leke sayısı ~200 civarı, 13 aylık düzgünleştirilmiş ~160)
//   * F10.7 ~ 63.7 + 0.728 S + 0.00089 S^2 (Tapping & Valdés 2011, leke sayısından yaklaşık)
//   * Termosfer yoğunluğu güneş minimumundan maksimumuna 400 km'de ~5-10 kat değişir (NRLMSISE mertebesi)
//   * Büyük güneş parçacık olayları maksimum yıllarında daha sık (yılda birkaç), minimumda nadir
#pragma once

namespace kozmo::solar {

constexpr double kCycleYears = 11.0;
constexpr double kCycle25PeakYear = 2024.8;

double sunspot_number(double year, double peak = 160.0);   // 13 aylık düzgünleştirilmiş mertebe
double f107(double sunspots);
// station::thermosphere_density'ye verilecek etkinlik çarpanı (minimum ~0.4, maksimum ~3)
double density_factor(double year);
// yılda beklenen büyük (>10 MeV, >10 pfu) güneş parçacık olayı sayısı
double spe_per_year(double year);
// oyun günü -> takvim yılı (oyun başlangıcı 2030.0 varsayımı)
double year_from_game_day(double day, double start_year = 2030.0);

}  // namespace kozmo::solar

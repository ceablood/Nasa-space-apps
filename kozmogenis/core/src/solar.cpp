#include "kozmo/solar.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::solar {

namespace {
constexpr double kPi = 3.14159265358979323846;
}

double sunspot_number(double year, double peak) {
    // döngü evresi: tepe noktası kCycle25PeakYear; asimetrik değil sin^2 yaklaşımı (yükseliş = iniş)
    const double phase = (year - kCycle25PeakYear) / kCycleYears;   // 0 tepe
    const double s = std::cos(kPi * phase);
    return std::max(5.0, peak * s * s);
}

double f107(double S) { return 63.7 + 0.728 * S + 0.00089 * S * S; }

double density_factor(double year) {
    const double f = f107(sunspot_number(year));
    // F10.7 70 (minimum) -> ~0.4, 200 (maksimum) -> ~3; üstel uyum
    return std::clamp(0.4 * std::exp((f - 70.0) / 64.0), 0.3, 3.5);
}

double spe_per_year(double year) { return 0.3 + 6.0 * sunspot_number(year) / 160.0; }

double year_from_game_day(double day, double start) { return start + day / 365.25; }

}  // namespace kozmo::solar

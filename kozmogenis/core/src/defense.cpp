#include "kozmo/defense.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace kozmo::defense {

namespace {
constexpr double kPi = 3.14159265358979323846;
std::string f(double v, const char* fmt = "%.2f") {
    char b[48];
    std::snprintf(b, sizeof(b), fmt, v);
    return b;
}
}  // namespace

double diameter_km(double h, double p) { return 1329.0 / std::sqrt(std::max(1e-4, p)) * std::pow(10.0, -h / 5.0); }
double mass_kg(double d_m, double rho) { return rho * kPi / 6.0 * d_m * d_m * d_m; }
double impact_energy_mt(double m, double v) { return 0.5 * m * v * v / kMegatonJ; }

double palermo(double p, double e_mt, double years) {
    const double fb = 0.03 * std::pow(std::max(1e-9, e_mt), -0.8);
    return std::log10(std::max(1e-30, p) / (fb * std::max(1e-6, years)));
}

int torino(double p, double e, double years) {
    if (years > 100.0) return 0;   // Torino ölçeği yalnız 100 yıl içindeki olaylar için tanımlıdır
    // Binzel tablosunun eşik bölgeleri (sadeleştirilmiş): enerji < 1 Mt ya da p < 1e-8 -> 0
    if (p >= 0.99) return e >= 1e5 ? 10 : (e >= 1e2 ? 9 : 8);
    if (e < 1.0 || p < 1e-8) return 0;
    if (p < 1e-6) return e > 1e5 ? 2 : 1;
    if (p < 1e-2) {
        if (e >= 1e5) return 4;
        return e >= 1e2 ? 3 : 2;
    }
    if (e >= 1e5) return 7;
    return e >= 1e2 ? 6 : 5;
}

double kinetic_dv(double beta, double m, double v, double M) { return beta * m * v / std::max(1.0, M); }
double deflection_km(double dv, double days) { return 3.0 * dv * days * 86400.0 / 1000.0; }

Effects effects(double e_mt) {
    // ölçek ~E^(1/3) (krater) ve ~E^(0.4) (ateş topu), ~E^(1/3) şiddetli patlama (20 psi) — yaklaşık katsayılar
    const double c = std::cbrt(std::max(0.0, e_mt));
    // Barringer (Meteor) krateri ~1.2 km, ~10 Mt -> 0.55 E^0.294; 1 Mt ateş topu yarıçapı ~0.5 km
    return {0.55 * std::pow(std::max(0.0, e_mt), 0.294), 0.44 * std::pow(std::max(0.0, e_mt), 0.4), 2.2 * c};
}

double Asteroid::diameter_m() const { return diameter_km(h_mag, albedo) * 1000.0; }
double Asteroid::mass() const { return mass_kg(diameter_m(), density); }
double Asteroid::energy_mt() const { return impact_energy_mt(mass(), velocity_ms); }

const std::vector<Asteroid>& catalog() {
    static const std::vector<Asteroid> c = {
        {"99942 Apophis", 19.7, 0.23, 3200, 7420, 0.0, 2.4, true, "2029-04-13'te ~31 600 km yakın geçiş; 2021 radar ölçümleriyle 100 yıllık çarpma riski elendi"},
        {"101955 Bennu", 20.19, 0.044, 1190, 12700, 3.7e-4, 157.0, true, "OSIRIS-REx: 2300'e kadar kümülatif olasılık ~1/2700 (en olası tarih 2182)"},
        {"65803 Didymos (Dimorphos)", 18.16, 0.15, 2400, 6140, 0.0, 0.0, true, "DART hedefi: Dimorphos ~160 m, 2022 çarpması periyodu ~33 dk kısalttı"},
        {"2023 KZ-1 (senaryo)", 22.5, 0.15, 2000, 17000, 2e-3, 8.0, false, "Oyun senaryosu: keşfedilmiş ~150 m cisim, yüksek olasılık"},
        {"2031 KZ-7 (senaryo)", 18.0, 0.14, 2600, 20000, 0.3, 12.0, false, "Oyun senaryosu: ~1 km sınıfı, küresel tehdit"},
    };
    return c;
}

double apparent_mag(double h, double r, double d) { return h + 5.0 * std::log10(std::max(1e-6, r) * std::max(1e-6, d)); }
bool detectable(const Survey& s, double h, double r, double d) { return apparent_mag(h, r, d) <= s.limiting_mag; }

Plan plan_deflection(const Asteroid& a, double lead_days, double beta, double m_imp, double v_imp, double required_km) {
    Plan p;
    p.method = "Kinetik çarpıcı (DART sınıfı)";
    const double M = a.mass();
    const double one = kinetic_dv(beta, m_imp, v_imp, M);
    const double needed_dv = required_km * 1000.0 / (3.0 * std::max(1.0, lead_days) * 86400.0);
    p.impactors = static_cast<int>(std::ceil(needed_dv / std::max(1e-12, one)));
    if (p.impactors <= 10) {
        p.dv_ms = one * p.impactors;
        p.shift_km = deflection_km(p.dv_ms, lead_days);
        p.sufficient = p.shift_km >= required_km;
        p.note = std::to_string(p.impactors) + " çarpıcı, toplam dv " + f(p.dv_ms * 1000, "%.2f") + " mm/s, kayma " + f(p.shift_km, "%.0f") + " km";
    } else {
        p.method = "Kinetik çarpma yetersiz: çekim traktörü/nükleer seçenek ya da daha uzun uyarı süresi";
        p.dv_ms = one * 10;
        p.shift_km = deflection_km(p.dv_ms, lead_days);
        p.impactors = 10;
        p.sufficient = false;
        p.note = "10 çarpıcıyla bile kayma " + f(p.shift_km, "%.0f") + " km (gereken " + f(required_km, "%.0f") + " km)";
    }
    return p;
}

LocalThreat assess_local(double d_m, double v, double kpa, double prob) {
    LocalThreat t{};
    t.probability = prob;
    t.energy_kt = impact_energy_mt(mass_kg(d_m, 2600), v) * 1000.0;
    // kalın atmosfer (> ~10 kPa) birkaç on metreden küçük taşlı cisimleri parçalar (Çelyabinsk ~19 m havada patladı)
    t.atmosphere_burns = kpa > 10.0 && d_m < 25.0;
    if (t.atmosphere_burns) t.advice = "Atmosfer cismi parçalar; şok dalgası için camlardan uzak durun";
    else if (kpa < 0.1) t.advice = "Atmosfer koruması yok: tüm cisimler yüzeye ulaşır; regolit örtülü sığınağa geçin";
    else t.advice = "İnce atmosfer kısmen korur; sığınağa geçin ve dış çalışmaları durdurun";
    return t;
}

}  // namespace kozmo::defense

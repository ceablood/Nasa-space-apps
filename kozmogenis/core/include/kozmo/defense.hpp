// KozmoCore — gezegen savunması (V30 §18.2, V41 §5.10 meteor tehdidi).
//
// Gerçek bağıntılar ve veriler:
//   * Çap: D(km) = 1329 / sqrt(p_v) * 10^(-H/5)   (Fowler & Chillemi 1992; Harris & Lagerros)
//   * Kütle: M = rho * pi/6 * D^3; çarpma enerjisi E = 1/2 M v^2; 1 Mt TNT = 4.184e15 J
//   * Palermo ölçeği: PS = log10( p / (f_B * T) ), f_B = 0.03 * E^-0.8 yıl^-1 (E Mt) (Chesley vd. 2002)
//   * Torino ölçeği: enerji-olasılık bölgeleri (Binzel 1997/2005), burada eşik tablosuyla
//   * Kinetik çarpma: dv = beta * m * v_imp / M. DART (2022): 580 kg, 6.14 km/s, beta ~3.6, Dimorphos ~4.3e9 kg
//     -> ~2.7 mm/s; yörünge periyodu ~33 dakika kısaldı (Cheng vd. 2023, Thomas vd. 2023)
//   * Saptırma: yörünge boyunca kayma ~ 3 * dv * t (kısa vadeli yaklaşık; Ahrens & Harris 1992)
//   * Örnek cisimler: Apophis (H 19.7, ~340 m, 13 Nisan 2029'da ~31 600 km yakın geçiş, çarpma riski elendi),
//     Bennu (~490 m, 2182'ye kadar kümülatif olasılık ~1/2700, OSIRIS-REx), Didymos/Dimorphos (DART hedefi)
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::defense {

constexpr double kMegatonJ = 4.184e15;

double diameter_km(double h_mag, double albedo);
double mass_kg(double diameter_m, double density_kgm3);
double impact_energy_mt(double mass_kg, double velocity_ms);
double palermo(double probability, double energy_mt, double years_to_impact);
int torino(double probability, double energy_mt, double years_to_impact = 0.0);   // yalnız önümüzdeki 100 yıl için tanımlı
// Kinetik çarpma ile hız değişimi (m/s)
double kinetic_dv(double beta, double impactor_kg, double impact_speed_ms, double target_kg);
// t gün önceden verilen dv'nin çarpma anındaki kayması (km): ~3 dv t
double deflection_km(double dv_ms, double lead_days);
// Bir yüzey yerleşimi için yerel etki yarıçapları (km) — Collins/Melosh/Marcus (2005) ölçeklerinden yaklaşık
struct Effects { double crater_km, fireball_km, severe_blast_km; };
Effects effects(double energy_mt);

struct Asteroid {
    std::string name;
    double h_mag, albedo, density;
    double velocity_ms;          // Dünya'ya göre çarpma hızı
    double probability;          // çarpma olasılığı (bilinen ölçümlere göre)
    double years_to_event;
    bool real;                   // gerçek katalog verisi mi, oyun senaryosu mu
    std::string note;
    double diameter_m() const;
    double mass() const;
    double energy_mt() const;
};
const std::vector<Asteroid>& catalog();

struct Survey {
    double limiting_mag = 22.0;   // ör. Pan-STARRS ~22, Rubin/LSST ~24.5
};
// Görünür parlaklık (yaklaşık, faz etkisi ihmal): V = H + 5 log10(r * delta) [AU]
double apparent_mag(double h_mag, double r_au, double delta_au);
bool detectable(const Survey& s, double h_mag, double r_au, double delta_au);

struct Plan {
    std::string method;
    double dv_ms = 0, shift_km = 0;
    bool sufficient = false;
    int impactors = 0;
    std::string note;
};
// Gerekli kayma: Dünya yarıçapı + güvenlik payı (km). DART sınıfı çarpıcı sayısı ve uyarı süresiyle plan
Plan plan_deflection(const Asteroid& a, double lead_days, double beta = 3.6, double impactor_kg = 580.0, double speed_ms = 6140.0,
                     double required_km = 6371.0 + 3000.0);

// Koloni için meteor tehdidi değerlendirmesi (NOVA §5.10): yerel atmosfer koruması ve kalkan
struct LocalThreat {
    double probability, energy_kt;
    bool atmosphere_burns;       // küçük cisimler kalın atmosferde yanar
    std::string advice;
};
LocalThreat assess_local(double diameter_m, double velocity_ms, double surface_pressure_kpa, double probability);

}  // namespace kozmo::defense

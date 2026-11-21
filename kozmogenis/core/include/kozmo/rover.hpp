// KozmoCore — yüzey araçları ve EVA keşfi (V30 §8, V41 §3.3 "mobil araştırma aracı").
//
// Gerçek değerler:
//   Apollo LRV: boş kütle 210 kg, yük 490 kg, en yüksek hız ~13 km/h (3.6 m/s), iki 36 V gümüş-çinko batarya
//     (2 x 121 Ah ~ 8.7 kWh), toplam menzil sınırı 92 km; "geri yürüyüş" kuralı: araç bozulursa astronotlar
//     giysi tüketimiyle geri yürüyebilmeli (Apollo 15-17 operasyon kısıtı).
//   Curiosity: 899 kg, ~0.04 m/s ortalama sürüş, MMRTG ~110 W elektrik; patinaj eğimle hızla artar
//     (gevşek kumda ~15-20° üstünde yüksek patinaj, Opportunity "Purgatory" kumulu 2005).
//   Yuvarlanma direnci katsayısı gevşek regolitte ~0.1-0.2 (Bekker toprak mekaniği yaklaşımı).
// Patinaj eğrisi, aşınma ve çevresel çarpanlar OYUN VARSAYIMIDIR.
#pragma once

#include <string>
#include <vector>

#include "kozmo/challenge.hpp"
#include "kozmo/core.hpp"
#include "kozmo/terrain.hpp"

namespace kozmo::rover {

struct Spec {
    std::string key, name;
    double mass_kg;            // boş
    double payload_kg;
    double battery_kwh;
    double solar_w;            // sürekli üretim (güneş paneli / RTG)
    double top_speed_ms;
    double max_slope_deg;
    double hotel_w;            // sürüş dışı sabit tüketim (elektronik, ısıtma)
    double drive_efficiency;   // motor + şanzıman verimi
    double rolling_coeff;      // yuvarlanma direnci
    bool crewed;
};
const std::vector<Spec>& catalog();          // lrv, pressurized (basınçlı rover konsepti), curiosity, prospector
Result<const Spec*> find(const std::string& key);

struct Waypoint {
    double x, y;
};

struct TraverseLeg {
    double distance_m, time_s, energy_kwh, slip, max_slope_deg;
};

struct TraverseReport {
    bool feasible = true;
    std::string failure;
    double distance_m = 0, time_s = 0, energy_kwh = 0, battery_left_kwh = 0, max_slope_deg = 0;
    double walkback_m = 0;              // en uzak noktanın araca dönüş mesafesi
    std::vector<TraverseLeg> legs;
    std::vector<std::string> notes;
};

// Patinaj oranı (0..1): eğim ve zemin gevşekliğine bağlı (Opportunity/Curiosity gözlemlerinden yaklaşık eğri)
double slip_ratio(double slope_deg, double looseness);
// Sürüş gücü (W): rampa + yuvarlanma direnci, verim ve patinajla (etkin ilerleme düşer)
double drive_power_w(const Spec& s, double load_kg, double g, double speed_ms, double slope_deg, double slip);

class Rover {
public:
    explicit Rover(const Spec& s);
    const Spec& spec() const { return spec_; }
    double battery() const { return battery_kwh_; }
    double odometer() const { return odo_m_; }
    double wear() const { return wear_; }
    void set_load(double kg) { load_kg_ = std::clamp(kg, 0.0, spec_.payload_kg); }
    void charge(double hours, double solar_factor = 1.0);

    // Arazi üzerinde yol noktalarını takip eden sürüşü planlar (ve apply=true ise uygular).
    // speed_frac: en yüksek hızın oranı; visibility: toz/kar fırtınasında hız sınırı (0..1)
    // eva_o2_h: mürettebatlı araçta giysi oksijeni (geri yürüyüş kuralı); 0 = kural yok
    TraverseReport traverse(const terrain::Heightmap& map, const challenge::PlanetEnvironment& env, Waypoint start,
                            const std::vector<Waypoint>& route, double speed_frac, double visibility, double eva_o2_h, bool apply);

private:
    Spec spec_;
    double battery_kwh_;
    double odo_m_ = 0, wear_ = 0, load_kg_ = 0;
};

// Geri yürüyüş menzili (m): giysi oksijeni ve düşük yerçekiminde yürüme hızıyla (rezerv %30)
double walkback_limit_m(double eva_o2_h, double gravity_ms2);

}  // namespace kozmo::rover

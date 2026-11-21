// KozmoCore — uzay giysisi (EVA) ve vurgun fizyolojisi (V30 §9 karakter, V41 §3.9 dış mekân uzay giysisi).
//
// Gerçek / yaklaşık:
//   * EMU/xEMU iç basıncı 29.6 kPa (4.3 psi) saf O2; ISS kabini 101.3 kPa hava (%21 O2 / %79 N2)
//   * Vurgun (DCS) ölçütü: doku N2 kısmi basıncı / giysi basıncı = R; NASA 360 dakika yarı ömürlü doku bölmesi,
//     R <= ~1.65 kabul (Conkin; NASA-STD-3001). Saf O2 ön soluma doku N2'sini üstel olarak düşürür; egzersizli
//     ön soluma (ISS "ISLE"/egzersiz protokolü) yarı ömrü kabaca yarıya indirir -> ~2 saat
//   * NASA keşif atmosferi 56.5 kPa / %34 O2 (Artemis/Gateway tasarımları): R ~1.26 -> ön soluma gerekmez
//   * Metabolizma: 1 L O2 ~ 20.1 kJ; O2 yoğunluğu 1.43 g/L -> 300 W ortalama iş ~0.077 kg O2/saat (EMU ~8 saat)
//   * Süblimatör soğutması yalnız vakumda çalışır (Mars atmosferinde çalışmaz — gerçek tasarım kısıtı)
#pragma once

#include <string>

#include "kozmo/core.hpp"

namespace kozmo::suit {

constexpr double kSuitKpa = 29.6;
constexpr double kTissueHalfMin = 360.0;
constexpr double kRLimit = 1.65;

struct Atmosphere {
    double total_kpa, o2_fraction;
    double n2_kpa() const { return total_kpa * (1.0 - o2_fraction); }
};
Atmosphere iss_cabin();          // 101.3 kPa, %21 O2
Atmosphere exploration();        // 56.5 kPa, %34 O2

double tissue_ratio(double tissue_n2_kpa, double suit_kpa = kSuitKpa);
// t dakika saf O2 ön solumadan sonra doku N2 (kPa); exercise: yarı ömür yarıya
double after_prebreathe(double start_n2_kpa, double minutes, bool exercise);
// R sınırına inmek için gereken ön soluma (dakika); gerekmiyorsa 0
double required_prebreathe_min(const Atmosphere& cabin, bool exercise, double suit_kpa = kSuitKpa);

enum class Workload { Rest, Light, Moderate, Heavy };
double metabolic_w(Workload w);          // 100 / 200 / 300 / 500 W
double o2_kg_per_h(double metabolic_w);

struct Consumables {
    double o2_kg = 0.6;                  // birincil O2 (~8 saat ortalama iş)
    double co2_capacity_h = 8.0;         // LiOH/METOX
    double battery_wh = 1000.0;          // PLSS elektroniği/fanlar ~110 W
    double cooling_water_kg = 3.6;       // süblimatör suyu (~0.45 kg/saat)
};

struct EvaState {
    Consumables c;
    double elapsed_h = 0;
    double tissue_n2_kpa = 0;
    bool dcs = false;                    // vurgun belirtisi
    bool overheating = false;
    std::string limiting;                // ilk tükenen sarf
    double remaining_h() const;          // en kısıtlı sarfa göre kalan süre (ortalama işte)
};

// EVA başlat: kabin atmosferi + yapılan ön soluma; R kontrolü
EvaState begin_eva(const Atmosphere& cabin, double prebreathe_min, bool exercise, Rng& rng);
// dt saat ilerlet; ortam basıncı (kPa) süblimatör için; dönüş: devam güvenli mi
bool tick(EvaState& s, double dt_h, Workload w, double ambient_kpa);

}  // namespace kozmo::suit

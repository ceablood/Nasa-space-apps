// KozmoCore — roket gövde mühendisliği (V30 §13.2): yakıt kimyası, tanklar, geometri, kütle merkezi,
// basınç merkezi, kararlılık, burun konisi (fairing). UE5 roket montaj aktörü bu geometriyi 3B'ye çevirir.
//
// Gerçek değerler (yaklaşık, yayımlanmış tipik değerler):
//   Yoğunluk (kg/m^3): LOX 1141, RP-1 810, LH2 70.85, LCH4 422.6, APCP katı yakıt ~1770
//   Oksitleyici/yakıt kütle oranı: kerosen ~2.56, hidrojen ~6.0, metan ~3.6
// Mühendislik yaklaşımları: %3 tank boşluğu (ullage), motor bölümü boyu, kademeler arası 1.5 m,
// yük yoğunluğu 150 kg/m^3, fairing 10 kg/m^2 (F9: ~190 m^2 yüzey, ~1.9 t), ogive burun.
// Basınç merkezi: Barrowman yöntemi (yalnız burun konisi; kanatçık yok) -> roketlerin çoğu statik olarak
// kararsızdır ve itki vektörü kontrolüyle (gimbal) uçar; rapor bunu açıkça söyler.
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/propulsion.hpp"

namespace kozmo::vehicle {

struct Propellant {
    std::string key;            // "RP-1/LOX" ...
    double fuel_density, ox_density, mixture_ratio;   // kg/m^3, kg/m^3, O/F kütle oranı (0: tek bileşen)
    double bulk_density() const;                       // karışımın ortalama yoğunluğu
};
Result<Propellant> propellant(const std::string& key);

struct StageGeometry {
    std::string label;
    double diameter_m, tank_volume_m3, tank_length_m, engine_section_m, stage_length_m;
    double base_m;              // kademenin tabanının roket tabanından yüksekliği
    double fuel_t, oxidizer_t, dry_t;
};

struct BoosterGeometry {
    int count;
    double diameter_m, length_m;
};

struct Geometry {
    std::vector<StageGeometry> stages;
    BoosterGeometry boosters{0, 0, 0};
    double fairing_length_m = 0, fairing_mass_t = 0, payload_volume_m3 = 0;
    double total_height_m = 0;
    double fineness = 0;                 // boy / çap
    double center_of_mass_m = 0;         // kalkışta, tabandan
    double center_of_pressure_m = 0;     // tabandan (Barrowman, burun konisi)
    double static_margin_cal = 0;        // (CoM - CoP) / D ; > 0 statik kararlı
    bool needs_active_control = true;
    std::vector<std::string> notes;
};

constexpr double kPayloadDensity = 150.0;      // kg/m^3 (oyun/mühendislik varsayımı)
constexpr double kFairingAreal = 0.010;        // t/m^2 (F9: ~13 m x 5.2 m, ~190 m^2, ~1.9 t)

Result<Geometry> geometry(const prop::Design& d);

}  // namespace kozmo::vehicle

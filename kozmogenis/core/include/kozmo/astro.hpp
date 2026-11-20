// KozmoCore — gök cisimleri (NASA verisi) ve yörünge mekaniği.
//
// Veri kaynağı etiketleri (şema kuralı 16: gerçek veri / mühendislik yaklaşımı / oyun varsayımı ayrımı):
//   Source::NasaFactSheet   NASA NSSDC Planetary Fact Sheet (metrik), sayfa güncellemesi 13 Kasım 2026
//   Source::Engineering     yayımlanmış görev profillerinden yuvarlanmış mühendislik yaklaşımı
//   Source::GameAssumption  oyun dengesi için seçilmiş değer (gerçek değildir)
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::astro {

constexpr double kG = 6.67430e-11;          // m^3 kg^-1 s^-2 (CODATA 2018)
constexpr double kAU = 1.495978707e11;      // m (IAU 2012 tanımı)
constexpr double kMuSun = 1.32712440018e20; // m^3/s^2 (Güneş'in kütleçekim parametresi, JPL)
constexpr double kPi = 3.14159265358979323846;
constexpr double kDay = 86400.0;

enum class Source { NasaFactSheet, Engineering, GameAssumption };
const char* to_string(Source s);

struct Body {
    std::string key;            // "earth", "mars" ...
    std::string name_tr;
    std::string parent;         // "sun" ya da gezegen anahtarı (Ay için "earth")
    double mass_1e24kg;         // 10^24 kg
    double diameter_km;
    double density_kgm3;
    double gravity_ms2;
    double escape_kms;
    double rotation_h;          // negatif = ters yönde dönüş
    double day_h;
    double distance_1e6km;      // ana cisme ortalama uzaklık (Ay için Dünya'ya)
    double perihelion_1e6km;
    double aphelion_1e6km;
    double period_days;
    double orbital_velocity_kms;
    double inclination_deg;
    double eccentricity;
    double obliquity_deg;
    double mean_temp_c;
    double surface_pressure_bar; // bilinmiyorsa < 0 (gaz devleri: katı yüzey yok)
    int moons;                   // NSSDC tablosundaki sayı (bkz. moons_note)
    Source source;

    double mu() const { return kG * mass_1e24kg * 1e24; }
    double radius_m() const { return diameter_km * 500.0; }
    double semi_major_m() const { return distance_1e6km * 1e9; }
    bool has_surface() const { return surface_pressure_bar >= 0.0; }
};

// NSSDC tablosu uydu sayılarını geç günceller; NASA Science "Moons" sayfası Ekim 2026'da gezegenler + Plüton
// için toplam 461 resmî uydu bildirir. Oyun arayüzü iki bilgiyi de kaynağıyla gösterir.
extern const char* const kMoonsNote;

const std::vector<Body>& bodies();
Result<const Body*> find(const std::string& key);

// ------------------------------------------------------------------------ yörünge mekaniği (fizik)
double circular_velocity(double mu, double r_m);                  // v = sqrt(mu/r)
double escape_velocity(double mu, double r_m);                    // v = sqrt(2 mu / r)
double vis_viva(double mu, double r_m, double a_m);               // v^2 = mu (2/r - 1/a)
double orbital_period(double mu, double a_m);                     // T = 2 pi sqrt(a^3 / mu)
double synodic_period_days(double t1_days, double t2_days);       // 1/S = |1/T1 - 1/T2|

struct Hohmann {
    double dv_depart_ms;      // güneş merkezli: kalkış yanması (hiperbolik fazla hız v_inf)
    double dv_arrive_ms;      // güneş merkezli: varış yanması
    double transfer_days;     // yarım transfer elipsi süresi
    double phase_angle_deg;   // kalkışta hedefin önde olması gereken açı
};
Hohmann hohmann(double mu, double r1_m, double r2_m);

// Bir gezegenin r yarıçaplı dairesel park yörüngesinden v_inf ile kaçış/yakalanma yanması (Oberth etkisi dahil).
double burn_from_parking(double mu_planet, double r_park_m, double v_inf_ms);

struct TransferWindow {
    double days_until;        // şu andan bir sonraki pencereye gün
    double synodic_days;
    double current_phase_deg; // şu anki faz açısı (hedef - kalkış)
    double required_phase_deg;
};
// Gezegenlerin ortalama boylamları (derece) verilip bir sonraki Hohmann penceresi.
Result<TransferWindow> next_window(const std::string& from, const std::string& to, double from_lon_deg,
                                   double to_lon_deg);

// Ortalama boylam: epoch'tan (gün) itibaren dairesel yaklaşım; başlangıç boylamları oyun varsayımıdır.
double mean_longitude_deg(const Body& b, double days_since_epoch);

// ------------------------------------------------------------------------ görev delta-v bütçesi
struct DeltaVBudget {
    double launch_to_leo_ms;   // Dünya yüzeyinden ~200 km LEO (atmosfer/yerçekimi kayıpları dahil)
    double departure_ms;       // LEO'dan transfer
    double capture_ms;         // hedefte düşük yörüngeye yakalanma
    double landing_ms;         // yörüngeden yüzeye iniş (yüzeyi yoksa 0)
    double return_ms;          // dönüş (yüzeyden kalkış + Dünya'ya transfer; atmosfer frenlemesi varsayılır)
    double total(bool land, bool ret) const;
    Source launch_source = Source::Engineering;
};
Result<DeltaVBudget> mission_budget(const std::string& target_key);

}  // namespace kozmo::astro

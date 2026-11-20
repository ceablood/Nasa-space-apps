// KozmoCore — roket uçuş fiziği (V30 §5, §14): fırlatmadan yörüngeye sayısal simülasyon.
//
// Model (düzlemsel, Dünya merkezli eylemsiz çerçeve):
//   * Kütleçekim: a = -mu r / |r|^3  (Newton; tek merkezli)
//   * Atmosfer: ABD Standart Atmosferi 1976, 0-86 km katmanları (gerçek tablo); 86 km üstü üstel yaklaşım
//   * Atmosfer Dünya ile döner: sürüklenme hava-göreli hızla, D = 1/2 rho v^2 Cd A
//   * Motor: sabit kütle akışı; Isp(p) = Isp_vac - (Isp_vac - Isp_sl) p/p0  (yaygın mühendislik yaklaşımı)
//   * İntegrasyon: RK4, sabit adım
//   * Güdüm: dikey tırmanış -> eğim tekmesi -> yerçekimi dönüşü (hava-göreli prograd) -> üst kademe
//     kapalı döngü yörüngeye giriş (radyal ivme komutu: hedef yükseklik + dikey hız hatası, yerçekimi - merkezkaç)
// Sınırlar (dokümante): 2B, Dünya basık değil, rüzgâr yok, Cd sabit (Mach etkisi yok), aerodinamik ısınma yok.
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/propulsion.hpp"

namespace kozmo::flight {

struct Vec2 {
    double x = 0, y = 0;
    Vec2 operator+(const Vec2& o) const { return {x + o.x, y + o.y}; }
    Vec2 operator-(const Vec2& o) const { return {x - o.x, y - o.y}; }
    Vec2 operator*(double k) const { return {x * k, y * k}; }
    double dot(const Vec2& o) const { return x * o.x + y * o.y; }
    double cross(const Vec2& o) const { return x * o.y - y * o.x; }
    double norm() const;
    Vec2 unit() const;
};

// ------------------------------------------------------------------------ atmosfer
struct AtmosphereSample {
    double temperature_k, pressure_pa, density_kgm3;
};
AtmosphereSample us_standard_1976(double geometric_altitude_m);

// ------------------------------------------------------------------------ yörünge elemanları (2B)
struct Orbit {
    double semi_major_m, eccentricity, periapsis_alt_m, apoapsis_alt_m, specific_energy;
    bool bound;
};
Orbit orbit_from_state(const Vec2& r, const Vec2& v, double mu, double body_radius_m);

// ------------------------------------------------------------------------ simülasyon
struct State {
    Vec2 r, v;
    double mass_kg;
};

enum class EventType { Liftoff, PitchKick, MaxQ, StageBurnout, StageSeparation, ApoapsisTargetReached, CoastStart,
                       CircularizeStart, OrbitAchieved, Crash, OutOfPropellant };
const char* event_name(EventType e);

struct FlightEvent {
    EventType type;
    double t_s, altitude_m, speed_ms;
    int stage;
};

struct Telemetry {
    double t_s, altitude_m, speed_ms, dynamic_pressure_pa, mass_kg, pitch_deg;
};

struct AscentConfig {
    double target_orbit_alt_m = 200e3;
    double launch_latitude_deg = 28.5;       // Cape Canaveral
    double drag_coefficient = 0.30;          // mühendislik yaklaşımı (Mach'tan bağımsız sabit)
    double diameter_m = 3.7;
    double pitch_kick_speed_ms = 60.0;
    double pitch_kick_deg = 5.0;
    double dt_s = 0.1;
    double max_time_s = 6000.0;
    double telemetry_every_s = 1.0;
    double stage_separation_coast_s = 2.0;   // ayrılma ve ikinci kademe ateşlemesi arası boşluk
    double max_accel_g = 4.0;                // motor kısma sınırı
    double min_throttle = 0.4;               // motorların en düşük kısma oranı (mühendislik yaklaşımı)
};

struct AscentResult {
    bool orbit = false;
    Orbit final_orbit{};
    double max_q_pa = 0, max_q_alt_m = 0, max_q_t_s = 0;
    double max_accel_g = 0;
    double payload_kg = 0;
    double remaining_propellant_kg = 0;
    double gravity_loss_ms = 0, drag_loss_ms = 0;
    std::vector<FlightEvent> events;
    std::vector<Telemetry> telemetry;
    std::string failure;
};

// Tasarımın fırlatmasını simüle eder (kademeler prop::Design'dan; yük + mürettebat kapsülü dahil).
Result<AscentResult> simulate_ascent(const prop::Design& design, const AscentConfig& cfg);

// Doğrulama yardımcıları: kütleçekim altında itkisiz yayılım (RK4), enerji/periyot testleri için
State propagate(State s, double mu, double dt, int steps);
// İtkisiz ve yerçekimsiz vakumda sabit kütle akışlı yanma (Tsiolkovsky doğrulaması)
double vacuum_burn_dv(double m0_kg, double propellant_kg, double isp_s, double thrust_n, double dt);

}  // namespace kozmo::flight

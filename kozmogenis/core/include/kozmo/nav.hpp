// KozmoCore — gezegenler arası navigasyon (V30 §5, §7; V41 §2.5 yörünge düzeltme): Lambert problemi
// (evrensel değişkenler, Curtis "Orbital Mechanics for Engineering Students" Algoritma 5.2), fırlatma
// penceresi "porkchop" taraması, gerekli C3 ve varış v_inf, yörünge düzeltme manevrası bütçesi.
// Gezegen konumları: astro'daki dairesel, eş düzlemli yaklaşım (gerçek eksantriklik/eğiklik ihmal; Mars için
// porkchop minimumu gerçekte ~%10-20 farklı çıkabilir — bu fark açıkça belgelenir).
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::nav {

struct Vec3 {
    double x = 0, y = 0, z = 0;
    Vec3 operator+(const Vec3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    Vec3 operator*(double k) const { return {x * k, y * k, z * k}; }
    double dot(const Vec3& o) const { return x * o.x + y * o.y + z * o.z; }
    Vec3 cross(const Vec3& o) const { return {y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x}; }
    double norm() const;
};

struct LambertSolution {
    Vec3 v1, v2;
    int iterations = 0;
};
// r1, r2 (m), tof (s), mu (m^3/s^2). prograde=true: z'ye göre saat yönü tersi geçiş
Result<LambertSolution> lambert(const Vec3& r1, const Vec3& r2, double tof_s, double mu, bool prograde = true);

// Gezegenin güneş merkezli konumu/hızı (dairesel eş düzlemli yaklaşım), gün: oyun dönemi başlangıcından
Result<Vec3> planet_position(const std::string& key, double day);
Result<Vec3> planet_velocity(const std::string& key, double day);

struct Transfer {
    double depart_day, tof_days;
    double vinf_depart_ms, vinf_arrive_ms;
    double c3_km2s2;                    // fırlatma enerjisi = vinf^2
    double total_ms() const { return vinf_depart_ms + vinf_arrive_ms; }
};
Result<Transfer> transfer(const std::string& from, const std::string& to, double depart_day, double tof_days);

struct Porkchop {
    std::vector<double> depart_days, tof_days;
    std::vector<std::vector<double>> c3;            // [i_depart][j_tof], km^2/s^2 (çözümsüzse -1)
    std::vector<std::vector<double>> vinf_arrive;   // m/s
    Transfer best{};                                // en düşük toplam v_inf
};
Result<Porkchop> porkchop(const std::string& from, const std::string& to, double depart_start, double depart_span_days, double depart_step,
                          double tof_min, double tof_max, double tof_step);

// Yörünge düzeltme (TCM) bütçesi: hedefleme hatası (km) ve kalan süreye göre gereken dv (m/s), yaklaşık
double correction_dv(double miss_km, double days_to_go);

}  // namespace kozmo::nav

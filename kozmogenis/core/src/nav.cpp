#include "kozmo/nav.hpp"

#include <algorithm>
#include <cmath>

#include "kozmo/astro.hpp"

namespace kozmo::nav {

namespace {
constexpr double kPi = 3.14159265358979323846;
// Stumpff fonksiyonları
double stumpC(double z) {
    if (z > 1e-8) return (1 - std::cos(std::sqrt(z))) / z;
    if (z < -1e-8) return (std::cosh(std::sqrt(-z)) - 1) / (-z);
    return 0.5 - z / 24.0;
}
double stumpS(double z) {
    if (z > 1e-8) {
        const double s = std::sqrt(z);
        return (s - std::sin(s)) / (s * s * s);
    }
    if (z < -1e-8) {
        const double s = std::sqrt(-z);
        return (std::sinh(s) - s) / (s * s * s);
    }
    return 1.0 / 6.0 - z / 120.0;
}
}  // namespace

double Vec3::norm() const { return std::sqrt(x * x + y * y + z * z); }

Result<LambertSolution> lambert(const Vec3& r1, const Vec3& r2, double tof, double mu, bool prograde) {
    const double R1 = r1.norm(), R2 = r2.norm();
    if (R1 <= 0 || R2 <= 0 || tof <= 0 || mu <= 0) return make_error(ErrorCode::InvalidArgument, "Geçersiz Lambert girdisi");
    const Vec3 c = r1.cross(r2);
    double cosd = std::clamp(r1.dot(r2) / (R1 * R2), -1.0, 1.0);
    double dth = std::acos(cosd);
    if (prograde ? c.z < 0 : c.z >= 0) dth = 2 * kPi - dth;
    if (std::fabs(std::sin(dth)) < 1e-10) return make_error(ErrorCode::Infeasible, "180° (ya da 0°) transfer: düzlem belirsiz, Lambert tekil");
    const double A = std::sin(dth) * std::sqrt(R1 * R2 / (1 - std::cos(dth)));
    auto y = [&](double z) { return R1 + R2 + A * (z * stumpS(z) - 1) / std::sqrt(stumpC(z)); };
    auto F = [&](double z) {
        const double yz = y(z);
        return std::pow(yz / stumpC(z), 1.5) * stumpS(z) + A * std::sqrt(yz) - std::sqrt(mu) * tof;
    };
    // z başlangıcı: F(z) işaret değiştirene kadar (y > 0 olacak şekilde)
    double z = -100.0;
    while (y(z) < 0 || F(z) < 0) {
        z += 0.1;
        if (z > 4 * kPi * kPi) return make_error(ErrorCode::Infeasible, "Lambert başlangıç değeri bulunamadı");
    }
    // Newton + gerektiğinde ikiye bölme
    LambertSolution s;
    double lo = z - 0.1, hi = z;
    for (int it = 0; it < 200; ++it) {
        s.iterations = it + 1;
        const double fz = F(z);
        double dFdz;
        if (std::fabs(z) > 1e-6) {
            const double yz = y(z), C = stumpC(z), S = stumpS(z);
            dFdz = std::pow(yz / C, 1.5) * (1 / (2 * z) * (C - 1.5 * S / C) + 0.75 * S * S / C) +
                   A / 8 * (3 * S / C * std::sqrt(yz) + A * std::sqrt(C / yz));
        } else {
            const double y0 = y(0);
            dFdz = std::sqrt(2.0) / 40 * std::pow(y0, 1.5) + A / 8 * (std::sqrt(y0) + A * std::sqrt(1 / (2 * y0)));
        }
        double zn = z - fz / dFdz;
        if (!(zn > lo && zn < 4 * kPi * kPi) || y(zn) < 0) zn = 0.5 * (z + std::max(lo, z - 1.0));
        if (std::fabs(zn - z) < 1e-10) {
            z = zn;
            break;
        }
        if (F(zn) < 0) lo = std::max(lo, zn);
        else hi = std::min(hi, zn);
        (void)hi;
        z = zn;
    }
    const double yz = y(z);
    const double f = 1 - yz / R1, g = A * std::sqrt(yz / mu), gd = 1 - yz / R2;
    s.v1 = (r2 - r1 * f) * (1 / g);
    s.v2 = (r2 * gd - r1) * (1 / g);
    if (!std::isfinite(s.v1.x) || !std::isfinite(s.v2.x)) return make_error(ErrorCode::Infeasible, "Lambert yakınsamadı");
    return s;
}

Result<Vec3> planet_position(const std::string& key, double day) {
    auto b = astro::find(key);
    if (!b) return b.error();
    if (b.value()->parent != "sun") return make_error(ErrorCode::InvalidArgument, key + " Güneş'i doğrudan dolanmıyor");
    const double lon = astro::mean_longitude_deg(*b.value(), day) * kPi / 180.0;
    const double r = b.value()->distance_1e6km * 1e9;
    return Vec3{r * std::cos(lon), r * std::sin(lon), 0};
}

Result<Vec3> planet_velocity(const std::string& key, double day) {
    auto b = astro::find(key);
    if (!b) return b.error();
    const double lon = astro::mean_longitude_deg(*b.value(), day) * kPi / 180.0;
    const double r = b.value()->distance_1e6km * 1e9;
    const double v = std::sqrt(astro::kMuSun / r);
    return Vec3{-v * std::sin(lon), v * std::cos(lon), 0};
}

Result<Transfer> transfer(const std::string& from, const std::string& to, double d0, double tof) {
    auto r1 = planet_position(from, d0);
    auto r2 = planet_position(to, d0 + tof);
    auto v1p = planet_velocity(from, d0);
    auto v2p = planet_velocity(to, d0 + tof);
    if (!r1 || !r2 || !v1p || !v2p) return make_error(ErrorCode::NotFound, "Gezegen konumu yok");
    auto L = lambert(r1.value(), r2.value(), tof * 86400.0, astro::kMuSun, true);
    if (!L) return L.error();
    Transfer t;
    t.depart_day = d0;
    t.tof_days = tof;
    t.vinf_depart_ms = (L.value().v1 - v1p.value()).norm();
    t.vinf_arrive_ms = (L.value().v2 - v2p.value()).norm();
    t.c3_km2s2 = t.vinf_depart_ms * t.vinf_depart_ms / 1e6;
    return t;
}

Result<Porkchop> porkchop(const std::string& from, const std::string& to, double ds, double span, double dstep, double tmin, double tmax, double tstep) {
    if (dstep <= 0 || tstep <= 0 || tmax < tmin) return make_error(ErrorCode::InvalidArgument, "Geçersiz tarama aralığı");
    Porkchop p;
    for (double d = ds; d <= ds + span + 1e-9; d += dstep) p.depart_days.push_back(d);
    for (double t = tmin; t <= tmax + 1e-9; t += tstep) p.tof_days.push_back(t);
    double best = 1e300;
    for (double d : p.depart_days) {
        std::vector<double> rowc, rowa;
        for (double t : p.tof_days) {
            auto tr = transfer(from, to, d, t);
            if (!tr) {
                rowc.push_back(-1);
                rowa.push_back(-1);
                continue;
            }
            rowc.push_back(tr.value().c3_km2s2);
            rowa.push_back(tr.value().vinf_arrive_ms);
            if (tr.value().total_ms() < best) {
                best = tr.value().total_ms();
                p.best = tr.value();
            }
        }
        p.c3.push_back(rowc);
        p.vinf_arrive.push_back(rowa);
    }
    if (best >= 1e300) return make_error(ErrorCode::Infeasible, "Hiçbir çözüm bulunamadı");
    return p;
}

double correction_dv(double miss_km, double days) {
    // hedef kayması ~ dv * t (kısa yay yaklaşımı) -> dv = miss / t; erken düzeltme ucuzdur
    return miss_km * 1000.0 / std::max(3600.0, days * 86400.0);
}

}  // namespace kozmo::nav

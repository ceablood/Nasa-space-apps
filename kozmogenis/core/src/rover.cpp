#include "kozmo/rover.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

#include "kozmo/life.hpp"

namespace kozmo::rover {

namespace {
constexpr double kPi = 3.14159265358979323846;
std::string f1(double v) {
    char b[32];
    std::snprintf(b, sizeof(b), "%.1f", v);
    return b;
}
}  // namespace

const std::vector<Spec>& catalog() {
    static const std::vector<Spec> c = {
        // anahtar, ad, kütle, yük, batarya kWh, güneş W, hız, eğim, sabit W, verim, yuvarlanma, mürettebat
        {"lrv", "Ay gezgini (Apollo LRV sınıfı)", 210, 490, 8.7, 0, 3.6, 25, 100, 0.55, 0.12, true},
        {"pressurized", "Basınçlı keşif aracı (NASA SEV/LTV konsepti)", 3000, 1000, 120, 2000, 2.8, 20, 1500, 0.7, 0.12, true},
        {"curiosity", "Curiosity sınıfı robotik gezgin", 899, 75, 1.0, 110, 0.04, 30, 60, 0.5, 0.15, false},
        {"prospector", "Kaynak arama robotu (VIPER sınıfı)", 430, 30, 5.0, 450, 0.2, 15, 150, 0.6, 0.15, false},
    };
    return c;
}

Result<const Spec*> find(const std::string& key) {
    for (const auto& s : catalog())
        if (s.key == key) return &s;
    return make_error(ErrorCode::NotFound, "Bilinmeyen araç: " + key);
}

double slip_ratio(double slope_deg, double looseness) {
    // düz zeminde ~%3; eğimle üstel artış; gevşek kumda kritik eğim düşer (Opportunity: ~%100 patinaj kumulda)
    const double crit = 28.0 - 14.0 * std::clamp(looseness, 0.0, 1.0);
    const double s = 0.03 + 0.97 * std::pow(std::clamp(std::max(0.0, slope_deg) / crit, 0.0, 1.0), 3.0);
    return std::clamp(s, 0.0, 1.0);
}

double drive_power_w(const Spec& s, double load_kg, double g, double v, double slope_deg, double slip) {
    const double m = s.mass_kg + load_kg;
    const double th = slope_deg * kPi / 180.0;
    const double force = m * g * (std::sin(th) + s.rolling_coeff * std::cos(th));
    // patinajda tekerlek yüzeyi daha hızlı döner: aynı ilerleme için 1/(1-slip) kat iş
    const double wheel_v = v / std::max(0.05, 1.0 - slip);
    return std::max(0.0, force * wheel_v / s.drive_efficiency);
}

double walkback_limit_m(double eva_o2_h, double g) {
    if (eva_o2_h <= 0) return 1e18;
    return life::walking_speed_ms(g) * eva_o2_h * 3600.0 * 0.7;   // %30 rezerv
}

Rover::Rover(const Spec& s) : spec_(s), battery_kwh_(s.battery_kwh) {}

void Rover::charge(double hours, double solar_factor) {
    battery_kwh_ = std::min(spec_.battery_kwh, battery_kwh_ + std::max(0.0, spec_.solar_w * solar_factor - spec_.hotel_w * 0.3) * hours / 1000.0);
}

TraverseReport Rover::traverse(const terrain::Heightmap& map, const challenge::PlanetEnvironment& env, Waypoint start,
                               const std::vector<Waypoint>& route, double speed_frac, double visibility, double eva_o2_h, bool apply) {
    TraverseReport r;
    double bat = battery_kwh_;
    const double v_lim = spec_.top_speed_ms * std::clamp(speed_frac, 0.05, 1.0) * std::clamp(0.3 + 0.7 * visibility, 0.1, 1.0);
    const double looseness = std::clamp(env.dust_level * 0.8 + (env.cls == challenge::PlanetClass::Desert ? 0.2 : 0.0), 0.0, 1.0);
    const double walk_lim = spec_.crewed ? walkback_limit_m(eva_o2_h, env.gravity_ms2) : 1e18;
    Waypoint p = start;
    const double step = std::max(2.0, map.cell());
    for (const auto& w : route) {
        TraverseLeg leg{0, 0, 0, 0, 0};
        const double D = std::hypot(w.x - p.x, w.y - p.y);
        const int n = std::max(1, static_cast<int>(D / step));
        for (int k = 0; k < n; ++k) {
            const double ax = p.x + (w.x - p.x) * k / n, ay = p.y + (w.y - p.y) * k / n;
            const double bx = p.x + (w.x - p.x) * (k + 1) / n, by = p.y + (w.y - p.y) * (k + 1) / n;
            const double dz = map.height(bx, by) - map.height(ax, ay);
            const double dl = std::hypot(bx - ax, by - ay);
            const double grade = std::atan2(dz, dl) * 180.0 / kPi;     // + yokuş, - iniş
            const double side = map.slope_deg(ax, ay);                  // en dik yerel eğim (devrilme)
            leg.max_slope_deg = std::max(leg.max_slope_deg, std::max(std::fabs(grade), side));
            if (side > spec_.max_slope_deg) {
                r.feasible = false;
                r.failure = "Eğim " + f1(side) + "° araç sınırını (" + f1(spec_.max_slope_deg) + "°) aşıyor: rota değiştir";
                break;
            }
            const double slip = slip_ratio(std::max(0.0, grade), looseness);
            if (slip > 0.9) {
                r.feasible = false;
                r.failure = "Patinaj %" + f1(slip * 100) + ": gevşek zeminde saplanma riski (Opportunity, Purgatory 2005)";
                break;
            }
            const double v = v_lim * (1.0 - 0.5 * std::min(1.0, std::fabs(grade) / spec_.max_slope_deg));
            const double dist = std::hypot(dl, dz);
            const double t = dist / std::max(1e-3, v * (1.0 - slip));
            const double pw = drive_power_w(spec_, load_kg_, env.gravity_ms2, v, grade, slip) + spec_.hotel_w - spec_.solar_w;
            const double e = std::max(0.0, pw) * t / 3.6e6;
            leg.distance_m += dist;
            leg.time_s += t;
            leg.energy_kwh += e;
            leg.slip = std::max(leg.slip, slip);
            bat -= e;
            if (bat < 0) {
                r.feasible = false;
                r.failure = "Batarya bitti (" + f1(r.distance_m + leg.distance_m) + " m sonra)";
                break;
            }
            r.walkback_m = std::max(r.walkback_m, std::hypot(bx - start.x, by - start.y));
            if (r.walkback_m > walk_lim) {
                r.feasible = false;
                r.failure = "Geri yürüyüş kuralı: " + f1(r.walkback_m / 1000) + " km, giysi O2 ile en çok " + f1(walk_lim / 1000) + " km dönülebilir";
                break;
            }
        }
        r.distance_m += leg.distance_m;
        r.time_s += leg.time_s;
        r.energy_kwh += leg.energy_kwh;
        r.max_slope_deg = std::max(r.max_slope_deg, leg.max_slope_deg);
        r.legs.push_back(leg);
        if (!r.feasible) break;
        p = w;
    }
    r.battery_left_kwh = std::max(0.0, bat);
    if (visibility < 0.5) r.notes.push_back("Düşük görüş: hız %" + f1((0.3 + 0.7 * visibility) * 100) + " ile sınırlandı");
    if (r.max_slope_deg > spec_.max_slope_deg * 0.7) r.notes.push_back("Dik bölümler var: dikkatli sürüş");
    if (apply) {
        battery_kwh_ = r.battery_left_kwh;
        odo_m_ += r.distance_m;
        wear_ = std::min(1.0, wear_ + r.distance_m / 1e6 * (1.0 + env.dust_level));   // ~1000 km'de tam aşınma (oyun)
    }
    return r;
}

}  // namespace kozmo::rover

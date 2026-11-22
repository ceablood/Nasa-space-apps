#include "kozmo/satellites.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::sats {

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kMuEarth = 398600.4418;   // km^3/s^2
}

const char* to_string(Orbit o) {
    switch (o) {
        case Orbit::LEO: return "Alçak Dünya yörüngesi (550 km)";
        case Orbit::SSO: return "Güneş-eşzamanlı (700 km)";
        case Orbit::MEO: return "Orta yörünge (20 200 km)";
        case Orbit::GEO: return "Yer-eşzamanlı (35 786 km)";
    }
    return "?";
}

double altitude_km(Orbit o) {
    switch (o) {
        case Orbit::LEO: return 550;
        case Orbit::SSO: return 700;
        case Orbit::MEO: return 20200;
        case Orbit::GEO: return 35786;
    }
    return 550;
}

const char* to_string(Purpose p) {
    switch (p) {
        case Purpose::Communication: return "Haberleşme";
        case Purpose::Navigation: return "Konum belirleme";
        case Purpose::Weather: return "Meteoroloji";
        case Purpose::EarthObservation: return "Yer gözlem";
    }
    return "?";
}

double coverage_half_angle_rad(double h, double e_deg) {
    const double e = e_deg * kPi / 180.0;
    return std::acos(kEarthRadiusKm * std::cos(e) / (kEarthRadiusKm + h)) - e;
}

double single_coverage(double h, double e) { return (1.0 - std::cos(coverage_half_angle_rad(h, e))) / 2.0; }

double constellation_coverage(double h, double e, int n) { return 1.0 - std::pow(1.0 - single_coverage(h, e), std::max(0, n)); }

double visible_average(double h, double e, int n) { return single_coverage(h, e) * n; }

double round_trip_ms(double h) { return 2.0 * h / kC * 1000.0; }

double period_min(double h) {
    const double a = kEarthRadiusKm + h;
    return 2 * kPi * std::sqrt(a * a * a / kMuEarth) / 60.0;
}

double Constellation::coverage() const {
    const double e = purpose == Purpose::Communication && orbit == Orbit::LEO ? 25.0 : 10.0;   // Starlink ~25°, diğerleri ~10°
    return constellation_coverage(altitude_km(orbit), e, active);
}

double Constellation::revenue_per_day() const {
    // gelir kapsama ile doyar (oyun): haberleşme en yüksek, konum belirleme kamu sözleşmesi, hava/gözlem veri satışı
    const double base = purpose == Purpose::Communication ? 20000 : (purpose == Purpose::Navigation ? 15000 : 6000);
    double cov = coverage();
    if (purpose == Purpose::Navigation) cov = std::min(1.0, visible_average(altitude_km(orbit), 10.0, active) / 4.0);   // 4 uydu görünmeli
    if (purpose == Purpose::EarthObservation || purpose == Purpose::Weather) cov = std::min(1.0, active / 6.0);
    return base * cov;
}

Result<int> Fleet::create(const std::string& name, Purpose p, Orbit o, double m) {
    if (m <= 0 || m > 20000) return make_error(ErrorCode::InvalidArgument, "Uydu kütlesi 0-20000 kg");
    list_.push_back({next_id_, name, p, o, 0, 0, m, 0});
    return next_id_++;
}

Status Fleet::deploy(int id, int n, double day) {
    for (auto& c : list_)
        if (c.id == id) {
            if (n <= 0) return make_error(ErrorCode::InvalidArgument, "Uydu sayısı pozitif olmalı");
            if (c.active == 0) c.launched_day = day;
            c.active += n;
            return ok_status();
        }
    return make_error(ErrorCode::NotFound, "Takımyıldızı yok");
}

double Fleet::advance(double days, double solar, Rng& rng) {
    double income = 0;
    for (auto& c : list_) {
        // rastgele arıza: yıllık %2
        for (int i = 0; i < c.active; ++i)
            if (rng.chance(1.0 - std::pow(0.98, days / 365.25))) {
                --c.active;
                ++c.failed;
            }
        // LEO yörünge ömrü: 550 km'de güneş maksimumunda ~5 yıl, minimumda ~10+ yıl (itkisiz; Starlink itkilidir)
        if (c.orbit == Orbit::LEO && c.active > 0) {
            const double life_years = 8.0 / std::max(0.3, solar);
            const double p = 1.0 - std::exp(-days / (life_years * 365.25));
            int lost = 0;
            for (int i = 0; i < c.active; ++i) lost += rng.chance(p) ? 1 : 0;
            c.active -= lost;
            c.failed += lost;
        }
        income += c.revenue_per_day() * days;
    }
    revenue_ += income;
    return income;
}

const Constellation* Fleet::find(int id) const {
    for (const auto& c : list_)
        if (c.id == id) return &c;
    return nullptr;
}

json::Value Fleet::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& c : list_) {
        json::Value o = json::Value::object();
        o.set("id", c.id);
        o.set("name", c.name);
        o.set("purpose", static_cast<int>(c.purpose));
        o.set("orbit", static_cast<int>(c.orbit));
        o.set("active", c.active);
        o.set("failed", c.failed);
        o.set("mass", c.mass_kg_each);
        o.set("day", c.launched_day);
        a.push(o);
    }
    v.set("list", a);
    v.set("next", next_id_);
    v.set("revenue", revenue_);
    return v;
}

Status Fleet::from_json(const json::Value& v) {
    list_.clear();
    for (const auto& o : v["list"].as_array()) {
        const int p = o["purpose"].as_int(-1), ob = o["orbit"].as_int(-1);
        if (p < 0 || p > 3 || ob < 0 || ob > 3) return make_error(ErrorCode::Parse, "Bozuk uydu kaydı");
        list_.push_back({o["id"].as_int(), o["name"].as_string(), static_cast<Purpose>(p), static_cast<Orbit>(ob), o["active"].as_int(), o["failed"].as_int(),
                         o["mass"].as_number(), o["day"].as_number()});
    }
    next_id_ = v["next"].as_int(1);
    revenue_ = v["revenue"].as_number();
    return ok_status();
}

}  // namespace kozmo::sats

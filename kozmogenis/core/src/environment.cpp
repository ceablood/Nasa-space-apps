#include "kozmo/environment.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::env {

Result<double> surface_dose_msv_per_day(const std::string& body) {
    if (body == "moon") return 1.37;
    if (body == "mars") return 0.64;
    if (body == "earth") return 2.4 / 365.25;
    return make_error(ErrorCode::NotFound, "Bu gök cismi için yüzey radyasyon ölçümü yok: " + body);
}

double cruise_dose_msv_per_day() { return 1.84; }

const char* to_string(EventKind k) {
    switch (k) {
        case EventKind::SolarParticleEvent: return "Güneş parçacık fırtınası";
        case EventKind::RegionalDustStorm: return "Bölgesel toz fırtınası";
        case EventKind::GlobalDustStorm: return "Küresel toz fırtınası";
        case EventKind::MicrometeoroidImpact: return "Mikrometeoroid çarpması";
    }
    return "?";
}

void Scheduler::advance(double from, double to, const std::vector<std::string>& bodies, Rng& rng, EventBus* bus) {
    if (to <= from) return;
    // biten olaylar
    for (auto it = active_.begin(); it != active_.end();) {
        if (it->end_day <= to) {
            if (bus) bus->publish(EnvironmentEventEnded{it->kind, it->body});
            history_.push_back(*it);
            it = active_.erase(it);
        } else {
            ++it;
        }
    }
    if (history_.size() > 200) history_.erase(history_.begin(), history_.begin() + 100);
    const double days = to - from;
    auto start = [&](ActiveEvent e) {
        if (bus) bus->publish(EnvironmentEventStarted{e.kind, e.body, e.end_day - e.start_day});
        KOZMO_LOG(Info, "env", std::string(to_string(e.kind)) + " başladı: " + e.body);
        active_.push_back(e);
    };
    auto has = [&](EventKind k, const std::string& b) {
        return std::any_of(active_.begin(), active_.end(), [&](const ActiveEvent& e) { return e.kind == k && e.body == b; });
    };
    // güneş parçacık olayı: ~60 günde bir (oyun varsayımı), 1-3 gün, korumasız ek doz 20-150 mSv/gün
    if (!has(EventKind::SolarParticleEvent, "all") && rng.chance(1.0 - std::exp(-days / 60.0))) {
        const double dur = rng.uniform(1.0, 3.0);
        start({EventKind::SolarParticleEvent, "all", to, to + dur, 1.0, rng.uniform(20.0, 150.0)});
    }
    for (const auto& b : bodies) {
        if (b == "mars") {
            // küresel toz fırtınası: birkaç Mars yılında bir (gerçek: 1971, 1977, 2001, 2007, 2018...), aylarca sürer
            if (!has(EventKind::GlobalDustStorm, b) && rng.chance(1.0 - std::exp(-days / (3.0 * 687.0)))) {
                start({EventKind::GlobalDustStorm, b, to, to + rng.uniform(40.0, 100.0), rng.uniform(0.15, 0.35), 0.0});
            } else if (!has(EventKind::RegionalDustStorm, b) && !has(EventKind::GlobalDustStorm, b) &&
                       rng.chance(1.0 - std::exp(-days / 120.0))) {
                start({EventKind::RegionalDustStorm, b, to, to + rng.uniform(5.0, 20.0), rng.uniform(0.6, 0.85), 0.0});
            }
        }
        // atmosfersiz yüzeylerde mikrometeoroid riski daha yüksek (oyun varsayımı)
        const double mean = (b == "moon") ? 200.0 : 600.0;
        if (rng.chance(1.0 - std::exp(-days / mean))) {
            impacts_.push_back(b);
            if (bus) bus->publish(EnvironmentEventStarted{EventKind::MicrometeoroidImpact, b, 0.0});
        }
    }
    last_day_ = to;
}

double Scheduler::solar_factor(const std::string& body, double day) const {
    double f = 1.0;
    for (const auto& e : active_)
        if ((e.body == body) && day >= e.start_day && day < e.end_day) f = std::min(f, e.solar_factor);
    return f;
}

double Scheduler::extra_dose(const std::string& body, double day) const {
    double d = 0.0;
    for (const auto& e : active_)
        if ((e.body == body || e.body == "all") && day >= e.start_day && day < e.end_day) {
            // Mars atmosferi (~20 g/cm^2) parçacık fırtınasını kısmen zayıflatır; Dünya tamamen korur (yaklaşık)
            const double atten = body == "earth" ? 0.0 : (body == "mars" ? 0.3 : 1.0);
            d += e.extra_dose_msv_per_day * atten;
        }
    return d;
}

bool Scheduler::impact_pending(const std::string& body) {
    auto it = std::find(impacts_.begin(), impacts_.end(), body);
    if (it == impacts_.end()) return false;
    impacts_.erase(it);
    return true;
}

json::Value Scheduler::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& e : active_) {
        json::Value o = json::Value::object();
        o.set("kind", static_cast<int>(e.kind));
        o.set("body", e.body);
        o.set("start", e.start_day);
        o.set("end", e.end_day);
        o.set("solar", e.solar_factor);
        o.set("dose", e.extra_dose_msv_per_day);
        a.push(o);
    }
    v.set("active", a);
    v.set("last", last_day_);
    return v;
}

Status Scheduler::from_json(const json::Value& v) {
    active_.clear();
    impacts_.clear();
    for (const auto& o : v["active"].as_array()) {
        const int k = o["kind"].as_int(-1);
        if (k < 0 || k > static_cast<int>(EventKind::MicrometeoroidImpact)) return make_error(ErrorCode::Parse, "Geçersiz çevre olayı");
        active_.push_back({static_cast<EventKind>(k), o["body"].as_string(), o["start"].as_number(), o["end"].as_number(),
                           o["solar"].as_number(1.0), o["dose"].as_number()});
    }
    last_day_ = v["last"].as_number();
    return ok_status();
}

}  // namespace kozmo::env

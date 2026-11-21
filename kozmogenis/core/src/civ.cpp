#include "kozmo/civ.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::civ {

const char* to_string(Era e) {
    switch (e) {
        case Era::Outpost: return "Karakol";
        case Era::Settlement: return "Yerleşim";
        case Era::Town: return "Kasaba";
        case Era::City: return "Şehir";
        case Era::Civilization: return "Gezegenler arası medeniyet";
    }
    return "?";
}

const char* to_string(Policy p) {
    switch (p) {
        case Policy::None: return "Politika yok";
        case Policy::Rationing: return "Karne (tayın)";
        case Policy::ResearchFocus: return "Araştırma odağı";
        case Policy::SafetyFirst: return "Önce güvenlik";
        case Policy::Festival: return "Kutlama haftası";
        case Policy::Expansion: return "Genişleme";
    }
    return "?";
}

const char* describe(Policy p) {
    switch (p) {
        case Policy::None: return "Etkisiz";
        case Policy::Rationing: return "Gıda tüketimi %10 azalır, moral günde -0.01";
        case Policy::ResearchFocus: return "Bilim insanı başına günde +1 araştırma puanı, moral günde -0.005";
        case Policy::SafetyFirst: return "Sağlık günde +0.004, araştırma -%20 (dikkatli prosedürler)";
        case Policy::Festival: return "Moral günde +0.02, gıda tüketimi +%5";
        case Policy::Expansion: return "Koloni demir stoğuna günde kişi başı +0.01 t (madencilik vardiyası), moral -0.005";
    }
    return "";
}

Era era_for(int pop, int colonies) {
    if (pop >= 1000 && colonies >= 3) return Era::Civilization;
    if (pop >= 200) return Era::City;
    if (pop >= 50) return Era::Town;
    if (pop >= 10) return Era::Settlement;
    return Era::Outpost;
}

Metrics Civilization::measure(const Game& g) const {
    Metrics m;
    double gen = 0, morale = 0, health = 0, food = 0, o2 = 0, water = 0, labs = 0;
    int shortages = 0;
    for (const auto& [id, c] : g.colonies()) {
        ++m.colonies;
        const int pop = c.population();
        m.population += pop;
        for (const auto& mod : c.modules()) {
            const auto& sp = colony::spec(mod.type);
            if (sp.power_kw > 0) gen += sp.power_kw * mod.condition;
            if (mod.type == colony::ModuleType::Lab) labs += 2.0 * mod.condition;   // spec: 2 rp/gün tam verimde
        }
        for (const auto& k : c.colonists())
            if (k.alive) {
                morale += k.needs.morale;
                health += k.needs.health;
            }
        food += c.resource("food");
        o2 += c.resource("oxygen");
        water += c.resource("water");
        if (pop > 0 && c.resource("food") / (pop * colony::kFoodPerPersonDay_t) < 10) ++shortages;
    }
    const int p = std::max(1, m.population);
    m.energy_kw_per_capita = gen / p;
    m.food_days = food / (p * colony::kFoodPerPersonDay_t);
    m.oxygen_days = o2 / (p * colony::kO2PerPersonDay_t);
    m.water_days = water / (p * colony::kWaterPerPersonDay_t);
    m.happiness = m.population ? morale / m.population : 0;
    const double h = m.population ? health / m.population : 0;
    m.stability = std::clamp(0.5 * m.happiness + 0.3 * h + 0.2 * (m.colonies ? 1.0 - static_cast<double>(shortages) / m.colonies : 0.0), 0.0, 1.0);
    m.research_per_day = labs * (policy_ == Policy::SafetyFirst ? 0.8 : 1.0);
    m.era = era_for(m.population, m.colonies);
    if (m.food_days < 30) m.notes.push_back("Gıda güvenliği zayıf (<30 gün)");
    if (m.energy_kw_per_capita < 2) m.notes.push_back("Kişi başı enerji düşük (<2 kW)");
    if (m.stability < 0.5) m.notes.push_back("İstikrar düşük: huzursuzluk riski");
    return m;
}

Status Civilization::set_policy(Policy p) {
    policy_ = p;
    return ok_status();
}

std::vector<std::string> Civilization::update(Game& g) {
    std::vector<std::string> log;
    const double day = g.day();
    if (last_day_ < 0) last_day_ = day;
    const double dd = day - last_day_;
    if (dd <= 0) return log;
    last_day_ = day;
    // politikalar: yalnız odakta değil tüm kolonilere, günlük oranla
    for (auto& [id, cref] : g.colonies()) {
        colony::Colony* c = g.colony(id);
        (void)cref;
        int scientists = 0;
        for (const auto& k : c->colonists()) scientists += k.alive && k.job == colony::Job::Scientist;
        const double food_need = c->population() * colony::kFoodPerPersonDay_t * dd;
        for (const auto& k : c->colonists()) {
            if (!k.alive) continue;
            colony::Colonist* x = c->colonist(k.id);
            double dm = 0, dh = 0;
            switch (policy_) {
                case Policy::Rationing: dm = -0.01; break;
                case Policy::ResearchFocus: dm = -0.005; break;
                case Policy::SafetyFirst: dh = 0.004; break;
                case Policy::Festival: dm = 0.02; break;
                case Policy::Expansion: dm = -0.005; break;
                case Policy::None: break;
            }
            x->needs.morale = std::clamp(x->needs.morale + dm * dd, 0.0, 1.0);
            x->needs.health = std::clamp(x->needs.health + dh * dd, 0.0, 1.0);
        }
        if (policy_ == Policy::Rationing) c->add_resource("food", 0.10 * food_need);
        if (policy_ == Policy::Festival) (void)c->take("food", 0.05 * food_need);
        if (policy_ == Policy::ResearchFocus) c->add_resource("rp", 1.0 * scientists * dd);
        if (policy_ == Policy::Expansion) c->add_resource("iron", 0.01 * c->population() * dd);
    }
    // ticaret seferleri
    for (auto& r : routes_) {
        while (day >= r.next_day) {
            colony::Colony* a = g.colony(r.from);
            colony::Colony* b = g.colony(r.to);
            r.next_day += r.period_days;
            if (!a || !b) {
                log.push_back("Ticaret yolu #" + std::to_string(r.id) + ": koloni yok");
                continue;
            }
            const double t = a->take(r.commodity, r.tons_per_trip);
            b->add_resource(r.commodity, t);
            ++r.trips;
            r.delivered_t += t;
            log.push_back(r.from + " -> " + r.to + ": " + std::to_string(t).substr(0, 5) + " t " + r.commodity);
        }
    }
    return log;
}

Result<int> Civilization::add_route(const Game& g, const std::string& from, const std::string& to, const std::string& commodity, double tons, double period) {
    if (from == to) return make_error(ErrorCode::InvalidArgument, "Aynı koloni");
    if (g.colonies().find(from) == g.colonies().end() || g.colonies().find(to) == g.colonies().end()) return make_error(ErrorCode::NotFound, "Koloni bulunamadı");
    if (tons <= 0 || period <= 0) return make_error(ErrorCode::InvalidArgument, "Miktar ve sefer aralığı pozitif olmalı");
    // aynı gök cismi değilse en kısa sefer aralığı: Hohmann süresi (yaklaşık); Ay-Dünya ~5 gün
    const std::string ba = g.colonies().at(from).body(), bb = g.colonies().at(to).body();
    double min_period = 0.5;
    if (ba != bb) {
        const bool earth_moon = (ba == "moon" && bb == "earth") || (ba == "earth" && bb == "moon");
        min_period = earth_moon ? 5.0 : 200.0;   // Dünya-Ay ~5 gün; gezegenler arası Hohmann ~200+ gün
    }
    if (period < min_period) return make_error(ErrorCode::Infeasible, "Sefer aralığı fiziksel olarak en az ~" + std::to_string(static_cast<int>(min_period)) + " gün");
    routes_.push_back({next_id_, from, to, commodity, tons, period, g.day() + period, 0, 0});
    return next_id_++;
}

Status Civilization::remove_route(int id) {
    auto it = std::find_if(routes_.begin(), routes_.end(), [&](const TradeRoute& r) { return r.id == id; });
    if (it == routes_.end()) return make_error(ErrorCode::NotFound, "Ticaret yolu yok");
    routes_.erase(it);
    return ok_status();
}

json::Value Civilization::to_json() const {
    json::Value v = json::Value::object();
    v.set("policy", static_cast<int>(policy_));
    v.set("last", last_day_);
    json::Value a = json::Value::array();
    for (const auto& r : routes_) {
        json::Value o = json::Value::object();
        o.set("id", r.id);
        o.set("from", r.from);
        o.set("to", r.to);
        o.set("c", r.commodity);
        o.set("t", r.tons_per_trip);
        o.set("p", r.period_days);
        o.set("n", r.next_day);
        o.set("trips", r.trips);
        o.set("d", r.delivered_t);
        a.push(o);
    }
    v.set("routes", a);
    v.set("next", next_id_);
    return v;
}

Status Civilization::from_json(const json::Value& v) {
    const int p = v["policy"].as_int();
    if (p < 0 || p > static_cast<int>(Policy::Expansion)) return make_error(ErrorCode::Parse, "Geçersiz politika");
    policy_ = static_cast<Policy>(p);
    last_day_ = v["last"].as_number(-1);
    routes_.clear();
    for (const auto& o : v["routes"].as_array())
        routes_.push_back({o["id"].as_int(), o["from"].as_string(), o["to"].as_string(), o["c"].as_string(), o["t"].as_number(), o["p"].as_number(1),
                           o["n"].as_number(), o["trips"].as_int(), o["d"].as_number()});
    next_id_ = v["next"].as_int(1);
    return ok_status();
}

}  // namespace kozmo::civ

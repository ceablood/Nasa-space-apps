#include "kozmo/game.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace kozmo {

double module_mass_t(colony::ModuleType t) {
    using colony::ModuleType;
    switch (t) {
        case ModuleType::Habitat: return 8.0;
        case ModuleType::Greenhouse: return 6.0;
        case ModuleType::Electrolyzer: return 3.0;
        case ModuleType::SolarArray: return 2.5;
        case ModuleType::FissionReactor: return 4.0;   // Kilopower ölçeği birkaç tondur (yaklaşık)
        case ModuleType::Mine: return 7.0;
        case ModuleType::Sabatier: return 5.0;
        case ModuleType::Lab: return 5.0;
        case ModuleType::Clinic: return 4.0;
    }
    return 5.0;
}

prop::Design preset_heavy_rocket(const std::string& target, double payload_t, int crew) {
    prop::Design d;
    d.name = "Ağır (metan/LOX + hidrojen iniş kademesi)";
    d.stages = {{"methalox_fc", 33, 3400.0, 0.06}, {"methalox_vac", 3, 1200.0, 0.06}, {"hydrolox_exp", 4, 140.0, 0.10}};
    d.payload_t = payload_t;
    d.crew = crew;
    d.target = target;
    d.land = true;
    return d;
}

prop::Design preset_light_rocket(const std::string& target, double payload_t) {
    prop::Design d;
    d.name = "Hafif (kerosen, 2 kademe — Falcon 9 sınıfı)";
    d.stages = {{"kerolox_gg", 9, 411.0, (25.6 - 9 * 0.47) / 411.0}, {"kerolox_vac", 1, 107.5, (4.0 - 0.49) / 107.5}};
    d.payload_t = payload_t;
    d.target = target;
    d.land = true;
    return d;
}

Payload standard_colony_kit() {
    using colony::Job;
    using colony::ModuleType;
    Payload p;
    p.modules = {ModuleType::Habitat, ModuleType::Greenhouse, ModuleType::Electrolyzer, ModuleType::SolarArray,
                 ModuleType::SolarArray, ModuleType::Lab};
    p.cargo = {{"water", 3.0}, {"oxygen", 0.3}, {"food", 0.3}};
    p.crew = {{"Ada", Job::Farmer}, {"Can", Job::Engineer}, {"Ece", Job::Scientist}};
    return p;
}

Payload vertical_slice_outpost() {
    using colony::Job;
    using colony::ModuleType;
    Payload p;
    p.modules = {ModuleType::Habitat, ModuleType::Habitat, ModuleType::Greenhouse, ModuleType::Electrolyzer, ModuleType::SolarArray,
                 ModuleType::SolarArray, ModuleType::SolarArray, ModuleType::SolarArray, ModuleType::Lab, ModuleType::Clinic, ModuleType::Mine};
    p.cargo = {{"water", 8.0}, {"oxygen", 0.6}, {"food", 1.2}, {"medicine", 0.5}};
    p.crew = {{"Ada", Job::Farmer}, {"Can", Job::Engineer}, {"Ece", Job::Scientist}, {"Deniz", Job::Medic},
              {"Mert", Job::Miner}, {"Selin", Job::Pilot}, {"Kaan", Job::Security}, {"Zeynep", Job::Engineer}};
    return p;
}

double payload_mass_t(const Payload& p) {
    double m = 0;
    for (auto t : p.modules) m += module_mass_t(t);
    for (const auto& [k, q] : p.cargo) m += (k == "he3" ? q / 1000.0 : q);
    m += 0.1 * static_cast<double>(p.crew.size());           // kişisel eşya
    return m;
}

Game::Game(std::uint64_t seed) : rng_(seed) {}

void Game::setup_earth_market() {
    econ::Market earth("earth", "Dünya");
    // Dünya'da bol ve ucuz olan malzemeler (oyun varsayımı)
    earth.set_item("food", {400, 400, 5, 5});
    earth.set_item("water", {800, 800, 10, 10});
    earth.set_item("oxygen", {600, 600, 10, 10});
    earth.set_item("iron", {900, 900, 8, 8});
    earth.set_item("aluminum", {700, 700, 6, 6});
    earth.set_item("electronics", {120, 120, 1, 1});
    earth.set_item("medicine", {60, 60, 0.5, 0.5});
    earth.set_item("methalox", {900, 900, 12, 12});
    earth.set_item("he3", {5, 50, 0, 0.05});               // Dünya'da He-3 çok kıt -> pahalı
    markets_["earth"] = earth;
}

void Game::new_game(const std::string& agency, double credits) {
    EventBus keep = std::move(bus_);             // abonelikler (arayüz) korunur
    *this = Game(rng_.state());
    bus_ = std::move(keep);
    agency_ = agency;
    wallet_ = econ::Wallet(credits);
    setup_earth_market();
    KOZMO_LOG(Info, "game", "Yeni oyun: " + agency);
}

colony::Colony* Game::colony(const std::string& id) {
    auto it = colonies_.find(id);
    return it == colonies_.end() ? nullptr : &it->second;
}

econ::Market* Game::market(const std::string& id) {
    auto it = markets_.find(id);
    return it == markets_.end() ? nullptr : &it->second;
}

double Game::longitude(const std::string& body) const {
    auto b = astro::find(body);
    return b ? astro::mean_longitude_deg(*b.value(), day_) : 0.0;
}

Result<astro::TransferWindow> Game::window_to(const std::string& target) const {
    return astro::next_window("earth", target, longitude("earth"), longitude(target));
}

double Game::local_hour(const std::string& body) const {
    auto b = astro::find(body);
    if (!b) return 12.0;
    const double day_h = std::fabs(b.value()->day_h);         // güneş günü uzunluğu (NASA "Length of Day")
    const double h = std::fmod(day_ * 24.0, day_h);
    return h / day_h * 24.0;
}

double Game::crew_hour(const std::string& body) const {
    if (body == "mars" || body == "earth") return local_hour(body);
    return std::fmod(day_ * 24.0, 24.0);
}

Result<prop::Report> Game::evaluate(const prop::Design& d) const { return prop::analyze(d, tree_.unlocked_list()); }

Result<int> Game::launch(const prop::Design& d, const Payload& p) {
    auto r = evaluate(d);
    if (!r) return r.error();
    const prop::Report& rep = r.value();
    if (!rep.feasible) return make_error(ErrorCode::Infeasible, rep.problems.front());
    const double need = payload_mass_t(p);
    if (need > d.payload_t + 1e-9)
        return make_error(ErrorCode::InvalidArgument, "Yük kapasitesi yetersiz: " + std::to_string(need) + " t gerekli, tasarım " +
                                                          std::to_string(d.payload_t) + " t");
    if (static_cast<int>(p.crew.size()) != d.crew)
        return make_error(ErrorCode::InvalidArgument, "Mürettebat sayısı tasarımla uyuşmuyor");
    auto target = astro::find(d.target);
    if (!target) return target.error();
    if (!p.modules.empty() && !target.value()->has_surface())
        return make_error(ErrorCode::Infeasible, target.value()->name_tr + " yüzeyine koloni kurulamaz (katı yüzey yok)");

    double transfer_days = 0;
    if (d.target == "moon") {
        auto E = *astro::find("earth").value();
        transfer_days = astro::hohmann(E.mu(), E.radius_m() + 200e3, target.value()->semi_major_m()).transfer_days;
    } else {
        auto w = window_to(d.target);
        if (!w) return w.error();
        const double until = w.value().days_until;
        const double since = w.value().synodic_days - until;      // geçen pencereden bu yana
        if (until > kWindowToleranceDays && since > kWindowToleranceDays)
            return make_error(ErrorCode::Infeasible, "Fırlatma penceresi kapalı. Sonraki pencere " +
                                                         std::to_string(static_cast<int>(until)) + " gün sonra");
        auto E = *astro::find("earth").value();
        transfer_days = astro::hohmann(astro::kMuSun, E.semi_major_m(), target.value()->semi_major_m()).transfer_days;
    }
    auto pay = wallet_.spend(rep.cost_mcr * 1000.0, "Fırlatma: " + d.name + " -> " + d.target, day_);
    if (!pay) return pay.error();

    Mission m;
    m.id = next_mission_++;
    m.design_name = d.name;
    m.target = d.target;
    m.payload = p;
    m.depart_day = day_;
    m.arrive_day = day_ + transfer_days;
    m.success_p = rep.success_p;
    if (!rng_.chance(rep.success_p)) {
        m.state = MissionState::Lost;
        missions_.push_back(m);
        KOZMO_LOG(Warn, "mission", "Görev " + std::to_string(m.id) + " fırlatmada kaybedildi");
        bus_.publish(MissionLost{m.id, m.target, "Fırlatma/uçuş arızası"});
        return m.id;
    }
    missions_.push_back(m);
    bus_.publish(MissionLaunched{m.id, m.target, m.arrive_day});
    return m.id;
}

void Game::arrive(Mission& m) {
    m.state = MissionState::Arrived;
    auto body = astro::find(m.target);
    const std::string cid = m.target + "_koloni";
    colony::Colony* c = colony(cid);
    if (!c && (!m.payload.modules.empty() || !m.payload.crew.empty())) {
        const bool co2 = m.target == "mars" || m.target == "venus";
        const double dist = body.value()->parent == "sun" ? body.value()->distance_1e6km : 149.6;
        colonies_.emplace(cid, colony::Colony(cid, m.target, dist, co2));
        c = colony(cid);
        bus_.publish(ColonyFounded{cid, m.target});
        if (focus_.empty()) focus_ = cid;
        KOZMO_LOG(Info, "colony", body.value()->name_tr + " kolonisi kuruldu");
        if (markets_.find(cid) == markets_.end()) {
            econ::Market mk(cid, body.value()->name_tr + " kolonisi");
            mk.set_item("regolith", {0, 200, 0, 0});
            mk.set_item("iron", {0, 60, 0, 0});
            mk.set_item("water", {0, 40, 0, 0});
            mk.set_item("food", {0, 20, 0, 0});
            mk.set_item("he3", {0, 20, 0, 0});
            markets_[cid] = mk;
        }
    }
    if (c) {
        for (auto t : m.payload.modules) {
            auto st = c->add_module(t, tree_.unlocked_list());
            if (!st) KOZMO_LOG(Warn, "colony", "Modül kurulamadı: " + st.error().message);
        }
        for (const auto& [k, q] : m.payload.cargo) c->add_resource(k, q);
        for (const auto& [name, job] : m.payload.crew) {
            const int cid_new = c->add_colonist(name, job, 0.5, rng_);
            c->add_dose(cid_new, env::cruise_dose_msv_per_day() * (m.arrive_day - m.depart_day));   // yolculuk dozu
        }
    }
    bus_.publish(MissionArrived{m.id, m.target});
}

Status Game::found_outpost(const std::string& body, const Payload& p) {
    if (!astro::find(body)) return make_error(ErrorCode::NotFound, "Bilinmeyen gök cismi: " + body);
    Mission m;
    m.id = next_mission_++;
    m.design_name = "Senaryo başlangıcı";
    m.target = body;
    m.payload = p;
    m.depart_day = m.arrive_day = day_;
    arrive(m);
    m.state = MissionState::Arrived;
    missions_.push_back(m);
    return ok_status();
}

Status Game::build_module(const std::string& colony_id, colony::ModuleType t) {
    colony::Colony* c = colony(colony_id);
    if (!c) return make_error(ErrorCode::NotFound, "Koloni yok: " + colony_id);
    const double iron_needed = module_mass_t(t) * 0.6;          // yerel demirden üretim (oyun varsayımı)
    if (c->resource("iron") < iron_needed)
        return make_error(ErrorCode::InsufficientResources, "Yerinde inşa için " + std::to_string(iron_needed) + " t demir gerekli");
    const double cost = colony::spec(t).build_cost;
    if (wallet_.balance() < cost) return make_error(ErrorCode::InsufficientFunds, "Yetersiz bakiye");
    auto st = c->add_module(t, tree_.unlocked_list());
    if (!st) return st;
    c->take("iron", iron_needed);
    return wallet_.spend(cost, std::string("İnşa: ") + colony::module_name(t), day_);
}

Result<econ::Trade> Game::trade(const std::string& market_id, const std::string& k, double qty, bool buy) {
    econ::Market* m = market(market_id);
    if (!m) return make_error(ErrorCode::NotFound, "Piyasa yok: " + market_id);
    colony::Colony* c = colony(market_id);          // koloni piyasası ise mal koloni deposundan çıkar/girer
    if (!buy && c && c->resource(k) < qty) return make_error(ErrorCode::InsufficientResources, "Koloni deposunda yeterli " + k + " yok");
    auto r = buy ? m->buy(k, qty, wallet_, day_) : m->sell(k, qty, wallet_, day_);
    if (!r) return r;
    if (c) {
        if (buy) c->add_resource(k, qty);
        else c->take(k, qty);
    }
    return r;
}

void Game::advance(double days) {
    if (days <= 0) return;
    const double end = day_ + days;
    while (day_ < end - 1e-9) {
        const double step_h = std::min(1.0, (end - day_) * 24.0);
        day_ += step_h / 24.0;
        // görev varışları
        for (auto& m : missions_)
            if (m.state == MissionState::InTransit && day_ >= m.arrive_day) arrive(m);
        // koloniler: odak tam, diğerleri 6 saatte bir kaba (ölçeklenebilir simülasyon)
        const long long hour_index = static_cast<long long>(std::floor(day_ * 24.0 + 1e-6));
        // çevre olayları: günde bir değerlendirilir
        if (hour_index % 24 == 0) {
            std::vector<std::string> bodies;
            for (const auto& [id, c] : colonies_)
                if (std::find(bodies.begin(), bodies.end(), c.body()) == bodies.end()) bodies.push_back(c.body());
            env_.advance(day_ - 1.0, day_, bodies, rng_, &bus_);
            for (auto& [id, c] : colonies_)
                if (env_.impact_pending(c.body())) c.damage_random_module(rng_.uniform(0.15, 0.4), rng_, &bus_);
        }
        for (auto& [id, c] : colonies_) {
            auto base = env::surface_dose_msv_per_day(c.body());
            c.set_environment(env_.solar_factor(c.body(), day_),
                              (base ? base.value() : env::cruise_dose_msv_per_day()) + env_.extra_dose(c.body(), day_));
            if (id == focus_) {
                c.tick(step_h, local_hour(c.body()), rng_, &bus_, colony::SimDetail::Full, crew_hour(c.body()));
            } else if (hour_index % 6 == 0) {
                c.tick(6.0, local_hour(c.body()), rng_, &bus_, colony::SimDetail::Coarse, crew_hour(c.body()));
            }
            const double rp = c.take("rp", 1e9);
            if (rp > 0) tree_.add_points(rp, &bus_);
        }
        if (hour_index % 24 == 0)
            for (auto& [id, mk] : markets_) mk.tick(1.0);
    }
}

// ------------------------------------------------------------------------ kayıt
std::string Game::save() const {
    json::Value v = json::Value::object();
    v.set("format", "kozmogenis-save");
    v.set("version", 1);
    v.set("day", day_);
    v.set("agency", agency_);
    v.set("credits", wallet_.balance());
    v.set("rng", std::to_string(rng_.state()));              // 64 bit: kesinlik kaybı olmasın diye metin
    v.set("focus", focus_);
    v.set("next_mission", next_mission_);
    v.set("research", tree_.to_json());
    v.set("environment", env_.to_json());
    json::Value cols = json::Value::array();
    for (const auto& [id, c] : colonies_) cols.push(c.to_json());
    v.set("colonies", cols);
    json::Value mk = json::Value::object();
    for (const auto& [id, m] : markets_) {
        json::Value o = json::Value::object();
        o.set("name", m.name());
        json::Value items = json::Value::object();
        for (const auto& [k, it] : m.items()) {
            json::Value a = json::Value::array();
            a.push(it.stock);
            a.push(it.target_stock);
            a.push(it.production);
            a.push(it.consumption);
            items.set(k, a);
        }
        o.set("items", items);
        mk.set(id, o);
    }
    v.set("markets", mk);
    json::Value ms = json::Value::array();
    for (const auto& m : missions_) {
        json::Value o = json::Value::object();
        o.set("id", m.id);
        o.set("design", m.design_name);
        o.set("target", m.target);
        o.set("depart", m.depart_day);
        o.set("arrive", m.arrive_day);
        o.set("state", static_cast<int>(m.state));
        json::Value mods = json::Value::array();
        for (auto t : m.payload.modules) mods.push(static_cast<int>(t));
        o.set("modules", mods);
        json::Value cargo = json::Value::object();
        for (const auto& [k, q] : m.payload.cargo) cargo.set(k, q);
        o.set("cargo", cargo);
        json::Value crew = json::Value::array();
        for (const auto& [n, j] : m.payload.crew) {
            json::Value c = json::Value::array();
            c.push(n);
            c.push(static_cast<int>(j));
            crew.push(c);
        }
        o.set("crew", crew);
        ms.push(o);
    }
    v.set("missions", ms);
    return v.dump(1);
}

Status Game::load(const std::string& text) {
    auto p = json::parse(text);
    if (!p) return p.error();
    const json::Value& v = p.value();
    if (v["format"].as_string() != "kozmogenis-save") return make_error(ErrorCode::Parse, "Bu bir KOZMOGENİS kaydı değil");
    if (v["version"].as_int() != 1) return make_error(ErrorCode::Parse, "Desteklenmeyen kayıt sürümü");
    Game g(1);
    g.day_ = v["day"].as_number();
    g.agency_ = v["agency"].as_string();
    g.wallet_ = econ::Wallet(v["credits"].as_number());
    g.rng_.set_state(std::strtoull(v["rng"].as_string().c_str(), nullptr, 10));   // istisnasız (UE: exceptions kapalı)
    g.focus_ = v["focus"].as_string();
    g.next_mission_ = v["next_mission"].as_int(1);
    auto st = g.tree_.from_json(v["research"]);
    if (!st) return st;
    if (v.has("environment")) {
        auto es = g.env_.from_json(v["environment"]);
        if (!es) return es;
    }
    for (const auto& cj : v["colonies"].as_array()) {
        auto c = colony::Colony::from_json(cj);
        if (!c) return c.error();
        g.colonies_.emplace(c.value().id(), c.value());
    }
    for (const auto& [id, o] : v["markets"].as_object()) {
        econ::Market m(id, o["name"].as_string());
        for (const auto& [k, a] : o["items"].as_object())
            m.set_item(k, {a.at(0).as_number(), a.at(1).as_number(100), a.at(2).as_number(), a.at(3).as_number()});
        g.markets_[id] = m;
    }
    for (const auto& o : v["missions"].as_array()) {
        Mission m;
        m.id = o["id"].as_int();
        m.design_name = o["design"].as_string();
        m.target = o["target"].as_string();
        m.depart_day = o["depart"].as_number();
        m.arrive_day = o["arrive"].as_number();
        const int s = o["state"].as_int();
        if (s < 0 || s > 2) return make_error(ErrorCode::Parse, "Geçersiz görev durumu");
        m.state = static_cast<MissionState>(s);
        for (const auto& t : o["modules"].as_array()) m.payload.modules.push_back(static_cast<colony::ModuleType>(t.as_int()));
        for (const auto& [k, q] : o["cargo"].as_object()) m.payload.cargo[k] = q.as_number();
        for (const auto& c : o["crew"].as_array())
            m.payload.crew.emplace_back(c.at(0).as_string(), static_cast<colony::Job>(c.at(1).as_int()));
        g.missions_.push_back(m);
    }
    // olay aboneleri (UE5 arayüzü vb.) korunur: yalnızca durum değişir
    EventBus keep = std::move(bus_);
    *this = std::move(g);
    bus_ = std::move(keep);
    return ok_status();
}

}  // namespace kozmo

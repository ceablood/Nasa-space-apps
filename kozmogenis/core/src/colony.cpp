#include "kozmo/colony.hpp"

#include "kozmo/environment.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>

namespace kozmo::colony {

double solar_flux(double distance_1e6km) {
    const double au = distance_1e6km * 1e9 / 1.495978707e11;
    return au > 0 ? kSolarConstant / (au * au) : 0.0;
}

const char* job_name(Job j) {
    switch (j) {
        case Job::Farmer: return "Çiftçi";
        case Job::Engineer: return "Mühendis";
        case Job::Miner: return "Madenci";
        case Job::Scientist: return "Bilim insanı";
        case Job::Medic: return "Doktor";
        case Job::Pilot: return "Pilot";
        case Job::Security: return "Güvenlik görevlisi";
    }
    return "?";
}

const char* activity_name(Activity a) {
    switch (a) {
        case Activity::Idle: return "Boşta";
        case Activity::Work: return "Çalışıyor";
        case Activity::Eat: return "Yemek";
        case Activity::Sleep: return "Uyku";
        case Activity::Socialize: return "Sosyal";
        case Activity::Treatment: return "Tedavi";
    }
    return "?";
}

const char* module_name(ModuleType t) {
    switch (t) {
        case ModuleType::Habitat: return "Yaşam modülü";
        case ModuleType::Greenhouse: return "Sera";
        case ModuleType::Electrolyzer: return "Elektroliz ünitesi";
        case ModuleType::SolarArray: return "Güneş paneli dizisi";
        case ModuleType::FissionReactor: return "Fisyon reaktörü";
        case ModuleType::Mine: return "Maden";
        case ModuleType::Sabatier: return "Sabatier yakıt reaktörü";
        case ModuleType::Lab: return "Laboratuvar";
        case ModuleType::Clinic: return "Klinik";
        case ModuleType::WaterRecycler: return "Su geri dönüşüm sistemi";
    }
    return "?";
}

const ModuleSpec& spec(ModuleType t) {
    // Elektroliz: 2 H2O -> 2 H2 + O2 ; kütlece 1 t su -> 0.889 t O2 (stokiyometri, fizik).
    // Diğer oranlar oyun varsayımıdır. Güneş paneli gücü 1 AU'da günlük ORTALAMA değerdir.
    static const std::map<ModuleType, ModuleSpec> s = {
        {ModuleType::Habitat, {ModuleType::Habitat, -3, 0, Job::Engineer, 6, {}, {}, 2000, ""}},
        {ModuleType::Greenhouse, {ModuleType::Greenhouse, -8, 1, Job::Farmer, 0, {{"water", 0.020}}, {{"food", 0.013}}, 1500, ""}},
        {ModuleType::Electrolyzer, {ModuleType::Electrolyzer, -6, 1, Job::Engineer, 0, {{"water", 0.012}}, {{"oxygen", 0.012 * 0.889}}, 1800, ""}},
        {ModuleType::SolarArray, {ModuleType::SolarArray, 10, 0, Job::Engineer, 0, {}, {}, 1200, ""}},
        {ModuleType::FissionReactor, {ModuleType::FissionReactor, 40, 1, Job::Engineer, 0, {}, {}, 9000, "fission"}},
        {ModuleType::Mine, {ModuleType::Mine, -10, 2, Job::Miner, 0, {}, {{"regolith", 2.0}, {"iron", 0.15}, {"water", 0.035}}, 2500, ""}},
        {ModuleType::Sabatier, {ModuleType::Sabatier, -12, 1, Job::Engineer, 0, {{"water", 0.05}}, {{"methalox", 0.04}}, 4000, "isru"}},
        {ModuleType::Lab, {ModuleType::Lab, -5, 1, Job::Scientist, 0, {}, {{"rp", 2.0}}, 3000, ""}},
        {ModuleType::Clinic, {ModuleType::Clinic, -4, 1, Job::Medic, 0, {{"medicine", 0.0005}}, {}, 2500, ""}},
        // ISS ECLSS su geri kazanımı 2023'te %98'e ulaştı (NASA); modülsüz temel habitat %85 varsayılır
        {ModuleType::WaterRecycler, {ModuleType::WaterRecycler, -2, 0, Job::Engineer, 0, {}, {}, 1800, ""}},
    };
    return s.at(t);
}

Colony::Colony(std::string id, std::string body_key, double dist, bool co2)
    : id_(std::move(id)), body_(std::move(body_key)), solar_flux_(::kozmo::colony::solar_flux(dist)), co2_atmosphere_(co2) {}

Status Colony::add_module(ModuleType t, const std::vector<std::string>& unlocked) {
    const ModuleSpec& sp = spec(t);
    if (!sp.research.empty() && std::find(unlocked.begin(), unlocked.end(), sp.research) == unlocked.end())
        return make_error(ErrorCode::Locked, std::string(module_name(t)) + " için araştırma gerekli: " + sp.research);
    if (t == ModuleType::Sabatier && !co2_atmosphere_)
        return make_error(ErrorCode::Infeasible, "Sabatier reaktörü CO2 atmosferi gerektirir (Mars, Venüs)");
    modules_.push_back({t, 1.0, 0.0});
    return ok_status();
}

int Colony::add_colonist(const std::string& name, Job job, double skill, Rng& rng) {
    Colonist c;
    c.id = next_id_++;
    c.name = name;
    c.job = job;
    c.skill = std::clamp(skill, 0.0, 1.0);
    c.needs.hunger = rng.uniform(0.05, 0.3);
    c.needs.fatigue = rng.uniform(0.05, 0.3);
    c.needs.morale = rng.uniform(0.6, 0.85);
    c.personality = Personality::random(rng);
    colonists_.push_back(c);
    return c.id;
}

double Colony::resource(const std::string& k) const {
    auto it = stock_.find(k);
    return it == stock_.end() ? 0.0 : it->second;
}

int Colony::population() const {
    return static_cast<int>(std::count_if(colonists_.begin(), colonists_.end(), [](const Colonist& c) { return c.alive; }));
}

int Colony::housing() const {
    int h = 0;
    for (const auto& m : modules_) h += spec(m.type).capacity;
    return h;
}

double Colony::average_morale() const {
    double s = 0;
    int n = 0;
    for (const auto& c : colonists_)
        if (c.alive) {
            s += c.needs.morale;
            ++n;
        }
    return n ? s / n : 0.0;
}

Personality Personality::random(Rng& rng) {
    Personality p;
    for (double* x : {&p.courage, &p.curiosity, &p.patience, &p.diligence, &p.sociability, &p.leadership, &p.competitiveness,
                      &p.helpfulness, &p.caution})
        *x = std::clamp(0.5 + (rng.uniform(0.0, 1.0) + rng.uniform(0.0, 1.0) - 1.0) * 0.6, 0.0, 1.0);   // üçgen dağılım
    return p;
}

std::vector<std::string> Personality::traits() const {
    std::vector<std::string> t;
    auto axis = [&](double v, const char* hi, const char* lo) {
        if (v > 0.68) t.push_back(hi);
        else if (v < 0.32) t.push_back(lo);
    };
    axis(courage, "Cesur", "Korkak");
    axis(curiosity, "Meraklı", "İlgisiz");
    axis(patience, "Sabırlı", "Aceleci");
    axis(diligence, "Çalışkan", "Tembel");
    axis(sociability, "Sosyal", "İçine kapanık");
    if (leadership > 0.68) t.push_back("Lider ruhlu");
    if (competitiveness > 0.68) t.push_back("Rekabetçi");
    if (helpfulness > 0.68) t.push_back("Yardımsever");
    axis(caution, "Dikkatli", "Risk alan");
    return t;
}

Status Colony::order(int id, Activity a, double hours) {
    Colonist* c = colonist(id);
    if (!c || !c->alive) return make_error(ErrorCode::NotFound, "Kolonist yok");
    c->activity = a;
    c->activity_hours_left = std::max(0.0, hours);
    c->ordered = hours > 0;
    return ok_status();
}

Colonist* Colony::colonist(int id) {
    for (auto& c : colonists_)
        if (c.id == id) return &c;
    return nullptr;
}

void Colony::repair(ModuleType t, double amount) {
    for (auto& m : modules_)
        if (m.type == t && m.condition < 1.0) {
            m.condition = std::min(1.0, m.condition + amount);
            return;
        }
}

void Colony::damage_module(ModuleType t, double amount) {
    for (auto& m : modules_)
        if (m.type == t) m.condition = std::clamp(m.condition - amount, 0.0, 1.0);
}

double Colony::module_condition(ModuleType t) const {
    double s = 0;
    int n = 0;
    for (const auto& m : modules_)
        if (m.type == t) {
            s += m.condition;
            ++n;
        }
    return n ? s / n : 1.0;
}

Activity Colony::choose_activity(const Colonist& c, double h) const {
    const bool night = h < 6.0 || h >= 22.0;
    const bool day_shift = h >= 8.0 && h < 18.0;
    const bool clinic = std::any_of(modules_.begin(), modules_.end(), [](const Module& m) { return m.type == ModuleType::Clinic; });
    const bool food = resource("food") > 0.0;
    // fayda tabanlı seçim (utility AI)
    double best = 0.05;
    Activity a = Activity::Idle;
    auto consider = [&](Activity act, double u) {
        if (u > best) {
            best = u;
            a = act;
        }
    };
    const Personality& p = c.personality;
    consider(Activity::Sleep, c.needs.fatigue * 1.2 + (night ? 0.55 : 0.0));
    if (food) consider(Activity::Eat, c.needs.hunger * 1.4);
    if (!c.dose_limit_reached)
        consider(Activity::Work, (day_shift ? 0.75 : 0.15) * (1.0 - c.needs.fatigue) * (0.6 + 0.4 * c.needs.health) * (0.8 + 0.4 * p.diligence));
    consider(Activity::Socialize, ((1.0 - c.needs.morale) * 0.8 + (!day_shift && !night ? 0.2 : 0.0)) * (0.6 + 0.8 * p.sociability));
    if (clinic) consider(Activity::Treatment, (1.0 - c.needs.health) * (1.3 + 0.6 * p.caution));
    return a;
}

void Colony::tick_npc_full(Colonist& c, double dt, double h, Rng& rng, bool food_ok) {
    Needs& n = c.needs;
    if (c.activity_hours_left <= 0.0) {
        c.ordered = false;
        c.activity = choose_activity(c, h);
        switch (c.activity) {
            case Activity::Work: c.activity_hours_left = 4.0; break;
            case Activity::Eat: c.activity_hours_left = 1.0; break;
            case Activity::Sleep: c.activity_hours_left = 8.0; break;
            case Activity::Socialize: c.activity_hours_left = 1.5; break;
            case Activity::Treatment: c.activity_hours_left = 2.0; break;
            case Activity::Idle: c.activity_hours_left = 1.0; break;
        }
    }
    c.activity_hours_left -= dt;
    const bool asleep = c.activity == Activity::Sleep;
    n.hunger = std::min(1.0, n.hunger + 0.042 * dt);                    // ~24 saatte tamamen acıkır
    n.fatigue = std::clamp(n.fatigue + (asleep ? -0.12 : 0.036) * dt, 0.0, 1.0);
    switch (c.activity) {
        case Activity::Eat: {
            const double meal = kFoodPerPersonDay_t / 3.0 * dt;           // saatlik öğün payı
            if (stock_["food"] >= meal) {
                stock_["food"] -= meal;
                n.hunger = std::max(0.0, n.hunger - 0.35 * dt);
                n.morale = std::min(1.0, n.morale + 0.01 * dt);
            } else {
                c.activity_hours_left = 0.0;
            }
            break;
        }
        case Activity::Work:
            c.hours_worked += dt;
            c.skill = std::min(1.0, c.skill + 0.0004 * dt);               // iş başında öğrenme
            n.morale = std::max(0.0, n.morale - 0.004 * dt);
            break;
        case Activity::Socialize: n.morale = std::min(1.0, n.morale + 0.05 * dt); break;
        case Activity::Treatment: n.health = std::min(1.0, n.health + 0.04 * dt); break;
        default: break;
    }
    if (asleep && n.fatigue <= 0.02) c.activity_hours_left = 0.0;      // dinlenince uyan
    if (n.hunger > 0.85) n.health = std::max(0.0, n.health - 0.004 * dt);
    if (n.fatigue > 0.9) n.morale = std::max(0.0, n.morale - 0.01 * dt);
    if (!food_ok) n.morale = std::max(0.0, n.morale - 0.006 * dt);
    if (rng.chance(0.00015 * dt)) n.health = std::max(0.0, n.health - rng.uniform(0.1, 0.3));   // hastalık/kaza
}

void Colony::tick_npc_coarse(Colonist& c, double dt, bool food_ok) {
    // ortalama günlük davranış: 8 saat iş, 8 saat uyku, 3 öğün; ihtiyaçlar dengeye yaklaşır
    Needs& n = c.needs;
    const double d = dt / 24.0;
    if (food_ok) {
        const double need = kFoodPerPersonDay_t * d;
        if (stock_["food"] >= need) {
            stock_["food"] -= need;
            n.hunger += (0.25 - n.hunger) * std::min(1.0, d * 2.0);
        } else {
            food_ok = false;
        }
    }
    if (!food_ok) {
        n.hunger = std::min(1.0, n.hunger + 0.6 * d);
        n.morale = std::max(0.0, n.morale - 0.15 * d);
    }
    n.fatigue += (0.3 - n.fatigue) * std::min(1.0, d * 2.0);
    if (c.ordered && c.activity_hours_left > 0) {
        c.activity_hours_left -= dt;            // emir (tahliye/onarım) süresince kendi işine dönmez
        if (c.activity_hours_left <= 0) c.ordered = false;
    } else if (!c.dose_limit_reached) {
        c.hours_worked += 8.0 * d;
        c.activity = Activity::Work;
    } else {
        c.activity = Activity::Idle;
    }
    if (n.hunger > 0.85) n.health = std::max(0.0, n.health - 0.1 * d);
}

TickReport Colony::tick(double dt, double local_hour, Rng& rng, EventBus* bus, SimDetail detail, double crew_hour) {
    if (crew_hour < 0) crew_hour = local_hour;
    TickReport rep;
    if (dt <= 0) return rep;
    const double d = dt / 24.0;
    const double flux_ratio = solar_flux_ / kSolarConstant * env_solar_;     // toz fırtınası güneşi keser
    // güneş: yerel gündüz eğrisi (günlük ortalaması 1 olacak şekilde pi ile ölçekli yarım sinüs)
    const double sun = std::max(0.0, std::sin(3.14159265358979 * (local_hour - 6.0) / 12.0)) * 3.14159265358979;

    // 1) personel: iş gücü 24 saatlik kayan ortalamayla ölçülür. Bir personel yuvası = günde 8 saatlik vardiya.
    //    Tam modda o an çalışanlar x3 (saatlik eşdeğer), kaba modda 8 saat varsayımı -> iki mod aynı ortalamaya
    //    yakınsar; modüller çalışan mola verince anında durmaz (vardiya devri).
    std::map<Job, double> instant;
    for (const auto& c : colonists_) {
        if (!c.alive) continue;
        const double sf = 0.5 + 0.5 * c.skill;
        if (detail == SimDetail::Full) {
            if (c.activity == Activity::Work) instant[c.job] += 3.0 * sf;
        } else {
            if (!c.dose_limit_reached) instant[c.job] += sf;
        }
    }
    const bool first = labor_ema_.empty();
    for (Job j : {Job::Farmer, Job::Engineer, Job::Miner, Job::Scientist, Job::Medic, Job::Pilot}) {
        double& e = labor_ema_[j];
        if (first || detail == SimDetail::Coarse) {
            double avg = 0;                               // ilk adım: vardiya varsayımıyla başlat
            for (const auto& c : colonists_)
                if (c.alive && c.job == j) avg += 0.5 + 0.5 * c.skill;
            e = detail == SimDetail::Coarse ? instant[j] : avg;
        } else {
            e += (instant[j] - e) * std::min(1.0, dt / 24.0);
        }
    }
    std::map<Job, double>& workers = labor_ema_;
    std::map<Job, double> need;
    for (const auto& m : modules_) need[spec(m.type).staff_job] += spec(m.type).staff;
    auto staff_ratio = [&](const Module& m) {
        const ModuleSpec& sp = spec(m.type);
        if (sp.staff == 0) return 1.0;
        const double req = need[sp.staff_job];
        return req > 0 ? std::min(1.0, workers[sp.staff_job] / req) : 1.0;
    };

    // 2) enerji dengesi + batarya (her yaşam modülü 50 kWh depolar; oyun varsayımı)
    double produced = 0, demand = 0;
    for (auto& m : modules_) {
        const ModuleSpec& sp = spec(m.type);
        if (sp.power_kw > 0) {
            double f = m.condition;
            if (m.type == ModuleType::SolarArray) f *= flux_ratio * sun;
            else f *= staff_ratio(m);
            produced += sp.power_kw * f;
        } else {
            demand += -sp.power_kw;
        }
    }
    const double battery_cap = 50.0 * static_cast<double>(std::count_if(modules_.begin(), modules_.end(),
                                                                         [](const Module& m) { return m.type == ModuleType::Habitat; }));
    double& batt = stock_["battery_kwh"];
    batt = std::min(batt, battery_cap);
    double ratio = 1.0;
    const double net_kwh = (produced - demand) * dt;
    if (net_kwh >= 0) {
        batt = std::min(battery_cap, batt + net_kwh);
    } else if (batt >= -net_kwh) {
        batt += net_kwh;
    } else {
        const double available = produced * dt + batt;
        batt = 0;
        ratio = demand > 0 ? std::clamp(available / (demand * dt), 0.0, 1.0) : 1.0;
    }
    rep.power_produced_kw = produced;
    rep.power_demand_kw = demand;
    rep.power_ratio = ratio;

    // 3) üretim zincirleri (girdi yetersizse verim orantılı düşer)
    for (auto& m : modules_) {
        const ModuleSpec& sp = spec(m.type);
        if (sp.power_kw > 0) {
            m.efficiency = m.type == ModuleType::SolarArray ? flux_ratio * sun * m.condition : staff_ratio(m) * m.condition;
            continue;
        }
        double eff = staff_ratio(m) * ratio * m.condition;
        for (const auto& [k, q] : sp.input_per_day) {
            const double want = q * d * eff;
            if (want > 0 && resource(k) < want) eff *= resource(k) / want;
        }
        m.efficiency = eff;
        for (const auto& [k, q] : sp.input_per_day) {
            stock_[k] -= q * d * eff;
            rep.consumed[k] += q * d * eff;
        }
        for (const auto& [k, q] : sp.output_per_day) {
            stock_[k] += q * d * eff;
            rep.produced[k] += q * d * eff;
        }
    }

    // 4) yaşam desteği: O2 ve su sürekli tüketilir
    const int pop = population();
    bool o2_ok = true, water_ok = true;
    const double o2_need = kO2PerPersonDay_t * pop * d;
    // temel habitat %85 su geri dönüşümü; su geri dönüşüm sistemi verimiyle %98'e (ISS 2023) yaklaşır
    double recycler = 0.0;
    for (const auto& m : modules_)
        if (m.type == ModuleType::WaterRecycler) recycler = std::max(recycler, m.efficiency);
    const double loss = 0.15 - (0.15 - 0.02) * std::clamp(recycler, 0.0, 1.0);
    const double w_need = kWaterPerPersonDay_t * pop * d * loss;
    if (resource("oxygen") >= o2_need) stock_["oxygen"] -= o2_need; else { o2_ok = false; stock_["oxygen"] = 0; }
    if (resource("water") >= w_need) stock_["water"] -= w_need; else { water_ok = false; stock_["water"] = 0; }
    rep.consumed["oxygen"] += o2_need;
    rep.consumed["water"] += w_need;
    const bool food_ok = resource("food") > 0.0;
    auto shortage = [&](const char* r) {
        rep.shortages.push_back(r);
        if (bus) bus->publish(ResourceShortage{id_, r});
    };
    if (!o2_ok) shortage("oxygen");
    if (!water_ok) shortage("water");
    if (!food_ok && pop > 0) shortage("food");
    if (ratio < 0.999) shortage("power");

    // 5) NPC yaşamı
    const double crowd = housing() > 0 ? static_cast<double>(pop) / housing() : 2.0;
    for (auto& c : colonists_) {
        if (!c.alive) continue;
        if (detail == SimDetail::Full) tick_npc_full(c, dt, crew_hour, rng, food_ok);
        else tick_npc_coarse(c, dt, food_ok);
        if (!o2_ok) c.needs.health -= 0.25 * dt;                 // oksijensizlik saatler içinde öldürür
        if (!water_ok) c.needs.health -= 0.012 * dt;             // susuzluk ~3-4 gün
        if (crowd > 1.0) c.needs.morale = std::max(0.0, c.needs.morale - 0.01 * (crowd - 1.0) * dt);
        if (env_dose_ > 0) {
            const bool sheltered = housing() > 0;
            c.dose_msv += env_dose_ * (sheltered ? env::kHabitatShielding : 1.0) * d;
            if (!c.dose_limit_reached && c.dose_msv >= env::kCareerLimitMsv) {
                c.dose_limit_reached = true;
                KOZMO_LOG(Warn, "colony", id_ + ": " + c.name + " radyasyon kariyer sınırını aştı");
                if (bus) bus->publish(RadiationLimitReached{id_, c.name, c.dose_msv});
            }
        }
        if (ratio < 0.5) c.needs.morale = std::max(0.0, c.needs.morale - 0.01 * dt);
        if (c.needs.health <= 0.0) {
            c.alive = false;
            ++rep.deaths;
            const char* cause = !o2_ok ? "oksijen yetersizliği" : (!water_ok ? "susuzluk" : "sağlık sorunları");
            KOZMO_LOG(Warn, "colony", id_ + ": " + c.name + " hayatını kaybetti (" + cause + ")");
            if (bus) bus->publish(ColonistDied{id_, c.name, cause});
        }
    }

    // 6) bakım: modüller yıpranır, çalışan mühendisler onarır
    const double eng = workers[Job::Engineer];
    for (auto& m : modules_) {
        m.condition = std::clamp(m.condition - 0.004 * d + 0.006 * d * std::min(1.0, eng / std::max(1.0, need[Job::Engineer] + 1.0)), 0.2, 1.0);
    }

    // 7) nüfus artışı (oyun varsayımı): yüksek moral + boş yatak + yeterli gıda
    const double morale = average_morale();
    if (pop >= 2 && morale > 0.75 && pop < housing() && food_ok && rng.chance(0.004 * d * pop)) {
        add_colonist("Koloni doğumlu #" + std::to_string(next_id_), Job::Farmer, 0.1, rng);
        ++rep.births;
    }
    if (bus && pop > 0 && morale < 0.3) bus->publish(ColonyMoraleLow{id_, morale});
    return rep;
}

}  // namespace kozmo::colony

namespace kozmo::colony {

double Colony::take(const std::string& k, double t) {
    auto it = stock_.find(k);
    if (it == stock_.end() || t <= 0) return 0.0;
    const double got = std::min(t, it->second);
    it->second -= got;
    return got;
}

json::Value Colony::to_json() const {
    json::Value v = json::Value::object();
    v.set("id", id_);
    v.set("body", body_);
    v.set("solar_flux", solar_flux_);
    v.set("co2", co2_atmosphere_);
    v.set("next_id", next_id_);
    json::Value st = json::Value::object();
    for (const auto& [k, q] : stock_) st.set(k, q);
    v.set("stock", st);
    json::Value mods = json::Value::array();
    for (const auto& m : modules_) {
        json::Value o = json::Value::object();
        o.set("type", static_cast<int>(m.type));
        o.set("condition", m.condition);
        mods.push(o);
    }
    v.set("modules", mods);
    json::Value cols = json::Value::array();
    for (const auto& c : colonists_) {
        json::Value o = json::Value::object();
        o.set("id", c.id);
        o.set("name", c.name);
        o.set("job", static_cast<int>(c.job));
        o.set("skill", c.skill);
        o.set("alive", c.alive);
        o.set("hours", c.hours_worked);
        o.set("act", static_cast<int>(c.activity));
        o.set("left", c.activity_hours_left);
        o.set("hunger", c.needs.hunger);
        o.set("fatigue", c.needs.fatigue);
        o.set("morale", c.needs.morale);
        o.set("health", c.needs.health);
        o.set("dose", c.dose_msv);
        o.set("dose_limit", c.dose_limit_reached);
        o.set("ordered", c.ordered);
        const Personality& p = c.personality;
        json::Value pj = json::Value::array();
        for (double x : {p.courage, p.curiosity, p.patience, p.diligence, p.sociability, p.leadership, p.competitiveness, p.helpfulness, p.caution})
            pj.push(x);
        o.set("pers", pj);
        cols.push(o);
    }
    v.set("colonists", cols);
    json::Value lab = json::Value::object();
    for (const auto& [j, q] : labor_ema_) lab.set(std::to_string(static_cast<int>(j)), q);
    v.set("labor", lab);
    return v;
}

Result<Colony> Colony::from_json(const json::Value& v) {
    if (!v.is_object() || !v.has("id")) return make_error(ErrorCode::Parse, "Koloni kaydı bozuk");
    Colony c(v["id"].as_string(), v["body"].as_string(), 149.6, v["co2"].as_bool());
    c.solar_flux_ = v["solar_flux"].as_number(kSolarConstant);
    c.next_id_ = v["next_id"].as_int(1);
    for (const auto& [k, q] : v["stock"].as_object()) c.stock_[k] = q.as_number();
    for (const auto& m : v["modules"].as_array()) {
        const int t = m["type"].as_int(-1);
        if (t < 0 || t > static_cast<int>(ModuleType::WaterRecycler)) return make_error(ErrorCode::Parse, "Geçersiz modül türü");
        c.modules_.push_back({static_cast<ModuleType>(t), m["condition"].as_number(1.0), 0.0});
    }
    for (const auto& o : v["colonists"].as_array()) {
        Colonist k;
        k.id = o["id"].as_int();
        k.name = o["name"].as_string();
        const int j = o["job"].as_int(-1);
        const int a = o["act"].as_int(0);
        if (j < 0 || j > static_cast<int>(Job::Security) || a < 0 || a > static_cast<int>(Activity::Treatment))
            return make_error(ErrorCode::Parse, "Geçersiz kolonist kaydı");
        k.job = static_cast<Job>(j);
        k.activity = static_cast<Activity>(a);
        k.skill = o["skill"].as_number(0.5);
        k.alive = o["alive"].as_bool(true);
        k.hours_worked = o["hours"].as_number();
        k.activity_hours_left = o["left"].as_number();
        k.needs.hunger = o["hunger"].as_number();
        k.needs.fatigue = o["fatigue"].as_number();
        k.needs.morale = o["morale"].as_number(0.7);
        k.needs.health = o["health"].as_number(1.0);
        k.dose_msv = o["dose"].as_number();
        k.dose_limit_reached = o["dose_limit"].as_bool(false);
        k.ordered = o["ordered"].as_bool(false);
        const auto& pa = o["pers"].as_array();
        if (pa.size() == 9) {
            double* f[] = {&k.personality.courage, &k.personality.curiosity, &k.personality.patience, &k.personality.diligence,
                           &k.personality.sociability, &k.personality.leadership, &k.personality.competitiveness,
                           &k.personality.helpfulness, &k.personality.caution};
            for (std::size_t i = 0; i < 9; ++i) *f[i] = std::clamp(pa[i].as_number(0.5), 0.0, 1.0);
        }
        c.colonists_.push_back(k);
    }
    for (const auto& [j, q] : v["labor"].as_object()) {
        const long jj = std::strtol(j.c_str(), nullptr, 10);            // istisnasız ayrıştırma
        if (jj < 0 || jj > static_cast<long>(Job::Pilot)) return make_error(ErrorCode::Parse, "Geçersiz iş gücü kaydı");
        c.labor_ema_[static_cast<Job>(jj)] = q.as_number();
    }
    return c;
}

}  // namespace kozmo::colony

namespace kozmo::colony {

void Colony::add_dose(int id, double msv) {
    for (auto& c : colonists_)
        if (c.id == id) {
            c.dose_msv += msv;
            if (c.dose_msv >= env::kCareerLimitMsv) c.dose_limit_reached = true;
        }
}

void Colony::damage_random_module(double amount, Rng& rng, EventBus* bus) {
    if (modules_.empty()) return;
    Module& m = modules_[static_cast<std::size_t>(rng.range(0, static_cast<int>(modules_.size()) - 1))];
    m.condition = std::max(0.2, m.condition - amount);
    KOZMO_LOG(Warn, "colony", id_ + ": " + module_name(m.type) + " hasar aldı");
    if (bus) bus->publish(ModuleDamaged{id_, module_name(m.type), m.condition});
}

}  // namespace kozmo::colony

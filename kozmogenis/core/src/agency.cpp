#include "kozmo/agency.hpp"

#include <algorithm>

namespace kozmo::agency {

const char* to_string(Facility f) { return spec(f).name.c_str(); }

const FacilitySpec& spec(Facility f) {
    using F = Facility;
    // ad, açıklama, başlangıç, en çok, yükseltme maliyeti, günlük gider, inşaat günü
    static const FacilitySpec s[kFacilityCount] = {
        {F::LaunchPads, "Fırlatma rampası", "A küçük, B orta, C dev roketler için; aynı anda hazırlanabilecek roket sayısı", 1, 3, {0, 0, 1500e3, 4000e3}, {0, 2e3, 5e3, 9e3}, {0, 0, 60, 120}},
        {F::Research, "Araştırma merkezi", "Araştırma süresini kısaltır", 0, 3, {0, 1000e3, 3000e3, 7000e3}, {0, 3e3, 6e3, 10e3}, {0, 30, 60, 90}},
        {F::AstronautCenter, "Astronot merkezi", "Astronot kapasitesi, eğitim hızı (simülatör, NBL havuzu)", 1, 3, {0, 0, 1200e3, 3000e3}, {0, 1e3, 3e3, 5e3}, {0, 0, 45, 90}},
        {F::Depot, "Depo", "Maden, yakıt ve yedek parça depolama", 1, 3, {0, 0, 800e3, 2000e3}, {0, 0.5e3, 1e3, 2e3}, {0, 0, 20, 40}},
        {F::MissionBoard, "Görev tahtası", "Aynı anda açık ticari sözleşme sayısı", 1, 3, {0, 0, 600e3, 1600e3}, {0, 0.2e3, 0.5e3, 1e3}, {0, 0, 10, 20}},
        {F::NovaCenter, "NOVA kontrol merkezi", "NOVA'nın yetenekleri: tavsiye, pencere/uyarı, otonom plan", 1, 3, {0, 2000e3, 5000e3, 10000e3}, {0, 2e3, 4e3, 8e3}, {0, 30, 60, 120}},
        {F::MissionControl, "Görev kontrol merkezi", "Eşzamanlı izlenebilen görev sayısı, canlı telemetri", 1, 3, {0, 0, 1000e3, 2500e3}, {0, 2e3, 4e3, 7e3}, {0, 0, 30, 60}},
        {F::FuelDepot, "Yakıt deposu", "Yerinde itici üretimi: fırlatma maliyetinde indirim", 1, 3, {0, 0, 900e3, 2200e3}, {0, 1e3, 2e3, 3e3}, {0, 0, 30, 60}},
        {F::Hangar, "Montaj hangarı", "Kalkış kütlesi ve kademe sayısı sınırı (Araç Montaj Binası ölçeği)", 1, 3, {0, 0, 1500e3, 4500e3}, {0, 1.5e3, 3e3, 6e3}, {0, 0, 90, 180}},
        {F::CommsTower, "İletişim kulesi", "Derin uzay anteni: iletişim menzili (Ay / Mars / dış gezegenler)", 1, 3, {0, 0, 1200e3, 3500e3}, {0, 1e3, 2e3, 4e3}, {0, 0, 45, 90}},
        {F::Medical, "Sağlık merkezi", "Astronot iyileşme hızı", 1, 3, {0, 0, 800e3, 2000e3}, {0, 1e3, 2e3, 3e3}, {0, 0, 30, 45}},
        {F::Recreation, "Dinlenme alanı", "Yorgunluk giderme; moral", 0, 3, {0, 600e3, 1500e3, 3000e3}, {0, 0.5e3, 1e3, 1.5e3}, {0, 20, 30, 45}},
    };
    return s[static_cast<int>(f)];
}

Base::Base() {
    for (int i = 0; i < kFacilityCount; ++i) levels_[static_cast<std::size_t>(i)] = spec(static_cast<Facility>(i)).start_level;
}

Capabilities Base::capabilities() const {
    auto L = [&](Facility f) { return level(f); };
    Capabilities c{};
    c.pads = std::max(0, L(Facility::LaunchPads));
    // hangar + rampa: 1 -> Falcon 9 sınıfı (~600 t), 2 -> Falcon Heavy sınıfı (~1500 t), 3 -> süper ağır (~5500 t)
    const int lim = std::min(L(Facility::Hangar), L(Facility::LaunchPads));
    c.max_liftoff_t = lim >= 3 ? 6000 : (lim == 2 ? 1500 : (lim == 1 ? 650 : 0));
    c.max_stages = 1 + lim;
    c.concurrent_missions = 1 + 2 * L(Facility::MissionControl);
    c.research_speed = 1.0 + 0.35 * L(Facility::Research);
    c.astronaut_capacity = 4 * (1 + L(Facility::AstronautCenter));
    c.training_speed = 1.0 + 0.25 * L(Facility::AstronautCenter);
    c.depot_capacity_t = 50.0 * (1 + 2 * L(Facility::Depot));
    c.contract_slots = 1 + 2 * L(Facility::MissionBoard);
    c.nova_level = L(Facility::NovaCenter);
    // menzil: 1 -> Ay (384 400 km + pay), 2 -> Mars en uzak ~401 milyon km, 3 -> dış gezegenler ~1.5 milyar km
    const int cm = L(Facility::CommsTower);
    c.comms_range_km = cm >= 3 ? 1.6e9 : (cm == 2 ? 4.1e8 : (cm == 1 ? 5.0e5 : 4.0e4));
    c.fuel_discount = 0.1 * L(Facility::FuelDepot);
    c.medical_recovery = 0.02 * (1 + L(Facility::Medical));
    c.fatigue_recovery = 0.05 * (1 + L(Facility::Recreation));
    return c;
}

Status Base::upgrade(Facility f, econ::Wallet& w, double day) {
    const FacilitySpec& s = spec(f);
    int target = level(f) + 1;
    for (const auto& p : pending_) {
        if (p.facility == f) return make_error(ErrorCode::Infeasible, s.name + " zaten yükseltiliyor");
    }
    if (target > s.max_level) return make_error(ErrorCode::Infeasible, s.name + " en yüksek seviyede");
    if (pending_.size() >= 2) return make_error(ErrorCode::Infeasible, "Aynı anda en çok 2 inşaat yürütülebilir");
    const double cost = s.upgrade_cost[static_cast<std::size_t>(target)];
    if (w.balance() < cost) return make_error(ErrorCode::InsufficientFunds, s.name + " için " + std::to_string(static_cast<long long>(cost)) + " kredi gerekli");
    auto st = w.spend(cost, s.name + " seviye " + std::to_string(target), day);
    if (!st) return st;
    pending_.push_back({f, target, day + s.build_days[static_cast<std::size_t>(target)]});
    return ok_status();
}

std::vector<std::string> Base::advance(double day, econ::Wallet& w) {
    std::vector<std::string> msg;
    for (auto it = pending_.begin(); it != pending_.end();) {
        if (day >= it->done_day) {
            levels_[static_cast<std::size_t>(it->facility)] = it->to_level;
            msg.push_back(spec(it->facility).name + " seviye " + std::to_string(it->to_level) + " tamamlandı");
            it = pending_.erase(it);
        } else {
            ++it;
        }
    }
    const double dd = day - last_day_;
    if (dd > 0) {
        const double cost = upkeep_per_day() * dd;
        if (!w.spend(cost, "Üs giderleri", day)) msg.push_back("UYARI: üs giderleri ödenemedi (bakiye yetersiz)");
        last_day_ = day;
    }
    return msg;
}

double Base::upkeep_per_day() const {
    double s = 0;
    for (int i = 0; i < kFacilityCount; ++i) s += spec(static_cast<Facility>(i)).upkeep_per_day[static_cast<std::size_t>(levels_[static_cast<std::size_t>(i)])];
    return s;
}

bool Base::max_base() const {
    for (int i = 0; i < kFacilityCount; ++i)
        if (levels_[static_cast<std::size_t>(i)] < spec(static_cast<Facility>(i)).max_level) return false;
    return true;
}

json::Value Base::to_json() const {
    json::Value v = json::Value::object();
    json::Value l = json::Value::array();
    for (int x : levels_) l.push(x);
    v.set("levels", l);
    json::Value p = json::Value::array();
    for (const auto& u : pending_) {
        json::Value o = json::Value::object();
        o.set("f", static_cast<int>(u.facility));
        o.set("to", u.to_level);
        o.set("done", u.done_day);
        p.push(o);
    }
    v.set("pending", p);
    v.set("last", last_day_);
    return v;
}

Status Base::from_json(const json::Value& v) {
    const auto& l = v["levels"].as_array();
    if (l.size() != kFacilityCount) return make_error(ErrorCode::Parse, "Bozuk üs kaydı");
    for (std::size_t i = 0; i < kFacilityCount; ++i) levels_[i] = std::clamp(l[i].as_int(), 0, spec(static_cast<Facility>(i)).max_level);
    pending_.clear();
    for (const auto& o : v["pending"].as_array()) {
        const int f = o["f"].as_int(-1);
        if (f < 0 || f >= kFacilityCount) return make_error(ErrorCode::Parse, "Bozuk yükseltme kaydı");
        pending_.push_back({static_cast<Facility>(f), o["to"].as_int(), o["done"].as_number()});
    }
    last_day_ = v["last"].as_number();
    return ok_status();
}

}  // namespace kozmo::agency

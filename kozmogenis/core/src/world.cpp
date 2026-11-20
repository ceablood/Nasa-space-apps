#include "kozmo/world.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace kozmo::world {

namespace {
std::string f1(double v) {
    char b[32];
    std::snprintf(b, sizeof(b), "%.1f", v);
    return b;
}
std::string f0(double v) {
    char b[32];
    std::snprintf(b, sizeof(b), "%.0f", v);
    return b;
}
}  // namespace

const char* to_string(PlayerMode m) {
    switch (m) {
        case PlayerMode::Seated: return "Kokpitte oturuyor";
        case PlayerMode::InCabin: return "Kabinde";
        case PlayerMode::OnFoot: return "Yüzeyde yürüyor";
        case PlayerMode::InBuilding: return "Bina içinde";
    }
    return "?";
}

Result<DescentStart> descent_start(const std::string& body) {
    if (body == "moon") return DescentStart{15000, 1650, 0, "Apollo motorlu iniş başlangıcı (PDI) ~15 km, ~1.65 km/s"};
    if (body == "mars") return DescentStart{10000, 400, -150, "Atmosfer girişi ve paraşüt sonrası (mühendislik yaklaşımı)"};
    if (body == "mercury") return DescentStart{15000, 2900, 0, "Alçak yörüngeden motorlu iniş (yaklaşım)"};
    return make_error(ErrorCode::NotFound, "Bu gök cismi için iniş senaryosu yok: " + body);
}

Expedition::Expedition(Game& g, std::string body, craft::Spacecraft c, std::uint64_t seed)
    : game_(g), body_(std::move(body)), craft_(std::move(c)), rng_(seed) {
    player_.eq.pressure_suit = true;
    player_.eq.dust_filters = true;
}

colony::Colony* Expedition::colony() { return game_.colony(body_ + "_koloni"); }
const colony::Colony* Expedition::colony() const {
    auto it = game_.colonies().find(body_ + "_koloni");
    return it == game_.colonies().end() ? nullptr : &it->second;
}

Status Expedition::init(bool in_orbit) {
    in_orbit_ = in_orbit;
    auto e = challenge::body_environment(body_);
    if (!e) return e.error();
    env_ = e.value();
    if (colony::Colony* c = colony()) {
        settlement_ = life::Settlement::build(*c, env_);
        society_.sync(*c, settlement_, rng_);
        game_.set_focus(c->id());
    }
    craft_.place_landed();   // yörüngedeyken araç durumu: in_orbit_ (iniş başlatılana kadar)
    if (const life::Building* pad = settlement_.find(life::District::LandingPad)) {
        player_.x = pad->x;
        player_.y = pad->y;
    }
    push(env_.name + " seferi hazır: " + craft_.model() + " (" + craft::to_string(craft_.craft_class()) + ")");
    return ok_status();
}

challenge::Equipment Expedition::equipment() const {
    challenge::Equipment q = player_.eq;
    for (const auto& p : craft_.installed()) {
        auto s = craft::find_part(p.key);
        if (!s) continue;
        if (s.value()->kind == craft::PartKind::HeatShield && p.health > 0.3) q.heat_shield = true;
        if (s.value()->kind == craft::PartKind::Radar && p.health > 0.3) q.landing_radar = true;
        if (s.value()->kind == craft::PartKind::RoboticArm) q.remote_probe = true;
    }
    if (const colony::Colony* c = colony()) {
        for (const auto& m : c->modules()) {
            if (m.type == colony::ModuleType::Habitat) q.heated_habitat = true;
            if (m.type == colony::ModuleType::Mine) q.water_extractor = true;
        }
        if (settlement_.layout() == life::Layout::Underground) q.shielding_gcm2 = std::max(q.shielding_gcm2, 50.0);   // ~30 cm regolit
    }
    return q;
}

void Expedition::push(const std::string& s) {
    log_.push_back("[" + f1(hours_) + " sa] " + s);
    if (log_.size() > 200) log_.erase(log_.begin(), log_.begin() + 50);
}

Status Expedition::sit() {
    if (player_.mode != PlayerMode::InCabin) return make_error(ErrorCode::Infeasible, "Kokpite oturmak için araç kabininde ol");
    auto st = craft_.sit();
    if (!st) return st;
    player_.mode = PlayerMode::Seated;
    return ok_status();
}

Status Expedition::stand() {
    if (player_.mode != PlayerMode::Seated) return make_error(ErrorCode::Infeasible, "Zaten ayaktasın");
    auto st = craft_.stand();
    if (!st) return st;
    player_.mode = PlayerMode::InCabin;
    return ok_status();
}

Status Expedition::begin_descent() {
    auto d = descent_start(body_);
    if (!d) return d.error();
    if (player_.mode != PlayerMode::Seated) return make_error(ErrorCode::Infeasible, "İniş için kokpitte otur");
    craft_.place_in_flight(d.value().altitude_m, d.value().horizontal_ms, d.value().vertical_ms);
    in_orbit_ = false;
    push("İniş başladı: " + d.value().note);
    return ok_status();
}

Status Expedition::exit_craft() {
    if (player_.mode == PlayerMode::Seated) return make_error(ErrorCode::Infeasible, "Önce koltuktan kalk");
    if (player_.mode != PlayerMode::InCabin) return make_error(ErrorCode::Infeasible, "Araçta değilsin");
    if (in_orbit_) return make_error(ErrorCode::Infeasible, "Araç yörüngede: önce iniş yap");
    if (!craft_.can_exit(env_, player_.eq.pressure_suit))
        return make_error(ErrorCode::Infeasible, craft_.phase() != craft::FlightPhase::Landed ? "Araç inmeden çıkılamaz" : "Dış ortam için basınçlı giysi gerekli");
    player_.mode = PlayerMode::OnFoot;
    if (const life::Building* pad = settlement_.find(life::District::LandingPad)) {
        player_.x = pad->x;
        player_.y = pad->y;
    }
    push("Araçtan çıkıldı: " + env_.name + " yüzeyi");
    return ok_status();
}

Status Expedition::enter_craft() {
    if (player_.mode != PlayerMode::OnFoot) return make_error(ErrorCode::Infeasible, "Araca dışarıdan binilir");
    const life::Building* pad = settlement_.find(life::District::LandingPad);
    if (pad && std::hypot(player_.x - pad->x, player_.y - pad->y) > 25) return make_error(ErrorCode::Infeasible, "Araç çok uzakta (iniş alanına yürü)");
    player_.mode = PlayerMode::InCabin;
    player_.route.clear();
    return ok_status();
}

Status Expedition::walk_to(const std::string& id) {
    if (player_.mode != PlayerMode::OnFoot && player_.mode != PlayerMode::InBuilding) return make_error(ErrorCode::Infeasible, "Yürümek için araçtan çık");
    const life::Building* b = settlement_.find(id);
    if (!b) return make_error(ErrorCode::NotFound, "Bina yok: " + id);
    if (player_.mode == PlayerMode::InBuilding) {
        auto st = leave_building();
        if (!st) return st;
    }
    player_.route = settlement_.path(player_.x, player_.y, *b);
    if (!player_.route.empty()) player_.route.pop_back();   // kapıda dur (içeri girmek ayrı eylem)
    return ok_status();
}

void Expedition::set_player_position(double x, double y) {
    if (player_.mode != PlayerMode::OnFoot && player_.mode != PlayerMode::InBuilding) return;
    player_.x = x;
    player_.y = y;
    player_.route.clear();
}

Status Expedition::enter_building(const std::string& id) {
    const life::Building* b = settlement_.find(id);
    if (!b) return make_error(ErrorCode::NotFound, "Bina yok: " + id);
    if (player_.mode != PlayerMode::OnFoot) return make_error(ErrorCode::Infeasible, "Binaya yürüyerek girilir");
    if (std::hypot(player_.x - b->door_x, player_.y - b->door_y) > 6) return make_error(ErrorCode::Infeasible, "Kapıya yürü (" + b->name + ")");
    player_.mode = PlayerMode::InBuilding;
    player_.building = b->id;
    player_.x = b->x;
    player_.y = b->y;
    player_.route.clear();
    push(b->name + " içine girildi" + std::string(b->pressurized ? " (hava kilidi, basınçlı)" : ""));
    return ok_status();
}

Status Expedition::leave_building() {
    if (player_.mode != PlayerMode::InBuilding) return make_error(ErrorCode::Infeasible, "Bina içinde değilsin");
    const life::Building* b = settlement_.find(player_.building);
    if (b) {
        player_.x = b->door_x;
        player_.y = b->door_y;
    }
    player_.mode = PlayerMode::OnFoot;
    player_.building.clear();
    return ok_status();
}

Status Expedition::collect_sample() {
    if (player_.mode != PlayerMode::OnFoot) return make_error(ErrorCode::Infeasible, "Numune dışarıda toplanır");
    ++player_.samples;
    push(env_.name + " yüzeyinden numune toplandı (" + std::to_string(player_.samples) + ")");
    return ok_status();
}

std::vector<int> Expedition::npcs_here() const {
    std::vector<int> out;
    for (const auto& n : society_.npcs()) {
        const bool same = player_.mode == PlayerMode::InBuilding && n.arrived && n.at == player_.building;
        if (same || std::hypot(n.x - player_.x, n.y - player_.y) < 10) out.push_back(n.id);
    }
    return out;
}

Result<std::string> Expedition::talk(int id, const std::string& topic) {
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Burada koloni yok");
    auto here = npcs_here();
    if (std::find(here.begin(), here.end(), id) == here.end()) return make_error(ErrorCode::Infeasible, "Konuşmak için yanına git");
    return society_.talk(id, topic, game_.day(), *c);
}

Result<std::string> Expedition::use(const std::string& item) {
    if (player_.mode != PlayerMode::InBuilding) return make_error(ErrorCode::Infeasible, "Konsollar bina içindedir");
    const life::Building* b = settlement_.find(player_.building);
    const life::Interactable* it = nullptr;
    for (const auto& r : b->rooms)
        for (const auto& x : r.items)
            if (x.id == item) it = &x;
    if (!it) return make_error(ErrorCode::NotFound, "Bu binada böyle bir konsol yok: " + item);
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Koloni yok");
    const std::string& a = it->action;
    if (a == "map") {
        std::string s = "Yerleşim: " + std::string(life::to_string(settlement_.layout())) + ", " + std::to_string(settlement_.buildings().size()) + " bölge:";
        for (const auto& x : settlement_.buildings()) s += "\n- " + x.id + " " + x.name;
        return s;
    }
    if (a == "population") {
        std::map<std::string, int> jobs;
        for (const auto& k : c->colonists())
            if (k.alive) jobs[colony::job_name(k.job)]++;
        std::string s = "Nüfus " + std::to_string(c->population()) + " / yatak " + std::to_string(c->housing()) + ", ortalama moral %" + f0(c->average_morale() * 100);
        for (const auto& [j, n] : jobs) s += "\n- " + j + ": " + std::to_string(n);
        return s;
    }
    if (a == "economy" || a == "inventory" || a == "food" || a == "water") return colony_report();
    if (a == "security" || a == "alarm") {
        if (a == "alarm") {
            society_.raise(society_.alarm() ? life::ColonyEvent::AllClear : life::ColonyEvent::Alarm, game_.day(), *c, settlement_);
            push(society_.alarm() ? "Koloni alarmı oyuncu tarafından başlatıldı" : "Alarm kapatıldı");
        }
        auto iss = society_.issues(*c);
        std::string s = std::string("Alarm: ") + (society_.alarm() ? to_string(society_.last_event()) : "yok");
        for (const auto& x : iss) s += "\n- " + x;
        return s;
    }
    if (a == "missions") {
        std::string s = "Görevler:";
        for (const auto& t : tasks()) s += "\n- " + t;
        return s;
    }
    if (a == "nova") return std::string("NOVA terminali hazır. Sorabilirsin: 'koloninin durumu nasıl?', 'neden üretim yavaşladı?', 'gezegen riski ne?'.");
    if (a == "power") {
        if (c->module_condition(colony::ModuleType::SolarArray) < 0.8) {
            for (int i = 0; i < 8; ++i) c->repair(colony::ModuleType::SolarArray, 0.35);
            push("Oyuncu enerji tesisindeki arızayı giderdi");
            update_events();
            return std::string("Arıza giderildi: güneş dizileri %" + f0(c->module_condition(colony::ModuleType::SolarArray) * 100) + " durumda.");
        }
        return std::string("Enerji sistemi normal: dizi durumu %" + f0(c->module_condition(colony::ModuleType::SolarArray) * 100));
    }
    if (a == "analyze" || a == "experiment") {
        if (player_.samples <= 0) return std::string("Analiz edilecek numune yok. Dışarıdan numune topla.");
        --player_.samples;
        c->add_resource("rp", 25.0);
        society_.raise(life::ColonyEvent::Discovery, game_.day(), *c, settlement_);
        push("Numune analiz edildi: +25 araştırma puanı, bilim ekibi laboratuvara çağrıldı");
        return std::string("Numune " + env_.name + " kökenli: analiz tamam, +25 araştırma puanı. Bilim insanları incelemeye geliyor.");
    }
    if (a == "samples") return std::string("Numune dolabı: oyuncuda " + std::to_string(player_.samples) + " numune");
    if (a == "research") return std::string("Laboratuvar araştırma puanı stoku: " + f0(c->resource("rp")));
    if (a == "treat" || a == "exam" || a == "medkit") {
        const double before = player_.body.health;
        player_.body.health = std::min(1.0, player_.body.health + (a == "treat" ? 0.4 : 0.1));
        return std::string("Sağlık %" + f0(before * 100) + " -> %" + f0(player_.body.health * 100) + ", birikmiş doz " + f1(player_.body.dose_msv) + " mSv");
    }
    if (a == "rest") return std::string("Dinlendin. (Oyuncu yorgunluğu bu dilimde modellenmiyor.)");
    if (a == "machines" || a == "arms" || a == "qc" || a == "farm") {
        std::string s = "Tesis verimleri:";
        for (const auto& m : c->modules()) s += "\n- " + std::string(colony::module_name(m.type)) + ": verim %" + f0(m.efficiency * 100) + ", durum %" + f0(m.condition * 100);
        return s;
    }
    if (a == "locker") return std::string("Kişisel depo: giysi oksijeni yenilendi.");
    return std::string(it->name + ": hazır.");
}

void Expedition::fail_power() {
    if (colony::Colony* c = colony()) {
        c->damage_module(colony::ModuleType::SolarArray, 0.7);
        push("Enerji tesisi arızalandı!");
        update_events();
    }
}

void Expedition::evacuate() {
    colony::Colony* c = colony();
    if (!c) return;
    society_.raise(life::ColonyEvent::Alarm, game_.day(), *c, settlement_);
    push("Tahliye emri: siviller sığınaklara");
}

double Expedition::local_hour() const { return game_.local_hour(body_); }
double Expedition::crew_hour() const { return game_.crew_hour(body_); }

void Expedition::update_events() {
    colony::Colony* c = colony();
    if (!c) return;
    const double cond = c->module_condition(colony::ModuleType::SolarArray);
    if (!power_alarm_ && cond < 0.5) {
        power_alarm_ = true;
        society_.raise(life::ColonyEvent::PowerOutage, game_.day(), *c, settlement_);
        push("Enerji kesintisi alarmı: mühendisler enerji merkezine");
    } else if (power_alarm_ && cond >= 0.8) {
        power_alarm_ = false;
        society_.raise(life::ColonyEvent::AllClear, game_.day(), *c, settlement_);
        push("Enerji normale döndü");
    }
}

void Expedition::move_player(double dt_s) {
    double budget = life::walking_speed_ms(env_.gravity_ms2) * dt_s;
    while (budget > 0 && !player_.route.empty()) {
        const auto [tx, ty] = player_.route.front();
        const double d = std::hypot(tx - player_.x, ty - player_.y);
        if (d <= budget) {
            player_.x = tx;
            player_.y = ty;
            budget -= d;
            player_.route.erase(player_.route.begin());
        } else {
            player_.x += (tx - player_.x) / d * budget;
            player_.y += (ty - player_.y) / d * budget;
            budget = 0;
        }
    }
}

void Expedition::tick(double dt_s) {
    if (dt_s <= 0) return;
    const double dt_h = dt_s / 3600.0;
    hours_ += dt_h;
    // araç uçuşu (0.1 s alt adım)
    if (craft_.phase() == craft::FlightPhase::Flying) {
        const auto before = craft_.phase();
        for (double t = 0; t < dt_s; t += 0.1) craft_.step(std::min(0.1, dt_s - t), env_, rng_);
        if (before != craft_.phase()) {
            if (craft_.phase() == craft::FlightPhase::Landed) push("İniş tamam: temas hızı " + f1(craft_.touchdown_speed()) + " m/s");
            else push("ARAÇ YÜZEYE ÇARPTI (" + f0(craft_.touchdown_speed()) + " m/s)");
        }
    }
    if (player_.mode == PlayerMode::Seated || player_.mode == PlayerMode::InCabin) craft_.tick_life_support(dt_h);
    move_player(dt_s);
    // gezegen hava olayları (parametrelere bağlı)
    weather_acc_ += dt_h;
    colony::Colony* c = colony();
    if (weather_acc_ >= 1.0) {
        for (auto& w : challenge::roll_weather(env_, hours_, weather_acc_, rng_)) {
            push(std::string("Hava olayı: ") + challenge::to_string(w.kind));
            if (c && (w.kind == challenge::Weather::DustStorm || w.kind == challenge::Weather::MeteorShower))
                society_.raise(w.kind == challenge::Weather::DustStorm ? life::ColonyEvent::DustStorm : life::ColonyEvent::MeteorThreat, game_.day(), *c, settlement_);
            weather_.push_back(w);
        }
        weather_acc_ = 0;
    }
    const bool storm_before = std::any_of(weather_.begin(), weather_.end(), [](const auto& w) {
        return w.kind == challenge::Weather::DustStorm || w.kind == challenge::Weather::MeteorShower;
    });
    weather_.erase(std::remove_if(weather_.begin(), weather_.end(), [&](const auto& w) { return w.end_h <= hours_; }), weather_.end());
    const bool storm_after = std::any_of(weather_.begin(), weather_.end(), [](const auto& w) {
        return w.kind == challenge::Weather::DustStorm || w.kind == challenge::Weather::MeteorShower;
    });
    if (c && storm_before && !storm_after && !power_alarm_) {
        society_.raise(life::ColonyEvent::AllClear, game_.day(), *c, settlement_);
        push("Fırtına geçti");
    }
    // oyuncunun hayatta kalması
    const bool outdoors = player_.mode == PlayerMode::OnFoot;
    challenge::Equipment eq = equipment();
    const bool in_craft = player_.mode == PlayerMode::Seated || player_.mode == PlayerMode::InCabin;
    if (in_craft && craft_.cabin_pressure() > 60.0 && craft_.instruments().power_kw_net > -50.0) eq.heated_habitat = true;   // ısıtmalı kabin
    auto tick = challenge::survive(env_, eq, outdoors, dt_h, weather_, local_hour(), player_.body);
    if (!player_.body.alive) push("Oyuncu hayatını kaybetti: " + player_.body.last_cause);
    if (!outdoors && player_.body.suit_o2_h < 8.0) player_.body.suit_o2_h = std::min(8.0, player_.body.suit_o2_h + dt_h * 4.0);   // basınçlı alanda şarj
    (void)tick;
    // koloni ekonomisi: tam oyun saatlerinde Game ilerler (odak koloni saatlik tam simülasyon)
    if (c) {
        const double px = player_.mode == PlayerMode::Seated || player_.mode == PlayerMode::InCabin ? 1e6 : player_.x;
        const double py = player_.mode == PlayerMode::Seated || player_.mode == PlayerMode::InCabin ? 1e6 : player_.y;
        society_.tick(dt_h, game_.day(), crew_hour(), *c, settlement_, env_.gravity_ms2, px, py, rng_);
    }
    hour_acc_ += dt_h;
    if (hour_acc_ >= 1.0) {
        game_.advance(hour_acc_ / 24.0);
        hour_acc_ = 0;
        if ((c = colony())) {
            society_.sync(*c, settlement_, rng_);
            update_events();
        }
    }
}

std::string Expedition::colony_report() const {
    const colony::Colony* c = colony();
    if (!c) return "Bu gök cisminde koloni yok.";
    const int pop = std::max(1, c->population());
    auto days = [&](const char* k, double per) { return f1(c->resource(k) / (pop * per)); };
    int sick = 0;
    for (const auto& k : c->colonists())
        if (k.alive && k.needs.health < 0.5) ++sick;
    double eff = 0;
    for (const auto& m : c->modules()) eff += m.efficiency;
    eff = c->modules().empty() ? 0 : eff / static_cast<double>(c->modules().size());
    std::string s = c->id() + ": nüfus " + std::to_string(c->population()) + ", enerji (güneş dizisi durumu) %" +
                    f0(c->module_condition(colony::ModuleType::SolarArray) * 100) + ", su " + days("water", colony::kWaterPerPersonDay_t) +
                    " gün, gıda " + days("food", colony::kFoodPerPersonDay_t) + " gün, oksijen " + days("oxygen", colony::kO2PerPersonDay_t) +
                    " gün, hasta " + std::to_string(sick) + ", ortalama üretim verimi %" + f0(eff * 100);
    if (society_.alarm()) s += ", ALARM: " + std::string(life::to_string(society_.last_event()));
    return s;
}

std::string Expedition::environment_report() const {
    const auto p = profile();
    std::string s = env_.name + " (" + challenge::to_string(env_.cls) + "): genel zorluk ekipmansız %" + f0(p.overall_raw * 100) +
                    ", mevcut ekipmanla %" + f0(p.overall * 100) + ". Yerel saat " + f1(local_hour()) + ", yüzey " +
                    f0(challenge::surface_temp_c(env_, local_hour())) + " °C. Radyasyon: " + f1(env_.dose_msv_day) + " mSv/gün (" + env_.dose_source + ").";
    for (int i = 0; i < challenge::kCategoryCount; ++i) {
        const auto& sc = p.scores[i];
        if (sc.mitigated >= 0.3) s += "\n- " + std::string(challenge::to_string(static_cast<challenge::Category>(i))) + " %" + f0(sc.mitigated * 100) + ": " + sc.reason;
        if (!sc.missing.empty() && sc.raw >= 0.3) s += " (eksik: " + sc.missing.front() + ")";
    }
    for (const auto& w : weather_) s += "\n- Etkin: " + std::string(challenge::to_string(w.kind)) + ", görüş %" + f0(w.visibility * 100);
    return s;
}

std::string Expedition::vehicle_report() const {
    const auto in = craft_.instruments();
    const auto sp = craft_.specs();
    std::string s = craft_.model() + ": yakıt " + f1(in.fuel_t) + " t (%" + f0(in.fuel_fraction * 100) + "), delta-v " + f0(sp.dv_ms) +
                    " m/s, gövde %" + f0(in.hull_fraction * 100) + ", motor %" + f0(in.engine_fraction * 100) + ", O2 " + f1(in.oxygen_days) +
                    " gün, kabin " + f1(in.cabin_pressure_kpa) + " kPa, kokpit V" + std::to_string(static_cast<int>(craft_.cockpit()));
    for (const auto& w : craft_.warnings()) s += "\n! " + w.message + " -> " + w.procedure;
    return s;
}

std::vector<std::string> Expedition::tasks() const {
    std::vector<std::string> t;
    const colony::Colony* c = colony();
    if (power_alarm_) t.push_back("ACİL: Enerji tesisine git ve kontrol panelinden arızayı gider");
    if (c) {
        for (const auto& f : life::diagnose_production(*c).suggestions) t.push_back(f);
        for (const auto& i : society_.issues(*c)) t.push_back("Ekip: " + i);
    }
    if (player_.samples > 0) t.push_back("Numuneleri laboratuvarda analiz et");
    if (!craft_.warnings().empty()) t.push_back("Araç uyarılarını gider");
    if (t.empty()) t.push_back("Yüzeyden numune topla ve laboratuvara getir");
    return t;
}

json::Value Expedition::to_json() const {
    json::Value v = json::Value::object();
    v.set("body", body_);
    v.set("craft", craft_.to_json());
    json::Value p = json::Value::object();
    p.set("mode", static_cast<int>(player_.mode));
    p.set("x", player_.x);
    p.set("y", player_.y);
    p.set("building", player_.building);
    p.set("health", player_.body.health);
    p.set("o2", player_.body.suit_o2_h);
    p.set("dose", player_.body.dose_msv);
    p.set("samples", player_.samples);
    v.set("player", p);
    v.set("society", society_.to_json());
    v.set("hours", hours_);
    v.set("power_alarm", power_alarm_);
    return v;
}

Status Expedition::from_json(const json::Value& v) {
    if (v["body"].as_string() != body_) return make_error(ErrorCode::Parse, "Kayıt başka bir gök cismine ait");
    auto c = craft::Spacecraft::from_json(v["craft"]);
    if (!c) return c.error();
    craft_ = c.value();
    const auto& p = v["player"];
    const int m = p["mode"].as_int(-1);
    if (m < 0 || m > 3) return make_error(ErrorCode::Parse, "Geçersiz oyuncu durumu");
    player_.mode = static_cast<PlayerMode>(m);
    player_.x = p["x"].as_number();
    player_.y = p["y"].as_number();
    player_.building = p["building"].as_string();
    player_.body.health = p["health"].as_number(1.0);
    player_.body.suit_o2_h = p["o2"].as_number(8.0);
    player_.body.dose_msv = p["dose"].as_number();
    player_.samples = p["samples"].as_int();
    auto st = society_.from_json(v["society"]);
    if (!st) return st;
    hours_ = v["hours"].as_number();
    power_alarm_ = v["power_alarm"].as_bool();
    return ok_status();
}

}  // namespace kozmo::world

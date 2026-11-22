#include "kozmo/world.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>

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
    if (body == "mars") return DescentStart{125000, 3400, -100, "Yörüngeden atmosfer girişi (125 km, 3.4 km/s): şişme ısı kalkanı ile frenleme, ses altında motorlu iniş"};
    if (body == "mercury") return DescentStart{15000, 2900, 0, "Alçak yörüngeden motorlu iniş (yaklaşım)"};
    if (body == "titan") return DescentStart{8000, 2, -5, "Huygens benzeri paraşüt inişi sonrası (Huygens 2005: ~5 m/s ile yere değdi)"};
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
    if (in_orbit_) {
        auto d = descent_start(body_);
        craft_.place_in_orbit(env_, d ? d.value().altitude_m : 100000.0);   // gerçek yörünge fazı
    } else {
        craft_.place_landed();
    }
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
    if (env_.pressure_kpa > 0.3 && env_.key != "titan") {
        bool decel = false;
        for (const auto& p : craft_.installed()) decel |= craft::find_part(p.key).value()->kind == craft::PartKind::Decelerator;
        if (!decel)
            return make_error(ErrorCode::Infeasible, env_.name + " girişi için şişme yavaşlatıcı (HIAD) gerekli: bu aracın balistik katsayısı yüksek, "
                                                                "yörüngeden giriş motorla karşılanamaz (Ares Mars iniş aracını kullan)");
    }
    craft_.place_in_flight(d.value().altitude_m, d.value().horizontal_ms, d.value().vertical_ms);
    // iniş alanı hedefi: motorlu iniş başlangıcının zamanlaması (Apollo PDI gibi) nominal menzile göre seçilir;
    // güdüm sapmaları konum geri beslemesiyle düzeltir
    {
        craft::Spacecraft sim = craft_;
        (void)sim.set_engines(true);
        if (!sim.instruments().seated) (void)sim.sit();
        (void)sim.set_engines(true);
        (void)sim.set_mode(craft::FlightMode::LandingAssist);
        Rng r2(1);
        if (sim.fly_until_landed(env_, r2, 4000, 0.1) == craft::FlightPhase::Landed) craft_.set_landing_target(sim.downrange());
    }
    in_orbit_ = false;
    push("İniş başladı: " + d.value().note);
    return ok_status();
}

Status Expedition::exit_craft() {
    if (player_.mode == PlayerMode::Seated) return make_error(ErrorCode::Infeasible, "Önce koltuktan kalk");
    if (player_.mode != PlayerMode::InCabin) return make_error(ErrorCode::Infeasible, "Araçta değilsin");
    if (in_orbit_ || craft_.phase() == craft::FlightPhase::Orbit) return make_error(ErrorCode::Infeasible, "Araç yörüngede: önce iniş yap");
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
    quest_event(quest::Goal::ReturnToCraft);
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
    if (!b->built && b->district != life::District::LandingPad) return make_error(ErrorCode::Infeasible, b->name + " henüz inşa edilmedi (arsa)");
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
    if (!b->built) return make_error(ErrorCode::Infeasible, b->name + " henüz inşa edilmedi");
    if (std::hypot(player_.x - b->door_x, player_.y - b->door_y) > 6) return make_error(ErrorCode::Infeasible, "Kapıya yürü (" + b->name + ")");
    player_.mode = PlayerMode::InBuilding;
    player_.building = b->id;
    player_.floor = 0;
    player_.x = b->x;
    player_.y = b->y;
    player_.route.clear();
    push(b->name + " içine girildi" + std::string(b->pressurized ? " (hava kilidi, basınçlı)" : ""));
    quest_event(quest::Goal::EnterDistrict, static_cast<int>(b->district));
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

Result<std::string> Expedition::change_floor(int floor, bool use_elevator) {
    if (player_.mode != PlayerMode::InBuilding) return make_error(ErrorCode::Infeasible, "Bina içinde değilsin");
    const life::Building* b = settlement_.find(player_.building);
    if (!b || b->floors <= 1) return make_error(ErrorCode::Infeasible, "Bu bina tek katlı");
    if (floor < 0 || floor >= b->floors) return make_error(ErrorCode::InvalidArgument, "Bu binada " + std::to_string(b->floors) + " kat var");
    if (floor == player_.floor) return std::string("Zaten bu kattasın");
    const bool underground = settlement_.layout() == life::Layout::Underground;
    const std::string name = floor == 0 ? "zemin kat" : (underground ? "-" + std::to_string(floor) + ". kat" : std::to_string(floor) + ". kat");
    if (use_elevator && b->elevator) {
        const colony::Colony* c = colony();
        const bool powered = c && (c->module_condition(colony::ModuleType::SolarArray) > 0.3 || c->module_condition(colony::ModuleType::FissionReactor) > 0.3) &&
                             !(society_.alarm() && society_.last_event() == life::ColonyEvent::PowerOutage);
        if (!powered) return make_error(ErrorCode::Infeasible, "Asansör enerjisiz: merdiveni kullan");
        player_.floor = floor;
        return std::string("Asansörle " + name);
    }
    const int steps = std::abs(floor - player_.floor);
    player_.floor = floor;
    tick(20.0 * steps);   // merdiven: kat başına ~20 s
    return std::string("Merdivenle " + name + (b->elevator ? "" : " (bu binada asansör yok)"));
}

Status Expedition::collect_sample() {
    if (player_.mode != PlayerMode::OnFoot) return make_error(ErrorCode::Infeasible, "Numune dışarıda toplanır");
    ++player_.samples;
    quest_event(quest::Goal::CollectSamples);
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
    auto r = society_.talk(id, topic, game_.day(), *c);
    if (r)
        if (const colony::Colonist* k = c->colonist(id)) quest_event(quest::Goal::TalkToJob, static_cast<int>(k->job));
    return r;
}

Result<std::string> Expedition::use(const std::string& item) {
    if (player_.mode != PlayerMode::InBuilding) return make_error(ErrorCode::Infeasible, "Konsollar bina içindedir");
    const life::Building* b = settlement_.find(player_.building);
    const life::Interactable* it = nullptr;
    int item_floor = 0;
    for (const auto& r : b->rooms)
        for (const auto& x : r.items)
            if (x.id == item) {
                it = &x;
                item_floor = r.floor;
            }
    if (!it) return make_error(ErrorCode::NotFound, "Bu binada böyle bir konsol yok: " + item);
    if (item_floor != player_.floor)
        return make_error(ErrorCode::Infeasible, it->name + " " + (item_floor == 0 ? std::string("zemin katta") : std::to_string(item_floor) + ". katta") +
                                                     (b->elevator ? " (asansörü kullan)" : " (merdiveni kullan)"));
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Koloni yok");
    quest_event(quest::Goal::UseItem, 0, item);
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
            quest_event(quest::Goal::RepairPower);
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
        quest_event(quest::Goal::AnalyzeSample);
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

Status Expedition::take_off(double alt_m) {
    if (player_.mode != PlayerMode::Seated) return make_error(ErrorCode::Infeasible, "Kalkış için kokpitte otur");
    auto st = craft_.launch_to_orbit(alt_m);
    if (st) push("Kalkış: hedef " + f0(alt_m / 1000.0) + " km yörünge");
    return st;
}

Result<std::string> Expedition::scan_water() {
    const bool outside = player_.mode == PlayerMode::OnFoot;
    bool sensor = false;
    for (const auto& p : craft_.installed())
        if (craft::find_part(p.key).value()->kind == craft::PartKind::Sensor && p.health > 0.3) sensor = true;
    if (!outside && !(sensor && craft_.phase() == craft::FlightPhase::Landed))
        return make_error(ErrorCode::Infeasible, "Su taraması için yüzeyde ol ya da araç sensörünü (inişten sonra) kullan");
    if (env_.water_availability < 0.1) {
        push("Su taraması: kullanılabilir su bulunamadı");
        return std::string(env_.name + ": bu bölgede kullanılabilir su/buz yok (su erişimi %" + f0(env_.water_availability * 100) + ")");
    }
    water_found_ = true;
    // yeraltı buzu derinliği: su erişimi yüksekse sığ (oyun varsayımı; Mars'ta orta enlemlerde <1 m buz gözlendi — Phoenix 2008)
    const double depth = std::max(0.05, (1.0 - env_.water_availability) * 2.0 + rng_.uniform(0.0, 0.5));
    push("Su bulundu: ~" + f1(depth) + " m derinlikte buz");
    return std::string("Yeraltı buzu bulundu: ~" + f1(depth) + " m derinlikte (" + env_.notes + "). Koloni kurulabilir.");
}

Status Expedition::found_colony() {
    if (colony()) return make_error(ErrorCode::Infeasible, "Burada zaten koloni var");
    if (craft_.phase() != craft::FlightPhase::Landed) return make_error(ErrorCode::Infeasible, "Önce iniş yap");
    if (!water_found_) return make_error(ErrorCode::Infeasible, "Önce su kaynağı bul (su taraması)");
    auto st = game_.found_outpost(body_, founding_crew_kit());
    if (!st) return st;
    colony::Colony* c = colony();
    settlement_ = life::Settlement::build(*c, env_);
    society_.sync(*c, settlement_, rng_);
    game_.set_focus(c->id());
    if (const life::Building* pad = settlement_.find(life::District::LandingPad)) {   // araç iniş alanında; oyuncu yanında
        if (player_.mode == PlayerMode::OnFoot) {
            player_.x = pad->x;
            player_.y = pad->y;
        }
    }
    push(env_.name + " kolonisi kuruldu: 4 kişilik ekip iniş kampında, ilk habitat inşa edilmeli");
    return ok_status();
}

Result<int> Expedition::build(colony::ModuleType t) {
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Koloni yok");
    auto r = construction_.start(t, *c, game_.wallet(), game_.research().unlocked_list(), game_.day());
    if (r) push(std::string("İnşaat başladı: ") + colony::module_name(t) + " (" + f0(build::total(build::blueprint(t)).labor_h) + " emek-saat)");
    return r;
}

Result<int> Expedition::reinforce() {
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Koloni yok");
    auto r = construction_.start_reinforcement(*c, game_.wallet(), game_.day());
    if (r) push("Güçlendirme başladı: regolit setleri ve rüzgâr duvarları");
    return r;
}

void Expedition::update_construction(double dt_h) {
    colony::Colony* c = colony();
    if (!c) return;
    (void)dt_h;
    const build::Project* p = construction_.current();
    std::string site;
    if (p) {
        const life::District d = p->reinforce ? life::District::Housing : static_cast<life::District>(build::site_district(p->module));
        if (const life::Building* b = settlement_.find(d)) site = b->id;
    }
    society_.set_construction_site(site);
    construction_.work(society_.take_construction_labor());
    for (auto t : construction_.complete(*c, game_.research().unlocked_list())) {
        push(std::string("İnşaat tamamlandı: ") + colony::module_name(t));
        quest_event(quest::Goal::BuildModule, static_cast<int>(t));
        settlement_.refresh(*c);
    }
    for (const auto& q : construction_.projects())
        if (q.state == build::State::WaitingConnection && !q.missing.empty() && q.labor_done_h > 0 && static_cast<int>(hours_ * 10) % 240 == 0)
            push(std::string(colony::module_name(q.module)) + " bağlantı bekliyor: " + q.missing);
}

std::string Expedition::damage_report() const {
    std::string s = "Hasar raporu:";
    bool any = false;
    if (const colony::Colony* c = colony()) {
        std::map<std::string, std::pair<double, int>> agg;
        for (const auto& m : c->modules()) {
            auto& a = agg[colony::module_name(m.type)];
            a.first += m.condition;
            a.second++;
        }
        for (const auto& [n, a] : agg)
            if (a.first / a.second < 0.95) {
                s += "\n- " + n + ": durum %" + f0(a.first / a.second * 100);
                any = true;
            }
        s += std::string("\n- Fırtına koruması: ") + (construction_.reinforced() ? "var (hasar %70 azalır)" : "YOK");
    }
    for (const auto& p : craft_.installed())
        if (p.health < 0.95) {
            s += "\n- Araç " + craft::find_part(p.key).value()->name + ": %" + f0(p.health * 100);
            any = true;
        }
    for (const auto& w : craft_.warnings()) {
        s += "\n! " + w.message;
        any = true;
    }
    if (!any) s += "\n- Kayda değer hasar yok";
    return s;
}

Result<std::string> Expedition::analyze_onboard() {
    bool lab = false;
    for (const auto& p : craft_.installed())
        if (craft::find_part(p.key).value()->kind == craft::PartKind::Science && p.health > 0.3) lab = true;
    if (!lab) return make_error(ErrorCode::Infeasible, "Araçta bilimsel laboratuvar yok");
    if (player_.mode != PlayerMode::InCabin && player_.mode != PlayerMode::Seated) return make_error(ErrorCode::Infeasible, "Laboratuvar araç içinde");
    if (player_.samples <= 0) return make_error(ErrorCode::Infeasible, "Analiz edilecek numune yok");
    --player_.samples;
    game_.research().add_points(25.0, &game_.bus());
    push("Araç laboratuvarında numune analizi: +25 araştırma puanı");
    quest_event(quest::Goal::AnalyzeSample);
    return std::string(env_.name + " numunesi analiz edildi: +25 araştırma puanı (etkin araştırmaya eklendi).");
}

Result<life::MissionReport> Expedition::assign_mission(life::MissionKind k, colony::Job job, life::District where, int count, double hours,
                                                       const std::string& description) {
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Koloni yok");
    auto r = society_.assign({k, job, where, hours, description}, count, game_.day(), *c, settlement_);
    push(std::string("Görev: ") + description + " — kabul " + std::to_string(r.accepted.size()) + ", sorun " + std::to_string(r.problems.size()));
    return r;
}

void Expedition::quest_event(quest::Goal g, int arg, const std::string& item, int amount) {
    for (const auto& c : quests_.notify({g, arg, item, amount}, hours_)) {
        completed_.push_back(c);
        if (c.reward.credits > 0) game_.wallet().earn(c.reward.credits, "Görev ödülü: " + c.title, game_.day());
        if (c.reward.research > 0) game_.research().add_points(c.reward.research, &game_.bus());
        if (c.giver > 0 && c.reward.affinity != 0) {
            life::Relation& r = society_.relation(life::Society::kPlayer, c.giver);
            r.affinity = std::clamp(r.affinity + c.reward.affinity, -1.0, 1.0);
            if (life::Npc* n = society_.npc(c.giver)) society_.remember(*n, {game_.day(), life::Society::kPlayer, "Oyuncu verdiğim görevi bitirdi: " + c.title, 0.8, 0.9});
        }
        push("Görev tamamlandı: " + c.title + " (+" + f0(c.reward.credits) + " kredi)");
    }
}

Result<int> Expedition::accept_quest(const std::string& key, int giver) {
    auto r = quests_.offer(key, giver, hours_);
    if (r) push("Görev alındı: " + quests_.find(r.value())->title);
    return r;
}

Result<dialogue::Conversation> Expedition::converse(int npc) {
    colony::Colony* c = colony();
    if (!c) return make_error(ErrorCode::NotFound, "Burada koloni yok");
    auto here = npcs_here();
    if (std::find(here.begin(), here.end(), npc) == here.end()) return make_error(ErrorCode::Infeasible, "Konuşmak için yanına git");
    dialogue::Conversation conv(npc, society_, *c, quests_, game_.day(), hours_);
    if (!conv.active()) return make_error(ErrorCode::NotFound, "Bu kişiyle konuşulamıyor");
    if (const colony::Colonist* k = c->colonist(npc)) quest_event(quest::Goal::TalkToJob, static_cast<int>(k->job));
    return conv;
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
    if (craft_.phase() == craft::FlightPhase::Flying || (craft_.phase() == craft::FlightPhase::Landed && craft_.instruments().engines_on)) {
        const auto before = craft_.phase();
        for (double t = 0; t < dt_s; t += 0.1) craft_.step(std::min(0.1, dt_s - t), env_, rng_);
        if (craft_.docking().active) craft_.step_docking(dt_s);
        if (before != craft_.phase()) {
            if (craft_.phase() == craft::FlightPhase::Landed) push("İniş tamam: temas hızı " + f1(craft_.touchdown_speed()) + " m/s");
            else if (craft_.phase() == craft::FlightPhase::Orbit) {
                push("Yörüngeye girildi: " + f0(craft_.altitude() / 1000.0) + " km, " + f0(craft_.horizontal_speed()) + " m/s");
                quest_event(quest::Goal::ReachOrbit);
            }
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
    for (const auto& w : weather_)
        if (w.end_h <= hours_ && c && (w.kind == challenge::Weather::DustStorm || w.kind == challenge::Weather::StrongWind || w.kind == challenge::Weather::MeteorShower)) {
            // fırtına hasarı (oyun varsayımı): güneş dizileri tozdan/rüzgârdan en çok etkilenir; güçlendirme %70 azaltır
            const double k = w.intensity * construction_.storm_damage_factor() * std::min(1.0, (w.end_h - w.start_h) / 48.0);
            c->damage_module(colony::ModuleType::SolarArray, 0.25 * k);
            for (auto t : {colony::ModuleType::Habitat, colony::ModuleType::Greenhouse, colony::ModuleType::WaterRecycler})
                c->damage_module(t, 0.08 * k);
            push(std::string(challenge::to_string(w.kind)) + " hasarı: güneş dizileri -%" + f0(25 * k) + (construction_.reinforced() ? " (güçlendirme sayesinde azaldı)" : ""));
        }
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
    update_construction(dt_h);
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
    auto days = [&](const char* k, double per) {
        auto it = c->stock().find(k);
        if (it == c->stock().end()) return std::string("? (kayıt yok)");                    // eksik veri açıkça bildirilir
        if (!(it->second >= 0) || std::isnan(it->second)) return std::string("? (tutarsız veri)");
        return f1(it->second / (pop * per));
    };
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
    if (c->housing() < c->population()) s += ", konut yetersiz (" + std::to_string(c->housing()) + "/" + std::to_string(c->population()) + ")";
    if (const build::Project* p = construction_.current())
        s += std::string(", inşaat: ") + (p->reinforce ? "güçlendirme" : colony::module_name(p->module)) + " %" + f0(p->progress() * 100);
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
    if (env_.dose_source.find("tahmin") != std::string::npos)
        s += "\n- VERİ UYARISI: radyasyon değeri ölçüm değil, tahmindir (" + env_.dose_source + ")";
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
    for (const auto& q : quests_.quests())
        if (q.state == quest::State::Active) t.push_back("Görev: " + q.title + " (%" + f0(q.progress() * 100) + ")");
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
    p.set("floor", player_.floor);
    p.set("health", player_.body.health);
    p.set("o2", player_.body.suit_o2_h);
    p.set("dose", player_.body.dose_msv);
    p.set("samples", player_.samples);
    v.set("player", p);
    v.set("society", society_.to_json());
    v.set("hours", hours_);
    v.set("power_alarm", power_alarm_);
    v.set("water_found", water_found_);
    v.set("quests", quests_.to_json());
    v.set("construction", construction_.to_json());
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
    player_.floor = p["floor"].as_int();
    player_.body.health = p["health"].as_number(1.0);
    player_.body.suit_o2_h = p["o2"].as_number(8.0);
    player_.body.dose_msv = p["dose"].as_number();
    player_.samples = p["samples"].as_int();
    auto st = society_.from_json(v["society"]);
    if (!st) return st;
    hours_ = v["hours"].as_number();
    power_alarm_ = v["power_alarm"].as_bool();
    water_found_ = v["water_found"].as_bool();
    if (v.has("quests")) {
        auto qs = quests_.from_json(v["quests"]);
        if (!qs) return qs;
    }
    if (v.has("construction")) {
        auto cs = construction_.from_json(v["construction"]);
        if (!cs) return cs;
    }
    if (const colony::Colony* cc = colony()) settlement_.refresh(*cc);
    return ok_status();
}

}  // namespace kozmo::world

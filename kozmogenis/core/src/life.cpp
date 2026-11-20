#include "kozmo/life.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace kozmo::life {

namespace {
constexpr double kPi = 3.14159265358979323846;
std::string pct(double v) { return std::to_string(static_cast<int>(std::lround(v * 100))) + "%"; }
std::string f1(double v) {
    char b[32];
    std::snprintf(b, sizeof(b), "%.1f", v);
    return b;
}
bool has_module(const colony::Colony& c, colony::ModuleType t) {
    for (const auto& m : c.modules())
        if (m.type == t) return true;
    return false;
}
District workplace(colony::Job j) {
    using colony::Job;
    switch (j) {
        case Job::Farmer: return District::Farm;
        case Job::Engineer: return District::Production;
        case Job::Miner: return District::Processing;
        case Job::Scientist: return District::Lab;
        case Job::Medic: return District::Hospital;
        case Job::Pilot: return District::Hangar;
        case Job::Security: return District::Security;
    }
    return District::Production;
}
bool outdoor(District d) { return d == District::LandingPad || d == District::Airlock || d == District::Processing; }
}  // namespace

double walking_speed_ms(double g) { return std::sqrt(0.25 * std::max(0.1, g) * 0.9); }

const char* to_string(District d) {
    switch (d) {
        case District::LandingPad: return "İniş alanı";
        case District::Hangar: return "Araç hangarı";
        case District::Admin: return "Yönetim merkezi";
        case District::Housing: return "Yaşam alanı";
        case District::Canteen: return "Yemek salonu";
        case District::Hospital: return "Hastane";
        case District::Lab: return "Araştırma laboratuvarı";
        case District::Production: return "Üretim merkezi";
        case District::Processing: return "Maden işleme tesisi";
        case District::Power: return "Enerji tesisi";
        case District::Water: return "Su arıtma merkezi";
        case District::Farm: return "Gıda üretim alanı";
        case District::Storage: return "Depolar";
        case District::Robotics: return "Robotik bakım merkezi";
        case District::Training: return "Eğitim merkezi";
        case District::Social: return "Sosyal alan";
        case District::Security: return "Güvenlik merkezi";
        case District::Airlock: return "Dış keşif çıkışı (hava kilidi)";
    }
    return "?";
}

const char* to_string(Layout l) {
    switch (l) {
        case Layout::SurfaceDomes: return "Yüzey kubbeleri";
        case Layout::Underground: return "Yer altı (regolit kalkanlı)";
        case Layout::Ocean: return "Okyanus modülleri";
        case Layout::Polar: return "Kutup (ısıtmalı geçitler)";
        case Layout::Orbital: return "Yörünge istasyonu";
    }
    return "?";
}

const char* to_string(Intent i) {
    switch (i) {
        case Intent::Sleep: return "Uyuyor";
        case Intent::Eat: return "Yemek yiyor";
        case Intent::Work: return "Çalışıyor";
        case Intent::Socialize: return "Sohbet ediyor";
        case Intent::Treatment: return "Tedavide";
        case Intent::Idle: return "Dinleniyor";
        case Intent::Shelter: return "Sığınakta";
        case Intent::RespondAlarm: return "Alarma müdahale";
        case Intent::RepairPower: return "Enerji onarımı";
        case Intent::Patrol: return "Devriyede";
        case Intent::Research: return "Araştırmada";
        case Intent::TalkToPlayer: return "Seninle konuşuyor";
    }
    return "?";
}

const char* to_string(ColonyEvent e) {
    switch (e) {
        case ColonyEvent::Alarm: return "Koloni alarmı";
        case ColonyEvent::PowerOutage: return "Enerji kesintisi";
        case ColonyEvent::MeteorThreat: return "Meteor tehdidi";
        case ColonyEvent::Discovery: return "Yeni keşif";
        case ColonyEvent::DustStorm: return "Toz fırtınası";
        case ColonyEvent::AllClear: return "Tehlike geçti";
    }
    return "?";
}

// ---------------------------------------------------------------------------------------------
Settlement Settlement::build(const colony::Colony& c, const challenge::PlanetEnvironment& env) {
    Settlement s;
    using challenge::PlanetClass;
    switch (env.cls) {
        case PlanetClass::Airless: case PlanetClass::Radiation: s.layout_ = Layout::Underground; break;
        case PlanetClass::Ice: s.layout_ = Layout::Polar; break;
        case PlanetClass::Ocean: s.layout_ = Layout::Ocean; break;
        case PlanetClass::GasGiant: s.layout_ = Layout::Orbital; break;
        default: s.layout_ = Layout::SurfaceDomes; break;
    }
    const bool underground = s.layout_ == Layout::Underground;
    auto room = [](std::string n, std::vector<Interactable> it) { return Room{std::move(n), std::move(it)}; };
    for (int i = 0; i < kDistrictCount; ++i) {
        const District d = static_cast<District>(i);
        Building b;
        b.district = d;
        b.id = "b" + std::to_string(i);
        b.name = to_string(d);
        // meydan çevresinde halka; iniş alanı ve hava kilidi dışarıda
        const double ang = 2.0 * kPi * i / kDistrictCount;
        double r = 45.0;
        if (d == District::LandingPad) { r = 130.0; b.w = b.d = 40; b.h = 0.5; b.pressurized = false; }
        if (d == District::Airlock || d == District::Processing) r = 75.0;
        if (d == District::Processing) b.pressurized = false;
        b.x = r * std::cos(ang);
        b.y = r * std::sin(ang);
        // kapı meydana bakar
        const double half = std::max(b.w, b.d) / 2.0;
        b.door_x = b.x - std::cos(ang) * half;
        b.door_y = b.y - std::sin(ang) * half;
        b.shelter = underground ? b.pressurized : (d == District::Housing || d == District::Admin || d == District::Hospital || d == District::Security);
        b.capacity = d == District::Housing ? std::max(10, c.housing()) : 12;
        switch (d) {
            case District::Admin:
                b.rooms = {room("Komuta salonu", {{"admin_map", "Koloni haritası", "map"}, {"admin_pop", "Nüfus ekranı", "population"},
                                                   {"admin_econ", "Ekonomi ekranı", "economy"}, {"admin_sec", "Güvenlik ekranı", "security"},
                                                   {"admin_desk", "Görev masası", "missions"}, {"admin_nova", "NOVA terminali", "nova"}})};
                break;
            case District::Lab:
                b.rooms = {room("Laboratuvar", {{"lab_scope", "Mikroskop", "analyze"}, {"lab_samples", "Numune dolapları", "samples"},
                                               {"lab_pc", "Araştırma bilgisayarı", "research"}, {"lab_bench", "Deney masası", "experiment"}})};
                break;
            case District::Hospital:
                b.rooms = {room("Muayene", {{"med_exam", "Muayene alanı", "exam"}}), room("Tedavi odası", {{"med_bed", "Tedavi yatağı", "treat"}}),
                           room("Acil müdahale", {{"med_kit", "Medikal ekipman", "medkit"}})};
                break;
            case District::Production:
                b.rooms = {room("Üretim hattı", {{"prod_machines", "Üretim makineleri", "machines"}, {"prod_arm", "Robot kolları", "arms"},
                                                {"prod_qc", "Kalite kontrol", "qc"}})};
                break;
            case District::Housing:
                b.rooms = {room("Yatakhane", {{"house_bed", "Yatak", "rest"}}), room("Ortak alan", {{"house_locker", "Kişisel depo", "locker"}})};
                break;
            case District::Power: b.rooms = {room("Kontrol odası", {{"power_panel", "Enerji paneli", "power"}})}; break;
            case District::Water: b.rooms = {room("Arıtma", {{"water_panel", "Su sistemi paneli", "water"}})}; break;
            case District::Farm: b.rooms = {room("Sera", {{"farm_panel", "Işık/su kontrolü", "farm"}})}; break;
            case District::Storage: b.rooms = {room("Depo", {{"store_inv", "Envanter", "inventory"}})}; break;
            case District::Canteen: b.rooms = {room("Yemek salonu", {{"canteen_menu", "Erzak durumu", "food"}})}; break;
            case District::Security: b.rooms = {room("Kontrol noktası", {{"sec_alarm", "Alarm paneli", "alarm"}})}; break;
            default: b.rooms = {room(b.name, {})}; break;
        }
        s.buildings_.push_back(std::move(b));
    }
    (void)has_module;
    return s;
}

const Building* Settlement::find(const std::string& id) const {
    for (const auto& b : buildings_)
        if (b.id == id) return &b;
    return nullptr;
}

const Building* Settlement::find(District d) const {
    for (const auto& b : buildings_)
        if (b.district == d) return &b;
    return nullptr;
}

const Building* Settlement::at(double x, double y) const {
    for (const auto& b : buildings_)
        if (std::fabs(x - b.x) <= b.w / 2 && std::fabs(y - b.y) <= b.d / 2) return &b;
    return nullptr;
}

std::vector<std::pair<double, double>> Settlement::path(double x0, double y0, const Building& to) const {
    std::vector<std::pair<double, double>> p;
    if (const Building* from = at(x0, y0)) {
        if (from->id == to.id) {
            p.push_back({to.x, to.y});
            return p;
        }
        p.push_back({from->door_x, from->door_y});
    }
    p.push_back({0.0, 0.0});                  // merkez meydan / ana koridor kavşağı
    p.push_back({to.door_x, to.door_y});
    p.push_back({to.x, to.y});
    return p;
}

// ---------------------------------------------------------------------------------------------
Relation& Society::relation(int a, int b) { return relations_[{std::min(a, b), std::max(a, b)}]; }

const Relation* Society::find_relation(int a, int b) const {
    auto it = relations_.find({std::min(a, b), std::max(a, b)});
    return it == relations_.end() ? nullptr : &it->second;
}

Npc* Society::npc(int id) {
    for (auto& n : npcs_)
        if (n.id == id) return &n;
    return nullptr;
}
const Npc* Society::npc(int id) const {
    for (const auto& n : npcs_)
        if (n.id == id) return &n;
    return nullptr;
}

void Society::remember(Npc& n, Memory m) {
    n.memories.push_back(std::move(m));
    if (n.memories.size() > kMaxMemories) {
        // en düşük (önem x tazelik) olanı unut; önemli anılar uzun süre kalır
        const double now = n.memories.back().day;
        auto score = [&](const Memory& x) { return x.importance * std::exp(-(now - x.day) / 30.0); };
        auto it = std::min_element(n.memories.begin(), n.memories.end(), [&](const Memory& a, const Memory& b) { return score(a) < score(b); });
        n.memories.erase(it);
    }
}

void Society::sync(colony::Colony& c, const Settlement& s, Rng& rng) {
    npcs_.erase(std::remove_if(npcs_.begin(), npcs_.end(), [&](const Npc& n) {
                    const colony::Colonist* k = c.colonist(n.id);
                    return !k || !k->alive;
                }),
                npcs_.end());
    const Building* home = s.find(District::Housing);
    for (const auto& k : c.colonists()) {
        if (!k.alive || npc(k.id)) continue;
        Npc n;
        n.id = k.id;
        n.shift = (k.id % 3 == 0) ? 1 : 0;
        if (home) {
            n.x = home->x + rng.uniform(-3.0, 3.0);
            n.y = home->y + rng.uniform(-3.0, 3.0);
            n.at = home->id;
        }
        n.think_in_h = rng.uniform(0.0, 0.5);
        for (const auto& o : npcs_) {
            const colony::Colonist* ok = c.colonist(o.id);
            Relation& r = relation(k.id, o.id);
            if (ok && ok->job == k.job) {
                r.tie = "iş arkadaşı";
                r.respect = 0.6;
            } else {
                r.tie = "ekip";
            }
            r.affinity = rng.uniform(-0.1, 0.3);
        }
        npcs_.push_back(n);
    }
}

void Society::decide(Npc& n, colony::Colonist& c, colony::Colony& col, const Settlement& s, double hour) {
    ++decisions_;
    const colony::Personality& p = c.personality;
    const Building* cur = s.at(n.x, n.y);
    // 1) algılama
    std::string perceive = alarm_ ? std::string(to_string(last_event_)) : "olağan";
    if (cur && outdoor(cur->district)) perceive += ", dışarıda";
    // 2) ihtiyaç analizi: en baskın ihtiyaç
    struct N { const char* name; double v; };
    const N needs[] = {{"açlık", c.needs.hunger}, {"yorgunluk", c.needs.fatigue}, {"sağlık", 1.0 - c.needs.health}, {"susuzluk", n.thirst},
                       {"sosyal", n.social}, {"güvenlik", 1.0 - n.safety}};
    const N* top = &needs[0];
    for (const auto& x : needs)
        if (x.v > top->v) top = &x;
    // 3) öncelik ve 4) eylem
    District dest = District::Housing;
    Intent in = Intent::Idle;
    std::string why;
    using colony::Activity;
    using colony::Job;
    if (alarm_) {
        const bool brave = p.courage > 0.6;
        if (c.job == Job::Security) {
            in = last_event_ == ColonyEvent::MeteorThreat || last_event_ == ColonyEvent::DustStorm ? Intent::Patrol : Intent::RespondAlarm;
            dest = in == Intent::Patrol ? District::Airlock : District::Security;
            why = "acil tehlike: güvenlik görevi";
            (void)col.order(c.id, Activity::Work, 1.0);
        } else if (c.job == Job::Engineer && (last_event_ == ColonyEvent::PowerOutage || last_event_ == ColonyEvent::Alarm)) {
            in = last_event_ == ColonyEvent::PowerOutage ? Intent::RepairPower : Intent::RespondAlarm;
            dest = District::Power;
            why = last_event_ == ColonyEvent::PowerOutage ? "acil: enerji merkezine, yaşam desteği öncelikli" : "acil: kritik sistemleri kontrol";
            (void)col.order(c.id, Activity::Work, 1.0);
        } else if (c.job == Job::Medic && brave) {
            in = Intent::RespondAlarm;
            dest = District::Hospital;
            why = "acil: cesur sağlıkçı, yaralılara hazır";
            (void)col.order(c.id, Activity::Work, 1.0);
        } else if (p.leadership > 0.7 && last_event_ != ColonyEvent::MeteorThreat) {
            in = Intent::RespondAlarm;
            dest = District::Admin;
            why = "lider: yönetim merkezinde NOVA'dan rapor istiyor";
            (void)col.order(c.id, Activity::Idle, 1.0);
        } else {
            in = Intent::Shelter;
            dest = District::Housing;
            why = p.courage < 0.35 ? "korkuyla en yakın sığınağa" : "sivil: güvenli alana";
            (void)col.order(c.id, Activity::Idle, 1.0);
        }
    } else if (last_event_ == ColonyEvent::Discovery && c.job == Job::Scientist && c.activity != Activity::Sleep) {
        in = Intent::Research;
        dest = District::Lab;
        why = p.curiosity > 0.6 ? "meraklı: yeni keşfi incelemeye koşuyor" : "keşif: araştırma ekibine katıldı";
        (void)col.order(c.id, Activity::Work, 2.0 + 2.0 * p.curiosity);
    } else {
        switch (c.activity) {   // ekonomi katmanının seçimi (utility AI) mekâna çevrilir
            case Activity::Sleep: in = Intent::Sleep; dest = District::Housing; why = "yorgunluk/gece"; break;
            case Activity::Eat: in = Intent::Eat; dest = District::Canteen; why = "açlık"; break;
            case Activity::Treatment: in = Intent::Treatment; dest = District::Hospital; why = "sağlık"; break;
            case Activity::Socialize: in = Intent::Socialize; dest = District::Social; why = "moral/sosyal ihtiyaç"; break;
            case Activity::Work:
                in = c.job == Job::Security ? Intent::Patrol : (c.job == Job::Scientist ? Intent::Research : Intent::Work);
                dest = workplace(c.job);
                if (c.job == Job::Engineer && hour >= 13 && hour < 15) dest = District::Power;   // öğleden sonra bakım turu
                why = "vardiya";
                break;
            case Activity::Idle:
                if (n.thirst > 0.7) { in = Intent::Eat; dest = District::Canteen; why = "susuzluk"; }
                else if (p.sociability > 0.6) { in = Intent::Socialize; dest = District::Social; why = "boş zaman: sosyal"; }
                else if (p.curiosity > 0.65) { in = Intent::Idle; dest = District::Training; why = "boş zaman: eğitim merkezinde okuma"; }
                else { in = Intent::Idle; dest = District::Housing; why = "boş zaman: dinlenme"; }
                break;
        }
    }
    const Building* b = s.find(dest);
    if (b && b->id != n.target) {
        n.route = s.path(n.x, n.y, *b);
        n.target = b->id;
        n.arrived = n.route.empty();
    }
    // 5) sonuç değerlendirmesi (önceki eylem ihtiyacı karşıladı mı?)
    if (n.intent == Intent::Eat && in != Intent::Eat && c.needs.hunger < 0.3) n.satisfaction = std::min(1.0, n.satisfaction + 0.05);
    if (n.intent != Intent::Shelter && in == Intent::Shelter)
        remember(n, {0, -1, std::string(to_string(last_event_)) + " sırasında sığınağa geçtim", 0.45, -0.3});
    n.intent = in;
    n.reason = "algı: " + perceive + " | baskın ihtiyaç: " + top->name + " " + pct(top->v) + " | karar: " + why;
}

void Society::move(Npc& n, double dt_h, double speed) {
    double budget = speed * dt_h * 3600.0;
    while (budget > 0 && !n.route.empty()) {
        const auto [tx, ty] = n.route.front();
        const double dx = tx - n.x, dy = ty - n.y;
        const double d = std::sqrt(dx * dx + dy * dy);
        if (d <= budget) {
            n.x = tx;
            n.y = ty;
            budget -= d;
            n.route.erase(n.route.begin());
        } else {
            n.x += dx / d * budget;
            n.y += dy / d * budget;
            budget = 0;
        }
    }
    if (n.route.empty() && !n.arrived) {
        n.arrived = true;
        n.at = n.target;
    }
}

void Society::socialize(double day, Rng& rng, const colony::Colony& c) {
    auto comp = [&](int id) {
        for (const auto& k : c.colonists())
            if (k.id == id) return k.personality.competitiveness;
        return 0.5;
    };
    for (std::size_t i = 0; i < npcs_.size(); ++i)
        for (std::size_t j = i + 1; j < npcs_.size(); ++j) {
            Npc& a = npcs_[i];
            Npc& b = npcs_[j];
            if (!a.arrived || !b.arrived || a.at != b.at || a.at.empty()) continue;
            Relation& r = relation(a.id, b.id);
            const bool social = (a.intent == Intent::Socialize || a.intent == Intent::Eat) && (b.intent == Intent::Socialize || b.intent == Intent::Eat);
            const bool work = (a.intent == Intent::Work || a.intent == Intent::Research) && a.intent == b.intent;
            if (social) {
                r.affinity = std::min(1.0, r.affinity + 0.03);
                r.trust = std::min(1.0, r.trust + 0.01);
                a.social = std::max(0.0, a.social - 0.2);
                b.social = std::max(0.0, b.social - 0.2);
                if (rng.chance(0.005 + 0.05 * comp(a.id) * comp(b.id))) {   // tartışma: rekabetçi ikililerde daha olası
                    r.affinity -= 0.15;
                    remember(a, {day, b.id, "Bir arkadaşla tartıştım", 0.5, -0.5});
                    remember(b, {day, a.id, "Bir arkadaşla tartıştım", 0.5, -0.5});
                }
            }
            if (work) {
                r.respect = std::min(1.0, r.respect + 0.01);
                if (r.tie.empty() || r.tie == "ekip") r.tie = "iş arkadaşı";
            }
            if (r.affinity < -0.4) r.tie = "rakip";
        }
}

void Society::tick(double dt_h, double day, double hour, colony::Colony& c, const Settlement& s, double g, double px, double py, Rng& rng) {
    if (dt_h <= 0) return;
    const double speed = walking_speed_ms(g);
    for (auto& n : npcs_) {
        colony::Colonist* k = c.colonist(n.id);
        if (!k || !k->alive) continue;
        const double dx = n.x - px, dy = n.y - py;
        const double dist = std::sqrt(dx * dx + dy * dy);
        n.lod = dist < 40 ? Lod::Near : (dist < 150 ? Lod::Mid : Lod::Far);
        // ek ihtiyaçlar
        n.thirst = std::clamp(n.thirst + (n.intent == Intent::Eat ? -0.6 : 0.06) * dt_h, 0.0, 1.0);
        n.social = std::clamp(n.social + (n.intent == Intent::Socialize || n.intent == Intent::TalkToPlayer ? -0.3 : 0.02) * dt_h, 0.0, 1.0);
        if (alarm_) n.safety = std::max(0.0, n.safety - (1.1 - k->personality.courage) * 0.5 * dt_h * (n.intent == Intent::Shelter ? 0.2 : 1.0));
        else n.safety = std::min(1.0, n.safety + 0.3 * dt_h);
        if (n.intent == Intent::Work || n.intent == Intent::Research) n.satisfaction = std::min(1.0, n.satisfaction + 0.02 * dt_h * (0.5 + k->skill));
        else if (n.intent == Intent::Idle) n.satisfaction = std::max(0.0, n.satisfaction - 0.005 * dt_h);
        if (n.safety < 0.3) k->needs.morale = std::max(0.0, k->needs.morale - 0.02 * dt_h);
        // karar sıklığı LOD'a bağlı
        n.think_in_h -= dt_h;
        if (n.think_in_h <= 0) {
            decide(n, *k, c, s, hour);
            n.think_in_h = n.lod == Lod::Near ? 0.1 : (n.lod == Lod::Mid ? 0.5 : 2.0);
            if (n.lod == Lod::Far && !n.route.empty()) {   // uzak NPC: soyut simülasyon, doğrudan hedefe
                n.x = n.route.back().first;
                n.y = n.route.back().second;
                n.route.clear();
                n.arrived = true;
                n.at = n.target;
            }
        }
        if (n.lod != Lod::Far) move(n, dt_h, speed);
        // enerji onarımı ekonomiye yansır
        if (n.intent == Intent::RepairPower && n.arrived) {
            c.repair(colony::ModuleType::SolarArray, 0.08 * dt_h * (0.5 + k->skill));
            c.repair(colony::ModuleType::FissionReactor, 0.08 * dt_h * (0.5 + k->skill));
        }
    }
    social_timer_h_ += dt_h;
    if (social_timer_h_ >= 1.0) {
        social_timer_h_ = 0;
        socialize(day, rng, c);
    }
}

void Society::raise(ColonyEvent e, double day, colony::Colony& c, const Settlement& s) {
    (void)s;
    last_event_ = e;
    alarm_ = e == ColonyEvent::Alarm || e == ColonyEvent::PowerOutage || e == ColonyEvent::MeteorThreat || e == ColonyEvent::DustStorm;
    for (auto& n : npcs_) {
        n.think_in_h = 0;   // hemen tepki
        if (e != ColonyEvent::AllClear) remember(n, {day, -1, std::string(to_string(e)) + " yaşandı", e == ColonyEvent::Discovery ? 0.6 : 0.4,
                                                     e == ColonyEvent::Discovery ? 0.6 : -0.4});
        if (e == ColonyEvent::AllClear) {
            if (colony::Colonist* k = c.colonist(n.id)) k->activity_hours_left = std::min(k->activity_hours_left, 0.0);
        }
    }
}

Result<std::string> Society::talk(int id, const std::string& topic, double day, colony::Colony& c) {
    Npc* n = npc(id);
    colony::Colonist* k = c.colonist(id);
    if (!n || !k || !k->alive) return make_error(ErrorCode::NotFound, "Bu kişi yok");
    if (n->intent == Intent::Sleep) return std::string(k->name + " uyuyor. (Uyandırmak istersen 'yardım' de.)");
    Relation& r = relation(kPlayer, id);
    std::string s;
    if (r.affinity > 0.4) s = "Ah, yine sen! ";
    else if (r.affinity < -0.3) s = "Ne istiyorsun? ";
    else s = "Merhaba, ben " + k->name + ", " + colony::job_name(k->job) + ". ";
    for (auto it = n->memories.rbegin(); it != n->memories.rend(); ++it)
        if (it->about == kPlayer && it->importance >= 0.6) {
            s += it->valence > 0 ? "Geçen sefer yardım etmiştin, unutmadım. " : "Geçen seferkini unutmadım. ";
            break;
        }
    const auto& nd = k->needs;
    if (topic == "nasılsın" || topic == "nasilsin" || topic == "durum") {
        if (nd.health < 0.5) s += "Kendimi iyi hissetmiyorum, revire gitmeliyim.";
        else if (nd.hunger > 0.7) s += "Çok açım, yemek salonuna gidiyorum.";
        else if (nd.fatigue > 0.7) s += "Ayakta duracak halim yok.";
        else if (n->safety < 0.4) s += "Bu alarm beni korkutuyor.";
        else if (nd.morale < 0.4) s += "Moralim bozuk açıkçası.";
        else s += "İyiyim, sağ ol.";
    } else if (topic == "iş" || topic == "is") {
        s += std::string("Şu an: ") + to_string(n->intent) + ". (" + n->reason + ")";
    } else if (topic == "koloni") {
        const int pop = std::max(1, c.population());
        s += "Oksijen " + f1(c.resource("oxygen") / (pop * colony::kO2PerPersonDay_t)) + " gün, su " +
             f1(c.resource("water") / (pop * colony::kWaterPerPersonDay_t)) + " gün, gıda " + f1(c.resource("food") / (pop * colony::kFoodPerPersonDay_t)) + " gün yeter.";
        auto iss = issues(c);
        if (!iss.empty()) s += " Duyduğuma göre: " + iss.front() + ".";
        if (alarm_) s += std::string(" Şu an ") + to_string(last_event_) + " var, dikkatli ol.";
    } else if (topic == "yardım" || topic == "yardim") {
        bool helped = true;
        if (nd.health < 0.6) { (void)c.order(id, colony::Activity::Treatment, 2.0); s += "Revire gitmeme yardım ettiğin için sağ ol."; }
        else if (nd.hunger > 0.6) { (void)c.order(id, colony::Activity::Eat, 1.0); s += "Haklısın, önce bir şeyler yemeliyim. Teşekkürler!"; }
        else if (nd.fatigue > 0.7) { (void)c.order(id, colony::Activity::Sleep, 6.0); s += "Biraz uyuyacağım, iyi fikir."; }
        else { helped = false; s += "Şu an bir şeye ihtiyacım yok ama teklifin için sağ ol."; }
        if (helped) {
            r.affinity = std::min(1.0, r.affinity + 0.15);
            r.trust = std::min(1.0, r.trust + 0.1);
            remember(*n, {day, kPlayer, "Oyuncu bana yardım etti", 0.7, 0.8});
            n->think_in_h = 0;
        } else {
            r.affinity = std::min(1.0, r.affinity + 0.03);
        }
    } else {
        r.affinity = std::min(1.0, r.affinity + 0.02);
        const auto tr = k->personality.traits();
        if (!tr.empty()) s += "(" + tr.front() + " biri olduğu belli.)";
    }
    remember(*n, {day, kPlayer, "Oyuncuyla konuştum: " + topic, 0.2, 0.1});
    n->social = std::max(0.0, n->social - 0.1);
    return s;
}

SocietyStats Society::stats() const {
    SocietyStats st;
    st.decisions = decisions_;
    for (const auto& n : npcs_) {
        (n.lod == Lod::Near ? st.near : (n.lod == Lod::Mid ? st.mid : st.far))++;
        st.by_intent[n.intent]++;
    }
    return st;
}

std::vector<std::string> Society::issues(const colony::Colony& c) const {
    std::vector<std::string> out;
    std::map<colony::Job, int> sick, alive;
    int dose = 0, low_morale = 0, hungry = 0;
    for (const auto& k : c.colonists()) {
        if (!k.alive) continue;
        alive[k.job]++;
        if (k.needs.health < 0.5) sick[k.job]++;
        if (k.dose_limit_reached) ++dose;
        if (k.needs.morale < 0.35) ++low_morale;
        if (k.needs.hunger > 0.8) ++hungry;
    }
    for (const auto& [j, n] : sick) out.push_back(std::to_string(n) + " " + colony::job_name(j) + " hasta");
    if (dose) out.push_back(std::to_string(dose) + " kişi radyasyon kariyer sınırında (çalışamaz)");
    if (low_morale) out.push_back(std::to_string(low_morale) + " kişinin morali çok düşük");
    if (hungry) out.push_back(std::to_string(hungry) + " kişi aç");
    int unsafe = 0;
    for (const auto& n : npcs_)
        if (n.safety < 0.3) ++unsafe;
    if (unsafe) out.push_back(std::to_string(unsafe) + " kişi kendini güvende hissetmiyor");
    return out;
}

json::Value Society::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& n : npcs_) {
        json::Value o = json::Value::object();
        o.set("id", n.id);
        o.set("thirst", n.thirst);
        o.set("social", n.social);
        o.set("safety", n.safety);
        o.set("sat", n.satisfaction);
        o.set("intent", static_cast<int>(n.intent));
        o.set("at", n.at);
        o.set("target", n.target);
        o.set("x", n.x);
        o.set("y", n.y);
        o.set("shift", n.shift);
        json::Value m = json::Value::array();
        for (const auto& x : n.memories) {
            json::Value mo = json::Value::object();
            mo.set("day", x.day);
            mo.set("about", x.about);
            mo.set("text", x.text);
            mo.set("imp", x.importance);
            mo.set("val", x.valence);
            m.push(mo);
        }
        o.set("mem", m);
        a.push(o);
    }
    v.set("npcs", a);
    json::Value r = json::Value::array();
    for (const auto& [k, x] : relations_) {
        json::Value o = json::Value::object();
        o.set("a", k.first);
        o.set("b", k.second);
        o.set("aff", x.affinity);
        o.set("trust", x.trust);
        o.set("resp", x.respect);
        o.set("tie", x.tie);
        r.push(o);
    }
    v.set("rel", r);
    v.set("alarm", alarm_);
    v.set("event", static_cast<int>(last_event_));
    return v;
}

Status Society::from_json(const json::Value& v) {
    npcs_.clear();
    relations_.clear();
    for (const auto& o : v["npcs"].as_array()) {
        Npc n;
        n.id = o["id"].as_int();
        n.thirst = o["thirst"].as_number();
        n.social = o["social"].as_number();
        n.safety = o["safety"].as_number(1.0);
        n.satisfaction = o["sat"].as_number(0.6);
        const int in = o["intent"].as_int(-1);
        if (in < 0 || in > static_cast<int>(Intent::TalkToPlayer)) return make_error(ErrorCode::Parse, "Geçersiz NPC niyeti");
        n.intent = static_cast<Intent>(in);
        n.at = o["at"].as_string();
        n.target = o["target"].as_string();
        n.x = o["x"].as_number();
        n.y = o["y"].as_number();
        n.shift = o["shift"].as_int();
        for (const auto& m : o["mem"].as_array())
            n.memories.push_back({m["day"].as_number(), m["about"].as_int(), m["text"].as_string(), m["imp"].as_number(), m["val"].as_number()});
        npcs_.push_back(n);
    }
    for (const auto& o : v["rel"].as_array())
        relations_[{o["a"].as_int(), o["b"].as_int()}] = {o["aff"].as_number(), o["trust"].as_number(0.5), o["resp"].as_number(0.5), o["tie"].as_string()};
    alarm_ = v["alarm"].as_bool();
    const int e = v["event"].as_int(static_cast<int>(ColonyEvent::AllClear));
    if (e < 0 || e > static_cast<int>(ColonyEvent::AllClear)) return make_error(ErrorCode::Parse, "Geçersiz koloni olayı");
    last_event_ = static_cast<ColonyEvent>(e);
    return ok_status();
}

Diagnosis diagnose_production(const colony::Colony& c) {
    Diagnosis d;
    if (c.modules().empty()) {
        d.findings.push_back("Kolonide tesis yok");
        return d;
    }
    double sum = 0;
    double gen = 0, demand = 0;
    std::map<colony::Job, int> need, have;
    for (const auto& m : c.modules()) {
        const auto& sp = colony::spec(m.type);
        sum += m.efficiency;
        if (sp.power_kw > 0) gen += sp.power_kw * m.condition;
        else demand -= sp.power_kw;
        need[sp.staff_job] += sp.staff;
        if (m.condition < 0.6) {
            d.findings.push_back(std::string(colony::module_name(m.type)) + " bakım durumu " + pct(m.condition));
            d.suggestions.push_back("Mühendisleri " + std::string(colony::module_name(m.type)) + " onarımına yönlendir");
        }
        for (const auto& [k, q] : sp.input_per_day)
            if (c.resource(k) < q) {
                d.findings.push_back(std::string(colony::module_name(m.type)) + " için girdi eksik: " + k);
                d.suggestions.push_back(k + " tedarik et (ticaret, madencilik ya da ikmal görevi)");
            }
    }
    d.average_efficiency = sum / static_cast<double>(c.modules().size());
    for (const auto& k : c.colonists())
        if (k.alive && !k.dose_limit_reached && k.needs.health >= 0.5) have[k.job]++;
    for (const auto& [j, n] : need) {
        if (n == 0) continue;
        // personel yuvası = 8 saatlik vardiya; bir kişi günde ~1 yuva doldurur (yaklaşık)
        if (have[j] < (n + 2) / 3) {
            d.findings.push_back(std::string(colony::job_name(j)) + " yetersiz: " + std::to_string(have[j]) + " sağlıklı kişi, gereken ~" + std::to_string((n + 2) / 3));
            d.suggestions.push_back(std::string(colony::job_name(j)) + " getir ya da eğit");
        }
    }
    if (demand > gen * 1.0 && gen >= 0) {
        d.findings.push_back("Enerji yetersiz: üretim ~" + f1(gen) + " kW, talep ~" + f1(demand) + " kW (gece/fırtına hariç)");
        d.suggestions.push_back("Güneş paneli ya da fisyon reaktörü ekle; kritik olmayan üretimi kıs");
    }
    std::sort(d.suggestions.begin(), d.suggestions.end());
    d.suggestions.erase(std::unique(d.suggestions.begin(), d.suggestions.end()), d.suggestions.end());
    if (d.findings.empty()) d.findings.push_back("Belirgin darboğaz yok (ortalama verim " + pct(d.average_efficiency) + ")");
    return d;
}

}  // namespace kozmo::life

#include "kozmo/crew.hpp"

#include <algorithm>

#include "kozmo/environment.hpp"

namespace kozmo::crew {

const char* to_string(Skill s) {
    switch (s) {
        case Skill::Piloting: return "Pilotaj";
        case Skill::Eva: return "EVA";
        case Skill::Science: return "Bilim";
        case Skill::Medicine: return "Tıp";
        case Skill::Engineering: return "Mühendislik";
        case Skill::Geology: return "Jeoloji";
        case Skill::Leadership: return "Liderlik";
    }
    return "?";
}

const char* to_string(Role r) {
    switch (r) {
        case Role::Commander: return "Komutan";
        case Role::Pilot: return "Pilot";
        case Role::FlightEngineer: return "Uçuş mühendisi";
        case Role::MissionSpecialist: return "Görev uzmanı";
        case Role::MedicalOfficer: return "Sağlık sorumlusu";
    }
    return "?";
}

const std::vector<Course>& courses() {
    using S = Skill;
    static const std::vector<Course> c = {
        {"ascan", "Astronot adayı temel eğitimi", 3500, {}, {{S::Piloting, 0.1}, {S::Eva, 0.1}, {S::Science, 0.05}, {S::Engineering, 0.1}}, "astronot"},
        {"eva", "EVA eğitimi (NBL havuzu)", 400, {"ascan"}, {{S::Eva, 0.35}}, "eva"},
        {"pilot", "Uzay aracı pilotaj sertifikası", 800, {"ascan"}, {{S::Piloting, 0.4}}, "pilot"},
        {"landing", "Gezegen iniş simülatörü", 300, {"pilot"}, {{S::Piloting, 0.2}}, "iniş"},
        {"medical", "Uzay hekimliği ve acil müdahale", 600, {"ascan"}, {{S::Medicine, 0.4}}, "sağlık"},
        {"systems", "Uzay aracı sistemleri ve onarım", 500, {"ascan"}, {{S::Engineering, 0.35}}, "sistemler"},
        {"geology", "Saha jeolojisi (Apollo tarzı arazi tatbikatı)", 250, {"ascan"}, {{S::Geology, 0.4}, {S::Science, 0.1}}, "jeoloji"},
        {"command", "Komuta ve ekip kaynak yönetimi", 300, {"pilot"}, {{S::Leadership, 0.4}}, "komuta"},
    };
    return c;
}

Result<const Course*> find_course(const std::string& k) {
    for (const auto& c : courses())
        if (c.key == k) return &c;
    return make_error(ErrorCode::NotFound, "Bilinmeyen ders: " + k);
}

std::string Astronaut::rank() const {
    if (!certifications.count("astronot")) return "Aday";
    if (missions >= 5 || flight_days >= 500) return "Kıdemli astronot";
    if (missions >= 2) return "Astronot";
    return "Astronot (uçmamış)";
}

int Roster::hire(const std::string& name, Rng& rng) {
    Astronaut a;
    a.id = next_id_++;
    a.name = name;
    for (auto& s : a.skill) s = rng.uniform(0.1, 0.4);
    list_.push_back(a);
    return a.id;
}

Astronaut* Roster::find(int id) {
    for (auto& a : list_)
        if (a.id == id) return &a;
    return nullptr;
}
const Astronaut* Roster::find(int id) const {
    for (const auto& a : list_)
        if (a.id == id) return &a;
    return nullptr;
}

Status Roster::enroll(int id, const std::string& key) {
    Astronaut* a = find(id);
    if (!a) return make_error(ErrorCode::NotFound, "Astronot yok");
    auto c = find_course(key);
    if (!c) return c.error();
    if (!a->training.empty()) return make_error(ErrorCode::Infeasible, a->name + " zaten '" + a->training + "' dersinde");
    if (a->completed.count(key)) return make_error(ErrorCode::Infeasible, "Ders zaten tamamlandı");
    for (const auto& p : c.value()->prerequisites)
        if (!a->completed.count(p)) return make_error(ErrorCode::Locked, "Önkoşul eksik: " + find_course(p).value()->name);
    if (a->dose_msv >= env::kCareerLimitMsv) return make_error(ErrorCode::Infeasible, "Kariyer doz sınırı: uçuş eğitimine alınamaz");
    a->training = key;
    a->training_left_h = c.value()->hours;
    return ok_status();
}

std::vector<std::string> Roster::train(double h) {
    std::vector<std::string> done;
    for (auto& a : list_) {
        if (a.training.empty() || h <= 0) continue;
        // yorgunluk verimi düşürür: %100 yorgunken yarım hız
        const double eff = 1.0 - 0.5 * a.fatigue;
        a.training_left_h -= h * eff;
        a.fatigue = std::min(1.0, a.fatigue + h / 400.0);
        if (a.training_left_h <= 0) {
            const Course* c = find_course(a.training).value();
            for (const auto& [s, g] : c->gains) a.skill[static_cast<int>(s)] = std::min(1.0, a.skill[static_cast<int>(s)] + g);
            if (!c->certification.empty()) a.certifications.insert(c->certification);
            a.completed.insert(a.training);
            done.push_back(a.name + ": " + c->name);
            a.training.clear();
            a.training_left_h = 0;
        }
    }
    return done;
}

void Roster::rest(double h) {
    for (auto& a : list_) a.fatigue = std::max(0.0, a.fatigue - h / 48.0);
}

Status Roster::log_eva(int id, double hours, double dose) {
    Astronaut* a = find(id);
    if (!a) return make_error(ErrorCode::NotFound, "Astronot yok");
    if (!a->certifications.count("eva")) return make_error(ErrorCode::Locked, a->name + " EVA sertifikasız");
    a->eva_hours += hours;
    a->dose_msv += dose;
    a->skill[static_cast<int>(Skill::Eva)] = std::min(1.0, a->get(Skill::Eva) + hours * 0.002);
    a->fatigue = std::min(1.0, a->fatigue + hours / 20.0);
    return ok_status();
}

Status Roster::log_mission(const std::vector<int>& ids, double days, double dpd) {
    for (int id : ids) {
        Astronaut* a = find(id);
        if (!a) return make_error(ErrorCode::NotFound, "Astronot yok: " + std::to_string(id));
        a->flight_days += days;
        a->dose_msv += days * dpd;
        ++a->missions;
    }
    return ok_status();
}

bool Roster::eligible(const Astronaut& a, Role r) const {
    if (!a.certifications.count("astronot") || a.dose_msv >= env::kCareerLimitMsv || a.fatigue > 0.85 || !a.training.empty()) return false;
    switch (r) {
        case Role::Commander: return a.certifications.count("komuta") && a.get(Skill::Leadership) >= 0.5 && a.get(Skill::Piloting) >= 0.5;
        case Role::Pilot: return a.certifications.count("pilot") > 0;
        case Role::FlightEngineer: return a.certifications.count("sistemler") > 0;
        case Role::MedicalOfficer: return a.certifications.count("sağlık") > 0;
        case Role::MissionSpecialist: return true;
    }
    return false;
}

CrewCheck Roster::select(const std::vector<Requirement>& req, double days, bool eva) const {
    CrewCheck c;
    std::set<int> used;
    std::vector<Requirement> r = req;
    if (days > 30 && std::none_of(r.begin(), r.end(), [](const Requirement& x) { return x.role == Role::MedicalOfficer; }))
        r.push_back({Role::MedicalOfficer, 1});
    // önce dar roller (komutan, pilot, sağlık) atanır
    std::sort(r.begin(), r.end(), [](const Requirement& a, const Requirement& b) { return static_cast<int>(a.role) < static_cast<int>(b.role); });
    for (const auto& q : r) {
        std::vector<const Astronaut*> cand;
        for (const auto& a : list_)
            if (!used.count(a.id) && eligible(a, q.role) && (!eva || q.role == Role::Pilot || q.role == Role::Commander || a.certifications.count("eva"))) cand.push_back(&a);
        auto key = [&](const Astronaut* a) {
            switch (q.role) {
                case Role::Commander: return a->get(Skill::Leadership) + a->get(Skill::Piloting);
                case Role::Pilot: return a->get(Skill::Piloting);
                case Role::FlightEngineer: return a->get(Skill::Engineering);
                case Role::MedicalOfficer: return a->get(Skill::Medicine);
                case Role::MissionSpecialist: return a->get(Skill::Science) + a->get(Skill::Geology);
            }
            return 0.0;
        };
        std::sort(cand.begin(), cand.end(), [&](const Astronaut* a, const Astronaut* b) { return key(a) > key(b); });
        for (int i = 0; i < q.count; ++i) {
            if (i >= static_cast<int>(cand.size())) {
                c.ok = false;
                c.problems.push_back(std::string(to_string(q.role)) + " için uygun astronot yok" + (eva ? " (EVA sertifikası gerekli)" : ""));
                break;
            }
            used.insert(cand[static_cast<std::size_t>(i)]->id);
            c.assignment[q.role].push_back(cand[static_cast<std::size_t>(i)]->id);
        }
    }
    return c;
}

std::vector<Requirement> standard_crew(double days) {
    std::vector<Requirement> r = {{Role::Commander, 1}, {Role::Pilot, 1}, {Role::FlightEngineer, 1}, {Role::MissionSpecialist, 1}};
    if (days > 30) r.push_back({Role::MedicalOfficer, 1});
    return r;
}

json::Value Roster::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& x : list_) {
        json::Value o = json::Value::object();
        o.set("id", x.id);
        o.set("name", x.name);
        json::Value s = json::Value::array();
        for (double k : x.skill) s.push(k);
        o.set("skill", s);
        json::Value cert = json::Value::array();
        for (const auto& k : x.certifications) cert.push(k);
        o.set("cert", cert);
        json::Value done = json::Value::array();
        for (const auto& k : x.completed) done.push(k);
        o.set("done", done);
        o.set("training", x.training);
        o.set("left", x.training_left_h);
        o.set("days", x.flight_days);
        o.set("eva", x.eva_hours);
        o.set("dose", x.dose_msv);
        o.set("missions", x.missions);
        o.set("fatigue", x.fatigue);
        a.push(o);
    }
    v.set("astronauts", a);
    v.set("next", next_id_);
    return v;
}

Status Roster::from_json(const json::Value& v) {
    list_.clear();
    for (const auto& o : v["astronauts"].as_array()) {
        Astronaut a;
        a.id = o["id"].as_int();
        a.name = o["name"].as_string();
        const auto& s = o["skill"].as_array();
        if (s.size() != kSkillCount) return make_error(ErrorCode::Parse, "Bozuk astronot kaydı");
        for (std::size_t i = 0; i < kSkillCount; ++i) a.skill[i] = std::clamp(s[i].as_number(), 0.0, 1.0);
        for (const auto& c : o["cert"].as_array()) a.certifications.insert(c.as_string());
        for (const auto& c : o["done"].as_array()) a.completed.insert(c.as_string());
        a.training = o["training"].as_string();
        if (!a.training.empty() && !find_course(a.training)) return make_error(ErrorCode::Parse, "Bilinmeyen ders kaydı");
        a.training_left_h = o["left"].as_number();
        a.flight_days = o["days"].as_number();
        a.eva_hours = o["eva"].as_number();
        a.dose_msv = o["dose"].as_number();
        a.missions = o["missions"].as_int();
        a.fatigue = o["fatigue"].as_number();
        list_.push_back(a);
    }
    next_id_ = v["next"].as_int(1);
    return ok_status();
}

}  // namespace kozmo::crew

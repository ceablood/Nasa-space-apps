#include "kozmo/quest.hpp"

#include <algorithm>
#include <cstdio>

namespace kozmo::quest {

const char* to_string(Goal g) {
    switch (g) {
        case Goal::EnterDistrict: return "Bölgeye git";
        case Goal::UseItem: return "Konsolu kullan";
        case Goal::TalkToJob: return "Konuş";
        case Goal::CollectSamples: return "Numune topla";
        case Goal::BuildModule: return "İnşa et";
        case Goal::RepairPower: return "Enerjiyi onar";
        case Goal::AnalyzeSample: return "Numune analizi";
        case Goal::ReturnToCraft: return "Araca dön";
        case Goal::ReachOrbit: return "Yörüngeye çık";
    }
    return "?";
}

const char* to_string(State s) {
    switch (s) {
        case State::Active: return "Etkin";
        case State::Completed: return "Tamamlandı";
        case State::Failed: return "Başarısız";
    }
    return "?";
}

double Quest::progress() const {
    if (objectives.empty()) return 1.0;
    double s = 0;
    for (const auto& o : objectives) s += std::min(1.0, static_cast<double>(o.progress) / std::max(1, o.count));
    return s / static_cast<double>(objectives.size());
}

std::vector<std::string> template_keys() { return {"power_crisis", "sample_hunt", "new_home", "health_check", "security_round", "orbit_test"}; }

namespace {
// bölge sırası life::District ile aynı: 2 Admin, 3 Housing, 5 Hospital, 6 Lab, 9 Power, 17 Airlock; meslek: colony::Job; modül: colony::ModuleType
Result<Quest> make(const std::string& k) {
    Quest q;
    q.key = k;
    if (k == "power_crisis") {
        q.title = "Enerji krizi";
        q.description = "Güneş dizileri arızalı. Enerji tesisine git ve kontrol panelinden arızayı gider.";
        q.objectives = {{Goal::EnterDistrict, 9, "", 1, 0, "Enerji tesisine git"}, {Goal::RepairPower, 0, "", 1, 0, "Arızayı gider"}};
        q.reward = {3000, 0, 0.2};
        q.deadline_h = 24;
    } else if (k == "sample_hunt") {
        q.title = "Numune avı";
        q.description = "Bilim ekibi yüzeyden 3 numune istiyor; laboratuvarda mikroskopla analiz et.";
        q.objectives = {{Goal::CollectSamples, 0, "", 3, 0, "3 numune topla"}, {Goal::AnalyzeSample, 0, "", 1, 0, "Laboratuvarda analiz et"}};
        q.reward = {1500, 25, 0.15};
    } else if (k == "new_home") {
        q.title = "Yeni yuva";
        q.description = "Ekip iniş kampında sıkışık yaşıyor. Bir yaşam modülü inşa ettir.";
        q.objectives = {{Goal::BuildModule, 0, "", 1, 0, "Yaşam modülü inşa et"}};
        q.reward = {5000, 0, 0.25};
    } else if (k == "health_check") {
        q.title = "Sağlık taraması";
        q.description = "Hastaneye git, muayene alanını kullan ve doktorla konuş.";
        q.objectives = {{Goal::EnterDistrict, 5, "", 1, 0, "Hastaneye git"}, {Goal::UseItem, 0, "med_exam", 1, 0, "Muayene ol"},
                        {Goal::TalkToJob, 4, "", 1, 0, "Doktorla konuş"}};
        q.reward = {500, 0, 0.1};
    } else if (k == "security_round") {
        q.title = "Güvenlik turu";
        q.description = "Dış keşif çıkışını kontrol et ve güvenlik görevlisine rapor ver.";
        q.objectives = {{Goal::EnterDistrict, 17, "", 1, 0, "Hava kilidine git"}, {Goal::TalkToJob, 6, "", 1, 0, "Güvenlik görevlisiyle konuş"}};
        q.reward = {800, 0, 0.1};
    } else if (k == "orbit_test") {
        q.title = "Yörünge testi";
        q.description = "Aracı yüzeyden alçak yörüngeye çıkar.";
        q.objectives = {{Goal::ReturnToCraft, 0, "", 1, 0, "Araca bin"}, {Goal::ReachOrbit, 0, "", 1, 0, "Yörüngeye çık"}};
        q.reward = {4000, 10, 0};
    } else {
        return make_error(ErrorCode::NotFound, "Bilinmeyen görev şablonu: " + k);
    }
    return q;
}
}  // namespace

Result<int> Log::offer(const std::string& k, int giver, double now_h) {
    for (const auto& q : quests_)
        if (q.key == k && q.state == State::Active) return make_error(ErrorCode::Infeasible, "Bu görev zaten etkin: " + q.title);
    auto q = make(k);
    if (!q) return q.error();
    q.value().giver = giver;
    return add(q.value(), now_h);
}

Result<int> Log::add(Quest q, double now_h) {
    if (q.objectives.empty()) return make_error(ErrorCode::InvalidArgument, "Hedefsiz görev");
    q.id = next_id_++;
    q.accepted_h = now_h;
    q.state = State::Active;
    quests_.push_back(q);
    return q.id;
}

std::vector<Completion> Log::notify(const Event& e, double now_h) {
    std::vector<Completion> out;
    for (auto& q : quests_) {
        if (q.state != State::Active) continue;
        for (auto& o : q.objectives) {
            if (o.done() || o.goal != e.goal) continue;
            bool match = true;
            switch (o.goal) {
                case Goal::EnterDistrict: case Goal::TalkToJob: case Goal::BuildModule: match = o.target == e.arg; break;
                case Goal::UseItem: match = o.item == e.item; break;
                default: break;
            }
            if (match) {
                o.progress = std::min(o.count, o.progress + std::max(1, e.amount));
                break;   // bir olay bir hedefi ilerletir
            }
        }
        const bool all = std::all_of(q.objectives.begin(), q.objectives.end(), [](const Objective& o) { return o.done(); });
        if (all && !q.rewarded) {
            q.state = State::Completed;
            q.rewarded = true;
            out.push_back({q.id, q.title, q.reward, q.giver});
        }
    }
    tick(now_h);
    return out;
}

void Log::tick(double now_h) {
    for (auto& q : quests_)
        if (q.state == State::Active && q.deadline_h > 0 && now_h - q.accepted_h > q.deadline_h) q.state = State::Failed;
}

Status Log::abandon(int id) {
    for (auto& q : quests_)
        if (q.id == id && q.state == State::Active) {
            q.state = State::Failed;
            return ok_status();
        }
    return make_error(ErrorCode::NotFound, "Etkin görev yok");
}

const Quest* Log::find(int id) const {
    for (const auto& q : quests_)
        if (q.id == id) return &q;
    return nullptr;
}

const Quest* Log::find_key(const std::string& k) const {
    for (auto it = quests_.rbegin(); it != quests_.rend(); ++it)
        if (it->key == k) return &*it;
    return nullptr;
}

int Log::active_count() const {
    return static_cast<int>(std::count_if(quests_.begin(), quests_.end(), [](const Quest& q) { return q.state == State::Active; }));
}

std::string Log::summary() const {
    std::string s;
    for (const auto& q : quests_) {
        if (q.state != State::Active) continue;
        char b[64];
        std::snprintf(b, sizeof(b), " %%%.0f", q.progress() * 100);
        s += "• " + q.title + b + "\n";
        for (const auto& o : q.objectives) s += std::string("   ") + (o.done() ? "[x] " : "[ ] ") + o.text + (o.count > 1 ? " (" + std::to_string(o.progress) + "/" + std::to_string(o.count) + ")" : "") + "\n";
    }
    return s.empty() ? "Etkin görev yok" : s;
}

json::Value Log::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& q : quests_) {
        json::Value o = json::Value::object();
        o.set("id", q.id);
        o.set("key", q.key);
        o.set("giver", q.giver);
        o.set("state", static_cast<int>(q.state));
        o.set("accepted", q.accepted_h);
        o.set("rewarded", q.rewarded);
        json::Value p = json::Value::array();
        for (const auto& ob : q.objectives) p.push(ob.progress);
        o.set("progress", p);
        a.push(o);
    }
    v.set("quests", a);
    v.set("next", next_id_);
    return v;
}

Status Log::from_json(const json::Value& v) {
    quests_.clear();
    for (const auto& o : v["quests"].as_array()) {
        auto q = make(o["key"].as_string());
        if (!q) return q.error();
        Quest x = q.value();
        x.id = o["id"].as_int();
        x.giver = o["giver"].as_int(-1);
        const int st = o["state"].as_int();
        if (st < 0 || st > 2) return make_error(ErrorCode::Parse, "Geçersiz görev durumu");
        x.state = static_cast<State>(st);
        x.accepted_h = o["accepted"].as_number();
        x.rewarded = o["rewarded"].as_bool();
        const auto& p = o["progress"].as_array();
        for (std::size_t i = 0; i < p.size() && i < x.objectives.size(); ++i) x.objectives[i].progress = p[i].as_int();
        quests_.push_back(x);
    }
    next_id_ = v["next"].as_int(1);
    return ok_status();
}

}  // namespace kozmo::quest

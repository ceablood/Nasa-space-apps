#include "kozmo/construction.hpp"

#include <algorithm>
#include <initializer_list>

namespace kozmo::build {

using colony::ModuleType;

const char* to_string(Piece p) {
    switch (p) {
        case Piece::Foundation: return "Temel";
        case Piece::Wall: return "Duvar";
        case Piece::Roof: return "Tavan";
        case Piece::Door: return "Kapı";
        case Piece::Window: return "Pencere";
        case Piece::Corridor: return "Koridor";
        case Piece::Airlock: return "Hava kilidi";
        case Piece::Stairs: return "Merdiven";
        case Piece::Elevator: return "Asansör";
        case Piece::PowerLink: return "Enerji bağlantısı";
        case Piece::WaterLink: return "Su bağlantısı";
        case Piece::OxygenLine: return "Oksijen hattı";
        case Piece::DataLine: return "Veri hattı";
    }
    return "?";
}

const char* to_string(State s) {
    switch (s) {
        case State::Building: return "İnşa ediliyor";
        case State::WaitingConnection: return "Bağlantı bekliyor";
        case State::Done: return "Tamamlandı";
    }
    return "?";
}

const PieceSpec& spec(Piece p) {
    //                          demir t  kredi  emek-sa  kW    bakım  dayanım kapasite
    static const PieceSpec k[kPieceCount] = {
        {Piece::Foundation, 2.0, 150, 16, 0.0, 0.01, 0.9, 0},
        {Piece::Wall, 0.6, 60, 6, 0.0, 0.02, 0.7, 0},
        {Piece::Roof, 1.0, 80, 8, 0.0, 0.03, 0.6, 0},
        {Piece::Door, 0.2, 40, 3, 0.05, 0.03, 0.5, 0},
        {Piece::Window, 0.1, 70, 3, 0.0, 0.04, 0.3, 0},
        {Piece::Corridor, 0.8, 70, 8, 0.2, 0.02, 0.7, 20},
        {Piece::Airlock, 0.9, 300, 14, 0.8, 0.05, 0.8, 2},
        {Piece::Stairs, 0.3, 30, 3, 0.0, 0.01, 0.8, 0},
        {Piece::Elevator, 0.7, 250, 12, 1.5, 0.06, 0.6, 6},
        {Piece::PowerLink, 0.2, 60, 4, 0.0, 0.02, 0.6, 0},
        {Piece::WaterLink, 0.2, 50, 4, 0.1, 0.03, 0.6, 0},
        {Piece::OxygenLine, 0.2, 60, 4, 0.1, 0.03, 0.6, 0},
        {Piece::DataLine, 0.05, 30, 2, 0.05, 0.01, 0.6, 0},
    };
    return k[static_cast<int>(p)];
}

Blueprint blueprint(ModuleType t) {
    using P = Piece;
    switch (t) {
        case ModuleType::Habitat:
            return {t, {{P::Foundation, 1}, {P::Wall, 4}, {P::Roof, 1}, {P::Door, 2}, {P::Window, 2}, {P::Airlock, 1}, {P::Stairs, 1},
                        {P::PowerLink, 1}, {P::OxygenLine, 1}, {P::WaterLink, 1}, {P::DataLine, 1}},
                    {P::PowerLink, P::OxygenLine, P::WaterLink}};
        case ModuleType::SolarArray: return {t, {{P::Foundation, 1}, {P::PowerLink, 2}, {P::DataLine, 1}}, {}};
        case ModuleType::FissionReactor: return {t, {{P::Foundation, 2}, {P::Wall, 4}, {P::Roof, 1}, {P::PowerLink, 2}, {P::DataLine, 1}}, {}};
        case ModuleType::WaterRecycler:
            return {t, {{P::Foundation, 1}, {P::Wall, 4}, {P::Roof, 1}, {P::Door, 1}, {P::PowerLink, 1}, {P::WaterLink, 2}, {P::DataLine, 1}},
                    {P::PowerLink, P::WaterLink}};
        case ModuleType::Greenhouse:
            return {t, {{P::Foundation, 1}, {P::Wall, 2}, {P::Window, 6}, {P::Roof, 1}, {P::Door, 1}, {P::PowerLink, 1}, {P::WaterLink, 1}},
                    {P::PowerLink, P::WaterLink}};
        case ModuleType::Electrolyzer:
            return {t, {{P::Foundation, 1}, {P::Wall, 4}, {P::Roof, 1}, {P::Door, 1}, {P::PowerLink, 1}, {P::WaterLink, 1}, {P::OxygenLine, 1}},
                    {P::PowerLink, P::WaterLink}};
        case ModuleType::Lab:
        case ModuleType::Clinic:
            return {t, {{P::Foundation, 1}, {P::Wall, 4}, {P::Roof, 1}, {P::Door, 1}, {P::Window, 1}, {P::Corridor, 1}, {P::PowerLink, 1},
                        {P::OxygenLine, 1}, {P::DataLine, 1}},
                    {P::PowerLink, P::OxygenLine}};
        case ModuleType::Mine:
        case ModuleType::Sabatier:
            return {t, {{P::Foundation, 2}, {P::Wall, 2}, {P::Roof, 1}, {P::Airlock, 1}, {P::PowerLink, 2}, {P::DataLine, 1}}, {P::PowerLink}};
    }
    return {t, {{Piece::Foundation, 1}}, {}};
}

Blueprint reinforcement() { return {ModuleType::Habitat, {{Piece::Wall, 6}, {Piece::Roof, 2}, {Piece::Foundation, 1}}, {}}; }

Cost total(const Blueprint& b) {
    Cost c;
    int n = 0;
    for (const auto& [p, k] : b.pieces) {
        const PieceSpec& s = spec(p);
        c.iron_t += s.iron_t * k;
        c.credits += s.credits * k;
        c.labor_h += s.labor_h * k;
        c.power_kw += s.power_kw * k;
        c.maintenance += s.maintenance * k;
        c.durability += s.durability * k;
        n += k;
    }
    if (n) c.durability /= n;
    return c;
}

int site_district(ModuleType t) {
    // life::District sırası: 0 LandingPad .. 3 Housing, 5 Hospital, 6 Lab, 8 Processing, 9 Power, 10 Water, 11 Farm
    switch (t) {
        case ModuleType::Habitat: return 3;
        case ModuleType::Clinic: return 5;
        case ModuleType::Lab: return 6;
        case ModuleType::Mine: case ModuleType::Sabatier: return 8;
        case ModuleType::SolarArray: case ModuleType::FissionReactor: return 9;
        case ModuleType::WaterRecycler: case ModuleType::Electrolyzer: return 10;
        case ModuleType::Greenhouse: return 11;
    }
    return 3;
}

namespace {
Result<int> begin(std::vector<Project>& ps, int& next, ModuleType t, bool reinforce, const Blueprint& b, colony::Colony& c, econ::Wallet& w, double day) {
    const Cost k = total(b);
    if (c.resource("iron") < k.iron_t)
        return make_error(ErrorCode::InsufficientResources, "Yetersiz demir: " + std::to_string(k.iron_t).substr(0, 5) + " t gerekli, stok " +
                                                                std::to_string(c.resource("iron")).substr(0, 5) + " t");
    if (w.balance() < k.credits) return make_error(ErrorCode::InsufficientFunds, "Yetersiz kredi");
    auto st = w.spend(k.credits, std::string("İnşaat: ") + (reinforce ? "güçlendirme" : colony::module_name(t)), day);
    if (!st) return st.error();
    (void)c.take("iron", k.iron_t);
    Project p;
    p.id = next++;
    p.module = t;
    p.reinforce = reinforce;
    p.labor_total_h = k.labor_h;
    ps.push_back(p);
    return p.id;
}
}  // namespace

Result<int> Manager::start(ModuleType t, colony::Colony& c, econ::Wallet& w, const std::vector<std::string>& unlocked, double day) {
    const auto& sp = colony::spec(t);
    if (!sp.research.empty() && std::find(unlocked.begin(), unlocked.end(), sp.research) == unlocked.end())
        return make_error(ErrorCode::Locked, std::string(colony::module_name(t)) + " için araştırma gerekli: " + sp.research);
    return begin(projects_, next_id_, t, false, blueprint(t), c, w, day);
}

Result<int> Manager::start_reinforcement(colony::Colony& c, econ::Wallet& w, double day) {
    if (reinforced_) return make_error(ErrorCode::Infeasible, "Koloni zaten güçlendirildi");
    for (const auto& p : projects_)
        if (p.reinforce && p.state != State::Done) return make_error(ErrorCode::Infeasible, "Güçlendirme projesi zaten sürüyor");
    return begin(projects_, next_id_, ModuleType::Habitat, true, reinforcement(), c, w, day);
}

bool Manager::active() const { return current() != nullptr; }

const Project* Manager::current() const {
    for (const auto& p : projects_)
        if (p.state == State::Building) return &p;
    return nullptr;
}

void Manager::work(double labor_h) {
    for (auto& p : projects_) {
        if (p.state != State::Building || labor_h <= 0) continue;
        const double use = std::min(labor_h, p.labor_total_h - p.labor_done_h);
        p.labor_done_h += use;
        labor_h -= use;
        if (p.labor_done_h >= p.labor_total_h - 1e-9) p.state = State::WaitingConnection;
    }
}

std::vector<ModuleType> Manager::complete(colony::Colony& c, const std::vector<std::string>& unlocked) {
    std::vector<ModuleType> out;
    auto has = [&](std::initializer_list<ModuleType> ts) {
        for (const auto& m : c.modules())
            for (auto t : ts)
                if (m.type == t) return true;
        return false;
    };
    for (bool changed = true; changed;) {   // bir modül tamamlanınca diğerlerinin bağlantısı açılabilir
      changed = false;
      for (auto& p : projects_) {
        if (p.state != State::WaitingConnection) continue;
        if (p.reinforce) {
            reinforced_ = true;
            p.state = State::Done;
            changed = true;
            continue;
        }
        // bağlantılar: enerji kaynağı, su kaynağı, oksijen kaynağı (stok ya da üretici)
        std::string miss;
        for (Piece k : blueprint(p.module).connections) {
            if (k == Piece::PowerLink && !has({ModuleType::SolarArray, ModuleType::FissionReactor})) miss = "enerji kaynağı yok (önce güneş dizisi/reaktör)";
            if (k == Piece::WaterLink && c.resource("water") <= 0 && !has({ModuleType::Mine, ModuleType::WaterRecycler})) miss = "su kaynağı yok";
            if (k == Piece::OxygenLine && c.resource("oxygen") <= 0 && !has({ModuleType::Electrolyzer})) miss = "oksijen kaynağı yok";
        }
        p.missing = miss;
        if (!miss.empty()) continue;
        auto st = c.add_module(p.module, unlocked);
        if (!st) {
            p.missing = st.error().message;
            continue;
        }
        p.state = State::Done;
        out.push_back(p.module);
        changed = true;
      }
    }
    return out;
}

json::Value Manager::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& p : projects_) {
        json::Value o = json::Value::object();
        o.set("id", p.id);
        o.set("module", static_cast<int>(p.module));
        o.set("reinforce", p.reinforce);
        o.set("done", p.labor_done_h);
        o.set("total", p.labor_total_h);
        o.set("state", static_cast<int>(p.state));
        a.push(o);
    }
    v.set("projects", a);
    v.set("next", next_id_);
    v.set("reinforced", reinforced_);
    return v;
}

Status Manager::from_json(const json::Value& v) {
    projects_.clear();
    for (const auto& o : v["projects"].as_array()) {
        const int m = o["module"].as_int(-1), s = o["state"].as_int(-1);
        if (m < 0 || m > static_cast<int>(ModuleType::WaterRecycler) || s < 0 || s > 2) return make_error(ErrorCode::Parse, "Geçersiz inşaat kaydı");
        Project p;
        p.id = o["id"].as_int();
        p.module = static_cast<ModuleType>(m);
        p.reinforce = o["reinforce"].as_bool();
        p.labor_done_h = o["done"].as_number();
        p.labor_total_h = o["total"].as_number();
        p.state = static_cast<State>(s);
        projects_.push_back(p);
    }
    next_id_ = v["next"].as_int(1);
    reinforced_ = v["reinforced"].as_bool();
    return ok_status();
}

}  // namespace kozmo::build

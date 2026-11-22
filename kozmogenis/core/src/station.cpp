#include "kozmo/station.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::station {

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kG0 = 9.80665;
constexpr double kCd = 2.2;
// ISS ECLSS: O2 elektrolizle üretilir (su tüketir); su geri kazanımı ~%98 (2023). Kişi başı O2 0.84 kg/gün.
constexpr double kO2PerCrewDay = 0.84, kWaterPerCrewDay = 3.5 * 0.02 + 0.84 * 1.125 * 0.0, kFoodPerCrewDay = 1.8;
}  // namespace

const char* to_string(ModuleKind k) {
    switch (k) {
        case ModuleKind::Node: return "Bağlantı düğümü";
        case ModuleKind::Habitat: return "Yaşam modülü";
        case ModuleKind::Lab: return "Laboratuvar";
        case ModuleKind::SolarTruss: return "Güneş paneli kafesi";
        case ModuleKind::DockingPort: return "Kenetlenme adaptörü";
        case ModuleKind::Cupola: return "Gözlem kubbesi";
        case ModuleKind::Airlock: return "Hava kilidi";
        case ModuleKind::Storage: return "Depo modülü";
        case ModuleKind::Propulsion: return "İtki modülü";
    }
    return "?";
}

const ModuleSpec& spec(ModuleKind k) {
    // ISS modüllerinden yuvarlanmış: Unity/Harmony düğümleri ~12-14 t, Destiny lab ~14.5 t, P/S kafes + panel ~
    // 15-17 t ve ~31 kW tepe (gölge dahil ortalama ~15 kW), Cupola ~1.9 t, Quest hava kilidi ~6 t, Zvezda (itki/yaşam) ~19 t
    static const ModuleSpec s[] = {
        {ModuleKind::Node, "Bağlantı düğümü", 13.0, -1.0, 0, 60, 2},
        {ModuleKind::Habitat, "Yaşam modülü", 19.0, -6.0, 3, 80, 1},
        {ModuleKind::Lab, "Laboratuvar", 14.5, -10.0, 0, 70, 0},
        {ModuleKind::SolarTruss, "Güneş paneli kafesi", 16.0, 15.0, 0, 60, 0},   // ~31 kW tepe, gölgeyle ortalama ~15 kW; paneller çoğunlukla kenardan
        {ModuleKind::DockingPort, "Kenetlenme adaptörü", 0.5, -0.2, 0, 5, 1},
        {ModuleKind::Cupola, "Gözlem kubbesi", 1.9, -0.3, 0, 5, 0},
        {ModuleKind::Airlock, "Hava kilidi", 6.0, -1.0, 0, 20, 0},
        {ModuleKind::Storage, "Depo modülü", 11.0, -0.5, 0, 50, 0},
        {ModuleKind::Propulsion, "İtki modülü", 19.0, -2.0, 1, 70, 1},
    };
    return s[static_cast<int>(k)];
}

Body earth() { return {3.986004418e14, 6.371e6, true}; }
Body moon() { return {4.9048695e12, 1.7374e6, false}; }

double thermosphere_density(double h, double solar) {
    // 400 km referansı; ölçek yüksekliği ~58 km (300-500 km arası için makul üstel uyum)
    return 3.0e-12 * std::clamp(solar, 0.3, 3.0) * std::exp(-(h - 400e3) / 58e3);
}

Station::Station(std::string name, Body b, double alt) : name_(std::move(name)), body_(b), altitude_m_(alt) {}

Status Station::add_module(ModuleKind k) {
    if (deorbited_) return make_error(ErrorCode::Infeasible, "İstasyon yörüngeden çıktı");
    // bağlantı kuralı: ilk modül dışında en az bir düğüm/itki modülü portu gerekir
    if (!modules_.empty() && k != ModuleKind::Node && k != ModuleKind::SolarTruss) {
        int structural = 0, used = 0;
        for (auto m : modules_) {
            if (m == ModuleKind::Node) structural += 4;      // düğüm: 6 yuva (2'si gövde hattı)
            if (m == ModuleKind::Propulsion || m == ModuleKind::Habitat) structural += 1;
            if (m != ModuleKind::Node && m != ModuleKind::SolarTruss) ++used;
        }
        if (used >= structural + 1) return make_error(ErrorCode::Infeasible, "Boş bağlantı yuvası yok: önce düğüm modülü ekle");
    }
    modules_.push_back(k);
    return ok_status();
}

double Station::mass_t() const {
    double m = 0;
    for (auto k : modules_) m += spec(k).mass_t;
    for (const auto& d : docked_) m += d.mass_t;
    return m + (o2_kg_ + water_kg_ + food_kg_ + prop_kg_) / 1000.0;
}

double Station::drag_area_m2() const {
    double a = 0;
    for (auto k : modules_) a += spec(k).area_m2;
    a += 15.0 * static_cast<double>(docked_.size());
    return a;
}

double Station::power_kw() const {
    double p = 0;
    for (auto k : modules_) p += spec(k).power_kw;
    return p - crew_ * 0.5;
}

int Station::crew_capacity() const {
    int c = 0;
    for (auto k : modules_) c += spec(k).crew;
    return c;
}

int Station::ports() const {
    int p = 0;
    for (auto k : modules_) p += spec(k).ports;
    return p;
}

double Station::period_min() const {
    const double a = body_.radius_m + altitude_m_;
    return 2 * kPi * std::sqrt(a * a * a / body_.mu) / 60.0;
}

Result<int> Station::dock(const std::string& vehicle, double mass) {
    if (deorbited_) return make_error(ErrorCode::Infeasible, "İstasyon yok");
    if (static_cast<int>(docked_.size()) >= ports()) return make_error(ErrorCode::Infeasible, "Boş kenetlenme portu yok (" + std::to_string(ports()) + " port dolu)");
    for (const auto& d : docked_)
        if (d.name == vehicle) return make_error(ErrorCode::Infeasible, vehicle + " zaten kenetli");
    std::vector<bool> used(static_cast<std::size_t>(ports()), false);
    for (const auto& d : docked_) used[static_cast<std::size_t>(d.port)] = true;
    int port = 0;
    while (used[static_cast<std::size_t>(port)]) ++port;
    docked_.push_back({port, vehicle, mass});
    return port;
}

Status Station::undock(const std::string& vehicle) {
    auto it = std::find_if(docked_.begin(), docked_.end(), [&](const DockedVehicle& d) { return d.name == vehicle; });
    if (it == docked_.end()) return make_error(ErrorCode::NotFound, vehicle + " kenetli değil");
    docked_.erase(it);
    return ok_status();
}

Status Station::set_crew(int n) {
    if (n < 0) return make_error(ErrorCode::InvalidArgument, "Negatif mürettebat");
    if (n > crew_capacity()) return make_error(ErrorCode::Infeasible, "Yaşam kapasitesi " + std::to_string(crew_capacity()) + " kişi");
    crew_ = n;
    return ok_status();
}

void Station::resupply(double o2, double w, double f, double p) {
    o2_kg_ += std::max(0.0, o2);
    water_kg_ += std::max(0.0, w);
    food_kg_ += std::max(0.0, f);
    prop_kg_ += std::max(0.0, p);
}

double Station::days_of_supplies() const {
    if (crew_ == 0) return 1e9;
    const double o2 = o2_kg_ / (crew_ * kO2PerCrewDay);
    const double food = food_kg_ / (crew_ * kFoodPerCrewDay);
    const double water = kWaterPerCrewDay > 0 ? water_kg_ / (crew_ * std::max(0.05, kWaterPerCrewDay)) : 1e9;
    return std::min({o2, food, water});
}

TickReport Station::advance_days(double days, double solar) {
    TickReport r;
    if (deorbited_ || days <= 0) return r;
    // sürüklenme: günlük adımlarla
    const double m = mass_t() * 1000.0;
    const int steps = std::max(1, static_cast<int>(std::ceil(days)));
    const double dt = days * 86400.0 / steps;
    for (int i = 0; i < steps && body_.atmosphere; ++i) {
        const double a = body_.radius_m + altitude_m_;
        const double rho = thermosphere_density(altitude_m_, solar);
        const double da = -rho * kCd * drag_area_m2() / m * std::sqrt(body_.mu * a) * dt;
        altitude_m_ += da;
        r.altitude_loss_m -= da;
        if (altitude_m_ < 150e3) {   // ~150 km altında hızlı yeniden giriş
            deorbited_ = true;
            r.warnings.push_back("İstasyon atmosfere girdi");
            break;
        }
    }
    // sarf malzemesi
    r.o2_used_kg = crew_ * kO2PerCrewDay * days;
    r.water_used_kg = crew_ * kWaterPerCrewDay * days;
    const double food = crew_ * kFoodPerCrewDay * days;
    o2_kg_ = std::max(0.0, o2_kg_ - r.o2_used_kg);
    water_kg_ = std::max(0.0, water_kg_ - r.water_used_kg);
    food_kg_ = std::max(0.0, food_kg_ - food);
    r.power_kw = power_kw();
    if (r.power_kw < 0) r.warnings.push_back("Enerji açığı: güneş paneli kafesi ekle");
    if (crew_ > 0 && days_of_supplies() < 30) r.warnings.push_back("Sarf malzemesi 30 günden az: ikmal görevi planla");
    if (body_.atmosphere && altitude_m_ < 370e3) r.warnings.push_back("İrtifa düşük: yeniden itki gerekli");
    return r;
}

Station::Reboost Station::reboost(double target, double isp, bool apply) {
    Reboost b{0, 0, false, ""};
    if (deorbited_) {
        b.note = "İstasyon yok";
        return b;
    }
    const double a = body_.radius_m + altitude_m_;
    const double v = std::sqrt(body_.mu / a);
    b.dv_ms = std::fabs(v / (2.0 * a) * (target - altitude_m_));
    const double m = mass_t() * 1000.0;
    b.propellant_kg = m * (1.0 - std::exp(-b.dv_ms / (isp * kG0)));
    if (b.propellant_kg > prop_kg_) {
        b.note = "Yetersiz yakıt: " + std::to_string(static_cast<int>(b.propellant_kg)) + " kg gerekli";
        return b;
    }
    if (apply) {
        prop_kg_ -= b.propellant_kg;
        altitude_m_ = target;
    }
    b.done = true;
    return b;
}

json::Value Station::to_json() const {
    json::Value v = json::Value::object();
    v.set("name", name_);
    v.set("mu", body_.mu);
    v.set("radius", body_.radius_m);
    v.set("atm", body_.atmosphere);
    v.set("alt", altitude_m_);
    json::Value m = json::Value::array();
    for (auto k : modules_) m.push(static_cast<int>(k));
    v.set("modules", m);
    json::Value d = json::Value::array();
    for (const auto& x : docked_) {
        json::Value o = json::Value::object();
        o.set("port", x.port);
        o.set("name", x.name);
        o.set("mass", x.mass_t);
        d.push(o);
    }
    v.set("docked", d);
    v.set("crew", crew_);
    v.set("o2", o2_kg_);
    v.set("water", water_kg_);
    v.set("food", food_kg_);
    v.set("prop", prop_kg_);
    v.set("deorbited", deorbited_);
    return v;
}

Result<Station> Station::from_json(const json::Value& v) {
    Station s(v["name"].as_string(), {v["mu"].as_number(3.986004418e14), v["radius"].as_number(6.371e6), v["atm"].as_bool(true)}, v["alt"].as_number(400e3));
    for (const auto& m : v["modules"].as_array()) {
        const int k = m.as_int(-1);
        if (k < 0 || k > static_cast<int>(ModuleKind::Propulsion)) return make_error(ErrorCode::Parse, "Geçersiz istasyon modülü");
        s.modules_.push_back(static_cast<ModuleKind>(k));
    }
    for (const auto& o : v["docked"].as_array()) s.docked_.push_back({o["port"].as_int(), o["name"].as_string(), o["mass"].as_number()});
    s.crew_ = v["crew"].as_int();
    s.o2_kg_ = v["o2"].as_number();
    s.water_kg_ = v["water"].as_number();
    s.food_kg_ = v["food"].as_number();
    s.prop_kg_ = v["prop"].as_number();
    s.deorbited_ = v["deorbited"].as_bool();
    return s;
}

Station iss_like() {
    Station s("Kapı İstasyonu", earth(), 415e3);
    for (auto k : {ModuleKind::Propulsion, ModuleKind::Node, ModuleKind::Habitat, ModuleKind::Lab, ModuleKind::Lab, ModuleKind::Node, ModuleKind::Habitat,
                   ModuleKind::Airlock, ModuleKind::Cupola, ModuleKind::Storage, ModuleKind::Node, ModuleKind::Lab, ModuleKind::DockingPort,
                   ModuleKind::DockingPort, ModuleKind::Node, ModuleKind::Storage, ModuleKind::Habitat})
        (void)s.add_module(k);
    for (int i = 0; i < 8; ++i) (void)s.add_module(ModuleKind::SolarTruss);
    for (int i = 0; i < 9; ++i) (void)s.add_module(ModuleKind::Storage);
    s.resupply(800, 2000, 1500, 5000);
    (void)s.set_crew(7);
    return s;
}

}  // namespace kozmo::station

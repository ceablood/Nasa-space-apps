#include "kozmo/spacecraft.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace kozmo::craft {

namespace {
constexpr double kG0 = 9.80665;
constexpr double kPi = 3.14159265358979323846;
constexpr double kO2PerPersonHour = 0.84 / 24.0;   // kg
std::string f1(double v) {
    char b[32];
    std::snprintf(b, sizeof(b), "%.1f", v);
    return b;
}
}  // namespace

const char* to_string(PartKind k) {
    switch (k) {
        case PartKind::Hull: return "Gövde";
        case PartKind::Cockpit: return "Kokpit";
        case PartKind::Engine: return "Motor";
        case PartKind::Tank: return "Yakıt tankı";
        case PartKind::Rcs: return "RCS iticisi";
        case PartKind::SolarPanel: return "Güneş paneli";
        case PartKind::Battery: return "Batarya";
        case PartKind::Sensor: return "Sensör";
        case PartKind::Radar: return "Radar";
        case PartKind::Science: return "Bilimsel cihaz";
        case PartKind::Cargo: return "Kargo modülü";
        case PartKind::LifeSupport: return "Yaşam destek";
        case PartKind::LandingGear: return "İniş takımı";
        case PartKind::RoboticArm: return "Robot kol";
        case PartKind::Comms: return "İletişim";
        case PartKind::HeatShield: return "Isı kalkanı";
        case PartKind::Wing: return "Kanat";
        case PartKind::Cabin: return "Mürettebat kabini";
    }
    return "?";
}

const char* to_string(CraftClass c) {
    switch (c) {
        case CraftClass::Exploration: return "Keşif";
        case CraftClass::Transport: return "Taşıma";
        case CraftClass::Research: return "Araştırma";
        case CraftClass::Construction: return "İnşa ve bakım";
        case CraftClass::Lander: return "İniş aracı";
        case CraftClass::Special: return "Özel";
    }
    return "?";
}

const char* to_string(Feature f) {
    switch (f) {
        case Feature::Navigation: return "Navigasyon";
        case Feature::Radar: return "Radar";
        case Feature::Autopilot: return "Otomatik pilot";
        case Feature::Targeting: return "Hedef belirleme";
        case Feature::FaultDisplay: return "Sistem hata ekranı";
        case Feature::HoloMap: return "Holografik harita";
        case Feature::LandingAssist: return "Otomatik iniş desteği";
        case Feature::PowerDistribution: return "Enerji dağıtımı";
        case Feature::MultiSensor: return "Çoklu sensör";
        case Feature::DockingAssist: return "Kenetlenme desteği";
        case Feature::NovaLink: return "NOVA bağlantısı";
        case Feature::AutonomousSystems: return "Otonom sistem yönetimi";
        case Feature::ScienceScan: return "Bilimsel tarama";
        case Feature::ThreatAnalysis: return "Tehdit analizi";
    }
    return "?";
}

bool cockpit_has(CockpitLevel level, Feature f) {
    const int l = static_cast<int>(level);
    switch (f) {
        case Feature::Navigation: case Feature::Radar: return l >= 1;
        case Feature::Autopilot: case Feature::Targeting: case Feature::FaultDisplay: return l >= 2;
        case Feature::HoloMap: case Feature::LandingAssist: case Feature::PowerDistribution: case Feature::MultiSensor:
        case Feature::DockingAssist: return l >= 3;
        case Feature::NovaLink: case Feature::AutonomousSystems: case Feature::ScienceScan: case Feature::ThreatAnalysis: return l >= 4;
    }
    return false;
}

const char* to_string(FlightMode m) {
    switch (m) {
        case FlightMode::Manual: return "Manuel";
        case FlightMode::Assisted: return "Destekli";
        case FlightMode::Autopilot: return "Otomatik pilot";
        case FlightMode::LandingAssist: return "İniş desteği";
        case FlightMode::DockingAssist: return "Kenetlenme desteği";
        case FlightMode::Emergency: return "Acil durum";
    }
    return "?";
}

const char* to_string(FlightPhase p) {
    switch (p) {
        case FlightPhase::Landed: return "Yüzeyde";
        case FlightPhase::Flying: return "Uçuşta";
        case FlightPhase::Crashed: return "Çarptı";
        case FlightPhase::Orbit: return "Yörüngede";
    }
    return "?";
}

const char* to_string(Tier t) {
    switch (t) {
        case Tier::V1Basic: return "V1 Temel";
        case Tier::V2Advanced: return "V2 Gelişmiş";
        case Tier::V3Professional: return "V3 Profesyonel";
        case Tier::V4Experimental: return "V4 Deneysel";
    }
    return "?";
}

const char* to_string(Fault f) {
    switch (f) {
        case Fault::EngineFailure: return "Motor arızası";
        case Fault::FuelLeak: return "Yakıt sızıntısı";
        case Fault::CabinDepressurization: return "Kabin basıncı kaybı";
        case Fault::OxygenLow: return "Oksijen düşük";
        case Fault::PowerFailure: return "Elektrik kesintisi";
        case Fault::NavigationFailure: return "Navigasyon arızası";
        case Fault::Overheat: return "Aşırı ısınma";
        case Fault::CollisionDamage: return "Çarpışma hasarı";
        case Fault::LandingGearFailure: return "İniş takımı arızası";
    }
    return "?";
}

const std::vector<PartSpec>& parts() {
    // anahtar, ad, tür, kütle t, güç kW, kapasite, itki kN, Isp s, kokpit, ısı kW/m^2, araştırma, deneysel
    static const std::vector<PartSpec> k = {
        {"hull_light", "Hafif Al-Li gövde (10 yuva)", PartKind::Hull, 2.0, 0, 10},
        {"hull_modular", "Modüler gövde (16 yuva)", PartKind::Hull, 4.0, 0, 16},
        {"hull_heavy", "Ağır gövde, Whipple kalkanlı (20 yuva)", PartKind::Hull, 6.5, 0, 20},
        {"cockpit_v1", "Kokpit V1 — Temel (analog)", PartKind::Cockpit, 0.8, -0.5, 2, 0, 0, 1},
        {"cockpit_v2", "Kokpit V2 — Gelişmiş (dijital)", PartKind::Cockpit, 1.0, -1.0, 2, 0, 0, 2},
        {"cockpit_v3", "Kokpit V3 — Profesyonel (çoklu ekran)", PartKind::Cockpit, 1.2, -1.5, 2, 0, 0, 3, 0, "avionics"},
        {"cockpit_v4", "Kokpit V4 — Deneysel (NOVA entegre)", PartKind::Cockpit, 1.5, -2.5, 2, 0, 0, 4, 0, "nova_link"},
        {"eng_hypergolic", "Hipergolik iniş motoru (Apollo LM sınıfı)", PartKind::Engine, 0.18, -0.1, 0, 45, 311},
        {"eng_methalox_lander", "Metan/LOX kısılabilir iniş motoru", PartKind::Engine, 0.6, -0.2, 0, 100, 355, 0, 0, "methalox"},
        {"eng_hydrolox", "Hidrojen/LOX motor (RL10 sınıfı)", PartKind::Engine, 0.3, -0.2, 0, 110, 465, 0, 0, "cryo"},
        {"eng_ion", "İyon itici (NEXT sınıfı)", PartKind::Engine, 0.06, -7.0, 0, 0.000236, 4190, 0, 0, "ion"},
        {"eng_ntr", "Nükleer termal (NERVA sınıfı)", PartKind::Engine, 18.0, 0, 0, 333, 841, 0, 0, "nuclear"},
        {"eng_fusion", "Füzyon sürücü (KURGUSAL)", PartKind::Engine, 30.0, 0, 0, 50, 20000, 0, 0, "fusion", true},
        {"tank_small", "Küçük tank (4 t)", PartKind::Tank, 0.35, 0, 4},
        {"tank_medium", "Orta tank (10 t)", PartKind::Tank, 0.8, 0, 10},
        {"tank_large", "Büyük tank (25 t)", PartKind::Tank, 1.8, 0, 25},
        {"rcs", "RCS iticileri (Draco sınıfı 4x400 N)", PartKind::Rcs, 0.15, -0.1, 0, 1.6, 300},
        {"solar_panel", "Güneş paneli (8 kW @1 AU)", PartKind::SolarPanel, 0.25, 8.0, 0},
        {"battery", "Li-iyon batarya (60 kWh)", PartKind::Battery, 0.4, 0, 60},
        {"sensor_suite", "Sensör paketi", PartKind::Sensor, 0.1, -0.3, 0},
        {"landing_radar", "İniş radarı", PartKind::Radar, 0.08, -0.5, 0},
        {"science_lab", "Bilimsel laboratuvar", PartKind::Science, 1.2, -3.0, 0},
        {"cargo_bay", "Kargo modülü (10 t)", PartKind::Cargo, 1.0, 0, 10},
        {"life_support", "Yaşam destek (ECLSS, 4 kişi)", PartKind::LifeSupport, 1.5, -4.0, 4},
        {"landing_legs", "İniş takımı", PartKind::LandingGear, 0.6, 0, 0},
        {"robotic_arm", "Robot kol", PartKind::RoboticArm, 0.5, -1.0, 0},
        {"comms_hga", "Yüksek kazançlı anten", PartKind::Comms, 0.1, -0.2, 0},
        {"heat_shield", "PICA ısı kalkanı", PartKind::HeatShield, 1.0, 0, 0, 0, 0, 0, 10000.0},
        {"wings", "Kanatlar (atmosferde süzülme)", PartKind::Wing, 1.5, 0, 0},
        {"crew_cabin", "Mürettebat kabini (4 koltuk, uyku/yemek/tuvalet)", PartKind::Cabin, 2.0, -1.0, 4},
    };
    return k;
}

Result<const PartSpec*> find_part(const std::string& key) {
    for (const auto& p : parts())
        if (p.key == key) return &p;
    return make_error(ErrorCode::NotFound, "Bilinmeyen parça: " + key);
}

Spacecraft::Spacecraft(std::string id, std::string model, CraftClass cls, int slots)
    : id_(std::move(id)), model_(std::move(model)), cls_(cls), slots_(slots) {}

bool Spacecraft::has_fault(Fault f) const { return std::find(faults_.begin(), faults_.end(), f) != faults_.end(); }
void Spacecraft::clear_fault(Fault f) { faults_.erase(std::remove(faults_.begin(), faults_.end(), f), faults_.end()); }

Status Spacecraft::install(const std::string& key, const std::vector<std::string>& unlocked) {
    auto p = find_part(key);
    if (!p) return p.error();
    const PartSpec& s = *p.value();
    if (!s.research.empty() && std::find(unlocked.begin(), unlocked.end(), s.research) == unlocked.end())
        return make_error(ErrorCode::Locked, s.name + " için araştırma gerekli: " + s.research);
    if (phase_ == FlightPhase::Flying) return make_error(ErrorCode::Infeasible, "Uçuş sırasında parça değiştirilemez");
    if (s.kind == PartKind::Hull) {
        for (const auto& q : parts_)
            if (find_part(q.key).value()->kind == PartKind::Hull) return make_error(ErrorCode::Infeasible, "Araçta zaten gövde var");
        slots_ = static_cast<int>(s.capacity);
    } else if (s.kind == PartKind::Cockpit) {
        for (const auto& q : parts_)
            if (find_part(q.key).value()->kind == PartKind::Cockpit) return make_error(ErrorCode::Infeasible, "Araçta zaten kokpit var");
    }
    if (s.kind != PartKind::Hull && specs().slots_used >= slots_) return make_error(ErrorCode::Infeasible, "Gövdede boş yuva yok");
    parts_.push_back({key});
    if (s.kind == PartKind::Battery) battery_kwh_ += s.capacity;
    return ok_status();
}

Status Spacecraft::remove(std::size_t i) {
    if (i >= parts_.size()) return make_error(ErrorCode::InvalidArgument, "Geçersiz parça");
    if (phase_ == FlightPhase::Flying) return make_error(ErrorCode::Infeasible, "Uçuş sırasında parça değiştirilemez");
    parts_.erase(parts_.begin() + static_cast<long>(i));
    const Specs s = specs();
    fuel_t_ = std::min(fuel_t_, s.fuel_capacity_t);
    battery_kwh_ = std::min(battery_kwh_, s.battery_kwh);
    return ok_status();
}

CockpitLevel Spacecraft::cockpit() const {
    for (const auto& q : parts_) {
        const PartSpec& s = *find_part(q.key).value();
        if (s.kind == PartKind::Cockpit && q.health > 0.2 && power_ok_) return static_cast<CockpitLevel>(s.cockpit_level);
        if (s.kind == PartKind::Cockpit) return CockpitLevel::Basic;   // hasarlı/elektriksiz: yalnız analog yedek
    }
    return CockpitLevel::None;
}

Tier Spacecraft::tier() const {
    // V2: çoklu motor ya da dijital kokpit; V3: modüler/ağır gövde + yaşam desteği + kenetlenme donanımı (RCS, V3 kokpit);
    // V4: NOVA entegre kokpit ya da yeni nesil itki (iyon, nükleer termal, kurgusal füzyon)
    int engines = 0;
    bool modular = false, ls = false, rcs = false, advanced = false;
    for (const auto& q : parts_) {
        const PartSpec& p = *find_part(q.key).value();
        engines += p.kind == PartKind::Engine;
        modular |= p.key == "hull_modular" || p.key == "hull_heavy";
        ls |= p.kind == PartKind::LifeSupport;
        rcs |= p.kind == PartKind::Rcs;
        advanced |= p.key == "eng_ion" || p.key == "eng_ntr" || p.key == "eng_fusion";
    }
    int lvl = 0;
    for (const auto& q : parts_) {
        const PartSpec& p = *find_part(q.key).value();
        if (p.kind == PartKind::Cockpit) lvl = p.cockpit_level;
    }
    if (lvl >= 4 || advanced) return Tier::V4Experimental;
    if (modular && ls && rcs && lvl >= 3) return Tier::V3Professional;
    if (engines >= 2 || lvl >= 2) return Tier::V2Advanced;
    return Tier::V1Basic;
}

double Spacecraft::part_health(PartKind k) const {
    double h = 0;
    int n = 0;
    for (const auto& q : parts_)
        if (find_part(q.key).value()->kind == k) {
            h += q.health;
            ++n;
        }
    return n ? h / n : 0.0;
}

bool Spacecraft::has_part(PartKind k) const {
    return std::any_of(parts_.begin(), parts_.end(), [&](const PartState& q) { return find_part(q.key).value()->kind == k; });
}

Specs Spacecraft::specs() const {
    Specs s;
    double thrust_isp = 0;
    for (const auto& q : parts_) {
        const PartSpec& p = *find_part(q.key).value();
        s.dry_t += p.mass_t;
        if (p.kind != PartKind::Hull) ++s.slots_used;
        if (p.power_kw > 0) s.power_gen_kw += p.power_kw * q.health;
        else s.power_use_kw -= p.power_kw;
        switch (p.kind) {
            case PartKind::Hull: s.slots_total = static_cast<int>(p.capacity); break;
            case PartKind::Tank: s.fuel_capacity_t += p.capacity; break;
            case PartKind::Cargo: s.cargo_capacity_t += p.capacity; break;
            case PartKind::Battery: s.battery_kwh += p.capacity; break;
            case PartKind::Cabin: s.crew_capacity += static_cast<int>(p.capacity); break;
            case PartKind::Cockpit: s.crew_capacity += static_cast<int>(p.capacity); s.cockpit = static_cast<CockpitLevel>(p.cockpit_level); break;
            case PartKind::LifeSupport: s.life_support_crew += static_cast<int>(p.capacity * q.health + 0.5); break;
            case PartKind::Engine:
                if (q.enabled) {
                    s.thrust_kn += p.thrust_kn * q.health;
                    thrust_isp += p.thrust_kn * q.health / p.isp_s;
                }
                break;
            case PartKind::HeatShield: s.heat_limit_kw_m2 = std::max(s.heat_limit_kw_m2, p.heat_limit_kw_m2 * q.health); break;
            default: break;
        }
    }
    s.isp_s = thrust_isp > 0 ? s.thrust_kn / thrust_isp : 0.0;
    s.cargo_t = cargo_t_;
    s.wet_t = s.dry_t + fuel_t_ + cargo_t_;
    s.max_t = s.dry_t + s.fuel_capacity_t + s.cargo_capacity_t;
    s.dv_ms = s.isp_s > 0 && s.wet_t > 0 ? s.isp_s * kG0 * std::log(s.wet_t / (s.dry_t + cargo_t_)) : 0.0;
    s.atmosphere_capable = has_part(PartKind::HeatShield) || has_part(PartKind::Wing);
    s.can_land = has_part(PartKind::LandingGear) && s.thrust_kn > 0;
    // boyut tahmini (mühendislik yaklaşımı): 4.5 m çaplı gövde, yakıt ~1 t/m^3 (metan/LOX ~0.83), kuru hacim 0.25 t/m^3
    s.width_m = has_part(PartKind::Wing) ? 12.0 : 4.5;
    s.height_m = 4.5 + (has_part(PartKind::LandingGear) ? 1.5 : 0.0);
    s.length_m = 3.0 + (s.fuel_capacity_t / 0.83 + s.dry_t / 0.25) / (kPi * 2.25 * 2.25);
    if (s.cockpit == CockpitLevel::None) s.problems.push_back("Kokpit yok: araç kontrol edilemez");
    if (s.thrust_kn <= 0) s.problems.push_back("Ana motor yok");
    if (crew_ > s.crew_capacity) s.problems.push_back("Mürettebat koltuk sayısını aşıyor");
    if (crew_ > 0 && crew_ > s.life_support_crew && !has_part(PartKind::LifeSupport))
        s.problems.push_back("Yaşam destek modülü yok: kabin oksijeni yalnız depolanan kadar");
    if (s.power_use_kw > s.power_gen_kw && s.battery_kwh <= 0) s.problems.push_back("Enerji açığı ve batarya yok");
    if (!s.can_land) s.problems.push_back("İniş takımı yok: gezegene inemez");
    if (s.slots_used > s.slots_total) s.problems.push_back("Yuva sayısı aşıldı");
    for (const auto& q : parts_)
        if (find_part(q.key).value()->experimental) s.problems.push_back(find_part(q.key).value()->name + ": kanıtlanmamış teknoloji (kurgusal)");
    return s;
}

void Spacecraft::refuel() { fuel_t_ = specs().fuel_capacity_t; }
void Spacecraft::set_fuel(double t) { fuel_t_ = std::clamp(t, 0.0, specs().fuel_capacity_t); }
void Spacecraft::load_cargo(double t) { cargo_t_ = std::clamp(t, 0.0, specs().cargo_capacity_t); }

Status Spacecraft::sit() {
    if (cockpit() == CockpitLevel::None) return make_error(ErrorCode::Infeasible, "Kokpit yok");
    seated_ = true;
    return ok_status();
}

Status Spacecraft::stand() {
    if (phase_ == FlightPhase::Flying && mode_ == FlightMode::Manual)
        return make_error(ErrorCode::Infeasible, "Manuel uçuşta koltuktan kalkılamaz: önce otomatik pilot/iniş desteği aç");
    seated_ = false;
    return ok_status();
}

Status Spacecraft::set_engines(bool on) {
    if (!on) {
        engines_on_ = false;
        return ok_status();
    }
    if (!seated_) return make_error(ErrorCode::Infeasible, "Motorları çalıştırmak için kokpitte otur");
    if (!power_ok_) return make_error(ErrorCode::Infeasible, "Elektrik yok: ateşleme sistemi çalışmıyor");
    if (fuel_t_ <= 0) return make_error(ErrorCode::Infeasible, "Yakıt yok");
    if (specs().thrust_kn <= 0) return make_error(ErrorCode::Infeasible, "Çalışır motor yok");
    if (has_fault(Fault::EngineFailure)) return make_error(ErrorCode::Infeasible, "Motor arızalı: önce acil prosedürü uygula");
    engines_on_ = true;
    return ok_status();
}

void Spacecraft::set_throttle(double t) { throttle_ = std::clamp(t, 0.0, 1.0); }
void Spacecraft::set_pitch_deg(double p) { pitch_deg_ = std::clamp(p, 0.0, 180.0); }

Status Spacecraft::set_mode(FlightMode m) {
    const CockpitLevel c = cockpit();
    Status st = ok_status();
    switch (m) {
        case FlightMode::Manual: break;
        case FlightMode::Assisted: if (!cockpit_has(c, Feature::Navigation)) st = make_error(ErrorCode::Infeasible, "Destekli uçuş için navigasyon gerekli"); break;
        case FlightMode::Autopilot: if (!cockpit_has(c, Feature::Autopilot)) st = make_error(ErrorCode::Infeasible, "Otomatik pilot için Kokpit V2+ gerekli"); break;
        case FlightMode::LandingAssist:
            if (!cockpit_has(c, Feature::LandingAssist)) st = make_error(ErrorCode::Infeasible, "İniş desteği için Kokpit V3+ gerekli");
            else if (!has_part(PartKind::Radar)) st = make_error(ErrorCode::Infeasible, "İniş desteği için iniş radarı gerekli");
            break;
        case FlightMode::DockingAssist:
            if (!cockpit_has(c, Feature::DockingAssist)) st = make_error(ErrorCode::Infeasible, "Kenetlenme desteği için Kokpit V3+ gerekli");
            else if (target_.find("istasyon") == std::string::npos) st = make_error(ErrorCode::Infeasible, "Kenetlenme hedefi (istasyon) seçilmedi");
            break;
        case FlightMode::Emergency: break;   // her zaman açılabilir (analog yedek)
    }
    if (!st.ok()) return st;
    if ((m == FlightMode::Autopilot || m == FlightMode::LandingAssist || m == FlightMode::DockingAssist) && !nav_ok_)
        return make_error(ErrorCode::Infeasible, "Navigasyon arızalı: yalnız manuel/acil mod");
    mode_ = m;
    return ok_status();
}

Status Spacecraft::set_target(const std::string& name) {
    if (!cockpit_has(cockpit(), Feature::Targeting)) return make_error(ErrorCode::Infeasible, "Hedef belirleme için Kokpit V2+ gerekli");
    target_ = name;
    return ok_status();
}

std::string Spacecraft::window_view(const challenge::PlanetEnvironment& e) const {
    std::string s;
    if (phase_ == FlightPhase::Landed) {
        s = e.name + " yüzeyi. ";
        if (e.pressure_kpa < 0.1) s += "Kapkara gökyüzü, yıldızlar gündüz bile görünür; gölgeler keskin. ";
        else if (e.key == "mars") s += "Toz yüklü soluk karamel gökyüzü; gün batımı mavimsi. ";
        else if (e.key == "venus") s += "Turuncu, kalın bulut örtüsü; ufuk bükülmüş görünür. ";
        else s += "Atmosferli gökyüzü. ";
    } else {
        s = e.name + " üzerinde " + f1(alt_ / 1000.0) + " km. ";
        if (alt_ > 50000) s += "Ufuk belirgin biçimde kavisli. ";
    }
    if (cabin_lights_ == 0) s += "Kabin karanlık: dış görüş en iyi.";
    return s;
}

void Spacecraft::place_landed() {
    phase_ = FlightPhase::Landed;
    alt_ = vv_ = vh_ = 0;
}

void Spacecraft::place_in_flight(double altitude_m, double horizontal_ms, double vertical_ms) {
    phase_ = FlightPhase::Flying;
    alt_ = altitude_m;
    vh_ = horizontal_ms;
    vv_ = vertical_ms;
    max_heat_kw_m2_ = 0;
}

double Spacecraft::mass_kg() const { return (specs().dry_t + fuel_t_ + cargo_t_) * 1000.0; }

double Spacecraft::available_thrust_n() const {
    if (!engines_on_ || fuel_t_ <= 0 || has_fault(Fault::EngineFailure)) return 0.0;
    return specs().thrust_kn * 1000.0;
}

double Spacecraft::effective_isp() const { return specs().isp_s; }

void Spacecraft::landing_guidance(double g_eff, double amax, double& thr, double& pitch) const {
    // iki eksenli güdüm: dikey hız referansı (kalan irtifada güvenli frenleme payı) + yatay hızı sıfırlama
    const double h = std::max(0.0, alt_);
    const double brake = std::max(0.3, 0.55 * (amax - std::max(0.0, g_eff)));
    const double v_sqrt = -std::sqrt(2.0 * brake * std::max(0.0, h - 3.0)) - 1.2;   // sabit frenleme, son 3 m ~1.2 m/s
    double v_ref = v_sqrt;
    // yatay hız sıfırlanmadan alçalma: yere varış süresi yatay frenleme süresinden uzun olmalı
    const double t_h = std::fabs(vh_) / std::max(0.1, amax * 0.8);
    if (std::fabs(vh_) > 1.0) v_ref = std::max(v_ref, -h / (t_h * 1.3 + 8.0));
    if (std::fabs(vh_) < 2.0) v_ref = std::min(v_ref, -1.2);   // asılı kalma (yakıt israfı) yok
    // ileri besleme: karekök profilinde referans hız sabit 'brake' ivmesiyle küçülür
    const double ff = (v_ref == v_sqrt && vv_ < 0 && h > 3.0) ? brake : 0.0;
    double av = (v_ref - vv_) / (h < 200 ? 0.6 : 1.5) + g_eff + ff;
    double ah = -vh_ / 3.0;
    av = std::max(0.0, av);
    if (av >= amax) {
        av = amax;
        ah = 0;
    } else {
        const double room = std::sqrt(amax * amax - av * av);
        ah = std::clamp(ah, -room, room);
    }
    const double a = std::sqrt(av * av + ah * ah);
    thr = std::clamp(a / amax, 0.0, 1.0);
    pitch = std::atan2(av, ah) * 180.0 / kPi;   // 0 ileri yatay, 90 yukarı, 180 geri
}

void Spacecraft::step(double dt, const challenge::PlanetEnvironment& e, Rng& rng) {
    if (phase_ == FlightPhase::Crashed || phase_ == FlightPhase::Orbit || dt <= 0) return;   // yörüngede kararlı (2B model)
    const double m = mass_kg();
    const double r = (e.radius_km * 1000.0 + alt_);
    const double g_eff = e.gravity_ms2 * std::pow(e.radius_km * 1000.0 / r, 2) - vh_ * vh_ / r;
    const double fmax = available_thrust_n();
    const double amax = fmax / m;
    // mod -> itki komutu
    double thr = throttle_, pitch = pitch_deg_;
    const double R0 = e.radius_km * 1000.0;
    const double v_circ = std::sqrt(e.gravity_ms2 * R0 * R0 / r);
    if (fmax > 0 && mode_ == FlightMode::Autopilot && orbit_target_m_ > 0) {
        // kalkış güdümü: dikey yükseliş, sonra hedef irtifayı tutarken yatayda yörünge hızına ivmelen
        if (alt_ < 100.0) {
            thr = 1.0;
            pitch = 90.0;
        } else {
            const double v_up = std::clamp((orbit_target_m_ - alt_) / 30.0, -20.0, 80.0);
            const double av = std::clamp((v_up - vv_) / 2.0 + g_eff, -amax, amax);   // gerekirse ufkun altına yönel
            const double ah = std::clamp((v_circ - vh_) / 2.0, 0.0, std::sqrt(std::max(0.0, amax * amax - av * av)));
            thr = std::clamp(std::sqrt(av * av + ah * ah) / amax, 0.0, 1.0);
            pitch = std::atan2(av, ah) * 180.0 / kPi;
        }
    } else if (fmax > 0 && phase_ == FlightPhase::Flying) {
        if (mode_ == FlightMode::LandingAssist || mode_ == FlightMode::Emergency) landing_guidance(g_eff, amax, thr, pitch);
        else if (mode_ == FlightMode::Autopilot) {
            // irtifa ve yatay hız tutma
            const double av = std::max(0.0, -vv_ / 2.0 + g_eff);
            const double ah = -vh_ / 20.0;
            thr = std::clamp(std::sqrt(av * av + ah * ah) / amax, 0.0, 1.0);
            pitch = std::atan2(av, ah) * 180.0 / kPi;
        } else if (mode_ == FlightMode::Assisted) {
            thr = std::min(thr, 3.0 * kG0 / std::max(1e-6, amax));   // 3 g sınırı
        }
    }
    if (has_fault(Fault::Overheat)) thr = std::min(thr, 0.5);
    double F = fmax * thr;
    // yakıt
    const double isp = effective_isp();
    if (F > 0 && isp > 0) {
        const double burn = F / (isp * kG0) * dt / 1000.0;
        if (burn >= fuel_t_) {
            F *= fuel_t_ / burn;
            fuel_t_ = 0;
            engines_on_ = false;
        } else {
            fuel_t_ -= burn;
        }
    }
    for (const auto& q : parts_)
        if (q.leaking) fuel_t_ = std::max(0.0, fuel_t_ - 0.002 * dt);   // ~2 kg/s sızıntı
    // motor sıcaklığı
    const double eh = part_health(PartKind::Engine);
    const double target = 290.0 + 1100.0 * thr * (F > 0 ? 1.0 : 0.0) * (2.0 - eh);
    engine_temp_k_ += (target - engine_temp_k_) * std::min(1.0, dt / 20.0);
    if (engine_temp_k_ > 1600) {
        damage(PartKind::Engine, 0.01 * dt);
        if (!has_fault(Fault::Overheat)) faults_.push_back(Fault::Overheat);
    }
    if (phase_ == FlightPhase::Landed) {
        if (F * std::sin(pitch * kPi / 180.0) > m * e.gravity_ms2) phase_ = FlightPhase::Flying;
        else return;
    }
    // kuvvetler
    const double rad = pitch * kPi / 180.0;
    double ax = F / m * std::cos(rad), ay = F / m * std::sin(rad) - g_eff;
    const double rho = e.density_at(alt_);
    const double v = std::sqrt(vh_ * vh_ + vv_ * vv_);
    if (rho > 0 && v > 0) {
        const Specs s = specs();
        const double area = kPi * s.width_m * s.width_m / 4.0;
        const double drag = 0.5 * rho * v * v * 1.2 * area / m;
        ax -= drag * vh_ / v;
        ay -= drag * vv_ / v;
        // Sutton-Graves durma noktası ısı akısı (burun yarıçapı 2 m)
        const double k = e.molar_mass_gmol > 40 ? 1.9027e-4 : 1.7415e-4;
        const double q = k * std::sqrt(rho / 2.0) * v * v * v / 1000.0;   // kW/m^2
        max_heat_kw_m2_ = std::max(max_heat_kw_m2_, q);
        if (s.heat_limit_kw_m2 > 0) {
            if (q > s.heat_limit_kw_m2) damage(PartKind::HeatShield, 0.02 * dt);
        } else if (q > 300.0) {
            damage(PartKind::Hull, 0.02 * dt * q / 300.0);
        }
    }
    vh_ += ax * dt;
    vv_ += ay * dt;
    x_ += vh_ * dt;
    alt_ += vv_ * dt;
    if (orbit_target_m_ > 0 && alt_ >= orbit_target_m_ * 0.8 && vh_ >= v_circ * 0.999 && std::fabs(vv_) < 5.0) {
        phase_ = FlightPhase::Orbit;   // dairesel yörünge (yaklaşım: kalan dikey hız sönümlenir)
        vv_ = 0;
        engines_on_ = false;
        orbit_target_m_ = 0;
        mode_ = FlightMode::Manual;
        return;
    }
    (void)rng;   // rastgele arıza yalnız inject() ile (deterministik uçuş)
    if (alt_ <= 0) {
        alt_ = 0;
        touchdown_ms_ = std::sqrt(vv_ * vv_ + vh_ * vh_);
        const bool gear = has_part(PartKind::LandingGear) && gear_ok_ && part_health(PartKind::LandingGear) > 0.3;
        if (gear && vv_ > -3.0 && std::fabs(vh_) < 2.0) {
            phase_ = FlightPhase::Landed;
        } else if (vv_ > -8.0 && std::fabs(vh_) < 5.0) {
            phase_ = FlightPhase::Landed;
            damage(PartKind::LandingGear, 0.6);
            damage(PartKind::Hull, 0.1);
            if (!has_fault(Fault::LandingGearFailure)) faults_.push_back(Fault::LandingGearFailure);
        } else {
            phase_ = FlightPhase::Crashed;
            damage(PartKind::Hull, 1.0);
        }
        vv_ = vh_ = 0;
        engines_on_ = false;
    }
}

FlightPhase Spacecraft::fly_until_landed(const challenge::PlanetEnvironment& e, Rng& rng, double max_s, double dt) {
    for (double t = 0; t < max_s && phase_ == FlightPhase::Flying; t += dt) step(dt, e, rng);
    return phase_;
}

Status Spacecraft::launch_to_orbit(double alt_m) {
    if (phase_ != FlightPhase::Landed && phase_ != FlightPhase::Flying) return make_error(ErrorCode::Infeasible, "Kalkış için araç yüzeyde ya da uçuşta olmalı");
    if (!cockpit_has(cockpit(), Feature::Autopilot)) return make_error(ErrorCode::Infeasible, "Otomatik kalkış için Kokpit V2+ gerekli");
    if (!nav_ok_) return make_error(ErrorCode::Infeasible, "Navigasyon arızalı");
    if (alt_m < 5000) return make_error(ErrorCode::InvalidArgument, "Yörünge irtifası en az 5 km olmalı");
    auto st = set_engines(true);
    if (!st) return st;
    orbit_target_m_ = alt_m;
    mode_ = FlightMode::Autopilot;
    target_ = "yörünge";
    return ok_status();
}

FlightPhase Spacecraft::fly_until_orbit(const challenge::PlanetEnvironment& e, Rng& rng, double max_s, double dt) {
    for (double t = 0; t < max_s && (phase_ == FlightPhase::Flying || phase_ == FlightPhase::Landed) && orbit_target_m_ > 0; t += dt) {
        step(dt, e, rng);
        if (!engines_on_ && phase_ != FlightPhase::Orbit) break;   // yakıt bitti
    }
    return phase_;
}

Status Spacecraft::begin_docking(double range_m, double closing_ms) {
    if (phase_ != FlightPhase::Orbit) return make_error(ErrorCode::Infeasible, "Kenetlenme yalnız yörüngede");
    if (target_.find("istasyon") == std::string::npos) return make_error(ErrorCode::Infeasible, "Hedef olarak istasyon seç");
    if (!has_part(PartKind::Rcs)) return make_error(ErrorCode::Infeasible, "Kenetlenme için RCS iticileri gerekli");
    dock_ = {std::max(1.0, range_m), closing_ms, true, false};
    return ok_status();
}

void Spacecraft::step_docking(double dt) {
    if (!dock_.active || dock_.docked || dt <= 0) return;
    double rcs_n = 0, rcs_isp = 300;
    for (const auto& q : parts_) {
        const PartSpec& p = *find_part(q.key).value();
        if (p.kind == PartKind::Rcs) {
            rcs_n += p.thrust_kn * 1000.0 * q.health;
            rcs_isp = p.isp_s;
        }
    }
    const double amax = rcs_n / mass_kg();
    double a = 0;
    if (mode_ == FlightMode::DockingAssist && nav_ok_) {
        // yaklaşma koridoru: uzakta en çok 1 m/s, son metrelerde ~0.05 m/s (gerçek kenetlenmeler 0.03-0.1 m/s)
        const double want = std::clamp(dock_.range_m / 60.0, 0.05, 1.0);
        a = std::clamp((want - dock_.closing_ms) / 3.0, -amax, amax);
    } else {
        a = rcs_cmd_ * amax;
    }
    if (fuel_t_ > 0 && a != 0) fuel_t_ = std::max(0.0, fuel_t_ - std::fabs(a) * mass_kg() / (rcs_isp * kG0) * dt / 1000.0);
    else if (fuel_t_ <= 0) a = 0;
    dock_.closing_ms += a * dt;
    dock_.range_m -= dock_.closing_ms * dt;
    if (dock_.range_m <= 0) {
        if (dock_.closing_ms <= 0.15) {
            dock_.docked = true;
            dock_.range_m = 0;
            dock_.closing_ms = 0;
        } else {
            damage(PartKind::Hull, std::min(0.5, 0.1 * dock_.closing_ms));
            inject(Fault::CollisionDamage);
            dock_.range_m = 2.0;
            dock_.closing_ms = -0.1;    // geri sekme
        }
    }
}

void Spacecraft::tick_life_support(double dt) {
    const Specs s = specs();
    // enerji
    const double net = s.power_gen_kw - s.power_use_kw;
    if (power_ok_ || has_fault(Fault::PowerFailure)) {
        battery_kwh_ = std::clamp(battery_kwh_ + net * dt, 0.0, s.battery_kwh);
        if (net < 0 && battery_kwh_ <= 0) {
            power_ok_ = false;
            if (!has_fault(Fault::PowerFailure)) faults_.push_back(Fault::PowerFailure);
        }
    }
    // oksijen: tüketim + ECLSS geri kazanımı (elektrik varsa)
    o2_kg_ -= crew_ * kO2PerPersonHour * dt;
    if (power_ok_ && has_part(PartKind::LifeSupport)) {
        const double regen = std::min(crew_, s.life_support_crew) * kO2PerPersonHour * dt * 0.95;   // %95 geri kazanım
        o2_kg_ += regen;
    }
    o2_kg_ = std::max(0.0, o2_kg_);
    if (crew_ > 0 && o2_kg_ / (crew_ * 0.84) < 2.0 && !has_fault(Fault::OxygenLow)) faults_.push_back(Fault::OxygenLow);
    // kabin basıncı
    if (has_fault(Fault::CabinDepressurization)) cabin_kpa_ = std::max(0.0, cabin_kpa_ - leak_rate_kpa_h_ * dt);
}

void Spacecraft::damage(PartKind kind, double amount) {
    for (auto& q : parts_)
        if (find_part(q.key).value()->kind == kind) {
            q.health = std::clamp(q.health - amount, 0.0, 1.0);
            if (kind == PartKind::Tank && q.health < 0.6) {
                q.leaking = true;
                if (!has_fault(Fault::FuelLeak)) faults_.push_back(Fault::FuelLeak);
            }
            if (kind == PartKind::Hull && q.health < 0.7 && !has_fault(Fault::CabinDepressurization)) {
                faults_.push_back(Fault::CabinDepressurization);
                leak_rate_kpa_h_ = 30.0 * (1.0 - q.health);
            }
            if (kind == PartKind::Engine && q.health < 0.25 && !has_fault(Fault::EngineFailure)) faults_.push_back(Fault::EngineFailure);
            if (kind == PartKind::LandingGear && q.health < 0.3 && !has_fault(Fault::LandingGearFailure)) faults_.push_back(Fault::LandingGearFailure);
        }
}

void Spacecraft::inject(Fault f) {
    if (has_fault(f)) return;
    faults_.push_back(f);
    switch (f) {
        case Fault::EngineFailure: engines_on_ = false; break;
        case Fault::FuelLeak:
            for (auto& q : parts_)
                if (find_part(q.key).value()->kind == PartKind::Tank) { q.leaking = true; break; }
            break;
        case Fault::CabinDepressurization: leak_rate_kpa_h_ = 20.0; break;
        case Fault::PowerFailure: power_ok_ = false; break;
        case Fault::NavigationFailure: nav_ok_ = false; if (mode_ != FlightMode::Manual && mode_ != FlightMode::Emergency) mode_ = FlightMode::Manual; break;
        case Fault::Overheat: engine_temp_k_ = 1650; break;
        case Fault::CollisionDamage: damage(PartKind::Hull, 0.35); break;
        case Fault::LandingGearFailure: gear_ok_ = false; break;
        case Fault::OxygenLow: o2_kg_ = std::min(o2_kg_, crew_ * 0.84 * 1.5); break;
    }
}

std::vector<Warning> Spacecraft::warnings() const {
    std::vector<Warning> w;
    for (Fault f : faults_) {
        switch (f) {
            case Fault::EngineFailure: w.push_back({f, 3, "ANA MOTOR ARIZASI", "Motoru kapat, hasarı değerlendir, yeniden ateşlemeyi dene"}); break;
            case Fault::FuelLeak: w.push_back({f, 2, "YAKIT SIZINTISI", "Sızan tankı yalıt (yakıtın bir kısmı kaybedilir)"}); break;
            case Fault::CabinDepressurization: w.push_back({f, 3, "KABİN BASINCI DÜŞÜYOR " + f1(cabin_kpa_) + " kPa", "Kapakları mühürle, yamayı uygula, O2 ile yeniden basınçlandır"}); break;
            case Fault::OxygenLow: w.push_back({f, 3, "OKSİJEN DÜŞÜK " + f1(o2_kg_) + " kg", "Acil O2 tüpünü aç, mürettebat aktivitesini azalt"}); break;
            case Fault::PowerFailure: w.push_back({f, 3, "ELEKTRİK KESİNTİSİ", "Bataryaya geç, kritik olmayan yükleri kapat, yeniden başlat"}); break;
            case Fault::NavigationFailure: w.push_back({f, 2, "NAVİGASYON ARIZASI", "Navigasyon bilgisayarını yeniden başlat; o sırada manuel uçuş"}); break;
            case Fault::Overheat: w.push_back({f, 2, "MOTOR AŞIRI ISINDI " + f1(engine_temp_k_) + " K", "Gazı %50'ye düşür, soğumayı bekle"}); break;
            case Fault::CollisionDamage: w.push_back({f, 2, "ÇARPIŞMA HASARI", "Robot kol / EVA ile gövde yaması"}); break;
            case Fault::LandingGearFailure: w.push_back({f, 2, "İNİŞ TAKIMI ARIZASI", "Yedek mekanik açmayı kullan"}); break;
        }
    }
    if (part_health(PartKind::Hull) < 0.5) w.push_back({Fault::CollisionDamage, 3, "GÖVDE BÜTÜNLÜĞÜ %" + std::to_string(static_cast<int>(part_health(PartKind::Hull) * 100)), "Acil iniş veya tahliye"});
    if (!cockpit_has(cockpit(), Feature::FaultDisplay)) {
        // V1 kokpitte ayrıntılı hata ekranı yok: yalnız genel uyarı lambası
        for (auto& x : w) x.procedure = "(V1 kokpit: ayrıntı yok) " + x.procedure;
    }
    std::sort(w.begin(), w.end(), [](const Warning& a, const Warning& b) { return a.severity > b.severity; });
    return w;
}

Status Spacecraft::apply_procedure(Fault f) {
    if (!has_fault(f)) return make_error(ErrorCode::Infeasible, std::string(to_string(f)) + " etkin değil");
    switch (f) {
        case Fault::EngineFailure:
            engines_on_ = false;
            if (part_health(PartKind::Engine) < 0.25) return make_error(ErrorCode::Infeasible, "Motor çok hasarlı: yeniden ateşlenemez (tamir gerekli)");
            break;
        case Fault::FuelLeak:
            for (auto& q : parts_) {
                if (!q.leaking) continue;
                q.leaking = false;
                q.enabled = false;   // yalıtılan tank
                fuel_t_ *= 0.9;
            }
            break;
        case Fault::CabinDepressurization: {
            leak_rate_kpa_h_ = 0;
            const double need = (101.3 - cabin_kpa_) * 0.2;      // yaklaşık: 20 m^3 kabin, ~0.2 kg O2/kPa (oyun yaklaşımı)
            const double use = std::min(o2_kg_, need);
            o2_kg_ -= use;
            cabin_kpa_ = std::min(101.3, cabin_kpa_ + use / 0.2);
            break;
        }
        case Fault::OxygenLow:
            if (emergency_o2_used_) return make_error(ErrorCode::Infeasible, "Acil O2 tüpü zaten kullanıldı");
            emergency_o2_used_ = true;
            o2_kg_ += 20.0;
            break;
        case Fault::PowerFailure:
            if (battery_kwh_ <= 0 && specs().power_gen_kw <= 0) return make_error(ErrorCode::Infeasible, "Batarya boş ve üretim yok: yeniden başlatılamaz");
            power_ok_ = true;
            break;
        case Fault::NavigationFailure: nav_ok_ = true; break;
        case Fault::Overheat:
            throttle_ = std::min(throttle_, 0.5);
            if (engine_temp_k_ > 1400) return make_error(ErrorCode::Infeasible, "Motor hâlâ çok sıcak (" + f1(engine_temp_k_) + " K): bekle");
            break;
        case Fault::CollisionDamage:
            for (auto& q : parts_)
                if (find_part(q.key).value()->kind == PartKind::Hull) q.health = std::min(1.0, q.health + (has_part(PartKind::RoboticArm) ? 0.25 : 0.1));
            break;
        case Fault::LandingGearFailure:
            if (part_health(PartKind::LandingGear) < 0.2) return make_error(ErrorCode::Infeasible, "İniş takımı kırık: yedek açma işe yaramaz");
            gear_ok_ = true;
            break;
    }
    clear_fault(f);
    return ok_status();
}

Instruments Spacecraft::instruments() const {
    Instruments in{};
    const Specs s = specs();
    in.vertical_ms = vv_;
    in.horizontal_ms = vh_;
    in.speed_ms = std::sqrt(vv_ * vv_ + vh_ * vh_);
    in.altitude_m = alt_;
    in.fuel_t = fuel_t_;
    in.fuel_fraction = s.fuel_capacity_t > 0 ? fuel_t_ / s.fuel_capacity_t : 0.0;
    in.oxygen_kg = o2_kg_;
    in.oxygen_days = crew_ > 0 ? o2_kg_ / (crew_ * 0.84) : 0.0;
    in.engine_temp_k = engine_temp_k_;
    in.cabin_pressure_kpa = cabin_kpa_;
    in.power_kw_net = s.power_gen_kw - s.power_use_kw;
    in.battery_fraction = s.battery_kwh > 0 ? battery_kwh_ / s.battery_kwh : 0.0;
    in.shield_fraction = has_part(PartKind::HeatShield) ? part_health(PartKind::HeatShield) : 0.0;
    in.hull_fraction = part_health(PartKind::Hull);
    in.engine_fraction = has_fault(Fault::EngineFailure) ? 0.0 : part_health(PartKind::Engine);
    in.navigation = !nav_ok_ ? "NAV ARIZASI" : (target_.empty() ? "Hedef yok" : "Hedef: " + target_);
    if (cockpit_has(cockpit(), Feature::Radar) && power_ok_) {
        if (phase_ == FlightPhase::Flying) in.radar.push_back("Yüzey " + f1(alt_) + " m");
        if (!target_.empty()) in.radar.push_back(target_);
    }
    in.engines_on = engines_on_;
    in.seated = seated_;
    in.mode = mode_;
    in.throttle = throttle_;
    return in;
}

bool Spacecraft::can_exit(const challenge::PlanetEnvironment& e, bool has_suit) const {
    if (phase_ != FlightPhase::Landed) return false;
    if (seated_) return false;
    return e.key == "earth" || has_suit;
}

json::Value Spacecraft::to_json() const {
    json::Value v = json::Value::object();
    v.set("id", id_);
    v.set("model", model_);
    v.set("class", static_cast<int>(cls_));
    json::Value a = json::Value::array();
    for (const auto& q : parts_) {
        json::Value o = json::Value::object();
        o.set("key", q.key);
        o.set("health", q.health);
        o.set("enabled", q.enabled);
        o.set("leak", q.leaking);
        a.push(o);
    }
    v.set("parts", a);
    v.set("fuel", fuel_t_);
    v.set("cargo", cargo_t_);
    v.set("crew", crew_);
    v.set("phase", static_cast<int>(phase_));
    v.set("alt", alt_);
    v.set("x", x_);
    v.set("vv", vv_);
    v.set("vh", vh_);
    v.set("o2", o2_kg_);
    v.set("cabin", cabin_kpa_);
    v.set("battery", battery_kwh_);
    v.set("mode", static_cast<int>(mode_));
    v.set("target", target_);
    json::Value f = json::Value::array();
    for (Fault x : faults_) f.push(static_cast<int>(x));
    v.set("faults", f);
    return v;
}

Result<Spacecraft> Spacecraft::from_json(const json::Value& v) {
    Spacecraft c(v["id"].as_string(), v["model"].as_string(), static_cast<CraftClass>(v["class"].as_int()));
    for (const auto& o : v["parts"].as_array()) {
        auto p = find_part(o["key"].as_string());
        if (!p) return p.error();
        PartState q{o["key"].as_string()};
        q.health = std::clamp(o["health"].as_number(1.0), 0.0, 1.0);
        q.enabled = o["enabled"].as_bool(true);
        q.leaking = o["leak"].as_bool(false);
        if (p.value()->kind == PartKind::Hull) c.slots_ = static_cast<int>(p.value()->capacity);
        c.parts_.push_back(q);
    }
    c.fuel_t_ = v["fuel"].as_number();
    c.cargo_t_ = v["cargo"].as_number();
    c.crew_ = v["crew"].as_int(1);
    const int ph = v["phase"].as_int();
    if (ph < 0 || ph > 3) return make_error(ErrorCode::Parse, "Geçersiz uçuş fazı");
    c.phase_ = static_cast<FlightPhase>(ph);
    c.alt_ = v["alt"].as_number();
    c.x_ = v["x"].as_number();
    c.vv_ = v["vv"].as_number();
    c.vh_ = v["vh"].as_number();
    c.o2_kg_ = v["o2"].as_number(50);
    c.cabin_kpa_ = v["cabin"].as_number(101.3);
    c.battery_kwh_ = v["battery"].as_number();
    const int md = v["mode"].as_int();
    if (md < 0 || md > 5) return make_error(ErrorCode::Parse, "Geçersiz uçuş modu");
    c.mode_ = static_cast<FlightMode>(md);
    c.target_ = v["target"].as_string();
    for (const auto& f : v["faults"].as_array()) {
        const int k = f.as_int(-1);
        if (k < 0 || k > static_cast<int>(Fault::LandingGearFailure)) return make_error(ErrorCode::Parse, "Geçersiz arıza");
        c.faults_.push_back(static_cast<Fault>(k));
    }
    c.power_ok_ = !c.has_fault(Fault::PowerFailure);
    c.nav_ok_ = !c.has_fault(Fault::NavigationFailure);
    c.gear_ok_ = !c.has_fault(Fault::LandingGearFailure);
    return c;
}

namespace {
struct PresetDef {
    const char* key;
    const char* id;
    const char* model;
    CraftClass cls;
    std::vector<const char*> parts;
    int crew;
};
const std::vector<PresetDef>& preset_defs() {
    using C = CraftClass;
    // V41 §2.1 araç sınıfları; parça listeleri katalogdaki gerçek sınıf motorlardan kurulur
    static const std::vector<PresetDef> d = {
        {"lander", "KZ-L1", "Kartal iniş aracı", C::Lander, {"hull_modular", "cockpit_v3", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "rcs", "solar_panel", "battery", "landing_radar", "sensor_suite", "life_support", "landing_legs", "comms_hga", "heat_shield", "crew_cabin"}, 3},
        {"scout", "KZ-S1", "Serçe küçük keşif gemisi", C::Exploration, {"hull_light", "cockpit_v1", "eng_hypergolic", "tank_small", "rcs", "solar_panel", "battery", "sensor_suite", "comms_hga"}, 1},
        {"longrange", "KZ-S2", "Albatros uzun menzilli keşif", C::Exploration, {"hull_modular", "cockpit_v3", "eng_hydrolox", "eng_hydrolox", "tank_large", "tank_medium", "rcs", "solar_panel", "solar_panel", "battery", "sensor_suite", "life_support", "crew_cabin", "comms_hga"}, 2},
        {"science", "KZ-A1", "Merak araştırma gemisi", C::Research, {"hull_modular", "cockpit_v4", "eng_hydrolox", "tank_medium", "rcs", "solar_panel", "solar_panel", "battery", "sensor_suite", "science_lab", "life_support", "crew_cabin", "comms_hga", "robotic_arm"}, 3},
        {"probe", "KZ-P1", "Gözcü otonom sonda", C::Exploration, {"hull_light", "cockpit_v2", "eng_ion", "tank_small", "solar_panel", "solar_panel", "battery", "sensor_suite", "comms_hga"}, 0},
        {"surveyor", "KZ-P2", "Haritacı gezegen tarama aracı", C::Exploration, {"hull_light", "cockpit_v2", "eng_hypergolic", "eng_hypergolic", "tank_medium", "rcs", "solar_panel", "battery", "sensor_suite", "landing_radar", "comms_hga"}, 1},
        {"cargo", "KZ-K1", "Kervan kargo gemisi", C::Transport, {"hull_heavy", "cockpit_v2", "eng_methalox_lander", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "tank_large", "cargo_bay", "cargo_bay", "rcs", "solar_panel", "battery", "landing_legs", "life_support", "comms_hga", "heat_shield"}, 2},
        {"tanker", "KZ-K2", "Pınar yakıt tankeri", C::Transport, {"hull_heavy", "cockpit_v2", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "tank_large", "tank_large", "tank_large", "rcs", "solar_panel", "battery", "comms_hga"}, 1},
        {"colony_ship", "KZ-K3", "Yuva koloni taşıyıcısı", C::Transport, {"hull_heavy", "cockpit_v3", "eng_methalox_lander", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "tank_large", "cargo_bay", "rcs", "solar_panel", "solar_panel", "battery", "life_support", "life_support", "crew_cabin", "crew_cabin", "landing_legs", "heat_shield", "landing_radar", "comms_hga"}, 8},
        {"crew", "KZ-K4", "Yolcu personel taşıyıcısı", C::Transport, {"hull_modular", "cockpit_v3", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "rcs", "solar_panel", "battery", "life_support", "life_support", "crew_cabin", "crew_cabin", "heat_shield", "comms_hga"}, 8},
        {"asteroid", "KZ-A2", "Kaya asteroit araştırma gemisi", C::Research, {"hull_modular", "cockpit_v3", "eng_ion", "eng_hypergolic", "tank_medium", "rcs", "solar_panel", "solar_panel", "battery", "sensor_suite", "science_lab", "robotic_arm", "life_support", "crew_cabin", "comms_hga"}, 2},
        {"atmo", "KZ-A3", "Rüzgâr atmosfer araştırma aracı", C::Research, {"hull_light", "cockpit_v2", "eng_hypergolic", "tank_small", "wings", "heat_shield", "sensor_suite", "battery", "solar_panel", "comms_hga"}, 0},
        {"constructor", "KZ-I1", "Usta uzay inşaat gemisi", C::Construction, {"hull_heavy", "cockpit_v3", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "cargo_bay", "robotic_arm", "robotic_arm", "rcs", "solar_panel", "solar_panel", "battery", "life_support", "crew_cabin", "comms_hga"}, 4},
        {"repair", "KZ-I2", "Onarıcı tamir gemisi", C::Construction, {"hull_modular", "cockpit_v3", "eng_hypergolic", "eng_hypergolic", "tank_medium", "robotic_arm", "rcs", "solar_panel", "battery", "sensor_suite", "life_support", "comms_hga"}, 2},
        {"miner", "KZ-I3", "Kazmacı maden gemisi", C::Construction, {"hull_heavy", "cockpit_v2", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "cargo_bay", "cargo_bay", "robotic_arm", "rcs", "landing_legs", "solar_panel", "battery", "life_support", "comms_hga"}, 2},
        {"heavy", "KZ-O1", "Fil ağır nakliye gemisi", C::Special, {"hull_heavy", "cockpit_v3", "eng_methalox_lander", "eng_methalox_lander", "eng_methalox_lander", "eng_methalox_lander", "tank_large", "tank_large", "tank_large", "cargo_bay", "cargo_bay", "cargo_bay", "rcs", "solar_panel", "battery", "life_support", "comms_hga"}, 2},
        {"transfer", "KZ-O2", "Köprü yörünge transfer aracı", C::Special, {"hull_modular", "cockpit_v2", "eng_hydrolox", "tank_large", "rcs", "solar_panel", "battery", "cargo_bay", "comms_hga"}, 1},
        {"deep", "KZ-O3", "Ufuk derin uzay aracı (nükleer termal)", C::Special, {"hull_heavy", "cockpit_v4", "eng_ntr", "tank_large", "tank_large", "tank_large", "rcs", "solar_panel", "solar_panel", "battery", "battery", "sensor_suite", "science_lab", "life_support", "crew_cabin", "comms_hga"}, 4},
        {"fusion", "KZ-X1", "Yıldız füzyon deneme gemisi (KURGUSAL)", C::Special, {"hull_heavy", "cockpit_v4", "eng_fusion", "tank_large", "rcs", "solar_panel", "battery", "life_support", "crew_cabin", "comms_hga"}, 2},
    };
    return d;
}
}  // namespace

const std::vector<std::string>& preset_keys() {
    static const std::vector<std::string> k = [] {
        std::vector<std::string> v;
        for (const auto& d : preset_defs()) v.push_back(d.key);
        return v;
    }();
    return k;
}

Spacecraft preset(const std::string& key) {
    const auto& defs = preset_defs();
    const PresetDef* d = &defs.front();
    for (const auto& x : defs)
        if (key == x.key) d = &x;
    Spacecraft c(d->id, d->model, d->cls);
    const std::vector<std::string> all = {"methalox", "avionics", "cryo", "nova_link", "ion", "nuclear", "fusion"};
    for (const char* p : d->parts) (void)c.install(p, all);
    c.refuel();
    c.set_crew(d->crew);
    return c;
}

}  // namespace kozmo::craft

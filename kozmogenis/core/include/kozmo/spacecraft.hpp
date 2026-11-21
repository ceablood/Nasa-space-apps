// KozmoCore — uzay aracı ve kokpit motoru (V41 §1, §2): modüler parçalar, türetilmiş teknik özellikler,
// kokpit seviyesine bağlı işlevler, uçuş modları, gerçek veriye bağlı göstergeler, arıza/acil durum
// prosedürleri, araç içi yaşam desteği ve gezegen yakınında 2B iniş/kalkış uçuşu.
//
// Gerçek / yaklaşık: Tsiolkovsky, yerçekimi + merkezkaç (v²/R), üstel atmosfer yoğunluğu, Sutton-Graves
// ısı akısı (k ~1.74e-4 Dünya, ~1.90e-4 Mars), kişi başı O2 0.84 kg/gün, kabin 101.3 kPa.
// Parça kütleleri/güçleri yayımlanmış araç sınıflarından yuvarlanmış mühendislik yaklaşımıdır; dayanıklılık,
// arıza olasılıkları ve kokpit işlev dağılımı OYUN VARSAYIMIDIR. "Kalkan" gerçekçi karşılığıyla
// mikrometeoroid/ısı kalkanıdır (bilimkurgu enerji kalkanı yok).
#pragma once

#include <algorithm>
#include <string>
#include <vector>

#include "kozmo/challenge.hpp"
#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::craft {

enum class PartKind { Hull, Cockpit, Engine, Tank, Rcs, SolarPanel, Battery, Sensor, Radar, Science, Cargo, LifeSupport,
                      LandingGear, RoboticArm, Comms, HeatShield, Wing, Cabin, Decelerator };
const char* to_string(PartKind k);

enum class CraftClass { Exploration, Transport, Research, Construction, Lander, Special };
const char* to_string(CraftClass c);

struct PartSpec {
    std::string key, name;
    PartKind kind;
    double mass_t;
    double power_kw;          // + üretir, - tüketir
    double capacity;          // tank: yakıt t, kargo: t, batarya: kWh, kabin: koltuk, yaşam desteği: kişi
    double thrust_kn = 0, isp_s = 0;
    int cockpit_level = 0;    // kokpit parçası: 1..4
    double heat_limit_kw_m2 = 0;   // ısı kalkanı dayanımı (kW/m^2)
    std::string research = "";   // "" başlangıçta açık
    bool experimental = false;     // kanıtlanmamış teknoloji (ayrı işaretlenir)
};
const std::vector<PartSpec>& parts();
Result<const PartSpec*> find_part(const std::string& key);

enum class CockpitLevel { None = 0, Basic = 1, Advanced = 2, Professional = 3, Experimental = 4 };
enum class Feature { Navigation, Radar, Autopilot, Targeting, FaultDisplay, HoloMap, LandingAssist, PowerDistribution,
                     MultiSensor, DockingAssist, NovaLink, AutonomousSystems, ScienceScan, ThreatAnalysis };
const char* to_string(Feature f);
bool cockpit_has(CockpitLevel level, Feature f);

enum class FlightMode { Manual, Assisted, Autopilot, LandingAssist, DockingAssist, Emergency };
const char* to_string(FlightMode m);

enum class Fault { EngineFailure, FuelLeak, CabinDepressurization, OxygenLow, PowerFailure, NavigationFailure, Overheat,
                   CollisionDamage, LandingGearFailure };
const char* to_string(Fault f);

struct Warning {
    Fault fault;
    int severity;               // 1 uyarı, 2 ciddi, 3 kritik
    std::string message, procedure;
};

struct Specs {
    double dry_t = 0, wet_t = 0, max_t = 0, fuel_capacity_t = 0;
    double thrust_kn = 0, isp_s = 0, dv_ms = 0;
    double power_gen_kw = 0, power_use_kw = 0, battery_kwh = 0;
    int crew_capacity = 0, life_support_crew = 0;
    double cargo_capacity_t = 0, cargo_t = 0;
    double length_m = 0, width_m = 0, height_m = 0;
    double heat_limit_kw_m2 = 0;
    bool atmosphere_capable = false, can_land = false;
    CockpitLevel cockpit = CockpitLevel::None;
    int slots_used = 0, slots_total = 0;
    std::vector<std::string> problems;
};

struct PartState {
    std::string key;
    double health = 1.0;
    bool enabled = true;
    bool leaking = false;
};

enum class FlightPhase { Landed, Flying, Crashed, Orbit };
const char* to_string(FlightPhase p);

// Araç sürümü (V41 §2.3): parçalardan türetilir, etiket değildir
enum class Tier { V1Basic = 1, V2Advanced, V3Professional, V4Experimental };
const char* to_string(Tier t);

struct Docking {
    double range_m = 0, closing_ms = 0;   // hedefe uzaklık, yaklaşma hızı (+ yaklaşıyor)
    bool active = false, docked = false;
};

struct Instruments {     // kokpit göstergeleri: tümü canlı durumdan okunur
    double speed_ms, vertical_ms, horizontal_ms;
    double altitude_m;
    double fuel_t, fuel_fraction;
    double oxygen_kg, oxygen_days;
    double engine_temp_k;
    double cabin_pressure_kpa;
    double power_kw_net, battery_fraction;
    double shield_fraction;           // ısı/mikrometeoroid kalkanı sağlığı
    double hull_fraction;
    double engine_fraction;           // motor sağlığı x etkinlik
    std::string navigation;           // rota/hedef
    std::vector<std::string> radar;   // yakındaki nesneler
    bool engines_on, seated;
    FlightMode mode;
    double throttle;
};

class Spacecraft {
public:
    Spacecraft() = default;
    Spacecraft(std::string id, std::string model, CraftClass cls, int slots = 16);

    const std::string& id() const { return id_; }
    const std::string& model() const { return model_; }
    CraftClass craft_class() const { return cls_; }
    std::string manufacturer = "KOZMOGENİS Tersaneleri";

    // --- parça yönetimi (oyuncu tasarımı)
    Status install(const std::string& key, const std::vector<std::string>& unlocked = {});
    Status remove(std::size_t index);
    const std::vector<PartState>& installed() const { return parts_; }
    Specs specs() const;
    CockpitLevel cockpit() const;
    Tier tier() const;

    // --- doldurma
    void refuel();                       // tankları doldur
    void set_fuel(double t);
    void load_cargo(double t);
    void set_crew(int n) { crew_ = n; }
    int crew() const { return crew_; }

    // --- kokpit etkileşimleri
    Status sit();
    Status stand();
    bool seated() const { return seated_; }
    Status set_engines(bool on);
    void set_throttle(double t);         // 0..1
    void set_pitch_deg(double p);        // manuel: itki yönü (0 = yatay ileri, 90 = dikey yukarı)
    Status set_mode(FlightMode m);
    FlightMode mode() const { return mode_; }
    void set_cabin_lights(int level) { cabin_lights_ = std::clamp(level, 0, 3); }
    int cabin_lights() const { return cabin_lights_; }
    Status set_target(const std::string& name);
    std::string window_view(const challenge::PlanetEnvironment& env) const;   // pencereden görünen

    // --- uçuş (gezegen yakını 2B: irtifa, yatay mesafe)
    void place_landed();
    void place_in_flight(double altitude_m, double horizontal_ms, double vertical_ms);
    void place_in_orbit(const challenge::PlanetEnvironment& env, double altitude_m);   // dairesel yörünge
    // iniş noktası (yatay konum, m): iniş desteği konumu da kontrol eder (yoksa yalnız hızı sıfırlar)
    void set_landing_target(double x_m) { target_x_ = x_m; has_target_ = true; }
    void clear_landing_target() { has_target_ = false; }
    bool has_landing_target() const { return has_target_; }
    double landing_target() const { return target_x_; }
    bool decelerator_deployed() const;
    void step(double dt_s, const challenge::PlanetEnvironment& env, Rng& rng);
    FlightPhase phase() const { return phase_; }
    double altitude() const { return alt_; }
    double vertical_speed() const { return vv_; }
    double horizontal_speed() const { return vh_; }
    double downrange() const { return x_; }
    double fuel() const { return fuel_t_; }
    double max_heat_flux() const { return max_heat_kw_m2_; }
    double touchdown_speed() const { return touchdown_ms_; }
    // tam otomatik iniş (LandingAssist) ya da kalkış simülasyonu: sonuç fazı döner
    FlightPhase fly_until_landed(const challenge::PlanetEnvironment& env, Rng& rng, double max_s = 3600.0, double dt = 0.1);
    // yüzeyden alçak yörüngeye otomatik kalkış (otomatik pilot, hedef "yörünge"); kalkıştan yörüngeye
    Status launch_to_orbit(double orbit_alt_m);
    FlightPhase fly_until_orbit(const challenge::PlanetEnvironment& env, Rng& rng, double max_s = 3600.0, double dt = 0.1);
    double orbit_altitude() const { return orbit_target_m_; }
    // kenetlenme (yörüngede, hedef istasyon): RCS ile yaklaşma. Kenetlenme desteği hızı otomatik yönetir;
    // manuel modda rcs_command (-1..1) ile yaklaşma ivmesi verilir. Temas hızı >0.15 m/s çarpışma hasarı.
    Status begin_docking(double range_m, double closing_ms);
    void set_rcs(double command) { rcs_cmd_ = std::clamp(command, -1.0, 1.0); }
    void step_docking(double dt_s);
    const Docking& docking() const { return dock_; }

    // --- yaşam desteği (saat adımı)
    void tick_life_support(double dt_h);
    double cabin_o2_kg() const { return o2_kg_; }
    double cabin_pressure() const { return cabin_kpa_; }
    double battery() const { return battery_kwh_; }

    // --- hasar ve arıza
    void damage(PartKind kind, double amount);
    void inject(Fault f);
    std::vector<Warning> warnings() const;
    Status apply_procedure(Fault f);       // her arızanın kendi müdahalesi
    Instruments instruments() const;
    bool can_exit(const challenge::PlanetEnvironment& env, bool has_suit) const;
    const std::vector<Fault>& faults() const { return faults_; }

    json::Value to_json() const;
    static Result<Spacecraft> from_json(const json::Value& v);

private:
    double part_health(PartKind k) const;
    bool has_part(PartKind k) const;
    double mass_kg() const;
    double available_thrust_n() const;
    double effective_isp() const;
    void landing_guidance(double g_eff, double max_acc, double& throttle, double& pitch) const;

    std::string id_, model_;
    CraftClass cls_ = CraftClass::Exploration;
    int slots_ = 16;
    std::vector<PartState> parts_;
    double fuel_t_ = 0, cargo_t_ = 0;
    int crew_ = 1;
    bool seated_ = false, engines_on_ = false, nav_ok_ = true, gear_ok_ = true, power_ok_ = true;
    double throttle_ = 0, pitch_deg_ = 90;
    FlightMode mode_ = FlightMode::Manual;
    int cabin_lights_ = 2;
    std::string target_;
    // uçuş durumu
    FlightPhase phase_ = FlightPhase::Landed;
    double alt_ = 0, x_ = 0, vv_ = 0, vh_ = 0;
    double engine_temp_k_ = 290, max_heat_kw_m2_ = 0, touchdown_ms_ = 0;
    // yaşam desteği
    double o2_kg_ = 50, cabin_kpa_ = 101.3, battery_kwh_ = 0, leak_rate_kpa_h_ = 0;
    bool emergency_o2_used_ = false;
    double orbit_target_m_ = 0;
    double target_x_ = 0;
    bool has_target_ = false, decel_jettisoned_ = false;
    Docking dock_;
    double rcs_cmd_ = 0;
    std::vector<Fault> faults_;
    bool has_fault(Fault f) const;
    void clear_fault(Fault f);
};

// Hazır araçlar: "lander", "cargo", "science" ve sınıf kataloğu (preset_keys)
Spacecraft preset(const std::string& key);
const std::vector<std::string>& preset_keys();

}  // namespace kozmo::craft

// KozmoCore — koloni: enerji dengesi, yaşam desteği, üretim zincirleri ve NPC (kolonist) yaşam simülasyonu.
//
// Gerçek / yaklaşık değerler:
//   * Güneş sabiti 1361 W/m^2 (1 AU), uzaklığın karesiyle azalır (fizik)
//   * Kişi başı günlük tüketim: O2 ~0.84 kg, içme+hazırlık suyu ~2.5 kg, gıda ~1.8 kg (NASA yaşam destek
//     referans değerlerinin mertebesine yuvarlanmış mühendislik yaklaşımı)
//   * Modül üretim oranları, NPC ihtiyaç hızları ve moral modeli oyun varsayımıdır.
#pragma once

#include <map>
#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::colony {

constexpr double kSolarConstant = 1361.0;          // W/m^2, 1 AU
constexpr double kO2PerPersonDay_t = 0.84e-3;      // ton
constexpr double kWaterPerPersonDay_t = 2.5e-3;    // ton
constexpr double kFoodPerPersonDay_t = 1.8e-3;     // ton

// Ortalama güneş ışınımı (W/m^2): 1361 / d_AU^2
double solar_flux(double distance_1e6km_from_sun);

enum class Job { Farmer, Engineer, Miner, Scientist, Medic, Pilot, Security };
const char* job_name(Job j);

enum class Activity { Idle, Work, Eat, Sleep, Socialize, Treatment };
const char* activity_name(Activity a);

struct Needs {
    double hunger = 0.2;   // 0 tok .. 1 aç
    double fatigue = 0.2;  // 0 dinç .. 1 bitkin
    double morale = 0.7;   // 0 .. 1
    double health = 1.0;   // 0 ölü .. 1 sağlıklı
};

// Kişilik (V41 §5.2): 0..1 eksenler; davranış ağırlıklarını değiştirir (oyun varsayımı)
struct Personality {
    double courage = 0.5, curiosity = 0.5, patience = 0.5, diligence = 0.5, sociability = 0.5;
    double leadership = 0.5, competitiveness = 0.5, helpfulness = 0.5, caution = 0.5;
    static Personality random(Rng& rng);
    std::vector<std::string> traits() const;   // "Cesur", "Meraklı", "Tembel" ...
};

struct Colonist {
    int id = 0;
    std::string name;
    Job job = Job::Engineer;
    Needs needs;
    Activity activity = Activity::Idle;
    double activity_hours_left = 0.0;
    double skill = 0.5;            // 0..1 meslek becerisi (oyun varsayımı)
    bool alive = true;
    double hours_worked = 0.0;
    double dose_msv = 0.0;           // birikmiş radyasyon dozu
    bool dose_limit_reached = false; // kariyer sınırı aşıldı: çalışma görevlerinden çekilir
    Personality personality;
    bool ordered = false;            // dış emir (alarm/tahliye/onarım): süre bitene kadar kendi seçimini yapmaz
};

enum class ModuleType { Habitat, Greenhouse, Electrolyzer, SolarArray, FissionReactor, Mine, Sabatier, Lab, Clinic };
const char* module_name(ModuleType t);

struct ModuleSpec {
    ModuleType type;
    double power_kw;               // + üretim, - tüketim (nominal)
    int staff;                     // tam verim için gereken çalışan
    Job staff_job;
    int capacity;                  // habitat: yatak sayısı
    std::map<std::string, double> input_per_day;   // ton/gün
    std::map<std::string, double> output_per_day;  // ton/gün (kg için he3 hariç)
    double build_cost;             // kredi (oyun varsayımı)
    std::string research;          // gerekli araştırma
};
const ModuleSpec& spec(ModuleType t);

struct Module {
    ModuleType type;
    double condition = 1.0;        // 0..1 bakım durumu
    double efficiency = 0.0;       // son tick'teki gerçekleşen verim (enerji x personel x girdi)
};

struct TickReport {
    double power_produced_kw = 0, power_demand_kw = 0, power_ratio = 1;
    std::map<std::string, double> produced, consumed;
    std::vector<std::string> shortages;
    int deaths = 0;
    int births = 0;
};

// Olaylar (EventBus)
struct ResourceShortage { std::string colony, resource; };
struct ColonistDied { std::string colony; std::string name; std::string cause; };
struct ColonyMoraleLow { std::string colony; double morale; };
struct RadiationLimitReached { std::string colony; std::string name; double dose_msv; };
struct ModuleDamaged { std::string colony; std::string module; double condition; };

enum class SimDetail { Full, Coarse };   // ölçeklenebilir simülasyon: odaktaki koloni Full

class Colony {
public:
    Colony(std::string id, std::string body_key, double distance_from_sun_1e6km, bool has_atmosphere_co2);

    const std::string& id() const { return id_; }
    const std::string& body() const { return body_; }

    Status add_module(ModuleType t, const std::vector<std::string>& unlocked);
    int add_colonist(const std::string& name, Job job, double skill, Rng& rng);
    void add_resource(const std::string& k, double t) { stock_[k] += t; }
    double resource(const std::string& k) const;
    const std::map<std::string, double>& stock() const { return stock_; }

    const std::vector<Module>& modules() const { return modules_; }
    const std::vector<Colonist>& colonists() const { return colonists_; }
    int population() const;
    int housing() const;
    double average_morale() const;
    double solar_flux() const { return solar_flux_; }

    // dt_hours: simülasyon adımı (saat). local_hour: 0..24 güneş yerel saati (güneş paneli).
    // crew_hour: mürettebatın 24 saatlik çalışma/uyku saati (<0 ise local_hour). Ay'da güneş günü ~29.5 Dünya
    // günüdür; mürettebat Dünya saatine (UTC) göre yaşar. Mars'ta görevler yerel güneş saatini (sol) kullanır.
    TickReport tick(double dt_hours, double local_hour, Rng& rng, EventBus* bus, SimDetail detail = SimDetail::Full, double crew_hour = -1.0);

    // tam durum kaydı (modüller, kolonistler, stok, iş gücü)
    json::Value to_json() const;
    static Result<Colony> from_json(const json::Value& v);
    // bir kaynağı çek (gemiye yükleme / laboratuvar araştırma puanı toplama): en fazla mevcut kadar
    double take(const std::string& k, double t);

    // çevre (her tick öncesi oyun tarafından ayarlanır): güneş çarpanı (toz fırtınası), korumasız dış doz
    void set_environment(double solar_factor, double outside_dose_msv_per_day) {
        env_solar_ = solar_factor;
        env_dose_ = outside_dose_msv_per_day;
    }
    void add_dose(int colonist_id, double msv);
    // dış emir (NPC davranış katmanı / NOVA tahliye): kolonisti belirli süre bir etkinliğe yönlendirir
    Status order(int colonist_id, Activity a, double hours);
    Colonist* colonist(int colonist_id);
    // bakım: modül durumunu onar (mühendis emek-saati ile; oyun varsayımı)
    void repair(ModuleType t, double amount);
    void damage_module(ModuleType t, double amount);   // belirli tür modüllerin tümüne hasar (arıza senaryosu)
    double module_condition(ModuleType t) const;        // o türün ortalama durumu (yoksa 1)
    // rastgele bir modüle hasar (mikrometeoroid vb.)
    void damage_random_module(double amount, Rng& rng, EventBus* bus);

private:
    void tick_npc_full(Colonist& c, double dt, double local_hour, Rng& rng, bool food_ok);
    void tick_npc_coarse(Colonist& c, double dt, bool food_ok);
    Activity choose_activity(const Colonist& c, double local_hour) const;

    std::string id_, body_;
    double solar_flux_;
    bool co2_atmosphere_;
    std::map<std::string, double> stock_;
    std::vector<Module> modules_;
    std::vector<Colonist> colonists_;
    std::map<Job, double> labor_ema_;   // iş gücü (personel yuvası eşdeğeri), 24 saatlik kayan ortalama
    double env_solar_ = 1.0, env_dose_ = 0.0;
    int next_id_ = 1;
};

}  // namespace kozmo::colony

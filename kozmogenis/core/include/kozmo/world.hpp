// KozmoCore — V41 dikey dilim: tek uzay aracı + kokpit, iki gezegen (Ay ve Mars), gezilebilir küçük koloni.
// Tüm sistemler ortak veri modelleri üzerinden bağlanır: craft::Spacecraft (araç/kokpit), challenge (gezegen
// zorluğu ve hayatta kalma), colony::Colony (ekonomi, ihtiyaçlar — tek doğruluk kaynağı), life (mekân, NPC
// zekâsı), Game (zaman, kayıt) ve NOVA (Nova::attach ile bu sefere bağlanır).
#pragma once

#include <string>
#include <vector>

#include "kozmo/challenge.hpp"
#include "kozmo/construction.hpp"
#include "kozmo/game.hpp"
#include "kozmo/life.hpp"
#include "kozmo/spacecraft.hpp"

namespace kozmo::world {

enum class PlayerMode { Seated, InCabin, OnFoot, InBuilding };
const char* to_string(PlayerMode m);

struct Player {
    PlayerMode mode = PlayerMode::InCabin;
    double x = 0, y = 0;               // yerleşim planında (m)
    std::string building;
    int floor = 0;
    std::vector<std::pair<double, double>> route;
    challenge::Survivor body;
    challenge::Equipment eq;
    int samples = 0;                   // dışarıdan toplanan numune
};

// Gövdeye özgü iniş başlangıcı. Ay: Apollo "motorlu iniş başlangıcı" (~15 km, ~1.65 km/s yatay; gerçek).
// Mars: atmosfer girişi + paraşüt sonrası (~10 km, 400 m/s yatay, -150 m/s; mühendislik yaklaşımı —
// bu aracın balistik katsayısı tam girişten motorsuz yavaşlamaya yetmez, model bunu açıkça gösterir).
struct DescentStart { double altitude_m, horizontal_ms, vertical_ms; std::string note; };
Result<DescentStart> descent_start(const std::string& body);

class Expedition {
public:
    Expedition(Game& g, std::string body, craft::Spacecraft c, std::uint64_t seed = 7);
    // ortam, koloni (varsa), yerleşim, toplum. in_orbit: sefer yörüngede başlar (iniş gerekir); false: araç iniş alanında
    Status init(bool in_orbit = true);

    const std::string& body() const { return body_; }
    const challenge::PlanetEnvironment& env() const { return env_; }
    challenge::Equipment equipment() const;         // oyuncu ekipmanı + araç + koloni altyapısı
    challenge::Profile profile() const { return challenge::assess(env_, equipment()); }
    craft::Spacecraft& craft() { return craft_; }
    const craft::Spacecraft& craft() const { return craft_; }
    Player& player() { return player_; }
    const Player& player() const { return player_; }
    life::Society& society() { return society_; }
    const life::Society& society() const { return society_; }
    const life::Settlement& settlement() const { return settlement_; }
    colony::Colony* colony();
    const colony::Colony* colony() const;
    Game& game() { return game_; }
    const Game& game() const { return game_; }

    // --- kokpit / araç
    Status sit();
    Status stand();
    Status begin_descent();
    Status exit_craft();
    Status enter_craft();

    // --- yüzey ve koloni
    Status walk_to(const std::string& building_id);
    // 3B istemci oyuncuyu kendisi yürütür: konumu buraya yazar (yalnız yürürken/bina içindeyken)
    void set_player_position(double x, double y);
    bool walking() const { return !player_.route.empty(); }
    Status enter_building(const std::string& id);
    Status leave_building();
    // kat değiştir: asansör (enerji varsa anında) ya da merdiven (her zaman, ~20 s/kat). Mesaj döner.
    Result<std::string> change_floor(int floor, bool use_elevator = true);
    Status collect_sample();
    Result<std::string> use(const std::string& interactable_id);
    Result<std::string> talk(int npc_id, const std::string& topic);
    std::vector<int> npcs_here() const;            // aynı binadaki / 10 m yakındaki NPC'ler

    // --- araç: yüzeyden yörüngeye ve kenetlenme
    Status take_off(double orbit_alt_m = 15000.0);

    // --- §7.1 koloni kurma: su ara, koloni kur, modül inşa et, güçlendir
    Result<std::string> scan_water();               // araç sensörü / oyuncu dışarıda; bulunursa kuruluş açılır
    bool water_found() const { return water_found_; }
    Status found_colony();                          // yalnız koloni yokken, iniş yapılmış ve su bulunmuşken
    Result<int> build(colony::ModuleType t);        // inşaat projesi (demir + kredi), NPC mühendisler inşa eder
    Result<int> reinforce();                        // fırtına koruması
    const build::Manager& construction() const { return construction_; }
    std::string damage_report() const;              // NOVA hasar raporu

    // --- §7.2 araştırma: araç laboratuvarında numune analizi (araştırma ağacına puan)
    Result<std::string> analyze_onboard();

    // --- §6.3 görevlendirme: NOVA genel emir verir, NPC kabul eder ya da sorun bildirir
    Result<life::MissionReport> assign_mission(life::MissionKind k, colony::Job job, life::District where, int count, double hours,
                                               const std::string& description);

    // --- senaryo olayları
    void fail_power();                              // enerji tesisi arızası (§7.3)
    void evacuate();                                // tüm NPC'ler sığınağa (NOVA onayı sonrası)

    // --- zaman (oyun saniyesi)
    void tick(double dt_s);
    double hours() const { return hours_; }
    double local_hour() const;      // güneş saati (sıcaklık, ışık)
    double crew_hour() const;       // mürettebat saati (NPC programı)
    const std::vector<challenge::WeatherEvent>& weather() const { return weather_; }
    const std::vector<std::string>& log() const { return log_; }

    // NOVA ve UI için özetler (gerçek durumdan)
    std::string colony_report() const;
    std::string environment_report() const;
    std::string vehicle_report() const;
    std::vector<std::string> tasks() const;         // oyuncuya önerilen görevler

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    void push(const std::string& s);
    void update_events();
    void move_player(double dt_s);

    Game& game_;
    std::string body_;
    challenge::PlanetEnvironment env_;
    craft::Spacecraft craft_;
    Player player_;
    life::Settlement settlement_;
    life::Society society_;
    Rng rng_;
    double hours_ = 0, hour_acc_ = 0, weather_acc_ = 0;
    std::vector<challenge::WeatherEvent> weather_;
    std::vector<std::string> log_;
    bool power_alarm_ = false;
    bool in_orbit_ = false;
    bool water_found_ = false;
    build::Manager construction_;
    void update_construction(double dt_h);
};

}  // namespace kozmo::world

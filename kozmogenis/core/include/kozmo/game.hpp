// KozmoCore — oyun çekirdeği: zaman, ajans cüzdanı, görevler, koloniler, piyasalar, araştırma.
// Tüm alt sistemler tek EventBus üzerinden haberleşir; UE5 tarafı yalnızca bu sınıfı sarmalar.
#pragma once

#include <map>
#include <string>
#include <vector>

#include "kozmo/astro.hpp"
#include "kozmo/colony.hpp"
#include "kozmo/core.hpp"
#include "kozmo/economy.hpp"
#include "kozmo/environment.hpp"
#include "kozmo/json.hpp"
#include "kozmo/propulsion.hpp"
#include "kozmo/research.hpp"

namespace kozmo {

struct Payload {
    std::vector<colony::ModuleType> modules;              // koloni kiti
    std::map<std::string, double> cargo;                  // emtia (ton)
    std::vector<std::pair<std::string, colony::Job>> crew;
};

double module_mass_t(colony::ModuleType t);               // oyun varsayımı

// Ortak hazır tasarımlar (CLI, NOVA ve UE5 istemcisi aynı tanımı kullanır)
prop::Design preset_heavy_rocket(const std::string& target, double payload_t, int crew);   // metan/LOX + hidrojen iniş
prop::Design preset_light_rocket(const std::string& target, double payload_t);             // Falcon 9 sınıfı
Payload standard_colony_kit();                                                              // 3 kişilik başlangıç kolonisi
Payload vertical_slice_outpost();
Payload founding_crew_kit();        // §7.1: modülsüz 4 kişilik kuruluş ekibi + 40 t demir (ilk habitatı kendileri inşa eder)   // V41 dikey dilim: 8 kişilik, hastaneli, madenli küçük koloni (senaryo başlangıcı)
double payload_mass_t(const Payload& p);                  // mürettebat kapsülü hariç (analiz ekler)

enum class MissionState { InTransit, Arrived, Lost };

struct Mission {
    int id = 0;
    std::string design_name;
    std::string target;
    Payload payload;
    double depart_day = 0, arrive_day = 0;
    MissionState state = MissionState::InTransit;
    double success_p = 1.0;
};

// Olaylar
struct MissionLaunched { int id; std::string target; double arrive_day; };
struct MissionArrived { int id; std::string target; };
struct MissionLost { int id; std::string target; std::string reason; };
struct ColonyFounded { std::string colony; std::string body; };

class Game {
public:
    explicit Game(std::uint64_t seed = 1);

    void new_game(const std::string& agency, double credits = 60000.0);

    // --- erişim
    double day() const { return day_; }
    const std::string& agency() const { return agency_; }
    econ::Wallet& wallet() { return wallet_; }
    const econ::Wallet& wallet() const { return wallet_; }
    EventBus& bus() { return bus_; }
    research::Tree& research() { return tree_; }
    const research::Tree& research() const { return tree_; }
    const std::map<std::string, colony::Colony>& colonies() const { return colonies_; }
    colony::Colony* colony(const std::string& id);
    const std::vector<Mission>& missions() const { return missions_; }
    econ::Market* market(const std::string& id);
    const std::map<std::string, econ::Market>& markets() const { return markets_; }
    void set_focus(const std::string& colony_id) { focus_ = colony_id; }
    const env::Scheduler& environment() const { return env_; }

    // --- astronomi (oyun saatine göre)
    double longitude(const std::string& body) const;
    Result<astro::TransferWindow> window_to(const std::string& target) const;
    double local_hour(const std::string& body) const;
    double crew_hour(const std::string& body) const;     // mürettebat saati (Mars: sol, diğerleri: Dünya saati)

    // --- eylemler
    Result<prop::Report> evaluate(const prop::Design& d) const;
    Result<int> launch(const prop::Design& d, const Payload& p);
    Status build_module(const std::string& colony_id, colony::ModuleType t);
    // Senaryo başlangıcı (dikey dilim / görev senaryoları): yükü fırlatma yapmadan varmış sayar.
    // Normal oyunda koloniler launch() + yolculuk ile kurulur; bu yol yalnız senaryo kurulumu içindir.
    Status found_outpost(const std::string& body, const Payload& p);   // koloniden yerinde inşa (demir + kredi)
    Result<econ::Trade> trade(const std::string& market_id, const std::string& commodity, double qty, bool buy);

    // --- zaman: days kadar ilerlet (odak koloni saatlik tam simülasyon, diğerleri 6 saatlik kaba)
    void advance(double days);

    // --- kayıt
    std::string save() const;
    Status load(const std::string& json_text);

    static constexpr double kWindowToleranceDays = 20.0;

private:
    void arrive(Mission& m);
    void setup_earth_market();

    double day_ = 0.0;
    std::string agency_;
    econ::Wallet wallet_;
    Rng rng_;
    EventBus bus_;
    research::Tree tree_;
    env::Scheduler env_;
    std::map<std::string, econ::Market> markets_;
    std::map<std::string, colony::Colony> colonies_;
    std::vector<Mission> missions_;
    std::string focus_;
    int next_mission_ = 1;
};

}  // namespace kozmo

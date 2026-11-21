// KozmoCore — modüler koloni inşaat sistemi (V41 §4.6). Her koloni modülü yapı parçalarından oluşan bir
// şablondan inşa edilir: temel, duvar, tavan, kapı, pencere, koridor, hava kilidi, merdiven, asansör, enerji/su/
// oksijen/veri hatları. Her parçanın maliyeti (demir + kredi), işçilik süresi, enerji ihtiyacı, bakım yükü,
// kapasitesi ve dayanıklılığı vardır. İşçiliği NPC mühendisler sahada çalışarak sağlar (life::Society).
// Tüm sayılar OYUN VARSAYIMIDIR (yayımlanmış habitat konseptlerinden mertebe olarak esinlenilmiştir).
#pragma once

#include <string>
#include <vector>

#include "kozmo/colony.hpp"
#include "kozmo/core.hpp"
#include "kozmo/economy.hpp"
#include "kozmo/json.hpp"

namespace kozmo::build {

enum class Piece { Foundation, Wall, Roof, Door, Window, Corridor, Airlock, Stairs, Elevator, PowerLink, WaterLink, OxygenLine, DataLine };
constexpr int kPieceCount = 13;
const char* to_string(Piece p);

struct PieceSpec {
    Piece piece;
    double iron_t;            // yerel demirden üretim
    double credits;
    double labor_h;           // mühendis emek-saati
    double power_kw;          // işletme gücü (tüketim)
    double maintenance;       // yıllık bakım yükü (0..1, dayanım kaybı)
    double durability;        // fırtına/çarpma direnci (0..1)
    int capacity;             // kişi (koridor/asansör geçiş kapasitesi, oda için yatak katkısı yok)
};
const PieceSpec& spec(Piece p);

struct Blueprint {
    colony::ModuleType module;
    std::vector<std::pair<Piece, int>> pieces;
    std::vector<Piece> connections;   // tamamlanınca bağlanması gereken hatlar
};
Blueprint blueprint(colony::ModuleType t);
Blueprint reinforcement();            // fırtına/toz koruması: regolit setleri + ek duvarlar

struct Cost {
    double iron_t = 0, credits = 0, labor_h = 0, power_kw = 0, maintenance = 0, durability = 0;
};
Cost total(const Blueprint& b);

enum class State { Building, WaitingConnection, Done };
const char* to_string(State s);

struct Project {
    int id = 0;
    colony::ModuleType module = colony::ModuleType::Habitat;
    bool reinforce = false;
    double labor_done_h = 0, labor_total_h = 0;
    State state = State::Building;
    std::string missing;        // bağlantı eksikliği açıklaması
    double progress() const { return labor_total_h > 0 ? labor_done_h / labor_total_h : 1.0; }
};

class Manager {
public:
    // Malzeme (koloni demiri) ve kredi peşin düşülür; araştırma gereksinimi kontrol edilir.
    Result<int> start(colony::ModuleType t, colony::Colony& c, econ::Wallet& w, const std::vector<std::string>& unlocked, double day);
    Result<int> start_reinforcement(colony::Colony& c, econ::Wallet& w, double day);
    // Sahadaki işçilik (mühendis emek-saati) en eski etkin projeye gider
    void work(double labor_h);
    // Bitmiş projeleri koloniye ekler (bağlantı uygunsa); eklenen modül türlerini döner
    std::vector<colony::ModuleType> complete(colony::Colony& c, const std::vector<std::string>& unlocked);
    const std::vector<Project>& projects() const { return projects_; }
    bool active() const;
    const Project* current() const;
    bool reinforced() const { return reinforced_; }
    double storm_damage_factor() const { return reinforced_ ? 0.3 : 1.0; }

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<Project> projects_;
    int next_id_ = 1;
    bool reinforced_ = false;
};

// Modül hangi yerleşim bölgesinde kurulur (life::District ile aynı sıra; bağımlılık döngüsü olmasın diye int)
int site_district(colony::ModuleType t);

}  // namespace kozmo::build

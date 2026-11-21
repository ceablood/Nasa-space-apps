// KozmoCore — medeniyet katmanı (V30 §17.2): tüm kolonilerin toplu göstergeleri, gelişim çağı, politikalar ve
// koloniler arası ticaret yolları. Politika etkileri ve çağ eşikleri OYUN VARSAYIMIDIR; göstergeler koloni
// çekirdeğinin gerçek durumundan hesaplanır.
#pragma once

#include <string>
#include <vector>

#include "kozmo/game.hpp"

namespace kozmo::civ {

enum class Era { Outpost, Settlement, Town, City, Civilization };
const char* to_string(Era e);

enum class Policy { None, Rationing, ResearchFocus, SafetyFirst, Festival, Expansion };
const char* to_string(Policy p);
const char* describe(Policy p);

struct Metrics {
    int colonies = 0, population = 0;
    double energy_kw_per_capita = 0;
    double food_days = 0, oxygen_days = 0, water_days = 0;
    double happiness = 0;            // ortalama moral
    double stability = 0;            // 0..1: moral, kıtlık ve sağlık
    double research_per_day = 0;     // laboratuvar kapasitesine göre
    Era era = Era::Outpost;
    std::vector<std::string> notes;
};

struct TradeRoute {
    int id;
    std::string from, to, commodity;
    double tons_per_trip, period_days, next_day;
    int trips = 0;
    double delivered_t = 0;
};

class Civilization {
public:
    Metrics measure(const Game& g) const;
    Status set_policy(Policy p);
    Policy policy() const { return policy_; }
    // günlük politika etkileri + ticaret seferleri (Game zamanına göre); Game::advance'tan sonra çağrılır
    std::vector<std::string> update(Game& g);
    Result<int> add_route(const Game& g, const std::string& from, const std::string& to, const std::string& commodity, double tons, double period_days);
    Status remove_route(int id);
    const std::vector<TradeRoute>& routes() const { return routes_; }

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    Policy policy_ = Policy::None;
    double last_day_ = -1;
    std::vector<TradeRoute> routes_;
    int next_id_ = 1;
};

Era era_for(int population, int colonies);

}  // namespace kozmo::civ

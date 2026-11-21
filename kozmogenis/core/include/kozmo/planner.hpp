// KozmoCore — görev planlayıcı (V30 §5 + §13 + §18; NOVA "görev planla"): hedefe göre fırlatma penceresi
// (Lambert porkchop), delta-v bütçesi, roket analizi, yaşam desteği sarfı, radyasyon dozu ve risk listesi.
// Bütün sayılar ilgili çekirdek modüllerden gelir (nav, astro, propulsion, environment, colony sabitleri).
#pragma once

#include <string>
#include <vector>

#include "kozmo/game.hpp"

namespace kozmo::planner {

struct Plan {
    std::string target;
    double depart_day = 0, tof_days = 0, surface_days = 0, total_days = 0;
    double c3_km2s2 = 0, vinf_arrive_ms = 0;
    double dv_total_ms = 0;
    prop::Report rocket;
    double o2_t = 0, water_t = 0, food_t = 0;         // mürettebat sarfı (geri dönüşümsüz üst sınır)
    double dose_msv = 0;                              // seyir + yüzey
    bool feasible = false;
    std::vector<std::string> risks;
    std::string summary() const;
};

// crew: kişi; payload_t: yük; surface_days: hedefte kalış; ret: dönüş dahil
Result<Plan> plan(const Game& g, const std::string& target, int crew, double payload_t, double surface_days, bool ret);

}  // namespace kozmo::planner

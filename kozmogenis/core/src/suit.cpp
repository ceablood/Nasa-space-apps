#include "kozmo/suit.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::suit {

Atmosphere iss_cabin() { return {101.3, 0.21}; }
Atmosphere exploration() { return {56.5, 0.34}; }

double tissue_ratio(double n2, double suit_kpa) { return n2 / std::max(1.0, suit_kpa); }

double after_prebreathe(double n2, double minutes, bool exercise) {
    const double half = exercise ? kTissueHalfMin / 2.0 : kTissueHalfMin;
    return n2 * std::pow(0.5, std::max(0.0, minutes) / half);
}

double required_prebreathe_min(const Atmosphere& cabin, bool exercise, double suit_kpa) {
    const double n2 = cabin.n2_kpa();
    const double target = kRLimit * suit_kpa;
    if (n2 <= target) return 0.0;
    const double half = exercise ? kTissueHalfMin / 2.0 : kTissueHalfMin;
    return half * std::log2(n2 / target);
}

double metabolic_w(Workload w) {
    switch (w) {
        case Workload::Rest: return 100;
        case Workload::Light: return 200;
        case Workload::Moderate: return 300;
        case Workload::Heavy: return 500;
    }
    return 300;
}

double o2_kg_per_h(double w) { return w * 3600.0 / 20100.0 * 1.43 / 1000.0; }

double EvaState::remaining_h() const {
    const double o2 = c.o2_kg / o2_kg_per_h(300);
    const double co2 = c.co2_capacity_h;
    const double bat = c.battery_wh / 110.0;
    const double cool = c.cooling_water_kg / 0.45;
    return std::max(0.0, std::min({o2, co2, bat, cool}));
}

EvaState begin_eva(const Atmosphere& cabin, double pre, bool exercise, Rng& rng) {
    EvaState s;
    s.tissue_n2_kpa = after_prebreathe(cabin.n2_kpa(), pre, exercise);
    const double R = tissue_ratio(s.tissue_n2_kpa);
    // R sınırın üstündeyse vurgun olasılığı artar (NASA verilerinden kabaca: R 1.65'te ~%5, 2.0'da ~%30)
    if (R > kRLimit) {
        const double p = std::clamp((R - kRLimit) / 0.35 * 0.25 + 0.05, 0.0, 0.9);
        s.dcs = rng.chance(p);
    }
    return s;
}

bool tick(EvaState& s, double dt, Workload w, double ambient_kpa) {
    if (dt <= 0) return true;
    const double met = metabolic_w(w);
    s.elapsed_h += dt;
    s.c.o2_kg = std::max(0.0, s.c.o2_kg - o2_kg_per_h(met) * dt);
    s.c.co2_capacity_h = std::max(0.0, s.c.co2_capacity_h - dt * met / 300.0);
    s.c.battery_wh = std::max(0.0, s.c.battery_wh - 110.0 * dt);
    // süblimatör: vakumda su buzlaşıp süblimleşerek ısı atar; ~0.1 kPa üstünde (Mars 0.6 kPa) çalışmaz
    const bool sublimator = ambient_kpa < 0.1;
    if (sublimator) s.c.cooling_water_kg = std::max(0.0, s.c.cooling_water_kg - 0.45 * dt * met / 300.0);
    s.overheating = !sublimator && met > 250.0 && ambient_kpa < 5.0;   // ince atmosfer: ne süblimatör ne konveksiyon yeterli
    // doku N2 giysi basıncında saf O2'de azalmaya devam eder
    s.tissue_n2_kpa = after_prebreathe(s.tissue_n2_kpa, dt * 60.0, w == Workload::Heavy);
    if (s.c.o2_kg <= 0) s.limiting = "Oksijen";
    else if (s.c.co2_capacity_h <= 0) s.limiting = "CO2 temizleyici";
    else if (s.c.battery_wh <= 0) s.limiting = "Batarya";
    else if (sublimator && s.c.cooling_water_kg <= 0) s.limiting = "Soğutma suyu";
    return s.limiting.empty() && !s.dcs;
}

}  // namespace kozmo::suit

#include "kozmo/planner.hpp"

#include <cstdio>

#include "kozmo/environment.hpp"
#include "kozmo/nav.hpp"

namespace kozmo::planner {

namespace {
std::string f(double v, const char* fmt = "%.1f") {
    char b[48];
    std::snprintf(b, sizeof(b), fmt, v);
    return b;
}
}  // namespace

std::string Plan::summary() const {
    std::string s = target + " görevi: kalkış oyun günü " + f(depart_day, "%.0f") + ", yolculuk " + f(tof_days, "%.0f") + " gün, toplam " + f(total_days, "%.0f") +
                    " gün, C3 " + f(c3_km2s2) + " km²/s², delta-v " + f(dv_total_ms / 1000.0, "%.2f") + " km/s, kalkış " + f(rocket.liftoff_mass_t, "%.0f") +
                    " t, başarı %" + f(rocket.success_p * 100, "%.0f") + ", doz " + f(dose_msv, "%.0f") + " mSv, sarf O2 " + f(o2_t, "%.2f") + " t / su " +
                    f(water_t, "%.2f") + " t / gıda " + f(food_t, "%.2f") + " t. " + (feasible ? "UYGUN" : "UYGUN DEĞİL");
    for (const auto& r : risks) s += "\n- " + r;
    return s;
}

Result<Plan> plan(const Game& g, const std::string& target, int crew, double payload_t, double surface_days, bool ret) {
    Plan p;
    p.target = target;
    p.surface_days = surface_days;
    auto body = astro::find(target);
    if (!body) return body.error();
    if (crew < 0 || payload_t < 0) return make_error(ErrorCode::InvalidArgument, "Geçersiz mürettebat/yük");
    // 1) pencere: Ay/LEO için Lambert gerekmez (birkaç gün); gezegenler için porkchop
    if (target == "moon") {
        p.depart_day = g.day();
        p.tof_days = 4.5;   // Apollo ~3-4 gün; düşük enerjili transferlerle uzar
        p.c3_km2s2 = -2.0;  // Ay transferi C3 ~ -2 km²/s² (yaklaşık)
    } else if (body.value()->parent == "sun") {
        const double span = std::max(200.0, astro::synodic_period_days(365.256, body.value()->period_days));
        auto pc = nav::porkchop("earth", target, g.day(), span, 5.0, 100.0, std::min(1500.0, body.value()->period_days * 0.8), 5.0);
        if (!pc) return pc.error();
        p.depart_day = pc.value().best.depart_day;
        p.tof_days = pc.value().best.tof_days;
        p.c3_km2s2 = pc.value().best.c3_km2s2;
        p.vinf_arrive_ms = pc.value().best.vinf_arrive_ms;
    } else {
        return make_error(ErrorCode::InvalidArgument, target + " için planlayıcı yalnız Ay ve gezegenleri destekler");
    }
    p.total_days = p.tof_days * (ret ? 2 : 1) + surface_days;
    // 2) delta-v ve roket
    auto budget = astro::mission_budget(target);
    if (!budget) return budget.error();
    p.dv_total_ms = budget.value().total(true, ret);
    const prop::Design d = preset_heavy_rocket(target, payload_t + (crew > 0 ? 3.0 + 0.5 * crew : 0.0), crew);
    auto rep = g.evaluate(d);
    std::string locked;
    if (!rep && rep.error().code == ErrorCode::Locked) {
        locked = rep.error().message;   // fizik yine hesaplanır; açılmamış teknoloji risk olarak bildirilir
        rep = prop::analyze(d, {"methalox", "cryo", "nuclear", "ion", "isru", "fission", "closed_loop"});
    }
    if (!rep) return rep.error();
    p.rocket = rep.value();
    // 3) sarf (geri dönüşümsüz üst sınır; kolonide %85-98 geri kazanım düşer)
    const double pd = p.total_days * crew;
    p.o2_t = colony::kO2PerPersonDay_t * pd;
    p.water_t = colony::kWaterPerPersonDay_t * pd;
    p.food_t = colony::kFoodPerPersonDay_t * pd;
    // 4) radyasyon
    const double cruise = env::cruise_dose_msv_per_day() * p.tof_days * (ret ? 2 : 1);
    auto sd = env::surface_dose_msv_per_day(target);
    p.dose_msv = cruise + (sd ? sd.value() * surface_days * env::kHabitatShielding : 0.0);
    // 5) riskler
    p.feasible = p.rocket.feasible && locked.empty();
    if (!locked.empty()) p.risks.push_back("Teknoloji: " + locked);
    for (const auto& r : p.rocket.problems) p.risks.push_back("Roket: " + r);
    if (crew > 0 && p.dose_msv > env::kCareerLimitMsv) {
        p.risks.push_back("Radyasyon: görev dozu " + f(p.dose_msv, "%.0f") + " mSv, NASA kariyer sınırını (600 mSv) aşıyor");
        p.feasible = false;
    } else if (crew > 0 && p.dose_msv > 0.5 * env::kCareerLimitMsv) {
        p.risks.push_back("Radyasyon: görev dozu kariyer sınırının yarısını aşıyor");
    }
    if (crew > 0 && p.total_days > 30) p.risks.push_back("Uzun görev: sağlık sorumlusu zorunlu (ekip kuralı)");
    if (p.depart_day - g.day() > 60) p.risks.push_back("Sonraki uygun pencere " + f(p.depart_day - g.day(), "%.0f") + " gün sonra");
    if (!sd && body.value()->diameter_km > 40000) p.risks.push_back("Katı yüzey yok: yalnız yörünge/atmosfer görevi");
    return p;
}

}  // namespace kozmo::planner

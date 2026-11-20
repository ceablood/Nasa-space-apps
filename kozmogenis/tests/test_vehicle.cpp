#include "kozmo/flight.hpp"
#include "kozmo/vehicle.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::vehicle;

namespace {
prop::Design f9(double payload) {
    prop::Design d;
    d.stages = {{"kerolox_gg", 9, 411.0, (25.6 - 9 * 0.47) / 411.0, 3.66}, {"kerolox_vac", 1, 107.5, (4.0 - 0.49) / 107.5, 3.66}};
    d.payload_t = payload;
    d.target = "leo";
    return d;
}
}  // namespace

TEST("vehicle: yakıt karışım yoğunlukları gerçek değerlere yakın") {
    CHECK_NEAR(propellant("RP-1/LOX").value().bulk_density(), 1023.0, 15.0);   // ~1030 kg/m^3
    CHECK_NEAR(propellant("LH2/LOX").value().bulk_density(), 361.0, 10.0);     // ~360 kg/m^3
    CHECK_NEAR(propellant("CH4/LOX").value().bulk_density(), 833.0, 15.0);     // ~830 kg/m^3
    CHECK_NEAR(propellant("APCP").value().bulk_density(), 1770.0, 1e-9);
    CHECK(!propellant("unobtainium").ok());
}

TEST("vehicle: Falcon 9 sınıfı geometri gerçek boyutlara yakın") {
    auto g = geometry(f9(22.0));
    CHECK(g.ok());
    const auto& x = g.value();
    CHECK(x.stages.size() == 2);
    CHECK(x.stages[0].stage_length_m > 38 && x.stages[0].stage_length_m < 47);   // gerçek 1. kademe ~41 m
    CHECK(x.total_height_m > 65 && x.total_height_m < 80);                       // gerçek ~70 m
    CHECK_NEAR(x.stages[0].oxidizer_t / x.stages[0].fuel_t, 2.56, 1e-9);
    CHECK(x.fairing_mass_t > 1.0 && x.fairing_mass_t < 3.0);                     // gerçek ~1.9 t
    CHECK(x.fineness > 15 && x.fineness < 25);                                   // gerçek ~19
    // kütle merkezi tabana yakın (dolu tanklar altta), CoP burunda -> statik kararsız, gimbal gerekli
    CHECK(x.center_of_mass_m < x.total_height_m * 0.5);
    CHECK(x.static_margin_cal < 0 && x.needs_active_control);
}

TEST("vehicle: hidrojen tankı aynı kütle için kerosenden ~2.8 kat hacimli") {
    prop::Design a, b;
    a.stages = {{"kerolox_vac", 1, 100.0, 0.05, 4.0}};
    b.stages = {{"hydrolox_exp", 1, 100.0, 0.05, 4.0}};
    const double va = geometry(a).value().stages[0].tank_volume_m3, vb = geometry(b).value().stages[0].tank_volume_m3;
    CHECK_NEAR(vb / va, 1023.0 / 361.0, 0.15);
    prop::Design bad = a;
    bad.stages[0].diameter_m = 0.1;
    CHECK(!geometry(bad).ok());
    prop::Design thin = a;
    thin.stages[0].propellant_t = 3000;
    thin.stages[0].diameter_m = 2.0;
    CHECK(!geometry(thin).value().notes.empty());                                // burkulma uyarısı
}

TEST("vehicle: paralel kademe — güçlendiriciler TWR'yi ve kapasiteyi artırır") {
    prop::Design d = f9(30.0);
    auto plain = prop::analyze(d, {});
    CHECK(!plain.value().feasible);                                              // F9 30 t'u taşıyamaz
    d.boosters.count = 2;
    d.boosters.propellant_t = 150;
    d.boosters.diameter_m = 2.5;
    auto r = prop::analyze(d, {});
    CHECK(r.ok());
    const auto& x = r.value();
    CHECK(x.stages.size() == 3);                                                 // A fazı + çekirdek + 2. kademe
    CHECK(x.stages[0].label.find("Güçlendirici") != std::string::npos);
    CHECK(x.liftoff_twr > plain.value().liftoff_twr * 2);
    CHECK(x.total_dv_ms > plain.value().total_dv_ms);
    // A fazı süresi = güçlendirici yakıtı / kütle akışı (SRB sınıfı: tam itki ~95 s / 500 t)
    auto e = prop::find_engine("srb").value();
    const double mdot = e->thrust_vac_kn * 1000.0 / (e->isp_vac_s * prop::kG0) / 1000.0;
    CHECK_NEAR(x.stages[0].burn_s, 150.0 / mdot, 1e-6);
    // mürettebatlıda kısılamayan güçlendirici uyarısı
    d.crew = 3;
    auto c = prop::analyze(d, {});
    bool warned = false;
    for (const auto& p : c.value().problems) warned |= p.find("kısılamaz") != std::string::npos;
    CHECK(warned);
    // geçersiz
    prop::Design bad = d;
    bad.boosters.count = 12;
    CHECK(!prop::analyze(bad, {}).ok());
}

TEST("vehicle: güçlendiricili uçuş — ayrılma olayları ve 35 t yörünge") {
    prop::Design d = f9(35.0);
    d.boosters.count = 2;
    d.boosters.propellant_t = 150;
    d.boosters.diameter_m = 2.5;
    auto r = flight::simulate_ascent(d, flight::AscentConfig{});
    CHECK(r.ok());
    const auto& x = r.value();
    CHECK(x.orbit);
    double t_boost = -1, t_meco = -1, t_fair = -1;
    for (const auto& e : x.events) {
        if (e.type == flight::EventType::BoosterSeparation) t_boost = e.t_s;
        if (e.type == flight::EventType::StageBurnout && t_meco < 0) t_meco = e.t_s;
        if (e.type == flight::EventType::FairingSeparation) t_fair = e.t_s;
    }
    CHECK(t_boost > 0 && t_boost < t_meco);
    CHECK(t_fair > 0);
    CHECK(x.fairing_kg > 0);
    // güçlendiricisiz aynı yük yörüngeye çıkamaz
    CHECK(!flight::simulate_ascent(f9(35.0), flight::AscentConfig{}).value().orbit);
}

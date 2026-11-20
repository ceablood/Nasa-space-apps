#include "kozmo/challenge.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::challenge;

TEST("gezegen: gerçek fiziksel veriler ve atmosfer yoğunluğu") {
    auto mars = body_environment("mars").value();
    CHECK_NEAR(mars.gravity_ms2, 3.71, 1e-9);
    // ideal gaz, 0.636 kPa, 208 K: ~0.016 kg/m^3 (NASA tablosu ~0.020 verir; farklı referans koşulları)
    CHECK_NEAR(mars.surface_density(), 0.016, 0.002);
    auto earth = body_environment("earth").value();
    CHECK_NEAR(earth.surface_density(), 1.225, 0.03);            // deniz seviyesi 1.225
    auto venus = body_environment("venus").value();
    CHECK_NEAR(venus.surface_density(), 65.0, 3.0);              // ~65 kg/m^3
    CHECK(!body_environment("vulcan").ok());
    CHECK_NEAR(body_environment("moon").value().dose_msv_day, 1.37, 1e-9);
    CHECK(!body_environment("jupiter").value().solid_surface);
}

TEST("gezegen: her sınıf farklı zorluk profili üretir") {
    Equipment none;
    auto moon = assess(body_environment("moon").value(), none);
    auto mars = assess(body_environment("mars").value(), none);
    auto venus = assess(body_environment("venus").value(), none);
    auto jup = assess(body_environment("jupiter").value(), none);
    auto europa = assess(body_environment("europa").value(), none);
    auto earth = assess(body_environment("earth").value(), none);
    CHECK(earth.overall_raw < mars.overall_raw);
    CHECK(moon[Category::Radiation].raw > mars[Category::Radiation].raw);     // Ay 1.37 > Mars 0.64 mSv/gün
    CHECK(europa[Category::Radiation].raw >= 1.0);
    CHECK(venus[Category::Atmosphere].raw > 0.9 && venus[Category::Temperature].raw >= 1.0);
    CHECK(mars[Category::Landing].raw > moon[Category::Landing].raw);          // atmosfer girişi gerekir
    CHECK(!jup.landable && jup[Category::Landing].raw >= 1.0);
    CHECK(!jup.playable.empty());
    CHECK(moon[Category::Gravity].raw > mars[Category::Gravity].raw);
}

TEST("gezegen: hazırlık zorluğu düşürür (dinamik zorluk)") {
    auto env = body_environment("mars").value();
    Equipment none, full;
    full.pressure_suit = full.thermal_suit = full.heated_habitat = full.dust_filters = full.water_recycler = true;
    full.water_extractor = full.heat_shield = full.landing_radar = full.rover = true;
    full.shielding_gcm2 = 40;
    auto a = assess(env, none), b = assess(env, full);
    CHECK(b.overall < a.overall);
    for (int i = 0; i < kCategoryCount; ++i) CHECK(b.scores[i].mitigated <= a.scores[i].mitigated + 1e-12);
    CHECK(a[Category::Atmosphere].mitigated >= 1.0 && b[Category::Atmosphere].mitigated < 0.2);
    CHECK(!a[Category::Landing].missing.empty());
    CHECK(b[Category::Landing].missing.empty());
}

TEST("gezegen: hava olayları atmosfer/iklim parametrelerinden türetilir") {
    auto has = [](const std::vector<Weather>& w, Weather x) { return std::find(w.begin(), w.end(), x) != w.end(); };
    auto mars = possible_weather(body_environment("mars").value());
    auto moon = possible_weather(body_environment("moon").value());
    auto venus = possible_weather(body_environment("venus").value());
    CHECK(has(mars, Weather::DustStorm) && !has(moon, Weather::DustStorm));       // atmosfersiz yerde kum fırtınası yok
    CHECK(has(moon, Weather::MeteorShower) && !has(mars, Weather::MeteorShower));
    CHECK(has(venus, Weather::AcidRain) && !has(mars, Weather::AcidRain));
    CHECK(has(moon, Weather::ThermalSwing));
    Rng rng(5);
    int storms = 0;
    for (int h = 0; h < 24 * 365; ++h)
        for (const auto& w : roll_weather(body_environment("mars").value(), h, 1.0, rng))
            if (w.kind == Weather::DustStorm) ++storms;
    CHECK(storms > 3 && storms < 30);                                            // yılda birkaç-onlarca
}

TEST("hayatta kalma: giysisiz vakum ölümcül, giysi oksijeni biter, kalkan dozu düşürür") {
    auto moon = body_environment("moon").value();
    Equipment none, suit;
    suit.pressure_suit = true;
    Survivor a;
    survive(moon, none, true, 0.01, {}, 12, a);
    CHECK(!a.alive);
    Survivor b;
    for (int i = 0; i < 9; ++i) survive(moon, suit, true, 1.0, {}, 9, b);   // sabah EVA, 9 saat
    CHECK(b.suit_o2_h <= 0.0 && !b.alive);
    Survivor c;
    survive(moon, suit, true, 4.0, {}, 9, c);
    CHECK(c.alive && c.dose_msv > 0.2 && c.dose_msv < 0.25);           // 1.37 mSv/gün x 4 saat
    Survivor night;
    survive(moon, suit, true, 1.0, {}, 0, night);                      // -173 °C gece: EMU sınırının altında
    CHECK(night.health < 1.0);
    Equipment thermal = suit;
    thermal.thermal_suit = true;
    Survivor ok;
    survive(moon, thermal, true, 1.0, {}, 0, ok);
    CHECK_NEAR(ok.health, 1.0, 1e-9);
    Equipment shield;
    shield.shielding_gcm2 = 60;
    Survivor in1, in2;
    survive(moon, none, false, 24, {}, 12, in1);
    survive(moon, shield, false, 24, {}, 12, in2);
    CHECK(in2.dose_msv < in1.dose_msv * 0.5);
    auto venus = body_environment("venus").value();
    Survivor v;
    survive(venus, thermal, true, 0.1, {}, 12, v);
    CHECK(!v.alive);                                                    // Venüs yüzeyinde EVA mümkün değil
}

TEST("gezegen: prosedürel gezegenler sınıflandırılır") {
    universe::Planet p{};
    p.name = "Test-b";
    p.semi_major_au = 1.0;
    p.radius_earth = 1.0;
    p.surface_gravity_g = 1.0;
    p.equilibrium_temp_k = 250;
    p.retains_atmosphere = true;
    p.type = universe::PlanetType::Ocean;
    auto e = from_procedural(p, 42);
    CHECK(e.cls == PlanetClass::Ocean && e.water_availability >= 1.0);
    p.type = universe::PlanetType::GasGiant;
    CHECK(!from_procedural(p, 42).solid_surface);
    p.type = universe::PlanetType::Airless;
    p.retains_atmosphere = false;
    p.semi_major_au = 0.05;
    CHECK(from_procedural(p, 42).cls == PlanetClass::Radiation);
}

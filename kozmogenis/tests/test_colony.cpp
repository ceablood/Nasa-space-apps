#include "kozmo/colony.hpp"
#include "test_framework.hpp"
#include <cstdio>

using namespace kozmo;
using namespace kozmo::colony;

namespace {
Colony mars_base(Rng& rng, int people = 6) {
    Colony c("ares", "mars", 228.0, true);
    std::vector<std::string> all = {"fission", "isru"};
    for (auto t : {ModuleType::Habitat, ModuleType::Habitat, ModuleType::Greenhouse, ModuleType::Greenhouse,
                   ModuleType::Electrolyzer, ModuleType::FissionReactor, ModuleType::SolarArray, ModuleType::Mine,
                   ModuleType::Clinic})
        CHECK(c.add_module(t, all).ok());
    const Job jobs[] = {Job::Farmer, Job::Farmer, Job::Engineer, Job::Engineer, Job::Miner, Job::Medic, Job::Miner,
                        Job::Scientist};
    for (int i = 0; i < people; ++i) c.add_colonist("K" + std::to_string(i), jobs[i % 8], 0.6, rng);
    c.add_resource("water", 6.0);
    c.add_resource("oxygen", 0.5);
    c.add_resource("food", 0.4);
    c.add_resource("medicine", 0.05);
    return c;
}
}  // namespace

TEST("colony: güneş ışınımı uzaklığın karesiyle azalır") {
    CHECK_NEAR(solar_flux(149.6), 1361.0, 2.0);
    CHECK_NEAR(solar_flux(228.0), 586.0, 3.0);       // Mars ~%43
    CHECK_NEAR(solar_flux(778.5), 50.3, 1.0);        // Jüpiter ~%3.7
}

TEST("colony: dengeli 6 kişilik Mars kolonisi 60 gün hayatta kalır (saatlik tam simülasyon)") {
    Rng rng(11);
    EventBus bus;
    int died = 0;
    bus.subscribe<ColonistDied>([&](const ColonistDied&) { ++died; });
    Colony c = mars_base(rng);
    for (int hour = 0; hour < 60 * 24; ++hour) c.tick(1.0, hour % 24, rng, &bus);
    CHECK(died == 0);
    CHECK(c.population() >= 6);
    CHECK(c.resource("food") > 0.0);
    CHECK(c.resource("oxygen") > 0.0);
    CHECK(c.average_morale() > 0.35);
    for (const auto& col : c.colonists()) CHECK(col.hours_worked > 60.0);   // herkes çalıştı
}

TEST("colony: oksijensiz koloni saatler içinde kaybedilir, olay yayınlanır") {
    Rng rng(3);
    EventBus bus;
    int died = 0, short_o2 = 0;
    bus.subscribe<ColonistDied>([&](const ColonistDied& e) { ++died; CHECK(e.cause == "oksijen yetersizliği"); });
    bus.subscribe<ResourceShortage>([&](const ResourceShortage& e) { if (e.resource == "oxygen") ++short_o2; });
    Colony c("x", "moon", 149.6, false);
    CHECK(c.add_module(ModuleType::Habitat, {}).ok());
    for (int i = 0; i < 3; ++i) c.add_colonist("A", Job::Engineer, 0.5, rng);
    c.add_resource("food", 1.0);
    c.add_resource("water", 1.0);
    for (int h = 0; h < 12; ++h) c.tick(1.0, 12, rng, &bus);
    CHECK(died == 3);
    CHECK(c.population() == 0);
    CHECK(short_o2 > 0);
}

TEST("colony: Sabatier yalnız CO2 atmosferinde, fisyon araştırma ister") {
    Colony moon("m", "moon", 149.6, false);
    CHECK(moon.add_module(ModuleType::Sabatier, {"isru"}).error().code == ErrorCode::Infeasible);
    CHECK(moon.add_module(ModuleType::FissionReactor, {}).error().code == ErrorCode::Locked);
    Colony mars("r", "mars", 228.0, true);
    CHECK(mars.add_module(ModuleType::Sabatier, {}).error().code == ErrorCode::Locked);
    CHECK(mars.add_module(ModuleType::Sabatier, {"isru"}).ok());
}

TEST("colony: gece güneş paneli üretmez, batarya biterse verim düşer") {
    Rng rng(5);
    Colony c("s", "moon", 149.6, false);
    for (auto t : {ModuleType::SolarArray, ModuleType::Greenhouse}) CHECK(c.add_module(t, {}).ok());
    c.add_colonist("F", Job::Farmer, 1.0, rng);
    c.add_resource("water", 5.0);
    auto day = c.tick(1.0, 12.0, rng, nullptr, SimDetail::Coarse);
    CHECK(day.power_produced_kw > 20.0);           // öğlen: 10 kW ortalama * pi
    auto night = c.tick(1.0, 0.0, rng, nullptr, SimDetail::Coarse);
    CHECK(night.power_produced_kw == 0.0);
    CHECK(night.power_ratio < 0.01);               // bataryasız (yaşam modülü yok)
}

TEST("colony: kaba simülasyon tam simülasyonla benzer gıda tüketir (ölçeklenebilirlik)") {
    Rng r1(9), r2(9);
    Colony a = mars_base(r1), b = mars_base(r2);
    const double fa0 = a.resource("food"), fb0 = b.resource("food");
    for (int h = 0; h < 20 * 24; ++h) a.tick(1.0, h % 24, r1, nullptr, SimDetail::Full);
    for (int day = 0; day < 20; ++day) b.tick(24.0, 12.0, r2, nullptr, SimDetail::Coarse);
    // doğumlar rastgeledir ve iki mod üreteci farklı sırada kullanır: kişi başı karşılaştır
    const double ra = (a.resource("food") - fa0) / a.population(), rb = (b.resource("food") - fb0) / b.population();
    std::printf("    kişi başı net gıda (t): tam %.4f  kaba %.4f   nüfus %d / %d\n", ra, rb, a.population(), b.population());
    CHECK_NEAR(ra, rb, 0.012);
    CHECK(a.population() >= 6 && b.population() >= 6);
}

#include "kozmo/environment.hpp"
#include "kozmo/game.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::env;

TEST("env: ölçülmüş doz oranları ve NASA kariyer sınırı") {
    CHECK_NEAR(surface_dose_msv_per_day("moon").value(), 1.37, 1e-12);     // Chang'e-4 LND
    CHECK_NEAR(surface_dose_msv_per_day("mars").value(), 0.64, 1e-12);     // Curiosity RAD
    CHECK_NEAR(surface_dose_msv_per_day("earth").value() * 365.25, 2.4, 1e-9);
    CHECK_NEAR(cruise_dose_msv_per_day(), 1.84, 1e-12);                     // MSL seyir
    CHECK(!surface_dose_msv_per_day("jupiter").ok());                       // ölçüm yok: uydurulmaz
    CHECK_NEAR(kCareerLimitMsv, 600.0, 0);
    // gerçeklik kontrolü: 259 günlük Mars transferi ~476 mSv (yayımlanmış ~330 mSv/180 gün oranıyla tutarlı)
    CHECK_NEAR(cruise_dose_msv_per_day() * 259.0, 476.0, 2.0);
}

TEST("env: olay sıklığı ve toz fırtınasının güneşi kesmesi") {
    Scheduler s;
    Rng rng(9);
    EventBus bus;
    int spe = 0, regional = 0, global = 0, impacts = 0;
    bus.subscribe<EnvironmentEventStarted>([&](const EnvironmentEventStarted& e) {
        spe += e.kind == EventKind::SolarParticleEvent;
        regional += e.kind == EventKind::RegionalDustStorm;
        global += e.kind == EventKind::GlobalDustStorm;
        impacts += e.kind == EventKind::MicrometeoroidImpact;
    });
    double min_factor = 1.0;
    const int days = 20000;                       // ~55 yıl: küresel fırtına beklenen ~10 kez
    for (int d = 1; d <= days; ++d) {
        s.advance(d - 1, d, {"mars", "moon"}, rng, &bus);
        min_factor = std::min(min_factor, s.solar_factor("mars", d));
        CHECK(s.solar_factor("moon", d) == 1.0);                            // Ay'da toz fırtınası yok
        while (s.impact_pending("moon")) {}
        while (s.impact_pending("mars")) {}
    }
    const double spe_per_60d = spe * 60.0 / days;
    CHECK(spe_per_60d > 0.7 && spe_per_60d < 1.3);                          // ~60 günde bir
    CHECK(regional > global);                                               // bölgesel daha sık
    CHECK(global >= 3 && global < 25);
    CHECK(min_factor < 0.9);
    CHECK(impacts > 5);
}

TEST("env: Ay kolonisi doz biriktirir; kariyer sınırını aşan çalışmaz") {
    Game g(21);
    g.new_game("A", 3e6);
    for (const char* k : {"cryo", "methalox"}) {
        g.research().start(k);
        g.research().add_points(1e6, nullptr);
    }
    auto kit = standard_colony_kit();
    CHECK(g.launch(preset_heavy_rocket("moon", payload_mass_t(kit) + 0.5, 3), kit).ok());
    g.advance(105.0);
    const auto& col = g.colonies().begin()->second;
    for (const auto& c : col.colonists()) {
        if (!c.alive) continue;
        // ~100 gün x 1.37 x 0.5 (habitat) + ~9 mSv yolculuk + olası fırtınalar
        CHECK(c.dose_msv > 70.0 && c.dose_msv < 400.0);
    }
    // doğrudan: aşırı doz -> sınır olayı ve iş bırakma
    colony::Colony c("x", "moon", 149.6, false);
    Rng rng(1);
    EventBus bus;
    int limit = 0;
    bus.subscribe<colony::RadiationLimitReached>([&](const colony::RadiationLimitReached&) { ++limit; });
    CHECK(c.add_module(colony::ModuleType::Habitat, {}).ok());
    c.add_colonist("R", colony::Job::Engineer, 0.5, rng);
    c.add_resource("oxygen", 5);
    c.add_resource("water", 5);
    c.add_resource("food", 5);
    c.set_environment(1.0, 2000.0);                                         // olağanüstü fırtına
    for (int h = 0; h < 24; ++h) c.tick(1.0, 12, rng, &bus);
    CHECK(limit == 1);
    CHECK(c.colonists()[0].dose_limit_reached);
    const double worked = c.colonists()[0].hours_worked;
    c.set_environment(1.0, 0.0);
    for (int h = 0; h < 48; ++h) c.tick(1.0, h % 24, rng, &bus);
    CHECK_NEAR(c.colonists()[0].hours_worked, worked, 1e-9);                // artık çalışmıyor
}

TEST("env: aktif olaylar ve doz kayıtta korunur") {
    Game a(77);
    a.new_game("A", 3e6);
    for (const char* k : {"cryo", "methalox"}) {
        a.research().start(k);
        a.research().add_points(1e6, nullptr);
    }
    auto kit = standard_colony_kit();
    CHECK(a.launch(preset_heavy_rocket("moon", payload_mass_t(kit) + 0.5, 3), kit).ok());
    for (int i = 0; i < 400 && a.environment().active().empty(); ++i) a.advance(1.0);
    CHECK(!a.environment().active().empty());
    const std::string s = a.save();
    Game b(1);
    CHECK(b.load(s).ok());
    CHECK(b.save() == s);
    CHECK(b.environment().active().size() == a.environment().active().size());
    a.advance(5.0);
    b.advance(5.0);
    CHECK(a.save() == b.save());
}

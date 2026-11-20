#include <cmath>

#include "kozmo/spacecraft.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::craft;

TEST("araç: parça değişimi kütle, yakıt, itki ve delta-v'yi değiştirir") {
    Spacecraft c = preset("lander");
    const Specs a = c.specs();
    CHECK(a.problems.empty() || a.problems.size() == 0);
    CHECK_NEAR(a.fuel_capacity_t, 25.0, 1e-9);
    CHECK_NEAR(a.thrust_kn, 200.0, 1e-9);
    CHECK_NEAR(a.dv_ms, 355 * 9.80665 * std::log(a.wet_t / a.dry_t), 1e-6);
    CHECK(a.can_land && a.atmosphere_capable);
    CHECK(c.install("tank_medium").ok());
    c.refuel();
    const Specs b = c.specs();
    CHECK_NEAR(b.fuel_capacity_t, 35.0, 1e-9);
    CHECK_NEAR(b.dry_t, a.dry_t + 0.8, 1e-9);
    CHECK(b.dv_ms > a.dv_ms);
    CHECK(!c.install("cockpit_v1").ok());                         // ikinci kokpit olmaz
    CHECK(c.install("eng_fusion").error().code == ErrorCode::Locked);   // kurgusal motor araştırma ister
    CHECK(c.install("eng_fusion", {"fusion"}).ok());
    bool flagged = false;
    for (const auto& p : c.specs().problems) flagged |= p.find("kurgusal") != std::string::npos;
    CHECK(flagged);                                                // deneysel teknoloji ayrı işaretlenir
}

TEST("kokpit: seviye işlevleri belirler (V1 analog .. V4 NOVA)") {
    CHECK(cockpit_has(CockpitLevel::Basic, Feature::Radar));
    CHECK(!cockpit_has(CockpitLevel::Basic, Feature::Autopilot));
    CHECK(cockpit_has(CockpitLevel::Advanced, Feature::Autopilot));
    CHECK(!cockpit_has(CockpitLevel::Advanced, Feature::LandingAssist));
    CHECK(cockpit_has(CockpitLevel::Professional, Feature::LandingAssist));
    CHECK(!cockpit_has(CockpitLevel::Professional, Feature::NovaLink));
    CHECK(cockpit_has(CockpitLevel::Experimental, Feature::NovaLink));
    Spacecraft c("t", "deneme", CraftClass::Lander);
    for (const char* p : {"hull_light", "cockpit_v1", "eng_hypergolic", "tank_small", "landing_legs", "landing_radar"}) CHECK(c.install(p).ok());
    CHECK(!c.set_mode(FlightMode::Autopilot).ok());
    CHECK(!c.set_mode(FlightMode::LandingAssist).ok());
    CHECK(!c.set_target("istasyon").ok());                         // hedef belirleme V2+
    CHECK(c.set_mode(FlightMode::Emergency).ok());                 // acil mod her zaman
}

TEST("kokpit: etkileşimler — oturmadan motor çalışmaz, manuel uçuşta kalkılmaz") {
    Spacecraft c = preset("lander");
    CHECK(!c.set_engines(true).ok());
    CHECK(c.sit().ok());
    CHECK(c.set_engines(true).ok());
    c.place_in_flight(1000, 0, 0);
    CHECK(!c.stand().ok());
    CHECK(c.set_mode(FlightMode::LandingAssist).ok());
    CHECK(c.stand().ok());
    c.set_cabin_lights(0);
    CHECK(c.window_view(challenge::body_environment("moon").value()).find("karanlık") != std::string::npos);
}

TEST("uçuş: Ay ve Mars'a otomatik iniş yumuşak temas, yakıt gerçek mertebede") {
    for (const char* body : {"moon", "mars"}) {
        auto env = challenge::body_environment(body).value();
        Spacecraft c = preset("lander");
        Rng rng(3);
        CHECK(c.sit().ok());
        CHECK(c.set_engines(true).ok());
        if (std::string(body) == "moon") c.place_in_flight(15000, 1650, 0);
        else c.place_in_flight(10000, 400, -150);
        CHECK(c.set_mode(FlightMode::LandingAssist).ok());
        const double f0 = c.fuel();
        CHECK(c.fly_until_landed(env, rng, 3000, 0.05) == FlightPhase::Landed);
        CHECK(c.touchdown_speed() < 3.0);
        if (std::string(body) == "moon") {
            // Apollo LM iniş bütçesi ~2.0 km/s; burada kullanılan delta-v
            const double dry = c.specs().dry_t;
            const double dv = 355 * 9.80665 * std::log((dry + f0) / (dry + c.fuel()));
            CHECK(dv > 1700 && dv < 2300);
        }
    }
}

TEST("uçuş: motorsuz düşüş çarpar; sert inişte iniş takımı hasar alır") {
    auto env = challenge::body_environment("moon").value();
    Spacecraft c = preset("lander");
    Rng rng(1);
    c.place_in_flight(500, 0, 0);
    CHECK(c.fly_until_landed(env, rng, 600, 0.05) == FlightPhase::Crashed);
    Spacecraft d = preset("lander");
    d.place_in_flight(0.5, 0, -5.0);
    (void)d.fly_until_landed(env, rng, 10, 0.01);
    CHECK(d.phase() == FlightPhase::Landed);
    bool gear = false;
    for (auto f : d.faults()) gear |= f == Fault::LandingGearFailure;
    CHECK(gear);
}

TEST("acil durum: her arızanın uyarısı ve müdahalesi farklı") {
    Spacecraft c = preset("lander");
    const Fault all[] = {Fault::EngineFailure, Fault::FuelLeak, Fault::CabinDepressurization, Fault::OxygenLow, Fault::PowerFailure,
                         Fault::NavigationFailure, Fault::CollisionDamage, Fault::LandingGearFailure};
    for (Fault f : all) c.inject(f);
    auto w = c.warnings();
    CHECK(w.size() >= 8);
    CHECK(w.front().severity == 3);                                  // kritikler önce
    // sızıntı yakıt kaybettirir
    const double fuel = c.fuel();
    auto env = challenge::body_environment("moon").value();
    Rng rng(1);
    c.place_in_flight(100000, 0, 0);
    c.step(10, env, rng);
    CHECK(c.fuel() < fuel);
    // basınç kaybı zamanla düşer
    const double p0 = c.cabin_pressure();
    c.tick_life_support(1.0);
    CHECK(c.cabin_pressure() < p0);
    // navigasyon arızasında otomatik modlar kapalı
    CHECK(!c.set_mode(FlightMode::LandingAssist).ok());
    for (Fault f : all) CHECK(c.apply_procedure(f).ok());
    CHECK(c.faults().empty());
    CHECK(c.set_mode(FlightMode::LandingAssist).ok());
    CHECK(!c.apply_procedure(Fault::OxygenLow).ok());               // etkin değil
}

TEST("göstergeler canlı veriye bağlı; araç kaydı ve yüklemesi") {
    Spacecraft c = preset("lander");
    auto in = c.instruments();
    CHECK_NEAR(in.fuel_fraction, 1.0, 1e-9);
    CHECK_NEAR(in.cabin_pressure_kpa, 101.3, 1e-9);
    CHECK_NEAR(in.oxygen_days, 50.0 / (3 * 0.84), 1e-9);
    c.tick_life_support(24.0);                                       // ECLSS %95 geri kazanım
    CHECK(c.instruments().oxygen_kg < 50.0 && c.instruments().oxygen_kg > 49.0);
    c.damage(PartKind::Engine, 0.5);
    CHECK_NEAR(c.instruments().engine_fraction, 0.5, 1e-9);
    CHECK_NEAR(c.specs().thrust_kn, 100.0, 1e-9);                     // hasar itkiyi düşürür
    c.inject(Fault::FuelLeak);
    auto j = c.to_json();
    auto r = Spacecraft::from_json(json::parse(j.dump()).value());
    CHECK(r.ok());
    CHECK_NEAR(r.value().specs().thrust_kn, 100.0, 1e-9);
    CHECK(r.value().faults().size() == 1);
    CHECK(r.value().installed().size() == c.installed().size());
}

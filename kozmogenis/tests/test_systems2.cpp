#include <cmath>

#include "kozmo/acoustics.hpp"
#include "kozmo/attitude.hpp"
#include "kozmo/lockstep.hpp"
#include "kozmo/nova.hpp"
#include "kozmo/planner.hpp"
#include "kozmo/solar.hpp"
#include "kozmo/station.hpp"
#include "kozmo/suit.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::attitude;

TEST("tutum: serbest dönüşte enerji ve açısal momentum korunur (RK4)") {
    Body b;
    b.set_omega({0.01, 0.2, 0.05});
    const double E0 = b.rotational_energy();
    const V3 L0 = b.angular_momentum_world();
    for (int i = 0; i < 60000; ++i) b.step(0.01);
    CHECK(std::fabs(b.rotational_energy() - E0) / E0 < 1e-9);
    CHECK((b.angular_momentum_world() - L0).norm() / L0.norm() < 1e-5);
    CHECK_NEAR(Quat{b.q()}.normalized().w * Quat{b.q()}.normalized().w + b.q().x * b.q().x + b.q().y * b.q().y + b.q().z * b.q().z, 1.0, 1e-12);
}

TEST("tutum: SAS dönüşü durdurur, hedefe yönelir, yönelimi tutar; tekerlek doyunca RCS") {
    Body k;
    k.set_omega({0.05, -0.03, 0.02});
    k.set_sas(Sas::KillRotation);
    for (int i = 0; i < 6000; ++i) k.step(0.05);
    CHECK(k.omega().norm() < 1e-4);
    const Quat goal = Quat::from_axis_angle({0, 0, 1}, 1.5708);
    Body t;
    t.set_target(goal);
    t.set_sas(Sas::Target);
    for (int i = 0; i < 12000; ++i) t.step(0.05);
    CHECK(t.q().angle_to(goal) < 0.01 && t.omega().norm() < 1e-3);
    Body h;
    h.set_sas(Sas::Hold);
    h.set_disturbance({0, 0, 0.05});
    for (int i = 0; i < 200000; ++i) h.step(0.05);
    CHECK(h.q().angle_to(Quat{}) < 0.01);
    CHECK_NEAR(std::fabs(h.wheel_momentum().z), 50.0, 1e-6);   // doydu
    CHECK(h.rcs_propellant_used() > 0);                        // RCS devraldı (momentum boşaltma)
    Body m;
    m.set_input({0, 0, 1});
    for (int i = 0; i < 100; ++i) m.step(0.1);
    CHECK(m.omega().z > 0.01 && m.rcs_propellant_used() > 0);  // kontrol kolu tork verir
    CHECK_NEAR(Quat::from_axis_angle({1, 0, 0}, 3.14159265358979).rotate({0, 1, 0}).y, -1.0, 1e-9);
}

TEST("giysi: vurgun ön soluması gerçek protokollere yakın; sarf ve süblimatör") {
    CHECK_NEAR(suit::required_prebreathe_min(suit::iss_cabin(), false), 256, 10);   // ~4 saat
    CHECK_NEAR(suit::required_prebreathe_min(suit::iss_cabin(), true), 128, 10);    // egzersizli ~2 saat
    CHECK(suit::required_prebreathe_min(suit::exploration(), false) == 0);           // keşif atmosferi
    CHECK_NEAR(suit::o2_kg_per_h(300), 0.077, 0.005);
    suit::EvaState fresh;
    CHECK_NEAR(fresh.remaining_h(), 7.8, 0.3);                                      // EMU ~8 saat
    Rng rng(4);
    int dcs = 0;
    for (int i = 0; i < 400; ++i) dcs += suit::begin_eva(suit::iss_cabin(), 0, false, rng).dcs;
    int safe = 0;
    for (int i = 0; i < 400; ++i) safe += suit::begin_eva(suit::iss_cabin(), 140, true, rng).dcs;
    CHECK(dcs > 100 && safe == 0);
    suit::EvaState s;
    bool ok = true;
    for (int i = 0; i < 100 && ok; ++i) ok = suit::tick(s, 0.1, suit::Workload::Heavy, 0.0);
    CHECK(!ok && !s.limiting.empty() && s.elapsed_h < 8.0);
    suit::EvaState mars;
    (void)suit::tick(mars, 1.0, suit::Workload::Heavy, 0.636);
    CHECK(mars.overheating);                                                         // süblimatör Mars'ta çalışmaz
}

TEST("akustik: ses hızı ve seviye ortama bağlı; vakumda yalnız temas/telsiz") {
    auto earth = challenge::body_environment("earth").value();
    auto mars = challenge::body_environment("mars").value();
    auto moon = challenge::body_environment("moon").value();
    CHECK_NEAR(acoustics::speed_of_sound(earth), 340, 5);
    CHECK_NEAR(acoustics::speed_of_sound(mars), 235, 15);                 // Perseverance ~240 m/s
    CHECK_NEAR(acoustics::level_offset_db(mars), -20, 3);                 // ~20 dB daha zayıf
    CHECK(acoustics::speed_of_sound(moon) == 0);
    auto air = acoustics::hear(acoustics::Cue::EngineRumble, moon, 100, false, false, false);
    CHECK(!air.audible);
    auto ground = acoustics::hear(acoustics::Cue::EngineRumble, moon, 100, false, true, false);
    CHECK(ground.audible && ground.channel == acoustics::Channel::Structure);
    auto radio = acoustics::hear(acoustics::Cue::Voice, moon, 500, false, false, true);
    CHECK(radio.audible && radio.channel == acoustics::Channel::Radio);
    auto m = acoustics::hear(acoustics::Cue::Voice, mars, 5, false, false, false);
    auto e = acoustics::hear(acoustics::Cue::Voice, earth, 5, false, false, false);
    CHECK(m.audible && e.level_db - m.level_db > 15 && m.delay_s > e.delay_s);
}

TEST("güneş döngüsü: Döngü 25 tepesi ~2024.8, minimum ~2019.9; istasyon alçalmasını değiştirir") {
    CHECK(solar::sunspot_number(2024.8) > 150 && solar::sunspot_number(2019.3) < 20);
    CHECK_NEAR(solar::f107(0), 63.7, 1e-9);
    CHECK(solar::density_factor(2024.8) > 5 * solar::density_factor(2019.3));
    CHECK(solar::spe_per_year(2024.8) > 3 * solar::spe_per_year(2019.3));
    auto a = station::iss_like(), b = station::iss_like();
    (void)a.advance_days(30, solar::density_factor(2024.8));
    (void)b.advance_days(30, solar::density_factor(2019.3));
    CHECK(a.altitude() < b.altitude() - 3000);
    CHECK_NEAR(solar::year_from_game_day(365.25, 2030), 2031, 1e-9);
}

TEST("görev planlayıcı: Ay ve Mars planı — pencere, delta-v, sarf, doz, riskler; NOVA") {
    Game g(9);
    g.new_game("x", 1e6);
    auto moon = planner::plan(g, "moon", 3, 5, 14, true);
    CHECK(moon.ok());
    CHECK(moon.value().tof_days < 6 && moon.value().dose_msv < 50);
    auto mars = planner::plan(g, "mars", 4, 10, 30, true);
    CHECK(mars.ok());
    CHECK(mars.value().tof_days > 180 && mars.value().tof_days < 330);
    CHECK(mars.value().c3_km2s2 > 7 && mars.value().c3_km2s2 < 13);
    CHECK(mars.value().dose_msv > 600);                                 // ~2 x 260 gün x 1.84 + yüzey: sınır aşılır
    CHECK(!mars.value().feasible);
    bool rad = false, medic = false;
    for (const auto& r : mars.value().risks) {
        rad |= r.find("Radyasyon") != std::string::npos;
        medic |= r.find("sağlık sorumlusu") != std::string::npos;
    }
    CHECK(rad && medic);
    CHECK_NEAR(mars.value().o2_t, colony::kO2PerPersonDay_t * 4 * mars.value().total_days, 1e-9);
    CHECK(!planner::plan(g, "sun", 1, 1, 1, false).ok());
    nova::Nova n(g);
    CHECK(n.ask("mars görevi planla 4 kişi").text.find("Mars") != std::string::npos || n.ask("mars görevi planla 4 kişi").text.find("mars") != std::string::npos);
}

TEST("çok oyunculu kilit adım: eşler aynı komutlarla senkron kalır; bozulma tespit edilir") {
    lockstep::Session s(3, 1234, 2, 1);
    s.submit(0, {replay::Op::FoundOutpost, 0, "moon"});
    s.submit(1, {replay::Op::StartResearch, 0, "cryo"});
    for (int i = 0; i < 20; ++i) (void)s.pump();
    CHECK(s.turn() > 10);
    CHECK(!s.desynced());
    CHECK(s.hash(0) == s.hash(1) && s.hash(1) == s.hash(2));
    CHECK(s.game(2).colonies().count("moon_koloni") == 1);           // 0. eşin komutu 2. eşte de uygulandı
    s.corrupt(1);
    for (int i = 0; i < 5; ++i) (void)s.pump();
    CHECK(s.desynced() && s.desync_turn() >= 10);
}

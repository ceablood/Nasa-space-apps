#include "kozmo/astro.hpp"
#include "kozmo/flight.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::flight;

namespace {
prop::Design f9(double payload) {
    prop::Design d;
    d.stages = {{"kerolox_gg", 9, 411.0, (25.6 - 9 * 0.47) / 411.0}, {"kerolox_vac", 1, 107.5, (4.0 - 0.49) / 107.5}};
    d.payload_t = payload;
    d.target = "leo";
    return d;
}
double mu_earth() { return astro::find("earth").value()->mu(); }
double re() { return astro::find("earth").value()->radius_m(); }
}  // namespace

TEST("flight: ABD Standart Atmosferi 1976 tablo değerleri") {
    auto a0 = us_standard_1976(0);
    CHECK_NEAR(a0.temperature_k, 288.15, 1e-9);
    CHECK_NEAR(a0.pressure_pa, 101325.0, 1e-6);
    CHECK_NEAR(a0.density_kgm3, 1.2250, 0.0005);
    auto a11 = us_standard_1976(11019.0);                 // 11 km jeopotansiyel ~ 11.019 km geometrik
    CHECK_NEAR(a11.temperature_k, 216.65, 0.05);
    CHECK_NEAR(a11.pressure_pa, 22632.0, 15.0);
    CHECK_NEAR(us_standard_1976(20000).density_kgm3, 0.08891, 0.0003);   // geometrik 20 km (jeopotansiyel 20 km: 0.08803)
    CHECK_NEAR(us_standard_1976(50000).pressure_pa, 79.78, 0.6);
    CHECK(us_standard_1976(120000).density_kgm3 < 1e-6);
    CHECK(us_standard_1976(30000).density_kgm3 < us_standard_1976(29000).density_kgm3);   // monoton
}

TEST("flight: RK4 dairesel yörünge — 10 yörüngede enerji korunumu") {
    const double mu = mu_earth(), r0 = re() + 400e3;
    State s{{0, r0}, {-std::sqrt(mu / r0), 0}, 1000};
    const double e0 = orbit_from_state(s.r, s.v, mu, re()).specific_energy;
    const double T = astro::orbital_period(mu, r0);
    const int steps = static_cast<int>(T / 5.0);
    for (int k = 0; k < 10; ++k) s = propagate(s, mu, T / steps, steps);
    const double e1 = orbit_from_state(s.r, s.v, mu, re()).specific_energy;
    CHECK(std::fabs((e1 - e0) / e0) < 1e-9);
    CHECK_NEAR(s.r.norm(), r0, 5.0);
    CHECK_NEAR(s.r.x, 0.0, 50.0);                         // 10 periyot sonra başladığı yerde
}

TEST("flight: eliptik yörünge — Kepler periyodu ve apsisler") {
    const double mu = mu_earth(), rp = re() + 300e3, ra = re() + 3000e3;
    const double a = 0.5 * (rp + ra);
    State s{{0, rp}, {-astro::vis_viva(mu, rp, a), 0}, 1};
    auto o = orbit_from_state(s.r, s.v, mu, re());
    CHECK_NEAR(o.periapsis_alt_m, 300e3, 1.0);
    CHECK_NEAR(o.apoapsis_alt_m, 3000e3, 1.0);
    CHECK_NEAR(o.eccentricity, (ra - rp) / (ra + rp), 1e-9);
    const double T = astro::orbital_period(mu, a);
    const int steps = 20000;
    State e = propagate(s, mu, T / steps, steps);
    CHECK_NEAR((e.r - s.r).norm(), 0.0, 2.0);            // tam bir periyotta başa döner
    State half = propagate(s, mu, T / steps, steps / 2);
    CHECK_NEAR(half.r.norm(), ra, 2.0);                  // yarım periyotta apoapsis
}

TEST("flight: vakumda yanma Tsiolkovsky denklemine eşit") {
    const double m0 = 120000, prop = 100000, isp = 348;
    const double dv = vacuum_burn_dv(m0, prop, isp, 981000, 0.5);
    const double ideal = isp * prop::kG0 * std::log(m0 / (m0 - prop));
    CHECK(std::fabs(dv - ideal) / ideal < 1e-6);
}

TEST("flight: Falcon 9 sınıfı fırlatma gerçek profile yakın, ~22.8 t LEO") {
    auto r = simulate_ascent(f9(22.8), AscentConfig{});
    CHECK(r.ok());
    const auto& x = r.value();
    CHECK(x.orbit);
    CHECK(x.final_orbit.periapsis_alt_m > 140e3);
    CHECK(x.max_q_pa > 25e3 && x.max_q_pa < 45e3);        // gerçek: ~30-35 kPa
    CHECK(x.max_q_alt_m > 9e3 && x.max_q_alt_m < 14e3);   // gerçek: ~11-13 km
    double meco = 0;
    for (const auto& e : x.events)
        if (e.type == EventType::StageBurnout && meco == 0) meco = e.t_s;
    CHECK(meco > 140 && meco < 175);                       // gerçek MECO ~160 s
    CHECK(x.max_accel_g <= 4.05);                          // motor kısma sınırı
    CHECK(x.gravity_loss_ms > 500 && x.gravity_loss_ms < 1600);
    // aşırı yük yörüngeye çıkamaz
    auto heavy = simulate_ascent(f9(27.0), AscentConfig{});
    CHECK(heavy.ok() && !heavy.value().orbit);
    CHECK(!heavy.value().failure.empty());
}

TEST("flight: olay sırası tutarlı, geçersiz girdi reddedilir") {
    auto r = simulate_ascent(f9(10.0), AscentConfig{});
    const auto& ev = r.value().events;
    CHECK(ev.front().type == EventType::Liftoff);
    CHECK(ev.back().type == EventType::OrbitAchieved);
    for (std::size_t i = 1; i < ev.size(); ++i) CHECK(ev[i].t_s >= ev[i - 1].t_s);
    CHECK(!r.value().telemetry.empty());
    prop::Design empty;
    CHECK(!simulate_ascent(empty, AscentConfig{}).ok());
    AscentConfig bad;
    bad.dt_s = 5.0;
    CHECK(!simulate_ascent(f9(1), bad).ok());
}

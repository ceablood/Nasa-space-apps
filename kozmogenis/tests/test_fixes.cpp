#include <algorithm>
#include <cmath>

#include "kozmo/world.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::world;

namespace {
bool land(Expedition& e) {
    if (!e.sit().ok() || !e.begin_descent().ok()) return false;
    if (!e.craft().set_engines(true).ok() || !e.craft().set_mode(craft::FlightMode::LandingAssist).ok()) return false;
    for (int i = 0; i < 2000 && e.craft().phase() == craft::FlightPhase::Flying; ++i) e.tick(1.0);
    return e.craft().phase() == craft::FlightPhase::Landed;
}
}  // namespace

TEST("düzeltme: sefer gerçek yörüngede başlar ve iniş alanına iner (konum güdümü)") {
    Game g(91);
    g.new_game("x", 1e6);
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init().ok());
    CHECK(e.craft().phase() == craft::FlightPhase::Orbit);
    CHECK_NEAR(e.craft().altitude(), 15000, 1e-6);
    CHECK_NEAR(e.craft().horizontal_speed(), 1670, 5);           // 15 km'de dairesel hız
    CHECK(!e.exit_craft().ok());
    CHECK(land(e));
    CHECK(e.craft().has_landing_target());
    CHECK(std::fabs(e.craft().downrange() - e.craft().landing_target()) < 50.0);
    CHECK(e.craft().touchdown_speed() < 3.0);
    // başlangıç sapması (geç PDI) güdümle düzeltilir
    auto c = craft::preset("lander");
    Rng rng(2);
    CHECK(c.sit().ok() && c.set_engines(true).ok());
    c.place_in_flight(15000, 1650, 0);
    c.set_landing_target(e.craft().landing_target() - 15000.0);
    CHECK(c.set_mode(craft::FlightMode::LandingAssist).ok());
    CHECK(c.fly_until_landed(challenge::body_environment("moon").value(), rng, 4000, 0.05) == craft::FlightPhase::Landed);
    CHECK(std::fabs(c.downrange() - c.landing_target()) < 50.0);
}

TEST("düzeltme: Mars'a yörüngeden tam giriş (şişme ısı kalkanı + motorlu iniş)") {
    Game g(92);
    g.new_game("x", 1e6);
    Expedition bad(g, "mars", craft::preset("lander"));
    CHECK(bad.init().ok());
    CHECK(bad.sit().ok());
    auto st = bad.begin_descent();
    CHECK(!st.ok() && st.error().message.find("HIAD") != std::string::npos);
    Expedition e(g, "mars", craft::preset("mars_lander"));
    CHECK(e.init().ok());
    CHECK(land(e));
    CHECK(e.craft().touchdown_speed() < 3.0);
    CHECK(std::fabs(e.craft().downrange() - e.craft().landing_target()) < 50.0);
    CHECK(e.craft().max_heat_flux() > 5.0);                       // gerçek atmosfer girişi ısınması
    CHECK(!e.craft().decelerator_deployed());                     // ses altında atıldı
    CHECK(e.craft().fuel() > 5.0);
}

TEST("düzeltme: mühendis bakım turu fırtınada aşınan güneş dizilerini onarır") {
    Game g(93);
    g.new_game("x", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    g.advance(9.375);
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init(false).ok());
    e.colony()->damage_module(colony::ModuleType::SolarArray, 0.4);
    const double before = e.colony()->module_condition(colony::ModuleType::SolarArray);
    for (int i = 0; i < 24 * 4 * 6; ++i) e.tick(600.0);
    CHECK(e.colony()->module_condition(colony::ModuleType::SolarArray) > before + 0.05);
}

TEST("düzeltme: katlı binalar — asansör (enerji ister), merdiven, kata göre konsollar") {
    Game g(94);
    g.new_game("x", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init(false).ok());
    CHECK(e.exit_craft().ok());
    const auto* admin = e.settlement().find(life::District::Admin);
    (void)e.walk_to(admin->id);
    for (int i = 0; i < 3000 && e.walking(); ++i) e.tick(1.0);
    CHECK(e.enter_building(admin->id).ok());
    auto r = e.use("admin_nova");
    CHECK(!r.ok() && r.error().message.find("1. katta") != std::string::npos);
    CHECK(e.change_floor(1).ok());
    CHECK(e.use("admin_nova").ok());
    CHECK(!e.change_floor(5).ok());
    e.fail_power();
    CHECK(!e.change_floor(0, true).ok());                         // enerji yok: asansör çalışmaz
    auto stairs = e.change_floor(0, false);
    CHECK(stairs.ok() && stairs.value().find("Merdiven") != std::string::npos);
    CHECK(e.use("admin_pop").ok());
    const auto* lab = e.settlement().find(life::District::Lab);
    CHECK(!lab->elevator && lab->floors == 2);
    auto j = e.to_json();
    CHECK(j["player"]["floor"].as_int() == 0);
}

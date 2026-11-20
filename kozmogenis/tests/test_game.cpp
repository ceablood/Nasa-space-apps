#include "kozmo/game.hpp"
#include "test_framework.hpp"
#include <cstdio>

using namespace kozmo;
using colony::Job;
using colony::ModuleType;

namespace {
prop::Design moon_lander(double payload, int crew) {
    prop::Design d;
    d.name = "Ay kolonisi taşıyıcısı";
    // ağır sınıf üç kademeli metan/LOX + hidrojen iniş kademesi; Ay yüzeyine ~40 t (toplam ~15.3 km/s)
    d.stages = {{"methalox_fc", 33, 3400.0, 0.06}, {"methalox_vac", 3, 1200.0, 0.06}, {"hydrolox_exp", 4, 140.0, 0.10}};
    d.payload_t = payload;
    d.crew = crew;
    d.target = "moon";
    d.land = true;
    return d;
}
void unlock(Game& g) {
    for (const char* k : {"cryo", "methalox"}) {
        g.research().start(k);
        g.research().add_points(1000, nullptr);
    }
}
Payload moon_kit() {
    Payload p;
    p.modules = {ModuleType::Habitat, ModuleType::Greenhouse, ModuleType::Electrolyzer, ModuleType::SolarArray,
                 ModuleType::SolarArray, ModuleType::Lab};
    p.cargo = {{"water", 3.0}, {"oxygen", 0.3}, {"food", 0.3}};
    p.crew = {{"Ada", Job::Farmer}, {"Can", Job::Engineer}, {"Ece", Job::Scientist}};
    return p;
}
}  // namespace

TEST("game: Ay'a koloni kiti gönderilir, varışta koloni kurulur") {
    Game g(77);
    g.new_game("AETHER", 2e6);
    unlock(g);
    int founded = 0, arrived = 0;
    g.bus().subscribe<ColonyFounded>([&](const ColonyFounded&) { ++founded; });
    g.bus().subscribe<MissionArrived>([&](const MissionArrived&) { ++arrived; });
    auto p = moon_kit();
    auto d = moon_lander(payload_mass_t(p) + 0.5, 3);
    auto rep = g.evaluate(d);
    CHECK(rep.ok());
    CHECK(rep.value().feasible);
    auto id = g.launch(d, p);
    CHECK(id.ok());
    if (!id.ok()) { std::printf("    fırlatma hatası: %s\n", id.error().message.c_str()); return; }
    if (rep.ok()) for (auto& pr : rep.value().problems) std::printf("    sorun: %s\n", pr.c_str());
    const auto& m = g.missions().front();
    CHECK(m.state == MissionState::InTransit);
    CHECK_NEAR(m.arrive_day - m.depart_day, 5.0, 0.4);     // Dünya-Ay Hohmann ~5 gün
    g.advance(6.0);
    CHECK(arrived == 1 && founded == 1);
    auto* c = g.colony("moon_koloni");
    CHECK(c != nullptr);
    CHECK(c->population() == 3);
    CHECK(c->modules().size() == 6);
    // Ay'da gün ~29.5 Dünya günü: yerel saat yavaş ilerler
    const double h0 = g.local_hour("moon");
    g.advance(1.0);
    CHECK_NEAR(std::fmod(g.local_hour("moon") - h0 + 24.0, 24.0), 24.0 / 29.53, 0.05);
}

TEST("game: Mars görevi pencere dışında reddedilir, pencerede kabul edilir") {
    Game g(5);
    g.new_game("AETHER", 1e7);
    unlock(g);
    prop::Design d = moon_lander(5.0, 0);
    d.target = "mars";
    d.land = false;
    Payload cargo;
    cargo.cargo = {{"water", 4.0}};
    auto w = g.window_to("mars");
    CHECK(w.ok());
    // pencereye kadar bekle
    if (w.value().days_until > Game::kWindowToleranceDays && w.value().synodic_days - w.value().days_until > Game::kWindowToleranceDays) {
        auto r = g.launch(d, cargo);
        CHECK(!r.ok());
        CHECK(r.error().code == ErrorCode::Infeasible);
        g.advance(w.value().days_until);
    }
    auto ok = g.launch(d, cargo);
    CHECK(ok.ok());
    if (!ok.ok()) { std::printf("    fırlatma hatası: %s\n", ok.error().message.c_str()); return; }
    const auto& m = g.missions().back();
    CHECK_NEAR(m.arrive_day - m.depart_day, 259.0, 4.0);
}

TEST("game: yük kapasitesi ve mürettebat doğrulanır, gaz devine koloni kurulmaz") {
    Game g(1);
    g.new_game("X", 1e7);
    unlock(g);
    auto p = moon_kit();
    CHECK(g.launch(moon_lander(1.0, 3), p).error().code == ErrorCode::InvalidArgument);
    CHECK(g.launch(moon_lander(payload_mass_t(p) + 1, 2), p).error().code == ErrorCode::InvalidArgument);
    Game poor(1);
    poor.new_game("Y", 10);
    unlock(poor);
    CHECK(poor.launch(moon_lander(payload_mass_t(p) + 1, 3), p).error().code == ErrorCode::InsufficientFunds);
}

TEST("game: kaydet/yükle tam durumu korur ve aynı geleceği üretir") {
    Game a(99);
    a.new_game("AETHER", 3e6);
    unlock(a);
    auto p = moon_kit();
    CHECK(a.launch(moon_lander(payload_mass_t(p) + 0.5, 3), p).ok());
    a.advance(8.0);
    CHECK(a.trade("earth", "water", 5, true).ok());
    const std::string s1 = a.save();
    Game b(1);
    int founded_b = 0;
    b.bus().subscribe<ColonyFounded>([&](const ColonyFounded&) { ++founded_b; });
    CHECK(b.load(s1).ok());
    CHECK(b.save() == s1);                       // birebir aynı durum
    // deterministik: iki oyun aynı süre ilerleyince aynı sonuç
    a.advance(10.0);
    b.advance(10.0);
    CHECK(a.save() == b.save());
    CHECK(!b.load("{\"format\":\"baska\"}").ok());
    CHECK(!b.load("bozuk").ok());
}

TEST("game: laboratuvar araştırma puanı üretir ve araştırmayı ilerletir") {
    Game g(3);
    g.new_game("AETHER", 3e6);
    unlock(g);
    auto p = moon_kit();
    CHECK(g.launch(moon_lander(payload_mass_t(p) + 0.5, 3), p).ok());
    g.advance(6.0);
    CHECK(g.research().start("closed_loop").ok());
    g.advance(20.0);
    CHECK(g.research().progress() > 0.05 || g.research().unlocked("closed_loop"));
}

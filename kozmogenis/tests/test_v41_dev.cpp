#include <algorithm>
#include <cmath>
#include <set>

#include "kozmo/nova.hpp"
#include "kozmo/world.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::world;

namespace {
bool land(Expedition& e) {
    if (!e.sit().ok() || !e.begin_descent().ok()) return false;
    if (!e.craft().set_engines(true).ok() || !e.craft().set_mode(craft::FlightMode::LandingAssist).ok()) return false;
    for (int i = 0; i < 1500 && e.craft().phase() == craft::FlightPhase::Flying; ++i) e.tick(1.0);
    return e.craft().phase() == craft::FlightPhase::Landed;
}
}  // namespace

TEST("inşaat: parça maliyetleri, malzeme düşümü, bağlantı sırası ve kayıt") {
    using colony::ModuleType;
    const auto hab = build::total(build::blueprint(ModuleType::Habitat));
    CHECK(hab.iron_t > 5 && hab.labor_h > 50 && hab.power_kw > 0 && hab.durability > 0 && hab.durability < 1);
    CHECK(build::total(build::blueprint(ModuleType::SolarArray)).labor_h < hab.labor_h);
    colony::Colony c("x", "mars", 227.9, true);
    econ::Wallet w(1e6);
    build::Manager m;
    CHECK(m.start(ModuleType::Habitat, c, w, {}, 0).error().code == ErrorCode::InsufficientResources);   // demir yok
    c.add_resource("iron", 40);
    c.add_resource("water", 5);
    c.add_resource("oxygen", 1);
    CHECK(m.start(ModuleType::FissionReactor, c, w, {}, 0).error().code == ErrorCode::Locked);
    auto id = m.start(ModuleType::Habitat, c, w, {}, 0);
    CHECK(id.ok());
    CHECK_NEAR(c.resource("iron"), 40 - hab.iron_t, 1e-9);
    CHECK_NEAR(w.balance(), 1e6 - hab.credits, 1e-6);
    m.work(hab.labor_h + 5);
    CHECK(m.complete(c, {}).empty());                       // enerji kaynağı yok: bağlantı bekliyor
    CHECK(m.projects()[0].state == build::State::WaitingConnection && m.projects()[0].missing.find("enerji") != std::string::npos);
    CHECK(m.start(ModuleType::SolarArray, c, w, {}, 0).ok());
    m.work(1000);
    auto done = m.complete(c, {});
    CHECK(done.size() == 2);                                // güneş dizisi bitince habitat da bağlanır
    CHECK(c.housing() == 6);
    CHECK(m.start_reinforcement(c, w, 0).ok());
    CHECK(!m.start_reinforcement(c, w, 0).ok());
    m.work(1000);
    (void)m.complete(c, {});
    CHECK(m.reinforced() && m.storm_damage_factor() < 0.5);
    build::Manager copy;
    CHECK(copy.from_json(json::parse(m.to_json().dump()).value()).ok());
    CHECK(copy.reinforced() && copy.projects().size() == 3);
}

TEST("su geri dönüşüm sistemi su tüketimini %85'ten ~%98 geri kazanıma çeker (ISS 2023)") {
    Rng r1(1), r2(1);
    auto mk = [](bool recycler, Rng& rng) {
        colony::Colony c("c", "moon", 149.6, false);
        for (auto t : {colony::ModuleType::Habitat, colony::ModuleType::SolarArray, colony::ModuleType::SolarArray, colony::ModuleType::SolarArray})
            (void)c.add_module(t, {});
        if (recycler) (void)c.add_module(colony::ModuleType::WaterRecycler, {});
        c.add_resource("water", 10);
        c.add_resource("oxygen", 1);
        c.add_resource("food", 1);
        for (int i = 0; i < 4; ++i) c.add_colonist("k" + std::to_string(i), colony::Job::Engineer, 0.5, rng);
        for (int h = 0; h < 240; ++h) c.tick(1.0, std::fmod(h, 24.0), rng, nullptr);
        return 10.0 - c.resource("water");
    };
    const double used_plain = mk(false, r1), used_rec = mk(true, r2);
    CHECK(used_plain > 0 && used_rec < used_plain * 0.5);
}

TEST("§7.1 çöl gezegeni (Mars): iniş -> su -> koloni -> enerji/habitat/su -> fırtına -> hasar raporu -> güçlendirme") {
    Game g(71);
    g.new_game("KOZMOGENİS", 1e6);
    Expedition e(g, "mars", craft::preset("lander"));
    CHECK(e.init().ok());
    nova::Nova nova(g);
    nova.attach(&e);
    CHECK(nova.ask("iniş riski ne?").text.find("Mars") != std::string::npos);
    CHECK(land(e));
    CHECK(!e.found_colony().ok());                           // su bulunmadan kurulamaz
    CHECK(nova.ask("koloni kur").pending_action == std::nullopt);
    CHECK(e.stand().ok() && e.exit_craft().ok());
    auto w = e.scan_water();
    CHECK(w.ok() && e.water_found());
    CHECK(nova.ask("koloni kur").pending_action.has_value());
    CHECK(nova.ask("onayla").text.find("kuruldu") != std::string::npos);
    CHECK(e.colony() && e.colony()->population() == 4 && e.colony()->housing() == 0);
    CHECK(!e.settlement().find(life::District::Housing)->built);
    CHECK(!e.walk_to(e.settlement().find(life::District::Admin)->id).ok());   // arsa: henüz yok
    // NOVA ile inşaat (onaylı)
    for (const char* q : {"güneş paneli kur", "habitat inşa et", "su geri dönüşüm sistemi kur"}) {
        auto r = nova.ask(q);
        CHECK(r.pending_action.has_value());
        CHECK(nova.ask("onayla").text.find("İnşaat başladı") != std::string::npos);
    }
    CHECK(e.construction().projects().size() == 3);
    CHECK(e.enter_craft().ok());
    bool construct_seen = false;
    for (int h = 0; h < 24 * 30; ++h) {
        e.tick(3600.0);
        for (const auto& n : e.society().npcs()) construct_seen |= n.intent == life::Intent::Construct;
    }
    CHECK(construct_seen);
    CHECK(e.colony()->housing() >= 6);
    CHECK(e.settlement().find(life::District::Housing)->built && e.settlement().find(life::District::Water)->built);
    int done = 0;
    for (const auto& q : e.construction().projects()) done += q.state == build::State::Done;
    CHECK(done == 3);
    // fırtınalar ve hasar raporu (uzun bekleme; NPC'ler sığınağa geçer)
    int storms_seen = 0;
    bool sheltered = false;
    for (int h = 0; h < 24 * 200 && storms_seen < 1; ++h) {
        e.tick(3600.0);
        for (const auto& x : e.weather())
            if (x.kind == challenge::Weather::DustStorm) {
                storms_seen = 1;
                for (const auto& n : e.society().npcs()) sheltered |= n.intent == life::Intent::Shelter;
            }
    }
    CHECK(storms_seen == 1 && sheltered);
    for (int h = 0; h < 24 * 6; ++h) e.tick(3600.0);
    CHECK(nova.ask("hasar raporu").text.find("Fırtına koruması: YOK") != std::string::npos);
    CHECK(e.reinforce().ok());
    for (int h = 0; h < 24 * 10; ++h) e.tick(3600.0);
    CHECK(e.construction().reinforced());
    CHECK(nova.ask("hasar raporu").text.find("koruması: var") != std::string::npos);
    // kayıt/yükleme inşaatı da taşır
    Expedition e2(g, "mars", craft::preset("lander"));
    CHECK(e2.init().ok());
    CHECK(e2.from_json(json::parse(e.to_json().dump()).value()).ok());
    CHECK(e2.construction().reinforced() && e2.water_found());
}

TEST("§7.2 buz dünyası (Titan): paraşüt sonrası iniş, termal gereksinim, numune, araç laboratuvarı") {
    Game g(72);
    g.new_game("KOZMOGENİS", 1e6);
    craft::Spacecraft c = craft::preset("lander");
    CHECK(c.install("science_lab").ok());
    Expedition e(g, "titan", c);
    CHECK(e.init().ok());
    auto p = e.profile();
    CHECK(std::find(p[challenge::Category::Temperature].missing.begin(), p[challenge::Category::Temperature].missing.end(), "termal giysi") !=
          p[challenge::Category::Temperature].missing.end());
    CHECK(std::find(p.weather.begin(), p.weather.end(), challenge::Weather::IceStorm) != p.weather.end());
    CHECK(land(e));
    CHECK(e.stand().ok());
    e.player().eq.thermal_suit = true;                      // termal ekipman kontrolü
    CHECK(e.exit_craft().ok());
    CHECK(e.collect_sample().ok() && e.collect_sample().ok());
    e.tick(1800);
    CHECK(e.player().body.alive && e.player().body.health > 0.95);
    CHECK(e.enter_craft().ok());
    auto a = e.analyze_onboard();
    CHECK(a.ok() && e.player().samples == 1);
    // termal giysisiz dışarı çıkış zarar verir (-179 °C < EMU sınırı -157 °C)
    e.player().eq.thermal_suit = false;
    CHECK(e.exit_craft().ok());
    e.tick(1800);
    CHECK(e.player().body.health < 0.95);
}

TEST("§6.3 görevlendirme: NOVA onaylı emir verir, NPC kabul eder ya da sorun bildirir") {
    Game g(63);
    g.new_game("KOZMOGENİS", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init(false).ok());
    nova::Nova nova(g);
    nova.attach(&e);
    e.tick(600);
    // bir mühendis bitkin
    for (const auto& k : e.colony()->colonists())
        if (k.job == colony::Job::Engineer) {
            e.colony()->colonist(k.id)->needs.fatigue = 0.95;
            break;
        }
    auto r = nova.ask("mühendislere görev ver");
    CHECK(r.pending_action.has_value());
    auto ok = nova.ask("onayla");
    CHECK(ok.text.find("1 kişi görevi kabul etti") != std::string::npos);
    CHECK(ok.text.find("yorgun") != std::string::npos);
    e.tick(300);
    int on_mission = 0;
    for (const auto& n : e.society().npcs()) on_mission += n.intent == life::Intent::Mission;
    CHECK(on_mission == 1);
    for (int i = 0; i < 6 * 60; ++i) e.tick(60.0);
    on_mission = 0;
    for (const auto& n : e.society().npcs()) on_mission += n.mission >= 0;
    CHECK(on_mission == 0);                                   // görev bitti, NPC kendi programına döndü
    CHECK(nova.ask("bilim insanlarına görev ver").pending_action.has_value());
    CHECK(nova.ask("iptal").text.find("iptal") != std::string::npos);
}

TEST("uçuş: Ay'dan yörüngeye kalkış (Apollo LM ~1.85 km/s), Mars'tan bu araçla olmaz; kenetlenme") {
    for (const char* b : {"moon", "mars"}) {
        auto env = challenge::body_environment(b).value();
        auto c = craft::preset("lander");
        Rng rng(1);
        CHECK(c.sit().ok());
        CHECK(c.launch_to_orbit(15000).ok());
        const double f0 = c.fuel(), dry = c.specs().dry_t;
        const auto ph = c.fly_until_orbit(env, rng, 3000, 0.05);
        if (std::string(b) == "moon") {
            CHECK(ph == craft::FlightPhase::Orbit);
            const double dv = 355 * 9.80665 * std::log((dry + f0) / (dry + c.fuel()));
            CHECK(dv > 1700 && dv < 2000);
            CHECK(c.set_target("istasyon Kapı").ok());
            CHECK(c.set_mode(craft::FlightMode::DockingAssist).ok());
            CHECK(c.begin_docking(400, 0).ok());
            for (int i = 0; i < 60000 && !c.docking().docked; ++i) c.step_docking(0.1);
            CHECK(c.docking().docked && c.faults().empty());
            // manuel, hızlı yaklaşma: çarpışma hasarı
            CHECK(c.set_mode(craft::FlightMode::Manual).ok());
            CHECK(c.begin_docking(30, 2.0).ok());
            for (int i = 0; i < 400; ++i) c.step_docking(0.1);
            bool hit = false;
            for (auto f : c.faults()) hit |= f == craft::Fault::CollisionDamage;
            CHECK(hit);
        } else {
            CHECK(ph != craft::FlightPhase::Orbit);            // Mars yörüngesi ~4 km/s ister; aracın bütçesi 3.5 km/s
        }
    }
    auto ground = craft::preset("lander");
    CHECK(!ground.begin_docking(100, 0).ok());                // yüzeyde kenetlenme yok
}

TEST("araç sınıfları: V41 §2.1 kataloğu, V1-V4 sürümleri, kurgusal motor ayrı işaretli") {
    std::set<craft::CraftClass> classes;
    std::set<craft::Tier> tiers;
    for (const auto& k : craft::preset_keys()) {
        auto c = craft::preset(k);
        classes.insert(c.craft_class());
        tiers.insert(c.tier());
        CHECK(c.cockpit() != craft::CockpitLevel::None && c.specs().thrust_kn > 0);
        CHECK(c.installed().size() >= 9);
    }
    CHECK(craft::preset_keys().size() >= 19);
    CHECK(classes.size() == 6 && tiers.size() == 4);
    CHECK(craft::preset("scout").tier() == craft::Tier::V1Basic);
    CHECK(craft::preset("deep").tier() == craft::Tier::V4Experimental);
    bool fiction = false;
    for (const auto& p : craft::preset("fusion").specs().problems) fiction |= p.find("kurgusal") != std::string::npos;
    CHECK(fiction);
    for (const auto& p : craft::preset("deep").specs().problems) CHECK(p.find("kurgusal") == std::string::npos);   // NERVA gerçek test edildi
}

TEST("NOVA: eksik ve tahmini veriyi açıkça bildirir") {
    Game g(80);
    g.new_game("KOZMOGENİS", 1e6);
    Payload p;
    p.modules = {colony::ModuleType::Habitat};
    p.cargo = {{"water", 1.0}, {"oxygen", 0.2}};
    p.crew = {{"Ada", colony::Job::Farmer}};
    CHECK(g.found_outpost("moon", p).ok());
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init(false).ok());
    CHECK(e.colony_report().find("gıda ? (kayıt yok)") != std::string::npos);
    Game g2(81);
    g2.new_game("x", 1e6);
    Expedition m(g2, "mercury", craft::preset("lander"));
    CHECK(m.init().ok());
    CHECK(m.environment_report().find("VERİ UYARISI") != std::string::npos);
    Expedition moon(g2, "moon", craft::preset("lander"));
    CHECK(moon.init().ok());
    CHECK(moon.environment_report().find("VERİ UYARISI") == std::string::npos);   // Ay değeri ölçüm (Chang'e-4)
}

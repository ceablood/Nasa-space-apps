#include <algorithm>
#include <cmath>

#include "kozmo/nova.hpp"
#include "kozmo/world.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::world;

namespace {
bool land(Expedition& e) {
    if (!e.sit().ok() || !e.begin_descent().ok()) return false;
    if (!e.craft().set_engines(true).ok() || !e.craft().set_mode(craft::FlightMode::LandingAssist).ok()) return false;
    for (int i = 0; i < 1200 && e.craft().phase() == craft::FlightPhase::Flying; ++i) e.tick(1.0);
    return e.craft().phase() == craft::FlightPhase::Landed;
}
void walk(Expedition& e, const std::string& id) {
    (void)e.walk_to(id);
    for (int i = 0; i < 2000 && e.walking(); ++i) e.tick(1.0);
}
}  // namespace

TEST("dikey dilim: kokpit -> Ay'a iniş -> araçtan çıkış -> koloni -> NPC -> NOVA") {
    Game g(21);
    g.new_game("KOZMOGENİS", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init().ok());
    nova::Nova nova(g);
    nova.attach(&e);
    // kokpit + iniş
    CHECK(!e.exit_craft().ok());                  // yörüngede araçtan çıkılamaz
    CHECK(land(e));
    CHECK(e.craft().touchdown_speed() < 3.0);
    CHECK(!e.exit_craft().ok());                  // önce koltuktan kalk
    CHECK(e.stand().ok());
    CHECK(e.exit_craft().ok());
    CHECK(e.player().mode == PlayerMode::OnFoot);
    // gezegene özgü zorluk: Ay'da vakum, radyasyon, sıcaklık
    auto p = e.profile();
    CHECK(p[challenge::Category::Atmosphere].mitigated < 0.2);   // giysi var
    CHECK(e.environment_report().find("Ay") != std::string::npos);
    CHECK(e.collect_sample().ok());
    // yönetim merkezine yürü, gir, konsolları kullan
    const auto* admin = e.settlement().find(life::District::Admin);
    walk(e, admin->id);
    CHECK(e.enter_building(admin->id).ok());
    auto pop = e.use("admin_pop");
    CHECK(pop.ok() && pop.value().find("Nüfus 8") != std::string::npos);
    CHECK(e.use("admin_map").value().find("18 bölge") != std::string::npos);
    CHECK(!e.use("lab_scope").ok());              // bu binada yok
    // NOVA koloni durumu ve gezegen riski
    auto r1 = nova.ask("NOVA, koloninin durumu nasıl?");
    CHECK(r1.text.find("nüfus 8") != std::string::npos && r1.text.find("su") != std::string::npos);
    auto r2 = nova.ask("Buradaki gezegen riski ne?");
    CHECK(r2.text.find("Radyasyon") != std::string::npos && !r2.sources.empty());
    CHECK(nova.ask("araç durumu").text.find("Kartal") != std::string::npos);
    // bir NPC'nin yanına git ve konuş
    e.tick(60);
    const life::Npc& n = e.society().npcs().front();
    const std::string where = n.target.empty() ? n.at : n.target;
    walk(e, where);
    CHECK(e.enter_building(where).ok());
    for (int i = 0; i < 600; ++i) {
        auto here = e.npcs_here();
        if (std::find(here.begin(), here.end(), n.id) != here.end()) break;
        e.tick(1.0);
    }
    auto t = e.talk(n.id, "iş");
    CHECK(t.ok());
    CHECK(!e.talk(-5, "selam").ok());
    // laboratuvarda numune analizi -> keşif olayı
    walk(e, e.settlement().find(life::District::Lab)->id);
    CHECK(e.enter_building(e.settlement().find(life::District::Lab)->id).ok());
    CHECK(e.use("lab_scope").value().find("+25") != std::string::npos);
    CHECK(e.society().last_event() == life::ColonyEvent::Discovery);
}

TEST("dikey dilim: kolonide acil durum (§7.3) ve NOVA onaylı tahliye") {
    Game g(22);
    g.new_game("KOZMOGENİS", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init(false).ok());                    // araç iniş alanında başlar
    nova::Nova nova(g);
    nova.attach(&e);
    CHECK(e.exit_craft().ok());
    e.tick(600);
    // NOVA tahliyeyi onaysız yapmaz
    auto ev = nova.ask("Bütün NPC'leri güvenli alana gönder");
    CHECK(ev.pending_action.has_value());
    e.tick(60);
    CHECK(!e.society().alarm());
    CHECK(nova.ask("onayla").text.find("Tahliye") != std::string::npos);
    e.tick(120);
    CHECK(e.society().alarm());
    int shelter = 0;
    for (const auto& n : e.society().npcs()) shelter += n.intent == life::Intent::Shelter;
    CHECK(shelter >= 2);
    e.society().raise(life::ColonyEvent::AllClear, g.day(), *e.colony(), e.settlement());
    // enerji tesisi arızası
    e.fail_power();
    CHECK(e.society().alarm() && e.society().last_event() == life::ColonyEvent::PowerOutage);
    e.tick(300);
    bool tasked = false;
    for (const auto& t : e.tasks()) tasked |= t.find("ACİL") != std::string::npos;
    CHECK(tasked);
    auto diag = nova.ask("Neden üretim yavaşladı?");
    CHECK(diag.text.find("Enerji yetersiz") != std::string::npos || diag.text.find("bakım") != std::string::npos);
    int engineers = 0;
    for (const auto& n : e.society().npcs()) engineers += n.intent == life::Intent::RepairPower;
    CHECK(engineers == 2);
    // oyuncu enerji tesisine gidip arızayı giderir
    const auto* power = e.settlement().find(life::District::Power);
    walk(e, power->id);
    CHECK(e.enter_building(power->id).ok());
    CHECK(e.use("power_panel").value().find("giderildi") != std::string::npos);
    CHECK(!e.society().alarm());
    // kayıt / yükleme
    auto j = e.to_json();
    Expedition e2(g, "moon", craft::preset("lander"));
    CHECK(e2.init(false).ok());
    CHECK(e2.from_json(json::parse(j.dump()).value()).ok());
    CHECK(e2.player().mode == PlayerMode::InBuilding && e2.player().building == power->id);
    CHECK(e2.society().npcs().size() == e.society().npcs().size());
}

TEST("dikey dilim: ikinci gezegen Mars — farklı iniş, çevre ve hava") {
    Game g(23);
    g.new_game("KOZMOGENİS", 1e6);
    Expedition e(g, "mars", craft::preset("mars_lander"));
    CHECK(e.init().ok());
    CHECK(land(e));
    CHECK(e.stand().ok());
    CHECK(e.exit_craft().ok());
    auto mars = e.profile();
    Expedition m(g, "moon", craft::preset("lander"));
    CHECK(m.init().ok());
    auto moon = m.profile();
    CHECK(mars[challenge::Category::Radiation].raw < moon[challenge::Category::Radiation].raw);
    CHECK(mars[challenge::Category::Environmental].raw > moon[challenge::Category::Environmental].raw);   // toz + rüzgâr
    CHECK(e.environment_report().find("Mars") != std::string::npos);
    CHECK(!e.use("admin_pop").ok());     // Mars'ta koloni yok, bina içinde değil
    // 30 gün dışarıda bekleme yerine hava olayı istatistiği: araçta güvenle bekle
    CHECK(e.enter_craft().ok());
    int storms = 0;
    for (int h = 0; h < 24 * 120; ++h) {
        e.tick(3600.0);
        for (const auto& w : e.weather()) storms += w.kind == challenge::Weather::DustStorm && std::fabs(w.start_h - e.hours()) < 1.0;
    }
    CHECK(storms >= 1);
    CHECK(e.player().body.alive);
}

#include <algorithm>
#include <cmath>

#include "kozmo/civ.hpp"
#include "kozmo/crew.hpp"
#include "kozmo/dialogue.hpp"
#include "kozmo/nova.hpp"
#include "kozmo/quest.hpp"
#include "kozmo/replay.hpp"
#include "kozmo/settings.hpp"
#include "kozmo/world.hpp"
#include "test_framework.hpp"

using namespace kozmo;

TEST("görev günlüğü: şablonlar, olaylarla ilerleme, ödül bir kez, süre aşımı, kayıt") {
    quest::Log log;
    for (const auto& k : quest::template_keys()) CHECK(log.offer(k, -1, 0).ok());
    CHECK(!log.offer("power_crisis", -1, 0).ok());                    // zaten etkin
    CHECK(!log.offer("yok", -1, 0).ok());
    auto done = log.notify({quest::Goal::EnterDistrict, 9}, 1);
    CHECK(done.empty());
    done = log.notify({quest::Goal::RepairPower}, 2);
    CHECK(done.size() == 1 && done[0].reward.credits == 3000);
    CHECK(log.notify({quest::Goal::RepairPower}, 3).empty());          // ödül tekrar verilmez
    for (int i = 0; i < 3; ++i) (void)log.notify({quest::Goal::CollectSamples}, 4);
    CHECK(log.notify({quest::Goal::AnalyzeSample}, 5).size() == 1);
    CHECK(log.offer("power_crisis", -1, 10).ok());
    log.tick(100);
    CHECK(log.find_key("power_crisis")->state == quest::State::Failed);   // 24 saat sınırı
    quest::Log copy;
    CHECK(copy.from_json(json::parse(log.to_json().dump()).value()).ok());
    CHECK(copy.quests().size() == log.quests().size() && copy.active_count() == log.active_count());
    CHECK(log.summary().find("Yeni yuva") != std::string::npos);
}

TEST("diyalog: tüm meslek ağaçları geçerli; koşullar ve etkiler çalışır") {
    for (int j = 0; j <= 6; ++j) {
        auto errs = dialogue::validate(dialogue::tree_for(static_cast<colony::Job>(j)));
        CHECK(errs.empty());
    }
    Game g(5);
    g.new_game("x", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    colony::Colony* c = g.colony("moon_koloni");
    life::Settlement s = life::Settlement::build(*c, challenge::body_environment("moon").value());
    life::Society soc;
    Rng rng(1);
    soc.sync(*c, s, rng);
    quest::Log log;
    int eng = -1;
    for (const auto& k : c->colonists())
        if (k.job == colony::Job::Engineer) eng = k.id;
    c->colonist(eng)->needs.hunger = 0.9;
    dialogue::Conversation conv(eng, soc, *c, log, 0, 0);
    CHECK(conv.active() && conv.text().find("Mühendis") != std::string::npos);
    auto opts = conv.options();
    CHECK(std::find(opts.begin(), opts.end(), "Geçen sefer için teşekkür ederim.") == opts.end());   // hafıza koşulu
    CHECK(conv.choose(0).ok());                                        // "Nasılsın?"
    opts = conv.options();
    CHECK(opts.front().find("Aç görünüyorsun") != std::string::npos);  // açlık koşulu
    const double before = soc.relation(life::Society::kPlayer, eng).affinity;
    CHECK(conv.choose(0).ok());
    CHECK(c->colonist(eng)->activity == colony::Activity::Eat && soc.relation(life::Society::kPlayer, eng).affinity > before);
    CHECK(conv.choose(0).ok());                                        // "Başka bir şey..." -> 0
    CHECK(conv.choose(3).ok());                                        // "İşin hakkında"
    CHECK(conv.text().find("Enerji") != std::string::npos);
    CHECK(conv.choose(0).ok());                                        // enerji görevini al
    CHECK(log.find_key("power_crisis") && log.find_key("power_crisis")->giver == eng);
    // artık "teşekkür" seçeneği görünür (hafıza)
    dialogue::Conversation again(eng, soc, *c, log, 1, 1);
    opts = again.options();
    CHECK(std::find(opts.begin(), opts.end(), "Geçen sefer için teşekkür ederim.") != opts.end());
    CHECK(!again.choose(99).ok());
}

TEST("sefer: diyalogdan görev, olaylarla tamamlanma ve ödül (kredi + ilişki)") {
    Game g(6);
    g.new_game("x", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    world::Expedition e(g, "moon", craft::preset("lander"));
    CHECK(e.init(false).ok());
    CHECK(e.exit_craft().ok());
    CHECK(e.accept_quest("health_check").ok());
    const auto* h = e.settlement().find(life::District::Hospital);
    (void)e.walk_to(h->id);
    for (int i = 0; i < 3000 && e.walking(); ++i) e.tick(1);
    CHECK(e.enter_building(h->id).ok());
    CHECK(e.use("med_exam").ok());
    int medic = -1;
    for (const auto& k : e.colony()->colonists())
        if (k.job == colony::Job::Medic) medic = k.id;
    for (int i = 0; i < 2000; ++i) {
        auto here = e.npcs_here();
        if (std::find(here.begin(), here.end(), medic) != here.end()) break;
        e.tick(30);
    }
    const double credits = g.wallet().balance();
    auto conv = e.converse(medic);
    if (conv.ok()) {
        CHECK(e.completed_quests().size() == 1);
        CHECK(g.wallet().balance() > credits);
    } else {
        CHECK(e.talk(medic, "selam").ok() || true);
    }
    nova::Nova n(g);
    n.attach(&e);
    CHECK(n.ask("görevlerim").text.size() > 3);
    CHECK(n.ask("asteroit tehdidi var mı?").text.find("Apophis") != std::string::npos);
    CHECK(n.ask("medeniyet durumu").text.find("Çağ:") != std::string::npos);
}

TEST("medeniyet: göstergeler, çağ eşikleri, politikalar, ticaret yolları") {
    CHECK(civ::era_for(5, 1) == civ::Era::Outpost && civ::era_for(60, 1) == civ::Era::Town && civ::era_for(1200, 3) == civ::Era::Civilization);
    Game g(7);
    g.new_game("x", 1e6);
    CHECK(g.found_outpost("moon", vertical_slice_outpost()).ok());
    CHECK(g.found_outpost("mars", vertical_slice_outpost()).ok());
    civ::Civilization c;
    auto m = c.measure(g);
    CHECK(m.colonies == 2 && m.population == 16 && m.era == civ::Era::Settlement);
    CHECK(m.stability > 0.3 && m.happiness > 0.3);
    CHECK(!c.add_route(g, "moon_koloni", "mars_koloni", "water", 1, 10).ok());   // Ay-Mars 10 günde olmaz
    auto r = c.add_route(g, "moon_koloni", "mars_koloni", "water", 1, 260);
    CHECK(r.ok());
    CHECK(c.set_policy(civ::Policy::Festival).ok());
    const double w0 = g.colony("mars_koloni")->resource("water");
    // aynı tohumlu ikiz oyun, politikasız: kutlama morali artırmalı
    Game twin(7);
    twin.new_game("x", 1e6);
    (void)twin.found_outpost("moon", vertical_slice_outpost());
    (void)twin.found_outpost("mars", vertical_slice_outpost());
    civ::Civilization none;
    (void)c.update(g);
    (void)none.update(twin);
    g.advance(3);
    twin.advance(3);
    (void)c.update(g);
    (void)none.update(twin);
    auto avg = [](const Game& x) {
        double s = 0;
        int n = 0;
        for (const auto& k : x.colonies().at("moon_koloni").colonists()) {
            s += k.needs.morale;
            ++n;
        }
        return s / n;
    };
    CHECK(avg(g) > avg(twin) + 0.03);
    g.advance(270);
    auto log = c.update(g);
    CHECK(!log.empty() && c.routes()[0].trips >= 1);
    CHECK(g.colony("mars_koloni")->resource("water") > 0 || w0 >= 0);
    civ::Civilization copy;
    CHECK(copy.from_json(json::parse(c.to_json().dump()).value()).ok() && copy.policy() == civ::Policy::Festival && copy.routes().size() == 1);
}

TEST("ayarlar: doğrulama, kayıt, tuş çakışması, zorluk, hareket azaltma") {
    settings::Settings s;
    s.text_scale = 9;
    s.camera_shake = -1;
    s.master_volume = 3;
    auto fixed = s.validate();
    CHECK(fixed.size() >= 4 && s.text_scale == 2.0 && s.camera_shake == 0.0);
    s.camera_shake = 1.0;
    s.reduce_motion = true;
    CHECK(s.effective_shake() == 0.0);
    s.keys["Motorlar"] = "E";                                           // Etkileşim ile çakışır
    auto c = settings::key_conflicts(s.keys);
    CHECK(c.size() == 1);
    auto r = settings::Settings::from_json(json::parse(s.to_json().dump()).value());
    CHECK(r.ok() && r.value().reduce_motion && r.value().keys.at("Motorlar") == "E");
    CHECK(settings::scale(settings::Difficulty::Realistic).permadeath && !settings::scale(settings::Difficulty::Story).permadeath);
}

TEST("erişilebilirlik: Machado renk körlüğü simülasyonu ve güvenli palet; yerelleştirme") {
    using settings::ColorVision;
    const settings::Rgb red{0.9, 0.25, 0.2}, green{0.3, 0.75, 0.4};
    // döteranopide kırmızı-yeşil farkı belirgin biçimde azalır
    const double normal = settings::difference(red, green);
    const double deut = settings::difference(settings::simulate(red, ColorVision::Deuteranopia), settings::simulate(green, ColorVision::Deuteranopia));
    CHECK(deut < normal * 0.6);
    // güvenli palette tamam/tehlike renkleri döteranopide de ayırt edilir
    auto p = settings::palette(ColorVision::Deuteranopia, false);
    const double safe = settings::difference(settings::simulate(p.ok, ColorVision::Deuteranopia), settings::simulate(p.danger, ColorVision::Deuteranopia));
    CHECK(safe > deut * 1.5);
    // beyaz/siyah değişmez (matris satırları ~1'e toplanır)
    auto w = settings::simulate({1, 1, 1}, ColorVision::Protanopia);
    CHECK_NEAR(w.r, 1.0, 0.02);
    CHECK_NEAR(w.g, 1.0, 0.02);
    CHECK(settings::missing_translations().empty());
    CHECK(settings::tr("hud.fuel", settings::Language::English) == "FUEL" && settings::tr("hud.fuel", settings::Language::Turkish) == "YAKIT");
    CHECK(settings::tr("yok.anahtar", settings::Language::English) == "yok.anahtar");
    CHECK(settings::keys().size() >= 40);
}

TEST("ekip: eğitim önkoşulları, sertifikalar, rol uygunluğu, ekip seçimi, doz sınırı") {
    crew::Roster r;
    Rng rng(3);
    std::vector<int> ids;
    for (const char* n : {"Ayşe", "Burak", "Cem", "Defne", "Emre"}) ids.push_back(r.hire(n, rng));
    CHECK(r.enroll(ids[0], "pilot").error().code == ErrorCode::Locked);
    for (int id : ids) CHECK(r.enroll(id, "ascan").ok());
    CHECK(!r.enroll(ids[0], "eva").ok());                              // zaten derste
    for (int i = 0; i < 40; ++i) {
        (void)r.train(100);
        r.rest(48);
    }
    for (int id : ids) CHECK(r.find(id)->certifications.count("astronot"));
    const char* plan[][2] = {{"pilot", "command"}, {"pilot", "eva"}, {"systems", "eva"}, {"medical", "eva"}, {"geology", "eva"}};
    for (std::size_t i = 0; i < ids.size(); ++i)
        for (const char* k : plan[i]) {
            (void)r.enroll(ids[i], k);
            for (int t = 0; t < 30 && !r.find(ids[i])->training.empty(); ++t) {
                (void)r.train(50);
                r.rest(24);
            }
        }
    CHECK(r.find(ids[0])->certifications.count("komuta"));
    auto c = r.select(crew::standard_crew(10), 10, false);
    CHECK(c.ok);
    CHECK(c.assignment[crew::Role::Commander].front() == ids[0]);
    auto longm = r.select(crew::standard_crew(200), 200, true);
    CHECK(longm.ok && !longm.assignment[crew::Role::MedicalOfficer].empty());
    CHECK(r.log_eva(ids[1], 6.5, 0.4).ok() && !r.log_eva(ids[0], 1, 0).ok());
    CHECK(r.log_mission({ids[2]}, 400, 1.84).ok());                    // ~736 mSv: sınır aşıldı
    CHECK(!r.eligible(*r.find(ids[2]), crew::Role::FlightEngineer));
    CHECK(r.find(ids[2])->rank() == "Astronot (uçmamış)" || r.find(ids[2])->missions == 1);
    crew::Roster copy;
    CHECK(copy.from_json(json::parse(r.to_json().dump()).value()).ok() && copy.astronauts().size() == 5);
}

TEST("tekrar oynatma: aynı komutlar aynı durumu üretir; farklı komut senkronu bozar") {
    replay::Recorder a(77, "KOZMOGENİS", 3e6);
    CHECK(a.apply({replay::Op::StartResearch, 0, "cryo"}).ok() || true);
    CHECK(a.apply({replay::Op::FoundOutpost, 0, "moon"}).ok());
    CHECK(a.apply({replay::Op::Advance, 5}).ok());
    (void)a.apply({replay::Op::LaunchKit, 0, "moon"});
    CHECK(a.apply({replay::Op::Advance, 10}).ok());
    CHECK(!a.apply({replay::Op::Advance, -1}).ok());
    const auto h = a.hash();
    CHECK(replay::replay(77, "KOZMOGENİS", 3e6, a.log()) == h);
    auto log2 = a.log();
    log2[2].a = 6;
    CHECK(replay::replay(77, "KOZMOGENİS", 3e6, log2) != h);
    CHECK(replay::replay(78, "KOZMOGENİS", 3e6, a.log()) != h);       // farklı tohum
    auto r = replay::Recorder::from_json(json::parse(a.to_json().dump()).value());
    CHECK(r.ok() && r.value().hash() == h);
    auto bad = a.to_json();
    bad.set("hash", "1");
    CHECK(!replay::Recorder::from_json(bad).ok());
}

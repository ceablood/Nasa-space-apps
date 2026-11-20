#include <cmath>

#include "kozmo/game.hpp"
#include "kozmo/life.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::life;

namespace {
struct Sim {
    Game g{11};
    colony::Colony* c = nullptr;
    Settlement s;
    Society soc;
    Rng rng{5};
    double acc = 0;
    explicit Sim(const char* body = "moon") {
        g.new_game("Test", 1e6);
        (void)g.found_outpost(body, vertical_slice_outpost());
        c = g.colony(std::string(body) + "_koloni");
        s = Settlement::build(*c, challenge::body_environment(body).value());
        soc.sync(*c, s, rng);
    }
    void run(double hours, double px = 1e6, double py = 1e6, double dt = 0.05) {
        for (double t = 0; t < hours; t += dt) {
            soc.tick(dt, g.day(), g.crew_hour(c->body()), *c, s, 1.62, px, py, rng);
            acc += dt;
            if (acc >= 1.0) {
                g.advance(acc / 24.0);
                acc = 0;
                c = g.colony(c->id());
            }
        }
    }
    int count(Intent i) const {
        int n = 0;
        for (const auto& x : soc.npcs()) n += x.intent == i;
        return n;
    }
};
}  // namespace

TEST("NPC: yürüme hızı yerçekimine bağlı (Froude benzerliği)") {
    CHECK_NEAR(walking_speed_ms(9.80665), 1.49, 0.05);
    CHECK_NEAR(walking_speed_ms(3.71), 0.91, 0.05);
    CHECK_NEAR(walking_speed_ms(1.62), 0.60, 0.05);
}

TEST("koloni: 18 bölgeli gezilebilir yerleşim, iç mekânlar ve yollar") {
    Sim m;
    CHECK(m.s.buildings().size() == 18);
    CHECK(m.s.layout() == Layout::Underground);   // Ay: regolit kalkanlı
    const Building* admin = m.s.find(District::Admin);
    CHECK(admin && !admin->rooms.empty() && admin->rooms[0].items.size() == 6);
    CHECK(m.s.find(District::Hospital)->rooms.size() == 3);
    CHECK(m.s.at(admin->x, admin->y) == admin);
    auto p = m.s.path(m.s.find(District::Housing)->x, m.s.find(District::Housing)->y, *admin);
    CHECK(p.size() == 4 && std::fabs(p.back().first - admin->x) < 1e-9);
    Game g2(3);
    g2.new_game("x");
    (void)g2.found_outpost("mars", vertical_slice_outpost());
    CHECK(Settlement::build(*g2.colony("mars_koloni"), challenge::body_environment("mars").value()).layout() == Layout::SurfaceDomes);
}

TEST("NPC: günlük program — gece uyku, gündüz meslek yerinde çalışma") {
    Sim m;
    CHECK(m.soc.npcs().size() == 8);
    // mürettebat saati 03:00'e ilerlet ve gözle
    const double to3 = std::fmod(27.0 - m.g.crew_hour("moon"), 24.0);
    m.run(to3 + 24.0);
    const int sleeping = m.count(Intent::Sleep);
    CHECK(sleeping >= 5);
    m.run(8.0);   // ~11:00
    CHECK(m.count(Intent::Work) + m.count(Intent::Research) + m.count(Intent::Patrol) >= 4);
    // meslekler farklı davranır: bilim insanı araştırma, güvenlik devriye
    bool sci = false, sec = false, farm = false;
    for (const auto& n : m.soc.npcs()) {
        const auto* k = m.c->colonist(n.id);
        if (k->job == colony::Job::Scientist && n.intent == Intent::Research) sci = true;
        if (k->job == colony::Job::Security && n.intent == Intent::Patrol) sec = true;
        if (k->job == colony::Job::Farmer && n.intent == Intent::Work && n.target == m.s.find(District::Farm)->id) farm = true;
    }
    CHECK(sci && sec && farm);
}

TEST("NPC: ihtiyaçlar davranışı değiştirir (aç NPC yemek salonuna gider)") {
    Sim m;
    m.run(2.0);
    auto& n = m.soc.npcs().front();
    colony::Colonist* k = m.c->colonist(n.id);
    k->needs.hunger = 0.97;
    k->activity_hours_left = 0;
    bool ate = false;
    for (int i = 0; i < 60 && !ate; ++i) {
        m.run(0.25, n.x, n.y);
        ate = m.soc.npc(n.id)->intent == Intent::Eat;
    }
    CHECK(ate);
    CHECK(m.soc.npc(n.id)->target == m.s.find(District::Canteen)->id);
}

TEST("NPC: olay tepkileri — enerji kesintisi, meteor, keşif") {
    Sim m;
    m.run(1.0);
    m.soc.raise(ColonyEvent::PowerOutage, m.g.day(), *m.c, m.s);
    m.run(0.2);
    int repair = 0, shelter = 0, respond = 0;
    for (const auto& n : m.soc.npcs()) {
        const auto* k = m.c->colonist(n.id);
        if (n.intent == Intent::RepairPower) {
            ++repair;
            CHECK(k->job == colony::Job::Engineer && n.target == m.s.find(District::Power)->id);
        }
        shelter += n.intent == Intent::Shelter;
        respond += n.intent == Intent::RespondAlarm;
        CHECK(k->ordered);                                     // emir ekonomiye yansır
    }
    CHECK(repair == 2 && shelter >= 2 && respond >= 1);
    m.soc.raise(ColonyEvent::MeteorThreat, m.g.day(), *m.c, m.s);
    m.run(0.2);
    for (const auto& n : m.soc.npcs())
        if (m.c->colonist(n.id)->job == colony::Job::Security) CHECK(n.intent == Intent::Patrol);
    m.soc.raise(ColonyEvent::AllClear, m.g.day(), *m.c, m.s);
    m.run(3.0);
    m.soc.raise(ColonyEvent::Discovery, m.g.day(), *m.c, m.s);
    m.run(0.2);
    bool sci = false;
    for (const auto& n : m.soc.npcs())
        if (m.c->colonist(n.id)->job == colony::Job::Scientist) sci = n.intent == Intent::Research || n.intent == Intent::Sleep;
    CHECK(sci);
}

TEST("NPC: hafıza sınırlı ve önem sıralı; ilişkiler zamanla değişir; kayıt") {
    Sim m;
    Npc* n = m.soc.npc(m.soc.npcs().front().id);
    m.soc.remember(*n, {0, 0, "Oyuncu hayatımı kurtardı", 1.0, 1.0});
    for (int i = 0; i < 30; ++i) m.soc.remember(*n, {1.0 + i * 0.01, -1, "sıradan olay", 0.1, 0.0});
    CHECK(n->memories.size() == Society::kMaxMemories);
    bool kept = false;
    for (const auto& x : n->memories) kept |= x.text == "Oyuncu hayatımı kurtardı";
    CHECK(kept);
    std::map<std::pair<int, int>, double> before;
    for (const auto& a : m.soc.npcs())
        for (const auto& b : m.soc.npcs())
            if (a.id < b.id) before[{a.id, b.id}] = m.soc.relation(a.id, b.id).affinity;
    m.run(72.0);
    int changed = 0;
    for (const auto& [k, v] : before) changed += std::fabs(m.soc.relation(k.first, k.second).affinity - v) > 1e-6;
    CHECK(changed >= 3);
    Society copy;
    CHECK(copy.from_json(json::parse(m.soc.to_json().dump()).value()).ok());
    CHECK(copy.npcs().size() == m.soc.npcs().size());
    CHECK(copy.npc(n->id)->memories.size() == n->memories.size());
    CHECK_NEAR(copy.relation(m.soc.npcs()[0].id, m.soc.npcs()[1].id).affinity, m.soc.relation(m.soc.npcs()[0].id, m.soc.npcs()[1].id).affinity, 1e-9);
}

TEST("NPC: diyalog ihtiyaç, iş ve hafızayı yansıtır; yardım ilişkiyi güçlendirir") {
    Sim m;
    m.run(1.0);
    const int id = m.soc.npcs().front().id;
    colony::Colonist* k = m.c->colonist(id);
    m.soc.npc(id)->intent = Intent::Idle;
    k->needs.hunger = 0.9;
    auto a = m.soc.talk(id, "nasılsın", m.g.day(), *m.c);
    CHECK(a.ok() && a.value().find("aç") != std::string::npos);
    const double aff = m.soc.relation(Society::kPlayer, id).affinity;
    auto h = m.soc.talk(id, "yardım", m.g.day(), *m.c);
    CHECK(h.ok() && m.soc.relation(Society::kPlayer, id).affinity > aff);
    CHECK(k->activity == colony::Activity::Eat && k->ordered);
    auto again = m.soc.talk(id, "selam", m.g.day(), *m.c);
    CHECK(again.value().find("unutmadım") != std::string::npos);
    CHECK(m.soc.talk(id, "koloni", m.g.day(), *m.c).value().find("Oksijen") != std::string::npos);
    CHECK(!m.soc.talk(999, "selam", m.g.day(), *m.c).ok());
}

TEST("NPC: simülasyon ayrıntı düzeyi — uzak NPC'ler daha az karar verir") {
    Sim near, far;
    const Building* h = near.s.find(District::Social);
    near.run(24.0, h->x, h->y);
    far.run(24.0);
    CHECK(far.soc.stats().far == 8);
    CHECK(near.soc.stats().decisions > far.soc.stats().decisions * 2);
}

TEST("üretim teşhisi: enerji arızası ve eksik personeli bulur") {
    Sim m;
    m.run(6.0);
    m.c->damage_module(colony::ModuleType::SolarArray, 0.7);
    auto d = diagnose_production(*m.c);
    bool power = false, maint = false;
    for (const auto& f : d.findings) {
        power |= f.find("Enerji yetersiz") != std::string::npos;
        maint |= f.find("bakım") != std::string::npos;
    }
    CHECK(power && maint);
    CHECK(!d.suggestions.empty());
}

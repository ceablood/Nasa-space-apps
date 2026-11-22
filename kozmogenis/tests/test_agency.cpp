#include <algorithm>
#include <cmath>

#include "kozmo/agency.hpp"
#include "kozmo/contracts.hpp"
#include "kozmo/game.hpp"
#include "kozmo/progression.hpp"
#include "kozmo/satellites.hpp"
#include "kozmo/savefmt.hpp"
#include "test_framework.hpp"

using namespace kozmo;

TEST("ajans: 12 tesis, seviyeler yetenekleri değiştirir, inşaat süresi, giderler, kayıt") {
    agency::Base b;
    CHECK(b.level(agency::Facility::Research) == 0 && b.level(agency::Facility::LaunchPads) == 1);
    auto c0 = b.capabilities();
    CHECK(c0.max_liftoff_t == 650 && c0.comms_range_km < 4e8);       // Mars'a ulaşamaz
    CHECK(!b.can_reach(2.25e8) && b.can_reach(384400));              // Ay evet, Mars (ort.) hayır
    econ::Wallet w(1e8);
    CHECK(b.upgrade(agency::Facility::CommsTower, w, 0).ok());
    CHECK(!b.upgrade(agency::Facility::CommsTower, w, 0).ok());      // zaten sürüyor
    CHECK(b.upgrade(agency::Facility::Hangar, w, 0).ok());
    CHECK(!b.upgrade(agency::Facility::Research, w, 0).ok());        // en çok 2 inşaat
    CHECK(b.advance(10, w).empty() && b.level(agency::Facility::CommsTower) == 1);
    auto msg = b.advance(100, w);
    CHECK(msg.size() == 2 && b.level(agency::Facility::CommsTower) == 2);
    CHECK(b.can_reach(4.0e8));                                       // Mars en uzak ~401 milyon km
    CHECK(b.capabilities().max_liftoff_t == 650);                    // rampa hâlâ 1: hangar tek başına yetmez
    CHECK(b.upgrade(agency::Facility::LaunchPads, w, 100).ok());
    (void)b.advance(200, w);
    CHECK(b.capabilities().max_liftoff_t == 1500 && b.capabilities().max_stages == 3);
    CHECK(w.balance() < 1e8 - 1500e3 - 1200e3 - 1500e3);              // yükseltme + günlük gider
    econ::Wallet poor(10);
    CHECK(b.upgrade(agency::Facility::Research, poor, 0).error().code == ErrorCode::InsufficientFunds);
    agency::Base copy;
    CHECK(copy.from_json(json::parse(b.to_json().dump()).value()).ok() && copy.level(agency::Facility::Hangar) == 2);
    CHECK(!b.max_base());
}

TEST("uydular: kapsama geometrisi, GEO gecikmesi, GPS görünürlüğü, gelir ve ömür") {
    // GEO: ufukta (0°) ~%42, 10° maskeyle ~%34 küre kapsama
    CHECK_NEAR(sats::single_coverage(35786, 0), 0.42, 0.01);
    CHECK_NEAR(sats::single_coverage(35786, 10), 0.34, 0.01);
    CHECK_NEAR(sats::round_trip_ms(35786), 239, 1);
    CHECK_NEAR(sats::round_trip_ms(550), 3.7, 0.1);
    CHECK_NEAR(sats::period_min(35786), 1436, 2);                     // yıldız günü ~1436 dk
    CHECK_NEAR(sats::period_min(550), 95.6, 0.5);
    // GPS: 24 uydu, 10° maske -> ortalama ~8-10 görünür (gerçek ~8-12)
    CHECK(sats::visible_average(20200, 10, 24) > 7 && sats::visible_average(20200, 10, 24) < 12);
    CHECK(sats::constellation_coverage(550, 25, 1000) > 0.9 && sats::constellation_coverage(550, 25, 10) < 0.2);
    sats::Fleet f;
    auto id = f.create("Kuşak", sats::Purpose::Communication, sats::Orbit::LEO, 260);
    CHECK(id.ok() && f.deploy(id.value(), 100, 0).ok());
    Rng rng(1);
    const double inc = f.advance(30, 1.0, rng);
    CHECK(inc > 0 && f.find(id.value())->active <= 100);
    sats::Fleet g2;
    auto gps = g2.create("Seyir", sats::Purpose::Navigation, sats::Orbit::MEO, 2000);
    (void)g2.deploy(gps.value(), 24, 0);
    CHECK(g2.find(gps.value())->revenue_per_day() > 14000);           // 4+ uydu görünüyor: tam hizmet
    Rng r2(2);
    sats::Fleet leo;
    auto l = leo.create("Ömür", sats::Purpose::EarthObservation, sats::Orbit::LEO, 100);
    (void)leo.deploy(l.value(), 50, 0);
    (void)leo.advance(365 * 10, 2.5, r2);
    CHECK(leo.find(l.value())->active < 20);                           // güneş maksimumunda itkisiz LEO ömrü kısa
    sats::Fleet copy;
    CHECK(copy.from_json(json::parse(f.to_json().dump()).value()).ok() && copy.constellations().size() == 1);
}

TEST("sözleşmeler: piyasa fiyatları, slotlar, kapasite, gecikme cezası, itibar") {
    CHECK_NEAR(contracts::price_usd_per_kg(contracts::Destination::LEO, false), 2900, 1e-9);
    CHECK_NEAR(contracts::price_usd_per_kg(contracts::Destination::LEO, true), 5500, 1e-9);
    contracts::Board b;
    Rng rng(3);
    b.refresh(0, 3, rng);
    CHECK(b.contracts().size() == 3);
    b.refresh(1, 3, rng);
    CHECK(b.contracts().size() == 3);                                 // slot dolu: yeni teklif yok
    const auto c = b.contracts()[0];
    CHECK(c.reward > 0 && c.penalty > 0 && c.deadline_day > c.offered_day);
    CHECK(b.accept(c.id, 1).ok());
    CHECK(!b.accept(b.contracts()[1].id, 1).ok());                    // görev kontrol kapasitesi
    econ::Wallet w(0);
    CHECK(!b.fulfil(c.id, c.payload_t * 0.5, 10, w).ok());             // kapasite yetersiz
    auto pay = b.fulfil(c.id, c.payload_t + 1, 10, w);
    CHECK(pay.ok() && w.balance() > 0 && b.reputation() > 0.5);
    CHECK(b.accept(b.contracts()[1].id, 1).ok());
    econ::Wallet w2(1e9);
    auto expired = b.expire(1e5, w2);
    CHECK(expired.size() == 1 && w2.balance() < 1e9 && b.reputation() < 0.55);
    contracts::Board copy;
    CHECK(copy.from_json(json::parse(b.to_json().dump()).value()).ok() && copy.contracts().size() == 3);
}

TEST("ilerleme: başarımlar bir kez açılır, eğitim adımları sıralı, haberler gerçek tarih notu ekler") {
    progress::Tracker t;
    progress::Snapshot s;
    CHECK(t.update(s).empty());
    s.landed_moon = true;
    s.colonies = 1;
    auto a = t.update(s);
    CHECK(a.size() == 2);
    CHECK(t.update(s).empty());
    s.credits = 2e7;
    CHECK(t.update(s).size() == 1 && t.unlocked("millionaire"));
    progress::Tracker copy;
    CHECK(copy.from_json(json::parse(t.to_json().dump()).value()).ok() && copy.count() == 3);
    progress::Tutorial tut;
    CHECK(tut.hint().find("otur") != std::string::npos);
    CHECK(!tut.on("exit") && tut.on("sit") && tut.step() == 1);
    for (const char* e : {"descent", "landed", "exit", "enter", "use", "talk", "nova", "sample"}) CHECK(tut.on(e));
    CHECK(tut.finished() && tut.hint().empty());
    progress::News n;
    n.report("landed_moon", 3);
    CHECK(n.items().size() == 2 && n.items()[1].real && n.items()[1].body.find("Apollo 11") != std::string::npos);
    n.report("özel olay", 4, "ayrıntı");
    CHECK(n.latest(1).front().body == "ayrıntı");
}

TEST("kayıt biçimi: zarf + sağlama toplamı, bozulma tespiti, v1 -> v3 taşıma") {
    Game g(12);
    g.new_game("x", 1e6);
    json::Value p = json::Value::object();
    p.set("game", json::parse(g.save()).value());
    const std::string s = savefmt::wrap(p);
    auto L = savefmt::unwrap(s);
    CHECK(L.ok() && !L.value().migrated && L.value().original_version == 3);
    std::string bad = s;
    const auto pos = bad.find("\"day\"");
    CHECK(pos != std::string::npos);
    bad[pos + 7] = bad[pos + 7] == '1' ? '2' : '1';
    CHECK(!savefmt::unwrap(bad).ok());
    auto old = savefmt::unwrap(g.save());                            // v1: zarfsız
    CHECK(old.ok() && old.value().migrated && old.value().original_version == 1);
    CHECK(old.value().payload.has("agency") && old.value().payload.has("settings") && old.value().notes.size() == 3);
    Game g2(12);
    CHECK(g2.load(old.value().payload["game"].dump()).ok());
    CHECK(!savefmt::unwrap("{\"format\":\"baska\",\"version\":1,\"payload\":{}}").ok());
    CHECK(!savefmt::unwrap("{\"format\":\"kozmogenis-save\",\"version\":99,\"payload\":{}}").ok());
}

#include "kozmo/economy.hpp"
#include "kozmo/json.hpp"
#include "kozmo/research.hpp"
#include "test_framework.hpp"

using namespace kozmo;

TEST("econ: kıtlık fiyatı yükseltir, büyük alım kayma ile pahalanır") {
    econ::Market m("x", "X");
    m.set_item("water", {100, 100, 0, 0});
    const double p0 = m.price("water").value();
    CHECK_NEAR(p0, 120.0, 1e-9);                 // dengede taban fiyat
    m.item_mut("water")->stock = 50;
    CHECK(m.price("water").value() > p0 * 2.0);  // esneklik 1.2: (2)^1.2 = 2.30
    m.item_mut("water")->stock = 100;
    const double small = m.quote("water", 1, true).value();
    const double big = m.quote("water", 60, true).value() / 60.0;
    CHECK(big > small);
    CHECK(!m.quote("water", 500, true).ok());     // piyasada o kadar yok
    CHECK(!m.price("unobtainium").ok());
}

TEST("econ: alım-satım cüzdanı ve stoğu tutarlı günceller") {
    econ::Market m("x", "X");
    m.set_item("iron", {100, 100, 2, 1});
    econ::Wallet w(10000);
    auto b = m.buy("iron", 10, w, 0);
    CHECK(b.ok());
    CHECK_NEAR(m.item("iron")->stock, 90, 1e-9);
    CHECK_NEAR(w.balance(), 10000 - b.value().total, 1e-6);
    auto s = m.sell("iron", 10, w, 1);
    CHECK(s.ok());
    CHECK(s.value().total < b.value().total);      // makas: aynı malı geri satmak zarar
    econ::Wallet poor(1);
    CHECK(m.buy("iron", 5, poor, 0).error().code == ErrorCode::InsufficientFunds);
    m.tick(10);
    CHECK_NEAR(m.item("iron")->stock, 110, 1e-9);
    CHECK(w.ledger().size() == 2);
}

TEST("research: önkoşul, ilerleme, olay ve kayıt") {
    research::Tree t;
    EventBus bus;
    std::string done;
    bus.subscribe<research::ResearchCompleted>([&](const research::ResearchCompleted& e) { done = e.key; });
    CHECK(t.start("methalox").error().code == ErrorCode::Locked);
    CHECK(t.start("cryo").ok());
    CHECK(!t.add_points(20, &bus));
    CHECK_NEAR(t.progress(), 0.5, 1e-9);
    CHECK(t.add_points(25, &bus));
    CHECK(done == "cryo");
    CHECK(t.unlocked("cryo"));
    CHECK(t.start("methalox").ok());
    t.add_points(10, &bus);
    research::Tree u;
    CHECK(u.from_json(t.to_json()).ok());
    CHECK(u.unlocked("cryo") && u.active() == "methalox");
    CHECK_NEAR(u.progress(), t.progress(), 1e-12);
    bool fiction = false;
    for (const auto& x : research::techs()) fiction |= x.fictional;
    CHECK(fiction);                                // kurgusal teknoloji açıkça işaretli
}

TEST("json: gidiş-dönüş, türkçe karakter, hatalı girdi") {
    json::Value v = json::Value::object();
    v.set("ad", "Şükrü Çağlayan ığüşöç");
    v.set("sayi", 3.25);
    v.set("tam", 42);
    v.set("ok", true);
    json::Value a = json::Value::array();
    a.push(1);
    a.push("x\n\"y\"");
    a.push(json::Value());
    v.set("liste", a);
    for (int indent : {0, 2}) {
        auto p = json::parse(v.dump(indent));
        CHECK(p.ok());
        CHECK(p.value()["ad"].as_string() == "Şükrü Çağlayan ığüşöç");
        CHECK_NEAR(p.value()["sayi"].as_number(), 3.25, 1e-12);
        CHECK(p.value()["tam"].as_int() == 42);
        CHECK(p.value()["liste"].at(1).as_string() == "x\n\"y\"");
        CHECK(p.value()["liste"].at(2).is_null());
        CHECK(p.value()["yok"].is_null());
    }
    CHECK(json::parse("{\"a\":1,}").error().code == ErrorCode::Parse);
    CHECK(!json::parse("[1,2").ok());
    CHECK(!json::parse("{} x").ok());
    CHECK(json::parse("\"\\u00e7\"").value().as_string() == "ç");
}

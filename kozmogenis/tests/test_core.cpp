#include "kozmo/core.hpp"
#include "test_framework.hpp"

using namespace kozmo;

TEST("core: Result başarı ve hata taşır") {
    Result<int> a(5);
    CHECK(a.ok());
    CHECK(a.value() == 5);
    Result<int> b(make_error(ErrorCode::NotFound, "yok"));
    CHECK(!b.ok());
    CHECK(b.error().code == ErrorCode::NotFound);
}

struct Ping { int v; };
struct Pong { std::string s; };

TEST("core: EventBus tür bazında yayın, abonelikten çıkma") {
    EventBus bus;
    int sum = 0, pongs = 0;
    auto id = bus.subscribe<Ping>([&](const Ping& p) { sum += p.v; });
    bus.subscribe<Pong>([&](const Pong&) { ++pongs; });
    bus.publish(Ping{3});
    bus.publish(Ping{4});
    bus.publish(Pong{"x"});
    CHECK(sum == 7);
    CHECK(pongs == 1);
    bus.unsubscribe(id);
    bus.publish(Ping{100});
    CHECK(sum == 7);
    CHECK(bus.published_count() == 4);
}

TEST("core: Rng deterministik ve dağılım makul") {
    Rng a(42), b(42);
    for (int i = 0; i < 100; ++i) CHECK(a.next_u64() == b.next_u64());
    Rng r(7);
    double s = 0;
    const int n = 20000;
    for (int i = 0; i < n; ++i) {
        const double u = r.uniform();
        CHECK(u >= 0.0 && u < 1.0);
        s += u;
    }
    CHECK_NEAR(s / n, 0.5, 0.01);
    double m = 0;
    for (int i = 0; i < n; ++i) m += r.normal(10.0, 2.0);
    CHECK_NEAR(m / n, 10.0, 0.06);
    for (int i = 0; i < 1000; ++i) {
        const int k = r.range(-3, 3);
        CHECK(k >= -3 && k <= 3);
    }
}

TEST("core: Log son satırları tutar") {
    Log::set_sink([](LogLevel, const std::string&, const std::string&) {});
    KOZMO_LOG(Info, "test", "merhaba");
    auto rec = Log::recent(1);
    CHECK(rec.size() == 1);
    CHECK(rec[0].find("merhaba") != std::string::npos);
    Log::set_sink(nullptr);
}

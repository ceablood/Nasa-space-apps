#include <algorithm>
#include "kozmo/gare.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::gare;

namespace {
struct Probe : Module {
    std::string n;
    std::vector<std::string> deps;
    std::vector<std::string>* log;
    bool fail = false;
    int fixed = 0, var = 0;
    double sim = 0;
    Probe(std::string name, std::vector<std::string> d, std::vector<std::string>* l, bool f = false)
        : n(std::move(name)), deps(std::move(d)), log(l), fail(f) {}
    std::string name() const override { return n; }
    std::vector<std::string> dependencies() const override { return deps; }
    Status init(Runtime&) override {
        log->push_back("init:" + n);
        if (fail) return make_error(ErrorCode::InvalidArgument, "test hatası");
        return ok_status();
    }
    void fixed_update(Runtime&, double dt) override { ++fixed; sim += dt; }
    void update(Runtime&, double) override { ++var; }
    void shutdown(Runtime&) override { log->push_back("shutdown:" + n); }
};
}  // namespace

TEST("gare: modüller bağımlılık sırasıyla başlar, ters sırayla kapanır") {
    std::vector<std::string> log;
    Runtime rt;
    CHECK(rt.add(std::make_unique<Probe>("ui", std::vector<std::string>{"game", "audio"}, &log)).ok());
    CHECK(rt.add(std::make_unique<Probe>("game", std::vector<std::string>{"physics"}, &log)).ok());
    CHECK(rt.add(std::make_unique<Probe>("audio", std::vector<std::string>{}, &log)).ok());
    CHECK(rt.add(std::make_unique<Probe>("physics", std::vector<std::string>{}, &log)).ok());
    CHECK(!rt.add(std::make_unique<Probe>("audio", std::vector<std::string>{}, &log)).ok());   // aynı ad
    CHECK(rt.init().ok());
    auto order = rt.init_order();
    auto pos = [&](const std::string& n) { return std::find(order.begin(), order.end(), n) - order.begin(); };
    CHECK(pos("physics") < pos("game") && pos("game") < pos("ui") && pos("audio") < pos("ui"));
    rt.shutdown();
    CHECK(log.back() == "shutdown:" + order.front());
}

TEST("gare: eksik bağımlılık, döngü ve başlatma hatası raporlanır") {
    std::vector<std::string> log;
    Runtime a;
    a.add(std::make_unique<Probe>("x", std::vector<std::string>{"yok"}, &log));
    CHECK(a.init().error().code == ErrorCode::NotFound);
    Runtime b;
    b.add(std::make_unique<Probe>("p", std::vector<std::string>{"q"}, &log));
    b.add(std::make_unique<Probe>("q", std::vector<std::string>{"p"}, &log));
    auto st = b.init();
    CHECK(!st.ok() && st.error().message.find("döngü") != std::string::npos);
    log.clear();
    Runtime c;
    std::string failed;
    c.bus().subscribe<ModuleInitFailed>([&](const ModuleInitFailed& e) { failed = e.module; });
    c.add(std::make_unique<Probe>("ok1", std::vector<std::string>{}, &log));
    c.add(std::make_unique<Probe>("bad", std::vector<std::string>{"ok1"}, &log, true));
    CHECK(!c.init().ok());
    CHECK(failed == "bad");
    CHECK(!c.running());
    CHECK(log.back() == "shutdown:ok1");          // başlatılmış olan geri alındı
}

TEST("gare: sabit adım biriktirici, zaman hızlandırma, duraklatma, üst sınır") {
    std::vector<std::string> log;
    Runtime rt;
    auto p = std::make_unique<Probe>("sim", std::vector<std::string>{}, &log);
    Probe* probe = p.get();
    rt.add(std::move(p));
    rt.set_fixed_step(0.01);
    CHECK(rt.init().ok());
    for (int i = 0; i < 100; ++i) rt.frame(1.0 / 60.0);       // 1.6667 s gerçek
    CHECK(probe->fixed == 166);
    CHECK(probe->var == 100);
    CHECK_NEAR(rt.sim_time(), 1.66, 1e-9);
    rt.set_time_scale(10.0);
    rt.set_max_steps_per_frame(10000);
    rt.frame(1.0);
    CHECK_NEAR(rt.sim_time(), 11.66, 0.011);
    rt.set_paused(true);
    const int f0 = probe->fixed;
    rt.frame(5.0);
    CHECK(probe->fixed == f0);
    rt.set_paused(false);
    rt.set_max_steps_per_frame(5);
    rt.frame(1.0);                                          // 10 sim sn istenir, en fazla 5 adım
    CHECK(probe->fixed == f0 + 5);
    CHECK(rt.stats().dropped_sim_s >= 9);
    CHECK(rt.diagnostics().find("sim") != std::string::npos);
    CHECK(rt.timings().at("sim").calls > 0);
}

TEST("gare: olay kuyruğu önceliğe göre ve ertelenmiş dağıtır") {
    EventQueue q;
    std::string out;
    q.post([&] { out += "a"; }, 0);
    q.post([&] { out += "b"; }, 5);
    q.post([&] {
        out += "c";
        q.post([&] { out += "d"; });                       // sonraki kareye kalmalı
    }, 0);
    CHECK(q.dispatch() == 3);
    CHECK(out == "bac");
    CHECK(q.pending() == 1);
    q.dispatch();
    CHECK(out == "bacd");
    for (int i = 0; i < 10; ++i) q.post([] {});
    CHECK(q.dispatch(4) == 4);
    CHECK(q.pending() == 6);
}

struct Clock { double now = 42; };

TEST("gare: servis bulucu, ayarlar ve özellik bayrakları") {
    Runtime rt;
    CHECK(rt.services().get<Clock>() == nullptr);
    rt.services().provide(std::make_shared<Clock>());
    CHECK(rt.services().get<Clock>()->now == 42);
    auto st = rt.config().parse("; yorum\n[graphics]\nprofile = Low\nfps=60\n[features]\nnova_online = false\nnew_flight=1\n");
    CHECK(st.ok());
    CHECK(rt.config().get("graphics.profile") == "Low");
    CHECK_NEAR(rt.config().get_number("graphics.fps", 0), 60, 1e-12);
    CHECK_NEAR(rt.config().get_number("graphics.profile", -1), -1, 1e-12);   // sayı değil -> varsayılan
    CHECK(!rt.flag("nova_online") && rt.flag("new_flight"));
    rt.set_flag("nova_online", true);
    CHECK(rt.flag("nova_online"));
    CHECK(!rt.config().parse("[eksik\n").ok());
    CHECK(!rt.config().parse("anahtarsiz\n").ok());
}

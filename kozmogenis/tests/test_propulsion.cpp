#include "kozmo/propulsion.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::prop;

namespace {
// Falcon 9 Full Thrust sınıfı: yayımlanmış yuvarlak değerler (S1 411 t yakıt, ~25.6 t kuru; S2 107.5 t, ~4 t kuru)
Design falcon9_like(double payload) {
    Design d;
    d.name = "F9 sınıfı";
    d.stages = {{"kerolox_gg", 9, 411.0, (25.6 - 9 * 0.47) / 411.0}, {"kerolox_vac", 1, 107.5, (4.0 - 0.49) / 107.5}};
    d.payload_t = payload;
    d.target = "leo";
    return d;
}
}  // namespace

TEST("prop: Falcon 9 sınıfı roket LEO'ya ~22.8 t taşır (gerçek veriyle doğrulama)") {
    auto r = analyze(falcon9_like(22.8), {});
    CHECK(r.ok());
    const auto& rep = r.value();
    CHECK_NEAR(rep.liftoff_mass_t, 571.0, 3.0);           // gerçek: ~549-570 t
    CHECK_NEAR(rep.liftoff_twr, 1.33, 0.08);              // gerçek: ~1.3-1.4
    CHECK_NEAR(rep.total_dv_ms, 9400.0, 350.0);           // LEO için gereken ~9.4 km/s civarı
    CHECK(rep.stages.size() == 2);
    CHECK_NEAR(rep.stages[0].burn_s, 162.0, 20.0);        // gerçek S1 yanma süresi ~162 s
}

TEST("prop: Tsiolkovsky tek kademe birebir") {
    Design d;
    d.stages = {{"kerolox_vac", 1, 90.0, 0.1}};
    d.payload_t = 1.0;
    d.target = "leo";
    auto r = analyze(d, {});
    CHECK(r.ok());
    // ilk kademe atmosferde çalışamayan motor -> engel listesinde
    CHECK(!r.value().feasible);
    const double m0 = 1.0 + 90.0 + 9.0 + 0.49, mf = 1.0 + 9.0 + 0.49;
    CHECK_NEAR(r.value().stages[0].dv_ms, 348 * 0.3 * kG0 * std::log(m0 / mf), 1e-6);
}

TEST("prop: yük arttıkça delta-v düşer, kilitli motor reddedilir") {
    auto a = analyze(falcon9_like(5.0), {});
    auto b = analyze(falcon9_like(30.0), {});
    CHECK(a.value().total_dv_ms > b.value().total_dv_ms);
    Design d = falcon9_like(5.0);
    d.stages[1].engine = "hydrolox_exp";
    auto c = analyze(d, {});
    CHECK(!c.ok());
    CHECK(c.error().code == ErrorCode::Locked);
    auto e = analyze(d, {"cryo"});
    CHECK(e.ok());
}

TEST("prop: Ay görevi için en az yakıt bulunur ve tasarım uygun olur") {
    Design d = falcon9_like(2.0);
    d.target = "moon";
    d.land = true;
    d.stages.push_back({"hydrolox_exp", 2, 10.0, 0.10});
    auto p = min_upper_propellant(d, {"cryo"});
    CHECK(p.ok());
    d.stages.back().propellant_t = p.value();
    auto r = analyze(d, {"cryo"});
    CHECK(r.value().margin_ms >= 0);
    CHECK(r.value().feasible);
    CHECK(r.value().success_p > 0.8 && r.value().success_p <= 1.0);
}

TEST("prop: geçersiz tasarımlar açık hata verir") {
    Design d;
    CHECK(!analyze(d, {}).ok());
    d.stages = {{"warp", 1, 10, 0.1}};
    CHECK(analyze(d, {}).error().code == ErrorCode::NotFound);
    d.stages = {{"kerolox_gg", 0, 10, 0.1}};
    CHECK(analyze(d, {}).error().code == ErrorCode::InvalidArgument);
    d.stages = {{"kerolox_gg", 1, 10, 0.9}};
    CHECK(analyze(d, {}).error().code == ErrorCode::InvalidArgument);
}

TEST("prop: düşük itki/ağırlık engel olarak raporlanır") {
    Design d = falcon9_like(5.0);
    d.stages[0].engine_count = 3;
    auto r = analyze(d, {});
    CHECK(r.ok());
    CHECK(!r.value().feasible);
    CHECK(r.value().success_p <= 0.05);
}

TEST("prop: motor kaybı toleransı binom olasılığıyla hesaplanır") {
    CHECK(engine_out_tolerance(1) == 0 && engine_out_tolerance(9) == 1 && engine_out_tolerance(33) == 2);
    CHECK_NEAR(stage_reliability(0.99, 1), 0.99, 1e-12);
    // 9 motor, 1 arıza tolere: p^9 + 9 p^8 q
    CHECK_NEAR(stage_reliability(0.99, 9), std::pow(0.99, 9) + 9 * std::pow(0.99, 8) * 0.01, 1e-12);
    CHECK(stage_reliability(0.99, 33) > 0.99);           // çok motorlu kademe toleransla güvenilir
    CHECK(stage_reliability(0.99, 8) < stage_reliability(0.99, 9));
}

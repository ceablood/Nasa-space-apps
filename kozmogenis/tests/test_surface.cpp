#include <algorithm>
#include <cmath>

#include "kozmo/rover.hpp"
#include "kozmo/terrain.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::terrain;

TEST("arazi: gürültü deterministik ve sınırlı") {
    CHECK_NEAR(value_noise(1.3, 2.7, 5), value_noise(1.3, 2.7, 5), 0);
    CHECK(value_noise(1.3, 2.7, 5) != value_noise(1.3, 2.7, 6));
    double lo = 1, hi = -1;
    for (int i = 0; i < 2000; ++i) {
        const double v = fbm(i * 0.37, i * 0.11, 9, 5);
        lo = std::min(lo, v);
        hi = std::max(hi, v);
    }
    CHECK(lo >= -1.0 && hi <= 1.0 && hi - lo > 0.5);
}

TEST("arazi: Ay kraterli, krater derinlik/çap ~0.2 ve boyut dağılımı D^-2") {
    auto env = challenge::body_environment("moon").value();
    auto m = Heightmap::generate(env, 42, 2000, 10);
    CHECK(m.side() == 201);
    CHECK(m.craters().size() > 100);
    int big = 0, small = 0;
    for (const auto& c : m.craters()) {
        CHECK_NEAR(c.depth_m / c.diameter_m, 0.2, 1e-9);
        CHECK_NEAR(c.rim_m / c.diameter_m, 0.04, 1e-9);
        big += c.diameter_m >= 40;
        small += c.diameter_m >= 20;
    }
    // N(>40)/N(>20) ~ (20/40)^2 = 0.25
    CHECK_NEAR(static_cast<double>(big) / small, 0.25, 0.08);
    CHECK(!m.pits().empty());                                    // lav tüpü girişi
    // aynı tohum aynı arazi
    auto m2 = Heightmap::generate(env, 42, 2000, 10);
    CHECK_NEAR(m.height(123, -456), m2.height(123, -456), 1e-12);
    // büyük kraterin içi çevresinden alçak
    const Crater* b = &m.craters().front();
    for (const auto& c : m.craters())
        if (c.diameter_m > b->diameter_m && std::fabs(c.x) < 800 && std::fabs(c.y) < 800) b = &c;
    CHECK(m.height(b->x, b->y) < m.height(b->x + b->diameter_m * 0.55, b->y));
}

TEST("arazi: Mars kumullu ve daha az kraterli; Europa genç yüzey") {
    auto moon = Heightmap::generate(challenge::body_environment("moon").value(), 1, 2000, 10);
    auto mars = Heightmap::generate(challenge::body_environment("mars").value(), 1, 2000, 10);
    auto eur = Heightmap::generate(challenge::body_environment("europa").value(), 1, 2000, 10);
    CHECK(mars.craters().size() < moon.craters().size() / 2);
    CHECK(eur.craters().size() < moon.craters().size() / 3);
    CHECK(mars.max_height() - mars.min_height() > 5);
}

TEST("arazi: iniş yeri taraması Apollo LM eğim sınırına uyar ve çukurlardan kaçınır") {
    auto m = Heightmap::generate(challenge::body_environment("moon").value(), 7, 2000, 10);
    auto sites = m.find_landing_sites(20.0, 12.0, 1.5, 5);
    CHECK(!sites.empty());
    for (const auto& s : sites) {
        CHECK(s.max_slope_deg <= 12.0 && s.roughness_m <= 1.5);
        for (const auto& p : m.pits()) CHECK(std::hypot(s.x - p.x, s.y - p.y) > p.diameter_m);
    }
    CHECK(sites.front().score >= sites.back().score);
    // düzleştirme eğimi sıfırlar
    m.flatten(sites.front().x, sites.front().y, 30);
    CHECK(m.slope_deg(sites.front().x, sites.front().y) < 1.0);
}

TEST("arazi: kaynak haritası ve 3B mesh") {
    auto moon = Heightmap::generate(challenge::body_environment("moon").value(), 3, 1000, 10);
    auto mars = Heightmap::generate(challenge::body_environment("mars").value(), 3, 1000, 10);
    CHECK(moon.resource(Resource::Helium3, 0, 0) > 0 && mars.resource(Resource::Helium3, 0, 0) == 0);   // He-3 yalnız atmosfersiz
    CHECK(moon.resource(Resource::WaterIce, 0, 0) <= 1.0);
    auto mesh = moon.mesh(2);
    CHECK(mesh.side == 51);
    CHECK(mesh.vertices.size() == 51u * 51u * 3u && mesh.normals.size() == mesh.vertices.size());
    CHECK(mesh.triangles.size() == 50u * 50u * 6u);
    for (std::size_t i = 2; i < mesh.normals.size(); i += 3) CHECK(mesh.normals[i] > 0.0f);
}

TEST("rover: Apollo LRV verileri, düz zeminde menzil ve enerji") {
    auto lrv = rover::find("lrv").value();
    CHECK_NEAR(lrv->mass_kg, 210, 1e-9);
    CHECK_NEAR(lrv->top_speed_ms * 3.6, 13, 0.1);
    // düz, sert zemin: 0.12 yuvarlanma, 1.62 m/s^2, 2 astronot+yük ~400 kg, 3 m/s
    const double p = rover::drive_power_w(*lrv, 400, 1.62, 3.0, 0, 0.03);
    CHECK(p > 300 && p < 1200);                                  // LRV motorları 4 x 0.25 hp ~ 750 W
    CHECK(rover::slip_ratio(0, 0.5) < 0.05 && rover::slip_ratio(25, 0.9) > 0.9);
    CHECK(rover::slip_ratio(10, 0.3) < rover::slip_ratio(20, 0.3));
}

TEST("rover: arazi geçişi, eğim sınırı, batarya ve geri yürüyüş kuralı") {
    auto env = challenge::body_environment("moon").value();
    auto m = Heightmap::generate(env, 11, 4000, 20);
    auto sites = m.find_landing_sites(40, 8, 3, 2);
    CHECK(sites.size() == 2);
    rover::Rover r(*rover::find("lrv").value());
    r.set_load(350);
    auto rep = r.traverse(m, env, {sites[0].x, sites[0].y}, {{sites[1].x, sites[1].y}}, 0.6, 1.0, 0.0, true);
    CHECK(rep.feasible || rep.failure.find("Eğim") != std::string::npos);
    if (rep.feasible) {
        CHECK(r.battery() < 8.7 && r.odometer() > 0);
        CHECK(rep.energy_kwh > 0 && rep.time_s > 0);
    }
    // geri yürüyüş: 1 saat giysi O2 ile Ay'da ~1.5 km
    CHECK_NEAR(rover::walkback_limit_m(1.0, 1.62), 0.6 * 3600 * 0.7, 150);
    rover::Rover r2(*rover::find("lrv").value());
    auto far = r2.traverse(m, env, {0, 0}, {{1900, 0}}, 1.0, 1.0, 0.5, false);
    CHECK(!far.feasible);
    // toz fırtınası hızı düşürür
    rover::Rover r3(*rover::find("curiosity").value());
    auto envm = challenge::body_environment("mars").value();
    auto mm = Heightmap::generate(envm, 4, 1000, 10);
    auto clear = r3.traverse(mm, envm, {0, 0}, {{30, 0}}, 1.0, 1.0, 0, false);
    auto storm = r3.traverse(mm, envm, {0, 0}, {{30, 0}}, 1.0, 0.2, 0, false);
    if (clear.feasible && storm.feasible) CHECK(storm.time_s > clear.time_s * 1.5);
}

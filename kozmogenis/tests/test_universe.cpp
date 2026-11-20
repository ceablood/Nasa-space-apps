#include <set>

#include "kozmo/universe.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::universe;

TEST("universe: Güneş modeli IAU nominal değerlerini verir") {
    Star sun = make_star(1.0, 4.6);
    CHECK_NEAR(sun.luminosity_lsun, 1.0, 1e-12);
    CHECK_NEAR(sun.radius_rsun, 1.0, 1e-12);
    CHECK_NEAR(sun.temperature_k, 5772.0, 1e-9);
    CHECK(sun.spectral == SpectralClass::G);
    CHECK_NEAR(sun.lifetime_gyr, 10.0, 1e-9);
    CHECK(classify_star(3500) == SpectralClass::M && classify_star(9000) == SpectralClass::A &&
          classify_star(40000) == SpectralClass::O && classify_star(4500) == SpectralClass::K);
    // büyük kütleli yıldız kısa yaşar (10 Msun: ~20-30 milyon yıl)
    CHECK(main_sequence_lifetime_gyr(10.0) > 0.015 && main_sequence_lifetime_gyr(10.0) < 0.035);
    CHECK(main_sequence_lifetime_gyr(0.2) > 100.0);
}

TEST("universe: Güneş Sistemiyle doğrulama — denge sıcaklığı, yaşanabilir bölge, atmosfer") {
    CHECK_NEAR(equilibrium_temperature(1.0, 1.0, 0.306), 254.0, 2.0);     // Dünya ~255 K
    CHECK_NEAR(equilibrium_temperature(1.0, 1.524, 0.25), 210.0, 3.0);    // Mars ~210 K
    const double in = habitable_inner_au(1.0), out = habitable_outer_au(1.0);
    CHECK(in < 1.0 && out > 1.0);                                           // Dünya içeride
    CHECK(0.723 < in);                                                      // Venüs dışarıda (içte)
    CHECK(1.524 > out);                                                     // Mars dışarıda (basit sınırla)
    CHECK(retains_atmosphere(11.19, 288 * 1.5));                           // Dünya tutar
    CHECK(!retains_atmosphere(2.38, 270 * 1.5));                           // Ay tutamaz
    CHECK(retains_atmosphere(5.03, 210 * 1.5));                            // Mars (ince) tutar
}

TEST("universe: kütle-yarıçap Dünya, Neptün, Jüpiter ile tutarlı") {
    CHECK_NEAR(planet_radius_earth(1.0), 1.0, 0.02);
    CHECK_NEAR(planet_radius_earth(17.15), 3.88, 3.88 * 0.15);             // Neptün
    CHECK_NEAR(planet_radius_earth(317.8), 11.21, 0.2);                    // Jüpiter
    CHECK(planet_radius_earth(0.5) < planet_radius_earth(1.5));
}

TEST("universe: aynı tohum aynı evren, farklı tohum farklı evren") {
    Galaxy a(2026, 300), b(2026, 300), c(7, 300);
    CHECK(a.systems().size() == 300);
    bool same = true, diff = false;
    for (std::size_t i = 0; i < 300; ++i) {
        same &= a.systems()[i].name == b.systems()[i].name && a.systems()[i].x_ly == b.systems()[i].x_ly &&
                a.systems()[i].planets.size() == b.systems()[i].planets.size();
        diff |= a.systems()[i].name != c.systems()[i].name;
    }
    CHECK(same);
    CHECK(diff);
}

TEST("universe: yıldız nüfusu gerçekçi — M cüceleri çoğunlukta, devler dış bölgede") {
    Galaxy g(42, 2000);
    int m_dwarfs = 0, gas_in = 0, gas_out = 0, hz = 0;
    for (const auto& s : g.systems()) {
        m_dwarfs += s.star.spectral == SpectralClass::M;
        CHECK(s.hz_inner_au < s.hz_outer_au);
        const double snow = 2.7 * std::sqrt(s.star.luminosity_lsun);
        for (const auto& p : s.planets) {
            if (p.type == PlanetType::GasGiant) (p.semi_major_au > snow ? gas_out : gas_in)++;
            hz += p.in_habitable_zone;
            CHECK(p.equilibrium_temp_k > 0 && p.radius_earth > 0);
            CHECK(p.colony_score >= 0 && p.colony_score <= 1);
            if (p.type == PlanetType::GasGiant) CHECK(p.colony_score == 0.0);
        }
    }
    CHECK(m_dwarfs > 2000 * 0.6);              // gerçekte yıldızların ~%75'i M cücesi
    CHECK(gas_out > gas_in);
    CHECK(hz > 0);
}

TEST("universe: A* rota menzile uyar ve en kısa yola yakındır") {
    Galaxy g(5, 400, 600.0);
    auto r = g.route(1, 200, 60.0);
    if (r.ok()) {
        const auto& p = r.value();
        CHECK(p.front() == 1 && p.back() == 200);
        double total = 0;
        for (std::size_t i = 1; i < p.size(); ++i) {
            const double d = g.distance_ly(p[i - 1], p[i]);
            CHECK(d <= 60.0 + 1e-9);
            total += d;
        }
        CHECK(total >= g.distance_ly(1, 200) - 1e-6);
    }
    CHECK(g.route(1, 200, 1e9).value().size() == 2);       // sınırsız menzil: doğrudan
    CHECK(g.route(1, 200, 0.001).error().code == ErrorCode::NotFound);
    CHECK(!g.route(1, 999999, 50).ok());
    auto best = g.best_colony_candidates(5);
    for (std::size_t i = 1; i < best.size(); ++i)
        CHECK(g.find(best[i - 1].first)->planets[best[i - 1].second].colony_score >=
              g.find(best[i].first)->planets[best[i].second].colony_score);
}

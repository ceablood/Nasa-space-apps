#include "kozmo/astro.hpp"
#include "test_framework.hpp"

using namespace kozmo;
using namespace kozmo::astro;

TEST("astro: NASA tablosu tam ve tutarlı") {
    CHECK(bodies().size() == 10);
    for (const auto& b : bodies()) {
        CHECK(b.source == Source::NasaFactSheet);
        CHECK(b.mass_1e24kg > 0 && b.diameter_km > 0);
        // tablo yerçekimi = GM/R^2 - ekvatorda dönüşün merkezkaç etkisi (w^2 R); hızlı dönen gaz devlerinde
        // bu fark ~2 m/s^2'dir (NASA tablosu ekvatoral, dönüş dahil değeri verir)
        const double w = 2.0 * kPi / (std::fabs(b.rotation_h) * 3600.0);
        const double g = b.mu() / (b.radius_m() * b.radius_m()) - w * w * b.radius_m();
        CHECK_NEAR(g, b.gravity_ms2, std::max(0.15, b.gravity_ms2 * 0.06));
        // kaçış hızı
        CHECK_NEAR(escape_velocity(b.mu(), b.radius_m()) / 1000.0, b.escape_kms, std::max(0.15, b.escape_kms * 0.03));
    }
    CHECK(!find("vulcan").ok());
}

TEST("astro: Kepler 3. yasa — tablo periyotları Güneş mu ile uyumlu") {
    for (const auto& b : bodies()) {
        if (b.parent != "sun") continue;
        const double T = orbital_period(kMuSun, b.semi_major_m()) / kDay;
        // tablodaki "Güneş'e uzaklık" yarı büyük eksenden %1-2 sapabilir (Neptün: 4515 vs ~4498 milyon km)
        CHECK_NEAR(T, b.period_days, b.period_days * 0.015);
    }
}

TEST("astro: Dünya->Mars Hohmann bilinen değerlerle uyumlu") {
    auto E = *find("earth").value();
    auto M = *find("mars").value();
    auto h = hohmann(kMuSun, E.semi_major_m(), M.semi_major_m());
    CHECK_NEAR(h.transfer_days, 259.0, 3.0);        // ~8,5 ay
    CHECK_NEAR(h.dv_depart_ms, 2945.0, 40.0);       // v_inf kalkış
    CHECK_NEAR(h.dv_arrive_ms, 2650.0, 40.0);
    CHECK_NEAR(h.phase_angle_deg, 44.3, 1.0);       // Mars ~44° önde olmalı
    // LEO'dan Mars'a transfer yanması ~3,6 km/s
    CHECK_NEAR(burn_from_parking(E.mu(), E.radius_m() + 200e3, h.dv_depart_ms), 3600.0, 80.0);
    CHECK_NEAR(synodic_period_days(E.period_days, M.period_days), 780.0, 3.0);
}

TEST("astro: Ay görev bütçesi (TLI ~3,1 km/s)") {
    auto b = mission_budget("moon");
    CHECK(b.ok());
    CHECK_NEAR(b.value().departure_ms, 3130.0, 80.0);
    CHECK_NEAR(b.value().capture_ms, 850.0, 200.0);
    CHECK(b.value().landing_ms > 1500 && b.value().landing_ms < 2300);
    CHECK(b.value().total(true, true) > b.value().total(false, false));
}

TEST("astro: gaz devlerinde iniş yok, dış gezegene bütçe büyür") {
    auto j = mission_budget("jupiter");
    auto m = mission_budget("mars");
    CHECK(j.ok() && m.ok());
    CHECK(j.value().landing_ms == 0.0);
    CHECK(j.value().departure_ms > m.value().departure_ms);
    CHECK(!mission_budget("earth").ok());
    CHECK(!mission_budget("nope").ok());
}

TEST("astro: fırlatma penceresi faz açısına göre hesaplanır") {
    // Mars tam istenen faz açısındaysa pencere hemen
    auto E = *find("earth").value();
    auto M = *find("mars").value();
    auto h = hohmann(kMuSun, E.semi_major_m(), M.semi_major_m());
    auto w = next_window("earth", "mars", 10.0, 10.0 + h.phase_angle_deg);
    CHECK(w.ok());
    CHECK(w.value().days_until < 1.0 || w.value().days_until > w.value().synodic_days - 1.0);
    // 1 gün geçtikten sonra bir sonraki pencere ~sinodik periyot sonra
    const double nE = 360.0 / E.period_days, nM = 360.0 / M.period_days;
    auto w2 = next_window("earth", "mars", 10.0 + nE, 10.0 + h.phase_angle_deg + nM);
    CHECK_NEAR(w2.value().days_until, w2.value().synodic_days - 1.0, 2.0);
    // ortalama boylam gerçek periyotla ilerler
    CHECK_NEAR(mean_longitude_deg(E, E.period_days) , mean_longitude_deg(E, 0), 1e-6);
}

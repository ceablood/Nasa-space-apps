#include <cmath>

#include "kozmo/defense.hpp"
#include "kozmo/nav.hpp"
#include "kozmo/station.hpp"
#include "test_framework.hpp"

using namespace kozmo;

TEST("istasyon: ISS ölçeği — periyot ~92.7 dk, alçalma 50-150 m/gün, yeniden itki birkaç m/s") {
    auto s = station::iss_like();
    CHECK(s.mass_t() > 380 && s.mass_t() < 480);
    CHECK_NEAR(s.period_min(), 92.8, 0.5);
    const double a0 = s.altitude();
    auto r = s.advance_days(30);
    const double per_day = (a0 - s.altitude()) / 30;
    CHECK(per_day > 50 && per_day < 150);
    // güneş maksimumu alçalmayı hızlandırır
    auto s2 = station::iss_like();
    (void)s2.advance_days(30, 2.0);
    CHECK(a0 - s2.altitude() > (a0 - s.altitude()) * 1.8);
    auto b = s.reboost(a0, 300, true);
    CHECK(b.done && b.dv_ms > 0.5 && b.dv_ms < 5);
    CHECK_NEAR(s.altitude(), a0, 1e-6);
    CHECK(r.o2_used_kg > 0 && s.days_of_supplies() < 119);
}

TEST("istasyon: kenetlenme portları, mürettebat kapasitesi, yörüngeden düşme, kayıt") {
    station::Station s("Deneme", station::earth(), 300e3);
    CHECK(s.add_module(station::ModuleKind::Habitat).ok());
    CHECK(!s.set_crew(4).ok());
    CHECK(s.set_crew(3).ok());
    CHECK(s.dock("Kartal", 30).ok());
    CHECK(!s.dock("Kervan", 50).ok());                          // tek port
    CHECK(s.add_module(station::ModuleKind::Node).ok() && s.add_module(station::ModuleKind::DockingPort).ok());
    CHECK(s.dock("Kervan", 50).ok());
    CHECK(s.undock("Kartal").ok() && !s.undock("Kartal").ok());
    auto j = station::Station::from_json(json::parse(s.to_json().dump()).value());
    CHECK(j.ok() && j.value().docked().size() == 1 && j.value().crew() == 3);
    // yeniden itki olmadan 200 km'den düşüş
    station::Station low("Alçak", station::earth(), 200e3);
    (void)low.add_module(station::ModuleKind::Habitat);
    (void)low.advance_days(400);
    CHECK(low.deorbited());
    // Ay yörüngesinde atmosfer yok: alçalma yok
    station::Station lunar("Ay Kapısı", station::moon(), 100e3);
    (void)lunar.add_module(station::ModuleKind::Habitat);
    (void)lunar.advance_days(365);
    CHECK_NEAR(lunar.altitude(), 100e3, 1e-9);
}

TEST("savunma: çap/kütle/enerji, Palermo ve Torino gerçek değerlere yakın") {
    CHECK_NEAR(defense::diameter_km(19.7, 0.23), 0.34, 0.04);         // Apophis ~340 m
    CHECK_NEAR(defense::diameter_km(18.16, 0.15), 0.78, 0.05);        // Didymos ~780 m
    const auto& bennu = defense::catalog()[1];
    CHECK_NEAR(defense::palermo(bennu.probability, bennu.energy_mt(), bennu.years_to_event), -1.41, 0.25);   // Sentry: -1.41
    CHECK(defense::torino(bennu.probability, bennu.energy_mt(), bennu.years_to_event) == 0);   // 100 yıl dışı
    CHECK(defense::torino(1e-9, 1000) == 0 && defense::torino(0.999, 1e6) == 10);
    CHECK(defense::torino(1e-3, 50) == 2);
    // 1 Mt = 4.184e15 J; 1e9 kg 20 km/s -> 2e17 J ~ 47.8 Mt
    CHECK_NEAR(defense::impact_energy_mt(1e9, 20000), 47.8, 0.1);
    // Barringer: ~10 Mt -> ~1.1 km krater
    CHECK_NEAR(defense::effects(10).crater_km, 1.08, 0.1);
}

TEST("savunma: DART kinetik çarpma ~2.5-2.7 mm/s, uyarı süresi planı belirler") {
    const double M = defense::mass_kg(160, 2400);
    CHECK_NEAR(M, 5.1e9, 0.5e9);                                        // Dimorphos ~4.3-5e9 kg
    CHECK_NEAR(defense::kinetic_dv(3.6, 580, 6140, M) * 1000, 2.5, 0.3);
    CHECK_NEAR(defense::deflection_km(0.001, 365), 94.6, 0.1);          // 1 mm/s, 1 yıl -> ~95 km
    const auto& kz1 = defense::catalog()[3];
    auto ten = defense::plan_deflection(kz1, 3650);
    auto one_month = defense::plan_deflection(kz1, 30);
    CHECK(ten.sufficient && ten.impactors <= 3);
    CHECK(!one_month.sufficient);                                       // geç fark edilirse kinetik çarpma yetmez
    CHECK(defense::detectable({24.5}, 22.5, 1.1, 0.1) && !defense::detectable({20.0}, 22.5, 1.5, 1.0));
    CHECK(defense::assess_local(15, 17000, 101.3, 1e-3).atmosphere_burns);
    CHECK(!defense::assess_local(15, 17000, 0, 1e-3).atmosphere_burns);
}

TEST("navigasyon: Lambert çözücüsü Curtis Örnek 5.2 ile aynı") {
    auto s = nav::lambert({5000e3, 10000e3, 2100e3}, {-14600e3, 2500e3, 7000e3}, 3600, 398600e9, true);
    CHECK(s.ok());
    CHECK_NEAR(s.value().v1.x, -5992.5, 0.5);
    CHECK_NEAR(s.value().v1.y, 1925.4, 0.5);
    CHECK_NEAR(s.value().v1.z, 3245.6, 0.5);
    CHECK_NEAR(s.value().v2.x, -3312.5, 0.5);
    CHECK_NEAR(s.value().v2.y, -4196.6, 0.5);
    CHECK_NEAR(s.value().v2.z, -385.3, 0.5);
    // dairesel yörüngede çeyrek tur: hız dairesel hızla aynı
    const double mu = 398600e9, r = 7000e3, v = std::sqrt(mu / r), T = 2 * 3.14159265358979 * std::sqrt(r * r * r / mu);
    auto q = nav::lambert({r, 0, 0}, {0, r, 0}, T / 4, mu, true);
    CHECK(q.ok());
    CHECK_NEAR(q.value().v1.norm(), v, 1.0);
    CHECK(!nav::lambert({r, 0, 0}, {-r, 0, 0}, T / 2, mu).ok());       // 180° tekil
}

TEST("navigasyon: Dünya-Mars porkchop minimumu Hohmann'a yakın; düzeltme bütçesi") {
    auto p = nav::porkchop("earth", "mars", 0, 800, 10, 180, 340, 10);
    CHECK(p.ok());
    const auto& b = p.value().best;
    CHECK_NEAR(b.vinf_depart_ms, 2945, 150);                          // Hohmann v_inf ~2.94 km/s
    CHECK(b.tof_days > 200 && b.tof_days < 320);
    CHECK(b.c3_km2s2 > 7 && b.c3_km2s2 < 12);                         // gerçek pencereler C3 ~8-16
    CHECK(p.value().c3.size() == p.value().depart_days.size());
    CHECK(nav::correction_dv(1000, 100) < nav::correction_dv(1000, 10));   // erken düzeltme ucuz
}

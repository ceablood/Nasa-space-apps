#include "kozmo/flight.hpp"

#include <algorithm>
#include <cmath>

#include "kozmo/astro.hpp"

namespace kozmo::flight {

double Vec2::norm() const { return std::sqrt(x * x + y * y); }
Vec2 Vec2::unit() const {
    const double n = norm();
    return n > 0 ? Vec2{x / n, y / n} : Vec2{0, 0};
}

const char* event_name(EventType e) {
    switch (e) {
        case EventType::Liftoff: return "Kalkış";
        case EventType::PitchKick: return "Eğim tekmesi";
        case EventType::MaxQ: return "Max-Q";
        case EventType::StageBurnout: return "Kademe yanma sonu";
        case EventType::StageSeparation: return "Kademe ayrılması";
        case EventType::ApoapsisTargetReached: return "Apoapsis hedefte (motor kesildi)";
        case EventType::CoastStart: return "Süzülme";
        case EventType::CircularizeStart: return "Dairesel yörünge yanması";
        case EventType::OrbitAchieved: return "Yörüngeye ulaşıldı";
        case EventType::Crash: return "Yere çarptı";
        case EventType::OutOfPropellant: return "Yakıt bitti";
    }
    return "?";
}

// ------------------------------------------------------------------------ ABD Standart Atmosferi 1976
AtmosphereSample us_standard_1976(double z) {
    constexpr double R0 = 6356766.0;                 // standart atmosferin Dünya yarıçapı (m)
    constexpr double g0 = 9.80665, M = 0.0289644, Rstar = 8.3144598;
    struct Layer { double hb, Tb, Lb, Pb; };
    // jeopotansiyel taban yükseklikleri (m), taban sıcaklığı (K), sıcaklık gradyanı (K/m), taban basıncı (Pa)
    static const Layer L[] = {
        {0, 288.15, -0.0065, 101325.0},      {11000, 216.65, 0.0, 22632.06},
        {20000, 216.65, 0.001, 5474.889},    {32000, 228.65, 0.0028, 868.0187},
        {47000, 270.65, 0.0, 110.9063},      {51000, 270.65, -0.0028, 66.93887},
        {71000, 214.65, -0.002, 3.956420},
    };
    if (z < 0) z = 0;
    const double h = R0 * z / (R0 + z);             // jeopotansiyel yükseklik
    if (h > 84852.0) {
        // 86 km üstü: üstel yaklaşım (ölçek yüksekliği ~7 km; mühendislik yaklaşımı)
        const double T = 186.87;
        const double P86 = 0.3734;
        const double P = P86 * std::exp(-(z - 86000.0) / 7000.0);
        return {T, P, P * M / (Rstar * T)};
    }
    int i = 6;
    while (i > 0 && h < L[i].hb) --i;
    const Layer& l = L[i];
    const double T = l.Tb + l.Lb * (h - l.hb);
    double P;
    if (l.Lb == 0.0) P = l.Pb * std::exp(-g0 * M * (h - l.hb) / (Rstar * l.Tb));
    else P = l.Pb * std::pow(l.Tb / T, g0 * M / (Rstar * l.Lb));
    return {T, P, P * M / (Rstar * T)};
}

// ------------------------------------------------------------------------ yörünge
Orbit orbit_from_state(const Vec2& r, const Vec2& v, double mu, double R) {
    Orbit o{};
    const double rn = r.norm();
    o.specific_energy = 0.5 * v.dot(v) - mu / rn;
    const double h = r.cross(v);
    o.eccentricity = std::sqrt(std::max(0.0, 1.0 + 2.0 * o.specific_energy * h * h / (mu * mu)));
    o.bound = o.specific_energy < 0;
    if (o.bound) {
        o.semi_major_m = -mu / (2.0 * o.specific_energy);
        o.periapsis_alt_m = o.semi_major_m * (1 - o.eccentricity) - R;
        o.apoapsis_alt_m = o.semi_major_m * (1 + o.eccentricity) - R;
    } else {
        o.semi_major_m = INFINITY;
        o.periapsis_alt_m = h * h / (mu * (1 + o.eccentricity)) - R;
        o.apoapsis_alt_m = INFINITY;
    }
    return o;
}

State propagate(State s, double mu, double dt, int steps) {
    auto acc = [mu](const Vec2& r) { const double rn = r.norm(); return r * (-mu / (rn * rn * rn)); };
    for (int i = 0; i < steps; ++i) {
        const Vec2 k1v = acc(s.r), k1r = s.v;
        const Vec2 k2v = acc(s.r + k1r * (dt / 2)), k2r = s.v + k1v * (dt / 2);
        const Vec2 k3v = acc(s.r + k2r * (dt / 2)), k3r = s.v + k2v * (dt / 2);
        const Vec2 k4v = acc(s.r + k3r * dt), k4r = s.v + k3v * dt;
        s.r = s.r + (k1r + k2r * 2 + k3r * 2 + k4r) * (dt / 6);
        s.v = s.v + (k1v + k2v * 2 + k3v * 2 + k4v) * (dt / 6);
    }
    return s;
}

double vacuum_burn_dv(double m0, double prop, double isp, double thrust, double dt) {
    const double mdot = thrust / (isp * prop::kG0);
    double m = m0, v = 0, burned = 0;
    while (burned < prop - 1e-9) {
        const double step = std::min(dt, (prop - burned) / mdot);
        // RK4: dv/dt = F/m(t), m(t) = m - mdot t
        auto a = [&](double tau) { return thrust / (m - mdot * tau); };
        v += step / 6.0 * (a(0) + 4 * a(step / 2) + a(step));
        m -= mdot * step;
        burned += mdot * step;
    }
    return v;
}

// ------------------------------------------------------------------------ fırlatma simülasyonu
Result<AscentResult> simulate_ascent(const prop::Design& design, const AscentConfig& cfg) {
    if (design.stages.empty()) return make_error(ErrorCode::InvalidArgument, "Tasarımda kademe yok");
    if (cfg.dt_s <= 0 || cfg.dt_s > 1.0) return make_error(ErrorCode::InvalidArgument, "Zaman adımı 0-1 s olmalı");
    auto earth = astro::find("earth");
    const double mu = earth.value()->mu();
    const double Re = earth.value()->radius_m();
    // yıldız günü dönüş hızı; 2B düzlemde enlemin kosinüsüyle ölçeklenir (yüzey ve atmosfer aynı hızla döner)
    const double omega = 2.0 * astro::kPi / (std::fabs(earth.value()->rotation_h) * 3600.0) * 1.0027 *
                         std::cos(cfg.launch_latitude_deg * astro::kPi / 180.0);
    const double area = astro::kPi * cfg.diameter_m * cfg.diameter_m / 4.0;
    const double p0 = 101325.0;

    struct St { const prop::Engine* e; int n; double prop, dry; };
    std::vector<St> st;
    for (const auto& s : design.stages) {
        auto e = prop::find_engine(s.engine);
        if (!e) return e.error();
        st.push_back({e.value(), s.engine_count, s.propellant_t * 1000.0,
                      (s.propellant_t * s.structure_fraction + e.value()->mass_t * s.engine_count) * 1000.0});
    }
    const double crew_module_kg = design.crew > 0 ? (3.0 + 0.5 * design.crew) * 1000.0 : 0.0;
    AscentResult res;
    res.payload_kg = design.payload_t * 1000.0 + crew_module_kg;

    // başlangıç: ekvator düzleminde enlemin yüzey dönüş hızı kadar doğuya hız (2B yaklaşım)
    State s;
    s.r = {0, Re};
    s.v = {-omega * Re, 0};             // saat yönü tersine dönüş: (0, Re) noktasında doğu = -x
    s.mass_kg = res.payload_kg;
    for (const auto& x : st) s.mass_kg += x.prop + x.dry;

    std::size_t stage = 0;
    double prop_left = st[0].prop;
    enum class Phase { Vertical, GravityTurn, UpperBurn, Coast, Circularize, Done } phase = Phase::Vertical;
    double t = 0, sep_timer = 0, last_tel = -1e9;
    bool kicked = false, maxq_logged = false;
    double prev_q = 0;
    double last_thrust_accel = 10.0;
    const double r_target = Re + cfg.target_orbit_alt_m;
    auto ev = [&](EventType type) {
        res.events.push_back({type, t, s.r.norm() - Re, s.v.norm(), static_cast<int>(stage) + 1});
    };
    ev(EventType::Liftoff);

    while (t < cfg.max_time_s && phase != Phase::Done) {
        const double alt = s.r.norm() - Re;
        if (alt < -1.0 && t > 1.0) {
            ev(EventType::Crash);
            res.failure = "Roket yere çarptı";
            break;
        }
        const Vec2 up = s.r.unit();
        const Vec2 air_v = s.v - Vec2{-omega * s.r.y, omega * s.r.x};     // atmosfer ile birlikte dönen hava
        const auto atm = us_standard_1976(alt);
        const double q = 0.5 * atm.density_kgm3 * air_v.dot(air_v);
        if (q > res.max_q_pa) {
            res.max_q_pa = q;
            res.max_q_alt_m = alt;
            res.max_q_t_s = t;
        }
        if (!maxq_logged && q < prev_q && q > 1000 && t > 10) {
            ev(EventType::MaxQ);
            maxq_logged = true;
        }
        prev_q = q;
        const Orbit orb = orbit_from_state(s.r, s.v, mu, Re);

        // --- güdüm ve aşama mantığı
        bool thrusting = false;
        Vec2 dir = up;
        if (sep_timer > 0) {
            sep_timer -= cfg.dt_s;
        } else if (phase == Phase::Vertical || phase == Phase::GravityTurn) {
            thrusting = true;
            const double vs = air_v.norm();
            if (!kicked && vs > cfg.pitch_kick_speed_ms) {
                kicked = true;
                phase = Phase::GravityTurn;
                ev(EventType::PitchKick);
            }
            if (phase == Phase::GravityTurn) {
                // tekme anında yön, sonra hava-göreli hız vektörünü izle (sıfır hücum açısı)
                const Vec2 east{-up.y, up.x};          // dönüş yönü (doğu)
                const double k = cfg.pitch_kick_deg * astro::kPi / 180.0;
                const Vec2 kick_dir = up * std::cos(k) + east * std::sin(k);
                dir = (air_v.unit().dot(up) > std::cos(k)) ? kick_dir : air_v.unit();
            }
            if (stage > 0) phase = Phase::UpperBurn;
        } else if (phase == Phase::UpperBurn) {
            // kapalı döngü yörüngeye giriş güdümü: radyal ivme komutu hedef yükseklik ve dikey hız hatasından;
            // yatay hız dairesel yörünge hızına ulaşınca ve periapsis güvenli olunca motor kesilir
            const Vec2 horiz = Vec2{-up.y, up.x} * ((Vec2{-up.y, up.x}).dot(s.v) >= 0 ? 1.0 : -1.0);
            const double rn = s.r.norm();
            const double vr = s.v.dot(up), vh = s.v.dot(horiz);
            const double v_circ = std::sqrt(mu / rn);
            // kesme: yatay hız bulunduğu yükseklikteki dairesel yörünge hızına ulaştı ve periapsis atmosferin üstünde
            if (vh >= v_circ && orb.bound && orb.periapsis_alt_m > 140e3) {
                phase = Phase::Done;
                res.orbit = true;
                ev(EventType::OrbitAchieved);
                break;
            }
            thrusting = true;
            const double a_thr = std::max(1e-6, last_thrust_accel);
            // yükseklik tutma: hedefe uzaklıkla orantılı dikey hız komutu (sınırlı), hız hatası ~15 s'de kapatılır;
            // radyal ivme = komut + yerçekimi - merkezkaç (yörünge hızına yaklaştıkça gereken dikey itki azalır)
            const double vr_cmd = std::clamp((r_target - rn) / 60.0, -150.0, 400.0);
            const double a_r_cmd = (vr_cmd - vr) / 15.0 + mu / (rn * rn) - vh * vh / rn;
            const double sr = std::clamp(a_r_cmd / a_thr, -0.6, 0.9);
            dir = (up * sr + horiz * std::sqrt(1.0 - sr * sr)).unit();
        } else if (phase == Phase::Coast || phase == Phase::Circularize) {
            phase = Phase::UpperBurn;          // (eski süzülme mantığı; kapalı döngü güdüm kullanılır)
            continue;
        }

        // --- kademe yakıtı bitti mi?
        if (thrusting && prop_left <= 0) {
            ev(EventType::StageBurnout);
            if (stage + 1 < st.size()) {
                s.mass_kg -= st[stage].dry;
                ++stage;
                prop_left = st[stage].prop;
                ev(EventType::StageSeparation);
                sep_timer = cfg.stage_separation_coast_s;
                if (phase == Phase::Vertical || phase == Phase::GravityTurn) phase = Phase::UpperBurn;
                thrusting = false;
            } else {
                ev(EventType::OutOfPropellant);
                res.failure = "Yakıt bitti, yörüngeye ulaşılamadı";
                break;
            }
        }

        const St& cur = st[stage];
        const double isp = cur.e->isp_sl_s > 0 ? cur.e->isp_vac_s - (cur.e->isp_vac_s - cur.e->isp_sl_s) * atm.pressure_pa / p0
                                                : cur.e->isp_vac_s * std::max(0.0, 1.0 - 3.0 * atm.pressure_pa / p0);   // vakum nozulu atmosferde verimsiz
        double mdot = thrusting ? cur.e->thrust_vac_kn * 1000.0 * cur.n / (cur.e->isp_vac_s * prop::kG0) : 0.0;
        // motor kısma: ivme cfg.max_accel_g ile sınırlanır (gerçek roketler yapı/mürettebat için kısar)
        if (mdot > 0) {
            const double full = mdot * isp * prop::kG0;
            const double limit = cfg.max_accel_g * prop::kG0 * s.mass_kg;
            if (full > limit) mdot *= std::max(cfg.min_throttle, limit / full);
        }
        const double thrust = mdot * isp * prop::kG0;
        last_thrust_accel = thrust > 0 ? thrust / s.mass_kg : last_thrust_accel;

        // --- RK4 (kütle adım içinde doğrusal azalır)
        auto deriv = [&](const Vec2& r, const Vec2& v, double m, Vec2& dr, Vec2& dv) {
            const double rn = r.norm();
            const Vec2 g = r * (-mu / (rn * rn * rn));
            const Vec2 av = v - Vec2{-omega * r.y, omega * r.x};
            const auto a = us_standard_1976(rn - Re);
            const double avn = av.norm();
            const Vec2 drag = avn > 0 ? av * (-0.5 * a.density_kgm3 * avn * cfg.drag_coefficient * area / m) : Vec2{};
            dr = v;
            dv = g + drag + dir * (thrust / m);
        };
        const double h = cfg.dt_s;
        const double burn = std::min(mdot * h, prop_left);
        const double m0 = s.mass_kg, m1 = s.mass_kg - burn;
        Vec2 r1, v1, r2, v2, r3, v3, r4, v4;
        deriv(s.r, s.v, m0, r1, v1);
        deriv(s.r + r1 * (h / 2), s.v + v1 * (h / 2), 0.5 * (m0 + m1), r2, v2);
        deriv(s.r + r2 * (h / 2), s.v + v2 * (h / 2), 0.5 * (m0 + m1), r3, v3);
        deriv(s.r + r3 * h, s.v + v3 * h, m1, r4, v4);
        // kayıp muhasebesi (yerçekimi ve sürüklenme bileşenlerinin hız yönündeki etkisi)
        if (thrusting) {
            const double rn = s.r.norm();
            const Vec2 vu = s.v.unit();
            res.gravity_loss_ms += mu / (rn * rn) * std::max(0.0, vu.dot(up)) * h;
            res.drag_loss_ms += 0.5 * atm.density_kgm3 * air_v.dot(air_v) * cfg.drag_coefficient * area / m0 * h;
            res.max_accel_g = std::max(res.max_accel_g, thrust / m1 / prop::kG0);
        }
        s.r = s.r + (r1 + r2 * 2 + r3 * 2 + r4) * (h / 6);
        s.v = s.v + (v1 + v2 * 2 + v3 * 2 + v4) * (h / 6);
        s.mass_kg = m1;
        prop_left -= burn;
        t += h;
        if (t - last_tel >= cfg.telemetry_every_s) {
            last_tel = t;
            res.telemetry.push_back({t, s.r.norm() - Re, s.v.norm(), q, s.mass_kg,
                                     std::atan2(dir.dot(up), std::fabs(dir.dot(Vec2{up.y, -up.x}))) * 180.0 / astro::kPi});
        }
    }
    res.final_orbit = orbit_from_state(s.r, s.v, mu, Re);
    res.remaining_propellant_kg = std::max(0.0, prop_left);
    for (std::size_t i = stage + 1; i < st.size(); ++i) res.remaining_propellant_kg += st[i].prop;
    if (!res.orbit && res.failure.empty()) res.failure = "Zaman sınırı aşıldı";
    return res;
}

}  // namespace kozmo::flight

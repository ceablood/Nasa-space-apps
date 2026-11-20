#include "kozmo/vehicle.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::vehicle {

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kUllage = 1.03;
constexpr double kInterstage = 1.5;

double engine_section_length(const prop::Engine& e, int n) {
    // motor bölümü boyu (m): büyük motorlar daha uzun; çok motorlu kademelerde de tek motor boyu (paralel dizilir)
    const double base = e.thrust_vac_kn > 1500 ? 4.0 : (e.thrust_vac_kn > 500 ? 3.2 : (e.thrust_vac_kn > 50 ? 2.3 : 1.0));
    return e.propellant == "APCP" ? 1.5 : base + (n > 1 ? 0.3 : 0.0);
}
}  // namespace

double Propellant::bulk_density() const {
    if (mixture_ratio <= 0) return fuel_density;
    const double f = 1.0 / (1.0 + mixture_ratio), o = mixture_ratio / (1.0 + mixture_ratio);
    return 1.0 / (f / fuel_density + o / ox_density);
}

Result<Propellant> propellant(const std::string& key) {
    if (key == "RP-1/LOX") return Propellant{key, 810.0, 1141.0, 2.56};
    if (key == "LH2/LOX") return Propellant{key, 70.85, 1141.0, 6.0};
    if (key == "CH4/LOX") return Propellant{key, 422.6, 1141.0, 3.6};
    if (key == "APCP") return Propellant{key, 1770.0, 0.0, 0.0};
    if (key == "LH2 (nükleer)") return Propellant{key, 70.85, 0.0, 0.0};
    if (key == "Xenon") return Propellant{key, 1600.0, 0.0, 0.0};          // süperkritik depolama (yaklaşık)
    return make_error(ErrorCode::NotFound, "Bilinmeyen yakıt: " + key);
}

Result<Geometry> geometry(const prop::Design& d) {
    if (d.stages.empty()) return make_error(ErrorCode::InvalidArgument, "Tasarımda kademe yok");
    Geometry g;
    double base = 0;
    // kütle momentleri (t*m) kalkış anı için
    double mass = 0, moment = 0;
    auto add_mass = [&](double m, double z) {
        mass += m;
        moment += m * z;
    };
    double top_diameter = d.stages.front().diameter_m;
    for (std::size_t i = 0; i < d.stages.size(); ++i) {
        const prop::Stage& s = d.stages[i];
        auto e = prop::find_engine(s.engine);
        if (!e) return e.error();
        auto p = propellant(e.value()->propellant);
        if (!p) return p.error();
        if (s.diameter_m < 0.5 || s.diameter_m > 15.0) return make_error(ErrorCode::InvalidArgument, "Çap 0.5-15 m olmalı");
        StageGeometry sg{};
        sg.label = std::to_string(i + 1) + ". kademe";
        sg.diameter_m = s.diameter_m;
        const double prop_kg = s.propellant_t * 1000.0;
        if (p.value().mixture_ratio > 0) {
            sg.oxidizer_t = s.propellant_t * p.value().mixture_ratio / (1.0 + p.value().mixture_ratio);
            sg.fuel_t = s.propellant_t - sg.oxidizer_t;
            sg.tank_volume_m3 = (sg.fuel_t * 1000.0 / p.value().fuel_density + sg.oxidizer_t * 1000.0 / p.value().ox_density) * kUllage;
        } else {
            sg.fuel_t = s.propellant_t;
            sg.tank_volume_m3 = prop_kg / p.value().fuel_density * kUllage;
        }
        const double area = kPi * s.diameter_m * s.diameter_m / 4.0;
        sg.tank_length_m = sg.tank_volume_m3 / area;
        sg.engine_section_m = engine_section_length(*e.value(), s.engine_count);
        sg.stage_length_m = sg.tank_length_m + sg.engine_section_m + (i > 0 ? kInterstage : 0.0);
        sg.base_m = base;
        sg.dry_t = s.propellant_t * s.structure_fraction + e.value()->mass_t * s.engine_count;
        // kütleler: motorlar tabanda, yakıt + tank tank merkezinde
        add_mass(e.value()->mass_t * s.engine_count, base + sg.engine_section_m * 0.4);
        add_mass(s.propellant_t + s.propellant_t * s.structure_fraction,
                 base + sg.engine_section_m + (i > 0 ? kInterstage : 0.0) + sg.tank_length_m / 2.0);
        if (sg.tank_length_m / s.diameter_m > 25.0)
            g.notes.push_back(sg.label + " çok ince ve uzun (boy/çap " + std::to_string(static_cast<int>(sg.tank_length_m / s.diameter_m)) +
                              "): yapısal burkulma riski, çapı artır");
        if (i > 0 && s.diameter_m > d.stages[i - 1].diameter_m * 1.3)
            g.notes.push_back(sg.label + " alt kademeden belirgin geniş (çekiç başlı): aerodinamik yük artar");
        base += sg.stage_length_m;
        top_diameter = s.diameter_m;
        g.stages.push_back(sg);
    }
    // burun konisi / fairing: yük hacmi + ogive burun (boy 1.5 D)
    const double D = top_diameter;
    const double r = D / 2.0;
    const double crew_t = d.crew > 0 ? 3.0 + 0.5 * d.crew : 0.0;
    g.payload_volume_m3 = (d.payload_t + crew_t) * 1000.0 / kPayloadDensity;
    const double nose = 1.5 * D;
    const double nose_vol = kPi * r * r * nose * 0.5;            // ogive ~ silindir hacminin yarısı (yaklaşık)
    const double cyl = std::max(0.0, (g.payload_volume_m3 - nose_vol) / (kPi * r * r));
    g.fairing_length_m = nose + cyl;
    g.fairing_mass_t = kFairingAreal * (kPi * D * cyl + kPi * r * std::sqrt(r * r + nose * nose));
    add_mass(d.payload_t + crew_t, base + cyl * 0.5 + nose * 0.2);
    add_mass(g.fairing_mass_t, base + g.fairing_length_m * 0.45);
    g.total_height_m = base + g.fairing_length_m;

    // yan güçlendiriciler: yakıt hacmi -> boy; yanlarda, tabandan başlar
    if (d.boosters.count > 0) {
        auto e = prop::find_engine(d.boosters.engine);
        if (!e) return e.error();
        auto p = propellant(e.value()->propellant);
        if (!p) return p.error();
        const double bd = d.boosters.diameter_m;
        const double vol = d.boosters.propellant_t * 1000.0 / p.value().bulk_density() * kUllage;
        g.boosters = {d.boosters.count, bd, vol / (kPi * bd * bd / 4.0) + engine_section_length(*e.value(), 1) + bd * 1.2};
        const double each = d.boosters.propellant_t * (1.0 + d.boosters.inert_fraction);
        add_mass(each * d.boosters.count, g.boosters.length_m * 0.45);
        if (g.boosters.length_m > g.total_height_m * 0.8) g.notes.push_back("Güçlendiriciler çekirdekten uzun: bağlantı yapısı zorlanır");
    }
    g.center_of_mass_m = moment / mass;
    g.fineness = g.total_height_m / d.stages.front().diameter_m;
    // Barrowman: yalnız burun konisi kaldırma üretir (CN_alpha = 2); ogive CP'si burun boyunun 0.466'sında
    g.center_of_pressure_m = g.total_height_m - 0.466 * nose;
    g.static_margin_cal = (g.center_of_mass_m - g.center_of_pressure_m) / d.stages.front().diameter_m;
    g.needs_active_control = g.static_margin_cal < 1.0;
    if (g.needs_active_control)
        g.notes.push_back("Kanatçıksız roket statik olarak kararsız: uçuş itki vektörü kontrolüyle (motor gimbal) sağlanır — "
                          "Falcon 9 ve Saturn V de böyle uçar");
    return g;
}

}  // namespace kozmo::vehicle

#include "kozmo/astro.hpp"

#include <cmath>

namespace kozmo::astro {

const char* to_string(Source s) {
    switch (s) {
        case Source::NasaFactSheet: return "NASA NSSDC Planetary Fact Sheet (13 Kasım 2026)";
        case Source::Engineering: return "Mühendislik yaklaşımı";
        case Source::GameAssumption: return "Oyun varsayımı";
    }
    return "?";
}

const char* const kMoonsNote =
    "Uydu sayıları NASA NSSDC tablosundandır. NASA Science 'Moons' sayfasına göre Ekim 2026 itibarıyla "
    "gezegenler ve Plüton çevresinde toplam 461 resmî uydu vardır; yeni keşifler tabloya gecikmeli işlenir.";

namespace {
// NASA NSSDC Planetary Fact Sheet — metrik tablo, birebir aktarıldı.
// Gaz devlerinde "Surface Pressure: Unknown*" -> -1. Ay'ın uzaklık/periyot/hızı Dünya'ya göredir.
const std::vector<Body>& table() {
    static const std::vector<Body> t = {
        // key      ad          ana     kütle   çap      yoğ.  g     kaçış dönüş    gün     uzak.   peri.   afel.   periyot hız  eğim  eks.   obl.   T°C  basınç  uydu
        {"mercury", "Merkür", "sun", 0.330, 4879, 5429, 3.7, 4.3, 1407.6, 4222.6, 57.9, 46.0, 69.8, 88.0, 47.4, 7.0, 0.206, 0.034, 167, 0.0, 0, Source::NasaFactSheet},
        {"venus", "Venüs", "sun", 4.87, 12104, 5243, 8.9, 10.4, -5832.5, 2802.0, 108.2, 107.5, 108.9, 224.7, 35.0, 3.4, 0.007, 177.4, 464, 92.0, 0, Source::NasaFactSheet},
        {"earth", "Dünya", "sun", 5.97, 12756, 5514, 9.8, 11.2, 23.9, 24.0, 149.6, 147.1, 152.1, 365.2, 29.8, 0.0, 0.017, 23.4, 15, 1.0, 1, Source::NasaFactSheet},
        {"moon", "Ay", "earth", 0.073, 3475, 3340, 1.6, 2.4, 655.7, 708.7, 0.384, 0.363, 0.406, 27.3, 1.0, 5.1, 0.055, 6.7, -20, 0.0, 0, Source::NasaFactSheet},
        {"mars", "Mars", "sun", 0.642, 6792, 3934, 3.7, 5.0, 24.6, 24.7, 228.0, 206.7, 249.3, 687.0, 24.1, 1.8, 0.094, 25.2, -65, 0.01, 2, Source::NasaFactSheet},
        {"jupiter", "Jüpiter", "sun", 1898, 142984, 1326, 23.1, 59.5, 9.9, 9.9, 778.5, 740.6, 816.4, 4331, 13.1, 1.3, 0.049, 3.1, -110, -1.0, 95, Source::NasaFactSheet},
        {"saturn", "Satürn", "sun", 568, 120536, 687, 9.0, 35.5, 10.7, 10.7, 1432.0, 1357.6, 1506.5, 10747, 9.7, 2.5, 0.052, 26.7, -140, -1.0, 274, Source::NasaFactSheet},
        {"uranus", "Uranüs", "sun", 86.8, 51118, 1270, 8.7, 21.3, -17.2, 17.2, 2867.0, 2732.7, 3001.4, 30589, 6.8, 0.8, 0.047, 97.8, -195, -1.0, 28, Source::NasaFactSheet},
        {"neptune", "Neptün", "sun", 102, 49528, 1638, 11.0, 23.5, 16.1, 16.1, 4515.0, 4471.1, 4558.9, 59800, 5.4, 1.8, 0.010, 28.3, -200, -1.0, 16, Source::NasaFactSheet},
        {"pluto", "Plüton", "sun", 0.0130, 2376, 1850, 0.6, 1.2, -153.3, 153.3, 5906.4, 4436.8, 7375.9, 90560, 4.7, 17.2, 0.244, 119.5, -225, 0.00001, 5, Source::NasaFactSheet},
    };
    return t;
}

// Oyun varsayımı: epoch anındaki ortalama boylamlar (derece). Gerçek efemeris değildir; pencereler bu
// başlangıçtan gerçek periyotlarla ilerler, böylece fırlatma pencereleri fiziksel olarak tutarlıdır.
double epoch_longitude(const std::string& key) {
    if (key == "mercury") return 252.3;
    if (key == "venus") return 181.98;
    if (key == "earth") return 100.46;
    if (key == "mars") return 355.45;
    if (key == "jupiter") return 34.40;
    if (key == "saturn") return 49.94;
    if (key == "uranus") return 313.23;
    if (key == "neptune") return 304.88;
    if (key == "pluto") return 238.93;
    return 0.0;
}

double wrap360(double a) {
    a = std::fmod(a, 360.0);
    return a < 0 ? a + 360.0 : a;
}
}  // namespace

const std::vector<Body>& bodies() { return table(); }

Result<const Body*> find(const std::string& key) {
    for (const auto& b : table())
        if (b.key == key) return &b;
    return make_error(ErrorCode::NotFound, "Bilinmeyen gök cismi: " + key);
}

double circular_velocity(double mu, double r) { return std::sqrt(mu / r); }
double escape_velocity(double mu, double r) { return std::sqrt(2.0 * mu / r); }
double vis_viva(double mu, double r, double a) { return std::sqrt(mu * (2.0 / r - 1.0 / a)); }
double orbital_period(double mu, double a) { return 2.0 * kPi * std::sqrt(a * a * a / mu); }

double synodic_period_days(double t1, double t2) {
    const double d = std::fabs(1.0 / t1 - 1.0 / t2);
    return d > 0 ? 1.0 / d : INFINITY;
}

Hohmann hohmann(double mu, double r1, double r2) {
    const double a = 0.5 * (r1 + r2);
    Hohmann h{};
    h.dv_depart_ms = std::fabs(vis_viva(mu, r1, a) - circular_velocity(mu, r1));
    h.dv_arrive_ms = std::fabs(circular_velocity(mu, r2) - vis_viva(mu, r2, a));
    h.transfer_days = 0.5 * orbital_period(mu, a) / kDay;
    // hedef transfer süresince 180° - (açısal hız * süre) kadar ilerlemeli
    const double n2 = 360.0 / (orbital_period(mu, r2) / kDay);     // derece/gün
    h.phase_angle_deg = wrap360(180.0 - n2 * h.transfer_days);
    return h;
}

double burn_from_parking(double mu_planet, double r_park, double v_inf) {
    const double v_esc = escape_velocity(mu_planet, r_park);
    return std::sqrt(v_inf * v_inf + v_esc * v_esc) - circular_velocity(mu_planet, r_park);
}

double mean_longitude_deg(const Body& b, double days) {
    return wrap360(epoch_longitude(b.key) + 360.0 * days / b.period_days);
}

Result<TransferWindow> next_window(const std::string& from, const std::string& to, double from_lon, double to_lon) {
    auto f = find(from);
    auto t = find(to);
    if (!f) return f.error();
    if (!t) return t.error();
    const Body& A = *f.value();
    const Body& B = *t.value();
    if (A.parent != "sun" || B.parent != "sun")
        return make_error(ErrorCode::InvalidArgument, "Gezegenler arası pencere yalnızca Güneş yörüngesindekiler için");
    if (A.key == B.key) return make_error(ErrorCode::InvalidArgument, "Kalkış ve hedef aynı");
    const Hohmann h = hohmann(kMuSun, A.semi_major_m(), B.semi_major_m());
    TransferWindow w{};
    w.synodic_days = synodic_period_days(A.period_days, B.period_days);
    w.current_phase_deg = wrap360(to_lon - from_lon);
    w.required_phase_deg = h.phase_angle_deg;
    // faz açısı göreli açısal hızla değişir: d(faz)/dt = n_B - n_A
    const double rel = 360.0 / B.period_days - 360.0 / A.period_days;      // derece/gün (dış gezegen için < 0)
    double diff = wrap360(w.required_phase_deg - w.current_phase_deg);      // ileri yönde fark
    if (rel < 0) diff = wrap360(w.current_phase_deg - w.required_phase_deg);
    w.days_until = diff / std::fabs(rel);
    return w;
}

double DeltaVBudget::total(bool land, bool ret) const {
    double t = launch_to_leo_ms + departure_ms + capture_ms;
    if (land) t += landing_ms;
    if (ret) t += return_ms;
    return t;
}

Result<DeltaVBudget> mission_budget(const std::string& target) {
    if (target == "leo") {                 // alçak Dünya yörüngesi (~200 km): yalnızca fırlatma
        DeltaVBudget b{};
        b.launch_to_leo_ms = 9400.0;
        return b;
    }
    auto e = find("earth");
    auto tb = find(target);
    if (!tb) return tb.error();
    const Body& E = *e.value();
    const Body& T = *tb.value();
    DeltaVBudget b{};
    b.launch_to_leo_ms = 9400.0;      // Mühendislik yaklaşımı: ~7.8 km/s yörünge hızı + ~1.5-2 km/s kayıplar
    const double r_leo = E.radius_m() + 200e3;
    const double r_low = T.radius_m() * 1.10 + 50e3;      // hedefte düşük yörünge (oyun varsayımı: yarıçapın %10 üstü)
    if (T.key == "moon") {
        // Dünya-Ay: Hohmann, Dünya merkezli
        const Hohmann h = hohmann(E.mu(), r_leo, T.semi_major_m());
        b.departure_ms = h.dv_depart_ms;                                     // TLI ~3.1 km/s
        const double v_inf = h.dv_arrive_ms;
        b.capture_ms = burn_from_parking(T.mu(), r_low, v_inf);             // LOI
        b.landing_ms = circular_velocity(T.mu(), r_low) * 1.15;             // iniş + %15 süzülme/kayıp payı
        b.return_ms = b.landing_ms + b.capture_ms;                          // kalkış + TEI (Dünya'da atmosfer frenleme)
        return b;
    }
    if (T.parent != "sun") return make_error(ErrorCode::InvalidArgument, "Desteklenmeyen hedef: " + target);
    if (T.key == "earth") return make_error(ErrorCode::InvalidArgument, "Hedef Dünya olamaz");
    const Hohmann h = hohmann(kMuSun, E.semi_major_m(), T.semi_major_m());
    b.departure_ms = burn_from_parking(E.mu(), r_leo, h.dv_depart_ms);
    b.capture_ms = burn_from_parking(T.mu(), r_low, h.dv_arrive_ms);
    if (T.has_surface()) {
        // atmosferli gezegende paraşüt/ısı kalkanı kaybı azaltır (oyun varsayımı: basınca göre %40'a kadar)
        const double aero = T.surface_pressure_bar > 0.005 ? std::min(0.4, 0.15 + 0.25 * std::log10(1.0 + T.surface_pressure_bar * 100.0) / 4.0) : 0.0;
        b.landing_ms = circular_velocity(T.mu(), r_low) * (1.15 - aero);
        b.return_ms = circular_velocity(T.mu(), r_low) * 1.15 + b.capture_ms;   // yüzeyden kalkış + yörüngeden ayrılma
    } else {
        b.landing_ms = 0.0;          // gaz devi: yüzey yok, yörünge istasyonu
        b.return_ms = b.capture_ms;  // yörüngeden ayrılma
    }
    return b;
}

}  // namespace kozmo::astro

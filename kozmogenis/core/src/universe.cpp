#include "kozmo/universe.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <queue>
#include <set>

namespace kozmo::universe {

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kBoltzmann = 1.380649e-23;       // J/K (SI tanımı)
constexpr double kN2Mass = 28.0134 * 1.66053907e-27;   // kg, azot molekülü
}  // namespace

const char* to_string(SpectralClass c) {
    switch (c) {
        case SpectralClass::O: return "O";
        case SpectralClass::B: return "B";
        case SpectralClass::A: return "A";
        case SpectralClass::F: return "F";
        case SpectralClass::G: return "G";
        case SpectralClass::K: return "K";
        case SpectralClass::M: return "M";
    }
    return "?";
}

SpectralClass classify_star(double t) {
    if (t >= 30000) return SpectralClass::O;
    if (t >= 10000) return SpectralClass::B;
    if (t >= 7500) return SpectralClass::A;
    if (t >= 6000) return SpectralClass::F;
    if (t >= 5200) return SpectralClass::G;
    if (t >= 3700) return SpectralClass::K;
    return SpectralClass::M;
}

const char* to_string(PlanetType t) {
    switch (t) {
        case PlanetType::Rocky: return "Kayalık";
        case PlanetType::Desert: return "Çöl";
        case PlanetType::Ocean: return "Okyanus";
        case PlanetType::Ice: return "Buz";
        case PlanetType::Volcanic: return "Volkanik";
        case PlanetType::Airless: return "Atmosfersiz";
        case PlanetType::DenseAtmosphere: return "Yoğun atmosferli";
        case PlanetType::SuperEarth: return "Süper Dünya";
        case PlanetType::Dwarf: return "Cüce gezegen";
        case PlanetType::GasGiant: return "Gaz devi";
        case PlanetType::IceGiant: return "Buz devi";
    }
    return "?";
}

// ------------------------------------------------------------------------ yıldız fiziği
double main_sequence_lifetime_gyr(double m) {
    const double l = m < 0.43 ? 0.23 * std::pow(m, 2.3) : (m < 2.0 ? std::pow(m, 4.0) : 1.4 * std::pow(m, 3.5));
    return 10.0 * m / l;
}

Star make_star(double m, double age) {
    Star s{};
    s.mass_msun = m;
    s.luminosity_lsun = m < 0.43 ? 0.23 * std::pow(m, 2.3) : (m < 2.0 ? std::pow(m, 4.0) : 1.4 * std::pow(m, 3.5));
    s.radius_rsun = m < 1.0 ? std::pow(m, 0.8) : std::pow(m, 0.57);
    s.temperature_k = 5772.0 * std::pow(s.luminosity_lsun / (s.radius_rsun * s.radius_rsun), 0.25);
    s.lifetime_gyr = main_sequence_lifetime_gyr(m);
    s.age_gyr = std::min(age, s.lifetime_gyr);
    s.spectral = classify_star(s.temperature_k);
    return s;
}

double equilibrium_temperature(double l, double d, double a) {
    return 278.6 * std::pow(l, 0.25) * std::pow(1.0 - a, 0.25) / std::sqrt(d);
}
double habitable_inner_au(double l) { return std::sqrt(l / 1.1); }
double habitable_outer_au(double l) { return std::sqrt(l / 0.53); }

double planet_radius_earth(double m) {
    // Chen & Kipping (2017, ApJ 834:17) olasılıksal kütle-yarıçap ilişkisinin ortalama kolları:
    //   kayalık (< 2.04 M_E): R = 1.008 M^0.279 ; Neptün tipi (< 131.6 M_E): R = 0.808 M^0.589 ;
    //   Jüpiter tipi: yarıçap neredeyse sabit (~1 R_J = 11.2 R_E'de sınırlandı)
    if (m < 2.04) return 1.008 * std::pow(m, 0.279);
    if (m < 131.6) return std::min(0.808 * std::pow(m, 0.589), 11.2);
    return 11.2;
}

bool retains_atmosphere(double v_esc_kms, double t) {
    const double v_th = std::sqrt(2.0 * kBoltzmann * t / kN2Mass) / 1000.0;   // km/s
    return v_esc_kms >= 6.0 * v_th;
}

// ------------------------------------------------------------------------ adlandırma
std::string procedural_name(Rng& rng) {
    static const char* syl[] = {"ka", "ze", "ra", "ni", "tor", "vel", "sa", "mi", "do", "ar", "lu", "ke", "on", "ti",
                                "bar", "es", "ya", "nu", "gor", "il", "ma", "zen", "qua", "dra"};
    const int n = rng.range(2, 3);
    std::string s;
    for (int i = 0; i < n; ++i) s += syl[rng.range(0, 23)];
    s[0] = static_cast<char>(s[0] - 32);
    return s;
}

// ------------------------------------------------------------------------ galaksi
Galaxy::Galaxy(std::uint64_t seed, int count, double radius, int arms) : seed_(seed) {
    Rng rng(seed);
    for (int i = 0; i < count; ++i) {
        StarSystem sys = generate_system(static_cast<std::uint64_t>(i + 1), rng);
        // sarmal kol üzerinde konum (logaritmik sarmal + saçılma)
        const double r = radius * std::sqrt(rng.uniform(0.02, 1.0));
        const int arm = rng.range(0, arms - 1);
        const double theta = std::log(r / radius * 8.0 + 1.0) * 2.2 + arm * 2.0 * kPi / arms + rng.normal(0.0, 0.25);
        sys.x_ly = r * std::cos(theta) + rng.normal(0.0, radius * 0.02);
        sys.y_ly = r * std::sin(theta) + rng.normal(0.0, radius * 0.02);
        systems_.push_back(std::move(sys));
    }
}

StarSystem Galaxy::generate_system(std::uint64_t id, Rng& rng) const {
    StarSystem s;
    s.id = id;
    s.name = procedural_name(rng);
    // başlangıç kütle fonksiyonu: alçak kütleli yıldızlar baskın (M cüceleri ~%75) — Salpeter tipi örnekleme
    const double u = rng.uniform();
    double m;
    if (u < 0.75) m = rng.uniform(0.08, 0.5);
    else if (u < 0.88) m = rng.uniform(0.5, 0.85);
    else if (u < 0.96) m = rng.uniform(0.85, 1.15);
    else if (u < 0.99) m = rng.uniform(1.15, 2.0);
    else m = std::min(40.0, 2.0 * std::pow(1.0 - rng.uniform(), -1.0 / 1.35));
    s.star = make_star(m, rng.uniform(0.5, 12.0));
    const double L = s.star.luminosity_lsun;
    s.hz_inner_au = habitable_inner_au(L);
    s.hz_outer_au = habitable_outer_au(L);

    // gezegenler: Titius-Bode benzeri geometrik aralık (oyun varsayımı), kar çizgisi ötesinde devler daha olası
    const int n = rng.range(0, 8);
    const double snow = 2.7 * std::sqrt(L);
    double a = rng.uniform(0.03, 0.4) * std::sqrt(std::max(L, 0.01)) + 0.02;
    for (int i = 0; i < n; ++i) {
        Planet p{};
        p.name = s.name + " " + static_cast<char>('b' + i);
        p.semi_major_au = a;
        const bool beyond = a > snow;
        if (beyond && rng.chance(0.55)) p.mass_earth = rng.chance(0.5) ? rng.uniform(10, 25) : rng.uniform(50, 600);
        else p.mass_earth = std::exp(rng.uniform(std::log(0.02), std::log(8.0)));
        p.radius_earth = planet_radius_earth(p.mass_earth);
        p.albedo = p.mass_earth > 10 ? rng.uniform(0.3, 0.5) : rng.uniform(0.1, 0.4);
        p.equilibrium_temp_k = equilibrium_temperature(L, a, p.albedo);
        p.surface_gravity_g = p.mass_earth / (p.radius_earth * p.radius_earth);
        p.escape_velocity_kms = 11.186 * std::sqrt(p.mass_earth / p.radius_earth);
        p.retains_atmosphere = retains_atmosphere(p.escape_velocity_kms, p.equilibrium_temp_k * 1.5);   // ekzosfer daha sıcak
        p.in_habitable_zone = a >= s.hz_inner_au && a <= s.hz_outer_au;
        p.tidally_locked = a < 0.2 * std::sqrt(s.star.mass_msun);            // yakın yörünge: gelgit kilidi (yaklaşık)
        const double t = p.equilibrium_temp_k;
        if (p.mass_earth >= 50) p.type = PlanetType::GasGiant;
        else if (p.mass_earth >= 10) p.type = PlanetType::IceGiant;
        else if (p.mass_earth < 0.05) p.type = PlanetType::Dwarf;
        else if (!p.retains_atmosphere) p.type = t > 600 ? PlanetType::Volcanic : PlanetType::Airless;
        else if (p.mass_earth > 2.0) p.type = PlanetType::SuperEarth;
        else if (t > 450) p.type = PlanetType::DenseAtmosphere;
        else if (t < 200) p.type = PlanetType::Ice;
        else if (p.in_habitable_zone) p.type = rng.chance(0.4) ? PlanetType::Ocean : PlanetType::Rocky;
        else p.type = PlanetType::Desert;
        // koloni puanı (oyun varsayımı): yerçekimi 0.4-1.5 g, sıcaklık 200-320 K, atmosfer, katı yüzey
        double score = 0;
        if (p.mass_earth < 10) {
            score += 0.35 * std::max(0.0, 1.0 - std::fabs(p.surface_gravity_g - 1.0) / 0.8);
            score += 0.35 * std::max(0.0, 1.0 - std::fabs(t - 270.0) / 90.0);
            score += p.retains_atmosphere ? 0.2 : 0.0;
            score += p.in_habitable_zone ? 0.1 : 0.0;
            // gelgit kilidi: bir yüz sürekli gündüz, öbürü gece; yakın M cücesi yörüngelerinde ayrıca parlama riski
            if (p.tidally_locked) score -= s.star.spectral == SpectralClass::M ? 0.2 : 0.1;
        }
        p.colony_score = std::clamp(score, 0.0, 1.0);
        p.moons = p.mass_earth > 50 ? rng.range(4, 40) : (p.mass_earth > 0.3 ? rng.range(0, 3) : 0);
        s.planets.push_back(p);
        a *= rng.uniform(1.4, 2.1);
    }
    return s;
}

const StarSystem* Galaxy::find(std::uint64_t id) const {
    if (id == 0 || id > systems_.size()) return nullptr;
    return &systems_[id - 1];
}

double Galaxy::distance_ly(std::uint64_t a, std::uint64_t b) const {
    const StarSystem* A = find(a);
    const StarSystem* B = find(b);
    if (!A || !B) return INFINITY;
    return std::hypot(A->x_ly - B->x_ly, A->y_ly - B->y_ly);
}

Result<std::vector<std::uint64_t>> Galaxy::route(std::uint64_t from, std::uint64_t to, double max_jump) const {
    if (!find(from) || !find(to)) return make_error(ErrorCode::NotFound, "Bilinmeyen yıldız sistemi");
    if (max_jump <= 0) return make_error(ErrorCode::InvalidArgument, "Sıçrama menzili pozitif olmalı");
    using QE = std::pair<double, std::uint64_t>;
    std::priority_queue<QE, std::vector<QE>, std::greater<QE>> open;
    std::map<std::uint64_t, double> g;
    std::map<std::uint64_t, std::uint64_t> parent;
    std::set<std::uint64_t> closed;
    g[from] = 0;
    open.push({distance_ly(from, to), from});
    while (!open.empty()) {
        const auto [f, cur] = open.top();
        open.pop();
        if (closed.count(cur)) continue;
        if (cur == to) {
            std::vector<std::uint64_t> path{to};
            while (path.back() != from) path.push_back(parent[path.back()]);
            std::reverse(path.begin(), path.end());
            return path;
        }
        closed.insert(cur);
        for (const auto& s : systems_) {
            if (closed.count(s.id)) continue;
            const double d = distance_ly(cur, s.id);
            if (d > max_jump) continue;
            const double ng = g[cur] + d;
            auto it = g.find(s.id);
            if (it == g.end() || ng < it->second) {
                g[s.id] = ng;
                parent[s.id] = cur;
                open.push({ng + distance_ly(s.id, to), s.id});
            }
        }
    }
    return make_error(ErrorCode::NotFound, "Bu sıçrama menziliyle rota yok");
}

std::vector<std::pair<std::uint64_t, int>> Galaxy::best_colony_candidates(int n) const {
    std::vector<std::tuple<double, std::uint64_t, int>> all;
    for (const auto& s : systems_)
        for (int i = 0; i < static_cast<int>(s.planets.size()); ++i)
            if (s.planets[i].colony_score > 0) all.emplace_back(s.planets[i].colony_score, s.id, i);
    std::sort(all.begin(), all.end(), [](const auto& a, const auto& b) { return std::get<0>(a) > std::get<0>(b); });
    std::vector<std::pair<std::uint64_t, int>> out;
    for (int i = 0; i < n && i < static_cast<int>(all.size()); ++i) out.emplace_back(std::get<1>(all[i]), std::get<2>(all[i]));
    return out;
}

}  // namespace kozmo::universe

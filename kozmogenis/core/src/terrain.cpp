#include "kozmo/terrain.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::terrain {

namespace {
constexpr double kPi = 3.14159265358979323846;
std::uint64_t mix(std::uint64_t z) {
    z += 0x9E3779B97F4A7C15ull;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}
double lattice(long long ix, long long iy, std::uint64_t seed) {
    const std::uint64_t h = mix(seed ^ mix(static_cast<std::uint64_t>(ix) * 0x632BE59BD9B4E019ull ^ static_cast<std::uint64_t>(iy) * 0x85157AF5ull));
    return static_cast<double>(h >> 11) * (1.0 / 9007199254740992.0) * 2.0 - 1.0;   // [-1, 1)
}
double smooth(double t) { return t * t * t * (t * (t * 6 - 15) + 10); }   // quintic
}  // namespace

const char* to_string(Resource r) {
    switch (r) {
        case Resource::WaterIce: return "Su buzu";
        case Resource::Iron: return "Demir";
        case Resource::Titanium: return "Titanyum (ilmenit)";
        case Resource::Helium3: return "Helyum-3";
        case Resource::Regolith: return "Regolit";
    }
    return "?";
}

double value_noise(double x, double y, std::uint64_t seed) {
    const double fx = std::floor(x), fy = std::floor(y);
    const long long ix = static_cast<long long>(fx), iy = static_cast<long long>(fy);
    const double tx = smooth(x - fx), ty = smooth(y - fy);
    const double a = lattice(ix, iy, seed), b = lattice(ix + 1, iy, seed);
    const double c = lattice(ix, iy + 1, seed), d = lattice(ix + 1, iy + 1, seed);
    return (a + (b - a) * tx) + ((c + (d - c) * tx) - (a + (b - a) * tx)) * ty;
}

double fbm(double x, double y, std::uint64_t seed, int octaves, double lac, double gain) {
    double s = 0, amp = 1, norm = 0, f = 1;
    for (int o = 0; o < octaves; ++o) {
        s += amp * value_noise(x * f, y * f, seed + static_cast<std::uint64_t>(o) * 1013);
        norm += amp;
        amp *= gain;
        f *= lac;
    }
    return norm > 0 ? s / norm : 0.0;
}

Heightmap Heightmap::generate(const challenge::PlanetEnvironment& env, std::uint64_t seed, double size_m, double cell_m) {
    Heightmap m;
    m.size_m_ = std::max(100.0, size_m);
    m.cell_m_ = std::clamp(cell_m, 0.5, m.size_m_ / 8.0);
    m.n_ = static_cast<int>(std::lround(m.size_m_ / m.cell_m_)) + 1;
    m.h_.assign(static_cast<std::size_t>(m.n_) * m.n_, 0.0);
    m.cls_ = env.cls;
    m.water_ = env.water_availability;
    m.dust_ = env.dust_level;
    m.seed_ = seed;
    Rng rng(seed ^ 0xC0FFEEull);
    using challenge::PlanetClass;
    // 1) taban topografya: pürüzlülüğe göre genlik (engebeli 1.0 -> ~60 m dalgalanma / 2 km)
    const double amp = 5.0 + 55.0 * env.terrain_roughness;
    const double wl = 600.0;   // en büyük dalga boyu (m)
    for (int j = 0; j < m.n_; ++j)
        for (int i = 0; i < m.n_; ++i) {
            const double x = -m.size_m_ / 2 + i * m.cell_m_, y = -m.size_m_ / 2 + j * m.cell_m_;
            double h = amp * fbm(x / wl, y / wl, seed, 6);
            // sınıfa özgü biçimler
            if (env.cls == PlanetClass::Desert && env.pressure_kpa > 0.1) {
                // kumullar: rüzgâra dik sırtlar, dalga boyu ~150 m, asimetrik (rüzgâraltı dik)
                const double ph = (x * 0.94 + y * 0.34) / 150.0 * 2 * kPi + 2.0 * fbm(x / 400, y / 400, seed + 7, 3);
                const double s = std::sin(ph);
                h += 4.0 * (s > 0 ? s : 0.45 * s) * (0.6 + 0.4 * fbm(x / 800, y / 800, seed + 9, 2));
            }
            if (env.cls == PlanetClass::Ice) {
                // buz sırtları ve çatlaklar (Europa "double ridges"): keskin, ince
                const double r = 1.0 - std::fabs(fbm(x / 250, y / 250, seed + 11, 4));
                h += 6.0 * std::pow(r, 8.0);
            }
            if (env.volcanism > 0.3) {
                // lav akıntısı lobları: düz, hafif yükselmiş platolar
                const double v = fbm(x / 700, y / 700, seed + 13, 3);
                if (v > 0.2) h += 8.0 * std::min(1.0, (v - 0.2) * 4.0);
            }
            m.cell_ref(i, j) = h;
        }
    // 2) kraterler: atmosfersiz yüzeylerde çok, kalın atmosferde az (küçük cisimler yanar), Mars'ta orta
    double density = env.pressure_kpa < 0.1 ? 1.0 : (env.pressure_kpa < 2.0 ? 0.35 : (env.pressure_kpa < 50 ? 0.08 : 0.02));
    if (env.cls == PlanetClass::Ice || env.volcanism > 0.7) density *= 0.2;   // genç yüzeyler (Europa, Io) az kraterli
    // N(>D) = k D^-2 : km^2 başına 20 m'den büyük ~ density*80 krater (oyun ölçeği)
    const double area_km2 = (m.size_m_ / 1000.0) * (m.size_m_ / 1000.0);
    const int count = static_cast<int>(density * 80.0 * area_km2);
    const double dmin = 20.0, dmax = std::min(600.0, m.size_m_ / 3.0);
    for (int k = 0; k < count; ++k) {
        // ters dönüşüm: P(D > d) = (dmin/d)^2
        const double u = std::max(1e-9, rng.uniform());
        const double D = std::min(dmax, dmin / std::sqrt(u));
        Crater c{rng.uniform(-m.size_m_ / 2, m.size_m_ / 2), rng.uniform(-m.size_m_ / 2, m.size_m_ / 2), D, 0.2 * D, 0.04 * D};
        if (env.pressure_kpa > 0.1) {   // atmosferli yüzeyde aşınma: sığlaşma
            c.depth_m *= 0.6;
            c.rim_m *= 0.5;
        }
        m.craters_.push_back(c);
    }
    for (const Crater& c : m.craters_) {
        const double R = c.diameter_m / 2;
        const int i0 = std::max(0, static_cast<int>((c.x - 2 * R + m.size_m_ / 2) / m.cell_m_));
        const int i1 = std::min(m.n_ - 1, static_cast<int>((c.x + 2 * R + m.size_m_ / 2) / m.cell_m_) + 1);
        const int j0 = std::max(0, static_cast<int>((c.y - 2 * R + m.size_m_ / 2) / m.cell_m_));
        const int j1 = std::min(m.n_ - 1, static_cast<int>((c.y + 2 * R + m.size_m_ / 2) / m.cell_m_) + 1);
        for (int j = j0; j <= j1; ++j)
            for (int i = i0; i <= i1; ++i) {
                const double x = -m.size_m_ / 2 + i * m.cell_m_, y = -m.size_m_ / 2 + j * m.cell_m_;
                const double r = std::hypot(x - c.x, y - c.y) / R;
                double dh = 0;
                if (r < 1.0) dh = -c.depth_m * (1.0 - r * r) + c.rim_m;          // parabolik çanak, kenar seviyesinden
                else if (r < 2.0) dh = c.rim_m * std::pow(2.0 - r, 2.0);         // ejecta örtüsü
                m.cell_ref(i, j) += dh;
            }
    }
    // 3) lav tüpü girişleri: Ay ve volkanik dünyalarda
    const bool tubes = env.key == "moon" || env.key == "mars" || env.volcanism > 0.3;
    if (tubes) {
        const int pits = 1 + static_cast<int>(rng.uniform() * 2.0);
        for (int k = 0; k < pits; ++k) {
            Pit p{rng.uniform(-m.size_m_ * 0.4, m.size_m_ * 0.4), rng.uniform(-m.size_m_ * 0.4, m.size_m_ * 0.4), rng.uniform(40.0, 90.0), 0, 0};
            p.depth_m = p.diameter_m * rng.uniform(0.5, 1.0);   // Marius Hills: ~65 m çap, ~40 m derinlik
            p.cave_length_m = rng.uniform(200.0, 2000.0);
            m.pits_.push_back(p);
            const double R = p.diameter_m / 2;
            for (int j = 0; j < m.n_; ++j)
                for (int i = 0; i < m.n_; ++i) {
                    const double x = -m.size_m_ / 2 + i * m.cell_m_, y = -m.size_m_ / 2 + j * m.cell_m_;
                    if (std::hypot(x - p.x, y - p.y) < R) m.cell_ref(i, j) -= p.depth_m;   // dik duvarlı çukur
                }
        }
    }
    return m;
}

double Heightmap::at(int i, int j) const {
    i = std::clamp(i, 0, n_ - 1);
    j = std::clamp(j, 0, n_ - 1);
    return h_[static_cast<std::size_t>(j) * n_ + i];
}

double Heightmap::height(double x, double y) const {
    if (n_ == 0) return 0;
    const double fx = (x + size_m_ / 2) / cell_m_, fy = (y + size_m_ / 2) / cell_m_;
    const int i = static_cast<int>(std::floor(fx)), j = static_cast<int>(std::floor(fy));
    const double tx = std::clamp(fx - i, 0.0, 1.0), ty = std::clamp(fy - j, 0.0, 1.0);
    const double a = at(i, j), b = at(i + 1, j), c = at(i, j + 1), d = at(i + 1, j + 1);
    return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty;
}

double Heightmap::slope_deg(double x, double y) const {
    const double e = cell_m_;
    const double dx = (height(x + e, y) - height(x - e, y)) / (2 * e);
    const double dy = (height(x, y + e) - height(x, y - e)) / (2 * e);
    return std::atan(std::sqrt(dx * dx + dy * dy)) * 180.0 / kPi;
}

void Heightmap::normal(double x, double y, double& nx, double& ny, double& nz) const {
    const double e = cell_m_;
    const double dx = (height(x + e, y) - height(x - e, y)) / (2 * e);
    const double dy = (height(x, y + e) - height(x, y - e)) / (2 * e);
    const double l = std::sqrt(dx * dx + dy * dy + 1.0);
    nx = -dx / l;
    ny = -dy / l;
    nz = 1.0 / l;
}

double Heightmap::roughness(double x, double y, double radius) const {
    double s = 0, s2 = 0;
    int n = 0;
    const int k = std::max(1, static_cast<int>(radius / cell_m_));
    for (int dj = -k; dj <= k; ++dj)
        for (int di = -k; di <= k; ++di) {
            const double h = height(x + di * cell_m_, y + dj * cell_m_);
            s += h;
            s2 += h * h;
            ++n;
        }
    const double mean = s / n;
    return std::sqrt(std::max(0.0, s2 / n - mean * mean));
}

double Heightmap::min_height() const { return h_.empty() ? 0 : *std::min_element(h_.begin(), h_.end()); }
double Heightmap::max_height() const { return h_.empty() ? 0 : *std::max_element(h_.begin(), h_.end()); }

std::vector<LandingSite> Heightmap::find_landing_sites(double footprint, double max_slope, double max_rough, int count) const {
    std::vector<LandingSite> all;
    const double step = std::max(cell_m_ * 2, footprint);
    const double half = size_m_ / 2 - footprint;
    for (double y = -half; y <= half; y += step)
        for (double x = -half; x <= half; x += step) {
            double ms = 0;
            for (double dy = -footprint / 2; dy <= footprint / 2 + 1e-9; dy += footprint / 2)
                for (double dx = -footprint / 2; dx <= footprint / 2 + 1e-9; dx += footprint / 2) ms = std::max(ms, slope_deg(x + dx, y + dy));
            const double r = roughness(x, y, footprint / 2);
            bool pit = false;
            for (const auto& p : pits_)
                if (std::hypot(x - p.x, y - p.y) < p.diameter_m + footprint) pit = true;
            if (ms > max_slope || r > max_rough || pit) continue;
            LandingSite s{x, y, ms, r, height(x, y), 0, ""};
            s.score = std::clamp(1.0 - 0.6 * ms / max_slope - 0.4 * r / max_rough, 0.0, 1.0);
            s.reason = "eğim " + std::to_string(static_cast<int>(ms * 10) / 10.0).substr(0, 4) + "°, pürüzlülük " + std::to_string(r).substr(0, 4) + " m";
            all.push_back(s);
        }
    std::sort(all.begin(), all.end(), [](const LandingSite& a, const LandingSite& b) { return a.score > b.score; });
    // birbirine çok yakın adayları ele (en az 3 ayak izi)
    std::vector<LandingSite> out;
    for (const auto& s : all) {
        bool near = false;
        for (const auto& o : out)
            if (std::hypot(s.x - o.x, s.y - o.y) < footprint * 3) near = true;
        if (!near) out.push_back(s);
        if (static_cast<int>(out.size()) >= count) break;
    }
    return out;
}

void Heightmap::flatten(double x, double y, double radius) {
    double s = 0;
    int n = 0;
    std::vector<std::pair<int, int>> cells;
    for (int j = 0; j < n_; ++j)
        for (int i = 0; i < n_; ++i) {
            const double cx = -size_m_ / 2 + i * cell_m_, cy = -size_m_ / 2 + j * cell_m_;
            if (std::hypot(cx - x, cy - y) <= radius) {
                s += at(i, j);
                ++n;
                cells.push_back({i, j});
            }
        }
    if (!n) return;
    const double mean = s / n;
    for (auto [i, j] : cells) cell_ref(i, j) = mean;
}

double Heightmap::resource(Resource r, double x, double y) const {
    const double n = 0.5 + 0.5 * fbm(x / 300, y / 300, seed_ + 101 + static_cast<std::uint64_t>(r), 3);
    switch (r) {
        case Resource::WaterIce: {
            // kalıcı gölgeli krater içleri (Ay kutupları, LCROSS) ve yeraltı buzu (Mars)
            double shade = 0;
            for (const auto& c : craters_)
                if (std::hypot(x - c.x, y - c.y) < c.diameter_m / 2 * 0.7) shade = std::max(shade, std::min(1.0, c.diameter_m / 200.0));
            return std::clamp(water_ * (0.4 + 0.6 * shade) * (0.5 + n), 0.0, 1.0);
        }
        case Resource::Iron: return std::clamp((cls_ == challenge::PlanetClass::Volcanic || cls_ == challenge::PlanetClass::Airless ? 0.5 : 0.3) * (0.5 + n), 0.0, 1.0);
        case Resource::Titanium: return std::clamp(0.2 * (0.3 + n), 0.0, 1.0);   // Ay maria ilmenit (yaklaşık)
        case Resource::Helium3: return cls_ == challenge::PlanetClass::Airless ? std::clamp(0.1 * (0.5 + n), 0.0, 1.0) : 0.0;   // güneş rüzgârı implantasyonu
        case Resource::Regolith: return std::clamp(0.7 + 0.3 * n - dust_ * 0.0, 0.0, 1.0);
    }
    return 0;
}

Mesh Heightmap::mesh(int step) const {
    Mesh m;
    step = std::max(1, step);
    const int s = (n_ - 1) / step + 1;
    m.side = s;
    m.vertices.reserve(static_cast<std::size_t>(s) * s * 3);
    m.normals.reserve(static_cast<std::size_t>(s) * s * 3);
    for (int j = 0; j < s; ++j)
        for (int i = 0; i < s; ++i) {
            const double x = -size_m_ / 2 + i * step * cell_m_, y = -size_m_ / 2 + j * step * cell_m_;
            m.vertices.push_back(static_cast<float>(x));
            m.vertices.push_back(static_cast<float>(y));
            m.vertices.push_back(static_cast<float>(height(x, y)));
            double nx, ny, nz;
            normal(x, y, nx, ny, nz);
            m.normals.push_back(static_cast<float>(nx));
            m.normals.push_back(static_cast<float>(ny));
            m.normals.push_back(static_cast<float>(nz));
        }
    for (int j = 0; j + 1 < s; ++j)
        for (int i = 0; i + 1 < s; ++i) {
            const int a = j * s + i, b = a + 1, c = a + s, d = c + 1;
            m.triangles.insert(m.triangles.end(), {a, c, b, b, c, d});
        }
    return m;
}

}  // namespace kozmo::terrain

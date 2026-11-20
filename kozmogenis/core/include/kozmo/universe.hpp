// KozmoCore — prosedürel evren ve gezegen motoru (V30 §6, §7, Phase 7).
//
// Gerçek astrofizik bağıntıları (yaklaşık, ana dizi yıldızları; kaynaklar yorumlarda):
//   * Kütle-parlaklık:  L ~ M^4 (0.43-2 Msun), 1.4 M^3.5 (2-55), 0.23 M^2.3 (<0.43)
//   * Kütle-yarıçap:    R ~ M^0.8 (M < 1), M^0.57 (M >= 1)
//   * Etkin sıcaklık:   Stefan-Boltzmann, T = 5772 K * (L / R^2)^(1/4)   (Güneş: IAU nominal 5772 K)
//   * Ana dizi ömrü:    t ~ 10 Gyr * M / L
//   * Yaşanabilir bölge: iç = sqrt(L / 1.1) AU, dış = sqrt(L / 0.53) AU (Kasting tarzı basit sınırlar)
//   * Denge sıcaklığı:  T_eq = 278.6 K * L^(1/4) * (1 - A)^(1/4) / sqrt(d_AU)  (Dünya, A=0.3 -> 255 K)
//   * Atmosfer tutma:   Jeans ölçütü, v_kaçış >= 6 * v_termal(N2) (ders kitabı kuralı)
// Kütle dağılımı (Salpeter/Kroupa benzeri başlangıç kütle fonksiyonu) ve gezegen dizilişi OYUN VARSAYIMIDIR.
// Aynı tohum her zaman aynı evreni üretir (deterministik, kayıtta yalnızca tohum saklanır).
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::universe {

enum class SpectralClass { O, B, A, F, G, K, M };
const char* to_string(SpectralClass c);
SpectralClass classify_star(double temperature_k);

struct Star {
    double mass_msun, luminosity_lsun, radius_rsun, temperature_k, lifetime_gyr, age_gyr;
    SpectralClass spectral;
};
Star make_star(double mass_msun, double age_gyr);

enum class PlanetType {
    Rocky, Desert, Ocean, Ice, Volcanic, Airless, DenseAtmosphere, SuperEarth, Dwarf, GasGiant, IceGiant
};
const char* to_string(PlanetType t);

struct Planet {
    std::string name;
    double semi_major_au, mass_earth, radius_earth, albedo;
    double equilibrium_temp_k, surface_gravity_g, escape_velocity_kms;
    bool retains_atmosphere, in_habitable_zone, tidally_locked;
    PlanetType type;
    double colony_score;     // 0..1 koloni uygunluğu (oyun varsayımı: yerçekimi, sıcaklık, atmosfer, ışınım)
    int moons;
};

struct StarSystem {
    std::uint64_t id;
    std::string name;
    double x_ly, y_ly;       // galaksi düzleminde konum (ışık yılı)
    Star star;
    double hz_inner_au, hz_outer_au;
    std::vector<Planet> planets;
};

// Yardımcı fizik fonksiyonları (testlenebilir)
double equilibrium_temperature(double luminosity_lsun, double distance_au, double albedo);
double habitable_inner_au(double luminosity_lsun);
double habitable_outer_au(double luminosity_lsun);
double planet_radius_earth(double mass_earth);             // Chen & Kipping (2017) kütle-yarıçap ilişkisi
bool retains_atmosphere(double escape_kms, double temperature_k);
double main_sequence_lifetime_gyr(double mass_msun);

class Galaxy {
public:
    // systems: üretilecek yıldız sistemi sayısı; radius_ly: disk yarıçapı
    Galaxy(std::uint64_t seed, int systems, double radius_ly = 1000.0, int arms = 4);

    std::uint64_t seed() const { return seed_; }
    const std::vector<StarSystem>& systems() const { return systems_; }
    const StarSystem* find(std::uint64_t id) const;
    double distance_ly(std::uint64_t a, std::uint64_t b) const;

    // En kısa rota (A*): her sıçrama en fazla max_jump_ly; bulunamazsa NotFound
    Result<std::vector<std::uint64_t>> route(std::uint64_t from, std::uint64_t to, double max_jump_ly) const;

    // En iyi koloni adayı gezegenleri (puana göre)
    std::vector<std::pair<std::uint64_t, int>> best_colony_candidates(int n) const;

private:
    StarSystem generate_system(std::uint64_t id, Rng& rng) const;
    std::uint64_t seed_;
    std::vector<StarSystem> systems_;
};

std::string procedural_name(Rng& rng);

}  // namespace kozmo::universe

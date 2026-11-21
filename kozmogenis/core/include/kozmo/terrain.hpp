// KozmoCore — prosedürel gezegen yüzeyi (V30 §6, V41 §3.3): yükseklik haritası, kraterler, kumullar, buz
// sırtları, lav akıntıları, lav tüpü girişleri (pit), eğim/pürüzlülük, iniş yeri tehlike taraması, kaynak
// haritası ve 3B mesh çıktısı (UE ProceduralMeshComponent için).
//
// Gerçek / yaklaşık bağıntılar:
//   * Basit kraterlerde derinlik/çap ~0.2, kenar yüksekliği ~0.04 D (Pike 1977; Melosh 1989)
//   * Krater boyut-sıklık dağılımı N(>D) ~ D^-2 (Ay maria, yaklaşık)
//   * Apollo LM iniş eğimi sınırı ~12°; tehlike tarama mantığı NASA ALHAT/Mars 2020 TRN'den esinlenme
//   * Ay'da Marius Hills çukuru ~65 m çap (SELENE/LRO) — lav tüpü girişi ölçeği
//   * Kumul dalga boyu Mars'ta ~50-500 m (HiRISE gözlemleri, yaklaşık)
// Gürültü fonksiyonu, yoğunluklar ve kaynak olasılıkları OYUN VARSAYIMIDIR.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "kozmo/challenge.hpp"
#include "kozmo/core.hpp"

namespace kozmo::terrain {

struct Crater {
    double x, y, diameter_m, depth_m, rim_m;
};

struct Pit {                 // lav tüpü / mağara girişi
    double x, y, diameter_m, depth_m;
    double cave_length_m;    // tahmini tüp uzunluğu
};

enum class Resource { WaterIce, Iron, Titanium, Helium3, Regolith };
const char* to_string(Resource r);

struct LandingSite {
    double x, y;
    double max_slope_deg, roughness_m, height_m;
    double score;            // 0..1 (1 en güvenli)
    std::string reason;
};

struct Mesh {
    std::vector<float> vertices;     // x,y,z (m) üçlüleri
    std::vector<float> normals;      // x,y,z
    std::vector<int> triangles;      // indeks üçlüleri
    int side = 0;
};

class Heightmap {
public:
    Heightmap() = default;
    // size_m: kare bölge kenarı, cell_m: hücre boyu. Ortam sınıfına göre biçimlendirilir.
    static Heightmap generate(const challenge::PlanetEnvironment& env, std::uint64_t seed, double size_m = 2000.0, double cell_m = 10.0);

    int side() const { return n_; }
    double size() const { return size_m_; }
    double cell() const { return cell_m_; }
    double at(int i, int j) const;                   // ham hücre (sınırlanmış)
    double height(double x, double y) const;         // bilinear; x,y in [-size/2, size/2]
    double slope_deg(double x, double y) const;      // merkezi farkla eğim
    double roughness(double x, double y, double radius_m) const;   // yerel yükseklik std sapması
    void normal(double x, double y, double& nx, double& ny, double& nz) const;
    double min_height() const;
    double max_height() const;

    const std::vector<Crater>& craters() const { return craters_; }
    const std::vector<Pit>& pits() const { return pits_; }

    // İniş yeri taraması: ayak izi (m) içinde en büyük eğim ve pürüzlülük; en iyi 'count' yer
    std::vector<LandingSite> find_landing_sites(double footprint_m, double max_slope_deg, double max_roughness_m, int count) const;
    // Düzleştirme (inşaat alanı / iniş pisti): yarıçap içinde ortalamaya çeker
    void flatten(double x, double y, double radius_m);
    // Kaynak olasılığı (0..1): su buzu gölgede ve kutba yakın, demir lav düzlüklerinde vb.
    double resource(Resource r, double x, double y) const;

    Mesh mesh(int step = 1) const;                    // her 'step' hücrede bir köşe

private:
    double& cell_ref(int i, int j) { return h_[static_cast<std::size_t>(j) * n_ + i]; }
    int n_ = 0;
    double size_m_ = 0, cell_m_ = 0;
    std::vector<double> h_;
    std::vector<Crater> craters_;
    std::vector<Pit> pits_;
    challenge::PlanetClass cls_ = challenge::PlanetClass::Rocky;
    double water_ = 0, dust_ = 0;
    std::uint64_t seed_ = 0;
};

// Deterministik değer gürültüsü (fBm); testlenebilir
double value_noise(double x, double y, std::uint64_t seed);
double fbm(double x, double y, std::uint64_t seed, int octaves, double lacunarity = 2.0, double gain = 0.5);

}  // namespace kozmo::terrain

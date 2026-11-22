// KozmoCore — Dünya yörüngesi uydu takımyıldızları (V27 iletişim/hava/konum uyduları; gelir kaynağı).
//
// Gerçek bağıntılar / değerler:
//   * Kapsama yarım açısı (Dünya merkezli): lambda = acos(Re cos(e) / (Re + h)) - e   (e: en küçük yükseklik açısı)
//   * Tek uydu kapsama oranı f = (1 - cos lambda) / 2; N uydu için kaba üst sınır 1 - (1 - f)^N (rastgele dağılım)
//   * Yörünge yükseklikleri: Starlink ~550 km, güneş-eşzamanlı (SSO) ~700 km, GPS 20 200 km, GEO 35 786 km
//   * Gidiş-dönüş gecikmesi 2h/c: GEO ~239 ms (yer istasyonu altta), LEO 550 km ~3.7 ms
//   * LEO ömrü sürüklenmeyle sınırlı (aynı termosfer modeli; 550 km'de birkaç yıl itkisiz)
// Gelir ve maliyet değerleri OYUN VARSAYIMIDIR.
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::sats {

constexpr double kEarthRadiusKm = 6371.0;
constexpr double kC = 299792.458;   // km/s

enum class Orbit { LEO, SSO, MEO, GEO };
const char* to_string(Orbit o);
double altitude_km(Orbit o);
enum class Purpose { Communication, Navigation, Weather, EarthObservation };
const char* to_string(Purpose p);

double coverage_half_angle_rad(double altitude_km, double min_elevation_deg);
double single_coverage(double altitude_km, double min_elevation_deg);
double constellation_coverage(double altitude_km, double min_elevation_deg, int count);
double round_trip_ms(double altitude_km);
double period_min(double altitude_km);

struct Constellation {
    int id;
    std::string name;
    Purpose purpose;
    Orbit orbit;
    int active = 0, failed = 0;
    double mass_kg_each;
    double launched_day = 0;
    double coverage() const;
    double revenue_per_day() const;   // kredi
};

class Fleet {
public:
    Result<int> create(const std::string& name, Purpose p, Orbit o, double mass_kg_each);
    // fırlatma: n uydu ekler (roket kapasitesi dışarıda kontrol edilir)
    Status deploy(int id, int n, double day);
    // zaman: arızalar (yıllık %2, oyun varsayımı), LEO sürüklenme ömrü, gelir
    double advance(double days, double solar_factor, Rng& rng);
    const std::vector<Constellation>& constellations() const { return list_; }
    const Constellation* find(int id) const;
    double total_revenue() const { return revenue_; }
    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<Constellation> list_;
    int next_id_ = 1;
    double revenue_ = 0, decay_acc_ = 0;
};

// GPS: 4 uydunun aynı anda görülmesi gerekir; N uydu için görünür ortalama sayı ~ N f
double visible_average(double altitude_km, double min_elevation_deg, int count);

}  // namespace kozmo::sats

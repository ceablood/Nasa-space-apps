// KozmoCore — gezegen zorluk ve hayatta kalma motoru (V41 §3).
//
// Gerçek veriler (yuvarlanmış): yüzey yerçekimi, yarıçap, ortalama basınç, sıcaklık aralığı, atmosfer
// mol kütlesi ve ölçek yüksekliği — NASA NSSDC Planetary Fact Sheet / görev ölçümleri.
// Yüzey radyasyonu: Ay 1.37, Mars 0.64 mSv/gün (ölçüm, bkz. environment.hpp); Europa ~5400, Io ~36000
// mSv/gün (yayımlanmış model tahminleri, ölçüm değil). Armstrong sınırı 6.3 kPa (fizyoloji, gerçek).
// Arazi pürüzlülüğü, toz/su düzeyleri, zorluk ağırlıkları ve ekipman azaltma katsayıları OYUN VARSAYIMIDIR.
#pragma once

#include <array>
#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/universe.hpp"

namespace kozmo::challenge {

enum class PlanetClass { Rocky, Desert, Ice, Volcanic, Ocean, GasGiant, Airless, Radiation };
const char* to_string(PlanetClass c);

struct PlanetEnvironment {
    std::string key, name;
    PlanetClass cls = PlanetClass::Rocky;
    bool solid_surface = true;
    double gravity_ms2 = 9.81, radius_km = 6371;
    double pressure_kpa = 101.3;            // ortalama yüzey basıncı
    double molar_mass_gmol = 28.97;         // atmosfer
    double scale_height_km = 8.5;
    double temp_min_c = -89, temp_mean_c = 15, temp_max_c = 57;
    double dose_msv_day = 0.0066;
    std::string dose_source;
    double terrain_roughness = 0.3;         // 0 düz .. 1 çok engebeli (oyun varsayımı)
    double water_availability = 1.0;       // 0 yok .. 1 bol (buz/yeraltı suyu dahil; oyun varsayımı)
    double dust_level = 0.1;                // 0..1
    double wind_max_ms = 30;
    double bio_hazard = 0.0;                // 0..1 (bilinen biyolojik tehlike yok: Güneş Sistemi'nde 0)
    double volcanism = 0.0;                 // 0..1 aktif volkanizma
    bool acid_clouds = false;               // Venüs sülfürik asit bulutları
    std::string notes;

    double surface_density() const;        // kg/m^3 = P M / (R T)
    double density_at(double altitude_m) const;
    bool breathable_pressure() const { return pressure_kpa >= 6.3; }   // Armstrong sınırı üstü (yine de solunamaz olabilir)
};

// Güneş Sistemi gövdeleri: earth, moon, mars, venus, mercury, jupiter, io, europa, titan
Result<PlanetEnvironment> body_environment(const std::string& key);
// Prosedürel gezegeni zorluk modeline çevirir (universe::PlanetType -> sınıf, fiziksel değerlerden tahmin)
PlanetEnvironment from_procedural(const universe::Planet& p, std::uint64_t seed);

struct Equipment {
    bool pressure_suit = false;      // basınçlı uzay giysisi (vakum, düşük basınç)
    bool thermal_suit = false;       // aşırı soğuk/sıcak
    bool heated_habitat = false;
    bool cooling_system = false;
    double shielding_gcm2 = 0.0;     // habitat radyasyon kalkanı (g/cm^2; regolit/su)
    bool dust_filters = false;
    bool water_recycler = false;
    bool water_extractor = false;    // buz/regolit suyu çıkarma
    bool heat_shield = false;        // atmosfer girişi
    bool landing_radar = false;
    bool rover = false;
    bool pressure_hull = false;      // yüksek dış basınç (Venüs, okyanus tabanı)
    bool remote_probe = false;       // uzaktan numune robotu (lav, gaz devi)
};

enum class Category { Environmental, Gravity, Atmosphere, Temperature, Radiation, Terrain, Biological, Resource, Landing, Colony };
constexpr int kCategoryCount = 10;
const char* to_string(Category c);

struct Score {
    double raw = 0;           // 0 kolay .. 1 ölümcül (ekipmansız)
    double mitigated = 0;     // ekipmanla
    std::string reason;
    std::vector<std::string> missing;   // bu kategoriyi azaltacak eksik ekipman
};

enum class Weather { DustStorm, IceStorm, AcidRain, VolcanicAsh, ElectricStorm, StrongWind, MeteorShower, ThermalSwing };
const char* to_string(Weather w);

struct Profile {
    std::array<Score, kCategoryCount> scores{};
    double overall_raw = 0, overall = 0;
    bool landable = true;                // gaz devlerinde false: yalnız yörünge/atmosfer sondası
    std::vector<Weather> weather;        // atmosfer/iklim parametrelerinden türetilmiş olası olaylar
    std::vector<std::string> playable;   // bu gezegende oynanabilir içerik
    const Score& operator[](Category c) const { return scores[static_cast<int>(c)]; }
};

Profile assess(const PlanetEnvironment& env, const Equipment& eq);
std::vector<Weather> possible_weather(const PlanetEnvironment& env);

// Etkin hava olayı (olasılıklar gezegen parametrelerine bağlı; rastgele ama parametrelerden bağımsız değil)
struct WeatherEvent {
    Weather kind;
    double start_h, end_h;
    double intensity;          // 0..1
    double visibility;         // 0..1 görüş çarpanı
    double solar_factor;       // güneş paneli çarpanı
    double wind_ms;
};
// dt saat içinde başlayan olaylar (her türün ortalama sıklığı ortamın yoğunluğuyla ölçeklenir)
std::vector<WeatherEvent> roll_weather(const PlanetEnvironment& env, double now_h, double dt_h, Rng& rng);

// Dış mekânda (EVA) hayatta kalma
struct Survivor {
    double health = 1.0;
    double suit_o2_h = 8.0;          // giysi oksijeni (saat; ISS EMU ~8 saat — gerçek mertebe)
    double dose_msv = 0.0;
    double core_temp_c = 37.0;
    bool alive = true;
    std::string last_cause;
};
struct SurvivalTick {
    std::vector<std::string> hazards;     // bu adımda etkileyen tehlikeler
    double health_loss = 0;
};
// outdoors=false: basınçlı habitat/araç içinde (kalkan ve ısıtma Equipment'ten)
SurvivalTick survive(const PlanetEnvironment& env, const Equipment& eq, bool outdoors, double dt_h, const std::vector<WeatherEvent>& active,
                     double local_hour, Survivor& s);
// Gündüz/gece yüzey sıcaklığı (yerel saat 0..24): min-max arası sinüs (yaklaşım)
double surface_temp_c(const PlanetEnvironment& env, double local_hour);

}  // namespace kozmo::challenge

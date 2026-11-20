#include "kozmo/challenge.hpp"

#include <algorithm>
#include <cmath>

#include "kozmo/environment.hpp"

namespace kozmo::challenge {

namespace {
constexpr double kR = 8.314462618;    // J/(mol K)
constexpr double kPiC = 3.14159265358979323846;
double clamp01(double x) { return std::clamp(x, 0.0, 1.0); }
}  // namespace

const char* to_string(PlanetClass c) {
    switch (c) {
        case PlanetClass::Rocky: return "Kayalık";
        case PlanetClass::Desert: return "Çöl";
        case PlanetClass::Ice: return "Buz";
        case PlanetClass::Volcanic: return "Volkanik";
        case PlanetClass::Ocean: return "Okyanus";
        case PlanetClass::GasGiant: return "Gaz devi";
        case PlanetClass::Airless: return "Atmosfersiz";
        case PlanetClass::Radiation: return "Radyasyonlu";
    }
    return "?";
}

const char* to_string(Category c) {
    switch (c) {
        case Category::Environmental: return "Çevre";
        case Category::Gravity: return "Yerçekimi";
        case Category::Atmosphere: return "Atmosfer";
        case Category::Temperature: return "Sıcaklık";
        case Category::Radiation: return "Radyasyon";
        case Category::Terrain: return "Arazi";
        case Category::Biological: return "Biyolojik";
        case Category::Resource: return "Kaynak";
        case Category::Landing: return "İniş";
        case Category::Colony: return "Koloni";
    }
    return "?";
}

const char* to_string(Weather w) {
    switch (w) {
        case Weather::DustStorm: return "Toz/kum fırtınası";
        case Weather::IceStorm: return "Kar/buz fırtınası";
        case Weather::AcidRain: return "Asit yağmuru";
        case Weather::VolcanicAsh: return "Volkanik kül";
        case Weather::ElectricStorm: return "Elektrik fırtınası";
        case Weather::StrongWind: return "Şiddetli rüzgâr";
        case Weather::MeteorShower: return "Mikrometeor yağmuru";
        case Weather::ThermalSwing: return "Ani sıcaklık değişimi";
    }
    return "?";
}

double PlanetEnvironment::surface_density() const {
    if (pressure_kpa <= 0 || molar_mass_gmol <= 0) return 0.0;
    return pressure_kpa * 1000.0 * molar_mass_gmol / 1000.0 / (kR * (temp_mean_c + 273.15));
}

double PlanetEnvironment::density_at(double altitude_m) const {
    if (scale_height_km <= 0) return 0.0;
    return surface_density() * std::exp(-std::max(0.0, altitude_m) / (scale_height_km * 1000.0));
}

Result<PlanetEnvironment> body_environment(const std::string& key) {
    PlanetEnvironment e;
    e.key = key;
    auto dose = [&](const std::string& b) {
        auto d = env::surface_dose_msv_per_day(b);
        return d.ok() ? d.value() : 0.0;
    };
    if (key == "earth") {
        e.name = "Dünya"; e.cls = PlanetClass::Rocky;
        e.dose_msv_day = dose("earth"); e.dose_source = "UNSCEAR dünya ortalaması";
        e.wind_max_ms = 60; e.dust_level = 0.1;
    } else if (key == "moon") {
        e.name = "Ay"; e.cls = PlanetClass::Airless;
        e.gravity_ms2 = 1.62; e.radius_km = 1737.4; e.pressure_kpa = 0; e.molar_mass_gmol = 0; e.scale_height_km = 0;
        e.temp_min_c = -173; e.temp_mean_c = -20; e.temp_max_c = 127;
        e.dose_msv_day = dose("moon"); e.dose_source = "Chang'e-4 LND ölçümü";
        e.terrain_roughness = 0.5; e.water_availability = 0.15; e.dust_level = 0.8; e.wind_max_ms = 0;
        e.notes = "Kutup kraterlerinde su buzu (LCROSS 2009); keskin regolit tozu ekipmanı aşındırır";
    } else if (key == "mars") {
        e.name = "Mars"; e.cls = PlanetClass::Desert;
        e.gravity_ms2 = 3.71; e.radius_km = 3389.5; e.pressure_kpa = 0.636; e.molar_mass_gmol = 43.34; e.scale_height_km = 11.1;
        e.temp_min_c = -153; e.temp_mean_c = -65; e.temp_max_c = 20;
        e.dose_msv_day = dose("mars"); e.dose_source = "Curiosity RAD ölçümü";
        e.terrain_roughness = 0.5; e.water_availability = 0.35; e.dust_level = 0.9; e.wind_max_ms = 30;
        e.notes = "Soğuk çöl: yeraltı ve kutup buzu; küresel toz fırtınaları güneş enerjisini aylarca keser";
    } else if (key == "venus") {
        e.name = "Venüs"; e.cls = PlanetClass::Volcanic;
        e.gravity_ms2 = 8.87; e.radius_km = 6051.8; e.pressure_kpa = 9200; e.molar_mass_gmol = 43.45; e.scale_height_km = 15.9;
        e.temp_min_c = 462; e.temp_mean_c = 464; e.temp_max_c = 467;
        e.dose_msv_day = 0.007; e.dose_source = "tahmin: kalın atmosfer koruması (ölçüm yok)";
        e.terrain_roughness = 0.4; e.water_availability = 0.0; e.dust_level = 0.2; e.wind_max_ms = 1;
        e.volcanism = 0.5; e.acid_clouds = true;
        e.notes = "92 bar, 464 °C: Venera 13 yüzeyde 127 dakika dayanabildi";
    } else if (key == "mercury") {
        e.name = "Merkür"; e.cls = PlanetClass::Airless;
        e.gravity_ms2 = 3.7; e.radius_km = 2439.7; e.pressure_kpa = 0; e.molar_mass_gmol = 0; e.scale_height_km = 0;
        e.temp_min_c = -173; e.temp_mean_c = 167; e.temp_max_c = 427;
        e.dose_msv_day = 1.5; e.dose_source = "tahmin: Ay benzeri kozmik ışın + daha yoğun güneş (ölçüm yok)";
        e.terrain_roughness = 0.5; e.water_availability = 0.05; e.dust_level = 0.6; e.wind_max_ms = 0;
    } else if (key == "jupiter") {
        e.name = "Jüpiter"; e.cls = PlanetClass::GasGiant; e.solid_surface = false;
        e.gravity_ms2 = 24.79; e.radius_km = 69911; e.pressure_kpa = 100; e.molar_mass_gmol = 2.22; e.scale_height_km = 27;
        e.temp_min_c = -145; e.temp_mean_c = -110; e.temp_max_c = -100;
        e.dose_msv_day = 5400; e.dose_source = "Europa yörüngesi mertebesi (model tahmini), istasyonlar için";
        e.terrain_roughness = 0; e.water_availability = 0.2; e.dust_level = 0; e.wind_max_ms = 150;
        e.notes = "Katı yüzey yok: değerler 1 bar seviyesi içindir";
    } else if (key == "io") {
        e.name = "Io"; e.cls = PlanetClass::Volcanic;
        e.gravity_ms2 = 1.796; e.radius_km = 1821.6; e.pressure_kpa = 0; e.molar_mass_gmol = 0; e.scale_height_km = 0;
        e.temp_min_c = -183; e.temp_mean_c = -143; e.temp_max_c = -130;
        e.dose_msv_day = 36000; e.dose_source = "model tahmini (Jüpiter radyasyon kuşakları)";
        e.terrain_roughness = 0.6; e.water_availability = 0.0; e.dust_level = 0.3; e.wind_max_ms = 0; e.volcanism = 1.0;
        e.notes = "Güneş Sistemi'nin en aktif volkanik cismi: lav gölleri ~1600 °C";
    } else if (key == "europa") {
        e.name = "Europa"; e.cls = PlanetClass::Ice;
        e.gravity_ms2 = 1.315; e.radius_km = 1560.8; e.pressure_kpa = 0; e.molar_mass_gmol = 0; e.scale_height_km = 0;
        e.temp_min_c = -220; e.temp_mean_c = -171; e.temp_max_c = -148;
        e.dose_msv_day = 5400; e.dose_source = "model tahmini (yüzey ~5.4 Sv/gün)";
        e.terrain_roughness = 0.5; e.water_availability = 1.0; e.dust_level = 0.1; e.wind_max_ms = 0;
        e.notes = "Buz kabuğu altında küresel tuzlu okyanus (Galileo manyetometresi)";
    } else if (key == "titan") {
        e.name = "Titan"; e.cls = PlanetClass::Ice;
        e.gravity_ms2 = 1.352; e.radius_km = 2574.7; e.pressure_kpa = 146.7; e.molar_mass_gmol = 28.6; e.scale_height_km = 21;
        e.temp_min_c = -180; e.temp_mean_c = -179; e.temp_max_c = -178;
        e.dose_msv_day = 0.01; e.dose_source = "tahmin: kalın azot atmosferi koruması (ölçüm yok)";
        e.terrain_roughness = 0.3; e.water_availability = 0.8; e.dust_level = 0.2; e.wind_max_ms = 1;
        e.notes = "Metan/etan gölleri (Cassini); su buzu kaya gibi davranır";
    } else {
        return make_error(ErrorCode::NotFound, "Zorluk profili tanımlı değil: " + key);
    }
    return e;
}

PlanetEnvironment from_procedural(const universe::Planet& p, std::uint64_t seed) {
    Rng rng(seed ^ 0x9E3779B97F4A7C15ull);
    PlanetEnvironment e;
    e.key = p.name;
    e.name = p.name;
    e.gravity_ms2 = p.surface_gravity_g * 9.80665;
    e.radius_km = p.radius_earth * 6371.0;
    const double t = p.equilibrium_temp_k - 273.15;
    using T = universe::PlanetType;
    const bool atm = p.retains_atmosphere;
    e.pressure_kpa = atm ? rng.uniform(20.0, 300.0) : 0.0;
    e.molar_mass_gmol = atm ? 28.0 + rng.uniform(0.0, 16.0) : 0.0;
    e.scale_height_km = atm ? 8.0 * (e.molar_mass_gmol > 0 ? 28.97 / e.molar_mass_gmol : 1.0) * (p.equilibrium_temp_k / 255.0) / p.surface_gravity_g : 0.0;
    e.temp_mean_c = t;
    const double swing = atm ? 40.0 : 250.0;
    e.temp_min_c = t - swing * 0.6;
    e.temp_max_c = t + swing * 0.4;
    e.dose_msv_day = atm ? rng.uniform(0.005, 0.2) : rng.uniform(0.6, 2.0);
    e.dose_source = "prosedürel tahmin (oyun varsayımı)";
    e.terrain_roughness = rng.uniform(0.2, 0.7);
    e.water_availability = rng.uniform(0.0, 0.5);
    e.dust_level = rng.uniform(0.0, 0.6);
    e.wind_max_ms = atm ? rng.uniform(5.0, 60.0) : 0.0;
    switch (p.type) {
        case T::Desert: e.cls = PlanetClass::Desert; e.water_availability *= 0.2; e.dust_level = std::max(e.dust_level, 0.7); break;
        case T::Ocean: e.cls = PlanetClass::Ocean; e.water_availability = 1.0; e.terrain_roughness = 0.1; break;
        case T::Ice: e.cls = PlanetClass::Ice; e.water_availability = 1.0; break;
        case T::Volcanic: e.cls = PlanetClass::Volcanic; e.volcanism = rng.uniform(0.5, 1.0); break;
        case T::Airless: case T::Dwarf: e.cls = PlanetClass::Airless; break;
        case T::GasGiant: case T::IceGiant: e.cls = PlanetClass::GasGiant; e.solid_surface = false; e.pressure_kpa = 100; e.wind_max_ms = 120; break;
        case T::DenseAtmosphere: e.cls = PlanetClass::Rocky; e.pressure_kpa = rng.uniform(500.0, 9000.0); break;
        default: e.cls = PlanetClass::Rocky; break;
    }
    // çok yüksek doz alan gezegen radyasyon sınıfına girer (yıldıza yakın, manyetosfersiz)
    if (!atm && p.semi_major_au < 0.1) {
        e.cls = PlanetClass::Radiation;
        e.dose_msv_day = rng.uniform(50.0, 500.0);
    }
    return e;
}

std::vector<Weather> possible_weather(const PlanetEnvironment& e) {
    std::vector<Weather> w;
    const bool atm = e.pressure_kpa > 0.1;
    if (atm && e.dust_level > 0.3 && e.wind_max_ms > 10) w.push_back(Weather::DustStorm);
    if (atm && e.temp_min_c < -20 && e.water_availability > 0.3) w.push_back(Weather::IceStorm);
    if (e.acid_clouds) w.push_back(Weather::AcidRain);
    if (atm && e.volcanism > 0.3) w.push_back(Weather::VolcanicAsh);
    if (e.pressure_kpa > 50) w.push_back(Weather::ElectricStorm);
    if (e.wind_max_ms > 25) w.push_back(Weather::StrongWind);
    if (!atm && e.solid_surface) w.push_back(Weather::MeteorShower);
    if (e.temp_max_c - e.temp_min_c > 120) w.push_back(Weather::ThermalSwing);
    return w;
}

Profile assess(const PlanetEnvironment& e, const Equipment& q) {
    Profile p;
    auto& S = p.scores;
    auto set = [&](Category c, double raw, double mit, std::string reason, std::vector<std::string> missing) {
        Score& s = S[static_cast<int>(c)];
        s.raw = clamp01(raw);
        s.mitigated = clamp01(std::min(raw, mit));
        s.reason = std::move(reason);
        s.missing = std::move(missing);
    };
    const double gr = e.gravity_ms2 / 9.80665;
    const bool earthlike_air = e.key == "earth";

    // yerçekimi: düşük g (kemik/kas kaybı, hareket) ve yüksek g (yorgunluk, iniş/kalkış maliyeti)
    {
        const double lg = std::fabs(std::log10(std::max(1e-3, gr)));
        const double raw = gr < 1.0 ? 0.6 * lg : 1.2 * lg;
        set(Category::Gravity, raw, raw, gr < 1.0 ? "Düşük yerçekimi: kemik/kas kaybı, farklı yürüyüş" : (gr > 1.05 ? "Yüksek yerçekimi: yorgunluk, yüksek kalkış delta-v" : "Dünya benzeri"), {});
    }
    // atmosfer: solunabilir hava yok -> giysi; Armstrong sınırı altı vakum; çok yüksek basınç -> basınç gövdesi
    {
        double raw = earthlike_air ? 0.0 : 1.0;
        double mit = earthlike_air ? 0.0 : (q.pressure_suit ? 0.15 : 1.0);
        std::vector<std::string> miss;
        std::string why = earthlike_air ? "Solunabilir" : (e.pressure_kpa < 6.3 ? "Armstrong sınırının altında: vakum benzeri, kan kaynar" : "Solunamaz atmosfer");
        if (!earthlike_air && !q.pressure_suit) miss.push_back("basınçlı uzay giysisi");
        if (e.pressure_kpa > 500) {
            const double hp = std::min(1.0, std::log10(e.pressure_kpa / 101.3) / 2.0);
            raw = std::max(raw, hp);
            mit = std::max(mit, q.pressure_hull ? hp * 0.4 : hp);
            why = "Ezici yüzey basıncı (" + std::to_string(static_cast<int>(e.pressure_kpa / 101.3)) + " atm)";
            if (!q.pressure_hull) miss.push_back("basınç dayanımlı gövde");
        }
        set(Category::Atmosphere, raw, mit, why, miss);
    }
    // sıcaklık
    {
        const double cold = std::max(0.0, (-20.0 - e.temp_min_c) / 150.0);
        const double hot = std::max(0.0, (e.temp_max_c - 45.0) / 200.0);
        const double raw = std::max(cold, hot);
        double mc = cold, mh = hot;
        std::vector<std::string> miss;
        if (cold > 0) {
            if (q.thermal_suit && q.heated_habitat) mc *= 0.25;
            else {
                if (!q.thermal_suit) miss.push_back("termal giysi");
                if (!q.heated_habitat) miss.push_back("ısıtmalı habitat");
                if (q.thermal_suit || q.heated_habitat) mc *= 0.6;
            }
        }
        if (hot > 0) {
            if (q.cooling_system && q.thermal_suit) mh = hot > 1.0 ? 0.6 : hot * 0.3;
            else {
                if (!q.cooling_system) miss.push_back("soğutma sistemi");
                if (!q.thermal_suit) miss.push_back("termal giysi");
            }
        }
        set(Category::Temperature, raw, std::max(mc, mh),
            "Sıcaklık " + std::to_string(static_cast<int>(e.temp_min_c)) + " / " + std::to_string(static_cast<int>(e.temp_max_c)) + " °C", miss);
    }
    // radyasyon: yıllık doz / NASA kariyer sınırı
    {
        const double raw = e.dose_msv_day * 365.25 / env::kCareerLimitMsv;
        const double factor = env::kHabitatShielding / (1.0 + q.shielding_gcm2 / 20.0);
        std::vector<std::string> miss;
        if (raw > 0.2 && q.shielding_gcm2 < 20) miss.push_back("radyasyon kalkanı (>= 20 g/cm² regolit/su)");
        set(Category::Radiation, raw, raw * factor, "Yüzey dozu " + std::to_string(e.dose_msv_day).substr(0, 6) + " mSv/gün (" + e.dose_source + ")", miss);
    }
    // arazi
    {
        const double raw = e.terrain_roughness + (e.cls == PlanetClass::Ice ? 0.15 : 0.0) + e.volcanism * 0.3;   // buz çatlakları, lav
        std::vector<std::string> miss;
        if (!q.rover) miss.push_back("keşif aracı (rover)");
        set(Category::Terrain, e.solid_surface ? raw : 0.0, e.solid_surface ? raw * (q.rover ? 0.6 : 1.0) : 0.0,
            e.solid_surface ? "Engebe, krater ve yükseklik değişimi" : "Katı yüzey yok", miss);
    }
    // biyolojik
    set(Category::Biological, e.bio_hazard, e.bio_hazard, e.bio_hazard > 0 ? "Bilinmeyen biyolojik tehlike" : "Bilinen biyolojik tehlike yok", {});
    // kaynak: su başta
    {
        const double raw = (1.0 - e.water_availability) * 0.8 + (e.solid_surface ? 0.0 : 0.3);
        double mit = raw;
        std::vector<std::string> miss;
        if (q.water_recycler) mit *= 0.5; else miss.push_back("su geri dönüşümü");
        if (e.water_availability > 0.1) {
            if (q.water_extractor) mit *= 0.5; else miss.push_back("buz/regolit su çıkarıcı");
        }
        set(Category::Resource, raw, mit, "Su erişimi %" + std::to_string(static_cast<int>(e.water_availability * 100)), miss);
    }
    // çevre: toz, rüzgâr, volkanizma, asit
    {
        const bool atm = e.pressure_kpa > 0.1;
        const double dust = e.dust_level * (atm ? 0.5 : 0.35);
        const double wind = e.wind_max_ms / 200.0;
        const double volc = e.volcanism * 0.6;
        const double acid = e.acid_clouds ? 0.5 : 0.0;
        std::vector<std::string> miss;
        if (dust > 0.1 && !q.dust_filters) miss.push_back("toz filtreleri");
        if (volc > 0.2 && !q.remote_probe) miss.push_back("uzaktan numune robotu");
        set(Category::Environmental, dust + wind + volc + acid,
            dust * (q.dust_filters ? 0.3 : 1.0) + wind + volc * (q.remote_probe ? 0.4 : 1.0) + acid * (q.pressure_hull ? 0.3 : 1.0),
            "Toz, rüzgâr, volkanizma", miss);
    }
    // iniş
    {
        std::vector<std::string> miss;
        if (!e.solid_surface) {
            p.landable = false;
            set(Category::Landing, 1.0, 1.0, "İniş yapılamaz: katı yüzey yok (yörünge istasyonu / atmosfer sondası)", {});
        } else {
            const bool needs_shield = e.pressure_kpa > 0.3;
            const double raw = std::min(0.6, gr * 0.35) + (needs_shield ? 0.4 : 0.0) + e.terrain_roughness * 0.3 + e.dust_level * 0.1;
            double mit = std::min(0.6, gr * 0.35) + (needs_shield ? (q.heat_shield ? 0.1 : 0.4) : 0.0) +
                         e.terrain_roughness * 0.3 * (q.landing_radar ? 0.4 : 1.0) + e.dust_level * 0.1;
            if (needs_shield && !q.heat_shield) miss.push_back("ısı kalkanı (atmosfer girişi)");
            if (!q.landing_radar) miss.push_back("iniş radarı");
            set(Category::Landing, raw, mit, needs_shield ? "Atmosfer girişi + engebeli yüzey" : "Atmosfersiz: tamamen motorla iniş", miss);
        }
    }
    // koloni sürdürülebilirliği (diğer kategorilerin ağırlıklı birleşimi)
    {
        auto r = [&](Category c, bool mit) { return mit ? S[static_cast<int>(c)].mitigated : S[static_cast<int>(c)].raw; };
        auto mix = [&](bool m) {
            return 0.25 * r(Category::Atmosphere, m) + 0.2 * r(Category::Temperature, m) + 0.2 * r(Category::Radiation, m) +
                   0.2 * r(Category::Resource, m) + 0.15 * r(Category::Environmental, m);
        };
        set(Category::Colony, mix(false), mix(true), "Yaşam desteği, enerji ve bakım yükü", {});
    }
    double mx = 0, sum = 0, mxm = 0, summ = 0;
    for (const auto& s : S) {
        mx = std::max(mx, s.raw);
        sum += s.raw;
        mxm = std::max(mxm, s.mitigated);
        summ += s.mitigated;
    }
    p.overall_raw = 0.5 * mx + 0.5 * sum / kCategoryCount;
    p.overall = 0.5 * mxm + 0.5 * summ / kCategoryCount;
    p.weather = possible_weather(e);
    switch (e.cls) {
        case PlanetClass::GasGiant: p.playable = {"Atmosfer araştırması", "Yüksek irtifa sondası", "Yörünge istasyonu", "Fırtına gözlemi", "Gaz örneği"}; break;
        case PlanetClass::Desert: p.playable = {"Su arama", "Gölgeli/yalıtımlı üs", "Güneş enerjisi", "Yeraltı deposu"}; break;
        case PlanetClass::Ice: p.playable = {"Buz delme", "Isıtmalı üs", "Yeraltı okyanusu araştırması"}; break;
        case PlanetClass::Volcanic: p.playable = {"Uzaktan lav numunesi", "Jeotermal enerji", "Acil tahliye tatbikatı"}; break;
        case PlanetClass::Ocean: p.playable = {"Yüzer koloni", "Su altı araştırma", "Deniz tabanı istasyonu"}; break;
        case PlanetClass::Airless: p.playable = {"Güvenli iniş alanı tarama", "Kalkanlı üs", "Kutup buzu madenciliği"}; break;
        case PlanetClass::Radiation: p.playable = {"Radyasyon haritası", "Kalkanlı güvenli bölgeler", "Maruziyet takibi"}; break;
        case PlanetClass::Rocky: p.playable = {"Arazi taraması", "Madencilik", "Mağara keşfi"}; break;
    }
    return p;
}

std::vector<WeatherEvent> roll_weather(const PlanetEnvironment& e, double now_h, double dt_h, Rng& rng) {
    std::vector<WeatherEvent> out;
    for (Weather w : possible_weather(e)) {
        double mean_h = 24.0 * 30.0, dur = 6.0, vis = 1.0, sol = 1.0, wind = e.wind_max_ms * 0.3;
        switch (w) {   // ortalama sıklıklar oyun varsayımı; yoğunluk parametrelerle ölçeklenir
            case Weather::DustStorm: mean_h = 24.0 * 40.0 / std::max(0.1, e.dust_level); dur = rng.uniform(12.0, 120.0); vis = 0.25; sol = 0.5; wind = e.wind_max_ms * 0.8; break;
            case Weather::IceStorm: mean_h = 24.0 * 20.0; dur = rng.uniform(4.0, 24.0); vis = 0.3; sol = 0.6; break;
            case Weather::AcidRain: mean_h = 24.0 * 5.0; dur = rng.uniform(2.0, 12.0); vis = 0.6; break;
            case Weather::VolcanicAsh: mean_h = 24.0 * 15.0 / std::max(0.1, e.volcanism); dur = rng.uniform(6.0, 48.0); vis = 0.2; sol = 0.4; break;
            case Weather::ElectricStorm: mean_h = 24.0 * 10.0; dur = rng.uniform(1.0, 6.0); vis = 0.7; break;
            case Weather::StrongWind: mean_h = 24.0 * 7.0; dur = rng.uniform(2.0, 12.0); vis = 0.8; wind = e.wind_max_ms; break;
            case Weather::MeteorShower: mean_h = 24.0 * 60.0; dur = rng.uniform(1.0, 4.0); break;
            case Weather::ThermalSwing: mean_h = 24.0 * 12.0; dur = rng.uniform(2.0, 8.0); break;
        }
        if (rng.chance(1.0 - std::exp(-dt_h / mean_h))) {
            const double k = rng.uniform(0.4, 1.0);
            out.push_back({w, now_h, now_h + dur, k, 1.0 - (1.0 - vis) * k, 1.0 - (1.0 - sol) * k, wind * k});
        }
    }
    return out;
}

double surface_temp_c(const PlanetEnvironment& e, double h) {
    const double day = std::sin(kPiC * (h - 6.0) / 12.0);   // 6-18 gündüz
    const double f = day > 0 ? day : 0.0;
    return e.temp_min_c + (e.temp_max_c - e.temp_min_c) * f;
}

SurvivalTick survive(const PlanetEnvironment& e, const Equipment& q, bool outdoors, double dt, const std::vector<WeatherEvent>& active, double local_hour,
                     Survivor& s) {
    SurvivalTick t;
    if (!s.alive || dt <= 0) return t;
    auto hurt = [&](double amount, const std::string& why) {
        if (amount <= 0) return;
        s.health -= amount;
        t.health_loss += amount;
        t.hazards.push_back(why);
        s.last_cause = why;
    };
    const double temp = surface_temp_c(e, local_hour);
    const bool earth_air = e.key == "earth";
    if (outdoors) {
        if (!e.solid_surface) hurt(1.0, "Katı yüzey yok");
        if (e.pressure_kpa > 2000) hurt(1.0, "Ezici basınç: yüzeyde EVA mümkün değil");
        if (!earth_air) {
            if (!q.pressure_suit) hurt(1.0, e.pressure_kpa < 6.3 ? "Vakum maruziyeti (giysi yok)" : "Solunamaz atmosfer (giysi yok)");
            else {
                s.suit_o2_h -= dt;
                if (s.suit_o2_h <= 0) {
                    s.suit_o2_h = 0;
                    hurt(12.0 * dt, "Giysi oksijeni bitti");
                }
            }
        }
        // giysi termal aralığı: EMU ~ -157..+121 °C; termal giysi aralığı genişletir (oyun varsayımı)
        const double lo = q.thermal_suit ? -230.0 : (q.pressure_suit ? -157.0 : -40.0);
        const double hi = q.thermal_suit ? 200.0 : (q.pressure_suit ? 121.0 : 45.0);
        if (temp < lo) hurt(0.5 * dt * std::min(2.0, (lo - temp) / 30.0 + 0.2), "Aşırı soğuk");
        if (temp > hi) hurt(0.5 * dt * std::min(2.0, (temp - hi) / 30.0 + 0.2), "Aşırı sıcak");
        s.core_temp_c = 37.0 - std::max(0.0, lo - temp) * 0.02 + std::max(0.0, temp - hi) * 0.02;
        if (e.gravity_ms2 > 2.0 * 9.80665) hurt(0.01 * dt, "Yüksek yerçekimi yorgunluğu");
    }
    // radyasyon
    const double factor = outdoors ? 1.0 : env::kHabitatShielding / (1.0 + q.shielding_gcm2 / 20.0);
    const double dose = e.dose_msv_day * factor * dt / 24.0;
    s.dose_msv += dose;
    if (e.dose_msv_day * factor > 1000.0) hurt(dose / 4000.0, "Akut radyasyon (LD50 ~4 Sv)");
    if (!outdoors && e.temp_min_c < -50 && !q.heated_habitat) hurt(0.01 * dt, "Habitat ısıtması yetersiz");
    for (const auto& w : active) {
        if (!outdoors) continue;
        switch (w.kind) {
            case Weather::DustStorm: if (!q.dust_filters) hurt(0.01 * dt * w.intensity, "Toz giysi contalarını aşındırıyor"); break;
            case Weather::StrongWind: if (w.wind_ms > 40 && e.pressure_kpa > 50) hurt(0.03 * dt * w.intensity, "Şiddetli rüzgâr"); break;
            case Weather::MeteorShower: hurt(0.02 * dt * w.intensity, "Mikrometeor çarpması riski"); break;
            case Weather::AcidRain: hurt(0.2 * dt * w.intensity, "Asit yağmuru"); break;
            case Weather::VolcanicAsh: if (!q.dust_filters) hurt(0.03 * dt * w.intensity, "Volkanik kül"); break;
            case Weather::ElectricStorm: hurt(0.01 * dt * w.intensity, "Yıldırım riski"); break;
            default: break;
        }
    }
    s.health = std::clamp(s.health, 0.0, 1.0);
    if (s.health <= 0.0) s.alive = false;
    return t;
}

}  // namespace kozmo::challenge

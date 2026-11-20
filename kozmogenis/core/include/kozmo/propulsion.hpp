// KozmoCore — roket mühendisliği: motorlar, kademeler, Tsiolkovsky, itki/ağırlık, görev uygunluğu, risk.
//
// Motor değerleri gerçek motor SINIFLARINI temsil eden yuvarlanmış mühendislik yaklaşımlarıdır
// (ör. "Merlin 1D sınıfı"); belirli bir üreticinin ürünü değildir. Güvenilirlik ve maliyet oyun varsayımıdır.
#pragma once

#include <string>
#include <vector>

#include "kozmo/astro.hpp"
#include "kozmo/core.hpp"

namespace kozmo::prop {

constexpr double kG0 = 9.80665;   // standart yerçekimi ivmesi (m/s^2), Isp dönüşümü için

struct Engine {
    std::string key;
    std::string name_tr;
    std::string propellant;     // "RP-1/LOX", "LH2/LOX", "CH4/LOX", "Xenon", "LH2 (nükleer)"
    double isp_sl_s;            // deniz seviyesi özgül itki (s); 0 = atmosferde çalışamaz
    double isp_vac_s;           // vakum özgül itki (s)
    double thrust_vac_kn;       // vakum itkisi (kN)
    double mass_t;              // motor kuru kütlesi (ton)
    double reliability;         // tek motor görev başına başarı olasılığı (oyun varsayımı)
    double cost_mcr;            // maliyet (milyon kredi, oyun varsayımı)
    std::string research;       // gerekli araştırma anahtarı ("" = başlangıçta açık)
    astro::Source source = astro::Source::Engineering;

    double thrust_sl_kn() const { return isp_sl_s > 0 ? thrust_vac_kn * isp_sl_s / isp_vac_s : 0.0; }
};

const std::vector<Engine>& engines();
Result<const Engine*> find_engine(const std::string& key);

struct Stage {
    std::string engine;     // motor anahtarı
    int engine_count = 1;
    double propellant_t = 0.0;
    double structure_fraction = 0.08;   // tank+yapı kütlesi / itki yakıtı (mühendislik yaklaşımı: 0.05-0.12)
    double diameter_m = 3.7;            // gövde çapı (tank boyu ve aerodinamik için)
};

// Yan güçlendiriciler: ilk kademeyle PARALEL yanar, yakıtı bitince atılır (paralel kademe).
struct Boosters {
    std::string engine = "srb";        // her güçlendiricinin motoru (katı yakıtlı: motor = güçlendiricinin kendisi)
    int count = 0;
    double propellant_t = 0.0;          // HER güçlendirici için yakıt
    double inert_fraction = 0.17;       // gövde+nozul / yakıt (Shuttle SRB: ~87 t / ~503 t)
    double diameter_m = 3.7;
};

struct Design {
    std::string name;
    std::vector<Stage> stages;          // [0] = ilk (alt) kademe
    Boosters boosters;                  // isteğe bağlı yan güçlendiriciler (count = 0: yok)
    double payload_t = 1.0;
    int crew = 0;
    std::string target = "moon";
    bool land = true;
    bool ret = false;
};

struct StageReport {
    std::string label;                  // "Güçlendirici + 1. kademe", "1. kademe", ...
    double m0_t, mf_t;                  // kademe yanma başı/sonu toplam kütle (üst kademeler + yük dahil)
    double isp_used_s;
    double dv_ms;
    double twr;                         // ateşleme anı itki/ağırlık (Dünya g)
    double burn_s;
};

struct Report {
    std::vector<StageReport> stages;
    double liftoff_mass_t = 0;
    double total_dv_ms = 0;
    double required_dv_ms = 0;
    double margin_ms = 0;               // total - required
    double liftoff_twr = 0;
    double cost_mcr = 0;
    double success_p = 0;               // tam başarı olasılığı (oyun modeli)
    bool feasible = false;
    std::vector<std::string> problems;  // insan okunur engeller
};

// Motor kaybı toleransı (oyun varsayımı, gerçek mühendislik kavramı): 9+ motor 1, 27+ motor 2 arızaya dayanır.
int engine_out_tolerance(int engines);
double stage_reliability(double engine_reliability, int engines);

// Bir tasarımı analiz eder. Fizik gerçek (Tsiolkovsky, itki/ağırlık); risk modeli oyun varsayımıdır.
Result<Report> analyze(const Design& d, const std::vector<std::string>& unlocked_research);

// Gerekli delta-v'ye ulaşmak için en az yakıt (verilen kademe yapısında son kademeyi ölçekleyerek)
Result<double> min_upper_propellant(Design d, const std::vector<std::string>& unlocked_research, double step_t = 0.5,
                                    double max_t = 2000.0);

}  // namespace kozmo::prop

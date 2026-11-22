// KozmoCore — ajans üssü ve tesisler (V27/V30 üs yönetimi; AETHER-X prototipindeki 12 tesisin C++ karşılığı).
// Her tesisin seviyesi (0-3) oyunun gerçek yeteneklerini belirler: fırlatılabilecek en büyük roket kütlesi,
// eşzamanlı görev sayısı, araştırma hızı, astronot kapasitesi/eğitim hızı, depo kapasitesi, sözleşme sayısı,
// NOVA özellikleri, iletişim menzili (Ay / Mars / dış gezegenler), yakıt üretim indirimi, sağlık ve dinlenme.
// Maliyetler ve etki katsayıları OYUN VARSAYIMIDIR (iletişim menzili gerçek uzaklık ölçekleriyle sınıflandırılır:
// Ay 384 400 km, Mars 55-400 milyon km, Jüpiter ~600-970 milyon km — NASA DSN 34/70 m antenlerin işlediği aralık).
#pragma once

#include <array>
#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/economy.hpp"
#include "kozmo/json.hpp"

namespace kozmo::agency {

enum class Facility { LaunchPads, Research, AstronautCenter, Depot, MissionBoard, NovaCenter, MissionControl, FuelDepot, Hangar, CommsTower,
                      Medical, Recreation };
constexpr int kFacilityCount = 12;
const char* to_string(Facility f);

struct FacilitySpec {
    Facility facility;
    std::string name, description;
    int start_level, max_level;
    std::array<double, 4> upgrade_cost;     // seviyeye çıkış maliyeti (0. indeks kullanılmaz)
    std::array<double, 4> upkeep_per_day;   // seviyeye göre günlük gider
    std::array<double, 4> build_days;       // inşaat süresi
};
const FacilitySpec& spec(Facility f);

struct Capabilities {
    int pads;                    // eşzamanlı hazırlanan roket
    double max_liftoff_t;        // en büyük kalkış kütlesi
    int concurrent_missions;
    double research_speed;       // çarpan
    int astronaut_capacity;
    double training_speed;
    double depot_capacity_t;
    int contract_slots;
    int nova_level;              // 0 yok, 1 temel tavsiye, 2 pencere/uyarı, 3 otonom plan
    double comms_range_km;
    double fuel_discount;        // 0..1
    int max_stages;
    double medical_recovery;     // sağlık/gün
    double fatigue_recovery;     // yorgunluk/gün
};

struct Upgrade {
    Facility facility;
    int to_level;
    double done_day;
};

class Base {
public:
    Base();
    int level(Facility f) const { return levels_[static_cast<std::size_t>(f)]; }
    Capabilities capabilities() const;
    // seviye yükselt: kredi peşin, inşaat süresi sonunda etkin; aynı anda en çok 2 inşaat
    Status upgrade(Facility f, econ::Wallet& w, double day);
    // zaman: tamamlanan yükseltmeleri uygular, günlük gideri düşer; mesajlar döner
    std::vector<std::string> advance(double day, econ::Wallet& w);
    const std::vector<Upgrade>& pending() const { return pending_; }
    double upkeep_per_day() const;
    bool can_reach(double distance_km) const { return distance_km <= capabilities().comms_range_km; }
    bool max_base() const;

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::array<int, kFacilityCount> levels_{};
    std::vector<Upgrade> pending_;
    double last_day_ = 0;
};

}  // namespace kozmo::agency

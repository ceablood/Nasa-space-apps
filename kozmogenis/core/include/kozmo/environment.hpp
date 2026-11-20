// KozmoCore — çevre, uzay havası ve radyasyon (V30 §6.3, §18).
//
// Ölçülmüş doz oranları (yüzeyde, korumasız; yayımlanmış ölçümler, yuvarlanmış):
//   Ay yüzeyi        1.37 mSv/gün   Chang'e-4 Lunar Lander Neutron & Dosimetry (Zhang vd., Science Advances 2020)
//   Mars yüzeyi      0.64 mSv/gün   Curiosity RAD (Hassler vd., Science 2014)
//   Gezegenler arası 1.84 mSv/gün   MSL seyir ölçümü (Zeitlin vd., Science 2013)
//   Dünya yüzeyi     ~2.4 mSv/yıl   dünya ortalaması doğal radyasyon (UNSCEAR)
//   Kariyer sınırı   600 mSv        NASA-STD-3001 (2022 revizyonu)
// Olay sıklıkları, şiddet dağılımları ve habitat koruma katsayısı OYUN VARSAYIMIDIR (gerçekte güneş döngüsüne bağlıdır).
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::env {

constexpr double kCareerLimitMsv = 600.0;
constexpr double kHabitatShielding = 0.5;     // habitat içi doz / dış doz (oyun varsayımı)

// Gök cisminin yüzeyindeki korumasız günlük doz (mSv/gün). Ölçüm yoksa NotFound döner.
Result<double> surface_dose_msv_per_day(const std::string& body);
double cruise_dose_msv_per_day();             // gezegenler arası yolculuk

enum class EventKind { SolarParticleEvent, RegionalDustStorm, GlobalDustStorm, MicrometeoroidImpact };
const char* to_string(EventKind k);

struct ActiveEvent {
    EventKind kind;
    std::string body;          // "all" = güneş olayı (tüm iç sistem)
    double start_day, end_day;
    double solar_factor;       // güneş paneli üretim çarpanı (toz fırtınası)
    double extra_dose_msv_per_day;
};

// Olaylar (EventBus)
struct EnvironmentEventStarted { EventKind kind; std::string body; double duration_days; };
struct EnvironmentEventEnded { EventKind kind; std::string body; };

class Scheduler {
public:
    // Her gün için olay olasılıklarını değerlendirir; bodies: koloni bulunan gök cisimleri
    void advance(double day_from, double day_to, const std::vector<std::string>& bodies, Rng& rng, EventBus* bus);
    // Bir gök cismi için şu anki çarpanlar
    double solar_factor(const std::string& body, double day) const;
    double extra_dose(const std::string& body, double day) const;
    bool impact_pending(const std::string& body);     // mikrometeoroid çarpması gerçekleşti mi (tüketir)
    const std::vector<ActiveEvent>& active() const { return active_; }
    const std::vector<ActiveEvent>& history() const { return history_; }

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<ActiveEvent> active_;
    std::vector<ActiveEvent> history_;
    std::vector<std::string> impacts_;
    double last_day_ = 0.0;
};

}  // namespace kozmo::env

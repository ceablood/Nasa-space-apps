// KozmoCore — yörünge istasyonları (V30 §15.1, V41 §4.2-E yörünge kolonisi).
//
// Gerçek / yaklaşık:
//   * Dünya termosferi yoğunluğu 400 km'de ~1e-12 .. 1e-11 kg/m^3 (güneş etkinliğine bağlı; NRLMSISE-00 mertebesi).
//     Modelde üstel yaklaşım: rho(h) = rho0 * exp(-(h - 400 km) / H), H ~ 58 km, rho0 = 3e-12 (ortalama etkinlik).
//   * ISS: ~420 t, irtifa ~400-420 km, alçalma tipik 50-100 m/gün (güneş maksimumunda daha fazla), yıllık
//     yeniden itki gereksinimi birkaç m/s mertebesi; Cd ~2.2.
//   * Dairesel yörüngede yarı büyük eksen değişimi: da/dt = -rho * Cd * A / m * sqrt(mu * a)
//   * Yeniden itki: delta-v ~ (v / 2a) * delta_a (küçük değişim yaklaşımı)
// Modül kütle/güç/kapasite değerleri ISS modüllerinden yuvarlanmış mühendislik yaklaşımıdır.
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::station {

enum class ModuleKind { Node, Habitat, Lab, SolarTruss, DockingPort, Cupola, Airlock, Storage, Propulsion };
const char* to_string(ModuleKind k);

struct ModuleSpec {
    ModuleKind kind;
    std::string name;
    double mass_t;
    double power_kw;          // + üretim, - tüketim
    int crew;                 // yaşam kapasitesi
    double area_m2;           // sürüklenme kesit alanına katkı
    int ports;                // kenetlenme portu sayısı
};
const ModuleSpec& spec(ModuleKind k);

struct Body {                 // istasyonun dolandığı cisim
    double mu, radius_m;
    bool atmosphere;          // sürüklenme modeli (yalnız Dünya kalibre)
};
Body earth();
Body moon();

double thermosphere_density(double altitude_m, double solar_activity = 1.0);   // 0.5 minimum .. 2 maksimum

struct DockedVehicle {
    int port;
    std::string name;
    double mass_t;
};

struct TickReport {
    double altitude_loss_m = 0;
    double power_kw = 0;
    double o2_used_kg = 0, water_used_kg = 0;
    std::vector<std::string> warnings;
};

class Station {
public:
    Station(std::string name, Body b, double altitude_m);

    const std::string& name() const { return name_; }
    Status add_module(ModuleKind k);
    const std::vector<ModuleKind>& modules() const { return modules_; }
    double mass_t() const;
    double drag_area_m2() const;
    double power_kw() const;
    int crew_capacity() const;
    int ports() const;
    double altitude() const { return altitude_m_; }
    double period_min() const;

    // kenetlenme
    Result<int> dock(const std::string& vehicle, double mass_t);
    Status undock(const std::string& vehicle);
    const std::vector<DockedVehicle>& docked() const { return docked_; }

    // mürettebat ve sarf malzemesi
    Status set_crew(int n);
    int crew() const { return crew_; }
    void resupply(double o2_kg, double water_kg, double food_kg, double propellant_kg);
    double o2() const { return o2_kg_; }
    double water() const { return water_kg_; }
    double food() const { return food_kg_; }
    double propellant() const { return prop_kg_; }
    double days_of_supplies() const;

    // zaman: gün; güneş etkinliği (0.5..2)
    TickReport advance_days(double days, double solar_activity = 1.0);
    // yeniden itki: hedef irtifaya delta-v ve yakıt (Isp, s) — yeterliyse uygular
    struct Reboost { double dv_ms, propellant_kg; bool done; std::string note; };
    Reboost reboost(double target_alt_m, double isp_s = 300.0, bool apply = true);
    bool deorbited() const { return deorbited_; }

    json::Value to_json() const;
    static Result<Station> from_json(const json::Value& v);

private:
    std::string name_;
    Body body_;
    double altitude_m_;
    std::vector<ModuleKind> modules_;
    std::vector<DockedVehicle> docked_;
    int crew_ = 0;
    double o2_kg_ = 0, water_kg_ = 0, food_kg_ = 0, prop_kg_ = 0;
    bool deorbited_ = false;
};

// ISS benzeri referans istasyon (testler ve senaryolar)
Station iss_like();

}  // namespace kozmo::station

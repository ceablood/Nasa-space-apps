// KozmoCore — GARE: KOZMOGENİS çalışma zamanı ve entegrasyon katmanı (V30 §2).
// Unreal'den bağımsızdır; UE5'te UKozmoSubsystem tarafından sürülür (FTSTicker -> Runtime::frame).
//
//   Module Registry + Dependency Manager   modüller adla kaydolur, bağımlılık sırasına göre başlatılır (döngü tespiti)
//   Runtime Scheduler                      sabit adımlı simülasyon (birikimli), değişken adımlı güncelleme,
//                                          zaman hızlandırma, duraklatma, adım başına üst sınır (spiral-of-death koruması)
//   Event Queue                            ertelenmiş, öncelikli olaylar (kare sonunda dağıtılır)
//   Service Locator                        tür bazlı servis kaydı (RTTI'sız)
//   Configuration + Feature Flags          anahtar=değer ayarları (ini benzeri metinden), çalışma anı bayrakları
//   Diagnostics                            modül başına süre ölçümü, kare istatistikleri
#pragma once

#include <chrono>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::gare {

// ------------------------------------------------------------------------ modül arayüzü
class Runtime;

class Module {
public:
    virtual ~Module() = default;
    virtual std::string name() const = 0;
    virtual std::vector<std::string> dependencies() const { return {}; }
    virtual Status init(Runtime&) { return ok_status(); }
    virtual void fixed_update(Runtime&, double /*dt_sim_s*/) {}          // sabit adım (fizik, simülasyon)
    virtual void update(Runtime&, double /*dt_real_s*/) {}               // değişken adım (arayüz, kamera)
    virtual void shutdown(Runtime&) {}
};

// ------------------------------------------------------------------------ ayarlar
class Config {
public:
    Status parse(const std::string& text);                // "[bölüm]" + "anahtar = değer", ';' / '#' yorum
    void set(const std::string& key, const std::string& value) { values_[key] = value; }
    bool has(const std::string& key) const { return values_.count(key) > 0; }
    std::string get(const std::string& key, const std::string& def = "") const;
    double get_number(const std::string& key, double def) const;
    bool get_bool(const std::string& key, bool def) const;
    const std::map<std::string, std::string>& values() const { return values_; }

private:
    std::map<std::string, std::string> values_;          // "bölüm.anahtar"
};

// ------------------------------------------------------------------------ servis bulucu
class Services {
public:
    template <typename T>
    void provide(std::shared_ptr<T> s) { map_[type_id<T>()] = std::move(s); }
    template <typename T>
    T* get() const {
        auto it = map_.find(type_id<T>());
        return it == map_.end() ? nullptr : static_cast<T*>(it->second.get());
    }
    template <typename T>
    bool has() const { return map_.count(type_id<T>()) > 0; }

private:
    std::map<TypeId, std::shared_ptr<void>> map_;
};

// ------------------------------------------------------------------------ olay kuyruğu
class EventQueue {
public:
    // ertelenmiş iş: yüksek öncelik önce, eşitlikte sıraya göre
    void post(std::function<void()> fn, int priority = 0);
    std::size_t pending() const { return items_.size(); }
    std::size_t dispatch(std::size_t max_items = 100000);   // dağıtılan sayıyı döner; dağıtım sırasında eklenenler sonraki kareye

private:
    struct Item {
        int priority;
        std::uint64_t seq;
        std::function<void()> fn;
    };
    std::vector<Item> items_;
    std::uint64_t seq_ = 0;
};

// ------------------------------------------------------------------------ tanılama
struct ModuleTiming {
    double total_ms = 0;
    double last_ms = 0;
    std::uint64_t calls = 0;
};

struct FrameStats {
    std::uint64_t frames = 0;
    std::uint64_t fixed_steps = 0;
    std::uint64_t dropped_sim_s = 0;      // üst sınır yüzünden atılan simülasyon süresi (tamsayı saniye)
    double sim_time_s = 0;
};

// ------------------------------------------------------------------------ çalışma zamanı
class Runtime {
public:
    Runtime();

    // modül kaydı (init'ten önce)
    Status add(std::unique_ptr<Module> m);
    // bağımlılık sırasına göre başlat; eksik bağımlılık / döngü / init hatası açıkça raporlanır
    Status init();
    void shutdown();
    bool running() const { return running_; }
    std::vector<std::string> init_order() const;
    Module* module(const std::string& name) const;

    // zamanlama
    void set_fixed_step(double seconds) { fixed_step_ = seconds > 0 ? seconds : fixed_step_; }
    double fixed_step() const { return fixed_step_; }
    void set_time_scale(double s) { time_scale_ = s < 0 ? 0 : s; }      // sim saniye / gerçek saniye
    double time_scale() const { return time_scale_; }
    void set_paused(bool p) { paused_ = p; }
    bool paused() const { return paused_; }
    void set_max_steps_per_frame(int n) { max_steps_ = n > 0 ? n : 1; }
    double sim_time() const { return stats_.sim_time_s; }
    double interpolation_alpha() const { return accumulator_ / fixed_step_; }

    // bir kare: real_dt gerçek saniye geçti
    void frame(double real_dt);

    // altyapı
    EventBus& bus() { return bus_; }
    EventQueue& queue() { return queue_; }
    Services& services() { return services_; }
    Config& config() { return config_; }
    bool flag(const std::string& name) const;
    void set_flag(const std::string& name, bool on) { flags_[name] = on; }

    const FrameStats& stats() const { return stats_; }
    const std::map<std::string, ModuleTiming>& timings() const { return timings_; }
    std::string diagnostics() const;          // insan okunur rapor (geliştirici konsolu)

private:
    template <typename F>
    void timed(Module& m, F&& fn);

    std::vector<std::unique_ptr<Module>> modules_;
    std::vector<Module*> order_;
    bool running_ = false;
    double fixed_step_ = 1.0 / 60.0;
    double time_scale_ = 1.0;
    bool paused_ = false;
    int max_steps_ = 8;
    double accumulator_ = 0.0;
    EventBus bus_;
    EventQueue queue_;
    Services services_;
    Config config_;
    std::map<std::string, bool> flags_;
    FrameStats stats_;
    std::map<std::string, ModuleTiming> timings_;
};

// Olaylar
struct ModuleInitFailed { std::string module, reason; };

}  // namespace kozmo::gare

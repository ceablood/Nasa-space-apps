// KozmoCore — NOVA AI çevrimdışı çekirdeği (V30 §12).
//
//   * Türkçe komut ayrıştırma ve niyet tanıma (anahtar sözcük + varlık çıkarımı: gezegen, teknoloji, sayı)
//   * Bağlam: oyun durumu (görevler, koloniler, araştırma, bakiye) doğrudan Game'den okunur
//   * Bilgi tabanı: NASA verisi KAYNAĞIYLA sunulur; NOVA yanıtı bilimsel gerçek olarak işaretlenmez
//   * Tavsiye: roket analizi (prop::analyze), fırlatma penceresi, koloni tehlikeleri, araştırma önerisi
//   * Güvenlik (§12.3): kaynak harcayan her eylem önce "bekleyen eylem" olur; ancak oyuncu açıkça onaylarsa
//     uygulanır. Kayıt dosyalarına dokunmaz. Çevrimiçi model isteğe bağlı bir arayüzdür; anahtar oyuna gömülmez,
//     bağlantı yoksa çevrimdışı motor yanıt verir.
#pragma once

#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "kozmo/game.hpp"

namespace kozmo::world {
class Expedition;
}

namespace kozmo::nova {

enum class Intent {
    Unknown, Help, Status, PlanetInfo, LaunchWindow, RocketAdvice, ColonyAdvice, ResearchAdvice,
    StartResearch, LaunchColonyKit, Confirm, Cancel, Economy,
    VehicleStatus, PlanetRisk, ProductionDiagnosis, Evacuate,     // V41: sefer (araç/gezegen/koloni) bağlamı
    DamageReport, AssignTask, BuildModule, FoundColony
};
const char* intent_name(Intent i);

struct Parsed {
    Intent intent = Intent::Unknown;
    std::string planet;        // "mars", "moon" ...
    std::string tech;          // araştırma anahtarı
    double number = 0;         // komuttaki ilk sayı (ör. yük tonu)
    int job = -1;              // colony::Job (görev verme)
    int module = -1;           // colony::ModuleType (inşaat)
    bool has_number = false;
};

// Türkçe metni ayrıştırır (büyük/küçük harf ve Türkçe karakterlere duyarsız)
Parsed parse(const std::string& text);

struct PendingAction {
    int id;
    std::string description;      // oyuncuya gösterilecek açıklama + maliyet
    std::function<std::string()> execute;
};

struct Reply {
    std::string text;
    std::vector<std::string> sources;          // bilimsel/veri kaynakları
    std::optional<int> pending_action;         // onay bekleyen eylem kimliği
    bool from_online_model = false;
};

// İsteğe bağlı çevrimiçi model bağlayıcısı (ör. kullanıcının kendi API'si). Oyun bu arayüzü yalnızca
// kullanıcı ayarlarda açıkça etkinleştirirse kullanır; anahtar oyun dosyasında saklanmaz.
class OnlineConnector {
public:
    virtual ~OnlineConnector() = default;
    virtual bool available() const = 0;
    // Başarısızsa boş döner (çevrimdışı motora düşülür)
    virtual std::optional<std::string> complete(const std::string& prompt, const std::string& context) = 0;
};

class Nova {
public:
    explicit Nova(Game& game) : game_(game) {}
    Reply ask(const std::string& text);
    void set_online(std::shared_ptr<OnlineConnector> c) { online_ = std::move(c); }
    // V41: etkin sefere bağlan (araç durumu, gezegen riski, üretim teşhisi, tahliye). nullptr: bağlantıyı kes.
    void attach(world::Expedition* e) { expedition_ = e; }
    const std::vector<PendingAction>& pending() const { return pending_; }
    // proaktif uyarılar (her oyun günü UI tarafından sorulabilir)
    std::vector<std::string> warnings() const;
    std::string context_summary() const;

private:
    Reply status() const;
    Reply planet_info(const std::string& key) const;
    Reply launch_window(const std::string& key) const;
    Reply rocket_advice(const std::string& key, double payload) const;
    Reply colony_advice() const;
    Reply research_advice() const;
    Reply vehicle_status() const;
    Reply planet_risk() const;
    Reply production_diagnosis() const;
    Reply evacuate();
    Reply assign_task(int job);
    Reply build_module(int module);
    Reply found_colony();
    Reply propose(const std::string& description, std::function<std::string()> fn);
    Reply confirm();
    Reply cancel();

    Game& game_;
    std::shared_ptr<OnlineConnector> online_;
    world::Expedition* expedition_ = nullptr;
    std::vector<PendingAction> pending_;
    int next_id_ = 1;
};

}  // namespace kozmo::nova

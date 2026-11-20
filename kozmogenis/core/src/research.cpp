#include "kozmo/research.hpp"

#include <algorithm>

namespace kozmo::research {

const std::vector<Tech>& techs() {
    static const std::vector<Tech> t = {
        {"cryo", "Kriyojenik itki", "Sıvı hidrojen/LOX üst kademe motoru (RL10 sınıfı).", 40, {}, false},
        {"methalox", "Metan/LOX tam akış", "Yüksek basınçlı tam akışlı kademeli yanma motorları.", 90, {"cryo"}, false},
        {"isru", "Yerinde kaynak kullanımı", "Sabatier reaktörüyle Mars atmosferinden yakıt üretimi.", 120, {"methalox"}, false},
        {"fission", "Yüzey fisyon reaktörü", "Kilopower türü küçük fisyon reaktörü; gece/toz fırtınasından bağımsız güç.", 150, {}, false},
        {"ion", "Elektrikli itki", "Xenon iyon iticiler: çok yüksek Isp, çok düşük itki (kargo).", 110, {"fission"}, false},
        {"nuclear", "Nükleer termal itki", "NERVA sınıfı nükleer termal roket (~840 s Isp).", 260, {"fission", "cryo"}, false},
        {"closed_loop", "Kapalı döngü yaşam desteği", "Su ve oksijen geri kazanımını artırır.", 140, {}, false},
        {"he3_fusion", "He-3 füzyon itkisi", "Spekülatif: Helyum-3 füzyon roketi. Gerçekte henüz yoktur.", 900, {"nuclear", "isru"}, true},
    };
    return t;
}

Result<const Tech*> find(const std::string& key) {
    for (const auto& t : techs())
        if (t.key == key) return &t;
    return make_error(ErrorCode::NotFound, "Bilinmeyen teknoloji: " + key);
}

bool Tree::unlocked(const std::string& key) const { return std::find(done_.begin(), done_.end(), key) != done_.end(); }

Status Tree::start(const std::string& key) {
    auto t = find(key);
    if (!t) return t.error();
    if (unlocked(key)) return make_error(ErrorCode::InvalidArgument, t.value()->name_tr + " zaten araştırıldı");
    for (const auto& r : t.value()->requires_)
        if (!unlocked(r)) return make_error(ErrorCode::Locked, t.value()->name_tr + " için önce gerekli: " + r);
    if (active_ != key) {
        active_ = key;
        spent_ = 0.0;
        progress_ = 0.0;
    }
    return ok_status();
}

bool Tree::add_points(double rp, EventBus* bus) {
    if (active_.empty() || rp <= 0) return false;
    auto t = find(active_);
    if (!t) return false;
    spent_ += rp;
    progress_ = std::min(1.0, spent_ / t.value()->cost_rp);
    if (progress_ < 1.0) return false;
    done_.push_back(active_);
    KOZMO_LOG(Info, "research", "Araştırma tamamlandı: " + t.value()->name_tr);
    if (bus) bus->publish(ResearchCompleted{active_});
    active_.clear();
    spent_ = progress_ = 0.0;
    return true;
}

json::Value Tree::to_json() const {
    json::Value v = json::Value::object();
    json::Value d = json::Value::array();
    for (const auto& k : done_) d.push(k);
    v.set("done", d);
    v.set("active", active_);
    v.set("spent", spent_);
    return v;
}

Status Tree::from_json(const json::Value& v) {
    done_.clear();
    for (const auto& k : v["done"].as_array()) {
        if (!find(k.as_string())) return make_error(ErrorCode::Parse, "Kayıtta bilinmeyen teknoloji: " + k.as_string());
        done_.push_back(k.as_string());
    }
    active_ = v["active"].as_string();
    spent_ = v["spent"].as_number();
    if (!active_.empty()) {
        auto t = find(active_);
        if (!t) return make_error(ErrorCode::Parse, "Kayıtta bilinmeyen aktif araştırma");
        progress_ = std::min(1.0, spent_ / t.value()->cost_rp);
    }
    return ok_status();
}

}  // namespace kozmo::research

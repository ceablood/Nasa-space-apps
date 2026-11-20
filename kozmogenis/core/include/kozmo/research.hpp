// KozmoCore — araştırma ağacı: önkoşullar, puan maliyeti, açtığı teknolojiler.
#pragma once

#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::research {

struct Tech {
    std::string key;
    std::string name_tr;
    std::string description_tr;
    double cost_rp;
    std::vector<std::string> requires_;
    bool fictional;            // true = kurgusal/spekülatif teknoloji (şema kuralı 16)
};

const std::vector<Tech>& techs();
Result<const Tech*> find(const std::string& key);

struct ResearchCompleted { std::string key; };

class Tree {
public:
    bool unlocked(const std::string& key) const;
    const std::vector<std::string>& unlocked_list() const { return done_; }
    Status start(const std::string& key);
    const std::string& active() const { return active_; }
    double progress() const { return progress_; }           // 0..1
    // puan ekle; tamamlanırsa olayı yayınlar ve true döner
    bool add_points(double rp, EventBus* bus);
    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<std::string> done_;
    std::string active_;
    double spent_ = 0.0;
    double progress_ = 0.0;
};

}  // namespace kozmo::research

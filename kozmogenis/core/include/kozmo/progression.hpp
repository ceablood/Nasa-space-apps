// KozmoCore — ilerleme: başarımlar, adım adım eğitim (ilk oynayış rehberi) ve haber akışı (V30 §19 UI/UX).
// Koşullar oyunun gerçek durumundan (Snapshot) değerlendirilir; metinler ve eşikler OYUN TASARIMIDIR.
#pragma once

#include <set>
#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::progress {

struct Snapshot {
    int colonies = 0, population = 0, missions = 0, research_done = 0, quests_done = 0, satellites = 0, astronauts = 0;
    bool landed_moon = false, landed_mars = false, reached_orbit = false, docked = false, survived_storm = false;
    bool max_base = false, deflection_planned = false, walked_on_surface = false, built_module = false;
    double credits = 0, day = 0;
};

struct Achievement {
    std::string key, title, description;
    bool secret = false;
};
const std::vector<Achievement>& achievements();

class Tracker {
public:
    // yeni açılan başarımların anahtarları
    std::vector<std::string> update(const Snapshot& s);
    bool unlocked(const std::string& key) const { return done_.count(key) > 0; }
    int count() const { return static_cast<int>(done_.size()); }
    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::set<std::string> done_;
};

// Eğitim: sıralı adımlar; olay adı adımı ilerletir ("sit", "descent", "landed", "exit", "enter", "use", "talk", "nova", "sample")
class Tutorial {
public:
    Tutorial();
    std::string hint() const;           // şu anki adımın yönergesi ("" bitti)
    int step() const { return step_; }
    int steps() const { return static_cast<int>(events_.size()); }
    bool finished() const { return step_ >= steps() || skipped_; }
    bool on(const std::string& event);  // doğru olay gelirse ilerler
    void skip() { skipped_ = true; }
    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<std::string> events_, hints_;
    int step_ = 0;
    bool skipped_ = false;
};

struct NewsItem {
    double day;
    std::string headline, body, source;
    bool real;                          // gerçek uzay tarihi notu mu
};

class News {
public:
    // olay -> haber (oyun içi); bazı olaylarda gerçek tarihî karşılık eklenir
    void report(const std::string& event, double day, const std::string& detail = "");
    const std::vector<NewsItem>& items() const { return items_; }
    std::vector<NewsItem> latest(std::size_t n) const;
    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<NewsItem> items_;
};

}  // namespace kozmo::progress

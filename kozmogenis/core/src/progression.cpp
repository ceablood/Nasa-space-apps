#include "kozmo/progression.hpp"

#include <algorithm>

namespace kozmo::progress {

const std::vector<Achievement>& achievements() {
    static const std::vector<Achievement> a = {
        {"first_orbit", "Yörüngeye merhaba", "Bir aracı yüzeyden yörüngeye çıkar"},
        {"eagle", "Kartal kondu", "Ay'a yumuşak iniş yap"},
        {"red_planet", "Kızıl gezegen", "Mars'a iniş yap"},
        {"first_steps", "Bir küçük adım", "Başka bir dünyanın yüzeyinde yürü"},
        {"docking", "Kenetlenme", "Bir istasyona kenetlen"},
        {"builder", "Usta", "Kolonide bir modül inşa ettir"},
        {"colony_1", "Yuva", "İlk koloniyi kur"},
        {"colony_3", "Gezegenler arası", "Üç koloni kur"},
        {"pop_50", "Kasaba", "Toplam nüfusu 50'ye çıkar"},
        {"storm", "Fırtına yolcusu", "Bir toz fırtınasını kayıpsız atlat"},
        {"helper", "Herkesin dostu", "5 görev tamamla"},
        {"research_5", "Bilim insanı", "5 araştırma tamamla"},
        {"constellation", "Gökyüzü ağı", "24 uydu yörüngede tut"},
        {"max_base", "Tam donanım", "Tüm üs tesislerini en yüksek seviyeye çıkar"},
        {"planetary_defense", "Gezegen savunucusu", "Tehlikeli bir asteroit için saptırma planı yap"},
        {"millionaire", "Milyoner ajans", "Bakiyeyi 10 milyon krediye çıkar", true},
    };
    return a;
}

std::vector<std::string> Tracker::update(const Snapshot& s) {
    std::vector<std::string> out;
    auto give = [&](const char* k, bool cond) {
        if (cond && done_.insert(k).second) out.push_back(k);
    };
    give("first_orbit", s.reached_orbit);
    give("eagle", s.landed_moon);
    give("red_planet", s.landed_mars);
    give("first_steps", s.walked_on_surface);
    give("docking", s.docked);
    give("builder", s.built_module);
    give("colony_1", s.colonies >= 1);
    give("colony_3", s.colonies >= 3);
    give("pop_50", s.population >= 50);
    give("storm", s.survived_storm);
    give("helper", s.quests_done >= 5);
    give("research_5", s.research_done >= 5);
    give("constellation", s.satellites >= 24);
    give("max_base", s.max_base);
    give("planetary_defense", s.deflection_planned);
    give("millionaire", s.credits >= 1e7);
    return out;
}

json::Value Tracker::to_json() const {
    json::Value a = json::Value::array();
    for (const auto& k : done_) a.push(k);
    json::Value v = json::Value::object();
    v.set("done", a);
    return v;
}

Status Tracker::from_json(const json::Value& v) {
    done_.clear();
    for (const auto& k : v["done"].as_array()) {
        const std::string s = k.as_string();
        if (std::none_of(achievements().begin(), achievements().end(), [&](const Achievement& a) { return a.key == s; }))
            return make_error(ErrorCode::Parse, "Bilinmeyen başarım: " + s);
        done_.insert(s);
    }
    return ok_status();
}

Tutorial::Tutorial() {
    events_ = {"sit", "descent", "landed", "exit", "enter", "use", "talk", "nova", "sample"};
    hints_ = {"Kokpitteki koltuğa otur (E).",
              "İnişi başlat (B), motorları ateşle (F) ve iniş desteğini aç (L).",
              "İniş desteği alçalmayı yönetiyor. İRTİFA ve HIZ göstergelerini izle.",
              "Koltuktan kalk (C) ve araçtan çık (X). Giysi oksijenini HUD'dan takip et.",
              "Koloniye yürü ve yönetim merkezinin kapısında E'ye bas.",
              "Nüfus ekranı konsolunu kullan (E).",
              "Bir koloniye bakıp E ile konuş; 1-5 tuşlarıyla konu seç.",
              "NOVA'ya sor: 'koloninin durumu nasıl?'",
              "Dışarıda G ile bir numune topla ve laboratuvara götür."};
}

std::string Tutorial::hint() const { return finished() ? std::string() : hints_[static_cast<std::size_t>(step_)]; }

bool Tutorial::on(const std::string& e) {
    if (finished() || e != events_[static_cast<std::size_t>(step_)]) return false;
    ++step_;
    return true;
}

json::Value Tutorial::to_json() const {
    json::Value v = json::Value::object();
    v.set("step", step_);
    v.set("skipped", skipped_);
    return v;
}

Status Tutorial::from_json(const json::Value& v) {
    step_ = std::clamp(v["step"].as_int(), 0, steps());
    skipped_ = v["skipped"].as_bool();
    return ok_status();
}

void News::report(const std::string& e, double day, const std::string& detail) {
    // olay adı -> başlık; gerçek tarihle bağ kurulabilenlerde ikinci, "gerçek" bir not eklenir
    struct T { const char* event; const char* headline; const char* real; const char* source; };
    static const T t[] = {
        {"landed_moon", "Ajansımızın aracı Ay'a yumuşak iniş yaptı", "Gerçek tarih: Apollo 11, 20 Temmuz 1969 — insanlığın Ay'a ilk inişi", "NASA"},
        {"landed_mars", "Mars'ta yeni bir dönem: iniş başarılı", "Gerçek tarih: Viking 1, 20 Temmuz 1976 — Mars yüzeyinden ilk başarılı görevler", "NASA"},
        {"colony_founded", "Yeni koloni kuruldu", "Gerçek: ISS 2 Kasım 2000'den beri kesintisiz insanlı", "NASA"},
        {"docked", "İstasyona kenetlenme tamamlandı", "Gerçek tarih: Gemini 8, 16 Mart 1966 — ilk uzay kenetlenmesi", "NASA"},
        {"dust_storm", "Kolonide toz fırtınası alarmı", "Gerçek: 2018 küresel toz fırtınası Opportunity gezginini sonlandırdı", "NASA/JPL"},
        {"deflection", "Gezegen savunma planı onaylandı", "Gerçek tarih: DART, 26 Eylül 2022 — Dimorphos'un yörüngesi değiştirildi", "NASA/JHU APL"},
        {"orbit", "Yörüngeye başarılı yükseliş", "Gerçek tarih: Sputnik 1, 4 Ekim 1957 — ilk yapay uydu", "Tarih"},
    };
    for (const auto& x : t)
        if (e == x.event) {
            items_.push_back({day, x.headline, detail, "KOZMOGENİS Ajans Bülteni", false});
            items_.push_back({day, "Tarihten", x.real, x.source, true});
            return;
        }
    items_.push_back({day, e, detail, "KOZMOGENİS Ajans Bülteni", false});
    if (items_.size() > 300) items_.erase(items_.begin(), items_.begin() + 100);
}

std::vector<NewsItem> News::latest(std::size_t n) const {
    std::vector<NewsItem> out;
    for (std::size_t i = items_.size() > n ? items_.size() - n : 0; i < items_.size(); ++i) out.push_back(items_[i]);
    return out;
}

json::Value News::to_json() const {
    json::Value a = json::Value::array();
    for (const auto& n : items_) {
        json::Value o = json::Value::object();
        o.set("day", n.day);
        o.set("h", n.headline);
        o.set("b", n.body);
        o.set("s", n.source);
        o.set("real", n.real);
        a.push(o);
    }
    json::Value v = json::Value::object();
    v.set("items", a);
    return v;
}

Status News::from_json(const json::Value& v) {
    items_.clear();
    for (const auto& o : v["items"].as_array()) items_.push_back({o["day"].as_number(), o["h"].as_string(), o["b"].as_string(), o["s"].as_string(), o["real"].as_bool()});
    return ok_status();
}

}  // namespace kozmo::progress

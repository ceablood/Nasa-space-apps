#include "kozmo/nova.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace kozmo::nova {

const char* intent_name(Intent i) {
    switch (i) {
        case Intent::Unknown: return "Bilinmiyor";
        case Intent::Help: return "Yardım";
        case Intent::Status: return "Durum";
        case Intent::PlanetInfo: return "Gezegen bilgisi";
        case Intent::LaunchWindow: return "Fırlatma penceresi";
        case Intent::RocketAdvice: return "Roket tavsiyesi";
        case Intent::ColonyAdvice: return "Koloni tavsiyesi";
        case Intent::ResearchAdvice: return "Araştırma tavsiyesi";
        case Intent::StartResearch: return "Araştırma başlat";
        case Intent::LaunchColonyKit: return "Koloni kiti fırlat";
        case Intent::Confirm: return "Onay";
        case Intent::Cancel: return "İptal";
        case Intent::Economy: return "Ekonomi";
    }
    return "?";
}

namespace {
// Türkçe karakterleri ASCII'ye indirger ve küçük harfe çevirir (UTF-8)
std::string fold(const std::string& in) {
    std::string out;
    for (std::size_t i = 0; i < in.size(); ++i) {
        const unsigned char c = static_cast<unsigned char>(in[i]);
        if (c < 0x80) {
            out += static_cast<char>(c >= 'A' && c <= 'Z' ? c + 32 : c);
            continue;
        }
        const unsigned char d = i + 1 < in.size() ? static_cast<unsigned char>(in[i + 1]) : 0;
        char r = 0;
        if (c == 0xC3) {
            if (d == 0xA7 || d == 0x87) r = 'c';        // ç Ç
            else if (d == 0xB6 || d == 0x96) r = 'o';   // ö Ö
            else if (d == 0xBC || d == 0x9C) r = 'u';   // ü Ü
            else if (d == 0xA2 || d == 0xA4) r = 'a';   // â ä
            else if (d == 0xAE) r = 'i';                // î
        } else if (c == 0xC4) {
            if (d == 0x9F || d == 0x9E) r = 'g';        // ğ Ğ
            else if (d == 0xB1 || d == 0xB0) r = 'i';   // ı İ
        } else if (c == 0xC5) {
            if (d == 0x9F || d == 0x9E) r = 's';        // ş Ş
        }
        if (r) {
            out += r;
            ++i;
        } else {
            out += ' ';                                 // bilinmeyen çok baytlı karakter: ayırıcı
            while (i + 1 < in.size() && (static_cast<unsigned char>(in[i + 1]) & 0xC0) == 0x80) ++i;
        }
    }
    return out;
}

std::vector<std::string> words(const std::string& folded) {
    std::vector<std::string> w;
    std::string cur;
    for (char c : folded) {
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' || c == ',') cur += c;
        else if (!cur.empty()) { w.push_back(cur); cur.clear(); }
    }
    if (!cur.empty()) w.push_back(cur);
    return w;
}

bool starts(const std::string& w, const char* p) { return w.rfind(p, 0) == 0; }

bool any(const std::vector<std::string>& w, std::initializer_list<const char*> prefixes) {
    for (const auto& x : w)
        for (const char* p : prefixes)
            if (starts(x, p)) return true;
    return false;
}

std::string planet_of(const std::vector<std::string>& w) {
    static const std::pair<const char*, const char*> names[] = {
        {"merkur", "mercury"}, {"venus", "venus"}, {"dunya", "earth"}, {"mars", "mars"}, {"jupiter", "jupiter"},
        {"saturn", "saturn"}, {"uranus", "uranus"}, {"neptun", "neptune"}, {"pluton", "pluto"}, {"leo", "leo"},
    };
    for (const auto& x : w) {
        for (const auto& [tr, key] : names)
            if (starts(x, tr)) return key;
        // "ay" kısa: yalnızca tam sözcük ya da ek almış hâli (aya, ayda, ayin, aydaki) — "ayar" değil
        if (x == "ay" || x == "aya" || x == "ayda" || x == "ayin" || x == "aydaki" || x == "aydan") return "moon";
    }
    return "";
}

std::string tech_of(const std::string& folded, const std::vector<std::string>& w) {
    if (any(w, {"fisyon", "reaktor"})) return "fission";
    if (any(w, {"isru", "sabatier"}) || folded.find("yakit uretim") != std::string::npos) return "isru";
    if (any(w, {"iyon", "elektrikli"})) return "ion";
    if (any(w, {"fuzyon", "he3", "helyum"})) return "he3_fusion";
    if (any(w, {"nukleer", "nerva"})) return "nuclear";
    if (any(w, {"kriyojenik", "hidrojen"})) return "cryo";
    if (any(w, {"metan", "raptor"})) return "methalox";
    if (folded.find("kapali dongu") != std::string::npos || any(w, {"geri donusum"})) return "closed_loop";
    return "";
}

std::string fmt(const char* f, double a) {
    char b[128];
    std::snprintf(b, sizeof b, f, a);
    return b;
}
}  // namespace

Parsed parse(const std::string& text) {
    Parsed p;
    const std::string f = fold(text);
    const auto w = words(f);
    p.planet = planet_of(w);
    p.tech = tech_of(f, w);
    for (const auto& x : w) {
        std::string n = x;
        std::replace(n.begin(), n.end(), ',', '.');
        char* end = nullptr;
        const double v = std::strtod(n.c_str(), &end);
        if (end && end != n.c_str() && *end == '\0') {
            p.number = v;
            p.has_number = true;
            break;
        }
    }
    if (any(w, {"onayla", "onayliyorum", "evet"}) || f == "onay") p.intent = Intent::Confirm;
    else if (any(w, {"iptal", "vazgec", "hayir"})) p.intent = Intent::Cancel;
    else if (any(w, {"yardim", "komut"}) || f.find("neler yapabilir") != std::string::npos) p.intent = Intent::Help;
    else if (any(w, {"firlat", "gonder"}) && any(w, {"koloni", "kit"})) p.intent = Intent::LaunchColonyKit;
    else if (!p.tech.empty() && any(w, {"arastir", "baslat"})) p.intent = Intent::StartResearch;
    else if (any(w, {"pencere"})) p.intent = Intent::LaunchWindow;
    else if (any(w, {"roket", "tasarim", "delta", "itki"}) || f.find("yakit hesab") != std::string::npos) p.intent = Intent::RocketAdvice;
    else if (any(w, {"koloni", "oksijen", "enerji", "gida", "kolonist"})) p.intent = Intent::ColonyAdvice;
    else if (any(w, {"arastirma", "teknoloji"})) p.intent = Intent::ResearchAdvice;
    else if (any(w, {"fiyat", "piyasa", "ekonomi", "bakiye", "para"})) p.intent = Intent::Economy;
    else if (any(w, {"durum", "ozet", "rapor"})) p.intent = Intent::Status;
    else if (!p.planet.empty()) p.intent = Intent::PlanetInfo;
    return p;
}

// ------------------------------------------------------------------------ yanıtlar
std::string Nova::context_summary() const {
    std::string s = "Gün " + fmt("%.1f", game_.day()) + ", bakiye " + fmt("%.0f", game_.wallet().balance()) + " kredi. ";
    s += "Araştırma: " + (game_.research().active().empty() ? std::string("yok") : game_.research().active()) + ". ";
    for (const auto& [id, c] : game_.colonies())
        s += id + ": nüfus " + std::to_string(c.population()) + ", moral " + fmt("%.2f", c.average_morale()) + ". ";
    int transit = 0;
    for (const auto& m : game_.missions()) transit += m.state == MissionState::InTransit;
    s += "Yoldaki görev: " + std::to_string(transit) + ".";
    return s;
}

Reply Nova::status() const { return {context_summary(), {}, std::nullopt, false}; }

Reply Nova::planet_info(const std::string& key) const {
    auto b = astro::find(key);
    if (!b) return {"Bu gök cismini tanımıyorum: " + key, {}, std::nullopt, false};
    const auto& x = *b.value();
    std::string t = x.name_tr + ": çap " + fmt("%.0f", x.diameter_km) + " km, yüzey yerçekimi " + fmt("%.1f", x.gravity_ms2) +
                    " m/s², kaçış hızı " + fmt("%.1f", x.escape_kms) + " km/s, ortalama sıcaklık " + fmt("%.0f", x.mean_temp_c) +
                    " °C, yörünge periyodu " + fmt("%.1f", x.period_days) + " gün, uydu sayısı " + std::to_string(x.moons) + ".";
    if (!x.has_surface()) t += " Katı yüzeyi yoktur; koloni ancak yörünge istasyonu olabilir.";
    else if (x.surface_pressure_bar > 10) t += " Yüzey basıncı " + fmt("%.0f", x.surface_pressure_bar) + " bar: iniş çok zorlu.";
    if (x.parent == "sun" && x.key != "earth") {
        const double flux = colony::solar_flux(x.distance_1e6km);
        t += " Güneş ışınımı ~" + fmt("%.0f", flux) + " W/m² (Dünya'nın %" + fmt("%.0f", flux / 13.61) + "'i).";
    }
    return {t, {astro::to_string(x.source), astro::kMoonsNote}, std::nullopt, false};
}

Reply Nova::launch_window(const std::string& key) const {
    if (key.empty()) return {"Hangi hedef için? Örnek: 'Mars penceresi ne zaman?'", {}, std::nullopt, false};
    if (key == "moon") return {"Ay'a fırlatma her gün mümkündür; Hohmann transferi yaklaşık 5 gün sürer.", {"Yörünge mekaniği (Hohmann)"}, std::nullopt, false};
    auto w = game_.window_to(key);
    if (!w) return {w.error().message, {}, std::nullopt, false};
    const auto& x = w.value();
    std::string t = "Şu anki faz açısı " + fmt("%.0f", x.current_phase_deg) + "°, Hohmann için gereken " + fmt("%.0f", x.required_phase_deg) +
                    "°. Sonraki pencere " + fmt("%.0f", x.days_until) + " gün sonra; pencereler " + fmt("%.0f", x.synodic_days) +
                    " günde bir tekrarlanır.";
    if (x.days_until <= Game::kWindowToleranceDays || x.synodic_days - x.days_until <= Game::kWindowToleranceDays)
        t += " Pencere ŞU AN açık.";
    return {t, {"Kepler / Hohmann transferi, sinodik periyot; NASA NSSDC yörünge verisi"}, std::nullopt, false};
}

Reply Nova::rocket_advice(const std::string& key, double payload) const {
    const std::string target = key.empty() ? "moon" : key;
    if (payload <= 0) payload = payload_mass_t(standard_colony_kit()) + 0.5;
    auto r = game_.evaluate(preset_heavy_rocket(target, payload, 0));
    if (!r) return {r.error().message, {}, std::nullopt, false};
    const auto& x = r.value();
    std::string t = "Ağır roketle " + target + " için " + fmt("%.1f", payload) + " t yük: delta-v " + fmt("%.2f", x.total_dv_ms / 1000) +
                    " / gereken " + fmt("%.2f", x.required_dv_ms / 1000) + " km/s, kalkış itki/ağırlık " + fmt("%.2f", x.liftoff_twr) +
                    ", başarı olasılığı %" + fmt("%.0f", x.success_p * 100) + ".";
    if (!x.feasible) {
        t += " Uygun değil: " + x.problems.front();
        auto light = preset_heavy_rocket(target, payload, 0);
        auto p = prop::min_upper_propellant(light, game_.research().unlocked_list());
        if (p) t += " Öneri: iniş kademesi yakıtını " + fmt("%.0f", p.value()) + " t'ye çıkar.";
        else t += " Bu yük için daha yüksek Isp'li motor (nükleer termal) ya da daha hafif yük gerekli.";
    } else if (x.margin_ms < 300) {
        t += " Delta-v payı düşük (" + fmt("%.0f", x.margin_ms) + " m/s); %5-10 yedek önerilir.";
    } else {
        t += " Tasarım uygun; pay " + fmt("%.0f", x.margin_ms) + " m/s.";
    }
    return {t, {"Tsiolkovsky roket denklemi", "Motor sınıfı değerleri: mühendislik yaklaşımı", "Risk modeli: oyun varsayımı"},
            std::nullopt, false};
}

std::vector<std::string> Nova::warnings() const {
    std::vector<std::string> w;
    for (const auto& [id, c] : game_.colonies()) {
        const int pop = c.population();
        if (pop == 0) continue;
        const double o2_days = c.resource("oxygen") / (colony::kO2PerPersonDay_t * pop);
        const double food_days = c.resource("food") / (colony::kFoodPerPersonDay_t * pop);
        bool electrolyzer = false, reactor = false;
        for (const auto& m : c.modules()) {
            electrolyzer |= m.type == colony::ModuleType::Electrolyzer;
            reactor |= m.type == colony::ModuleType::FissionReactor;
        }
        if (!electrolyzer && o2_days < 30) w.push_back(id + ": oksijen " + fmt("%.0f", o2_days) + " gün yeter ve üretim yok!");
        if (food_days < 10) w.push_back(id + ": gıda stoğu yaklaşık " + fmt("%.0f", food_days) + " günlük.");
        if (c.body() == "moon" && !reactor)
            w.push_back(id + ": Ay gecesi ~14 Dünya günü sürer; güneş paneliyle enerji kesintisi olur. Fisyon reaktörü önerilir.");
        if (c.average_morale() < 0.4) w.push_back(id + ": moral düşük (" + fmt("%.2f", c.average_morale()) + ").");
        if (c.housing() < pop) w.push_back(id + ": konut yetersiz (" + std::to_string(pop) + "/" + std::to_string(c.housing()) + ").");
        for (const auto& col : c.colonists())
            if (col.alive && col.dose_msv > env::kCareerLimitMsv * 0.8)
                w.push_back(id + ": " + col.name + " radyasyon dozu " + fmt("%.0f", col.dose_msv) + " mSv (NASA kariyer sınırı 600 mSv)" +
                            (col.dose_limit_reached ? " — çalışamaz." : "."));
        const double sf = game_.environment().solar_factor(c.body(), game_.day());
        if (sf < 0.9)
            w.push_back(id + ": toz fırtınası güneş enerjisini %" + fmt("%.0f", (1 - sf) * 100) + " düşürüyor.");
    }
    return w;
}

Reply Nova::colony_advice() const {
    if (game_.colonies().empty()) return {"Henüz koloni yok. 'Ay'a koloni kiti fırlat' diyebilirsin.", {}, std::nullopt, false};
    auto w = warnings();
    std::string t = w.empty() ? "Kolonilerde kritik sorun görünmüyor." : "Dikkat:";
    for (const auto& x : w) t += "\n- " + x;
    return {t, {"Yaşam desteği tüketimi: NASA referans değerleri mertebesi (mühendislik yaklaşımı)"}, std::nullopt, false};
}

Reply Nova::research_advice() const {
    const auto& tr = game_.research();
    auto open = [&](const std::string& k) {
        auto t = research::find(k);
        if (!t || tr.unlocked(k)) return false;
        for (const auto& r : t.value()->requires_)
            if (!tr.unlocked(r)) return false;
        return true;
    };
    std::string pick;
    for (const auto& [id, c] : game_.colonies()) {
        if (c.body() == "moon" && open("fission")) pick = "fission";
        if (c.body() == "mars" && open("isru")) pick = "isru";
    }
    if (pick.empty()) {
        double best = 1e18;
        for (const auto& t : research::techs())
            if (open(t.key) && !t.fictional && t.cost_rp < best) {
                best = t.cost_rp;
                pick = t.key;
            }
    }
    if (pick.empty()) return {"Açılabilecek yeni araştırma kalmadı.", {}, std::nullopt, false};
    auto t = research::find(pick).value();
    return {"Önerim: " + t->name_tr + " (" + fmt("%.0f", t->cost_rp) + " puan). " + t->description_tr +
                " Başlatmak için '" + t->name_tr + " araştır' de.",
            {}, std::nullopt, false};
}

Reply Nova::propose(const std::string& description, std::function<std::string()> fn) {
    pending_.push_back({next_id_, description, std::move(fn)});
    Reply r{description + "\nOnaylıyor musun? ('onayla' ya da 'iptal')", {}, next_id_, false};
    ++next_id_;
    return r;
}

Reply Nova::confirm() {
    if (pending_.empty()) return {"Onay bekleyen bir işlem yok.", {}, std::nullopt, false};
    PendingAction a = std::move(pending_.back());
    pending_.pop_back();
    return {a.execute(), {}, std::nullopt, false};
}

Reply Nova::cancel() {
    if (pending_.empty()) return {"İptal edilecek işlem yok.", {}, std::nullopt, false};
    pending_.pop_back();
    return {"İşlem iptal edildi; hiçbir kaynak harcanmadı.", {}, std::nullopt, false};
}

Reply Nova::ask(const std::string& text) {
    const Parsed p = parse(text);
    switch (p.intent) {
        case Intent::Help:
            return {"Sorabileceklerin: durum, '<gezegen> hakkında bilgi', '<gezegen> penceresi', 'Mars roketi 30 ton', "
                    "koloni durumu, ne araştırmalıyım, '<teknoloji> araştır', '<gezegen>'a koloni kiti fırlat', piyasa fiyatları. "
                    "Kaynak harcayan işlemler senin onayın olmadan yapılmaz.",
                    {}, std::nullopt, false};
        case Intent::Status: return status();
        case Intent::PlanetInfo: return planet_info(p.planet);
        case Intent::LaunchWindow: return launch_window(p.planet);
        case Intent::RocketAdvice: return rocket_advice(p.planet, p.has_number ? p.number : 0);
        case Intent::ColonyAdvice: return colony_advice();
        case Intent::ResearchAdvice: return research_advice();
        case Intent::Economy: {
            std::string t = "Dünya piyasası:";
            if (auto* m = game_.market("earth"))
                for (const auto& [k, it] : m->items()) {
                    auto pr = m->price(k);
                    if (pr) t += "\n- " + k + ": " + fmt("%.0f", pr.value()) + " kredi";
                }
            return {t, {"Fiyat modeli: oyun varsayımı"}, std::nullopt, false};
        }
        case Intent::StartResearch: {
            auto t = research::find(p.tech);
            if (!t) return {t.error().message, {}, std::nullopt, false};
            const std::string key = p.tech;
            std::string desc = t.value()->name_tr + " araştırması başlatılacak (" + fmt("%.0f", t.value()->cost_rp) + " puan).";
            if (!game_.research().active().empty() && game_.research().active() != key)
                desc += " Uyarı: devam eden '" + game_.research().active() + "' araştırmasının ilerlemesi sıfırlanır.";
            if (t.value()->fictional) desc += " Not: bu teknoloji kurgusaldır (gerçekte yoktur).";
            return propose(desc, [this, key] {
                auto st = game_.research().start(key);
                return st ? std::string("Araştırma başladı.") : st.error().message;
            });
        }
        case Intent::LaunchColonyKit: {
            const std::string target = p.planet.empty() ? "moon" : p.planet;
            const Payload kit = standard_colony_kit();
            const auto design = preset_heavy_rocket(target, payload_mass_t(kit) + 0.5, static_cast<int>(kit.crew.size()));
            auto r = game_.evaluate(design);
            if (!r) return {r.error().message, {}, std::nullopt, false};
            if (!r.value().feasible) return {"Bu görev uygun değil: " + r.value().problems.front(), {}, std::nullopt, false};
            const std::string desc = target + " hedefine 3 kişilik koloni kiti: maliyet " + fmt("%.0f", r.value().cost_mcr * 1000) +
                                     " kredi, başarı olasılığı %" + fmt("%.0f", r.value().success_p * 100) + ".";
            return propose(desc, [this, design, kit] {
                auto id = game_.launch(design, kit);
                if (!id) return "Fırlatılamadı: " + id.error().message;
                const auto& m = game_.missions().back();
                return m.state == MissionState::Lost ? std::string("Görev fırlatmada kaybedildi.")
                                                     : "Görev #" + std::to_string(m.id) + " yolda; varış " +
                                                           fmt("%.1f", m.arrive_day - m.depart_day) + " gün sonra.";
            });
        }
        case Intent::Confirm: return confirm();
        case Intent::Cancel: return cancel();
        case Intent::Unknown: break;
    }
    if (online_ && online_->available()) {
        auto ans = online_->complete(text, context_summary());
        if (ans) return {*ans + "\n(Çevrimiçi model yanıtı: bilimsel doğruluğu garanti edilmez.)", {}, std::nullopt, true};
    }
    return {"Bunu anlayamadım. 'yardım' yazarak neler yapabileceğimi görebilirsin.", {}, std::nullopt, false};
}

}  // namespace kozmo::nova

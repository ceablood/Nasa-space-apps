#include "kozmo/settings.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::settings {

const char* to_string(ColorVision c) {
    switch (c) {
        case ColorVision::Normal: return "Normal";
        case ColorVision::Protanopia: return "Protanopi (kırmızı körlüğü)";
        case ColorVision::Deuteranopia: return "Döteranopi (yeşil körlüğü)";
        case ColorVision::Tritanopia: return "Tritanopi (mavi körlüğü)";
    }
    return "?";
}

const char* to_string(Difficulty d) {
    switch (d) {
        case Difficulty::Story: return "Hikâye";
        case Difficulty::Standard: return "Standart";
        case Difficulty::Realistic: return "Gerçekçi";
    }
    return "?";
}

std::map<std::string, std::string> default_keys() {
    return {{"İleri", "W"}, {"Geri", "S"}, {"Sol", "A"}, {"Sağ", "D"}, {"Zıpla", "SpaceBar"}, {"Etkileşim", "E"}, {"Otur/Kalk", "C"},
            {"Motorlar", "F"}, {"İniş desteği", "L"}, {"İnişi başlat", "B"}, {"Araçtan çık", "X"}, {"Numune", "G"}, {"Gaz +", "R"},
            {"Gaz -", "V"}, {"İmleç", "Tab"}};
}

std::vector<std::pair<std::string, std::string>> key_conflicts(const std::map<std::string, std::string>& keys) {
    std::vector<std::pair<std::string, std::string>> out;
    for (auto a = keys.begin(); a != keys.end(); ++a)
        for (auto b = std::next(a); b != keys.end(); ++b)
            if (!a->second.empty() && a->second == b->second) out.push_back({a->first, b->first});
    return out;
}

std::vector<std::string> Settings::validate() {
    std::vector<std::string> fixed;
    auto clampf = [&](double& v, double lo, double hi, const char* name) {
        const double c = std::isfinite(v) ? std::clamp(v, lo, hi) : lo;
        if (c != v) {
            v = c;
            fixed.push_back(name);
        }
    };
    clampf(text_scale, 0.75, 2.0, "text_scale");
    clampf(camera_shake, 0.0, 1.0, "camera_shake");
    clampf(master_volume, 0.0, 1.0, "master_volume");
    clampf(music_volume, 0.0, 1.0, "music_volume");
    clampf(sfx_volume, 0.0, 1.0, "sfx_volume");
    clampf(voice_volume, 0.0, 1.0, "voice_volume");
    clampf(mouse_sensitivity, 0.1, 5.0, "mouse_sensitivity");
    if (autosave_minutes < 0 || autosave_minutes > 120) {
        autosave_minutes = std::clamp(autosave_minutes, 0, 120);
        fixed.push_back("autosave_minutes");
    }
    if (keys.empty()) {
        keys = default_keys();
        fixed.push_back("keys");
    }
    return fixed;
}

json::Value Settings::to_json() const {
    json::Value v = json::Value::object();
    v.set("lang", static_cast<int>(language));
    v.set("text_scale", text_scale);
    v.set("subtitles", subtitles);
    v.set("color_vision", static_cast<int>(color_vision));
    v.set("high_contrast", high_contrast);
    v.set("camera_shake", camera_shake);
    v.set("reduce_motion", reduce_motion);
    v.set("master", master_volume);
    v.set("music", music_volume);
    v.set("sfx", sfx_volume);
    v.set("voice", voice_volume);
    v.set("invert_y", invert_y);
    v.set("mouse", mouse_sensitivity);
    v.set("difficulty", static_cast<int>(difficulty));
    v.set("autosave", autosave_minutes);
    json::Value k = json::Value::object();
    for (const auto& [a, b] : keys) k.set(a, b);
    v.set("keys", k);
    return v;
}

Result<Settings> Settings::from_json(const json::Value& v) {
    if (!v.is_object()) return make_error(ErrorCode::Parse, "Ayar dosyası bozuk");
    Settings s;
    const int lang = v["lang"].as_int(0), cv = v["color_vision"].as_int(0), df = v["difficulty"].as_int(1);
    if (lang < 0 || lang > 1 || cv < 0 || cv > 3 || df < 0 || df > 2) return make_error(ErrorCode::Parse, "Geçersiz ayar değeri");
    s.language = static_cast<Language>(lang);
    s.text_scale = v["text_scale"].as_number(1.0);
    s.subtitles = v["subtitles"].as_bool(true);
    s.color_vision = static_cast<ColorVision>(cv);
    s.high_contrast = v["high_contrast"].as_bool(false);
    s.camera_shake = v["camera_shake"].as_number(1.0);
    s.reduce_motion = v["reduce_motion"].as_bool(false);
    s.master_volume = v["master"].as_number(0.8);
    s.music_volume = v["music"].as_number(0.6);
    s.sfx_volume = v["sfx"].as_number(0.8);
    s.voice_volume = v["voice"].as_number(1.0);
    s.invert_y = v["invert_y"].as_bool(false);
    s.mouse_sensitivity = v["mouse"].as_number(1.0);
    s.difficulty = static_cast<Difficulty>(df);
    s.autosave_minutes = v["autosave"].as_int(10);
    for (const auto& [a, b] : v["keys"].as_object()) s.keys[a] = b.as_string();
    (void)s.validate();
    return s;
}

DifficultyScale scale(Difficulty d) {
    switch (d) {
        case Difficulty::Story: return {0.6, 0.3, 0.5, false};
        case Difficulty::Standard: return {1.0, 1.0, 1.0, false};
        case Difficulty::Realistic: return {1.0, 1.5, 1.2, true};
    }
    return {1, 1, 1, false};
}

namespace {
double to_linear(double c) { return c <= 0.04045 ? c / 12.92 : std::pow((c + 0.055) / 1.055, 2.4); }
double to_srgb(double c) {
    c = std::clamp(c, 0.0, 1.0);
    return c <= 0.0031308 ? 12.92 * c : 1.055 * std::pow(c, 1.0 / 2.4) - 0.055;
}
using M3 = std::array<std::array<double, 3>, 3>;
const M3& machado(ColorVision v) {
    static const M3 I = {{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}};
    static const M3 P = {{{0.152286, 1.052583, -0.204868}, {0.114503, 0.786281, 0.099216}, {-0.003882, -0.048116, 1.051998}}};
    static const M3 D = {{{0.367322, 0.860646, -0.227968}, {0.280085, 0.672501, 0.047413}, {-0.011820, 0.042940, 0.968881}}};
    static const M3 T = {{{1.255528, -0.076749, -0.178779}, {-0.078411, 0.930809, 0.147602}, {0.004733, 0.691367, 0.303900}}};
    switch (v) {
        case ColorVision::Protanopia: return P;
        case ColorVision::Deuteranopia: return D;
        case ColorVision::Tritanopia: return T;
        default: return I;
    }
}
}  // namespace

Rgb simulate(Rgb c, ColorVision v) {
    const double l[3] = {to_linear(c.r), to_linear(c.g), to_linear(c.b)};
    const M3& m = machado(v);
    double o[3];
    for (int i = 0; i < 3; ++i) o[i] = m[i][0] * l[0] + m[i][1] * l[1] + m[i][2] * l[2];
    return {to_srgb(o[0]), to_srgb(o[1]), to_srgb(o[2])};
}

double difference(Rgb a, Rgb b) {
    const double dr = to_linear(a.r) - to_linear(b.r), dg = to_linear(a.g) - to_linear(b.g), db = to_linear(a.b) - to_linear(b.b);
    return std::sqrt(dr * dr + dg * dg + db * db);
}

Palette palette(ColorVision v, bool hc) {
    Palette p;
    // varsayılan: yeşil tamam, sarı uyarı, kırmızı tehlike, camgöbeği bilgi (KOZMOGENİS key-art tonları)
    p = {{0.30, 0.75, 0.40}, {0.95, 0.75, 0.20}, {0.90, 0.25, 0.20}, {0.45, 0.80, 0.90}, {0.92, 0.93, 0.95}, {0.04, 0.05, 0.08}};
    if (v == ColorVision::Protanopia || v == ColorVision::Deuteranopia) {
        // kırmızı/yeşil yerine mavi/turuncu ekseni (Okabe-Ito güvenli paleti)
        p.ok = {0.00, 0.45, 0.70};       // mavi
        p.warning = {0.94, 0.89, 0.26};  // sarı
        p.danger = {0.84, 0.37, 0.00};   // vermilyon/turuncu
        p.info = {0.34, 0.71, 0.91};
    } else if (v == ColorVision::Tritanopia) {
        p.ok = {0.00, 0.62, 0.45};       // mavimsi yeşil
        p.warning = {0.80, 0.47, 0.65};  // pembe
        p.danger = {0.84, 0.37, 0.00};
        p.info = {0.60, 0.60, 0.60};
    }
    if (hc) {
        p.text = {1, 1, 1};
        p.background = {0, 0, 0};
    }
    return p;
}

// ------------------------------------------------------------------------- dil tablosu
namespace {
const std::map<std::string, std::pair<std::string, std::string>>& table() {
    static const std::map<std::string, std::pair<std::string, std::string>> t = {
        {"menu.new_game", {"Yeni oyun", "New game"}},
        {"menu.load", {"Yükle", "Load"}},
        {"menu.save", {"Kaydet", "Save"}},
        {"menu.settings", {"Ayarlar", "Settings"}},
        {"menu.quit", {"Çıkış", "Quit"}},
        {"hud.altitude", {"İRTİFA", "ALTITUDE"}},
        {"hud.speed", {"HIZ", "SPEED"}},
        {"hud.fuel", {"YAKIT", "FUEL"}},
        {"hud.oxygen", {"OKSİJEN", "OXYGEN"}},
        {"hud.temperature", {"SICAKLIK", "TEMPERATURE"}},
        {"hud.pressure", {"BASINÇ", "PRESSURE"}},
        {"hud.power", {"GÜÇ", "POWER"}},
        {"hud.shield", {"KALKAN", "SHIELD"}},
        {"hud.hull", {"GÖVDE", "HULL"}},
        {"hud.engine", {"MOTOR", "ENGINE"}},
        {"hud.navigation", {"NAVİGASYON", "NAVIGATION"}},
        {"hud.radar", {"RADAR", "RADAR"}},
        {"action.sit", {"Otur", "Sit"}},
        {"action.stand", {"Kalk", "Stand"}},
        {"action.exit_craft", {"Araçtan çık", "Exit vehicle"}},
        {"action.enter", {"Gir", "Enter"}},
        {"action.talk", {"Konuş", "Talk"}},
        {"action.sample", {"Numune topla", "Collect sample"}},
        {"action.build", {"İnşa et", "Build"}},
        {"warn.fuel_leak", {"YAKIT SIZINTISI", "FUEL LEAK"}},
        {"warn.depressurization", {"KABİN BASINCI DÜŞÜYOR", "CABIN DEPRESSURIZATION"}},
        {"warn.oxygen_low", {"OKSİJEN DÜŞÜK", "OXYGEN LOW"}},
        {"warn.power_failure", {"ELEKTRİK KESİNTİSİ", "POWER FAILURE"}},
        {"warn.engine_failure", {"MOTOR ARIZASI", "ENGINE FAILURE"}},
        {"nova.confirm", {"Onaylıyor musun?", "Do you confirm?"}},
        {"nova.cancelled", {"İşlem iptal edildi", "Action cancelled"}},
        {"settings.subtitles", {"Altyazılar", "Subtitles"}},
        {"settings.text_scale", {"Yazı boyutu", "Text size"}},
        {"settings.color_vision", {"Renk görme modu", "Color vision mode"}},
        {"settings.camera_shake", {"Kamera sarsıntısı", "Camera shake"}},
        {"settings.reduce_motion", {"Hareketi azalt", "Reduce motion"}},
        {"settings.difficulty", {"Zorluk", "Difficulty"}},
        {"colony.population", {"Nüfus", "Population"}},
        {"colony.housing", {"Konut", "Housing"}},
        {"colony.morale", {"Moral", "Morale"}},
        {"quest.active", {"Etkin görevler", "Active quests"}},
        {"quest.completed", {"Görev tamamlandı", "Quest completed"}},
    };
    return t;
}
}  // namespace

std::string tr(const std::string& key, Language lang) {
    static const std::string missing = "[?]";
    auto it = table().find(key);
    if (it == table().end()) return key;   // anahtar kendisi (görünür eksik)
    const std::string& s = lang == Language::Turkish ? it->second.first : it->second.second;
    if (!s.empty()) return s;
    return it->second.first.empty() ? missing : it->second.first;   // İngilizce eksikse Türkçeye düş
}

std::vector<std::string> missing_translations() {
    std::vector<std::string> m;
    for (const auto& [k, v] : table())
        if (v.first.empty() || v.second.empty()) m.push_back(k);
    return m;
}

std::vector<std::string> keys() {
    std::vector<std::string> k;
    for (const auto& [a, b] : table()) k.push_back(a);
    return k;
}

}  // namespace kozmo::settings

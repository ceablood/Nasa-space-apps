// KozmoCore — ayarlar, erişilebilirlik ve yerelleştirme (V30 §19; V41 §1.6 "kamera sarsıntısı azaltılabilmeli").
//
// Renk körlüğü: Machado, Oliveira & Fernandes (2009) "A Physiologically-based Model for Simulation of Color
// Vision Deficiency", şiddet 1.0 matrisleri (doğrusal RGB). Arayüz paleti, kırmızı/yeşil ayrımına dayanmayan
// (mavi/turuncu) uyarı renklerine geçer. Dil tablosu: Türkçe (ana) ve İngilizce; eksik anahtarlar raporlanır.
#pragma once

#include <array>
#include <map>
#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::settings {

enum class Language { Turkish, English };
enum class ColorVision { Normal, Protanopia, Deuteranopia, Tritanopia };
enum class Difficulty { Story, Standard, Realistic };
const char* to_string(ColorVision c);
const char* to_string(Difficulty d);

struct Rgb {
    double r, g, b;   // 0..1 sRGB
};

struct Settings {
    Language language = Language::Turkish;
    double text_scale = 1.0;          // 0.75 .. 2.0
    bool subtitles = true;
    ColorVision color_vision = ColorVision::Normal;
    bool high_contrast = false;
    double camera_shake = 1.0;        // 0 .. 1
    bool reduce_motion = false;       // sıfır-g süzülme, kafa sallanması kapanır
    double master_volume = 0.8, music_volume = 0.6, sfx_volume = 0.8, voice_volume = 1.0;
    bool invert_y = false;
    double mouse_sensitivity = 1.0;   // 0.1 .. 5
    Difficulty difficulty = Difficulty::Standard;
    int autosave_minutes = 10;        // 0 = kapalı
    std::map<std::string, std::string> keys;   // eylem -> tuş

    // aralık dışı değerleri sınırlar; düzeltilen alanları döner
    std::vector<std::string> validate();
    double effective_shake() const { return reduce_motion ? 0.0 : camera_shake; }
    json::Value to_json() const;
    static Result<Settings> from_json(const json::Value& v);
};
std::map<std::string, std::string> default_keys();
// tuş çakışması (aynı tuş iki eyleme): çakışan eylem çiftleri
std::vector<std::pair<std::string, std::string>> key_conflicts(const std::map<std::string, std::string>& keys);

// Zorluk: oyun parametre çarpanları (bilimsel değerleri DEĞİL, oyuncuya verilen payı değiştirir)
struct DifficultyScale {
    double consumables;      // yaşam desteği tüketim çarpanı
    double failure_rate;     // arıza sıklığı çarpanı
    double weather;          // hava olayı sıklığı
    bool permadeath;
};
DifficultyScale scale(Difficulty d);

// renk görme simülasyonu (sRGB -> doğrusal -> Machado matrisi -> sRGB)
Rgb simulate(Rgb c, ColorVision v);
// iki rengin algısal farkı (doğrusal RGB'de öklid; basit ölçü) — palet testleri için
double difference(Rgb a, Rgb b);

struct Palette {
    Rgb ok, warning, danger, info, text, background;
};
Palette palette(ColorVision v, bool high_contrast);

// --- yerelleştirme
std::string tr(const std::string& key, Language lang);   // eksik anahtar: anahtarın kendisi
std::vector<std::string> missing_translations();      // her iki dilde de olmayan anahtarlar
std::vector<std::string> keys();

}  // namespace kozmo::settings

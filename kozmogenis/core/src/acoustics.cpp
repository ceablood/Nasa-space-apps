#include "kozmo/acoustics.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::acoustics {

namespace {
constexpr double kR = 8.314462618;
double source_db(Cue c) {   // 1 m'deki kaynak seviyesi (Dünya havasında), dB SPL — ses tasarımı
    switch (c) {
        case Cue::Footstep: return 60;
        case Cue::EngineRumble: return 140;
        case Cue::Thruster: return 120;
        case Cue::DoorAirlock: return 85;
        case Cue::Wind: return 70;
        case Cue::DustImpact: return 55;
        case Cue::Explosion: return 160;
        case Cue::Voice: return 65;
        case Cue::Alarm: return 90;
        case Cue::Drill: return 100;
    }
    return 60;
}
}  // namespace

double speed_of_sound(double gamma, double t, double m) { return std::sqrt(gamma * kR * t / std::max(1e-6, m)); }

double gamma_for(const challenge::PlanetEnvironment& e) {
    if (e.molar_mass_gmol > 40) return 1.29;        // CO2 (Mars, Venüs)
    if (e.molar_mass_gmol < 4) return 1.45;         // H2/He (gaz devleri, yaklaşık)
    return 1.40;                                    // N2/hava (Dünya, Titan)
}

double speed_of_sound(const challenge::PlanetEnvironment& e) {
    if (e.pressure_kpa <= 0.01 || e.molar_mass_gmol <= 0) return 0.0;
    return speed_of_sound(gamma_for(e), e.temp_mean_c + 273.15, e.molar_mass_gmol / 1000.0);
}

double level_offset_db(const challenge::PlanetEnvironment& e) {
    const double c = speed_of_sound(e);
    if (c <= 0) return -200.0;
    const double z = e.surface_density() * c, z0 = 1.225 * 343.0;
    return 10.0 * std::log10(z / z0);
}

const char* to_string(Channel c) {
    switch (c) {
        case Channel::Air: return "hava";
        case Channel::Structure: return "yapı (temas)";
        case Channel::Internal: return "iç (kabin/giysi)";
        case Channel::Radio: return "telsiz";
    }
    return "?";
}

const char* to_string(Cue c) {
    switch (c) {
        case Cue::Footstep: return "Ayak sesi";
        case Cue::EngineRumble: return "Motor gürültüsü";
        case Cue::Thruster: return "RCS iticisi";
        case Cue::DoorAirlock: return "Hava kilidi kapısı";
        case Cue::Wind: return "Rüzgâr";
        case Cue::DustImpact: return "Toz çarpması";
        case Cue::Explosion: return "Patlama";
        case Cue::Voice: return "Konuşma";
        case Cue::Alarm: return "Alarm";
        case Cue::Drill: return "Matkap";
    }
    return "?";
}

Heard hear(Cue cue, const challenge::PlanetEnvironment& e, double d, bool inside, bool touching, bool radio) {
    Heard h{false, Channel::Air, -200, 0, ""};
    const double src = source_db(cue);
    const double spread = 20.0 * std::log10(std::max(1.0, d));   // küresel yayılma
    if (inside && (cue == Cue::Alarm || cue == Cue::Voice || cue == Cue::DoorAirlock)) {
        h = {true, Channel::Internal, src - spread, d / 343.0, "Basınçlı ortam: normal duyulur"};
        return h;
    }
    const double offs = level_offset_db(e);
    if (offs > -150 && !inside) {
        const double lvl = src + offs - spread - (e.pressure_kpa < 2.0 ? 0.002 * d : 0.0);   // ince atmosferde yüksek frekans emilimi (kaba)
        if (lvl > 0) {
            const double c = speed_of_sound(e);
            h = {true, Channel::Air, lvl, d / c, "Hava yoluyla, ses hızı " + std::to_string(static_cast<int>(c)) + " m/s"};
        }
    }
    if (touching) {
        const double lvl = src - 15.0 - 0.5 * spread;   // yapı yoluyla iletim: kayıp yüksek, mesafeyle yavaş azalır
        if (!h.audible || lvl > h.level_db) h = {lvl > 0, Channel::Structure, lvl, d / 3000.0, "Zemin/gövde titreşimi olarak hissedilir"};
    }
    if (!h.audible && radio && (cue == Cue::Voice || cue == Cue::Alarm)) h = {true, Channel::Radio, 60, 0, "Telsizden"};
    if (!h.audible) h.note = offs <= -150 ? "Vakum: hava yoluyla ses yok" : "Çok uzak/zayıf";
    return h;
}

}  // namespace kozmo::acoustics

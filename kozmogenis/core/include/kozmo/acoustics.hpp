// KozmoCore — ortama göre ses fiziği (V30 §19 ses): hangi ses duyulur, ne kadar yüksek, ne hızla yayılır.
//
// Gerçek:
//   * Ses hızı c = sqrt(gamma R T / M): Dünya ~343 m/s (20 °C); Mars ~240 m/s (Perseverance mikrofonu 2022:
//     düşük frekanslar ~240, yüksek ~250 m/s); Titan ~194 m/s
//   * Aynı akustik güç için seviye farkı ~10 log10(rho c / rho0 c0): Mars'ta sesler ~20 dB daha zayıf
//     (Maurice vd., Nature 2022 ölçümleriyle uyumlu mertebe)
//   * Vakumda hava yoluyla ses yoktur: yalnız gövdeye temasla (yapı yoluyla), giysi/kabin içinden ve telsizle
// Olay seviyeleri (dB) ve kanal kuralları OYUN SES TASARIMI VARSAYIMIDIR.
#pragma once

#include <string>

#include "kozmo/challenge.hpp"

namespace kozmo::acoustics {

double speed_of_sound(double gamma, double temp_k, double molar_kg);
double speed_of_sound(const challenge::PlanetEnvironment& env);          // ortam ortalama sıcaklığında
double gamma_for(const challenge::PlanetEnvironment& env);               // CO2 ~1.29, N2/hava ~1.40, H2/He ~1.4-1.66
double level_offset_db(const challenge::PlanetEnvironment& env);         // Dünya'ya göre (vakumda -inf yerine -200)

enum class Channel { Air, Structure, Internal, Radio };
const char* to_string(Channel c);

enum class Cue { Footstep, EngineRumble, Thruster, DoorAirlock, Wind, DustImpact, Explosion, Voice, Alarm, Drill };
const char* to_string(Cue c);

struct Heard {
    bool audible;
    Channel channel;
    double level_db;          // dinleyicideki seviye
    double delay_s;           // yayılma gecikmesi (hava yolu)
    std::string note;
};

// listener_inside: basınçlı alan/kabin içinde; touching: kaynakla aynı yapıya temas (zemin, gövde)
Heard hear(Cue cue, const challenge::PlanetEnvironment& env, double distance_m, bool listener_inside, bool touching, bool radio_on);

}  // namespace kozmo::acoustics

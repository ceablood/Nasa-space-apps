// KozmoCore — deterministik komut kaydı ve tekrar oynatma (V30 §19.3 kayıt, §20 çok oyunculu altyapı).
// Oyun durumu tohumlu ve deterministik olduğundan aynı başlangıç + aynı komut dizisi aynı durumu üretir.
// Bu, kilit adımlı (lockstep) çok oyunculu senkronizasyonun ve hata yeniden üretiminin temelidir:
// istemciler yalnız komutları paylaşır, durum karması (FNV-1a 64) eşleşmezse senkron bozulmuştur.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "kozmo/game.hpp"

namespace kozmo::replay {

enum class Op { Advance, StartResearch, LaunchKit, FoundOutpost, BuildModule, Trade };
const char* to_string(Op o);

struct Command {
    Op op;
    double a = 0;            // gün / miktar
    std::string s1 = "", s2 = "";   // anahtar / hedef / koloni / emtia
    bool flag = false;       // alım (trade)
};

std::uint64_t fnv1a(const std::string& s);
std::uint64_t state_hash(const Game& g);

class Recorder {
public:
    Recorder(std::uint64_t seed, std::string agency, double credits);
    Game& game() { return game_; }
    const Game& game() const { return game_; }
    // komutu uygula ve kaydet; başarısız komut da kaydedilir (tekrarlarda aynı sonucu vermeli)
    Status apply(const Command& c);
    const std::vector<Command>& log() const { return log_; }
    std::uint64_t hash() const { return state_hash(game_); }
    json::Value to_json() const;
    static Result<Recorder> from_json(const json::Value& v);   // kaydı baştan oynatarak kurar

private:
    static Status exec(Game& g, const Command& c);
    std::uint64_t seed_;
    std::string agency_;
    double credits_;
    Game game_;
    std::vector<Command> log_;
};

// kaydı yeni bir oyunda oynat; karma döner
std::uint64_t replay(std::uint64_t seed, const std::string& agency, double credits, const std::vector<Command>& log);

}  // namespace kozmo::replay

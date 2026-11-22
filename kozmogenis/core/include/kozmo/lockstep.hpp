// KozmoCore — kilit adımlı (lockstep) çok oyunculu oturum (V30 §20): eşler yalnız komut paylaşır; her adımda
// tüm eşlerin komutları toplanınca simülasyon ilerler (giriş gecikmesi = ağ gecikmesini gizleme payı) ve durum
// karmaları karşılaştırılır. Uyuşmazlık (desync) hangi adımda olduğuyla raporlanır. Ağ katmanı yerine bellekte
// gecikmeli mesaj kuyruğu kullanılır (test edilebilir aktarım); gerçek soket katmanı PLANLANDI.
#pragma once

#include <cstdint>
#include <deque>
#include <string>
#include <vector>

#include "kozmo/replay.hpp"

namespace kozmo::lockstep {

struct Packet {
    int from, turn;
    std::vector<replay::Command> commands;
    std::uint64_t hash;           // gönderenin bir önceki tur sonrası karması
    int deliver_at;               // simülasyon "saat"i (aktarım gecikmesi)
};

class Session {
public:
    Session(int peers, std::uint64_t seed, int input_delay_turns = 2, int latency_ticks = 1);
    // oyuncu komutu: input_delay tur sonra uygulanır
    void submit(int peer, const replay::Command& c);
    // bir ağ saati ilerle: paketleri ilet, hazır turları uygula; dönüş: bu adımda uygulanan tur sayısı
    int pump();
    int turn() const { return turn_; }
    bool desynced() const { return desync_turn_ >= 0; }
    int desync_turn() const { return desync_turn_; }
    std::uint64_t hash(int peer) const;
    const Game& game(int peer) const { return peers_[static_cast<std::size_t>(peer)].rec.game(); }
    // test: bir eşin durumunu bozar (hile/hata benzetimi)
    void corrupt(int peer);
    double turn_days = 0.25;      // her tur oyun zamanında 6 saat

private:
    struct Peer {
        replay::Recorder rec;
        std::vector<std::vector<replay::Command>> outbox;        // tur -> komutlar
        std::vector<std::vector<std::vector<replay::Command>>> inbox;   // tur -> eş -> komutlar
        std::vector<std::vector<bool>> got;                      // tur -> eş -> alındı
        std::vector<std::uint64_t> hashes;                       // tur -> karma
    };
    void ensure(Peer& p, int t);
    std::vector<Peer> peers_;
    std::deque<Packet> wire_;
    int n_, delay_, latency_, turn_ = 0, clock_ = 0, desync_turn_ = -1;
    std::vector<std::vector<std::uint64_t>> reported_;           // tur -> eş -> karma
};

}  // namespace kozmo::lockstep

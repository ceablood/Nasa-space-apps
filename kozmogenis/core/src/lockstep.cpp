#include "kozmo/lockstep.hpp"

#include <algorithm>

namespace kozmo::lockstep {

Session::Session(int peers, std::uint64_t seed, int delay, int latency) : n_(std::max(1, peers)), delay_(std::max(1, delay)), latency_(std::max(0, latency)) {
    for (int i = 0; i < n_; ++i) peers_.push_back({replay::Recorder(seed, "KOZMOGENİS", 3e6), {}, {}, {}, {}});
}

void Session::ensure(Peer& p, int t) {
    const std::size_t need = static_cast<std::size_t>(t + 1);
    if (p.outbox.size() < need) p.outbox.resize(need);
    if (p.inbox.size() < need) p.inbox.resize(need, std::vector<std::vector<replay::Command>>(static_cast<std::size_t>(n_)));
    if (p.got.size() < need) p.got.resize(need, std::vector<bool>(static_cast<std::size_t>(n_), false));
    if (reported_.size() < need) reported_.resize(need, std::vector<std::uint64_t>(static_cast<std::size_t>(n_), 0));
}

void Session::submit(int peer, const replay::Command& c) {
    Peer& p = peers_[static_cast<std::size_t>(peer)];
    const int t = turn_ + delay_;
    ensure(p, t);
    p.outbox[static_cast<std::size_t>(t)].push_back(c);
}

std::uint64_t Session::hash(int peer) const { return peers_[static_cast<std::size_t>(peer)].rec.hash(); }

void Session::corrupt(int peer) { (void)peers_[static_cast<std::size_t>(peer)].rec.game().wallet().spend(1.0, "bozulma", 0); }

int Session::pump() {
    ++clock_;
    // 1) her eş, henüz göndermediği bir sonraki tur paketini (boş olsa bile) yayınlar
    for (int i = 0; i < n_; ++i) {
        Peer& p = peers_[static_cast<std::size_t>(i)];
        const int t = turn_ + delay_ - 1;   // gecikme penceresinin sonu
        for (int tt = turn_; tt <= t; ++tt) {
            ensure(p, tt);
            if (p.got[static_cast<std::size_t>(tt)][static_cast<std::size_t>(i)]) continue;
            p.got[static_cast<std::size_t>(tt)][static_cast<std::size_t>(i)] = true;
            p.inbox[static_cast<std::size_t>(tt)][static_cast<std::size_t>(i)] = p.outbox[static_cast<std::size_t>(tt)];
            for (int j = 0; j < n_; ++j)
                if (j != i) wire_.push_back({i, tt, p.outbox[static_cast<std::size_t>(tt)], p.rec.hash(), clock_ + latency_});
        }
    }
    // 2) aktarım: zamanı gelen paketler
    for (auto it = wire_.begin(); it != wire_.end();) {
        if (it->deliver_at > clock_) {
            ++it;
            continue;
        }
        for (int j = 0; j < n_; ++j) {
            if (j == it->from) continue;
            Peer& p = peers_[static_cast<std::size_t>(j)];
            ensure(p, it->turn);
            p.got[static_cast<std::size_t>(it->turn)][static_cast<std::size_t>(it->from)] = true;
            p.inbox[static_cast<std::size_t>(it->turn)][static_cast<std::size_t>(it->from)] = it->commands;
        }
        it = wire_.erase(it);
    }
    // 3) tüm eşlerde tüm girdiler geldiyse turu uygula (eş sırası sabit: deterministik)
    int applied = 0;
    for (;;) {
        bool ready = true;
        for (auto& p : peers_) {
            ensure(p, turn_);
            for (bool b : p.got[static_cast<std::size_t>(turn_)]) ready = ready && b;
        }
        if (!ready) break;
        for (int i = 0; i < n_; ++i) {
            Peer& p = peers_[static_cast<std::size_t>(i)];
            for (int src = 0; src < n_; ++src)
                for (const auto& c : p.inbox[static_cast<std::size_t>(turn_)][static_cast<std::size_t>(src)]) (void)p.rec.apply(c);
            (void)p.rec.apply({replay::Op::Advance, turn_days});
            reported_[static_cast<std::size_t>(turn_)][static_cast<std::size_t>(i)] = p.rec.hash();
        }
        for (int i = 1; i < n_; ++i)
            if (desync_turn_ < 0 && reported_[static_cast<std::size_t>(turn_)][static_cast<std::size_t>(i)] != reported_[static_cast<std::size_t>(turn_)][0])
                desync_turn_ = turn_;
        ++turn_;
        ++applied;
    }
    return applied;
}

}  // namespace kozmo::lockstep

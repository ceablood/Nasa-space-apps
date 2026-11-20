#include "kozmo/core.hpp"

#include <cmath>
#include <cstdio>
#include <deque>

namespace kozmo {

const char* to_string(ErrorCode c) {
    switch (c) {
        case ErrorCode::InvalidArgument: return "InvalidArgument";
        case ErrorCode::NotFound: return "NotFound";
        case ErrorCode::InsufficientFunds: return "InsufficientFunds";
        case ErrorCode::InsufficientResources: return "InsufficientResources";
        case ErrorCode::Infeasible: return "Infeasible";
        case ErrorCode::Locked: return "Locked";
        case ErrorCode::Parse: return "Parse";
        case ErrorCode::Io: return "Io";
    }
    return "Unknown";
}

// ------------------------------------------------------------------------ Log
namespace {
Log::Sink g_sink;
LogLevel g_level = LogLevel::Info;
std::deque<std::string> g_recent;
constexpr std::size_t kRecentMax = 256;

const char* level_name(LogLevel l) {
    switch (l) {
        case LogLevel::Debug: return "DEBUG";
        case LogLevel::Info: return "INFO";
        case LogLevel::Warn: return "WARN";
        case LogLevel::Error: return "ERROR";
    }
    return "?";
}
}  // namespace

std::mutex& Log::mtx() {
    static std::mutex m;
    return m;
}

void Log::set_sink(Sink s) {
    std::lock_guard<std::mutex> lk(mtx());
    g_sink = std::move(s);
}

void Log::set_level(LogLevel l) {
    std::lock_guard<std::mutex> lk(mtx());
    g_level = l;
}

void Log::write(LogLevel l, const std::string& channel, const std::string& msg) {
    std::lock_guard<std::mutex> lk(mtx());
    if (static_cast<int>(l) < static_cast<int>(g_level)) return;
    std::string line = std::string("[") + level_name(l) + "][" + channel + "] " + msg;
    g_recent.push_back(line);
    if (g_recent.size() > kRecentMax) g_recent.pop_front();
    if (g_sink) {
        g_sink(l, channel, msg);
    } else if (l >= LogLevel::Warn) {
        std::fprintf(stderr, "%s\n", line.c_str());
    }
}

std::vector<std::string> Log::recent(std::size_t n) {
    std::lock_guard<std::mutex> lk(mtx());
    std::vector<std::string> out;
    const std::size_t start = g_recent.size() > n ? g_recent.size() - n : 0;
    for (std::size_t i = start; i < g_recent.size(); ++i) out.push_back(g_recent[i]);
    return out;
}

// ------------------------------------------------------------------------ EventBus
void EventBus::unsubscribe(HandlerId id) {
    for (auto& [type, list] : handlers_) {
        for (auto it = list.begin(); it != list.end(); ++it) {
            if (it->id == id) {
                list.erase(it);
                return;
            }
        }
    }
}

// ------------------------------------------------------------------------ Rng
std::uint64_t Rng::next_u64() {
    std::uint64_t z = (s_ += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}

double Rng::uniform() { return static_cast<double>(next_u64() >> 11) * (1.0 / 9007199254740992.0); }

double Rng::uniform(double lo, double hi) { return lo + (hi - lo) * uniform(); }

int Rng::range(int lo, int hi_inclusive) {
    if (hi_inclusive <= lo) return lo;
    const auto span = static_cast<std::uint64_t>(hi_inclusive - lo) + 1;
    return lo + static_cast<int>(next_u64() % span);
}

bool Rng::chance(double p) { return uniform() < p; }

double Rng::normal(double mean, double sd) {
    double u1 = uniform();
    if (u1 < 1e-300) u1 = 1e-300;
    const double u2 = uniform();
    return mean + sd * std::sqrt(-2.0 * std::log(u1)) * std::cos(6.283185307179586 * u2);
}

}  // namespace kozmo

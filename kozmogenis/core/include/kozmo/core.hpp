// KozmoCore — temel altyapı: hata/sonuç türü, günlük (log), olay yolu, deterministik rastgele sayı.
// Bu başlık Unreal Engine'den bağımsızdır; UE5 modülü aynı kodu sarmalar (bkz. unreal/).
#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace kozmo {

// ------------------------------------------------------------------------ Hata / Sonuç
enum class ErrorCode {
    InvalidArgument,
    NotFound,
    InsufficientFunds,
    InsufficientResources,
    Infeasible,          // fiziksel olarak mümkün değil (ör. delta-v yetersiz)
    Locked,              // araştırma / önkoşul eksik
    Parse,
    Io,
};

const char* to_string(ErrorCode c);

struct Error {
    ErrorCode code;
    std::string message;
};

template <typename T>
class Result {
public:
    Result(T value) : v_(std::move(value)) {}              // NOLINT: örtük başarı
    Result(Error err) : v_(std::move(err)) {}              // NOLINT: örtük hata
    bool ok() const { return std::holds_alternative<T>(v_); }
    explicit operator bool() const { return ok(); }
    const T& value() const { return std::get<T>(v_); }
    T& value() { return std::get<T>(v_); }
    const Error& error() const { return std::get<Error>(v_); }

private:
    std::variant<T, Error> v_;
};

struct Ok {};                                              // değersiz başarı
using Status = Result<Ok>;
inline Status ok_status() { return Status(Ok{}); }
inline Error make_error(ErrorCode c, std::string msg) { return Error{c, std::move(msg)}; }

// ------------------------------------------------------------------------ Günlük
enum class LogLevel { Debug = 0, Info = 1, Warn = 2, Error = 3 };

class Log {
public:
    using Sink = std::function<void(LogLevel, const std::string& channel, const std::string& msg)>;
    static void set_sink(Sink s);                          // UE5: UE_LOG'a yönlendirilir
    static void set_level(LogLevel l);
    static void write(LogLevel l, const std::string& channel, const std::string& msg);
    static std::vector<std::string> recent(std::size_t n); // son n satır (oyun içi konsol/test)

private:
    static std::mutex& mtx();
};

#define KOZMO_LOG(level, chan, msg) ::kozmo::Log::write(::kozmo::LogLevel::level, chan, msg)

// ------------------------------------------------------------------------ tür kimliği (RTTI'sız)
// Unreal Engine varsayılan olarak RTTI'yi kapatır (typeid kullanılamaz); her tür için şablon statik değişkeninin
// adresi benzersiz bir kimliktir.
using TypeId = const void*;
template <typename T>
TypeId type_id() {
    static const char tag = 0;
    return &tag;
}

// ------------------------------------------------------------------------ Olay yolu
// Tüm sistemler birbirine doğrudan bağlanmak yerine olay yayınlar/dinler (şema kuralı 8).
class EventBus {
public:
    using HandlerId = std::uint64_t;

    template <typename E>
    HandlerId subscribe(std::function<void(const E&)> fn) {
        const HandlerId id = ++next_id_;
        handlers_[type_id<E>()].push_back(
            {id, [fn = std::move(fn)](const void* e) { fn(*static_cast<const E*>(e)); }});
        return id;
    }

    void unsubscribe(HandlerId id);

    template <typename E>
    void publish(const E& e) {
        auto it = handlers_.find(type_id<E>());
        if (it == handlers_.end()) return;
        // kopya: işleyici yayın sırasında abone ekleyip çıkarabilir
        const auto list = it->second;
        for (const auto& h : list) h.fn(&e);
        ++published_;
    }

    std::uint64_t published_count() const { return published_; }

private:
    struct Entry {
        HandlerId id;
        std::function<void(const void*)> fn;
    };
    std::map<TypeId, std::vector<Entry>> handlers_;
    HandlerId next_id_ = 0;
    std::uint64_t published_ = 0;
};

// ------------------------------------------------------------------------ Rastgele
// SplitMix64 tabanlı, platformdan bağımsız deterministik üreteç: aynı tohum = aynı oyun (kayıt/tekrar/test).
class Rng {
public:
    explicit Rng(std::uint64_t seed = 0x9E3779B97F4A7C15ull) : s_(seed) {}
    std::uint64_t next_u64();
    double uniform();                                   // [0, 1)
    double uniform(double lo, double hi);
    int range(int lo, int hi_inclusive);
    bool chance(double p);
    double normal(double mean, double sd);              // Box-Muller
    std::uint64_t state() const { return s_; }
    void set_state(std::uint64_t s) { s_ = s; }

private:
    std::uint64_t s_;
};

}  // namespace kozmo

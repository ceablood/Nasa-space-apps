#include "kozmo/gare.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <sstream>

namespace kozmo::gare {

namespace {
std::string trim(const std::string& s) {
    const auto a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    const auto b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}
}  // namespace

// ------------------------------------------------------------------------ Config
Status Config::parse(const std::string& text) {
    std::istringstream in(text);
    std::string line, section;
    int n = 0;
    while (std::getline(in, line)) {
        ++n;
        line = trim(line);
        if (line.empty() || line[0] == ';' || line[0] == '#') continue;
        if (line.front() == '[') {
            if (line.back() != ']') return make_error(ErrorCode::Parse, "Ayar satırı " + std::to_string(n) + ": ']' eksik");
            section = trim(line.substr(1, line.size() - 2));
            continue;
        }
        const auto eq = line.find('=');
        if (eq == std::string::npos) return make_error(ErrorCode::Parse, "Ayar satırı " + std::to_string(n) + ": '=' eksik");
        const std::string key = trim(line.substr(0, eq));
        if (key.empty()) return make_error(ErrorCode::Parse, "Ayar satırı " + std::to_string(n) + ": anahtar boş");
        values_[section.empty() ? key : section + "." + key] = trim(line.substr(eq + 1));
    }
    return ok_status();
}

std::string Config::get(const std::string& key, const std::string& def) const {
    auto it = values_.find(key);
    return it == values_.end() ? def : it->second;
}

double Config::get_number(const std::string& key, double def) const {
    auto it = values_.find(key);
    if (it == values_.end()) return def;
    char* end = nullptr;
    const double v = std::strtod(it->second.c_str(), &end);
    return (end && *end == '\0' && end != it->second.c_str()) ? v : def;
}

bool Config::get_bool(const std::string& key, bool def) const {
    auto it = values_.find(key);
    if (it == values_.end()) return def;
    const std::string& v = it->second;
    if (v == "1" || v == "true" || v == "True" || v == "evet" || v == "on") return true;
    if (v == "0" || v == "false" || v == "False" || v == "hayir" || v == "off") return false;
    return def;
}

// ------------------------------------------------------------------------ EventQueue
void EventQueue::post(std::function<void()> fn, int priority) {
    if (fn) items_.push_back({priority, seq_++, std::move(fn)});
}

std::size_t EventQueue::dispatch(std::size_t max_items) {
    if (items_.empty()) return 0;
    std::vector<Item> batch;
    batch.swap(items_);                   // dağıtım sırasında gönderilenler sonraki kareye kalır
    std::stable_sort(batch.begin(), batch.end(), [](const Item& a, const Item& b) {
        return a.priority != b.priority ? a.priority > b.priority : a.seq < b.seq;
    });
    std::size_t n = 0;
    for (auto& it : batch) {
        if (n >= max_items) {
            items_.push_back(std::move(it));           // bütçe aşıldı: kalanlar sonraki kareye
            continue;
        }
        it.fn();
        ++n;
    }
    return n;
}

// ------------------------------------------------------------------------ Runtime
Runtime::Runtime() = default;

Status Runtime::add(std::unique_ptr<Module> m) {
    if (!m) return make_error(ErrorCode::InvalidArgument, "Boş modül");
    if (running_) return make_error(ErrorCode::InvalidArgument, "Çalışma anında modül eklenemez: " + m->name());
    for (const auto& x : modules_)
        if (x->name() == m->name()) return make_error(ErrorCode::InvalidArgument, "Modül zaten kayıtlı: " + m->name());
    modules_.push_back(std::move(m));
    return ok_status();
}

Module* Runtime::module(const std::string& name) const {
    for (const auto& m : modules_)
        if (m->name() == name) return m.get();
    return nullptr;
}

Status Runtime::init() {
    if (running_) return ok_status();
    // topolojik sıralama (Kahn), kayıt sırası kararlı kalır
    std::map<std::string, Module*> by_name;
    for (const auto& m : modules_) by_name[m->name()] = m.get();
    for (const auto& m : modules_)
        for (const auto& d : m->dependencies())
            if (!by_name.count(d))
                return make_error(ErrorCode::NotFound, "Modül '" + m->name() + "' eksik bağımlılık: '" + d + "'");
    order_.clear();
    std::set<std::string> done;
    while (order_.size() < modules_.size()) {
        bool progressed = false;
        for (const auto& m : modules_) {
            if (done.count(m->name())) continue;
            const auto deps = m->dependencies();
            if (std::all_of(deps.begin(), deps.end(), [&](const std::string& d) { return done.count(d) > 0; })) {
                order_.push_back(m.get());
                done.insert(m->name());
                progressed = true;
            }
        }
        if (!progressed) {
            std::string cyc;
            for (const auto& m : modules_)
                if (!done.count(m->name())) cyc += (cyc.empty() ? "" : ", ") + m->name();
            order_.clear();
            return make_error(ErrorCode::InvalidArgument, "Modül bağımlılık döngüsü: " + cyc);
        }
    }
    for (std::size_t i = 0; i < order_.size(); ++i) {
        Module* m = order_[i];
        auto st = m->init(*this);
        if (!st) {
            KOZMO_LOG(Error, "gare", "Modül başlatılamadı: " + m->name() + " — " + st.error().message);
            bus_.publish(ModuleInitFailed{m->name(), st.error().message});
            // geri al: başlatılmış olanları ters sırayla kapat
            for (std::size_t j = i; j-- > 0;) order_[j]->shutdown(*this);
            order_.clear();
            return st;
        }
        KOZMO_LOG(Info, "gare", "Modül hazır: " + m->name());
    }
    running_ = true;
    return ok_status();
}

void Runtime::shutdown() {
    if (!running_) return;
    for (auto it = order_.rbegin(); it != order_.rend(); ++it) (*it)->shutdown(*this);
    running_ = false;
}

std::vector<std::string> Runtime::init_order() const {
    std::vector<std::string> v;
    for (auto* m : order_) v.push_back(m->name());
    return v;
}

bool Runtime::flag(const std::string& name) const {
    auto it = flags_.find(name);
    if (it != flags_.end()) return it->second;
    return config_.get_bool("features." + name, false);
}

template <typename F>
void Runtime::timed(Module& m, F&& fn) {
    const auto t0 = std::chrono::steady_clock::now();
    fn();
    const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    ModuleTiming& t = timings_[m.name()];
    t.total_ms += ms;
    t.last_ms = ms;
    ++t.calls;
}

void Runtime::frame(double real_dt) {
    if (!running_) return;
    if (real_dt < 0) real_dt = 0;
    ++stats_.frames;
    if (!paused_) {
        accumulator_ += real_dt * time_scale_;
        int steps = 0;
        while (accumulator_ >= fixed_step_ && steps < max_steps_) {
            for (Module* m : order_) timed(*m, [&] { m->fixed_update(*this, fixed_step_); });
            accumulator_ -= fixed_step_;
            stats_.sim_time_s += fixed_step_;
            ++stats_.fixed_steps;
            ++steps;
        }
        if (accumulator_ >= fixed_step_) {
            // kare bütçesi aşıldı: birikmiş süreyi at (simülasyon yavaşlar ama donmaz), kaydını tut
            stats_.dropped_sim_s += static_cast<std::uint64_t>(accumulator_ - std::fmod(accumulator_, fixed_step_));
            accumulator_ = std::fmod(accumulator_, fixed_step_);
        }
    }
    for (Module* m : order_) timed(*m, [&] { m->update(*this, real_dt); });
    queue_.dispatch();
}

std::string Runtime::diagnostics() const {
    std::string s;
    char buf[256];
    std::snprintf(buf, sizeof buf, "GARE: kare %llu, sabit adım %llu (%.4f s), sim zamanı %.2f s, hız x%.2f%s, atılan %llu s\n",
                  static_cast<unsigned long long>(stats_.frames), static_cast<unsigned long long>(stats_.fixed_steps), fixed_step_,
                  stats_.sim_time_s, time_scale_, paused_ ? " (duraklatıldı)" : "",
                  static_cast<unsigned long long>(stats_.dropped_sim_s));
    s += buf;
    for (const auto* m : order_) {
        auto it = timings_.find(m->name());
        if (it == timings_.end()) continue;
        std::snprintf(buf, sizeof buf, "  %-20s çağrı %8llu  toplam %9.3f ms  son %7.3f ms\n", m->name().c_str(),
                      static_cast<unsigned long long>(it->second.calls), it->second.total_ms, it->second.last_ms);
        s += buf;
    }
    return s;
}

}  // namespace kozmo::gare

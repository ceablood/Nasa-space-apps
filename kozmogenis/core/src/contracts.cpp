#include "kozmo/contracts.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::contracts {

const char* to_string(Destination d) {
    switch (d) {
        case Destination::LEO: return "Alçak Dünya yörüngesi";
        case Destination::SSO: return "Güneş-eşzamanlı yörünge";
        case Destination::GTO: return "Yer-eşzamanlı transfer yörüngesi";
        case Destination::Moon: return "Ay yüzeyi";
    }
    return "?";
}

const char* to_string(Status_ s) {
    switch (s) {
        case Status_::Offered: return "Teklif";
        case Status_::Accepted: return "Kabul edildi";
        case Status_::Completed: return "Tamamlandı";
        case Status_::Failed: return "Başarısız";
        case Status_::Expired: return "Süresi doldu";
    }
    return "?";
}

double price_usd_per_kg(Destination d, bool rideshare) {
    switch (d) {
        case Destination::LEO: return rideshare ? 5500 : 2900;
        case Destination::SSO: return rideshare ? 6000 : 3300;
        case Destination::GTO: return 7500;
        case Destination::Moon: return 1.0e6;   // NASA CLPS mertebesi
    }
    return 3000;
}

void Board::refresh(double day, int slots, Rng& rng) {
    int open = 0;
    for (const auto& c : list_) open += c.status == Status_::Offered;
    static const char* clients[] = {"Anadolu Telekom", "Boğaziçi Üniversitesi", "Kapadokya Uydu", "Ege Hava Gözlem", "Orbit Lojistik", "Ay Bilim Konsorsiyumu"};
    while (open < slots) {
        Contract c{};
        c.id = next_id_++;
        c.client = clients[rng.range(0, 5)];
        const double r = rng.uniform();
        c.dest = r < 0.45 ? Destination::LEO : (r < 0.7 ? Destination::SSO : (r < 0.93 ? Destination::GTO : Destination::Moon));
        c.rideshare = c.dest != Destination::GTO && c.dest != Destination::Moon && rng.chance(0.4);
        c.payload_t = c.dest == Destination::Moon ? rng.uniform(0.1, 1.5) : (c.rideshare ? rng.uniform(0.05, 0.8) : rng.uniform(1.0, 15.0));
        c.offered_day = day;
        c.deadline_day = day + rng.uniform(60, 240);
        // ödül: piyasa fiyatı x itibar primi (0.8..1.2)
        c.reward = c.payload_t * 1000.0 * price_usd_per_kg(c.dest, c.rideshare) / 1000.0 * (0.8 + 0.4 * reputation_);
        c.penalty = 0.2 * c.reward;
        list_.push_back(c);
        ++open;
    }
}

Status Board::accept(int id, int max_active) {
    int active = 0;
    for (const auto& c : list_) active += c.status == Status_::Accepted;
    for (auto& c : list_)
        if (c.id == id) {
            if (c.status != Status_::Offered) return make_error(ErrorCode::Infeasible, "Teklif açık değil");
            if (active >= max_active) return make_error(ErrorCode::Infeasible, "Görev kontrol kapasitesi dolu (" + std::to_string(max_active) + ")");
            c.status = Status_::Accepted;
            return ok_status();
        }
    return make_error(ErrorCode::NotFound, "Sözleşme yok");
}

Result<double> Board::fulfil(int id, double capacity_t, double day, econ::Wallet& w) {
    for (auto& c : list_)
        if (c.id == id) {
            if (c.status != Status_::Accepted) return make_error(ErrorCode::Infeasible, "Sözleşme kabul edilmemiş");
            if (capacity_t < c.payload_t) return make_error(ErrorCode::Infeasible, "Roket kapasitesi yetersiz");
            double pay = c.reward;
            if (day > c.deadline_day) pay -= c.penalty;
            w.earn(pay, "Sözleşme: " + c.client, day);
            c.status = Status_::Completed;
            reputation_ = std::min(1.0, reputation_ + (day > c.deadline_day ? 0.01 : 0.05));
            return pay;
        }
    return make_error(ErrorCode::NotFound, "Sözleşme yok");
}

std::vector<std::string> Board::expire(double day, econ::Wallet& w) {
    std::vector<std::string> out;
    for (auto& c : list_) {
        if (day <= c.deadline_day + 30) continue;   // 30 gün tolerans (gecikmeli teslim cezalı)
        if (c.status == Status_::Accepted) {
            (void)w.spend(c.penalty, "Sözleşme cezası: " + c.client, day);
            c.status = Status_::Failed;
            reputation_ = std::max(0.0, reputation_ - 0.1);
            out.push_back(c.client + " sözleşmesi başarısız: ceza ödendi");
        } else if (c.status == Status_::Offered) {
            c.status = Status_::Expired;
        }
    }
    return out;
}

json::Value Board::to_json() const {
    json::Value v = json::Value::object();
    json::Value a = json::Value::array();
    for (const auto& c : list_) {
        json::Value o = json::Value::object();
        o.set("id", c.id);
        o.set("client", c.client);
        o.set("dest", static_cast<int>(c.dest));
        o.set("t", c.payload_t);
        o.set("rs", c.rideshare);
        o.set("o", c.offered_day);
        o.set("d", c.deadline_day);
        o.set("r", c.reward);
        o.set("p", c.penalty);
        o.set("s", static_cast<int>(c.status));
        a.push(o);
    }
    v.set("list", a);
    v.set("next", next_id_);
    v.set("rep", reputation_);
    return v;
}

Status Board::from_json(const json::Value& v) {
    list_.clear();
    for (const auto& o : v["list"].as_array()) {
        const int d = o["dest"].as_int(-1), s = o["s"].as_int(-1);
        if (d < 0 || d > 3 || s < 0 || s > 4) return make_error(ErrorCode::Parse, "Bozuk sözleşme kaydı");
        list_.push_back({o["id"].as_int(), o["client"].as_string(), static_cast<Destination>(d), o["t"].as_number(), o["rs"].as_bool(), o["o"].as_number(),
                         o["d"].as_number(), o["r"].as_number(), o["p"].as_number(), static_cast<Status_>(s)});
    }
    next_id_ = v["next"].as_int(1);
    reputation_ = v["rep"].as_number(0.5);
    return ok_status();
}

}  // namespace kozmo::contracts

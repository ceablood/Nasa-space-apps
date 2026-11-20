#include "kozmo/economy.hpp"

#include <algorithm>
#include <cmath>

namespace kozmo::econ {

namespace {
const std::vector<Commodity>& table() {
    // Oyun varsayımı: Dünya'dan fırlatma maliyeti yüksek olduğundan yerinde üretilebilen su/oksijen/yakıt
    // değerlidir; nadir malzemeler (He-3) çok pahalıdır.
    static const std::vector<Commodity> t = {
        {"water", "Su", "t", 120.0, 1.2},
        {"oxygen", "Oksijen", "t", 150.0, 1.3},
        {"food", "Gıda", "t", 300.0, 1.5},
        {"regolith", "Regolit", "t", 8.0, 0.6},
        {"iron", "Demir", "t", 60.0, 0.9},
        {"aluminum", "Alüminyum", "t", 110.0, 0.9},
        {"methalox", "Metan/LOX yakıt", "t", 90.0, 1.4},
        {"electronics", "Elektronik", "t", 2400.0, 1.0},
        {"he3", "Helyum-3", "kg", 9000.0, 1.6},
        {"medicine", "İlaç", "t", 5200.0, 1.4},
    };
    return t;
}
}  // namespace

const std::vector<Commodity>& commodities() { return table(); }

Result<const Commodity*> find_commodity(const std::string& key) {
    for (const auto& c : table())
        if (c.key == key) return &c;
    return make_error(ErrorCode::NotFound, "Bilinmeyen emtia: " + key);
}

// ------------------------------------------------------------------------ Wallet
Status Wallet::spend(double amount, const std::string& reason, double now) {
    if (amount < 0) return make_error(ErrorCode::InvalidArgument, "Negatif harcama");
    if (amount > balance_ + 1e-9)
        return make_error(ErrorCode::InsufficientFunds, "Yetersiz bakiye: " + std::to_string(static_cast<long long>(amount)) +
                                                            " gerekli, " + std::to_string(static_cast<long long>(balance_)) + " var");
    balance_ -= amount;
    ledger_.push_back({now, -amount, reason});
    return ok_status();
}

void Wallet::earn(double amount, const std::string& reason, double now) {
    if (amount <= 0) return;
    balance_ += amount;
    ledger_.push_back({now, amount, reason});
}

double Wallet::net_since(double t) const {
    double s = 0;
    for (const auto& e : ledger_)
        if (e.time_days >= t) s += e.amount;
    return s;
}

// ------------------------------------------------------------------------ Market
double price_at(const Commodity& c, const MarketItem& m, double stock) {
    // p = taban * (hedef / stok)^esneklik ; stok -> 0 iken fiyat taban*20 ile sınırlanır
    const double s = std::max(stock, m.target_stock * 0.02);
    const double p = c.base_price * std::pow(m.target_stock / s, c.elasticity);
    return std::clamp(p, c.base_price * 0.1, c.base_price * 20.0);
}

const MarketItem* Market::item(const std::string& k) const {
    auto it = items_.find(k);
    return it == items_.end() ? nullptr : &it->second;
}

MarketItem* Market::item_mut(const std::string& k) {
    auto it = items_.find(k);
    return it == items_.end() ? nullptr : &it->second;
}

Result<double> Market::price(const std::string& k) const {
    auto c = find_commodity(k);
    if (!c) return c.error();
    const MarketItem* m = item(k);
    if (!m) return make_error(ErrorCode::NotFound, name_ + " piyasasında " + c.value()->name_tr + " işlem görmüyor");
    return price_at(*c.value(), *m, m->stock);
}

Result<double> Market::quote(const std::string& k, double qty, bool buying) const {
    if (qty <= 0) return make_error(ErrorCode::InvalidArgument, "Miktar pozitif olmalı");
    auto c = find_commodity(k);
    if (!c) return c.error();
    const MarketItem* m = item(k);
    if (!m) return make_error(ErrorCode::NotFound, "Piyasada yok: " + k);
    if (buying && qty > m->stock + 1e-9) return make_error(ErrorCode::InsufficientResources, "Piyasada yeterli stok yok");
    // fiyat stokla sürekli değiştiğinden 32 adımlı orta nokta integrali
    const int n = 32;
    const double step = qty / n;
    double total = 0;
    for (int i = 0; i < n; ++i) {
        const double s = buying ? m->stock - step * (i + 0.5) : m->stock + step * (i + 0.5);
        total += price_at(*c.value(), *m, s) * step;
    }
    // alış-satış makası %4 (oyun varsayımı)
    return buying ? total * 1.02 : total * 0.98;
}

Result<Trade> Market::buy(const std::string& k, double qty, Wallet& w, double now) {
    auto q = quote(k, qty, true);
    if (!q) return q.error();
    auto st = w.spend(q.value(), "Alış: " + k + " @ " + name_, now);
    if (!st) return st.error();
    item_mut(k)->stock -= qty;
    return Trade{id_, k, qty, q.value() / qty, q.value()};
}

Result<Trade> Market::sell(const std::string& k, double qty, Wallet& w, double now) {
    auto q = quote(k, qty, false);
    if (!q) return q.error();
    item_mut(k)->stock += qty;
    w.earn(q.value(), "Satış: " + k + " @ " + name_, now);
    return Trade{id_, k, -qty, q.value() / qty, q.value()};
}

void Market::tick(double days) {
    for (auto& [k, m] : items_) {
        m.stock = std::max(0.0, m.stock + (m.production - m.consumption) * days);
    }
}

}  // namespace kozmo::econ

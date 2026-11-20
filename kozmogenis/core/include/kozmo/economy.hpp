// KozmoCore — ekonomi: emtialar, arz-talebe duyarlı piyasalar, cüzdan ve hesap defteri.
// Fiyat modeli ve taban fiyatlar oyun varsayımıdır (gerçek piyasa verisi değildir).
#pragma once

#include <map>
#include <string>
#include <vector>

#include "kozmo/core.hpp"

namespace kozmo::econ {

struct Commodity {
    std::string key;
    std::string name_tr;
    std::string unit;          // "t", "kg", "adet"
    double base_price;         // kredi / birim (oyun varsayımı)
    double elasticity;         // fiyatın stok oranına duyarlılığı
};

const std::vector<Commodity>& commodities();
Result<const Commodity*> find_commodity(const std::string& key);

// ------------------------------------------------------------------------ cüzdan / defter
struct LedgerEntry {
    double time_days;
    double amount;            // + gelir, - gider
    std::string reason;
};

class Wallet {
public:
    explicit Wallet(double credits = 0.0) : balance_(credits) {}
    double balance() const { return balance_; }
    Status spend(double amount, const std::string& reason, double now_days);
    void earn(double amount, const std::string& reason, double now_days);
    const std::vector<LedgerEntry>& ledger() const { return ledger_; }
    double net_since(double t_days) const;

private:
    double balance_;
    std::vector<LedgerEntry> ledger_;
};

// ------------------------------------------------------------------------ piyasa
struct MarketItem {
    double stock = 0.0;          // piyasadaki mevcut miktar
    double target_stock = 100.0; // "dengedeki" stok; fiyat bu orana göre değişir
    double production = 0.0;     // birim / gün (yerel üretim)
    double consumption = 0.0;    // birim / gün (yerel tüketim)
};

struct Trade {
    std::string market, commodity;
    double qty;          // + alış (oyuncu satın aldı), - satış
    double unit_price;
    double total;
};

class Market {
public:
    Market() = default;
    Market(std::string id, std::string name_tr) : id_(std::move(id)), name_(std::move(name_tr)) {}
    const std::string& id() const { return id_; }
    const std::string& name() const { return name_; }

    void set_item(const std::string& commodity, MarketItem item) { items_[commodity] = item; }
    const MarketItem* item(const std::string& commodity) const;
    MarketItem* item_mut(const std::string& commodity);
    const std::map<std::string, MarketItem>& items() const { return items_; }

    // Anlık birim fiyat (stok azaldıkça artar). Kenar fiyatı; büyük işlemler ortalama fiyattan hesaplanır.
    Result<double> price(const std::string& commodity) const;
    // qty birimlik alış/satışın toplam tutarı (fiyat kayması dahil, sayısal integral)
    Result<double> quote(const std::string& commodity, double qty, bool buying) const;

    Result<Trade> buy(const std::string& commodity, double qty, Wallet& w, double now_days);
    Result<Trade> sell(const std::string& commodity, double qty, Wallet& w, double now_days);

    // Zaman ilerlemesi: üretim/tüketim stoğu değiştirir; stok asla negatif olmaz.
    void tick(double days);

private:
    std::string id_, name_;
    std::map<std::string, MarketItem> items_;
};

double price_at(const Commodity& c, const MarketItem& m, double stock);

}  // namespace kozmo::econ

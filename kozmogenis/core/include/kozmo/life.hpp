// KozmoCore — gezilebilir koloni yerleşimi ve yaşayan NPC zekâsı (V41 §4, §5, §6.3).
//
// Tek doğruluk kaynağı: kolonistin ihtiyaçları, mesleği, etkinliği ve kişiliği colony::Colony'dedir.
// Bu katman onların ÜSTÜNE mekân (bina, konum, yürüyüş), algılama, öncelik, hafıza, ilişki, sosyal
// etkileşim, olay tepkisi, diyalog ve simülasyon ayrıntı düzeyini (LOD) ekler. Alarm/tahliye/onarım
// emirleri Colony::order ile ekonomiye yansır (çalışmayan işçi üretmez).
//
// Gerçek: yürüme hızı Froude benzerliğiyle yerçekimine bağlı, v = sqrt(Fr g L), Fr ~0.25, L ~0.9 m
// (Dünya ~1.5 m/s, Mars ~0.9, Ay ~0.6 — Apollo yürüyüşleriyle uyumlu). Diğer katsayılar oyun varsayımı.
#pragma once

#include <map>
#include <string>
#include <utility>
#include <vector>

#include "kozmo/challenge.hpp"
#include "kozmo/colony.hpp"
#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::life {

double walking_speed_ms(double gravity_ms2);

enum class District { LandingPad, Hangar, Admin, Housing, Canteen, Hospital, Lab, Production, Processing, Power, Water, Farm,
                      Storage, Robotics, Training, Social, Security, Airlock };
constexpr int kDistrictCount = 18;
const char* to_string(District d);

struct Interactable {
    std::string id, name, action;   // action: "map", "population", "economy", "security", "missions", "nova", "analyze", ...
};
struct Room {
    std::string name;
    std::vector<Interactable> items;
    int floor = 0;              // 0 zemin; yer altı düzeninde aşağı doğru sayılır (ad olarak "-1. kat")
};
struct Building {
    std::string id;
    District district;
    std::string name;
    double x = 0, y = 0, w = 10, d = 10, h = 4;   // plan konumu (m), boyut
    double door_x = 0, door_y = 0;
    std::vector<Room> rooms;
    bool pressurized = true, shelter = false;
    int capacity = 10;
    bool built = true;          // false: arsa / inşaat alanı (girilemez)
    int floors = 1;
    bool elevator = false;      // true: asansör (enerji gerekir); her katlı binada merdiven de vardır
};

enum class Layout { SurfaceDomes, Underground, Ocean, Polar, Orbital };
const char* to_string(Layout l);

class Settlement {
public:
    Settlement() = default;
    // Koloninin modüllerinden ve gezegen sınıfından yerleşim kurar (18 bölge; koloni modülleri ilgili bölgeye bağlanır)
    static Settlement build(const colony::Colony& c, const challenge::PlanetEnvironment& env);
    // Koloni modüllerine göre hangi bölgelerin inşa edilmiş olduğunu günceller (yeni koloni: yalnız iniş alanı + hava kilidi)
    void refresh(const colony::Colony& c);
    const std::vector<Building>& buildings() const { return buildings_; }
    const Building* find(const std::string& id) const;
    const Building* find(District d) const;
    const Building* at(double x, double y) const;     // nokta hangi binanın içinde
    Layout layout() const { return layout_; }
    double plaza_x() const { return 0; }
    double plaza_y() const { return 0; }
    // kapıdan kapıya yürüyüş yolu (bina içi -> kapı -> meydan/koridor -> hedef kapı -> hedef iç)
    std::vector<std::pair<double, double>> path(double x0, double y0, const Building& to) const;

private:
    std::vector<Building> buildings_;
    Layout layout_ = Layout::SurfaceDomes;
};

struct Memory {
    double day;
    int about;              // 0 = oyuncu, >0 kolonist kimliği, -1 koloni olayı
    std::string text;
    double importance;      // 0..1
    double valence;         // -1 kötü .. +1 iyi
};

struct Relation {
    double affinity = 0.0;   // -1 düşmanlık .. +1 arkadaşlık
    double trust = 0.5, respect = 0.5;
    std::string tie;         // "iş arkadaşı", "ekip", "rakip"
};

enum class Intent { Sleep, Eat, Work, Socialize, Treatment, Idle, Shelter, RespondAlarm, RepairPower, Patrol, Research, TalkToPlayer,
                    Construct, Mission };

// NOVA / oyuncu tarafından verilen görev (§6.3): NOVA genel emir verir, NPC kendi durumuna göre kabul eder ya da sorun bildirir
enum class MissionKind { Repair, Construct, Research, Patrol, Medical, Supply };
const char* to_string(MissionKind k);
struct MissionOrder {
    MissionKind kind;
    colony::Job job;          // görevi yapacak meslek
    District where;
    double hours;
    std::string description;
};
struct MissionReport {
    std::vector<int> accepted;
    std::vector<std::string> problems;   // "Can: çok yorgun (yorgunluk %91)" gibi
};
const char* to_string(Intent i);

enum class Lod { Near, Mid, Far };

enum class ColonyEvent { Alarm, PowerOutage, MeteorThreat, Discovery, DustStorm, AllClear };
const char* to_string(ColonyEvent e);

struct Npc {
    int id = 0;
    double thirst = 0.2, social = 0.3, safety = 1.0, satisfaction = 0.6;   // ek ihtiyaçlar (0..1; safety 1 = güvende)
    Intent intent = Intent::Idle;
    std::string reason;            // karar gerekçesi (5 katmanlı kararın özeti)
    std::string at, target;        // bulunduğu / gittiği bina
    double x = 0, y = 0;
    std::vector<std::pair<double, double>> route;
    Lod lod = Lod::Far;
    double think_in_h = 0;         // sonraki karar
    int shift = 0;                 // 0 gündüz (08-17), 1 akşam (14-23) — vardiya
    int mission = -1;              // etkin görev (MissionKind), -1 yok
    double mission_h = 0;
    std::string mission_site;
    std::vector<Memory> memories;
    bool arrived = true;
};

struct SocietyStats {
    int near = 0, mid = 0, far = 0;
    long decisions = 0;            // toplam karar sayısı (LOD verim ölçüsü)
    std::map<Intent, int> by_intent;
};

class Society {
public:
    static constexpr int kPlayer = 0;
    static constexpr std::size_t kMaxMemories = 12;

    void sync(colony::Colony& c, const Settlement& s, Rng& rng);     // yeni kolonistleri ekler, ölenleri çıkarır
    // dt saat; player_x/y: oyuncunun yerleşimdeki konumu (LOD için; oyuncu yoksa çok uzak bir değer verilir)
    void tick(double dt_h, double day, double local_hour, colony::Colony& c, const Settlement& s, double gravity, double player_x,
              double player_y, Rng& rng);
    void raise(ColonyEvent e, double day, colony::Colony& c, const Settlement& s);
    // görev ata: uygun NPC'ler kabul eder, uygun olmayanlar nedenini bildirir; count: en çok kaç kişi
    MissionReport assign(const MissionOrder& m, int count, double day, colony::Colony& c, const Settlement& s);
    // inşaat sahası (bina kimliği; boş = yok). Mühendisler iş saatinde sahada çalışır.
    void set_construction_site(const std::string& building_id) { site_ = building_id; }
    double take_construction_labor();      // son çağrıdan beri üretilen emek-saat
    bool alarm() const { return alarm_; }
    ColonyEvent last_event() const { return last_event_; }

    // diyalog: konu "selam" "nasılsın" "iş" "koloni" "yardım" "teşekkür"
    Result<std::string> talk(int npc_id, const std::string& topic, double day, colony::Colony& c);
    void remember(Npc& n, Memory m);
    Relation& relation(int a, int b);
    const Relation* find_relation(int a, int b) const;

    const std::vector<Npc>& npcs() const { return npcs_; }
    Npc* npc(int id);
    const Npc* npc(int id) const;
    SocietyStats stats() const;
    // NOVA için: insan kaynaklı sorunlar (hasta mühendis, doz sınırı, düşük moral ...)
    std::vector<std::string> issues(const colony::Colony& c) const;

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    void decide(Npc& n, colony::Colonist& c, colony::Colony& col, const Settlement& s, double hour);
    void move(Npc& n, double dt_h, double speed_ms);
    void socialize(double day, Rng& rng, const colony::Colony& c);
    std::vector<Npc> npcs_;
    std::map<std::pair<int, int>, Relation> relations_;
    bool alarm_ = false;
    ColonyEvent last_event_ = ColonyEvent::AllClear;
    long decisions_ = 0;
    double social_timer_h_ = 0;
    std::string site_;
    double labor_h_ = 0;
};

// Üretim teşhisi (V41 §6.2 "Neden üretim yavaşladı?"): tesis -> personel -> enerji/girdi -> eksik -> öneri
struct Diagnosis {
    std::vector<std::string> findings;
    std::vector<std::string> suggestions;
    double average_efficiency = 1.0;
};
Diagnosis diagnose_production(const colony::Colony& c);

}  // namespace kozmo::life

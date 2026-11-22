// KozmoCore — astronot kadrosu, eğitim ve görev ekibi (V30 §22 ekip/haklar, V41 §5.5 meslekler).
//
// Gerçek / yaklaşık:
//   * NASA astronot adayı temel eğitimi ~2 yıl (ASCAN); EVA eğitimi Nötr Yüzerlik Laboratuvarı'nda (NBL) her
//     1 saatlik EVA için ~7 saat havuz (yaygın kural); NASA kariyer dozu sınırı 600 mSv (NASA-STD-3001, 2022)
//   * Ekip rolleri: komutan, pilot, uçuş mühendisi, görev uzmanı, sağlık sorumlusu (uzun görevlerde zorunlu)
// Ders süreleri, beceri artış hızları ve rütbe eşikleri OYUN VARSAYIMIDIR.
#pragma once

#include <array>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "kozmo/core.hpp"
#include "kozmo/json.hpp"

namespace kozmo::crew {

enum class Skill { Piloting, Eva, Science, Medicine, Engineering, Geology, Leadership };
constexpr int kSkillCount = 7;
const char* to_string(Skill s);

enum class Role { Commander, Pilot, FlightEngineer, MissionSpecialist, MedicalOfficer };
const char* to_string(Role r);

struct Course {
    std::string key, name;
    double hours;
    std::vector<std::string> prerequisites;
    std::map<Skill, double> gains;      // tamamlanınca beceri artışı (0..1 ölçek)
    std::string certification;          // verilen sertifika ("" yok)
};
const std::vector<Course>& courses();
Result<const Course*> find_course(const std::string& key);

struct Astronaut {
    int id = 0;
    std::string name;
    std::array<double, kSkillCount> skill{};
    std::set<std::string> certifications;
    std::set<std::string> completed;
    std::string training;               // yürüyen ders
    double training_left_h = 0;
    double flight_days = 0, eva_hours = 0, dose_msv = 0;
    int missions = 0;
    double fatigue = 0;                 // 0..1
    std::string rank() const;
    double get(Skill s) const { return skill[static_cast<int>(s)]; }
};

struct Requirement {
    Role role;
    int count;
};

struct CrewCheck {
    bool ok = true;
    std::vector<std::string> problems;
    std::map<Role, std::vector<int>> assignment;
};

class Roster {
public:
    int hire(const std::string& name, Rng& rng);
    Astronaut* find(int id);
    const Astronaut* find(int id) const;
    const std::vector<Astronaut>& astronauts() const { return list_; }

    Status enroll(int id, const std::string& course);
    // eğitim saati ilerlet (yorgunluk artar); tamamlanan dersleri döner ("ad: ders")
    std::vector<std::string> train(double hours);
    void rest(double hours);
    // EVA / görev kaydı: doz ve saat; kariyer sınırı aşılırsa uçuştan çekilir
    Status log_eva(int id, double hours, double dose_msv);
    Status log_mission(const std::vector<int>& ids, double days, double dose_per_day_msv);

    bool eligible(const Astronaut& a, Role r) const;
    // görev için ekip seç: uzun görev (>30 gün) sağlık sorumlusu ister; EVA'lı görev EVA sertifikası ister
    CrewCheck select(const std::vector<Requirement>& req, double mission_days, bool eva) const;

    json::Value to_json() const;
    Status from_json(const json::Value& v);

private:
    std::vector<Astronaut> list_;
    int next_id_ = 1;
};

std::vector<Requirement> standard_crew(double mission_days);   // 4 kişilik temel ekip

}  // namespace kozmo::crew

// KOZMOGENİS — KozmoCore oyun çekirdeğini Unreal Engine'e bağlayan GameInstance alt sistemi.
// Oyun durumu (zaman, görevler, koloniler, NPC'ler, ekonomi, araştırma) tamamen çekirdektedir;
// bu sınıf zamanı ilerletir, olayları Blueprint/Slate'e iletir ve kaydı Saved/ klasörüne yazar.
#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/flight.hpp"
#include "kozmo/game.hpp"
#include "kozmo/nova.hpp"
#include "kozmo/universe.hpp"
#include "kozmo/vehicle.hpp"
#include "kozmo/world.hpp"
#include "kozmo/agency.hpp"
#include "kozmo/civ.hpp"
#include "kozmo/contracts.hpp"
#include "kozmo/crew.hpp"
#include "kozmo/progression.hpp"
#include "kozmo/satellites.hpp"
#include "kozmo/settings.hpp"
#include "kozmo/station.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmoGraphics.h"
#include "KozmoSubsystem.generated.h"

DECLARE_LOG_CATEGORY_EXTERN(LogKozmo, Log, All);

USTRUCT(BlueprintType)
struct FKozmoColonySummary
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FString Id;
	UPROPERTY(BlueprintReadOnly) FString Body;
	UPROPERTY(BlueprintReadOnly) int32 Population = 0;
	UPROPERTY(BlueprintReadOnly) int32 Housing = 0;
	UPROPERTY(BlueprintReadOnly) float Morale = 0.f;
	UPROPERTY(BlueprintReadOnly) float OxygenT = 0.f;
	UPROPERTY(BlueprintReadOnly) float WaterT = 0.f;
	UPROPERTY(BlueprintReadOnly) float FoodT = 0.f;
	UPROPERTY(BlueprintReadOnly) float SolarFluxWm2 = 0.f;
};

USTRUCT(BlueprintType)
struct FKozmoBodyInfo
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FString Key;
	UPROPERTY(BlueprintReadOnly) FString Name;
	UPROPERTY(BlueprintReadOnly) FString Parent;
	UPROPERTY(BlueprintReadOnly) float DiameterKm = 0.f;
	UPROPERTY(BlueprintReadOnly) float DistanceMkm = 0.f;
	UPROPERTY(BlueprintReadOnly) float PeriodDays = 0.f;
	UPROPERTY(BlueprintReadOnly) float GravityMs2 = 0.f;
	UPROPERTY(BlueprintReadOnly) float MeanTempC = 0.f;
	UPROPERTY(BlueprintReadOnly) int32 Moons = 0;
	UPROPERTY(BlueprintReadOnly) FString Source;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FKozmoMessageSignature, const FString&, Message);
DECLARE_MULTICAST_DELEGATE_OneParam(FKozmoDesignChanged, const kozmo::prop::Design&);

UCLASS()
class KOZMOGENIS_API UKozmoSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	UFUNCTION(BlueprintCallable, Category = "Kozmo") void NewGame(const FString& Agency);
	UFUNCTION(BlueprintCallable, Category = "Kozmo") void SetTimeScale(float InDaysPerSecond);
	UFUNCTION(BlueprintPure, Category = "Kozmo") float GetTimeScale() const { return DaysPerSecond; }
	UFUNCTION(BlueprintPure, Category = "Kozmo") double GetDay() const;
	UFUNCTION(BlueprintPure, Category = "Kozmo") double GetCredits() const;

	/** Ağır roketle 3 kişilik koloni kiti fırlatır. Başarıda boş metin, aksi halde hata nedeni döner. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo") FString LaunchColonyKit(const FString& Target);
	/** Ağır roket tasarımının hedef için analizini insan okunur metin olarak döner. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo") FString EvaluateHeavyRocket(const FString& Target, float PayloadT, int32 Crew) const;
	UFUNCTION(BlueprintCallable, Category = "Kozmo") FString StartResearch(const FString& TechKey);
	UFUNCTION(BlueprintPure, Category = "Kozmo") FString GetWindowText(const FString& Target) const;

	UFUNCTION(BlueprintPure, Category = "Kozmo") TArray<FKozmoColonySummary> GetColonies() const;
	UFUNCTION(BlueprintPure, Category = "Kozmo") TArray<FKozmoBodyInfo> GetBodies() const;
	UFUNCTION(BlueprintPure, Category = "Kozmo") float GetBodyLongitudeDeg(const FString& Key) const;
	UFUNCTION(BlueprintPure, Category = "Kozmo") FString GetStatusText() const;

	/** NOVA'ya Türkçe soru/komut. Kaynak harcayan işlemler "onayla" denene kadar uygulanmaz. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|NOVA") FString AskNova(const FString& Text);
	UFUNCTION(BlueprintPure, Category = "Kozmo|NOVA") TArray<FString> GetNovaWarnings() const;
	/** Hafif/ağır roketin fiziksel fırlatma simülasyonu (atmosfer, kademeler, yörünge); özet metin döner. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Flight") FString SimulateAscent(bool bHeavy, float PayloadT);

	/** Tohumlu prosedürel galaksiden en iyi koloni adaylarını metin olarak döner. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Universe") FString DescribeGalaxy(int64 Seed, int32 Systems);

	// --- Roket tasarımcısı (V30 §13): tek tasarım üzerinde gerçek çekirdek analizi ---
	/** Hazır tasarım yükler: "f9" (Falcon 9 sınıfı), "heavy" (metan/LOX ağır), "f9_srb" (F9 + 2 katı güçlendirici). */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void LoadPresetDesign(const FString& Preset);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void CycleStageEngine(int32 Stage, int32 Direction);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void AdjustStage(int32 Stage, int32 EngineDelta, float PropellantFactor, float DiameterDelta);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void AddStage();
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void RemoveTopStage();
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void AdjustBoosters(int32 CountDelta, float PropellantDeltaT);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void AdjustPayload(float DeltaT);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Designer") void CycleTarget();
	/** Analiz (delta-v, TWR, başarı, maliyet) + gövde geometrisi (boy, kütle/basınç merkezi) metni. */
	UFUNCTION(BlueprintPure, Category = "Kozmo|Designer") FString GetDesignReport() const;
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Flight") FString SimulateDesignAscent() const;
	const kozmo::prop::Design& GetDesign() const { return Design; }
	FKozmoDesignChanged OnDesignChanged;

	// --- V41 dikey dilim: ayrı senaryo oyunu (kampanyayı etkilemez) ---
	/** Ay ("moon", gezilebilir 8 kişilik koloniyle) ya da Mars ("mars", iniş + çevre) seferi başlatır. Hata metni ya da boş. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Expedition") FString StartExpedition(const FString& Body, bool bInOrbit = true);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Expedition") void EndExpedition();
	UFUNCTION(BlueprintPure, Category = "Kozmo|Expedition") bool HasExpedition() const { return Expedition.IsValid(); }
	/** Sefer zaman ölçeği (oyun saniyesi / gerçek saniye). Uçuş ve yürüyüş 1, bekleme için yükseltilebilir. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Expedition") void SetExpeditionTimeScale(float Scale) { ExpeditionTimeScale = FMath::Clamp(Scale, 0.f, 3600.f); }
	kozmo::world::Expedition* GetExpedition() { return Expedition.Get(); }
	const kozmo::world::Expedition* GetExpedition() const { return Expedition.Get(); }

	// --- Yönetim katmanı: ajans üssü, sözleşmeler, uydular, ekip, medeniyet, istasyon (çekirdekte test edildi) ---
	kozmo::agency::Base& Base() { return AgencyBase; }
	kozmo::contracts::Board& Contracts() { return ContractBoard; }
	kozmo::sats::Fleet& Fleet() { return SatFleet; }
	kozmo::crew::Roster& Roster() { return CrewRoster; }
	kozmo::civ::Civilization& Civ() { return Civilization; }
	kozmo::station::Station& Station() { return *OrbitalStation; }
	kozmo::progress::Tracker& Achievements() { return AchievementTracker; }
	kozmo::progress::Tutorial& Tutorial() { return TutorialSteps; }
	kozmo::progress::News& News() { return NewsFeed; }
	kozmo::settings::Settings& Settings() { return UserSettings; }
	/** Ayarları doğrular, uygular (grafik/kamera/ses) ve Saved/kozmo_ayarlar.json dosyasına yazar. */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Settings") FString ApplySettings();
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Settings") void LoadSettings();
	/** Yönetim özet metni (ajans, sözleşmeler, uydular, medeniyet) — panel için */
	UFUNCTION(BlueprintPure, Category = "Kozmo|Management") FString GetManagementText() const;
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Management") FString UpgradeFacility(int32 Facility);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Management") FString AcceptContract(int32 Id);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Management") FString LaunchConstellation(int32 Purpose, int32 Orbit, int32 Count);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Management") FString HireAstronaut(const FString& Name);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Management") FString SetPolicy(int32 Policy);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Management") FString PlanMission(const FString& Target, int32 Crew);

	// --- Grafik kalite profilleri (V30 §27) ---
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Graphics") void SetQuality(EKozmoQuality Q);
	UFUNCTION(BlueprintPure, Category = "Kozmo|Graphics") FString GetQualityText() const;

	UFUNCTION(BlueprintCallable, Category = "Kozmo") bool SaveToSlot(const FString& SlotName);
	UFUNCTION(BlueprintCallable, Category = "Kozmo") FString LoadFromSlot(const FString& SlotName);

	UPROPERTY(BlueprintAssignable, Category = "Kozmo") FKozmoMessageSignature OnMessage;

	const TArray<FString>& GetRecentMessages() const { return Messages; }
	kozmo::Game& GetGame() { return *Game; }

private:
	bool TickGame(float DeltaTime);
	void Push(const FString& Msg);
	void SubscribeEvents();
	FString SlotPath(const FString& SlotName) const;

	TUniquePtr<kozmo::Game> Game;
	TUniquePtr<kozmo::nova::Nova> Nova;
	float DaysPerSecond = 0.25f;
	FTSTicker::FDelegateHandle TickHandle;
	TArray<FString> Messages;
	kozmo::prop::Design Design;
	TUniquePtr<kozmo::Game> SliceGame;
	TUniquePtr<kozmo::world::Expedition> Expedition;
	TUniquePtr<kozmo::nova::Nova> SliceNova;
	float ExpeditionTimeScale = 1.f;
	kozmo::agency::Base AgencyBase;
	kozmo::contracts::Board ContractBoard;
	kozmo::sats::Fleet SatFleet;
	kozmo::crew::Roster CrewRoster;
	kozmo::civ::Civilization Civilization;
	TUniquePtr<kozmo::station::Station> OrbitalStation;
	kozmo::progress::Tracker AchievementTracker;
	kozmo::progress::Tutorial TutorialSteps;
	kozmo::progress::News NewsFeed;
	kozmo::settings::Settings UserSettings;
	kozmo::Rng MgmtRng{20300101};
	double LastManagedDay = 0;
	void ManageDaily();
	FString SettingsPath() const;
	FString QualityReason;
	void DesignChanged();
};

/** std::string (UTF-8) <-> FString dönüşümleri */
inline FString KozmoStr(const std::string& S) { return FString(UTF8_TO_TCHAR(S.c_str())); }
inline std::string KozmoStd(const FString& S) { return std::string(TCHAR_TO_UTF8(*S)); }

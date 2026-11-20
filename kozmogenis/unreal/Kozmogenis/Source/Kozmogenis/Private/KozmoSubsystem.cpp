#include "KozmoSubsystem.h"

#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY(LogKozmo);

namespace
{
kozmo::prop::Design HeavyRocket(const std::string& Target, double PayloadT, int Crew)
{
	kozmo::prop::Design D;
	D.name = "Ağır (metan/LOX + hidrojen iniş kademesi)";
	D.stages = {{"methalox_fc", 33, 3400.0, 0.06}, {"methalox_vac", 3, 1200.0, 0.06}, {"hydrolox_exp", 4, 140.0, 0.10}};
	D.payload_t = PayloadT;
	D.crew = Crew;
	D.target = Target;
	D.land = true;
	return D;
}

kozmo::Payload ColonyKit()
{
	using kozmo::colony::Job;
	using kozmo::colony::ModuleType;
	kozmo::Payload P;
	P.modules = {ModuleType::Habitat, ModuleType::Greenhouse, ModuleType::Electrolyzer, ModuleType::SolarArray,
	             ModuleType::SolarArray, ModuleType::Lab};
	P.cargo = {{"water", 3.0}, {"oxygen", 0.3}, {"food", 0.3}};
	P.crew = {{"Ada", Job::Farmer}, {"Can", Job::Engineer}, {"Ece", Job::Scientist}};
	return P;
}
}  // namespace

void UKozmoSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	kozmo::Log::set_sink([](kozmo::LogLevel Level, const std::string& Channel, const std::string& Msg) {
		const FString Line = FString::Printf(TEXT("[%s] %s"), *KozmoStr(Channel), *KozmoStr(Msg));
		if (Level >= kozmo::LogLevel::Warn)
		{
			UE_LOG(LogKozmo, Warning, TEXT("%s"), *Line);
		}
		else
		{
			UE_LOG(LogKozmo, Display, TEXT("%s"), *Line);
		}
	});
	Game = MakeUnique<kozmo::Game>(static_cast<std::uint64_t>(FPlatformTime::Cycles64()));
	SubscribeEvents();
	NewGame(TEXT("AETHER"));
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UKozmoSubsystem::TickGame));
}

void UKozmoSubsystem::Deinitialize()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
	kozmo::Log::set_sink(nullptr);
	Game.Reset();
	Super::Deinitialize();
}

void UKozmoSubsystem::SubscribeEvents()
{
	TWeakObjectPtr<UKozmoSubsystem> Weak(this);
	kozmo::EventBus& Bus = Game->bus();
	Bus.subscribe<kozmo::ColonyFounded>([Weak](const kozmo::ColonyFounded& E) {
		if (Weak.IsValid()) Weak->Push(FString::Printf(TEXT("Koloni kuruldu: %s"), *KozmoStr(E.colony)));
	});
	Bus.subscribe<kozmo::MissionArrived>([Weak](const kozmo::MissionArrived& E) {
		if (Weak.IsValid()) Weak->Push(FString::Printf(TEXT("Görev #%d vardı: %s"), E.id, *KozmoStr(E.target)));
	});
	Bus.subscribe<kozmo::MissionLost>([Weak](const kozmo::MissionLost& E) {
		if (Weak.IsValid()) Weak->Push(FString::Printf(TEXT("Görev #%d kaybedildi: %s"), E.id, *KozmoStr(E.reason)));
	});
	Bus.subscribe<kozmo::colony::ColonistDied>([Weak](const kozmo::colony::ColonistDied& E) {
		if (Weak.IsValid()) Weak->Push(FString::Printf(TEXT("%s hayatını kaybetti (%s)"), *KozmoStr(E.name), *KozmoStr(E.cause)));
	});
	Bus.subscribe<kozmo::research::ResearchCompleted>([Weak](const kozmo::research::ResearchCompleted& E) {
		if (Weak.IsValid()) Weak->Push(FString::Printf(TEXT("Araştırma tamamlandı: %s"), *KozmoStr(E.key)));
	});
}

void UKozmoSubsystem::Push(const FString& Msg)
{
	Messages.Add(FString::Printf(TEXT("Gün %.1f — %s"), GetDay(), *Msg));
	if (Messages.Num() > 50) Messages.RemoveAt(0);
	OnMessage.Broadcast(Msg);
}

void UKozmoSubsystem::NewGame(const FString& Agency)
{
	Game->new_game(KozmoStd(Agency), 3e6);
	// başlangıç: Dünya laboratuvarlarında tamamlanmış kriyojenik ve metan/LOX itki
	for (const char* Key : {"cryo", "methalox"})
	{
		Game->research().start(Key);
		Game->research().add_points(1e6, nullptr);
	}
	Messages.Reset();
	Push(FString::Printf(TEXT("Yeni oyun: %s"), *Agency));
}

void UKozmoSubsystem::SetTimeScale(float InDaysPerSecond) { DaysPerSecond = FMath::Clamp(InDaysPerSecond, 0.f, 50.f); }

double UKozmoSubsystem::GetDay() const { return Game ? Game->day() : 0.0; }
double UKozmoSubsystem::GetCredits() const { return Game ? Game->wallet().balance() : 0.0; }

bool UKozmoSubsystem::TickGame(float DeltaTime)
{
	if (Game && DaysPerSecond > 0.f)
	{
		// kare başına en fazla 2 oyun günü: yavaş karelerde simülasyon patlamasın
		Game->advance(FMath::Min<double>(DeltaTime * DaysPerSecond, 2.0));
	}
	return true;  // ticker kalsın
}

FString UKozmoSubsystem::LaunchColonyKit(const FString& Target)
{
	const kozmo::Payload Kit = ColonyKit();
	auto R = Game->launch(HeavyRocket(KozmoStd(Target), kozmo::payload_mass_t(Kit) + 0.5, 3), Kit);
	if (!R.ok()) return KozmoStr(R.error().message);
	const auto& M = Game->missions().back();
	Push(M.state == kozmo::MissionState::Lost
		? FString::Printf(TEXT("Görev #%d fırlatmada kaybedildi"), M.id)
		: FString::Printf(TEXT("Görev #%d fırlatıldı, varış %.1f gün sonra"), M.id, M.arrive_day - M.depart_day));
	return FString();
}

FString UKozmoSubsystem::EvaluateHeavyRocket(const FString& Target, float PayloadT, int32 Crew) const
{
	auto R = Game->evaluate(HeavyRocket(KozmoStd(Target), PayloadT, Crew));
	if (!R.ok()) return KozmoStr(R.error().message);
	const kozmo::prop::Report& Rep = R.value();
	FString S = FString::Printf(TEXT("Kalkış %.0f t, TWR %.2f, delta-v %.2f/%.2f km/s, başarı %%%.1f, maliyet %.0f bin"),
		Rep.liftoff_mass_t, Rep.liftoff_twr, Rep.total_dv_ms / 1000.0, Rep.required_dv_ms / 1000.0, Rep.success_p * 100.0,
		Rep.cost_mcr);
	for (const std::string& P : Rep.problems) S += TEXT("\n! ") + KozmoStr(P);
	return S;
}

FString UKozmoSubsystem::StartResearch(const FString& TechKey)
{
	auto R = Game->research().start(KozmoStd(TechKey));
	return R.ok() ? FString() : KozmoStr(R.error().message);
}

FString UKozmoSubsystem::GetWindowText(const FString& Target) const
{
	auto W = Game->window_to(KozmoStd(Target));
	if (!W.ok()) return KozmoStr(W.error().message);
	return FString::Printf(TEXT("%s penceresi: %.0f gün sonra (faz %.0f°, gereken %.0f°)"), *Target, W.value().days_until,
		W.value().current_phase_deg, W.value().required_phase_deg);
}

TArray<FKozmoColonySummary> UKozmoSubsystem::GetColonies() const
{
	TArray<FKozmoColonySummary> Out;
	for (const auto& [Id, C] : Game->colonies())
	{
		FKozmoColonySummary S;
		S.Id = KozmoStr(Id);
		S.Body = KozmoStr(C.body());
		S.Population = C.population();
		S.Housing = C.housing();
		S.Morale = static_cast<float>(C.average_morale());
		S.OxygenT = static_cast<float>(C.resource("oxygen"));
		S.WaterT = static_cast<float>(C.resource("water"));
		S.FoodT = static_cast<float>(C.resource("food"));
		S.SolarFluxWm2 = static_cast<float>(C.solar_flux());
		Out.Add(S);
	}
	return Out;
}

TArray<FKozmoBodyInfo> UKozmoSubsystem::GetBodies() const
{
	TArray<FKozmoBodyInfo> Out;
	for (const kozmo::astro::Body& B : kozmo::astro::bodies())
	{
		FKozmoBodyInfo I;
		I.Key = KozmoStr(B.key);
		I.Name = KozmoStr(B.name_tr);
		I.Parent = KozmoStr(B.parent);
		I.DiameterKm = static_cast<float>(B.diameter_km);
		I.DistanceMkm = static_cast<float>(B.distance_1e6km);
		I.PeriodDays = static_cast<float>(B.period_days);
		I.GravityMs2 = static_cast<float>(B.gravity_ms2);
		I.MeanTempC = static_cast<float>(B.mean_temp_c);
		I.Moons = B.moons;
		I.Source = KozmoStr(kozmo::astro::to_string(B.source));
		Out.Add(I);
	}
	return Out;
}

float UKozmoSubsystem::GetBodyLongitudeDeg(const FString& Key) const
{
	const std::string K = KozmoStd(Key);
	if (K == "moon") return static_cast<float>(FMath::Fmod(GetDay() / 27.3 * 360.0, 360.0));   // Dünya çevresinde
	return static_cast<float>(Game->longitude(K));
}

FString UKozmoSubsystem::GetStatusText() const
{
	FString S = FString::Printf(TEXT("%s  |  Gün %.1f  |  %.0f kredi  |  Zaman x%.2f gün/sn\n"), *KozmoStr(Game->agency()), GetDay(),
		GetCredits(), DaysPerSecond);
	const auto& T = Game->research();
	S += FString::Printf(TEXT("Araştırma: %s"), T.active().empty() ? TEXT("(yok)") : *KozmoStr(T.active()));
	if (!T.active().empty()) S += FString::Printf(TEXT(" %%%.0f"), T.progress() * 100.0);
	S += TEXT("\n");
	for (const auto& M : Game->missions())
	{
		if (M.state != kozmo::MissionState::InTransit) continue;
		S += FString::Printf(TEXT("Görev #%d -> %s, varışa %.1f gün\n"), M.id, *KozmoStr(M.target), M.arrive_day - GetDay());
	}
	for (const FKozmoColonySummary& C : GetColonies())
	{
		S += FString::Printf(TEXT("%s: nüfus %d/%d, moral %.2f, O2 %.2f t, su %.2f t, gıda %.2f t\n"), *C.Id, C.Population,
			C.Housing, C.Morale, C.OxygenT, C.WaterT, C.FoodT);
	}
	return S;
}

FString UKozmoSubsystem::SlotPath(const FString& SlotName) const
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Kozmo"), SlotName + TEXT(".json"));
}

bool UKozmoSubsystem::SaveToSlot(const FString& SlotName)
{
	const bool bOk = FFileHelper::SaveStringToFile(KozmoStr(Game->save()), *SlotPath(SlotName),
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	Push(bOk ? FString::Printf(TEXT("Kaydedildi: %s"), *SlotName) : TEXT("Kayıt yazılamadı"));
	return bOk;
}

FString UKozmoSubsystem::LoadFromSlot(const FString& SlotName)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *SlotPath(SlotName))) return TEXT("Kayıt bulunamadı");
	auto R = Game->load(KozmoStd(Text));
	if (!R.ok()) return KozmoStr(R.error().message);
	Push(FString::Printf(TEXT("Yüklendi: %s"), *SlotName));
	return FString();
}

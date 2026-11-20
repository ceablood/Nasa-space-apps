#include "KozmoSubsystem.h"

#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY(LogKozmo);

namespace
{
// Hazır tasarımlar çekirdekte tek yerde tanımlıdır (kozmo/game.hpp)
kozmo::prop::Design HeavyRocket(const std::string& Target, double PayloadT, int Crew)
{
	return kozmo::preset_heavy_rocket(Target, PayloadT, Crew);
}
kozmo::Payload ColonyKit() { return kozmo::standard_colony_kit(); }
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
	Nova = MakeUnique<kozmo::nova::Nova>(*Game);      // Game nesnesi yeni oyun/yüklemede yerinde güncellenir
	SubscribeEvents();
	NewGame(TEXT("AETHER"));
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UKozmoSubsystem::TickGame));
}

void UKozmoSubsystem::Deinitialize()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
	kozmo::Log::set_sink(nullptr);
	Nova.Reset();
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

FString UKozmoSubsystem::AskNova(const FString& Text)
{
	const kozmo::nova::Reply R = Nova->ask(KozmoStd(Text));
	FString Out = KozmoStr(R.text);
	for (const std::string& Src : R.sources) Out += TEXT("\n[kaynak] ") + KozmoStr(Src);
	Push(TEXT("NOVA: ") + KozmoStr(R.text).Left(120));
	return Out;
}

TArray<FString> UKozmoSubsystem::GetNovaWarnings() const
{
	TArray<FString> Out;
	for (const std::string& W : Nova->warnings()) Out.Add(KozmoStr(W));
	return Out;
}

FString UKozmoSubsystem::SimulateAscent(bool bHeavy, float PayloadT)
{
	const kozmo::prop::Design D = bHeavy ? kozmo::preset_heavy_rocket("leo", PayloadT, 0) : kozmo::preset_light_rocket("leo", PayloadT);
	auto R = kozmo::flight::simulate_ascent(D, kozmo::flight::AscentConfig{});
	if (!R.ok()) return KozmoStr(R.error().message);
	const auto& X = R.value();
	FString S;
	for (const auto& E : X.events)
	{
		S += FString::Printf(TEXT("T+%.0f s  %s  %.1f km  %.0f m/s\n"), E.t_s, *KozmoStr(kozmo::flight::event_name(E.type)),
			E.altitude_m / 1000.0, E.speed_ms);
	}
	S += FString::Printf(TEXT("%s — yörünge %.0f x %.0f km, Max-Q %.1f kPa"), X.orbit ? TEXT("YÖRÜNGE") : TEXT("BAŞARISIZ"),
		X.final_orbit.periapsis_alt_m / 1000.0, X.final_orbit.apoapsis_alt_m / 1000.0, X.max_q_pa / 1000.0);
	return S;
}

FString UKozmoSubsystem::DescribeGalaxy(int64 Seed, int32 Systems)
{
	const kozmo::universe::Galaxy G(static_cast<std::uint64_t>(Seed), FMath::Clamp(Systems, 1, 20000));
	FString S = FString::Printf(TEXT("Galaksi (tohum %lld): %d yıldız sistemi\n"), Seed, G.systems().size());
	for (const auto& [Id, Pi] : G.best_colony_candidates(5))
	{
		const auto* Sys = G.find(Id);
		const auto& P = Sys->planets[Pi];
		S += FString::Printf(TEXT("%s (%s) -> %s: %s, %.0f K, %.2f g, puan %.2f\n"), *KozmoStr(Sys->name),
			*KozmoStr(kozmo::universe::to_string(Sys->star.spectral)), *KozmoStr(P.name), *KozmoStr(kozmo::universe::to_string(P.type)),
			P.equilibrium_temp_k, P.surface_gravity_g, P.colony_score);
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

#include "KozmoSubsystem.h"

#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "KozmoGraphics.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/planner.hpp"
#include "kozmo/savefmt.hpp"
#include "kozmo/solar.hpp"
THIRD_PARTY_INCLUDES_END

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
	LoadSettings();
	LoadPresetDesign(TEXT("f9"));
	SetQuality(KozmoGraphics::Recommend(QualityReason));   // ilk açılışta donanıma göre öneri
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
	AgencyBase = kozmo::agency::Base();
	ContractBoard = kozmo::contracts::Board();
	SatFleet = kozmo::sats::Fleet();
	CrewRoster = kozmo::crew::Roster();
	Civilization = kozmo::civ::Civilization();
	OrbitalStation = MakeUnique<kozmo::station::Station>(kozmo::station::iss_like());
	for (const char* N : {"Ayşe Yıldız", "Burak Demir", "Cemre Kaya", "Deniz Aksoy"}) (void)CrewRoster.hire(N, MgmtRng);
	ContractBoard.refresh(0, AgencyBase.capabilities().contract_slots, MgmtRng);
	LastManagedDay = 0;
	NewsFeed.report(std::string("Yeni ajans kuruldu: ") + KozmoStd(Agency), 0);
	Push(FString::Printf(TEXT("Yeni oyun: %s"), *Agency));
}

void UKozmoSubsystem::SetTimeScale(float InDaysPerSecond) { DaysPerSecond = FMath::Clamp(InDaysPerSecond, 0.f, 50.f); }

double UKozmoSubsystem::GetDay() const { return Game ? Game->day() : 0.0; }
double UKozmoSubsystem::GetCredits() const { return Game ? Game->wallet().balance() : 0.0; }

FString UKozmoSubsystem::StartExpedition(const FString& Body, bool bInOrbit)
{
	EndExpedition();
	const std::string B = KozmoStd(Body);
	SliceGame = MakeUnique<kozmo::Game>(41);
	SliceGame->new_game("KOZMOGENİS", 1e6);
	if (B == "moon")
	{
		auto St = SliceGame->found_outpost("moon", kozmo::vertical_slice_outpost());
		if (!St.ok()) return KozmoStr(St.error().message);
		SliceGame->advance(9.375);   // Ay sabahı, mürettebat 09:00
	}
	Expedition = MakeUnique<kozmo::world::Expedition>(*SliceGame, B, kozmo::craft::preset("lander"));
	auto St = Expedition->init(bInOrbit);
	if (!St.ok())
	{
		const FString Err = KozmoStr(St.error().message);
		EndExpedition();
		return Err;
	}
	// §7.2 adım 4: buz dünyası seferinde termal ekipman hazırlanmış olarak başlar (-179 °C, EMU sınırı -157 °C)
	if (B == "titan" || B == "europa") Expedition->player().eq.thermal_suit = true;
	SliceNova = MakeUnique<kozmo::nova::Nova>(*SliceGame);
	SliceNova->attach(Expedition.Get());
	Push(FString::Printf(TEXT("Sefer başladı: %s"), *KozmoStr(Expedition->env().name)));
	return FString();
}

void UKozmoSubsystem::EndExpedition()
{
	if (SliceNova) SliceNova->attach(nullptr);
	SliceNova.Reset();
	Expedition.Reset();
	SliceGame.Reset();
}

bool UKozmoSubsystem::TickGame(float DeltaTime)
{
	if (Expedition)
	{
		// sefer sürerken kampanya zamanı durur; sefer kendi senaryo oyununu ilerletir (kare başına en çok 1 oyun saati)
		Expedition->tick(FMath::Min<double>(DeltaTime * ExpeditionTimeScale, 3600.0));
		return true;
	}
	if (Game && DaysPerSecond > 0.f)
	{
		// kare başına en fazla 2 oyun günü: yavaş karelerde simülasyon patlamasın
		Game->advance(FMath::Min<double>(DeltaTime * DaysPerSecond, 2.0));
		if (Game->day() - LastManagedDay >= 1.0) ManageDaily();
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
	kozmo::nova::Nova& N = SliceNova ? *SliceNova : *Nova;   // seferdeyken NOVA sefere bağlıdır
	const kozmo::nova::Reply R = N.ask(KozmoStd(Text));
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

void UKozmoSubsystem::ManageDaily()
{
	const double Day = Game->day();
	for (const auto& M : AgencyBase.advance(Day, Game->wallet())) Push(KozmoStr(M));
	for (const auto& M : ContractBoard.expire(Day, Game->wallet())) Push(KozmoStr(M));
	ContractBoard.refresh(Day, AgencyBase.capabilities().contract_slots, MgmtRng);
	const double Solar = kozmo::solar::density_factor(kozmo::solar::year_from_game_day(Day));
	const double Income = SatFleet.advance(Day - LastManagedDay, Solar, MgmtRng);
	if (Income > 0) Game->wallet().earn(Income, "Uydu hizmet geliri", Day);
	if (OrbitalStation) for (const auto& W : OrbitalStation->advance_days(Day - LastManagedDay, Solar).warnings) Push(KozmoStr(OrbitalStation->name() + ": " + W));
	for (const auto& M : Civilization.update(*Game)) Push(KozmoStr(M));
	(void)CrewRoster.train(8.0 * (Day - LastManagedDay) * AgencyBase.capabilities().training_speed);
	CrewRoster.rest(16.0 * (Day - LastManagedDay));
	kozmo::progress::Snapshot Snap;
	Snap.colonies = static_cast<int>(Game->colonies().size());
	for (const auto& [Id, C] : Game->colonies()) Snap.population += C.population();
	Snap.missions = static_cast<int>(Game->missions().size());
	Snap.research_done = static_cast<int>(Game->research().unlocked_list().size());
	for (const auto& C : SatFleet.constellations()) Snap.satellites += C.active;
	Snap.max_base = AgencyBase.max_base();
	Snap.credits = Game->wallet().balance();
	Snap.day = Day;
	for (const auto& K : AchievementTracker.update(Snap))
		for (const auto& A : kozmo::progress::achievements())
			if (A.key == K) Push(TEXT("BAŞARIM: ") + KozmoStr(A.title));
	LastManagedDay = Day;
}

FString UKozmoSubsystem::SettingsPath() const { return FPaths::ProjectSavedDir() / TEXT("kozmo_ayarlar.json"); }

FString UKozmoSubsystem::ApplySettings()
{
	const auto Fixed = UserSettings.validate();
	const auto Conflicts = kozmo::settings::key_conflicts(UserSettings.keys);
	FFileHelper::SaveStringToFile(KozmoStr(UserSettings.to_json().dump()), *SettingsPath(), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	FString S = TEXT("Ayarlar kaydedildi");
	if (!Fixed.empty()) S += FString::Printf(TEXT(" (%d değer sınırlandı)"), static_cast<int32>(Fixed.size()));
	for (const auto& C : Conflicts) S += TEXT("\nTuş çakışması: ") + KozmoStr(C.first) + TEXT(" / ") + KozmoStr(C.second);
	return S;
}

void UKozmoSubsystem::LoadSettings()
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *SettingsPath())) return;
	auto J = kozmo::json::parse(KozmoStd(Text));
	if (!J.ok()) return;
	auto R = kozmo::settings::Settings::from_json(J.value());
	if (R.ok()) UserSettings = R.value();
}

FString UKozmoSubsystem::GetManagementText() const
{
	const auto Cap = AgencyBase.capabilities();
	FString S = FString::Printf(TEXT("ÜS: rampa %d, en büyük roket %.0f t, eşzamanlı görev %d, araştırma x%.2f, iletişim %.0f milyon km, NOVA seviye %d, günlük gider %.0f\n"),
		Cap.pads, Cap.max_liftoff_t, Cap.concurrent_missions, Cap.research_speed, Cap.comms_range_km / 1e6, Cap.nova_level, AgencyBase.upkeep_per_day());
	for (int32 i = 0; i < kozmo::agency::kFacilityCount; ++i)
	{
		const auto F = static_cast<kozmo::agency::Facility>(i);
		S += FString::Printf(TEXT("  %d) %s: %d/%d\n"), i, *KozmoStr(kozmo::agency::spec(F).name), AgencyBase.level(F), kozmo::agency::spec(F).max_level);
	}
	S += FString::Printf(TEXT("SÖZLEŞMELER (itibar %%%.0f):\n"), ContractBoard.reputation() * 100);
	for (const auto& C : ContractBoard.contracts())
		if (C.status == kozmo::contracts::Status_::Offered || C.status == kozmo::contracts::Status_::Accepted)
			S += FString::Printf(TEXT("  #%d %s: %.2f t -> %s, ödül %.0f, son gün %.0f [%s]\n"), C.id, *KozmoStr(C.client), C.payload_t, *KozmoStr(kozmo::contracts::to_string(C.dest)),
				C.reward, C.deadline_day, *KozmoStr(kozmo::contracts::to_string(C.status)));
	for (const auto& C : SatFleet.constellations())
		S += FString::Printf(TEXT("UYDU %s: %d etkin, kapsama %%%.0f, %.0f kredi/gün\n"), *KozmoStr(C.name), C.active, C.coverage() * 100, C.revenue_per_day());
	const auto M = Civilization.measure(*Game);
	S += FString::Printf(TEXT("MEDENİYET: %s, nüfus %d, istikrar %%%.0f, politika: %s\n"), *KozmoStr(kozmo::civ::to_string(M.era)), M.population, M.stability * 100,
		*KozmoStr(kozmo::civ::to_string(Civilization.policy())));
	if (OrbitalStation)
		S += FString::Printf(TEXT("İSTASYON %s: %.1f km, %d/%d mürettebat, sarf %.0f gün\n"), *KozmoStr(OrbitalStation->name()), OrbitalStation->altitude() / 1000.0,
			OrbitalStation->crew(), OrbitalStation->crew_capacity(), OrbitalStation->days_of_supplies());
	S += FString::Printf(TEXT("EKİP: %d astronot, başarım %d/%d"), static_cast<int32>(CrewRoster.astronauts().size()), AchievementTracker.count(),
		static_cast<int32>(kozmo::progress::achievements().size()));
	return S;
}

FString UKozmoSubsystem::UpgradeFacility(int32 F)
{
	if (F < 0 || F >= kozmo::agency::kFacilityCount) return TEXT("Geçersiz tesis");
	auto St = AgencyBase.upgrade(static_cast<kozmo::agency::Facility>(F), Game->wallet(), Game->day());
	return St.ok() ? TEXT("Yükseltme başladı") : KozmoStr(St.error().message);
}

FString UKozmoSubsystem::AcceptContract(int32 Id)
{
	auto St = ContractBoard.accept(Id, AgencyBase.capabilities().concurrent_missions);
	return St.ok() ? TEXT("Sözleşme kabul edildi") : KozmoStr(St.error().message);
}

FString UKozmoSubsystem::LaunchConstellation(int32 Purpose, int32 Orbit, int32 Count)
{
	if (Purpose < 0 || Purpose > 3 || Orbit < 0 || Orbit > 3 || Count <= 0) return TEXT("Geçersiz takımyıldızı");
	const double Cost = 2000.0 * Count;   // uydu + fırlatma payı (oyun ölçeği, kredi)
	if (!Game->wallet().spend(Cost, "Uydu fırlatma", Game->day()).ok()) return TEXT("Yetersiz bakiye");
	auto Id = SatFleet.create(std::string("Takımyıldızı ") + std::to_string(SatFleet.constellations().size() + 1), static_cast<kozmo::sats::Purpose>(Purpose),
		static_cast<kozmo::sats::Orbit>(Orbit), 300);
	if (!Id.ok()) return KozmoStr(Id.error().message);
	(void)SatFleet.deploy(Id.value(), Count, Game->day());
	return FString::Printf(TEXT("%d uydu %s yörüngesine yerleştirildi"), Count, *KozmoStr(kozmo::sats::to_string(static_cast<kozmo::sats::Orbit>(Orbit))));
}

FString UKozmoSubsystem::HireAstronaut(const FString& Name)
{
	if (static_cast<int32>(CrewRoster.astronauts().size()) >= AgencyBase.capabilities().astronaut_capacity) return TEXT("Astronot merkezi kapasitesi dolu");
	const int Id = CrewRoster.hire(KozmoStd(Name), MgmtRng);
	(void)CrewRoster.enroll(Id, "ascan");
	return FString::Printf(TEXT("%s işe alındı; temel eğitime başladı"), *Name);
}

FString UKozmoSubsystem::SetPolicy(int32 P)
{
	if (P < 0 || P > static_cast<int32>(kozmo::civ::Policy::Expansion)) return TEXT("Geçersiz politika");
	(void)Civilization.set_policy(static_cast<kozmo::civ::Policy>(P));
	return KozmoStr(std::string(kozmo::civ::to_string(Civilization.policy())) + ": " + kozmo::civ::describe(Civilization.policy()));
}

FString UKozmoSubsystem::PlanMission(const FString& Target, int32 Crew)
{
	auto P = kozmo::planner::plan(*Game, KozmoStd(Target), Crew, 10.0, Target == TEXT("moon") ? 14.0 : 30.0, true);
	return P.ok() ? KozmoStr(P.value().summary()) : KozmoStr(P.error().message);
}

bool UKozmoSubsystem::SaveToSlot(const FString& SlotName)
{
	// sürümlü zarf (v3): oyun + ajans + uydular + sözleşmeler + ekip + medeniyet + istasyon + ilerleme; FNV sağlama
	kozmo::json::Value P = kozmo::json::Value::object();
	P.set("game", kozmo::json::parse(Game->save()).value());
	P.set("agency", AgencyBase.to_json());
	P.set("satellites", SatFleet.to_json());
	P.set("contracts", ContractBoard.to_json());
	P.set("crew", CrewRoster.to_json());
	P.set("civ", Civilization.to_json());
	if (OrbitalStation) P.set("station", OrbitalStation->to_json());
	kozmo::json::Value Prog = kozmo::json::Value::object();
	Prog.set("achievements", AchievementTracker.to_json());
	Prog.set("tutorial", TutorialSteps.to_json());
	Prog.set("news", NewsFeed.to_json());
	P.set("progress", Prog);
	P.set("settings", UserSettings.to_json());
	const bool bOk = FFileHelper::SaveStringToFile(KozmoStr(kozmo::savefmt::wrap(P)), *SlotPath(SlotName),
		FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	Push(bOk ? FString::Printf(TEXT("Kaydedildi: %s"), *SlotName) : TEXT("Kayıt yazılamadı"));
	return bOk;
}

FString UKozmoSubsystem::LoadFromSlot(const FString& SlotName)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *SlotPath(SlotName))) return TEXT("Kayıt bulunamadı");
	auto L = kozmo::savefmt::unwrap(KozmoStd(Text));   // sağlama + eski sürüm taşıma (yalnız bellekte; dosya değişmez)
	if (!L.ok()) return KozmoStr(L.error().message);
	const auto& P = L.value().payload;
	auto R = Game->load(P["game"].dump());
	if (!R.ok()) return KozmoStr(R.error().message);
	if (P["agency"].has("levels")) (void)AgencyBase.from_json(P["agency"]);
	if (P["satellites"].has("list")) (void)SatFleet.from_json(P["satellites"]);
	if (P["contracts"].has("list")) (void)ContractBoard.from_json(P["contracts"]);
	if (P.has("crew")) (void)CrewRoster.from_json(P["crew"]);
	if (P.has("civ")) (void)Civilization.from_json(P["civ"]);
	if (P.has("station"))
		if (auto S = kozmo::station::Station::from_json(P["station"]); S.ok()) OrbitalStation = MakeUnique<kozmo::station::Station>(S.value());
	if (P["progress"].has("achievements")) (void)AchievementTracker.from_json(P["progress"]["achievements"]);
	LastManagedDay = Game->day();
	for (const auto& N : L.value().notes) Push(KozmoStr(N));
	Push(FString::Printf(TEXT("Yüklendi: %s"), *SlotName));
	return FString();
}

// ------------------------------------------------------------------------------------------------
// Roket tasarımcısı
namespace
{
const char* const kTargets[] = {"leo", "moon", "mars"};
// motor döngüsünde gösterilecek kademe motorları (iyon/SRB çekirdek kademe için uygun değil)
const char* const kStageEngines[] = {"kerolox_gg", "kerolox_vac", "methalox_fc", "methalox_vac", "hydrolox_exp", "ntr"};
}  // namespace

void UKozmoSubsystem::DesignChanged() { OnDesignChanged.Broadcast(Design); }

void UKozmoSubsystem::LoadPresetDesign(const FString& Preset)
{
	if (Preset == TEXT("heavy"))
	{
		Design = kozmo::preset_heavy_rocket("moon", 40.0, 0);
	}
	else
	{
		Design = kozmo::preset_light_rocket("leo", 22.0);
		if (Preset == TEXT("f9_srb"))
		{
			Design.boosters.count = 2;
			Design.boosters.propellant_t = 150.0;
			Design.boosters.diameter_m = 2.5;
			Design.payload_t = 30.0;
		}
	}
	DesignChanged();
}

void UKozmoSubsystem::CycleStageEngine(int32 Stage, int32 Direction)
{
	if (Stage < 0 || Stage >= static_cast<int32>(Design.stages.size())) return;
	const int32 N = UE_ARRAY_COUNT(kStageEngines);
	int32 Cur = 0;
	for (int32 i = 0; i < N; ++i)
		if (Design.stages[Stage].engine == kStageEngines[i]) Cur = i;
	Design.stages[Stage].engine = kStageEngines[(Cur + (Direction >= 0 ? 1 : N - 1)) % N];
	DesignChanged();
}

void UKozmoSubsystem::AdjustStage(int32 Stage, int32 EngineDelta, float PropellantFactor, float DiameterDelta)
{
	if (Stage < 0 || Stage >= static_cast<int32>(Design.stages.size())) return;
	kozmo::prop::Stage& S = Design.stages[Stage];
	S.engine_count = FMath::Clamp(S.engine_count + EngineDelta, 1, 40);
	S.propellant_t = FMath::Clamp(S.propellant_t * (PropellantFactor > 0.f ? PropellantFactor : 1.f), 1.0, 6000.0);
	S.diameter_m = FMath::Clamp(S.diameter_m + DiameterDelta, 1.0, 12.0);
	DesignChanged();
}

void UKozmoSubsystem::AddStage()
{
	if (Design.stages.size() >= 4) return;
	kozmo::prop::Stage Top = Design.stages.empty() ? kozmo::prop::Stage{"kerolox_vac", 1, 50.0, 0.06, 3.7} : Design.stages.back();
	Top.engine = "hydrolox_exp";
	Top.engine_count = 1;
	Top.propellant_t = FMath::Max(5.0, Top.propellant_t * 0.25);
	Design.stages.push_back(Top);
	DesignChanged();
}

void UKozmoSubsystem::RemoveTopStage()
{
	if (Design.stages.size() <= 1) return;
	Design.stages.pop_back();
	DesignChanged();
}

void UKozmoSubsystem::AdjustBoosters(int32 CountDelta, float PropellantDeltaT)
{
	Design.boosters.count = FMath::Clamp(Design.boosters.count + CountDelta, 0, 8);
	if (Design.boosters.count > 0 && Design.boosters.propellant_t <= 0) Design.boosters.propellant_t = 150.0;
	Design.boosters.propellant_t = FMath::Clamp(Design.boosters.propellant_t + PropellantDeltaT, 10.0, 700.0);
	DesignChanged();
}

void UKozmoSubsystem::AdjustPayload(float DeltaT)
{
	Design.payload_t = FMath::Clamp(Design.payload_t + DeltaT, 0.1, 500.0);
	DesignChanged();
}

void UKozmoSubsystem::CycleTarget()
{
	int32 Cur = 0;
	for (int32 i = 0; i < 3; ++i)
		if (Design.target == kTargets[i]) Cur = i;
	Design.target = kTargets[(Cur + 1) % 3];
	DesignChanged();
}

FString UKozmoSubsystem::GetDesignReport() const
{
	FString S = FString::Printf(TEXT("Hedef: %s  |  Yük %.1f t"), *KozmoStr(Design.target), Design.payload_t);
	for (int32 i = 0; i < static_cast<int32>(Design.stages.size()); ++i)
	{
		const auto& St = Design.stages[i];
		auto E = kozmo::prop::find_engine(St.engine);
		S += FString::Printf(TEXT("\n%d. kademe: %d x %s, %.0f t yakıt, Ø %.1f m"), i + 1, St.engine_count,
			E.ok() ? *KozmoStr(E.value()->name_tr) : *KozmoStr(St.engine), St.propellant_t, St.diameter_m);
	}
	if (Design.boosters.count > 0)
		S += FString::Printf(TEXT("\nGüçlendirici: %d x %.0f t katı yakıt"), Design.boosters.count, Design.boosters.propellant_t);
	auto R = Game->evaluate(Design);
	if (!R.ok()) return S + TEXT("\n! ") + KozmoStr(R.error().message);
	const auto& Rep = R.value();
	S += FString::Printf(TEXT("\n\nKalkış %.0f t, TWR %.2f, delta-v %.2f / gereken %.2f km/s, başarı %%%.1f, maliyet %.0f"),
		Rep.liftoff_mass_t, Rep.liftoff_twr, Rep.total_dv_ms / 1000.0, Rep.required_dv_ms / 1000.0, Rep.success_p * 100.0, Rep.cost_mcr);
	S += Rep.feasible ? TEXT("  [UYGUN]") : TEXT("  [YETERSİZ]");
	for (const auto& P : Rep.problems) S += TEXT("\n! ") + KozmoStr(P);
	auto G = kozmo::vehicle::geometry(Design);
	if (G.ok())
	{
		const auto& X = G.value();
		S += FString::Printf(TEXT("\nBoy %.1f m, incelik %.1f, kütle merkezi %.1f m, basınç merkezi %.1f m, fairing %.1f t"), X.total_height_m,
			X.fineness, X.center_of_mass_m, X.center_of_pressure_m, X.fairing_mass_t);
		for (const auto& N : X.notes) S += TEXT("\n• ") + KozmoStr(N);
	}
	return S;
}

FString UKozmoSubsystem::SimulateDesignAscent() const
{
	auto R = kozmo::flight::simulate_ascent(Design, kozmo::flight::AscentConfig{});
	if (!R.ok()) return KozmoStr(R.error().message);
	const auto& X = R.value();
	FString S;
	for (const auto& E : X.events)
		S += FString::Printf(TEXT("T+%.0f s  %s  %.1f km\n"), E.t_s, *KozmoStr(kozmo::flight::event_name(E.type)), E.altitude_m / 1000.0);
	S += FString::Printf(TEXT("%s — %.0f x %.0f km, Max-Q %.1f kPa, en yüksek %.1f g"), X.orbit ? TEXT("YÖRÜNGE") : TEXT("BAŞARISIZ"),
		X.final_orbit.periapsis_alt_m / 1000.0, X.final_orbit.apoapsis_alt_m / 1000.0, X.max_q_pa / 1000.0, X.max_accel_g);
	return S;
}

void UKozmoSubsystem::SetQuality(EKozmoQuality Q)
{
	KozmoGraphics::Apply(Q);
	Push(FString::Printf(TEXT("Grafik profili: %s"), KozmoGraphics::Get(Q).Name));
}

FString UKozmoSubsystem::GetQualityText() const
{
	const auto& P = KozmoGraphics::Get(KozmoGraphics::Current());
	return FString::Printf(TEXT("Grafik: %s (iç çözünürlük %%%.0f, Lumen %s)%s%s"), P.Name, P.ScreenPercentage,
		P.GlobalIllumination == 1 ? TEXT("açık") : TEXT("kapalı"), QualityReason.IsEmpty() ? TEXT("") : TEXT(" — öneri: "), *QualityReason);
}

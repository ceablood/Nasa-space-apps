#include "KozmoExpedition.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "KozmoShapes.h"
#include "KozmoSubsystem.h"
#include "KozmogenisCharacter.h"
#include "KozmogenisColony.h"
#include "KozmogenisSpacecraft.h"

AKozmoExpeditionScene::AKozmoExpeditionScene()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(Root);
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->SetLightSourceAngle(0.53f);
	Sun->SetAtmosphereSunLight(true);
	Sky = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("Sky"));
	Sky->SetupAttachment(Root);
	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(Root);
	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->bRealTimeCapture = true;
	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("Fog"));
	Fog->SetupAttachment(Root);
	Post = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Post"));
	Post->SetupAttachment(Root);
	Post->bUnbound = true;
	Post->Settings.bOverride_BloomIntensity = true;
	Post->Settings.BloomIntensity = 0.5f;
	Post->Settings.bOverride_VignetteIntensity = true;
	Post->Settings.VignetteIntensity = 0.3f;
}

UKozmoSubsystem* AKozmoExpeditionScene::Kozmo() const
{
	return GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
}

void AKozmoExpeditionScene::SetupEnvironment()
{
	const UKozmoSubsystem* K = Kozmo();
	const auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	const auto& Env = E->env();
	const bool Atmos = Env.pressure_kpa > 0.1;
	// güneş: yerel güneş saatinden yükseklik
	const double H = E->local_hour();
	const float Elev = static_cast<float>(FMath::Clamp(FMath::Sin(PI * (H - 6.0) / 12.0) * 70.0, -10.0, 70.0));
	Sun->SetWorldRotation(FRotator(-Elev, 40.f, 0.f));
	if (Env.key == "moon")
	{
		Sky->SetVisibility(false);                      // atmosfer yok: kara gökyüzü, keskin gölgeler
		BaseSun = 12.f;
		SkyLight->SetIntensity(0.05f);
		BaseFog = 0.f;
		Fog->SetVisibility(false);
	}
	else if (Env.key == "mars")
	{
		// Mars: ince CO2 atmosferi, toz (Mie) baskın -> gündüz karamel, gün batımı mavimsi (gözlenen)
		Sky->SetBottomRadius(static_cast<float>(Env.radius_km));
		Sky->SetAtmosphereHeight(80.f);
		Sky->SetRayleighScattering(FLinearColor(0.019f, 0.013f, 0.0057f));
		Sky->SetRayleighScatteringScale(0.03f);
		Sky->SetRayleighExponentialDistribution(11.1f);    // ölçek yüksekliği (km, gerçek)
		Sky->SetMieScattering(FLinearColor(0.9f, 0.55f, 0.3f));
		Sky->SetMieScatteringScale(0.012f);
		Sky->SetMieAbsorption(FLinearColor(0.2f, 0.35f, 0.6f));
		Sky->SetMieAnisotropy(0.7f);
		Sky->SetGroundAlbedo(FColor(170, 100, 60));
		BaseSun = 10.f * 0.43f;                           // 1.52 AU: 1/r² ~ %43 güneş
		SkyLight->SetIntensity(0.6f);
		BaseFog = 0.01f;
		Fog->SetFogDensity(BaseFog);
		Fog->SetFogInscatteringColor(FLinearColor(0.55f, 0.35f, 0.22f));
	}
	else if (Env.key == "titan")
	{
		// Titan: kalın azot atmosferi, tolin pusu -> turuncu gök; yüzeye güneş ışığının ~%0.1'i ulaşır (Huygens)
		Sky->SetBottomRadius(static_cast<float>(Env.radius_km));
		Sky->SetAtmosphereHeight(600.f);
		Sky->SetRayleighExponentialDistribution(21.f);
		Sky->SetMieScattering(FLinearColor(0.9f, 0.55f, 0.2f));
		Sky->SetMieScatteringScale(0.05f);
		Sky->SetMieAbsorption(FLinearColor(0.1f, 0.3f, 0.8f));
		BaseSun = 0.8f;
		SkyLight->SetIntensity(0.4f);
		BaseFog = 0.04f;
		Fog->SetFogDensity(BaseFog);
		Fog->SetFogInscatteringColor(FLinearColor(0.6f, 0.38f, 0.15f));
	}
	else if (!Atmos)
	{
		Sky->SetVisibility(false);
		Fog->SetVisibility(false);
	}
	Sun->SetIntensity(BaseSun);
	// zemin, kraterler, kayalar (prosedürel, tohumlu)
	const FLinearColor Ground = Env.key == "mars" ? FLinearColor(0.42f, 0.22f, 0.12f)
		: (Env.key == "titan" ? FLinearColor(0.30f, 0.22f, 0.12f) : FLinearColor(0.33f, 0.33f, 0.32f));
	KozmoShapes::Add(this, Root, EKozmoShape::Plane, FVector(0, 0, 0), FVector(4000.f, 4000.f, 1.f), Ground, 0.95f);
	FRandomStream R(41);
	for (int32 i = 0; i < 60; ++i)
	{
		const FVector P(R.FRandRange(-1500.f, 1500.f), R.FRandRange(-1500.f, 1500.f), 0.f);
		if (P.Size2D() < 180.f) continue;           // koloni alanı temiz
		const float S = R.FRandRange(4.f, 40.f);
		if (Env.key == "moon" && i % 2 == 0)
			KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, P + FVector(0, 0, -0.2f * S), FVector(S, S, 0.25f * S), Ground * 0.7f, 0.95f);   // krater çanağı
		else
			KozmoShapes::Add(this, Root, EKozmoShape::Sphere, P, FVector(S * 0.15f, S * 0.12f, S * 0.08f), Ground * 0.85f, 0.9f,
				FRotator(R.FRandRange(0, 30), R.FRandRange(0, 360), 0));
	}
}

void AKozmoExpeditionScene::BeginPlay()
{
	Super::BeginPlay();
	SetupEnvironment();
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	SyncColony();
	Craft = GetWorld()->SpawnActor<AKozmogenisSpacecraft>(LandingPadWorld(), FRotator::ZeroRotator);
	if (Craft) Craft->SetScene(this);
	PossessCraft();
	SetFeedback(TEXT("Kabindesin. E: koltuğa otur, B: inişi başlat, F: motorlar, L: iniş desteği. Tab: imleç."));
}

void AKozmoExpeditionScene::EndPlay(const EEndPlayReason::Type Reason)
{
	for (auto& [Id, N] : Npcs)
		if (N) N->Destroy();
	if (Walker) Walker->Destroy();
	if (Craft) Craft->Destroy();
	if (Colony) Colony->Destroy();
	Super::EndPlay(Reason);
}

FVector AKozmoExpeditionScene::SettlementToWorld(double X, double Y, double Z) const
{
	return GetActorLocation() + FVector(X, Y, Z) * 100.0;
}

FVector2D AKozmoExpeditionScene::WorldToSettlement(const FVector& W) const
{
	const FVector L = (W - GetActorLocation()) / 100.0;
	return FVector2D(L.X, L.Y);
}

FVector AKozmoExpeditionScene::LandingPadWorld() const
{
	const UKozmoSubsystem* K = Kozmo();
	const auto* E = K ? K->GetExpedition() : nullptr;
	const auto* Pad = E ? E->settlement().find(kozmo::life::District::LandingPad) : nullptr;
	return Pad ? SettlementToWorld(Pad->x, Pad->y, 0.3) : GetActorLocation() + FVector(13000, 0, 30);
}

FString AKozmoExpeditionScene::BuildingAt(const FVector& W) const { return Colony ? Colony->BuildingAt(W) : FString(); }

bool AKozmoExpeditionScene::IsPlayerInCraft() const
{
	const UKozmoSubsystem* K = Kozmo();
	const auto* E = K ? K->GetExpedition() : nullptr;
	return E && (E->player().mode == kozmo::world::PlayerMode::Seated || E->player().mode == kozmo::world::PlayerMode::InCabin);
}

void AKozmoExpeditionScene::PossessCraft()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!PC || !Craft) return;
	PC->Possess(Craft);
	if (Walker)
	{
		Walker->Destroy();
		Walker = nullptr;
	}
}

void AKozmoExpeditionScene::PossessCharacter()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!PC || !E) return;
	const FVector P = (Craft ? Craft->GetHatchLocation() : LandingPadWorld()) + FVector(150.f, 0.f, 120.f);
	FActorSpawnParameters SP;
	SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
	Walker = GetWorld()->SpawnActor<AKozmogenisCharacter>(P, FRotator(0.f, 180.f, 0.f), SP);
	if (!Walker) return;
	Walker->SetScene(this, static_cast<float>(E->env().gravity_ms2));
	PC->Possess(Walker);
	SetFeedback(TEXT("Yüzeydesin. WASD yürü, Space zıpla, E etkileşim (kapı/konsol/NPC/araç kapağı), G numune topla."));
}

void AKozmoExpeditionScene::SyncColony()
{
	// koloni kurulduğunda ya da bir modül tamamlandığında 3B yerleşimi yeniden kur (inşa edilmiş bölge imzası)
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !E->colony()) return;
	int32 Sig = 0;
	for (const auto& B : E->settlement().buildings()) Sig = Sig * 2 + (B.built ? 1 : 0);
	const auto* P = E->construction().current();
	Sig = Sig * 31 + (P ? P->id * 10 + static_cast<int32>(P->progress() * 4) : 0);
	if (Sig == BuiltSignature) return;
	BuiltSignature = Sig;
	if (Colony) Colony->Destroy();
	Colony = GetWorld()->SpawnActor<AKozmogenisColony>(GetActorLocation(), FRotator::ZeroRotator);
	if (!Colony) return;
	FString SiteId;
	float Progress = 0.f;
	if (P)
	{
		const auto D = P->reinforce ? kozmo::life::District::Housing : static_cast<kozmo::life::District>(kozmo::build::site_district(P->module));
		if (const auto* B = E->settlement().find(D)) SiteId = KozmoStr(B->id);
		Progress = static_cast<float>(P->progress());
	}
	Colony->Build(E->settlement(), SiteId, Progress);
}

void AKozmoExpeditionScene::SyncNpcs()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !E->colony()) return;
	TSet<int32> Alive;
	for (const auto& N : E->society().npcs())
	{
		Alive.Add(N.id);
		TObjectPtr<AKozmogenisNPC>* Found = Npcs.Find(N.id);
		AKozmogenisNPC* A = Found ? Found->Get() : nullptr;
		const auto* C = E->colony()->colonist(N.id);
		if (!A && C)
		{
			A = GetWorld()->SpawnActor<AKozmogenisNPC>(SettlementToWorld(N.x, N.y), FRotator::ZeroRotator);
			if (A) A->Setup(N.id, KozmoStr(C->name) + TEXT(" — ") + KozmoStr(kozmo::colony::job_name(C->job)), static_cast<int32>(C->job));
			Npcs.Add(N.id, A);
		}
		if (A) A->Sync(SettlementToWorld(N.x, N.y), KozmoStr(kozmo::life::to_string(N.intent)), N.lod != kozmo::life::Lod::Far);
	}
	for (auto It = Npcs.CreateIterator(); It; ++It)
		if (!Alive.Contains(It.Key()))
		{
			if (It.Value()) It.Value()->Destroy();
			It.RemoveCurrent();
		}
}

void AKozmoExpeditionScene::Tick(float Dt)
{
	Super::Tick(Dt);
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	SyncColony();
	SyncNpcs();
	// hava olayları: görüş -> sis, güneş çarpanı -> ışık
	double Vis = 1.0, Solar = 1.0;
	for (const auto& W : E->weather())
	{
		Vis = FMath::Min(Vis, W.visibility);
		Solar = FMath::Min(Solar, W.solar_factor);
	}
	Sun->SetIntensity(BaseSun * static_cast<float>(Solar));
	if (BaseFog > 0) Fog->SetFogDensity(BaseFog + static_cast<float>((1.0 - Vis) * 0.15));
	const double H = E->local_hour();
	const float Elev = static_cast<float>(FMath::Clamp(FMath::Sin(PI * (H - 6.0) / 12.0) * 70.0, -10.0, 70.0));
	Sun->SetWorldRotation(FRotator(-Elev, 40.f, 0.f));
}

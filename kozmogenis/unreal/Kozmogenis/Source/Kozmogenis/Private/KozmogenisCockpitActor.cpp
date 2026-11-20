#include "KozmogenisCockpitActor.h"

#include "Components/PointLightComponent.h"
#include "Components/TextRenderComponent.h"
#include "KozmoShapes.h"
#include "KozmoSubsystem.h"   // KozmoStr

namespace
{
const FLinearColor Panel(0.08f, 0.085f, 0.095f);
const FLinearColor Trim(0.30f, 0.31f, 0.33f);
const FLinearColor Seat(0.18f, 0.10f, 0.06f);
const TCHAR* GaugeNames[] = {TEXT("SPEED"), TEXT("ALTITUDE"), TEXT("FUEL"), TEXT("OXYGEN"), TEXT("TEMPERATURE"), TEXT("PRESSURE"),
	TEXT("POWER"), TEXT("SHIELD"), TEXT("HULL"), TEXT("ENGINE"), TEXT("NAVIGATION"), TEXT("RADAR")};
}

AKozmogenisCockpitActor::AKozmogenisCockpitActor()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	CabinLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("CabinLight"));
	CabinLight->SetupAttachment(Root);
	CabinLight->SetRelativeLocation(FVector(0, 0, 180));
	CabinLight->SetIntensity(800.f);
	CabinLight->SetAttenuationRadius(500.f);
	CabinLight->SetLightColor(FLinearColor(1.f, 0.93f, 0.85f));
}

void AKozmogenisCockpitActor::Build(kozmo::craft::CockpitLevel InLevel)
{
	using kozmo::craft::CockpitLevel;
	using kozmo::craft::Feature;
	Level = InLevel;
	// koltuk, emniyet kemeri, konsol, pencere çerçevesi, yan paneller
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(0, 0, 0.45f), FVector(0.6f, 0.6f, 0.12f), Seat, 0.8f));
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(-0.3f, 0, 0.9f), FVector(0.12f, 0.6f, 0.9f), Seat, 0.8f));
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(-0.24f, 0, 0.95f), FVector(0.02f, 0.08f, 0.7f), FLinearColor(0.6f, 0.45f, 0.1f), 0.5f));
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(0.75f, 0, 0.75f), FVector(0.5f, 1.6f, 0.08f), Panel, 0.5f, 0.3f, FRotator(-25.f, 0, 0)));
	for (int32 i = -1; i <= 1; i += 2)
	{
		Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(0.2f, i * 0.85f, 0.85f), FVector(0.9f, 0.06f, 0.5f), Panel, 0.5f, 0.3f));
		Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(1.05f, i * 0.7f, 1.45f), FVector(0.06f, 0.06f, 0.9f), Trim, 0.35f, 0.9f, FRotator(-20.f, 0, 0)));
	}
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(1.15f, 0, 1.95f), FVector(0.06f, 1.5f, 0.06f), Trim, 0.35f, 0.9f));
	// kontrol kolu ve gaz kolu (hareketli: kokpit güncellemesinde döndürülür)
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, FVector(0.35f, 0.25f, 0.65f), FVector(0.04f, 0.04f, 0.3f), Trim, 0.4f, 0.8f));
	Parts.Add(KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, FVector(0.35f, -0.35f, 0.65f), FVector(0.05f, 0.05f, 0.25f), FLinearColor(0.5f, 0.1f, 0.05f), 0.4f, 0.3f));

	// göstergeler: V1'de yalnız temel 6 analog gösterge, V2+ dijital 12 gösterge
	const int32 N = Level == CockpitLevel::Basic ? 6 : 12;
	const FColor Col = Level == CockpitLevel::Basic ? FColor(230, 200, 140) : FColor(150, 225, 240);
	for (int32 i = 0; i < N; ++i)
	{
		const int32 Row = i / 4, Colm = i % 4;
		const FVector P(0.68f, -0.6f + Colm * 0.4f, 0.98f - Row * 0.13f);
		Gauges.Add(KozmoShapes::Label(this, Root, P, GaugeNames[i], 3.2f, Col, FRotator(65.f, 180.f, 0.f)));
	}
	WarningText = KozmoShapes::Label(this, Root, FVector(0.7f, 0, 1.2f), TEXT(""), 4.f, FColor(255, 90, 60), FRotator(65.f, 180.f, 0.f));
	// uyarı lambaları (3 seviye)
	for (int32 i = 0; i < 3; ++i)
	{
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetupAttachment(Root);
		L->SetRelativeLocation(FVector(70.f, -30.f + i * 30.f, 125.f));
		L->SetIntensity(0.f);
		L->SetAttenuationRadius(120.f);
		L->SetLightColor(i == 0 ? FLinearColor(1, 0.8f, 0.1f) : FLinearColor(1, 0.1f, 0.05f));
		L->RegisterComponent();
		WarningLamps.Add(L);
	}
	// fiziksel düğmeler: yalnız kokpit seviyesinin desteklediği işlevler
	auto AddButton = [&](const FString& Action, const FString& Label, const FVector& P, const FLinearColor& C) {
		UStaticMeshComponent* B = KozmoShapes::Add(this, Root, EKozmoShape::Cube, P, FVector(0.05f, 0.05f, 0.025f), C, 0.4f);
		B->ComponentTags.Add(FName(*(TEXT("cockpit:") + Action)));
		Buttons.Add(B, Action);
		KozmoShapes::Label(this, Root, P + FVector(0, 0, 0.05f), Label, 2.2f, FColor(220, 220, 220), FRotator(65.f, 180.f, 0.f));
	};
	AddButton(TEXT("engines"), TEXT("MOTOR"), FVector(0.55f, -0.5f, 0.66f), FLinearColor(0.7f, 0.1f, 0.05f));
	AddButton(TEXT("lights"), TEXT("IŞIK"), FVector(0.55f, -0.3f, 0.66f), FLinearColor(0.7f, 0.7f, 0.6f));
	AddButton(TEXT("emergency"), TEXT("ACİL"), FVector(0.55f, 0.5f, 0.66f), FLinearColor(0.9f, 0.6f, 0.0f));
	AddButton(TEXT("fix"), TEXT("PROSEDÜR"), FVector(0.55f, 0.3f, 0.66f), FLinearColor(0.2f, 0.5f, 0.2f));
	AddButton(TEXT("manual"), TEXT("MANUEL"), FVector(0.55f, -0.1f, 0.66f), FLinearColor(0.3f, 0.3f, 0.35f));
	if (kozmo::craft::cockpit_has(Level, Feature::Autopilot))
		AddButton(TEXT("auto"), TEXT("OTOPİLOT"), FVector(0.55f, 0.1f, 0.66f), FLinearColor(0.1f, 0.3f, 0.6f));
	if (kozmo::craft::cockpit_has(Level, Feature::LandingAssist))
		AddButton(TEXT("landing"), TEXT("İNİŞ DESTEK"), FVector(0.62f, 0.f, 0.72f), FLinearColor(0.1f, 0.5f, 0.6f));
	if (kozmo::craft::cockpit_has(Level, Feature::HoloMap))
		HoloMap = KozmoShapes::Label(this, Root, FVector(0.9f, 0, 1.45f), TEXT("HOLO HARİTA"), 6.f, FColor(80, 230, 255), FRotator(0.f, 180.f, 0.f));
}

void AKozmogenisCockpitActor::UpdateFrom(const kozmo::craft::Spacecraft& Craft)
{
	const kozmo::craft::Instruments In = Craft.instruments();
	const FString V[] = {
		FString::Printf(TEXT("HIZ\n%.1f m/s"), In.speed_ms),
		FString::Printf(TEXT("İRTİFA\n%.0f m"), In.altitude_m),
		FString::Printf(TEXT("YAKIT\n%.1f t %%%.0f"), In.fuel_t, In.fuel_fraction * 100.0),
		FString::Printf(TEXT("OKSİJEN\n%.1f gün"), In.oxygen_days),
		FString::Printf(TEXT("MOTOR ISI\n%.0f K"), In.engine_temp_k),
		FString::Printf(TEXT("KABİN\n%.1f kPa"), In.cabin_pressure_kpa),
		FString::Printf(TEXT("GÜÇ\n%+.1f kW %%%.0f"), In.power_kw_net, In.battery_fraction * 100.0),
		FString::Printf(TEXT("KALKAN\n%%%.0f"), In.shield_fraction * 100.0),
		FString::Printf(TEXT("GÖVDE\n%%%.0f"), In.hull_fraction * 100.0),
		FString::Printf(TEXT("MOTOR\n%s %%%.0f"), In.engines_on ? TEXT("AÇIK") : TEXT("KAPALI"), In.engine_fraction * 100.0),
		FString::Printf(TEXT("NAV\n%s"), *KozmoStr(In.navigation)),
		FString::Printf(TEXT("RADAR\n%s"), In.radar.empty() ? TEXT("-") : *KozmoStr(In.radar.front())),
	};
	for (int32 i = 0; i < Gauges.Num(); ++i)
		if (Gauges[i]) Gauges[i]->SetText(FText::FromString(V[i]));
	const auto W = Craft.warnings();
	int32 MaxSev = 0;
	FString WT;
	for (const auto& X : W)
	{
		MaxSev = FMath::Max(MaxSev, X.severity);
		if (WT.Len() < 200) WT += KozmoStr(X.message) + TEXT("\n");
	}
	if (WarningText) WarningText->SetText(FText::FromString(WT));
	BlinkT += 0.1f;
	const bool On = FMath::Fmod(BlinkT, 1.f) < 0.5f;
	for (int32 i = 0; i < WarningLamps.Num(); ++i)
		WarningLamps[i]->SetIntensity(MaxSev > i && On ? 2000.f : 0.f);
	CabinLight->SetIntensity(200.f * Craft.cabin_lights() + (MaxSev >= 3 && On ? 400.f : 0.f));
	CabinLight->SetLightColor(MaxSev >= 3 ? FLinearColor(1.f, 0.25f, 0.15f) : FLinearColor(1.f, 0.93f, 0.85f));
	if (HoloMap) HoloMap->SetText(FText::FromString(FString::Printf(TEXT("HOLO HARİTA\nmenzil %.1f km  hedef: iniş alanı"), Craft.downrange() / 1000.0)));
}

FString AKozmogenisCockpitActor::ButtonAction(const UPrimitiveComponent* Hit) const
{
	for (const auto& [C, A] : Buttons)
		if (C == Hit) return A;
	return FString();
}

FVector AKozmogenisCockpitActor::GetEyeLocation() const { return GetActorTransform().TransformPosition(FVector(-5.f, 0.f, 125.f)); }

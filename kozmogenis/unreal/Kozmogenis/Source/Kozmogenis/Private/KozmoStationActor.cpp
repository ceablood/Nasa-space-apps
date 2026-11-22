#include "KozmoStationActor.h"

#include "Components/TextRenderComponent.h"
#include "Engine/GameInstance.h"
#include "KozmoShapes.h"
#include "KozmoSubsystem.h"

AKozmoStationActor::AKozmoStationActor()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Body = CreateDefaultSubobject<USceneComponent>(TEXT("Body"));
	Body->SetupAttachment(Root);
}

UKozmoSubsystem* AKozmoStationActor::Kozmo() const { return GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr; }

void AKozmoStationActor::BeginPlay()
{
	Super::BeginPlay();
	Rebuild();
}

void AKozmoStationActor::Rebuild()
{
	UKozmoSubsystem* K = Kozmo();
	if (!K) return;
	TArray<USceneComponent*> Old;
	Body->GetChildrenComponents(true, Old);
	for (USceneComponent* C : Old) C->DestroyComponent();
	const auto& S = K->Station();
	using kozmo::station::ModuleKind;
	const FLinearColor White(0.78f, 0.79f, 0.80f), Truss(0.45f, 0.46f, 0.48f), Panel(0.10f, 0.12f, 0.25f), Gold(0.62f, 0.48f, 0.16f);
	// basınçlı modüller ana eksende (X), güneş kafesleri dik eksende (Y) dizilir
	float X = 0.f;
	int32 Truss_ = 0;
	for (ModuleKind M : S.modules())
	{
		switch (M)
		{
			case ModuleKind::SolarTruss:
			{
				const float Y = (Truss_ % 2 == 0 ? 1.f : -1.f) * (8.f + 12.f * (Truss_ / 2));
				KozmoShapes::Add(this, Body, EKozmoShape::Cube, FVector(0, Y, 0), FVector(1.2f, 12.f, 1.2f), Truss, 0.5f, 0.8f, FRotator::ZeroRotator, false);
				KozmoShapes::Add(this, Body, EKozmoShape::Cube, FVector(0, Y, 9.f), FVector(0.05f, 11.f, 16.f), Panel, 0.2f, 0.6f, FRotator::ZeroRotator, false);
				KozmoShapes::Add(this, Body, EKozmoShape::Cube, FVector(0, Y, -9.f), FVector(0.05f, 11.f, 16.f), Panel, 0.2f, 0.6f, FRotator::ZeroRotator, false);
				++Truss_;
				break;
			}
			case ModuleKind::Cupola:
				KozmoShapes::Add(this, Body, EKozmoShape::Sphere, FVector(X, 0, -3.f), FVector(3.f, 3.f, 2.f), FLinearColor(0.3f, 0.35f, 0.4f), 0.1f, 0.9f, FRotator::ZeroRotator, false);
				break;
			default:
			{
				const float L = M == ModuleKind::Node ? 7.f : (M == ModuleKind::DockingPort ? 2.f : 10.f);
				const float D = M == ModuleKind::DockingPort ? 1.6f : 4.3f;   // ISS modülleri ~4.3 m çap
				KozmoShapes::Add(this, Body, EKozmoShape::Cylinder, FVector(X + L / 2, 0, 0), FVector(D, D, L), M == ModuleKind::Propulsion ? Gold : White, 0.5f, 0.2f,
					FRotator(90.f, 0.f, 0.f), false);
				X += L;
				break;
			}
		}
	}
	for (const auto& Dk : S.docked())
		KozmoShapes::Add(this, Body, EKozmoShape::Cone, FVector(X + 6.f + Dk.port * 2.f, Dk.port % 2 ? 6.f : -6.f, 0), FVector(4.f, 4.f, 8.f), White, 0.4f, 0.3f,
			FRotator(-90.f, 0.f, 0.f), false);
	Info = KozmoShapes::Label(this, Body, FVector(X / 2, 0, 25.f), TEXT(""), 250.f, FColor(180, 230, 255));
	LastModules = static_cast<int32>(S.modules().size());
	LastDocked = static_cast<int32>(S.docked().size());
}

void AKozmoStationActor::Tick(float Dt)
{
	Super::Tick(Dt);
	UKozmoSubsystem* K = Kozmo();
	if (!K) return;
	const auto& S = K->Station();
	if (static_cast<int32>(S.modules().size()) != LastModules || static_cast<int32>(S.docked().size()) != LastDocked) Rebuild();
	// görsel dönüş: yerçekimi gradyanı kararlı tutum (bir yörüngede bir tur) — oyun hızında hızlandırılmış
	Body->AddLocalRotation(FRotator(0.f, 0.f, 360.f / (static_cast<float>(S.period_min()) * 60.f) * Dt * 60.f));
	if (Info)
		Info->SetText(FText::FromString(FString::Printf(TEXT("%s\n%.1f km | %.1f dk | %d/%d mürettebat | sarf %.0f gün | yakıt %.0f kg"), *KozmoStr(S.name()), S.altitude() / 1000.0,
			S.period_min(), S.crew(), S.crew_capacity(), S.days_of_supplies(), S.propellant())));
}

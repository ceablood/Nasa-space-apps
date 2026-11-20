#include "KozmoSolarSystem.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "KozmoSubsystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
// Gerçek renklere yakın (sRGB) gövde renkleri — görsel tercih
FLinearColor BodyColor(const FString& Key)
{
	if (Key == TEXT("sun")) return FLinearColor(1.0f, 0.78f, 0.35f);
	if (Key == TEXT("mercury")) return FLinearColor(0.55f, 0.53f, 0.50f);
	if (Key == TEXT("venus")) return FLinearColor(0.85f, 0.75f, 0.55f);
	if (Key == TEXT("earth")) return FLinearColor(0.20f, 0.40f, 0.75f);
	if (Key == TEXT("moon")) return FLinearColor(0.62f, 0.62f, 0.60f);
	if (Key == TEXT("mars")) return FLinearColor(0.72f, 0.35f, 0.20f);
	if (Key == TEXT("jupiter")) return FLinearColor(0.80f, 0.68f, 0.52f);
	if (Key == TEXT("saturn")) return FLinearColor(0.85f, 0.78f, 0.58f);
	if (Key == TEXT("uranus")) return FLinearColor(0.60f, 0.82f, 0.86f);
	if (Key == TEXT("neptune")) return FLinearColor(0.30f, 0.45f, 0.85f);
	return FLinearColor(0.7f, 0.65f, 0.6f);
}
}  // namespace

AKozmoSolarSystem::AKozmoSolarSystem()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SunLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("SunLight"));
	SunLight->SetupAttachment(RootComponent);
	SunLight->SetIntensity(5.0e8f);
	SunLight->SetAttenuationRadius(2.0e5f);
	SunLight->SetLightColor(FLinearColor(1.0f, 0.95f, 0.88f));
	SunLight->SetCastShadows(false);
}

float AKozmoSolarSystem::VisualDistance(float DistanceMkm)
{
	// 1 AU ~ 5200 birim, Neptün ~ 26000 birim (log ölçek)
	const float Au = DistanceMkm / 149.6f;
	return 6000.f * FMath::Log2(1.f + Au * 2.f);
}

float AKozmoSolarSystem::VisualRadius(float DiameterKm, bool bStar)
{
	if (bStar) return 900.f;
	return 120.f * FMath::Pow(DiameterKm / 12756.f, 0.45f);
}

void AKozmoSolarSystem::BeginPlay()
{
	Super::BeginPlay();
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UMaterialInterface* BaseMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (!Sphere || !BaseMat)
	{
		UE_LOG(LogKozmo, Error, TEXT("Motor temel şekilleri yüklenemedi (/Engine/BasicShapes)"));
		return;
	}
	const UKozmoSubsystem* Kozmo = GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
	if (!Kozmo) return;

	for (const FKozmoBodyInfo& B : Kozmo->GetBodies())
	{
		const bool bStar = false;
		FBodyVisual V;
		V.Key = B.Key;
		V.Parent = B.Parent;
		V.Distance = B.Parent == TEXT("sun") ? VisualDistance(B.DistanceMkm) : 420.f;    // Ay: Dünya'ya göre
		V.Mesh = NewObject<UStaticMeshComponent>(this);
		V.Mesh->SetStaticMesh(Sphere);
		V.Mesh->SetupAttachment(RootComponent);
		V.Mesh->RegisterComponent();
		// temel küre 100 birim çaplıdır
		V.Mesh->SetWorldScale3D(FVector(VisualRadius(B.DiameterKm, bStar) / 50.f));
		UMaterialInstanceDynamic* Mid = UMaterialInstanceDynamic::Create(BaseMat, this);
		Mid->SetVectorParameterValue(TEXT("Color"), BodyColor(B.Key));
		V.Mesh->SetMaterial(0, Mid);
		V.Label = NewObject<UTextRenderComponent>(this);
		V.Label->SetupAttachment(RootComponent);
		V.Label->RegisterComponent();
		V.Label->SetText(FText::FromString(B.Name));
		V.Label->SetWorldSize(140.f);
		V.Label->SetHorizontalAlignment(EHTA_Center);
		V.Label->SetTextRenderColor(FColor(225, 228, 235));
		MeshRefs.Add(V.Mesh);
		LabelRefs.Add(V.Label);
		Bodies.Add(V);
	}
	// Güneş: kendi ışığını engellemesin diye gölge atmayan küre
	UStaticMeshComponent* Sun = NewObject<UStaticMeshComponent>(this);
	Sun->SetStaticMesh(Sphere);
	Sun->SetupAttachment(RootComponent);
	Sun->RegisterComponent();
	Sun->SetWorldScale3D(FVector(VisualRadius(1392700.f, true) / 50.f));
	Sun->SetCastShadow(false);
	UMaterialInstanceDynamic* SunMat = UMaterialInstanceDynamic::Create(BaseMat, this);
	SunMat->SetVectorParameterValue(TEXT("Color"), BodyColor(TEXT("sun")));
	Sun->SetMaterial(0, SunMat);
	MeshRefs.Add(Sun);
	SunLight->SetRelativeLocation(FVector(0.f, 0.f, 0.f));
}

void AKozmoSolarSystem::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const UKozmoSubsystem* Kozmo = GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
	if (!Kozmo) return;
	TMap<FString, FVector> Pos;
	for (const FBodyVisual& V : Bodies)
	{
		if (V.Parent != TEXT("sun")) continue;
		const float A = FMath::DegreesToRadians(Kozmo->GetBodyLongitudeDeg(V.Key));
		Pos.Add(V.Key, FVector(FMath::Cos(A) * V.Distance, FMath::Sin(A) * V.Distance, 0.f));
	}
	for (const FBodyVisual& V : Bodies)
	{
		FVector P = FVector::ZeroVector;
		if (const FVector* Found = Pos.Find(V.Key))
		{
			P = *Found;
		}
		else if (const FVector* ParentPos = Pos.Find(V.Parent))
		{
			const float A = FMath::DegreesToRadians(Kozmo->GetBodyLongitudeDeg(V.Key));
			P = *ParentPos + FVector(FMath::Cos(A) * V.Distance, FMath::Sin(A) * V.Distance, 0.f);
		}
		V.Mesh->SetRelativeLocation(P);
		V.Label->SetRelativeLocation(P + FVector(0.f, 0.f, V.Mesh->Bounds.SphereRadius + 120.f));
	}
}

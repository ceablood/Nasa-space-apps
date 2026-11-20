#include "KozmoLaunchSite.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "KozmoRocketAssembly.h"
#include "KozmoSubsystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

AKozmoLaunchSite::AKozmoLaunchSite()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(Root);
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->SetIntensity(10.f);                       // lüks; fiziksel gün ışığı ~100000 lux, pozlama ile dengelenir
	Sun->SetLightSourceAngle(0.53f);               // Güneş'in Dünya'dan görünen açısal çapı (gerçek)
	Sun->SetAtmosphereSunLight(true);
	Sun->SetCastShadows(true);
	Sun->SetDynamicShadowCascades(4);
	Sun->SetDynamicShadowDistanceMovableLight(30000.f);

	Sky = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("Sky"));   // varsayılanlar Dünya atmosferi (Bruneton modeli)
	Sky->SetupAttachment(Root);

	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(Root);
	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->bRealTimeCapture = true;
	SkyLight->SetIntensity(1.f);

	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("Fog"));
	Fog->SetupAttachment(Root);
	Fog->SetFogDensity(0.012f);
	Fog->SetFogHeightFalloff(0.2f);
	Fog->SetVolumetricFog(true);
	Fog->SetVolumetricFogScatteringDistribution(0.6f);

	Clouds = CreateDefaultSubobject<UVolumetricCloudComponent>(TEXT("Clouds"));
	Clouds->SetupAttachment(Root);
	Clouds->SetLayerBottomAltitude(2.5f);          // km (kümülüs tabanı ~1-3 km)
	Clouds->SetLayerHeight(6.f);

	Post = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Post"));
	Post->SetupAttachment(Root);
	Post->bUnbound = true;
	FPostProcessSettings& P = Post->Settings;
	// sinematik (key-art) görünüm: hafif bloom, vinyet, soğuk gölgeler / sıcak ışıklar, aşırı beyaz bastırılır
	P.bOverride_BloomIntensity = true;          P.BloomIntensity = 0.55f;
	P.bOverride_VignetteIntensity = true;       P.VignetteIntensity = 0.35f;
	P.bOverride_FilmGrainIntensity = true;      P.FilmGrainIntensity = 0.0f;
	P.bOverride_MotionBlurAmount = true;        P.MotionBlurAmount = 0.0f;
	P.bOverride_ColorSaturation = true;         P.ColorSaturation = FVector4(1.0f, 1.0f, 1.05f, 1.05f);
	P.bOverride_ColorGainShadows = true;        P.ColorGainShadows = FVector4(0.92f, 0.98f, 1.08f, 1.0f);
	P.bOverride_ColorGainHighlights = true;     P.ColorGainHighlights = FVector4(1.04f, 1.0f, 0.94f, 1.0f);
	P.bOverride_LensFlareIntensity = true;      P.LensFlareIntensity = 0.25f;
	P.bOverride_AutoExposureMinBrightness = true; P.AutoExposureMinBrightness = 0.8f;
	P.bOverride_AutoExposureMaxBrightness = true; P.AutoExposureMaxBrightness = 2.0f;

	static ConstructorHelpers::FObjectFinder<UMaterialInterface> MatF(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	BaseMaterial = MatF.Object;
	// motorla gelen basit hacimsel bulut malzemesi; bulunamazsa bulutlar kapalı kalır (sahte görüntü yok)
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> CloudF(
		TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst"));
	CloudMaterial = CloudF.Object;
}

UStaticMeshComponent* AKozmoLaunchSite::AddBlock(UStaticMesh* Mesh, const FVector& Loc, const FVector& Scale, const FLinearColor& Color, float Rough)
{
	if (!Mesh) return nullptr;
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
	C->SetStaticMesh(Mesh);
	C->SetupAttachment(Root);
	C->SetRelativeLocation(Loc);
	C->SetRelativeScale3D(Scale);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (BaseMaterial)
	{
		UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(BaseMaterial, this);
		M->SetVectorParameterValue(TEXT("Color"), Color);
		M->SetScalarParameterValue(TEXT("Roughness"), Rough);
		C->SetMaterial(0, M);
	}
	C->RegisterComponent();
	Blocks.Add(C);
	return C;
}

void AKozmoLaunchSite::BuildPad()
{
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Cyl = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	const FLinearColor Ground(0.16f, 0.17f, 0.13f), Concrete(0.42f, 0.41f, 0.39f), Tower(0.30f, 0.12f, 0.08f), Metal(0.35f, 0.36f, 0.37f);
	// zemin (2 km) ve beton rampa
	AddBlock(Plane, FVector(0, 0, -5.f), FVector(2000.f, 2000.f, 1.f), Ground, 0.95f);
	AddBlock(Cube, FVector(0, 0, -150.f), FVector(60.f, 60.f, 3.f), Concrete, 0.85f);
	// alev kanalı
	AddBlock(Cube, FVector(0, 0, -200.f), FVector(12.f, 40.f, 3.2f), FLinearColor(0.06f, 0.06f, 0.06f), 0.9f);
	// hizmet kulesi: 4 ayaklı kafes, her 6 m'de bir kat (LC-39 / SLC-40 sınıfı ~80 m)
	const FVector T(-1400.f, 0.f, 0.f);
	for (int32 k = 0; k < 4; ++k)
	{
		const FVector Leg = T + FVector((k & 1) ? 350.f : -350.f, (k & 2) ? 350.f : -350.f, 4000.f);
		AddBlock(Cube, Leg, FVector(0.5f, 0.5f, 80.f), Tower, 0.6f);
	}
	for (float Z = 300.f; Z < 8000.f; Z += 600.f)
	{
		AddBlock(Cube, T + FVector(0, 0, Z), FVector(7.4f, 7.4f, 0.3f), Tower, 0.6f);
	}
	// mürettebat erişim kolu ve paratoner direkleri
	AddBlock(Cube, T + FVector(700.f, 0.f, 5200.f), FVector(10.f, 1.6f, 0.4f), Metal, 0.5f);
	for (int32 k = 0; k < 3; ++k)
	{
		const float A = 2.f * PI * k / 3.f + 0.4f;
		AddBlock(Cyl, FVector(FMath::Cos(A), FMath::Sin(A), 0.f) * 9000.f + FVector(0, 0, 6000.f), FVector(1.2f, 1.2f, 120.f), Metal, 0.5f);
	}
	// su kulesi (ses bastırma sistemi)
	AddBlock(Cyl, FVector(6000.f, 7000.f, 3500.f), FVector(1.5f, 1.5f, 70.f), Metal, 0.5f);
	AddBlock(Cyl, FVector(6000.f, 7000.f, 7600.f), FVector(12.f, 12.f, 12.f), FLinearColor(0.62f, 0.62f, 0.60f), 0.6f);
}

void AKozmoLaunchSite::BeginPlay()
{
	Super::BeginPlay();
	if (Clouds) Clouds->SetMaterial(CloudMaterial);
	if (!CloudMaterial && Clouds) Clouds->SetVisibility(false);
	BuildPad();
	SetSunElevation(12.f);   // altın saat: uzun gölgeler, sıcak ışık

	FActorSpawnParameters Params;
	Params.Owner = this;
	Rocket = GetWorld()->SpawnActor<AKozmoRocketAssembly>(GetActorLocation(), FRotator::ZeroRotator, Params);
	if (UKozmoSubsystem* K = GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr)
	{
		if (Rocket) Rocket->Build(K->GetDesign());
		TWeakObjectPtr<AKozmoLaunchSite> Weak(this);
		DesignHandle = K->OnDesignChanged.AddLambda([Weak](const kozmo::prop::Design& D) {
			if (Weak.IsValid() && Weak->Rocket && !Weak->Rocket->IsPlaying()) Weak->Rocket->Build(D);
		});
	}
	ApplyQuality(KozmoGraphics::Current());
}

void AKozmoLaunchSite::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UKozmoSubsystem* K = GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr)
	{
		K->OnDesignChanged.Remove(DesignHandle);
	}
	if (Rocket) Rocket->Destroy();
	Super::EndPlay(Reason);
}

void AKozmoLaunchSite::SetSunElevation(float Degrees)
{
	if (Sun) Sun->SetWorldRotation(FRotator(-FMath::Clamp(Degrees, -10.f, 90.f), 35.f, 0.f));
}

void AKozmoLaunchSite::ApplyQuality(EKozmoQuality Q)
{
	const KozmoGraphics::FProfile& P = KozmoGraphics::Get(Q);
	if (Fog) Fog->SetVolumetricFog(P.bVolumetricFog);
	if (Clouds) Clouds->SetVisibility(P.bVolumetricClouds && CloudMaterial != nullptr);
	if (Sun) Sun->SetDynamicShadowCascades(P.Scalability >= 2 ? 4 : 2);
}

FVector AKozmoLaunchSite::GetViewPoint() const
{
	const float H = Rocket ? Rocket->GetTotalHeightCm() : 7000.f;
	return GetActorLocation() + FVector(-H * 1.1f, -H * 0.8f, H * 0.45f);
}

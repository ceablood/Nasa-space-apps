#include "KozmoRocketAssembly.h"

#include "KozmoSubsystem.h"   // KozmoStr

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
constexpr float Cm = 100.f;   // 1 m = 100 Unreal birimi
// Temel şekiller 100 birimlik birim gövdelerdir: silindir/küp merkezde, koni tabanı altta
FVector CylScale(float DiameterM, float LengthM) { return FVector(DiameterM, DiameterM, LengthM); }

// Renk paleti (key-art tonları; aşırı parlak saf beyaz yok)
const FLinearColor Paint(0.78f, 0.79f, 0.80f);          // kirli beyaz boya
const FLinearColor Soot(0.035f, 0.035f, 0.04f);         // kademeler arası karbon / is
const FLinearColor Steel(0.56f, 0.57f, 0.58f);          // paslanmaz çelik (metan kademesi)
const FLinearColor Bell(0.10f, 0.09f, 0.085f);          // nozul
const FLinearColor Orange(0.62f, 0.26f, 0.06f);         // köpük yalıtım (hidrojen tankı)
const FLinearColor Srb(0.70f, 0.70f, 0.68f);

int32 RingCount(int32 N) { return N <= 1 ? 0 : (N <= 4 ? N : N - 1); }   // 9 motor -> 1 merkez + 8 halka
}  // namespace

AKozmoRocketAssembly::AKozmoRocketAssembly()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Body = CreateDefaultSubobject<USceneComponent>(TEXT("Body"));
	Body->SetupAttachment(Root);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylF(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> ConeF(TEXT("/Engine/BasicShapes/Cone.Cone"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeF(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphF(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> MatF(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	Cylinder = CylF.Object;
	Cone = ConeF.Object;
	Cube = CubeF.Object;
	Sphere = SphF.Object;
	BaseMaterial = MatF.Object;

	Plume = CreateDefaultSubobject<UPointLightComponent>(TEXT("Plume"));
	Plume->SetupAttachment(Body);
	Plume->SetIntensity(0.f);
	Plume->SetLightColor(FLinearColor(1.f, 0.55f, 0.22f));
	Plume->SetAttenuationRadius(20000.f);
	Plume->SetCastShadows(false);
}

UMaterialInstanceDynamic* AKozmoRocketAssembly::MakeMaterial(const FLinearColor& Color, float Metallic, float Roughness)
{
	if (!BaseMaterial) return nullptr;
	UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(BaseMaterial, this);
	// BasicShapeMaterial'in "Color" parametresi var; diğerleri yoksa sessizce yok sayılır.
	M->SetVectorParameterValue(TEXT("Color"), Color);
	M->SetScalarParameterValue(TEXT("Metallic"), Metallic);
	M->SetScalarParameterValue(TEXT("Roughness"), Roughness);
	return M;
}

UStaticMeshComponent* AKozmoRocketAssembly::AddShape(UStaticMesh* Shape, const FVector& Loc, const FVector& Scale, const FRotator& Rot,
	const FLinearColor& Color, float Metallic, float Roughness, EPart Kind, int32 Stage)
{
	if (!Shape) return nullptr;
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
	C->SetStaticMesh(Shape);
	C->SetupAttachment(Kind == EPart::Static ? Root.Get() : Body.Get());
	C->SetRelativeLocationAndRotation(Loc, Rot);
	C->SetRelativeScale3D(Scale);
	C->SetMobility(EComponentMobility::Movable);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (UMaterialInstanceDynamic* M = MakeMaterial(Color, Metallic, Roughness)) C->SetMaterial(0, M);
	C->RegisterComponent();
	Owned.Add(C);
	FPart P;
	P.Mesh = C;
	P.Kind = Kind;
	P.Stage = Stage;
	Parts.Add(P);
	return C;
}

void AKozmoRocketAssembly::Clear()
{
	for (UStaticMeshComponent* C : Owned)
		if (C) C->DestroyComponent();
	for (UTextRenderComponent* T : Labels)
		if (T) T->DestroyComponent();
	Owned.Reset();
	Labels.Reset();
	Parts.Reset();
	if (PlumeMesh) PlumeMesh = nullptr;
	Body->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
}

FString AKozmoRocketAssembly::Build(const kozmo::prop::Design& Design)
{
	StopAscent();
	auto G = kozmo::vehicle::geometry(Design);
	if (!G.ok()) return KozmoStr(G.error().message);
	Clear();
	const kozmo::vehicle::Geometry& Geo = G.value();

	for (int32 i = 0; i < static_cast<int32>(Geo.stages.size()); ++i)
	{
		const kozmo::vehicle::StageGeometry& S = Geo.stages[i];
		const kozmo::prop::Stage& DS = Design.stages[i];
		auto E = kozmo::prop::find_engine(DS.engine);
		const std::string PropKey = E.ok() ? E.value()->propellant : std::string();
		const float D = S.diameter_m;
		float Z = S.base_m;
		// motorlar: halka + merkez düzeni, nozul aşağı bakan koni
		const int32 N = FMath::Max(1, DS.engine_count);
		const int32 Ring = RingCount(N);
		const float BellD = FMath::Min(D * 0.9f / FMath::Max(1.f, FMath::Sqrt(static_cast<float>(N))) * 1.15f, D * 0.9f);
		const float BellL = S.engine_section_m * 0.75f;
		for (int32 k = 0; k < N; ++k)
		{
			FVector2D Off(0.f, 0.f);
			if (Ring > 0 && (k < Ring))
			{
				const float A = 2.f * PI * k / Ring;
				Off = FVector2D(FMath::Cos(A), FMath::Sin(A)) * (D * 0.5f - BellD * 0.5f);
			}
			AddShape(Cone, FVector(Off.X, Off.Y, Z + BellL * 0.5f) * Cm, CylScale(BellD, BellL), FRotator(180.f, 0.f, 0.f), Bell, 0.9f,
				0.35f, EPart::Stage, i);
		}
		// motor bölümü (iskelet + ısı kalkanı)
		AddShape(Cylinder, FVector(0, 0, Z + S.engine_section_m * 0.85f) * Cm, CylScale(D * 0.98f, S.engine_section_m * 0.3f), FRotator::ZeroRotator,
			Soot, 0.2f, 0.7f, EPart::Stage, i);
		Z += S.engine_section_m;
		if (i > 0)
		{
			AddShape(Cylinder, FVector(0, 0, Z + 0.75f) * Cm, CylScale(D, 1.5f), FRotator::ZeroRotator, Soot, 0.1f, 0.8f, EPart::Stage, i);
			Z += 1.5f;
		}
		// tank: yakıta göre yüzey (kerosen beyaz boya, metan çelik, hidrojen turuncu köpük)
		FLinearColor TankColor = Paint;
		float Metal = 0.05f, Rough = 0.45f;
		if (PropKey == "CH4/LOX") { TankColor = Steel; Metal = 1.f; Rough = 0.25f; }
		if (PropKey == "LH2/LOX" && i == 0) { TankColor = Orange; Rough = 0.85f; }
		AddShape(Cylinder, FVector(0, 0, Z + S.tank_length_m * 0.5f) * Cm, CylScale(D, S.tank_length_m), FRotator::ZeroRotator, TankColor, Metal,
			Rough, EPart::Stage, i);
		// oksitleyici/yakıt tankı arası ortak perde çizgisi (görsel ipucu)
		if (S.oxidizer_t > 0)
		{
			const double Ox = S.oxidizer_t / FMath::Max(1e-6, S.oxidizer_t + S.fuel_t);
			AddShape(Cylinder, FVector(0, 0, Z + S.tank_length_m * (1.0 - Ox * 0.6)) * Cm, CylScale(D * 1.005f, 0.12f), FRotator::ZeroRotator,
				Soot, 0.1f, 0.6f, EPart::Stage, i);
		}
		// ilk kademe yeniden kullanılabilir ve inişliyse ızgara kanatçıklar + iniş bacakları
		if (i == 0 && Design.land && PropKey != "LH2/LOX")
		{
			for (int32 k = 0; k < 4; ++k)
			{
				const float A = PI * 0.5f * k + PI * 0.25f;
				const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
				AddShape(Cube, (Dir * (D * 0.5f + 0.6f) + FVector(0, 0, Z + S.tank_length_m - 1.0f)) * Cm, FVector(1.2f, 0.12f, 1.5f),
					FRotator(0.f, FMath::RadiansToDegrees(A) + 90.f, 0.f), Soot, 0.8f, 0.4f, EPart::Stage, i);
				AddShape(Cube, (Dir * (D * 0.5f + 0.1f) + FVector(0, 0, S.base_m + S.engine_section_m + 4.f)) * Cm, FVector(0.3f, 0.5f, 8.f),
					FRotator(0.f, FMath::RadiansToDegrees(A), 0.f), Soot, 0.6f, 0.5f, EPart::Stage, i);
			}
		}
		UTextRenderComponent* T = NewObject<UTextRenderComponent>(this);
		T->SetupAttachment(Root);
		T->SetRelativeLocation(FVector(0.f, (D * 0.5f + 3.f) * Cm, (Z + S.tank_length_m * 0.5f) * Cm));
		T->SetRelativeRotation(FRotator(0.f, 90.f, 0.f));
		T->SetText(FText::FromString(FString::Printf(TEXT("%s  %.1f m x %.1f m\n%.0f t yakıt (%s)"), *KozmoStr(S.label), S.stage_length_m, D,
			DS.propellant_t, *KozmoStr(PropKey))));
		T->SetWorldSize(70.f);
		T->SetTextRenderColor(FColor(200, 220, 235));
		T->RegisterComponent();
		Labels.Add(T);
	}

	// burun konisi / fairing: silindir + koni + yuvarlatılmış uç
	const float TopD = Geo.stages.back().diameter_m;
	const float FairBase = Geo.total_height_m - Geo.fairing_length_m;
	const float Nose = 1.5f * TopD;
	const float Cyl = FMath::Max(0.f, static_cast<float>(Geo.fairing_length_m) - Nose);
	if (Cyl > 0.f)
		AddShape(Cylinder, FVector(0, 0, FairBase + Cyl * 0.5f) * Cm, CylScale(TopD, Cyl), FRotator::ZeroRotator, Paint, 0.05f, 0.4f, EPart::Fairing, 0);
	AddShape(Cone, FVector(0, 0, FairBase + Cyl + Nose * 0.5f) * Cm, CylScale(TopD, Nose), FRotator::ZeroRotator, Paint, 0.05f, 0.4f, EPart::Fairing, 0);
	// yük (fairing ayrılınca görünür)
	AddShape(Cylinder, FVector(0, 0, FairBase + Cyl * 0.5f + 0.5f) * Cm, CylScale(TopD * 0.6f, FMath::Max(1.f, Cyl * 0.7f)), FRotator::ZeroRotator,
		FLinearColor(0.55f, 0.45f, 0.18f), 1.f, 0.3f, EPart::Payload, 0);

	// yan güçlendiriciler
	if (Geo.boosters.count > 0)
	{
		const float CoreR = Geo.stages.front().diameter_m * 0.5f;
		const float BR = Geo.boosters.diameter_m * 0.5f;
		const float L = Geo.boosters.length_m;
		for (int32 k = 0; k < Geo.boosters.count; ++k)
		{
			const float A = 2.f * PI * k / Geo.boosters.count;
			const FVector P = FVector(FMath::Cos(A), FMath::Sin(A), 0.f) * (CoreR + BR + 0.2f);
			AddShape(Cylinder, (P + FVector(0, 0, L * 0.5f)) * Cm, CylScale(BR * 2.f, L - BR * 1.2f), FRotator::ZeroRotator, Srb, 0.1f, 0.5f,
				EPart::Booster, 0);
			AddShape(Cone, (P + FVector(0, 0, L - BR * 0.6f)) * Cm, CylScale(BR * 2.f, BR * 1.2f), FRotator::ZeroRotator, Srb, 0.1f, 0.5f, EPart::Booster, 0);
			AddShape(Cone, (P + FVector(0, 0, 1.f)) * Cm, CylScale(BR * 1.6f, 2.f), FRotator(180.f, 0.f, 0.f), Bell, 0.9f, 0.35f, EPart::Booster, 0);
		}
	}
	// motor alevi (oynatmada görünür): emissive yerine parlak turuncu koni + nokta ışık
	PlumeMesh = AddShape(Cone, FVector(0, 0, -8.f) * Cm, CylScale(Geo.stages.front().diameter_m * 1.2f, 16.f), FRotator(180.f, 0.f, 0.f),
		FLinearColor(1.f, 0.6f, 0.25f), 0.f, 1.f, EPart::Stage, -1);
	if (PlumeMesh) PlumeMesh->SetVisibility(false);
	Plume->SetRelativeLocation(FVector(0, 0, -10.f * Cm));
	TotalHeightCm = Geo.total_height_m * Cm;
	return FString();
}

void AKozmoRocketAssembly::Detach(EPart Kind, int32 Stage)
{
	for (FPart& P : Parts)
	{
		if (P.bDetached || P.Kind != Kind || (Kind == EPart::Stage && P.Stage != Stage)) continue;
		P.bDetached = true;
		const FVector W = P.Mesh->GetComponentLocation();
		const FRotator R = P.Mesh->GetComponentRotation();
		P.Mesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
		P.Mesh->SetWorldLocationAndRotation(W, R);
		const FVector Side = (W - Body->GetComponentLocation()).GetSafeNormal2D();
		P.DropVelocity = Side * 600.f + FVector(0, 0, -900.f);
		if (Kind == EPart::Stage && P.Mesh == PlumeMesh) P.Mesh->SetVisibility(false);
	}
}

FString AKozmoRocketAssembly::PlayAscent(const kozmo::prop::Design& Design, float TimeScale)
{
	const FString Err = Build(Design);
	if (!Err.IsEmpty()) return Err;
	auto R = kozmo::flight::simulate_ascent(Design, kozmo::flight::AscentConfig{});
	if (!R.ok()) return KozmoStr(R.error().message);
	Ascent = R.value();
	PlayT = 0.f;
	PlayScale = FMath::Clamp(TimeScale, 1.f, 100.f);
	NextEvent = 0;
	Downrange = 0.0;
	bPlaying = Ascent.telemetry.size() > 1;
	if (PlumeMesh) PlumeMesh->SetVisibility(true);
	Plume->SetIntensity(5.0e6f);
	return FString::Printf(TEXT("%s — %.0f x %.0f km, Max-Q %.1f kPa, en yüksek ivme %.1f g"), Ascent.orbit ? TEXT("YÖRÜNGE") : TEXT("BAŞARISIZ"),
		Ascent.final_orbit.periapsis_alt_m / 1000.0, Ascent.final_orbit.apoapsis_alt_m / 1000.0, Ascent.max_q_pa / 1000.0, Ascent.max_accel_g);
}

FVector AKozmoRocketAssembly::GetBodyLocation() const
{
	return Body->GetComponentLocation() + Body->GetUpVector() * TotalHeightCm * 0.5f;
}

void AKozmoRocketAssembly::StopAscent()
{
	bPlaying = false;
	if (Plume) Plume->SetIntensity(0.f);
}

void AKozmoRocketAssembly::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// ayrılan parçalar: basit balistik düşüş (görsel; çekirdekteki uçuş fiziğinden bağımsız)
	for (FPart& P : Parts)
	{
		if (!P.bDetached || !P.Mesh) continue;
		P.DropVelocity.Z -= 981.f * DeltaSeconds;
		P.Mesh->AddWorldOffset(P.DropVelocity * DeltaSeconds);
		P.Mesh->AddWorldRotation(FRotator(20.f * DeltaSeconds, 0.f, 8.f * DeltaSeconds));
	}
	if (!bPlaying) return;
	PlayT += DeltaSeconds * PlayScale;
	const auto& Tel = Ascent.telemetry;
	// telemetri örnekleri arasında doğrusal ara değer
	int32 i = 0;
	while (i + 1 < static_cast<int32>(Tel.size()) && Tel[i + 1].t_s < PlayT) ++i;
	if (i + 1 >= static_cast<int32>(Tel.size()))
	{
		StopAscent();
		return;
	}
	const auto& A = Tel[i];
	const auto& B = Tel[i + 1];
	const double F = FMath::Clamp((PlayT - A.t_s) / FMath::Max(1e-6, B.t_s - A.t_s), 0.0, 1.0);
	const double Alt = FMath::Lerp(A.altitude_m, B.altitude_m, F);
	const double Pitch = FMath::Lerp(A.pitch_deg, B.pitch_deg, F);      // ufka göre derece (90 = dikey)
	const double Speed = FMath::Lerp(A.speed_ms, B.speed_ms, F);
	Downrange += Speed * FMath::Cos(FMath::DegreesToRadians(Pitch)) * DeltaSeconds * PlayScale;
	Body->SetRelativeLocation(FVector(Downrange * VisualAltitudeScale * Cm, 0.0, Alt * VisualAltitudeScale * Cm));
	Body->SetRelativeRotation(FRotator(0.f, 0.f, 0.f) + FRotator(-(90.0 - Pitch), 0.f, 0.f));
	while (NextEvent < static_cast<int32>(Ascent.events.size()) && Ascent.events[NextEvent].t_s <= PlayT)
	{
		const auto& E = Ascent.events[NextEvent++];
		using kozmo::flight::EventType;
		if (E.type == EventType::BoosterSeparation) Detach(EPart::Booster, 0);
		if (E.type == EventType::StageSeparation) Detach(EPart::Stage, E.stage - 2);   // olay yeni kademeyi (1 tabanlı) taşır; atılan = önceki
		if (E.type == EventType::FairingSeparation) Detach(EPart::Fairing, 0);
		if (E.type == EventType::Crash || E.type == EventType::OutOfPropellant || E.type == EventType::OrbitAchieved) StopAscent();
	}
}

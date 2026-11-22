#include "KozmoRoverPawn.h"

#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/TextRenderComponent.h"
#include "KozmoShapes.h"
#include "KozmoSubsystem.h"
#include "KozmoTerrainActor.h"

AKozmoRoverPawn::AKozmoRoverPawn()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Root);
	Camera->SetRelativeLocation(FVector(-450.f, 0.f, 260.f));
	Camera->SetRelativeRotation(FRotator(-15.f, 0.f, 0.f));
	Camera->bUsePawnControlRotation = false;
}

void AKozmoRoverPawn::Setup(AKozmoTerrainActor* InTerrain, const FString& Key, const FString& Body)
{
	Terrain = InTerrain;
	auto S = kozmo::rover::find(KozmoStd(Key));
	Rover = MakeUnique<kozmo::rover::Rover>(*(S.ok() ? S.value() : &kozmo::rover::catalog().front()));
	Rover->set_load(300);
	auto E = kozmo::challenge::body_environment(KozmoStd(Body));
	if (E.ok()) Env = E.value();
	Start = GetActorLocation();
	// gövde: şasi, 4 tekerlek, anten, güneş paneli (LRV benzeri açık şasi)
	const FLinearColor Frame(0.55f, 0.56f, 0.58f), Tire(0.12f, 0.12f, 0.12f), Gold(0.62f, 0.48f, 0.16f);
	KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(0, 0, 0.7f), FVector(3.0f, 1.8f, 0.15f), Frame, 0.5f, 0.6f, FRotator::ZeroRotator, false);
	for (int32 i = 0; i < 4; ++i)
		KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, FVector((i & 1) ? 1.1f : -1.1f, (i & 2) ? 1.0f : -1.0f, 0.4f), FVector(0.8f, 0.8f, 0.25f), Tire, 0.9f, 0.f,
			FRotator(0.f, 0.f, 90.f), false);
	KozmoShapes::Add(this, Root, EKozmoShape::Cone, FVector(-1.2f, 0, 1.8f), FVector(0.8f, 0.8f, 0.2f), Gold, 0.4f, 0.9f, FRotator(180.f, 0, 0), false);
	KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, FVector(-1.2f, 0, 1.2f), FVector(0.05f, 0.05f, 1.0f), Frame, 0.4f, 0.8f, FRotator::ZeroRotator, false);
	Dash = KozmoShapes::Label(this, Root, FVector(0.8f, 0, 1.4f), TEXT(""), 14.f, FColor(150, 230, 255), FRotator(0.f, 180.f, 0.f));
}

void AKozmoRoverPawn::SetupPlayerInputComponent(UInputComponent* In)
{
	Super::SetupPlayerInputComponent(In);
	In->BindAxis(TEXT("MoveForward"), this, &AKozmoRoverPawn::Throttle);
	In->BindAxis(TEXT("MoveRight"), this, &AKozmoRoverPawn::Steer);
}

FString AKozmoRoverPawn::Status() const
{
	if (!Rover) return FString();
	return FString::Printf(TEXT("%s | hız %.1f km/h | batarya %.2f/%.1f kWh | odometre %.2f km | eğim %.1f° %s"), *KozmoStr(Rover->spec().name), Speed * 3.6f,
		Rover->battery(), Rover->spec().battery_kwh, Rover->odometer() / 1000.0, Terrain ? Terrain->GetSlopeAt(GetActorLocation()) : 0.f, *LastWarning);
}

void AKozmoRoverPawn::Tick(float Dt)
{
	Super::Tick(Dt);
	if (!Rover || !Terrain) return;
	const auto& S = Rover->spec();
	// hız hedefi gaza göre; ivme sınırlı (LRV ~0.5 m/s^2 mertebesi)
	const float Target = Gas * static_cast<float>(S.top_speed_ms);
	Speed = FMath::FInterpConstantTo(Speed, Target, Dt, 0.5f);
	Heading += Turn * 35.f * Dt * FMath::Clamp(FMath::Abs(Speed) / 1.5f, 0.2f, 1.f);
	const FVector Dir = FRotator(0.f, Heading, 0.f).Vector();
	const FVector Next = GetActorLocation() + Dir * Speed * 100.f * Dt;
	// çekirdek: bu küçük adımın enerjisi, patinajı ve eğim kontrolü (rota = tek bacak)
	const FVector L0 = (GetActorLocation() - Terrain->GetActorLocation()) / 100.f, L1 = (Next - Terrain->GetActorLocation()) / 100.f;
	const FVector S0 = (Start - Terrain->GetActorLocation()) / 100.f;
	auto R = Rover->traverse(Terrain->Map(), Env, {L0.X, L0.Y}, {{L1.X, L1.Y}}, FMath::Clamp(FMath::Abs(Gas), 0.05f, 1.f), 1.0, 8.0, true);
	if (!R.feasible)
	{
		LastWarning = TEXT("— ") + KozmoStr(R.failure);
		Speed = 0.f;
		return;
	}
	LastWarning.Reset();
	if (FVector::Dist2D(FVector(L1.X, L1.Y, 0), FVector(S0.X, S0.Y, 0)) > kozmo::rover::walkback_limit_m(8.0, Env.gravity_ms2) * 0.9)
		LastWarning = TEXT("— geri yürüyüş sınırına yaklaştın");
	FVector P = Next;
	P.Z = Terrain->GetHeightAt(Next) + 10.f;
	// zemine göre eğilme: ön/arka yükseklik farkı
	const float Front = Terrain->GetHeightAt(Next + Dir * 150.f), Back = Terrain->GetHeightAt(Next - Dir * 150.f);
	const float Pitch = FMath::RadiansToDegrees(FMath::Atan2(Front - Back, 300.f));
	SetActorLocationAndRotation(P, FRotator(Pitch, Heading, 0.f));
	if (Dash) Dash->SetText(FText::FromString(Status()));
}

#include "KozmogenisSpacecraft.h"

#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "KozmoExpedition.h"
#include "KozmoShapes.h"
#include "KozmoSubsystem.h"
#include "KozmogenisCockpitActor.h"

AKozmogenisSpacecraft::AKozmogenisSpacecraft()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Hull = CreateDefaultSubobject<USceneComponent>(TEXT("Hull"));
	Hull->SetupAttachment(Root);
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Root);
	Camera->bUsePawnControlRotation = true;    // baş hareketi: fareyle bakış
	Camera->SetFieldOfView(85.f);
	PlumeLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("PlumeLight"));
	PlumeLight->SetupAttachment(Root);
	PlumeLight->SetRelativeLocation(FVector(0, 0, -300));
	PlumeLight->SetLightColor(FLinearColor(1.f, 0.6f, 0.3f));
	PlumeLight->SetAttenuationRadius(6000.f);
	PlumeLight->SetIntensity(0.f);
	AutoPossessPlayer = EAutoReceiveInput::Disabled;
}

UKozmoSubsystem* AKozmogenisSpacecraft::Kozmo() const
{
	return GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
}

void AKozmogenisSpacecraft::BeginPlay()
{
	Super::BeginPlay();
	BuildHull();
	FActorSpawnParameters P;
	P.Owner = this;
	Cockpit = GetWorld()->SpawnActor<AKozmogenisCockpitActor>(GetActorLocation(), GetActorRotation(), P);
	if (Cockpit)
	{
		Cockpit->AttachToComponent(Hull, FAttachmentTransformRules::KeepRelativeTransform);
		Cockpit->SetActorRelativeLocation(FVector(0.f, 0.f, 520.f));   // üst güverte
		const UKozmoSubsystem* K = Kozmo();
		const auto* E = K ? K->GetExpedition() : nullptr;
		Cockpit->Build(E ? E->craft().cockpit() : kozmo::craft::CockpitLevel::Basic);
		Camera->SetRelativeLocation(Cockpit->GetEyeLocation() - GetActorLocation());
	}
}

void AKozmogenisSpacecraft::BuildHull()
{
	// çekirdek araç parçalarından gövde: tank silindiri, kabin, motor çanları, iniş bacakları, paneller
	const UKozmoSubsystem* K = Kozmo();
	const auto* E = K ? K->GetExpedition() : nullptr;
	const FLinearColor Foil(0.62f, 0.48f, 0.16f), White(0.74f, 0.75f, 0.76f), Dark(0.08f, 0.08f, 0.09f);
	int32 Engines = 0;
	bool Legs = false, Solar = false;
	if (E)
		for (const auto& P : E->craft().installed())
		{
			auto S = kozmo::craft::find_part(P.key);
			if (!S.ok()) continue;
			Engines += S.value()->kind == kozmo::craft::PartKind::Engine;
			Legs |= S.value()->kind == kozmo::craft::PartKind::LandingGear;
			Solar |= S.value()->kind == kozmo::craft::PartKind::SolarPanel;
		}
	const auto Sp = E ? E->craft().specs() : kozmo::craft::Specs{};
	const float D = Sp.width_m > 0 ? Sp.width_m : 4.5f;
	const float L = FMath::Clamp(static_cast<float>(Sp.length_m), 4.f, 14.f);
	KozmoShapes::Add(this, Hull, EKozmoShape::Cylinder, FVector(0, 0, 1.5f + L * 0.25f), FVector(D, D, L * 0.5f), Foil, 0.35f, 0.9f);   // yakıt bölümü (altın folyo)
	KozmoShapes::Add(this, Hull, EKozmoShape::Cylinder, FVector(0, 0, 1.5f + L * 0.5f + 1.2f), FVector(D * 0.8f, D * 0.8f, 2.4f), White, 0.5f);  // kabin
	KozmoShapes::Add(this, Hull, EKozmoShape::Cone, FVector(0, 0, 1.5f + L * 0.5f + 3.0f), FVector(D * 0.8f, D * 0.8f, 1.2f), White, 0.5f);
	for (int32 i = 0; i < FMath::Max(1, Engines); ++i)
	{
		const float A = 2.f * PI * i / FMath::Max(1, Engines);
		const FVector Off = Engines > 1 ? FVector(FMath::Cos(A), FMath::Sin(A), 0) * D * 0.22f : FVector::ZeroVector;
		KozmoShapes::Add(this, Hull, EKozmoShape::Cone, Off + FVector(0, 0, 1.0f), FVector(1.2f, 1.2f, 1.4f), Dark, 0.3f, 0.9f, FRotator(180.f, 0, 0));
	}
	if (Legs)
		for (int32 i = 0; i < 4; ++i)
		{
			const float A = PI * 0.5f * i + PI * 0.25f;
			const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0);
			KozmoShapes::Add(this, Hull, EKozmoShape::Cylinder, Dir * (D * 0.6f) + FVector(0, 0, 1.0f), FVector(0.18f, 0.18f, 2.6f), White, 0.4f, 0.8f,
				FRotator(0.f, 0.f, 0.f) + FRotator(28.f, FMath::RadiansToDegrees(A), 0.f));
			KozmoShapes::Add(this, Hull, EKozmoShape::Cylinder, Dir * (D * 0.85f) + FVector(0, 0, 0.05f), FVector(0.8f, 0.8f, 0.1f), White, 0.5f);
		}
	if (Solar)
		for (int32 i = -1; i <= 1; i += 2)
			KozmoShapes::Add(this, Hull, EKozmoShape::Cube, FVector(0, i * (D * 0.5f + 2.2f), 1.5f + L * 0.4f), FVector(0.05f, 4.f, 1.6f),
				FLinearColor(0.05f, 0.08f, 0.2f), 0.2f, 0.6f);
	// kapak (hatch): dışarıdan araca binmek için etiketli bileşen
	UStaticMeshComponent* Hatch = KozmoShapes::Add(this, Hull, EKozmoShape::Cube, FVector(D * 0.4f, 0, 1.5f + L * 0.5f + 0.6f), FVector(0.1f, 1.0f, 1.4f), Dark, 0.5f);
	Hatch->ComponentTags.Add(TEXT("craft:hatch"));
	Plume = KozmoShapes::Add(this, Hull, EKozmoShape::Cone, FVector(0, 0, -2.5f), FVector(2.f, 2.f, 5.f), FLinearColor(1.f, 0.7f, 0.35f), 1.f, 0.f,
		FRotator(180.f, 0, 0), false);
	Plume->SetVisibility(false);
}

FVector AKozmogenisSpacecraft::GetHatchLocation() const { return GetActorLocation() + FVector(450.f, 0.f, 0.f); }

void AKozmogenisSpacecraft::SetupPlayerInputComponent(UInputComponent* In)
{
	Super::SetupPlayerInputComponent(In);
	In->BindAxis(TEXT("Turn"), this, &APawn::AddControllerYawInput);
	In->BindAxis(TEXT("LookUp"), this, &APawn::AddControllerPitchInput);
	In->BindAxis(TEXT("Throttle"), this, &AKozmogenisSpacecraft::Throttle);
	In->BindAxis(TEXT("MoveRight"), this, &AKozmogenisSpacecraft::PitchInput);
	In->BindAxis(TEXT("Zoom"), this, &AKozmogenisSpacecraft::Zoom);
	In->BindAction(TEXT("Interact"), IE_Pressed, this, &AKozmogenisSpacecraft::Interact);
	In->BindAction(TEXT("Seat"), IE_Pressed, this, &AKozmogenisSpacecraft::SeatToggle);
	In->BindAction(TEXT("Engines"), IE_Pressed, this, &AKozmogenisSpacecraft::ToggleEngines);
	In->BindAction(TEXT("LandingAssist"), IE_Pressed, this, &AKozmogenisSpacecraft::LandingAssist);
	In->BindAction(TEXT("BeginDescent"), IE_Pressed, this, &AKozmogenisSpacecraft::BeginDescent);
	In->BindAction(TEXT("Exit"), IE_Pressed, this, &AKozmogenisSpacecraft::ExitCraft);
}

void AKozmogenisSpacecraft::Feedback(const FString& S)
{
	if (Scene) Scene->SetFeedback(S);
}

void AKozmogenisSpacecraft::SeatToggle()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	auto St = E->player().mode == kozmo::world::PlayerMode::Seated ? E->stand() : E->sit();
	Feedback(St.ok() ? KozmoStr(kozmo::world::to_string(E->player().mode)) : KozmoStr(St.error().message));
}

void AKozmogenisSpacecraft::ToggleEngines()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	auto St = E->craft().set_engines(!E->craft().instruments().engines_on);
	Feedback(St.ok() ? (E->craft().instruments().engines_on ? TEXT("Motorlar ateşlendi") : TEXT("Motorlar kapatıldı")) : KozmoStr(St.error().message));
}

void AKozmogenisSpacecraft::LandingAssist()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	auto St = E->craft().set_mode(kozmo::craft::FlightMode::LandingAssist);
	Feedback(St.ok() ? TEXT("İniş desteği açık: alçalma ve yatay hız bilgisayarda") : KozmoStr(St.error().message));
}

void AKozmogenisSpacecraft::BeginDescent()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	auto St = E->begin_descent();
	Feedback(St.ok() ? TEXT("İniş başladı. Motorları (F) ateşle, iniş desteğini (L) aç ya da elle uç (R/V gaz, A/D yunuslama).") : KozmoStr(St.error().message));
}

void AKozmogenisSpacecraft::ExitCraft()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	auto St = E->exit_craft();
	if (!St.ok())
	{
		Feedback(KozmoStr(St.error().message));
		return;
	}
	if (Scene) Scene->PossessCharacter();
}

void AKozmogenisSpacecraft::Throttle(float V)
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || FMath::IsNearlyZero(V) || E->player().mode != kozmo::world::PlayerMode::Seated) return;
	E->craft().set_throttle(E->craft().instruments().throttle + V * 0.01f);
}

void AKozmogenisSpacecraft::PitchInput(float V)
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || FMath::IsNearlyZero(V) || E->player().mode != kozmo::world::PlayerMode::Seated) return;
	PitchDeg = FMath::Clamp(PitchDeg + V * 0.6f, 0.f, 180.f);
	E->craft().set_pitch_deg(PitchDeg);
}

void AKozmogenisSpacecraft::Zoom(float V)
{
	if (FMath::IsNearlyZero(V)) return;
	Fov = FMath::Clamp(Fov - V * 5.f, 25.f, 100.f);   // kamera yakınlaştırma (pencere dışı ayrıntı)
	Camera->SetFieldOfView(Fov);
}

void AKozmogenisSpacecraft::Interact()
{
	// kameranın baktığı düğmeye bas (fiziksel kokpit etkileşimi)
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !Cockpit) return;
	FHitResult Hit;
	const FVector S = Camera->GetComponentLocation(), End = S + Camera->GetForwardVector() * 250.f;
	FCollisionQueryParams Q;
	Q.AddIgnoredActor(this);
	if (!GetWorld()->LineTraceSingleByChannel(Hit, S, End, ECC_Visibility, Q))
	{
		SeatToggle();   // boşluğa bakarken E: otur/kalk
		return;
	}
	const FString A = Cockpit->ButtonAction(Hit.GetComponent());
	auto& C = E->craft();
	using kozmo::craft::FlightMode;
	if (A == TEXT("engines")) ToggleEngines();
	else if (A == TEXT("landing")) LandingAssist();
	else if (A == TEXT("manual")) Feedback(C.set_mode(FlightMode::Manual).ok() ? TEXT("Manuel uçuş") : TEXT("Mod değiştirilemedi"));
	else if (A == TEXT("auto")) { auto St = C.set_mode(FlightMode::Autopilot); Feedback(St.ok() ? TEXT("Otomatik pilot: irtifa tutma") : KozmoStr(St.error().message)); }
	else if (A == TEXT("emergency")) Feedback(C.set_mode(FlightMode::Emergency).ok() ? TEXT("ACİL DURUM MODU: güvenli iniş prosedürü") : TEXT(""));
	else if (A == TEXT("lights")) C.set_cabin_lights((C.cabin_lights() + 1) % 4);
	else if (A == TEXT("fix"))
	{
		const auto W = C.warnings();
		if (W.empty()) Feedback(TEXT("Etkin arıza yok"));
		else { auto St = C.apply_procedure(W.front().fault); Feedback(St.ok() ? TEXT("Prosedür uygulandı: ") + KozmoStr(W.front().procedure) : KozmoStr(St.error().message)); }
	}
	else SeatToggle();
}

void AKozmogenisSpacecraft::Tick(float Dt)
{
	Super::Tick(Dt);
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !Scene) return;
	const auto& C = E->craft();
	const auto In = C.instruments();
	// konum: çekirdekteki gerçek menzil (iniş alanı hedefine kalan mesafe) ve irtifa; hedef yoksa yörüngede iniş alanının üstü
	const FVector Pad = Scene->LandingPadWorld();
	const double Remaining = C.has_landing_target() ? C.landing_target() - C.downrange() : 0.0;
	SetActorLocation(Pad + FVector(static_cast<float>(-Remaining * 100.0), 0.f, In.altitude_m * 100.f));
	if (Cockpit) Cockpit->SetLevers(In.throttle, PitchDeg);
	if (Cockpit) Cockpit->UpdateFrom(C);
	// motor alevi ve titreşim (kalkış/iniş titreşimi, ayarla azaltılabilir)
	const bool Burning = In.engines_on && In.fuel_t > 0;
	if (Plume) Plume->SetVisibility(Burning);
	PlumeLight->SetIntensity(Burning ? 8.0e5f : 0.f);
	ShakeT += Dt;
	// titreşim: motor (kalkış/iniş) + atmosferde türbülans (dinamik basınçla) + çarpışma tepkisi; ShakeScale ile azaltılabilir
	const int32 Faults = static_cast<int32>(C.faults().size());
	if (Faults > LastFaultCount) CollisionKick = 1.f;
	LastFaultCount = Faults;
	CollisionKick = FMath::Max(0.f, CollisionKick - Dt * 2.f);
	const float Turb = C.phase() == kozmo::craft::FlightPhase::Flying ? static_cast<float>(FMath::Min(1.0, E->env().density_at(In.altitude_m) * In.speed_ms * In.speed_ms / 20000.0)) : 0.f;
	const float Amp = ((Burning ? 0.6f : 0.f) + Turb * 1.5f + CollisionKick * 8.f) * ShakeScale;
	FVector Offset = FVector(FMath::Sin(ShakeT * 47.f), FMath::Cos(ShakeT * 53.f), FMath::Sin(ShakeT * 61.f)) * Amp;
	// sıfır yerçekimi: yörüngede koltukta değilken baş yavaşça süzülür
	if (C.phase() == kozmo::craft::FlightPhase::Orbit && !In.seated)
		Offset += FVector(FMath::Sin(ShakeT * 0.4f) * 6.f, FMath::Cos(ShakeT * 0.3f) * 5.f, FMath::Sin(ShakeT * 0.5f) * 8.f);
	Camera->SetRelativeLocation((Cockpit ? Cockpit->GetEyeLocation() - GetActorLocation() : FVector(0, 0, 640)) + Offset);
}

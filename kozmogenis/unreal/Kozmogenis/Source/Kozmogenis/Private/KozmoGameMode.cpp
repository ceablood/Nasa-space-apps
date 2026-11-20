#include "KozmoGameMode.h"

#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/FloatingPawnMovement.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpectatorPawn.h"
#include "KozmoLaunchSite.h"
#include "KozmoRocketAssembly.h"
#include "KozmoSolarSystem.h"
#include "KozmoSubsystem.h"
#include "SKozmoDashboard.h"
#include "SKozmoDesigner.h"
#include "Widgets/SWeakWidget.h"

AKozmoGameMode::AKozmoGameMode()
{
	DefaultPawnClass = ASpectatorPawn::StaticClass();   // WASD + fare ile serbest uçuş kamerası
	PrimaryActorTick.bCanEverTick = true;               // fırlatma sırasında kamera roketi izler
}

void AKozmoGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	if (!World) return;
	SolarSystem = World->SpawnActor<AKozmoSolarSystem>(FVector::ZeroVector, FRotator::ZeroRotator);

	UKozmoSubsystem* Kozmo = GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;

	if (APlayerController* PC = World->GetFirstPlayerController())
	{
		if (APawn* Pawn = PC->GetPawn())
		{
			// iç gezegenleri yukarıdan-çapraz gören başlangıç noktası
			const FVector Start(-16000.f, -16000.f, 14000.f);
			Pawn->SetActorLocation(Start);
			PC->SetControlRotation((FVector::ZeroVector - Start).Rotation());
			if (UFloatingPawnMovement* Move = Cast<UFloatingPawnMovement>(Pawn->GetMovementComponent()))
			{
				Move->MaxSpeed = 12000.f;
				Move->Acceleration = 30000.f;
			}
		}
		PC->bShowMouseCursor = true;
		FInputModeGameAndUI Mode;
		Mode.SetHideCursorDuringCapture(false);
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		PC->SetInputMode(Mode);
	}

	if (GEngine && GEngine->GameViewport && Kozmo)
	{
		SAssignNew(Dashboard, SKozmoDashboard).Subsystem(Kozmo);
		DashboardContainer = SNew(SWeakWidget).PossiblyNullContent(Dashboard.ToSharedRef());
		GEngine->GameViewport->AddViewportWidgetContent(DashboardContainer.ToSharedRef(), 10);
		SAssignNew(Designer, SKozmoDesigner).Subsystem(Kozmo).GameMode(this);
		DesignerContainer = SNew(SWeakWidget).PossiblyNullContent(Designer.ToSharedRef());
		GEngine->GameViewport->AddViewportWidgetContent(DesignerContainer.ToSharedRef(), 11);
	}
}

void AKozmoGameMode::EndPlay(const EEndPlayReason::Type Reason)
{
	if (GEngine && GEngine->GameViewport && DashboardContainer.IsValid())
	{
		GEngine->GameViewport->RemoveViewportWidgetContent(DashboardContainer.ToSharedRef());
	}
	if (GEngine && GEngine->GameViewport && DesignerContainer.IsValid())
	{
		GEngine->GameViewport->RemoveViewportWidgetContent(DesignerContainer.ToSharedRef());
	}
	Designer.Reset();
	DesignerContainer.Reset();
	Dashboard.Reset();
	DashboardContainer.Reset();
	Super::EndPlay(Reason);
}

namespace
{
// Rampa sahnesi Güneş Sistemi'nden uzağa kurulur (100 km); gökyüzü atmosferi gezegen tepesini bu noktaya koyar.
const FVector GLaunchSiteOrigin(0.f, 0.f, -10000000.f);
}

void AKozmoGameMode::MovePawn(const FVector& Location, const FVector& LookAt, float Speed)
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn) return;
	Pawn->SetActorLocation(Location);
	PC->SetControlRotation((LookAt - Location).Rotation());
	if (UFloatingPawnMovement* Move = Cast<UFloatingPawnMovement>(Pawn->GetMovementComponent()))
	{
		Move->MaxSpeed = Speed;
		Move->Acceleration = Speed * 2.5f;
	}
}

void AKozmoGameMode::ShowLaunchSite(bool bShow)
{
	UWorld* World = GetWorld();
	if (!World) return;
	if (bShow)
	{
		if (!LaunchSite) LaunchSite = World->SpawnActor<AKozmoLaunchSite>(GLaunchSiteOrigin, FRotator::ZeroRotator);
		if (SolarSystem) SolarSystem->SetActorHiddenInGame(true);
		if (LaunchSite) MovePawn(LaunchSite->GetViewPoint(), GLaunchSiteOrigin + FVector(0, 0, 3000.f), 3000.f);
	}
	else
	{
		if (LaunchSite) LaunchSite->Destroy();
		LaunchSite = nullptr;
		if (SolarSystem) SolarSystem->SetActorHiddenInGame(false);
		MovePawn(FVector(-16000.f, -16000.f, 14000.f), FVector::ZeroVector, 12000.f);
	}
}

FString AKozmoGameMode::PlayDesignAscent()
{
	UKozmoSubsystem* Kozmo = GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
	if (!Kozmo) return TEXT("Oyun çekirdeği yok");
	ShowLaunchSite(true);
	if (!LaunchSite || !LaunchSite->GetRocket()) return TEXT("Rampa sahnesi kurulamadı");
	return LaunchSite->GetRocket()->PlayAscent(Kozmo->GetDesign(), 10.f);
}

void AKozmoGameMode::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	AKozmoRocketAssembly* Rocket = LaunchSite ? LaunchSite->GetRocket() : nullptr;
	if (!Rocket || !Rocket->IsPlaying()) return;
	APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn) return;
	// yumuşak takip: roketin yan-arkasından, boyunun ~1.5 katı uzaklıktan
	const FVector Target = Rocket->GetBodyLocation();
	const float H = FMath::Max(3000.f, Rocket->GetTotalHeightCm());
	const FVector Desired = Target + FVector(-H * 1.2f, -H * 0.9f, H * 0.2f);
	Pawn->SetActorLocation(FMath::VInterpTo(Pawn->GetActorLocation(), Desired, DeltaSeconds, 2.5f));
	PC->SetControlRotation((Target - Pawn->GetActorLocation()).Rotation());
}

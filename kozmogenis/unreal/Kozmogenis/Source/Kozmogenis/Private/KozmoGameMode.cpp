#include "KozmoGameMode.h"

#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/FloatingPawnMovement.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpectatorPawn.h"
#include "KozmoSolarSystem.h"
#include "KozmoSubsystem.h"
#include "SKozmoDashboard.h"
#include "Widgets/SWeakWidget.h"

AKozmoGameMode::AKozmoGameMode()
{
	DefaultPawnClass = ASpectatorPawn::StaticClass();   // WASD + fare ile serbest uçuş kamerası
}

void AKozmoGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	if (!World) return;
	World->SpawnActor<AKozmoSolarSystem>(FVector::ZeroVector, FRotator::ZeroRotator);

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
	}
}

void AKozmoGameMode::EndPlay(const EEndPlayReason::Type Reason)
{
	if (GEngine && GEngine->GameViewport && DashboardContainer.IsValid())
	{
		GEngine->GameViewport->RemoveViewportWidgetContent(DashboardContainer.ToSharedRef());
	}
	Dashboard.Reset();
	DashboardContainer.Reset();
	Super::EndPlay(Reason);
}

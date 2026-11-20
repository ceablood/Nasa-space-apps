// KOZMOGENİS — oyuncunun kullandığı uzay aracı (V41 §2): çekirdekteki world::Expedition'ın aracını
// (craft::Spacecraft) 3B gövde + kokpit olarak gösterir ve kumanda eder. Uçuş fiziği çekirdektedir.
// Kontroller: E düğmeye bas/otur-kalk, F motorlar, L iniş desteği, B inişi başlat, R/V gaz, A/D yunuslama,
// X araçtan çık, fare bakış. Kamera sarsıntısı ayarlardan azaltılabilir (ShakeScale).
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "KozmogenisSpacecraft.generated.h"

class UCameraComponent;
class AKozmogenisCockpitActor;
class AKozmoExpeditionScene;
class UPointLightComponent;
class UStaticMeshComponent;

UCLASS()
class KOZMOGENIS_API AKozmogenisSpacecraft : public APawn
{
	GENERATED_BODY()

public:
	AKozmogenisSpacecraft();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;

	void SetScene(AKozmoExpeditionScene* InScene) { Scene = InScene; }
	/** Kamera sarsıntısı çarpanı (0 kapalı .. 1 tam). Erişilebilirlik ayarı. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kozmo") float ShakeScale = 1.f;
	FVector GetHatchLocation() const;

private:
	void BuildHull();
	void Interact();
	void ToggleEngines();
	void LandingAssist();
	void BeginDescent();
	void ExitCraft();
	void SeatToggle();
	void Throttle(float V);
	void PitchInput(float V);
	void Feedback(const FString& S);
	class UKozmoSubsystem* Kozmo() const;

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<USceneComponent> Hull;
	UPROPERTY() TObjectPtr<UCameraComponent> Camera;
	UPROPERTY() TObjectPtr<AKozmogenisCockpitActor> Cockpit;
	UPROPERTY() TObjectPtr<AKozmoExpeditionScene> Scene;
	UPROPERTY() TObjectPtr<UPointLightComponent> PlumeLight;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Plume;
	float ShakeT = 0.f;
};

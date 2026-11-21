// KOZMOGENİS — V41 dikey dilim sahnesi: gezegene özgü ışık/gökyüzü (Ay: atmosfersiz kara gök; Mars:
// toz yüklü SkyAtmosphere + sis), zemin ve kraterler/kayalar, 3B koloni, NPC aktörleri, uzay aracı pawn'ı ve
// yürüyen oyuncu. Hava olayları (toz fırtınası) sis ve güneş ışığını çekirdekteki görüş değerine göre değiştirir.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KozmoExpedition.generated.h"

class AKozmogenisSpacecraft;
class AKozmogenisCharacter;
class AKozmogenisColony;
class AKozmogenisNPC;
class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UPostProcessComponent;

UCLASS()
class KOZMOGENIS_API AKozmoExpeditionScene : public AActor
{
	GENERATED_BODY()

public:
	AKozmoExpeditionScene();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void Tick(float DeltaSeconds) override;

	void PossessCraft();
	void PossessCharacter();
	void SetFeedback(const FString& S) { Feedback = S; }
	const FString& GetFeedback() const { return Feedback; }
	FVector LandingPadWorld() const;
	FVector SettlementToWorld(double X, double Y, double Z = 0) const;
	FVector2D WorldToSettlement(const FVector& W) const;
	FString BuildingAt(const FVector& W) const;
	bool IsPlayerInCraft() const;

private:
	void SetupEnvironment();
	void SyncNpcs();
	void SyncColony();
	int32 BuiltSignature = -1;
	class UKozmoSubsystem* Kozmo() const;

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY() TObjectPtr<USkyAtmosphereComponent> Sky;
	UPROPERTY() TObjectPtr<USkyLightComponent> SkyLight;
	UPROPERTY() TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY() TObjectPtr<UPostProcessComponent> Post;
	UPROPERTY() TObjectPtr<AKozmogenisSpacecraft> Craft;
	UPROPERTY() TObjectPtr<AKozmogenisCharacter> Walker;
	UPROPERTY() TObjectPtr<AKozmogenisColony> Colony;
	UPROPERTY() TMap<int32, TObjectPtr<AKozmogenisNPC>> Npcs;
	FString Feedback;
	float BaseSun = 10.f, BaseFog = 0.f;
};

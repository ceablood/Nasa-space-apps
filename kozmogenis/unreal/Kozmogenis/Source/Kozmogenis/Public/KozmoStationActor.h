// KOZMOGENİS — yörünge istasyonu görünümü (V30 §15.1): KozmoCore station::Station modüllerinden kafes, basınçlı
// modüller, güneş kanatları, kenetli araçlar; yörünge periyoduyla döner; irtifa/sarf etiketi canlıdır.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KozmoStationActor.generated.h"

class UTextRenderComponent;

UCLASS()
class KOZMOGENIS_API AKozmoStationActor : public AActor
{
	GENERATED_BODY()

public:
	AKozmoStationActor();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	void Rebuild();

private:
	class UKozmoSubsystem* Kozmo() const;
	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<USceneComponent> Body;
	UPROPERTY() TObjectPtr<UTextRenderComponent> Info;
	int32 LastModules = -1, LastDocked = -1;
};

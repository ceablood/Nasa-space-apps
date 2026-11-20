// KOZMOGENİS — NASA verileriyle 3B Güneş Sistemi sahnesi (motorun temel şekilleri; harici varlık gerekmez).
// Görsel ölçek (oyun varsayımı, şema kuralı 16): uzaklıklar logaritmik, boyutlar üstel sıkıştırmalıdır;
// gerçek ölçekte gezegenler görünmeyecek kadar küçük kalır. Konumlar çekirdekteki gerçek periyotlarla ilerler.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KozmoSolarSystem.generated.h"

class UStaticMeshComponent;
class UTextRenderComponent;
class UPointLightComponent;

UCLASS()
class KOZMOGENIS_API AKozmoSolarSystem : public AActor
{
	GENERATED_BODY()

public:
	AKozmoSolarSystem();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** Gerçek uzaklığı (milyon km) sahne birimine çevirir (logaritmik görsel ölçek). */
	static float VisualDistance(float DistanceMkm);
	/** Gerçek çapı (km) sahne yarıçapına çevirir (üstel sıkıştırma). */
	static float VisualRadius(float DiameterKm, bool bStar);

private:
	struct FBodyVisual
	{
		FString Key;
		FString Parent;
		float Distance = 0.f;
		UStaticMeshComponent* Mesh = nullptr;
		UTextRenderComponent* Label = nullptr;
	};
	TArray<FBodyVisual> Bodies;

	UPROPERTY() TObjectPtr<UPointLightComponent> SunLight;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> MeshRefs;   // GC koruması
	UPROPERTY() TArray<TObjectPtr<UTextRenderComponent>> LabelRefs;
};

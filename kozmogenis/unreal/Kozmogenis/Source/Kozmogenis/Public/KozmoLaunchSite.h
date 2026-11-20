// KOZMOGENİS — fırlatma rampası sahnesi: fiziksel gökyüzü (SkyAtmosphere, Dünya Rayleigh/Mie saçılımı),
// Güneş (gerçek açısal çap 0.53°), gerçek zamanlı gök ışığı, üstel yükseklik sisi, hacimsel bulut,
// sinematik post-process ve 3B roket montajı. Harici varlık gerekmez (motorun temel şekilleri).
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KozmoGraphics.h"
#include "KozmoLaunchSite.generated.h"

class AKozmoRocketAssembly;
class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UVolumetricCloudComponent;
class UPostProcessComponent;
class UStaticMeshComponent;

UCLASS()
class KOZMOGENIS_API AKozmoLaunchSite : public AActor
{
	GENERATED_BODY()

public:
	AKozmoLaunchSite();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	AKozmoRocketAssembly* GetRocket() const { return Rocket; }
	/** Güneş yüksekliği (derece): 5 = gün doğumu altın saati, 45 = öğle. */
	void SetSunElevation(float Degrees);
	/** Kalite profiline göre hacimsel sis/bulut aç-kapa. */
	void ApplyQuality(EKozmoQuality Q);
	FVector GetViewPoint() const;

private:
	void BuildPad();
	UStaticMeshComponent* AddBlock(class UStaticMesh* Mesh, const FVector& Loc, const FVector& Scale, const FLinearColor& Color, float Rough);

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY() TObjectPtr<USkyAtmosphereComponent> Sky;
	UPROPERTY() TObjectPtr<USkyLightComponent> SkyLight;
	UPROPERTY() TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY() TObjectPtr<UVolumetricCloudComponent> Clouds;
	UPROPERTY() TObjectPtr<UPostProcessComponent> Post;
	UPROPERTY() TObjectPtr<AKozmoRocketAssembly> Rocket;
	UPROPERTY() TObjectPtr<class UMaterialInterface> BaseMaterial;
	UPROPERTY() TObjectPtr<class UMaterialInterface> CloudMaterial;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Blocks;
	FDelegateHandle DesignHandle;
};

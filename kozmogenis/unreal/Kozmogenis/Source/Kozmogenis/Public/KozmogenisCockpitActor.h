// KOZMOGENİS — 3B kokpit (V41 §1): koltuk, konsol, 12 canlı gösterge, uyarı lambaları, fiziksel düğmeler.
// Göstergeler yalnız çekirdekteki craft::Spacecraft::instruments() değerlerini gösterir (sahte veri yok).
// Kokpit seviyesi (V1..V4) hangi ekranların/düğmelerin var olduğunu belirler.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/spacecraft.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmogenisCockpitActor.generated.h"

class UTextRenderComponent;
class UPointLightComponent;
class UStaticMeshComponent;

UCLASS()
class KOZMOGENIS_API AKozmogenisCockpitActor : public AActor
{
	GENERATED_BODY()

public:
	AKozmogenisCockpitActor();
	/** Kokpiti seviyeye göre kurar (V1 analog, V2 dijital, V3 çoklu ekran, V4 NOVA/holo). */
	void Build(kozmo::craft::CockpitLevel Level);
	/** Göstergeleri, uyarı lambalarını ve kabin ışığını canlı durumdan günceller. */
	void UpdateFrom(const kozmo::craft::Spacecraft& Craft);
	/** Bileşen bir düğmeyse eylem adını döner ("engines", "landing", "manual", "auto", "lights", "emergency", "fix") */
	FString ButtonAction(const UPrimitiveComponent* Hit) const;
	FVector GetEyeLocation() const;
	/** Gaz kolu (0..1) ve kontrol kolu (yunuslama derecesi) animasyonu */
	void SetLevers(double Throttle, float PitchDeg);

private:
	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TArray<TObjectPtr<UTextRenderComponent>> Gauges;     // 12 gösterge (SPEED .. RADAR)
	UPROPERTY() TArray<TObjectPtr<UPointLightComponent>> WarningLamps;
	UPROPERTY() TObjectPtr<UPointLightComponent> CabinLight;
	UPROPERTY() TObjectPtr<UTextRenderComponent> WarningText;
	UPROPERTY() TObjectPtr<UTextRenderComponent> HoloMap;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Stick;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> ThrottleLever;
	TMap<TObjectPtr<UPrimitiveComponent>, FString> Buttons;
	kozmo::craft::CockpitLevel Level = kozmo::craft::CockpitLevel::None;
	float BlinkT = 0.f;
};

// KOZMOGENİS — 3B roket montajı: KozmoCore vehicle::geometry çıktısını (tank boyları, çaplar, motor sayısı,
// güçlendiriciler, burun konisi) motorun temel şekilleriyle gerçek ölçekte (1 m = 100 birim) kurar ve
// fırlatma simülasyonunun telemetrisini oynatır (irtifa, yunuslama, kademe/güçlendirici/fairing ayrılması).
// DURUM: yazıldı, UE5 yokken DERLENMEDİ. Görünüm Cumartesi hedef PC'de doğrulanacak.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/flight.hpp"
#include "kozmo/vehicle.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmoRocketAssembly.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class UTextRenderComponent;

UCLASS()
class KOZMOGENIS_API AKozmoRocketAssembly : public AActor
{
	GENERATED_BODY()

public:
	AKozmoRocketAssembly();
	virtual void Tick(float DeltaSeconds) override;

	/** Tasarımı yeniden kurar. Hata varsa (geçersiz tasarım) metni döner, boşsa başarılı. */
	FString Build(const kozmo::prop::Design& Design);
	/** Fırlatma simülasyonunu (çekirdek) çalıştırır ve sahnede oynatır; özet metin döner. */
	FString PlayAscent(const kozmo::prop::Design& Design, float TimeScale = 10.f);
	void StopAscent();
	bool IsPlaying() const { return bPlaying; }
	float GetTotalHeightCm() const { return TotalHeightCm; }
	FVector GetBodyLocation() const;

private:
	enum class EPart : uint8 { Stage, Booster, Fairing, Payload, Static };
	struct FPart
	{
		UStaticMeshComponent* Mesh = nullptr;
		EPart Kind = EPart::Static;
		int32 Stage = 0;          // hangi kademeye bağlı (ayrılınca düşer)
		FVector DropVelocity = FVector::ZeroVector;
		bool bDetached = false;
	};

	UStaticMeshComponent* AddShape(UStaticMesh* Shape, const FVector& Loc, const FVector& Scale, const FRotator& Rot,
		const FLinearColor& Color, float Metallic, float Roughness, EPart Kind, int32 Stage);
	UMaterialInstanceDynamic* MakeMaterial(const FLinearColor& Color, float Metallic, float Roughness);
	void Clear();
	void Detach(EPart Kind, int32 Stage);

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<USceneComponent> Body;           // uçuşta hareket eden gövde
	UPROPERTY() TObjectPtr<UStaticMesh> Cylinder;
	UPROPERTY() TObjectPtr<UStaticMesh> Cone;
	UPROPERTY() TObjectPtr<UStaticMesh> Cube;
	UPROPERTY() TObjectPtr<UStaticMesh> Sphere;
	UPROPERTY() TObjectPtr<UMaterialInterface> BaseMaterial;
	UPROPERTY() TObjectPtr<UPointLightComponent> Plume;     // motor alevi ışığı
	UPROPERTY() TObjectPtr<UStaticMeshComponent> PlumeMesh;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Owned;   // GC koruması
	UPROPERTY() TArray<TObjectPtr<UTextRenderComponent>> Labels;
	TArray<FPart> Parts;

	// oynatma
	kozmo::flight::AscentResult Ascent;
	bool bPlaying = false;
	float PlayT = 0.f;
	float PlayScale = 10.f;
	int32 NextEvent = 0;
	double Downrange = 0.0;
	float TotalHeightCm = 0.f;
	float VisualAltitudeScale = 0.02f;   // görsel: 1 km irtifa = 20 m sahne (oyun varsayımı, kamera takip eder)
};

// KOZMOGENİS — prosedürel 3B gezegen yüzeyi: KozmoCore terrain::Heightmap'ten ProceduralMeshComponent ile mesh
// kurar (kraterler, kumullar, buz sırtları, lav akıntıları, lav tüpü girişleri), iniş yeri ve çukur işaretleri
// koyar. Yükseklik sorgusu (GetHeightAt) rover ve karakterin zemini için kullanılır.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ. Üçgen sargı yönü (bFlipWinding) ilk derlemede doğrulanacak.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/terrain.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmoTerrainActor.generated.h"

class UProceduralMeshComponent;

UCLASS()
class KOZMOGENIS_API AKozmoTerrainActor : public AActor
{
	GENERATED_BODY()

public:
	AKozmoTerrainActor();
	/** Gezegen anahtarı ("moon", "mars", "titan" ...) ve tohumla araziyi üretir; boyut metre */
	FString Generate(const FString& Body, int64 Seed, float SizeM = 2000.f, float CellM = 10.f);
	/** Dünya konumundaki zemin yüksekliği (cm, dünya Z) */
	float GetHeightAt(const FVector& World) const;
	float GetSlopeAt(const FVector& World) const;
	const kozmo::terrain::Heightmap& Map() const { return Heightmap; }

	UPROPERTY(EditAnywhere, Category = "Kozmo") bool bFlipWinding = false;
	UPROPERTY(EditAnywhere, Category = "Kozmo") int32 MeshStep = 1;

private:
	UPROPERTY() TObjectPtr<UProceduralMeshComponent> Mesh;
	kozmo::terrain::Heightmap Heightmap;
	bool bReady = false;
};

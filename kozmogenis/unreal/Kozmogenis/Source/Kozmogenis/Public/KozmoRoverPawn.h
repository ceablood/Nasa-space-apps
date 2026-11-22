// KOZMOGENİS — yüzey aracı (V30 §8): arazi üzerinde sürüş; enerji, patinaj, eğim sınırı ve "geri yürüyüş"
// kuralı çekirdekteki rover::Rover ile hesaplanır. Araç zemini AKozmoTerrainActor'dan alır.
// Kontroller: W/S gaz, A/D direksiyon, E in/bin, fare bakış.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/rover.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmoRoverPawn.generated.h"

class UCameraComponent;
class UTextRenderComponent;
class AKozmoTerrainActor;

UCLASS()
class KOZMOGENIS_API AKozmoRoverPawn : public APawn
{
	GENERATED_BODY()

public:
	AKozmoRoverPawn();
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
	void Setup(AKozmoTerrainActor* InTerrain, const FString& RoverKey, const FString& Body);
	FString Status() const;

private:
	void Throttle(float V) { Gas = V; }
	void Steer(float V) { Turn = V; }
	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UCameraComponent> Camera;
	UPROPERTY() TObjectPtr<UTextRenderComponent> Dash;
	UPROPERTY() TObjectPtr<AKozmoTerrainActor> Terrain;
	TUniquePtr<kozmo::rover::Rover> Rover;
	kozmo::challenge::PlanetEnvironment Env;
	float Gas = 0.f, Turn = 0.f, Speed = 0.f, Heading = 0.f;
	FVector Start = FVector::ZeroVector;
	FString LastWarning;
};

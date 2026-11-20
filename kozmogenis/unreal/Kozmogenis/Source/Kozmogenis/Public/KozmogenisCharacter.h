// KOZMOGENİS — yüzeyde yürüyen oyuncu (V41 §4.1): birinci şahıs, gezegen yerçekimine göre ölçekli hareket
// (Ay 0.165 g, Mars 0.38 g), E ile kapı/konsol/NPC/araç etkileşimi, G numune, 1-5 konuşma konuları.
// Konum her karede çekirdeğe yazılır (Expedition::set_player_position); hayatta kalma çekirdekte hesaplanır.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "KozmogenisCharacter.generated.h"

class UCameraComponent;
class AKozmoExpeditionScene;

UCLASS()
class KOZMOGENIS_API AKozmogenisCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AKozmogenisCharacter();
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
	void SetScene(AKozmoExpeditionScene* InScene, float GravityMs2);
	int32 GetFocusedNpc() const { return FocusedNpc; }

private:
	void MoveForward(float V);
	void MoveRight(float V);
	void Interact();
	void Sample();
	void Topic1() { Talk(TEXT("selam")); }
	void Topic2() { Talk(TEXT("nasılsın")); }
	void Topic3() { Talk(TEXT("iş")); }
	void Topic4() { Talk(TEXT("koloni")); }
	void Topic5() { Talk(TEXT("yardım")); }
	void Talk(const FString& Topic);
	bool Trace(FHitResult& Hit) const;
	class UKozmoSubsystem* Kozmo() const;

	UPROPERTY() TObjectPtr<UCameraComponent> Camera;
	UPROPERTY() TObjectPtr<AKozmoExpeditionScene> Scene;
	int32 FocusedNpc = -1;
};

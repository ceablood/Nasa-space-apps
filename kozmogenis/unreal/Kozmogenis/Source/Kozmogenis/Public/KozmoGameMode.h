// KOZMOGENİS — oyun modu: Güneş Sistemi sahnesini kurar, kontrol panelini açar, serbest kamera verir.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "KozmoGameMode.generated.h"

class SKozmoDashboard;
class SKozmoDesigner;
class AKozmoSolarSystem;
class AKozmoLaunchSite;

UCLASS()
class KOZMOGENIS_API AKozmoGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AKozmoGameMode();
	virtual void StartPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	/** true: fırlatma rampası (gökyüzü, 3B roket); false: Güneş Sistemi. Gökyüzü atmosferi uzay görünümünü
	 *  boyayacağı için rampa sahnesi her geçişte kurulur/kaldırılır. */
	void ShowLaunchSite(bool bShow);
	/** Tasarımı rampada fırlatır (gerekirse rampaya geçer); özet metin döner. */
	FString PlayDesignAscent();

private:
	TSharedPtr<SKozmoDashboard> Dashboard;
	TSharedPtr<class SWidget> DashboardContainer;
	TSharedPtr<SKozmoDesigner> Designer;
	TSharedPtr<class SWidget> DesignerContainer;
	UPROPERTY() TObjectPtr<AKozmoSolarSystem> SolarSystem;
	UPROPERTY() TObjectPtr<AKozmoLaunchSite> LaunchSite;
	void MovePawn(const FVector& Location, const FVector& LookAt, float Speed);
};

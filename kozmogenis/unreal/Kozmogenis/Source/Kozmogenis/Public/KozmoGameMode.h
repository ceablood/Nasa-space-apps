// KOZMOGENİS — oyun modu: Güneş Sistemi sahnesini kurar, kontrol panelini açar, serbest kamera verir.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "KozmoGameMode.generated.h"

class SKozmoDashboard;
class SKozmoDesigner;
class AKozmoSolarSystem;
class AKozmoLaunchSite;
class AKozmoExpeditionScene;
class SKozmoExpeditionHud;

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

	/** V41 dikey dilim: "moon" (gezilebilir koloni) ya da "mars". Hata metni ya da boş. */
	FString StartExpedition(const FString& Body);
	void EndExpedition();
	FString GetExpeditionFeedback() const;
	void SetExpeditionFeedback(const FString& S);

private:
	TSharedPtr<SKozmoDashboard> Dashboard;
	TSharedPtr<class SWidget> DashboardContainer;
	TSharedPtr<SKozmoDesigner> Designer;
	TSharedPtr<class SWidget> DesignerContainer;
	UPROPERTY() TObjectPtr<AKozmoSolarSystem> SolarSystem;
	UPROPERTY() TObjectPtr<AKozmoLaunchSite> LaunchSite;
	UPROPERTY() TObjectPtr<AKozmoExpeditionScene> ExpeditionScene;
	UPROPERTY() TObjectPtr<APawn> SpectatorPawn;
	TSharedPtr<SKozmoExpeditionHud> ExpeditionHud;
	TSharedPtr<class SWidget> ExpeditionHudContainer;
	void SetPanelsVisible(bool bVisible);
	void MovePawn(const FVector& Location, const FVector& LookAt, float Speed);
};

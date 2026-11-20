// KOZMOGENİS — oyun modu: Güneş Sistemi sahnesini kurar, kontrol panelini açar, serbest kamera verir.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "KozmoGameMode.generated.h"

class SKozmoDashboard;

UCLASS()
class KOZMOGENIS_API AKozmoGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AKozmoGameMode();
	virtual void StartPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	TSharedPtr<SKozmoDashboard> Dashboard;
	TSharedPtr<class SWidget> DashboardContainer;
};

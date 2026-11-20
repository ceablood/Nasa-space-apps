// KOZMOGENİS — roket tasarım paneli (Slate). Her düğme UKozmoSubsystem'deki gerçek tasarım işlemine bağlıdır;
// rapor çekirdeğin analiz + geometri sonucudur. Görünüm düğmesi fırlatma rampası ile Güneş Sistemi arasında geçer.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class UKozmoSubsystem;
class AKozmoGameMode;

class KOZMOGENIS_API SKozmoDesigner : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SKozmoDesigner) {}
		SLATE_ARGUMENT(TWeakObjectPtr<UKozmoSubsystem>, Subsystem)
		SLATE_ARGUMENT(TWeakObjectPtr<AKozmoGameMode>, GameMode)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	TSharedRef<SWidget> Btn(const FString& Label, TFunction<void()> Action);
	TSharedRef<SWidget> StageRow(int32 Stage);
	FText Report() const;
	FText Quality() const;

	TWeakObjectPtr<UKozmoSubsystem> Subsystem;
	TWeakObjectPtr<AKozmoGameMode> GameMode;
	FText FlightText;
};

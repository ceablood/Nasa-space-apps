// KOZMOGENİS — sefer HUD'u (Slate): kokpit göstergeleri özeti, uyarılar + prosedür düğmesi, gezegen zorluğu,
// giysi O2/sağlık/doz, NPC diyaloğu, görevler, NOVA kutusu (onay gerektiren işlemler 'onayla' ile).
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "CoreMinimal.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/SCompoundWidget.h"

class UKozmoSubsystem;
class AKozmoGameMode;

class KOZMOGENIS_API SKozmoExpeditionHud : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SKozmoExpeditionHud) {}
		SLATE_ARGUMENT(TWeakObjectPtr<UKozmoSubsystem>, Subsystem)
		SLATE_ARGUMENT(TWeakObjectPtr<AKozmoGameMode>, GameMode)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FText Status() const;
	FText Env() const;
	FText Feedback() const;
	FText Tasks() const;
	TSharedRef<SWidget> Btn(const FString& Label, TFunction<void()> Action);
	void OnNova(const FText& T, ETextCommit::Type C);

	TWeakObjectPtr<UKozmoSubsystem> Subsystem;
	TWeakObjectPtr<AKozmoGameMode> GameMode;
	TSharedPtr<SEditableTextBox> NovaBox;
	FText NovaText;
};

// KOZMOGENİS — Slate kontrol paneli: her düğme KozmoCore'daki gerçek bir eyleme bağlıdır (sahte düğme yok).
#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Input/SEditableTextBox.h"

class UKozmoSubsystem;

class KOZMOGENIS_API SKozmoDashboard : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SKozmoDashboard) {}
		SLATE_ARGUMENT(TWeakObjectPtr<UKozmoSubsystem>, Subsystem)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FText GetStatus() const;
	FText GetMessages() const;
	FText GetFeedback() const { return Feedback; }
	FReply Launch(FString Target);
	FReply Research(FString Key);
	FReply SetSpeed(float DaysPerSecond);
	FReply Evaluate(FString Target);
	FReply Save();
	FReply Load();
	FReply AscentSim();
	void OnNovaCommitted(const FText& Text, ETextCommit::Type CommitType);
	TSharedRef<SWidget> MakeButton(const FString& Label, FOnClicked Handler);

	TWeakObjectPtr<UKozmoSubsystem> Subsystem;
	FText Feedback;
	TSharedPtr<SEditableTextBox> NovaInput;
};

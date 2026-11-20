#include "SKozmoDashboard.h"

#include "KozmoSubsystem.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "KozmoDashboard"

TSharedRef<SWidget> SKozmoDashboard::MakeButton(const FString& Label, FOnClicked Handler)
{
	return SNew(SBox).Padding(2.f)
	[
		SNew(SButton)
		.Text(FText::FromString(Label))
		.OnClicked(Handler)
	];
}

void SKozmoDashboard::Construct(const FArguments& InArgs)
{
	Subsystem = InArgs._Subsystem;
	const FSlateFontInfo Body = FCoreStyle::GetDefaultFontStyle("Regular", 11);
	const FSlateFontInfo Title = FCoreStyle::GetDefaultFontStyle("Bold", 16);

	ChildSlot
	.HAlign(HAlign_Left)
	.VAlign(VAlign_Top)
	.Padding(16.f)
	[
		SNew(SBox).WidthOverride(560.f)
		[
			SNew(SBorder)
			.BorderImage(FCoreStyle::Get().GetBrush("ToolPanel.GroupBorder"))
			.BorderBackgroundColor(FLinearColor(0.02f, 0.03f, 0.06f, 0.85f))
			.Padding(12.f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(STextBlock).Text(LOCTEXT("Title", "KOZMOGENİS — Görev Kontrol")).Font(Title)
					.ColorAndOpacity(FLinearColor(0.55f, 0.85f, 0.95f))
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f)
				[
					SNew(STextBlock).Text(this, &SKozmoDashboard::GetStatus).Font(Body).AutoWrapText(true)
					.ColorAndOpacity(FLinearColor(0.92f, 0.93f, 0.95f))
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[MakeButton(TEXT("Ay'a koloni kiti"), FOnClicked::CreateSP(this, &SKozmoDashboard::Launch, FString(TEXT("moon"))))]
					+ SWrapBox::Slot()[MakeButton(TEXT("Mars'a koloni kiti"), FOnClicked::CreateSP(this, &SKozmoDashboard::Launch, FString(TEXT("mars"))))]
					+ SWrapBox::Slot()[MakeButton(TEXT("Mars görevi analizi"), FOnClicked::CreateSP(this, &SKozmoDashboard::Evaluate, FString(TEXT("mars"))))]
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[MakeButton(TEXT("Araştır: Fisyon"), FOnClicked::CreateSP(this, &SKozmoDashboard::Research, FString(TEXT("fission"))))]
					+ SWrapBox::Slot()[MakeButton(TEXT("Araştır: ISRU"), FOnClicked::CreateSP(this, &SKozmoDashboard::Research, FString(TEXT("isru"))))]
					+ SWrapBox::Slot()[MakeButton(TEXT("Araştır: Kapalı döngü"), FOnClicked::CreateSP(this, &SKozmoDashboard::Research, FString(TEXT("closed_loop"))))]
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[MakeButton(TEXT("Duraklat"), FOnClicked::CreateSP(this, &SKozmoDashboard::SetSpeed, 0.f))]
					+ SWrapBox::Slot()[MakeButton(TEXT("x0.25 gün/sn"), FOnClicked::CreateSP(this, &SKozmoDashboard::SetSpeed, 0.25f))]
					+ SWrapBox::Slot()[MakeButton(TEXT("x2 gün/sn"), FOnClicked::CreateSP(this, &SKozmoDashboard::SetSpeed, 2.f))]
					+ SWrapBox::Slot()[MakeButton(TEXT("x20 gün/sn"), FOnClicked::CreateSP(this, &SKozmoDashboard::SetSpeed, 20.f))]
					+ SWrapBox::Slot()[MakeButton(TEXT("Kaydet"), FOnClicked::CreateSP(this, &SKozmoDashboard::Save))]
					+ SWrapBox::Slot()[MakeButton(TEXT("Yükle"), FOnClicked::CreateSP(this, &SKozmoDashboard::Load))]
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[MakeButton(TEXT("Fırlatma simülasyonu (F9 sınıfı, 22 t)"), FOnClicked::CreateSP(this, &SKozmoDashboard::AscentSim))]
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
				[
					SAssignNew(NovaInput, SEditableTextBox)
					.HintText(LOCTEXT("NovaHint", "NOVA'ya sor: ör. 'Mars penceresi ne zaman?' ya da 'onayla'"))
					.OnTextCommitted(this, &SKozmoDashboard::OnNovaCommitted)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f)
				[
					SNew(STextBlock).Text(this, &SKozmoDashboard::GetFeedback).Font(Body).AutoWrapText(true)
					.ColorAndOpacity(FLinearColor(0.95f, 0.78f, 0.45f))
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(STextBlock).Text(this, &SKozmoDashboard::GetMessages).Font(Body).AutoWrapText(true)
					.ColorAndOpacity(FLinearColor(0.70f, 0.80f, 0.88f))
				]
			]
		]
	];
}

FText SKozmoDashboard::GetStatus() const
{
	return Subsystem.IsValid() ? FText::FromString(Subsystem->GetStatusText()) : FText::GetEmpty();
}

FText SKozmoDashboard::GetMessages() const
{
	if (!Subsystem.IsValid()) return FText::GetEmpty();
	const TArray<FString>& M = Subsystem->GetRecentMessages();
	FString S;
	for (int32 i = FMath::Max(0, M.Num() - 6); i < M.Num(); ++i) S += M[i] + TEXT("\n");
	return FText::FromString(S);
}

FReply SKozmoDashboard::Launch(FString Target)
{
	if (Subsystem.IsValid())
	{
		const FString Err = Subsystem->LaunchColonyKit(Target);
		Feedback = FText::FromString(Err.IsEmpty() ? TEXT("Fırlatma komutu verildi.") : Err + TEXT("\n") + Subsystem->GetWindowText(Target));
	}
	return FReply::Handled();
}

FReply SKozmoDashboard::Evaluate(FString Target)
{
	if (Subsystem.IsValid())
	{
		Feedback = FText::FromString(Subsystem->EvaluateHeavyRocket(Target, 42.f, 3) + TEXT("\n") + Subsystem->GetWindowText(Target));
	}
	return FReply::Handled();
}

FReply SKozmoDashboard::Research(FString Key)
{
	if (Subsystem.IsValid())
	{
		const FString Err = Subsystem->StartResearch(Key);
		Feedback = FText::FromString(Err.IsEmpty() ? TEXT("Araştırma başladı (koloni laboratuvarları puan üretir).") : Err);
	}
	return FReply::Handled();
}

FReply SKozmoDashboard::SetSpeed(float DaysPerSecond)
{
	if (Subsystem.IsValid()) Subsystem->SetTimeScale(DaysPerSecond);
	return FReply::Handled();
}

FReply SKozmoDashboard::Save()
{
	if (Subsystem.IsValid()) Subsystem->SaveToSlot(TEXT("kayit1"));
	return FReply::Handled();
}

FReply SKozmoDashboard::Load()
{
	if (Subsystem.IsValid())
	{
		const FString Err = Subsystem->LoadFromSlot(TEXT("kayit1"));
		Feedback = FText::FromString(Err.IsEmpty() ? TEXT("Kayıt yüklendi.") : Err);
	}
	return FReply::Handled();
}

FReply SKozmoDashboard::AscentSim()
{
	if (Subsystem.IsValid()) Feedback = FText::FromString(Subsystem->SimulateAscent(false, 22.0f));
	return FReply::Handled();
}

void SKozmoDashboard::OnNovaCommitted(const FText& Text, ETextCommit::Type CommitType)
{
	if (CommitType != ETextCommit::OnEnter || !Subsystem.IsValid() || Text.IsEmpty()) return;
	Feedback = FText::FromString(Subsystem->AskNova(Text.ToString()));
	if (NovaInput.IsValid()) NovaInput->SetText(FText::GetEmpty());
}

#undef LOCTEXT_NAMESPACE

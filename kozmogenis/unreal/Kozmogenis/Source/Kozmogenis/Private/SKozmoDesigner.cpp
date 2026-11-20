#include "SKozmoDesigner.h"

#include "KozmoGameMode.h"
#include "KozmoSubsystem.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "KozmoDesigner"

TSharedRef<SWidget> SKozmoDesigner::Btn(const FString& Label, TFunction<void()> Action)
{
	return SNew(SBox).Padding(2.f)
	[
		SNew(SButton)
		.Text(FText::FromString(Label))
		.OnClicked_Lambda([Action]() { Action(); return FReply::Handled(); })
	];
}

TSharedRef<SWidget> SKozmoDesigner::StageRow(int32 Stage)
{
	TWeakObjectPtr<UKozmoSubsystem> K = Subsystem;
	auto Do = [K](TFunction<void(UKozmoSubsystem&)> F) { return [K, F]() { if (K.IsValid()) F(*K); }; };
	return SNew(SWrapBox).UseAllottedSize(true)
		+ SWrapBox::Slot()[SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%d. kademe "), Stage + 1)))]
		+ SWrapBox::Slot()[Btn(TEXT("Motor ◀"), Do([Stage](UKozmoSubsystem& S) { S.CycleStageEngine(Stage, -1); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Motor ▶"), Do([Stage](UKozmoSubsystem& S) { S.CycleStageEngine(Stage, 1); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Adet −"), Do([Stage](UKozmoSubsystem& S) { S.AdjustStage(Stage, -1, 1.f, 0.f); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Adet +"), Do([Stage](UKozmoSubsystem& S) { S.AdjustStage(Stage, 1, 1.f, 0.f); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Yakıt −%10"), Do([Stage](UKozmoSubsystem& S) { S.AdjustStage(Stage, 0, 0.9f, 0.f); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Yakıt +%10"), Do([Stage](UKozmoSubsystem& S) { S.AdjustStage(Stage, 0, 1.1f, 0.f); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Çap −"), Do([Stage](UKozmoSubsystem& S) { S.AdjustStage(Stage, 0, 1.f, -0.5f); }))]
		+ SWrapBox::Slot()[Btn(TEXT("Çap +"), Do([Stage](UKozmoSubsystem& S) { S.AdjustStage(Stage, 0, 1.f, 0.5f); }))];
}

void SKozmoDesigner::Construct(const FArguments& InArgs)
{
	Subsystem = InArgs._Subsystem;
	GameMode = InArgs._GameMode;
	TWeakObjectPtr<UKozmoSubsystem> K = Subsystem;
	TWeakObjectPtr<AKozmoGameMode> GM = GameMode;
	auto Do = [K](TFunction<void(UKozmoSubsystem&)> F) { return [K, F]() { if (K.IsValid()) F(*K); }; };
	const FSlateFontInfo Body = FCoreStyle::GetDefaultFontStyle("Regular", 10);
	const FSlateFontInfo Title = FCoreStyle::GetDefaultFontStyle("Bold", 15);

	TSharedRef<SVerticalBox> Stages = SNew(SVerticalBox);
	for (int32 i = 0; i < 4; ++i)   // en çok 4 kademe; olmayan kademenin düğmeleri çekirdekte yok sayılır
	{
		Stages->AddSlot().AutoHeight()[StageRow(i)];
	}

	ChildSlot
	.HAlign(HAlign_Right)
	.VAlign(VAlign_Top)
	.Padding(16.f)
	[
		SNew(SBox).WidthOverride(520.f).MaxDesiredHeight(900.f)
		[
			SNew(SBorder)
			.BorderImage(FCoreStyle::Get().GetBrush("ToolPanel.GroupBorder"))
			.BorderBackgroundColor(FLinearColor(0.02f, 0.03f, 0.06f, 0.85f))
			.Padding(12.f)
			[
				SNew(SScrollBox)
				+ SScrollBox::Slot()
				[
					SNew(STextBlock).Text(LOCTEXT("T", "Roket Tasarımcısı")).Font(Title).ColorAndOpacity(FLinearColor(0.95f, 0.70f, 0.40f))
				]
				+ SScrollBox::Slot()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[Btn(TEXT("Hazır: F9 sınıfı"), Do([](UKozmoSubsystem& S) { S.LoadPresetDesign(TEXT("f9")); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Hazır: F9 + 2 SRB"), Do([](UKozmoSubsystem& S) { S.LoadPresetDesign(TEXT("f9_srb")); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Hazır: Ağır metan"), Do([](UKozmoSubsystem& S) { S.LoadPresetDesign(TEXT("heavy")); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Hedef değiştir"), Do([](UKozmoSubsystem& S) { S.CycleTarget(); }))]
				]
				+ SScrollBox::Slot()[Stages]
				+ SScrollBox::Slot()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[Btn(TEXT("Kademe ekle"), Do([](UKozmoSubsystem& S) { S.AddStage(); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Üst kademeyi sil"), Do([](UKozmoSubsystem& S) { S.RemoveTopStage(); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Güçlendirici −"), Do([](UKozmoSubsystem& S) { S.AdjustBoosters(-1, 0.f); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Güçlendirici +"), Do([](UKozmoSubsystem& S) { S.AdjustBoosters(1, 0.f); }))]
					+ SWrapBox::Slot()[Btn(TEXT("SRB yakıt −25 t"), Do([](UKozmoSubsystem& S) { S.AdjustBoosters(0, -25.f); }))]
					+ SWrapBox::Slot()[Btn(TEXT("SRB yakıt +25 t"), Do([](UKozmoSubsystem& S) { S.AdjustBoosters(0, 25.f); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Yük −1 t"), Do([](UKozmoSubsystem& S) { S.AdjustPayload(-1.f); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Yük +1 t"), Do([](UKozmoSubsystem& S) { S.AdjustPayload(1.f); }))]
				]
				+ SScrollBox::Slot().Padding(0.f, 6.f)
				[
					SNew(STextBlock).Text(this, &SKozmoDesigner::Report).Font(Body).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.90f, 0.91f, 0.93f))
				]
				+ SScrollBox::Slot()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[Btn(TEXT("Rampa görünümü"), [GM]() { if (GM.IsValid()) GM->ShowLaunchSite(true); })]
					+ SWrapBox::Slot()[Btn(TEXT("Güneş Sistemi"), [GM]() { if (GM.IsValid()) GM->ShowLaunchSite(false); })]
					+ SWrapBox::Slot()[Btn(TEXT("SEFER: Ay (koloni)"), [this, GM]() { if (GM.IsValid()) FlightText = FText::FromString(GM->StartExpedition(TEXT("moon"))); })]
					+ SWrapBox::Slot()[Btn(TEXT("SEFER: Mars"), [this, GM]() { if (GM.IsValid()) FlightText = FText::FromString(GM->StartExpedition(TEXT("mars"))); })]
					+ SWrapBox::Slot()[Btn(TEXT("FIRLAT (simülasyon)"), [this, GM]() {
						if (GM.IsValid()) FlightText = FText::FromString(GM->PlayDesignAscent());
					})]
				]
				+ SScrollBox::Slot().Padding(0.f, 4.f)
				[
					SNew(STextBlock).Text_Lambda([this]() { return FlightText; }).Font(Body).AutoWrapText(true)
					.ColorAndOpacity(FLinearColor(0.95f, 0.78f, 0.45f))
				]
				+ SScrollBox::Slot().Padding(0.f, 8.f, 0.f, 0.f)
				[
					SNew(STextBlock).Text(this, &SKozmoDesigner::Quality).Font(Body).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.6f, 0.8f, 0.9f))
				]
				+ SScrollBox::Slot()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[Btn(TEXT("Ultra"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::Ultra); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Yüksek"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::High); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Orta"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::Medium); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Düşük"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::Low); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Çok düşük"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::VeryLow); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Performans"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::Performance); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Dahili GPU"), Do([](UKozmoSubsystem& S) { S.SetQuality(EKozmoQuality::Integrated); }))]
				]
			]
		]
	];
}

FText SKozmoDesigner::Report() const
{
	return Subsystem.IsValid() ? FText::FromString(Subsystem->GetDesignReport()) : FText::GetEmpty();
}

FText SKozmoDesigner::Quality() const
{
	return Subsystem.IsValid() ? FText::FromString(Subsystem->GetQualityText()) : FText::GetEmpty();
}

#undef LOCTEXT_NAMESPACE

#include "SKozmoExpeditionHud.h"

#include "KozmoGameMode.h"
#include "KozmoSubsystem.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "KozmoExpeditionHud"

TSharedRef<SWidget> SKozmoExpeditionHud::Btn(const FString& Label, TFunction<void()> Action)
{
	return SNew(SBox).Padding(2.f)[SNew(SButton).Text(FText::FromString(Label)).OnClicked_Lambda([Action]() { Action(); return FReply::Handled(); })];
}

void SKozmoExpeditionHud::Construct(const FArguments& InArgs)
{
	Subsystem = InArgs._Subsystem;
	GameMode = InArgs._GameMode;
	TWeakObjectPtr<UKozmoSubsystem> K = Subsystem;
	TWeakObjectPtr<AKozmoGameMode> GM = GameMode;
	const FSlateFontInfo Body = FCoreStyle::GetDefaultFontStyle("Regular", 10);
	const FSlateFontInfo Mono = FCoreStyle::GetDefaultFontStyle("Mono", 10);
	auto WithE = [K](TFunction<void(kozmo::world::Expedition&)> F) {
		return [K, F]() { if (K.IsValid() && K->GetExpedition()) F(*K->GetExpedition()); };
	};
	ChildSlot.HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(16.f)
	[
		SNew(SBox).WidthOverride(620.f)
		[
			SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("ToolPanel.GroupBorder"))
			.BorderBackgroundColor(FLinearColor(0.02f, 0.03f, 0.05f, 0.8f)).Padding(10.f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(this, &SKozmoExpeditionHud::Status).Font(Mono).ColorAndOpacity(FLinearColor(0.6f, 0.9f, 0.95f))]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)[SNew(STextBlock).Text(this, &SKozmoExpeditionHud::Env).Font(Body).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.9f, 0.85f, 0.7f))]
				+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(this, &SKozmoExpeditionHud::Feedback).Font(Body).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.95f, 0.78f, 0.45f))]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)[SNew(STextBlock).Text(this, &SKozmoExpeditionHud::Tasks).Font(Body).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.75f, 0.85f, 0.75f))]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[Btn(TEXT("Prosedür uygula"), WithE([](kozmo::world::Expedition& E) {
						auto W = E.craft().warnings();
						if (!W.empty()) (void)E.craft().apply_procedure(W.front().fault);
					}))]
					+ SWrapBox::Slot()[Btn(TEXT("Zaman x1"), [K]() { if (K.IsValid()) K->SetExpeditionTimeScale(1.f); })]
					+ SWrapBox::Slot()[Btn(TEXT("Zaman x60"), [K]() { if (K.IsValid()) K->SetExpeditionTimeScale(60.f); })]
					+ SWrapBox::Slot()[Btn(TEXT("Senaryo: enerji arızası"), WithE([](kozmo::world::Expedition& E) { E.fail_power(); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Seferi bitir"), [GM]() { if (GM.IsValid()) GM->EndExpedition(); })]
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					// V41 §7.1 / §2.5: koloni kurma, inşaat, kalkış, kenetlenme — her düğme çekirdekte gerçek bir işlem
					SNew(SWrapBox).UseAllottedSize(true)
					+ SWrapBox::Slot()[Btn(TEXT("Su ara"), WithE([GM](kozmo::world::Expedition& E) { auto R = E.scan_water(); if (GM.IsValid()) GM->SetExpeditionFeedback(R.ok() ? KozmoStr(R.value()) : KozmoStr(R.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Koloni kur"), WithE([GM](kozmo::world::Expedition& E) { auto St = E.found_colony(); if (GM.IsValid()) GM->SetExpeditionFeedback(St.ok() ? TEXT("Koloni kuruldu: önce güneş dizisi, sonra habitat") : KozmoStr(St.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("İnşa: güneş dizisi"), WithE([GM](kozmo::world::Expedition& E) { auto R = E.build(kozmo::colony::ModuleType::SolarArray); if (GM.IsValid()) GM->SetExpeditionFeedback(R.ok() ? TEXT("İnşaat başladı") : KozmoStr(R.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("İnşa: habitat"), WithE([GM](kozmo::world::Expedition& E) { auto R = E.build(kozmo::colony::ModuleType::Habitat); if (GM.IsValid()) GM->SetExpeditionFeedback(R.ok() ? TEXT("İnşaat başladı") : KozmoStr(R.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("İnşa: su geri dönüşüm"), WithE([GM](kozmo::world::Expedition& E) { auto R = E.build(kozmo::colony::ModuleType::WaterRecycler); if (GM.IsValid()) GM->SetExpeditionFeedback(R.ok() ? TEXT("İnşaat başladı") : KozmoStr(R.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Güçlendir"), WithE([GM](kozmo::world::Expedition& E) { auto R = E.reinforce(); if (GM.IsValid()) GM->SetExpeditionFeedback(R.ok() ? TEXT("Güçlendirme başladı") : KozmoStr(R.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Hasar raporu"), WithE([GM](kozmo::world::Expedition& E) { if (GM.IsValid()) GM->SetExpeditionFeedback(KozmoStr(E.damage_report())); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Araç lab: analiz"), WithE([GM](kozmo::world::Expedition& E) { auto R = E.analyze_onboard(); if (GM.IsValid()) GM->SetExpeditionFeedback(R.ok() ? KozmoStr(R.value()) : KozmoStr(R.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("Yörüngeye kalk"), WithE([GM](kozmo::world::Expedition& E) { auto St = E.take_off(15000.0); if (GM.IsValid()) GM->SetExpeditionFeedback(St.ok() ? TEXT("Kalkış: otomatik pilot yörüngeye çıkıyor") : KozmoStr(St.error().message)); }))]
					+ SWrapBox::Slot()[Btn(TEXT("İstasyona kenetlen"), WithE([GM](kozmo::world::Expedition& E) {
						(void)E.craft().set_target("istasyon Kapı");
						(void)E.craft().set_mode(kozmo::craft::FlightMode::DockingAssist);
						auto St = E.craft().begin_docking(500.0, 0.0);
						if (GM.IsValid()) GM->SetExpeditionFeedback(St.ok() ? TEXT("Kenetlenme desteği: 500 m, RCS yaklaşma") : KozmoStr(St.error().message));
					}))]
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
				[
					SAssignNew(NovaBox, SEditableTextBox)
					.HintText(LOCTEXT("Hint", "NOVA: 'koloninin durumu nasıl?', 'neden üretim yavaşladı?', 'gezegen riski', 'NPC'leri güvenli alana gönder'"))
					.OnTextCommitted(this, &SKozmoExpeditionHud::OnNova)
				]
				+ SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this]() { return NovaText; }).Font(Body).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.7f, 0.85f, 1.f))]
			]
		]
	];
}

FText SKozmoExpeditionHud::Status() const
{
	const auto* E = Subsystem.IsValid() ? Subsystem->GetExpedition() : nullptr;
	if (!E) return FText::GetEmpty();
	const auto In = E->craft().instruments();
	const auto& B = E->player().body;
	return FText::FromString(FString::Printf(
		TEXT("%s | İRT %.0f m  HIZ %.1f m/s  DİKEY %.1f  YAKIT %%%.0f  GAZ %%%.0f  MOD %s\nSAĞLIK %%%.0f  GİYSİ O2 %.1f sa  DOZ %.2f mSv  NUMUNE %d  YEREL %.1f  MÜRETTEBAT %.1f"),
		*KozmoStr(kozmo::world::to_string(E->player().mode)), In.altitude_m, In.speed_ms, In.vertical_ms, In.fuel_fraction * 100, In.throttle * 100,
		*KozmoStr(kozmo::craft::to_string(In.mode)), B.health * 100, B.suit_o2_h, B.dose_msv, E->player().samples, E->local_hour(), E->crew_hour()));
}

FText SKozmoExpeditionHud::Env() const
{
	const auto* E = Subsystem.IsValid() ? Subsystem->GetExpedition() : nullptr;
	if (!E) return FText::GetEmpty();
	FString S = KozmoStr(E->environment_report());
	for (const auto& W : E->craft().warnings()) S += TEXT("\n! ") + KozmoStr(W.message) + TEXT(" -> ") + KozmoStr(W.procedure);
	return FText::FromString(S);
}

FText SKozmoExpeditionHud::Feedback() const
{
	return GameMode.IsValid() ? FText::FromString(GameMode->GetExpeditionFeedback()) : FText::GetEmpty();
}

FText SKozmoExpeditionHud::Tasks() const
{
	const auto* E = Subsystem.IsValid() ? Subsystem->GetExpedition() : nullptr;
	if (!E) return FText::GetEmpty();
	FString S;
	if (const auto& D = E->craft().docking(); D.active)
		S += FString::Printf(TEXT("KENETLENME: %.1f m, yaklaşma %.2f m/s %s\n"), D.range_m, D.closing_ms, D.docked ? TEXT("— KENETLENDİ") : TEXT(""));
	for (const auto& P : E->construction().projects())
		if (P.state != kozmo::build::State::Done)
			S += FString::Printf(TEXT("İNŞAAT: %s %%%.0f (%s)\n"), P.reinforce ? TEXT("güçlendirme") : *KozmoStr(kozmo::colony::module_name(P.module)), P.progress() * 100.0,
				*KozmoStr(kozmo::build::to_string(P.state)));
	S += TEXT("Görevler:");
	for (const auto& T : E->tasks()) S += TEXT("\n• ") + KozmoStr(T);
	const auto& L = E->log();
	for (int32 i = FMath::Max(0, static_cast<int32>(L.size()) - 3); i < static_cast<int32>(L.size()); ++i) S += TEXT("\n") + KozmoStr(L[i]);
	return FText::FromString(S);
}

void SKozmoExpeditionHud::OnNova(const FText& T, ETextCommit::Type C)
{
	if (C != ETextCommit::OnEnter || !Subsystem.IsValid() || T.IsEmpty()) return;
	NovaText = FText::FromString(Subsystem->AskNova(T.ToString()));
	if (NovaBox.IsValid()) NovaBox->SetText(FText::GetEmpty());
}

#undef LOCTEXT_NAMESPACE

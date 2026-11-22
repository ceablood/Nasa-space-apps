#include "KozmoAudioDirector.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "KozmoSubsystem.h"
#include "Sound/SoundBase.h"

UKozmoAudioDirector::UKozmoAudioDirector() { PrimaryComponentTick.bCanEverTick = true; }

void UKozmoAudioDirector::PlayCue(kozmo::acoustics::Cue Cue, const FVector& Source, bool bTouching, USoundBase* Sound)
{
	UWorld* W = GetWorld();
	UKozmoSubsystem* K = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
	const auto* E = K ? K->GetExpedition() : nullptr;
	if (!E) return;
	APlayerController* PC = W->GetFirstPlayerController();
	const FVector Listener = PC && PC->GetPawn() ? PC->GetPawn()->GetActorLocation() : Source;
	const double D = FVector::Dist(Listener, Source) / 100.0;
	const bool Inside = E->player().mode != kozmo::world::PlayerMode::OnFoot;
	const auto H = kozmo::acoustics::hear(Cue, E->env(), D, Inside, bTouching, true);
	const auto& Set = K->Settings();
	if (H.audible && Sound)
	{
		// dB -> doğrusal ölçek (60 dB referans), ayar ses düzeyleriyle
		const float Vol = FMath::Clamp(FMath::Pow(10.f, static_cast<float>(H.level_db - 60.0) / 20.f), 0.f, 4.f) * static_cast<float>(Set.master_volume * Set.sfx_volume);
		UGameplayStatics::PlaySoundAtLocation(this, Sound, Source, Vol);
	}
	if (Set.subtitles)
	{
		const FString T = H.audible ? FString::Printf(TEXT("[%s — %s]"), *KozmoStr(kozmo::acoustics::to_string(Cue)), *KozmoStr(kozmo::acoustics::to_string(H.channel)))
									: FString::Printf(TEXT("[%s — duyulmuyor: %s]"), *KozmoStr(kozmo::acoustics::to_string(Cue)), *KozmoStr(H.note));
		Pending.Add({Clock + H.delay_s, T});   // ses hızıyla gecikmeli altyazı (Mars'ta daha geç)
	}
}

void UKozmoAudioDirector::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* Fn)
{
	Super::TickComponent(Dt, Type, Fn);
	Clock += Dt;
	for (int32 i = Pending.Num() - 1; i >= 0; --i)
		if (Pending[i].At <= Clock)
		{
			Lines.Add(Pending[i].Text);
			Pending.RemoveAt(i);
		}
	while (Lines.Num() > 6) Lines.RemoveAt(0);
}

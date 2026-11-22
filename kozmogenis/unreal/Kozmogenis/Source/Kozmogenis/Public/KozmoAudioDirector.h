// KOZMOGENİS — ses yönetmeni (V30 §19 ses + erişilebilirlik): oyundaki ses olaylarını çekirdekteki akustik
// kurallarla (acoustics::hear) değerlendirir — vakumda hava yoluyla ses yok, Mars'ta ~20 dB zayıf ve gecikmeli,
// temas/telsiz kanalları — ve ayarlara göre ses düzeyi + altyazı üretir. Ses varlıkları (USoundBase) eklendiğinde
// PlayCue bu düzeyleri kullanır; şimdilik altyazılar HUD'da gösterilir.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "Components/ActorComponent.h"
#include "CoreMinimal.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/acoustics.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmoAudioDirector.generated.h"

class USoundBase;

UCLASS(ClassGroup = (Kozmo), meta = (BlueprintSpawnableComponent))
class KOZMOGENIS_API UKozmoAudioDirector : public UActorComponent
{
	GENERATED_BODY()

public:
	UKozmoAudioDirector();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	/** Ses olayı: Cue (acoustics::Cue), kaynak konumu; dinleyici durumu çekirdek seferinden okunur */
	void PlayCue(kozmo::acoustics::Cue Cue, const FVector& Source, bool bTouching, USoundBase* Sound = nullptr);
	/** Son altyazılar (erişilebilirlik): "[RCS iticisi — yapı (temas)]" */
	const TArray<FString>& Subtitles() const { return Lines; }

private:
	struct FPending { double At; FString Text; };
	TArray<FPending> Pending;
	TArray<FString> Lines;
	double Clock = 0;
};

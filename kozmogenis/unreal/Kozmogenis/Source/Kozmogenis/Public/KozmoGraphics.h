// KOZMOGENİS — grafik kalite profilleri (V30 §27). Her profil motorun gerçek konsol değişkenlerini ve
// ölçeklenebilirlik gruplarını ayarlar; uydurma "kalite" çarpanı yoktur.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ ve ÖLÇÜLMEDİ. FPS değerleri Cumartesi hedef PC'de ölçülecek.
#pragma once

#include "CoreMinimal.h"
#include "KozmoGraphics.generated.h"

UENUM(BlueprintType)
enum class EKozmoQuality : uint8
{
	Ultra,
	High,
	Medium,
	Low,
	VeryLow,
	Performance,
	Integrated   // dahili ekran kartı (AMD Radeon Graphics / Intel UHD-Iris) profili
};

namespace KozmoGraphics
{
	struct FProfile
	{
		const TCHAR* Name;
		int32 Scalability;          // 0 düşük .. 3 epik (sg.* grupları)
		float ScreenPercentage;     // iç çözünürlük; TSR/TAA ile yukarı ölçeklenir
		int32 GlobalIllumination;   // r.DynamicGlobalIlluminationMethod: 0 yok, 1 Lumen
		int32 Reflections;          // r.ReflectionMethod: 0 yok, 1 Lumen, 2 ekran uzayı
		bool bVirtualShadows;       // r.Shadow.Virtual.Enable
		bool bVolumetricFog;        // r.VolumetricFog
		bool bVolumetricClouds;     // bulut bileşeni açılır mı
		int32 AntiAliasing;         // r.AntiAliasingMethod: 1 FXAA, 2 TAA, 4 TSR
		float MaxFPS;               // t.MaxFPS (0 sınırsız)
	};

	const FProfile& Get(EKozmoQuality Q);
	/** Profili motor değişkenlerine uygular. */
	void Apply(EKozmoQuality Q);
	/** Ekran kartı adından ve bellekten öneri (sezgisel; yanlışsa oyuncu elle seçer). */
	EKozmoQuality Recommend(FString& OutReason);
	EKozmoQuality Current();
}

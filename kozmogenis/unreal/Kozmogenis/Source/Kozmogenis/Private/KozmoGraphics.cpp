#include "KozmoGraphics.h"

#include "GameFramework/GameUserSettings.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformMemory.h"
#include "Engine/Engine.h"

namespace
{
const KozmoGraphics::FProfile GProfiles[] = {
	//  ad              sg  ekran% GI refl VSM   sis    bulut  AA  fps
	{TEXT("Ultra"),       3, 100.f, 1, 1, true,  true,  true,  4, 0.f},
	{TEXT("Yüksek"),      2, 100.f, 1, 1, true,  true,  true,  4, 120.f},
	{TEXT("Orta"),        2,  85.f, 0, 2, false, true,  true,  4, 60.f},
	{TEXT("Düşük"),       1,  75.f, 0, 2, false, false, false, 2, 60.f},
	{TEXT("Çok düşük"),   0,  67.f, 0, 0, false, false, false, 1, 60.f},
	{TEXT("Performans"),  1,  60.f, 0, 2, false, false, false, 4, 144.f},
	{TEXT("Dahili GPU"),  1,  70.f, 0, 2, false, false, false, 2, 60.f},
};
EKozmoQuality GCurrent = EKozmoQuality::Integrated;

void SetCVar(const TCHAR* Name, float Value)
{
	if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name))
	{
		V->Set(Value, ECVF_SetByGameSetting);
	}
}
}  // namespace

const KozmoGraphics::FProfile& KozmoGraphics::Get(EKozmoQuality Q)
{
	return GProfiles[FMath::Clamp(static_cast<int32>(Q), 0, static_cast<int32>(UE_ARRAY_COUNT(GProfiles)) - 1)];
}

EKozmoQuality KozmoGraphics::Current() { return GCurrent; }

void KozmoGraphics::Apply(EKozmoQuality Q)
{
	const FProfile& P = Get(Q);
	if (UGameUserSettings* S = GEngine ? GEngine->GetGameUserSettings() : nullptr)
	{
		S->SetOverallScalabilityLevel(P.Scalability);
		S->SetFrameRateLimit(P.MaxFPS);
		S->ApplySettings(false);
	}
	SetCVar(TEXT("r.ScreenPercentage"), P.ScreenPercentage);
	SetCVar(TEXT("r.DynamicGlobalIlluminationMethod"), static_cast<float>(P.GlobalIllumination));
	SetCVar(TEXT("r.ReflectionMethod"), static_cast<float>(P.Reflections));
	SetCVar(TEXT("r.Shadow.Virtual.Enable"), P.bVirtualShadows ? 1.f : 0.f);
	SetCVar(TEXT("r.VolumetricFog"), P.bVolumetricFog ? 1.f : 0.f);
	SetCVar(TEXT("r.AntiAliasingMethod"), static_cast<float>(P.AntiAliasing));
	SetCVar(TEXT("t.MaxFPS"), P.MaxFPS);
	GCurrent = Q;
}

EKozmoQuality KozmoGraphics::Recommend(FString& OutReason)
{
	const FString Gpu = FPlatformMisc::GetPrimaryGPUBrand();
	const uint32 RamGB = FPlatformMemory::GetConstants().TotalPhysicalGB;
	// Dahili GPU adları: AMD APU'lar "AMD Radeon(TM) Graphics" / "Radeon Vega", Intel "UHD/Iris/HD Graphics".
	// Ayrık kartlar model numarası taşır (RX 6600, RTX 3060 ...). Sezgiseldir; oyuncu her zaman değiştirebilir.
	const bool bIntegrated = Gpu.Contains(TEXT("Radeon(TM) Graphics")) || Gpu.Equals(TEXT("AMD Radeon Graphics")) ||
		Gpu.Contains(TEXT("Vega")) || Gpu.Contains(TEXT("UHD")) || Gpu.Contains(TEXT("Iris")) || Gpu.Contains(TEXT("HD Graphics"));
	if (bIntegrated)
	{
		OutReason = FString::Printf(TEXT("Dahili ekran kartı algılandı (%s, %u GB RAM)"), *Gpu, RamGB);
		return EKozmoQuality::Integrated;
	}
	const bool bHighEnd = Gpu.Contains(TEXT("RTX 40")) || Gpu.Contains(TEXT("RTX 50")) || Gpu.Contains(TEXT("RX 7")) ||
		Gpu.Contains(TEXT("RX 9")) || Gpu.Contains(TEXT("RTX 308")) || Gpu.Contains(TEXT("RTX 309"));
	if (bHighEnd && RamGB >= 16)
	{
		OutReason = FString::Printf(TEXT("Güçlü ayrık ekran kartı (%s)"), *Gpu);
		return EKozmoQuality::High;
	}
	OutReason = FString::Printf(TEXT("Ayrık ekran kartı varsayıldı (%s, %u GB RAM)"), *Gpu, RamGB);
	return RamGB >= 16 ? EKozmoQuality::Medium : EKozmoQuality::Low;
}

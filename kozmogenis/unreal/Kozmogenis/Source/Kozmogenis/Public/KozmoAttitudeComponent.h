// KOZMOGENİS — tutum kontrol bileşeni (V30 §14.2): sahibinin yönelimini çekirdekteki attitude::Body (kuaterniyon,
// Euler denklemleri, RCS + reaksiyon tekerleği, SAS) ile sürer. Yörüngede ve uzay boşluğunda kullanılır.
// Kontrol: SetStick (-1..1), SAS modları (Kapalı / Dönüşü durdur / Yönelimi tut / Hedefe yönel).
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "Components/ActorComponent.h"
#include "CoreMinimal.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/attitude.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmoAttitudeComponent.generated.h"

UCLASS(ClassGroup = (Kozmo), meta = (BlueprintSpawnableComponent))
class KOZMOGENIS_API UKozmoAttitudeComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UKozmoAttitudeComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Attitude") void SetStick(FVector Stick);
	/** 0 kapalı, 1 dönüşü durdur, 2 yönelimi tut, 3 hedefe yönel */
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Attitude") void SetSasMode(int32 Mode);
	UFUNCTION(BlueprintCallable, Category = "Kozmo|Attitude") void SetTargetRotation(FRotator Target);
	UFUNCTION(BlueprintPure, Category = "Kozmo|Attitude") FString GetStatus() const;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kozmo|Attitude") bool bDriveOwnerRotation = true;

private:
	static kozmo::attitude::Quat ToQuat(const FQuat& Q);
	static FQuat FromQuat(const kozmo::attitude::Quat& Q);
	kozmo::attitude::Body Body;
};

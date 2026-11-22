#include "KozmoAttitudeComponent.h"

#include "GameFramework/Actor.h"
#include "KozmoSubsystem.h"   // KozmoStr

UKozmoAttitudeComponent::UKozmoAttitudeComponent() { PrimaryComponentTick.bCanEverTick = true; }

kozmo::attitude::Quat UKozmoAttitudeComponent::ToQuat(const FQuat& Q) { return {Q.W, Q.X, Q.Y, Q.Z}; }
FQuat UKozmoAttitudeComponent::FromQuat(const kozmo::attitude::Quat& Q) { return FQuat(Q.x, Q.y, Q.z, Q.w); }

void UKozmoAttitudeComponent::SetStick(FVector S) { Body.set_input({S.X, S.Y, S.Z}); }

void UKozmoAttitudeComponent::SetSasMode(int32 M) { Body.set_sas(static_cast<kozmo::attitude::Sas>(FMath::Clamp(M, 0, 3))); }

void UKozmoAttitudeComponent::SetTargetRotation(FRotator T) { Body.set_target(ToQuat(T.Quaternion())); }

FString UKozmoAttitudeComponent::GetStatus() const
{
	const auto W = Body.omega();
	return FString::Printf(TEXT("%s | dönüş %.2f °/s | tekerlek %.0f N·m·s | RCS yakıtı %.2f kg"), *KozmoStr(kozmo::attitude::to_string(Body.sas())),
		FMath::RadiansToDegrees(W.norm()), Body.wheel_momentum().norm(), Body.rcs_propellant_used());
}

void UKozmoAttitudeComponent::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* Fn)
{
	Super::TickComponent(Dt, Type, Fn);
	AActor* Owner = GetOwner();
	if (!Owner || Dt <= 0) return;
	// sabit alt adım (20 ms): kare hızından bağımsız fizik
	float Left = FMath::Min(Dt, 0.25f);
	while (Left > 0)
	{
		const float Step = FMath::Min(Left, 0.02f);
		Body.step(Step);
		Left -= Step;
	}
	if (bDriveOwnerRotation) Owner->SetActorRotation(FromQuat(Body.q()));
}

#include "KozmogenisCharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KozmoExpedition.h"
#include "KozmoSubsystem.h"
THIRD_PARTY_INCLUDES_START
#include "kozmo/life.hpp"
THIRD_PARTY_INCLUDES_END

AKozmogenisCharacter::AKozmogenisCharacter()
{
	PrimaryActorTick.bCanEverTick = true;
	GetCapsuleComponent()->InitCapsuleSize(35.f, 90.f);
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(GetCapsuleComponent());
	Camera->SetRelativeLocation(FVector(0.f, 0.f, 70.f));
	Camera->bUsePawnControlRotation = true;
	bUseControllerRotationYaw = true;
	AutoPossessPlayer = EAutoReceiveInput::Disabled;
}

UKozmoSubsystem* AKozmogenisCharacter::Kozmo() const
{
	return GetGameInstance() ? GetGameInstance()->GetSubsystem<UKozmoSubsystem>() : nullptr;
}

void AKozmogenisCharacter::SetScene(AKozmoExpeditionScene* InScene, float G)
{
	Scene = InScene;
	UCharacterMovementComponent* M = GetCharacterMovement();
	M->GravityScale = G / 9.80665f;
	// tercih edilen yürüyüş hızı Froude benzerliğiyle (çekirdekle aynı formül); koşu 2 katı
	M->MaxWalkSpeed = static_cast<float>(kozmo::life::walking_speed_ms(G)) * 100.f * 1.6f;
	M->JumpZVelocity = 420.f;           // aynı kas gücü: düşük g'de çok daha yükseğe/uzağa sıçrar
	M->AirControl = 0.15f;
}

void AKozmogenisCharacter::SetupPlayerInputComponent(UInputComponent* In)
{
	Super::SetupPlayerInputComponent(In);
	In->BindAxis(TEXT("MoveForward"), this, &AKozmogenisCharacter::MoveForward);
	In->BindAxis(TEXT("MoveRight"), this, &AKozmogenisCharacter::MoveRight);
	In->BindAxis(TEXT("Turn"), this, &APawn::AddControllerYawInput);
	In->BindAxis(TEXT("LookUp"), this, &APawn::AddControllerPitchInput);
	In->BindAction(TEXT("Jump"), IE_Pressed, this, &ACharacter::Jump);
	In->BindAction(TEXT("Interact"), IE_Pressed, this, &AKozmogenisCharacter::Interact);
	In->BindAction(TEXT("Sample"), IE_Pressed, this, &AKozmogenisCharacter::Sample);
	In->BindAction(TEXT("Topic1"), IE_Pressed, this, &AKozmogenisCharacter::Topic1);
	In->BindAction(TEXT("Topic2"), IE_Pressed, this, &AKozmogenisCharacter::Topic2);
	In->BindAction(TEXT("Topic3"), IE_Pressed, this, &AKozmogenisCharacter::Topic3);
	In->BindAction(TEXT("Topic4"), IE_Pressed, this, &AKozmogenisCharacter::Topic4);
	In->BindAction(TEXT("Topic5"), IE_Pressed, this, &AKozmogenisCharacter::Topic5);
}

void AKozmogenisCharacter::MoveForward(float V)
{
	if (Controller && !FMath::IsNearlyZero(V)) AddMovementInput(FRotationMatrix(FRotator(0, Controller->GetControlRotation().Yaw, 0)).GetUnitAxis(EAxis::X), V);
}

void AKozmogenisCharacter::MoveRight(float V)
{
	if (Controller && !FMath::IsNearlyZero(V)) AddMovementInput(FRotationMatrix(FRotator(0, Controller->GetControlRotation().Yaw, 0)).GetUnitAxis(EAxis::Y), V);
}

bool AKozmogenisCharacter::Trace(FHitResult& Hit) const
{
	const FVector S = Camera->GetComponentLocation(), E = S + Camera->GetForwardVector() * 350.f;
	FCollisionQueryParams Q;
	Q.AddIgnoredActor(this);
	return GetWorld()->LineTraceSingleByChannel(Hit, S, E, ECC_Visibility, Q);
}

void AKozmogenisCharacter::Interact()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	FHitResult Hit;
	if (!E || !Scene || !Trace(Hit) || !Hit.GetComponent()) return;
	for (const FName& Tag : Hit.GetComponent()->ComponentTags)
	{
		const FString T = Tag.ToString();
		if (T.StartsWith(TEXT("door:")))
		{
			const std::string Id = KozmoStd(T.RightChop(5));
			if (E->player().mode == kozmo::world::PlayerMode::InBuilding) (void)E->leave_building();
			kozmo::Status St = E->enter_building(Id);
			if (!St.ok() && E->player().mode == kozmo::world::PlayerMode::OnFoot)
			{
				// kapı işaretine yakınsak konumu kapıya eşitleyip yeniden dene (3B konum çekirdekten hassas değil)
				const auto* B = E->settlement().find(Id);
				if (B) E->set_player_position(B->door_x, B->door_y);
				St = E->enter_building(Id);
			}
			Scene->SetFeedback(St.ok() ? KozmoStr(E->settlement().find(Id)->name) + TEXT(" — içeridesin") : KozmoStr(St.error().message));
			return;
		}
		if (T.StartsWith(TEXT("use:")))
		{
			if (E->player().mode != kozmo::world::PlayerMode::InBuilding)
			{
				const std::string B = KozmoStd(Scene->BuildingAt(GetActorLocation()));
				if (!B.empty())
				{
					const auto* Bd = E->settlement().find(B);
					if (Bd) E->set_player_position(Bd->door_x, Bd->door_y);
					(void)E->enter_building(B);
				}
			}
			auto R = E->use(KozmoStd(T.RightChop(4)));
			Scene->SetFeedback(R.ok() ? KozmoStr(R.value()) : KozmoStr(R.error().message));
			return;
		}
		if (T.StartsWith(TEXT("npc:")))
		{
			FocusedNpc = FCString::Atoi(*T.RightChop(4));
			Talk(TEXT("selam"));
			return;
		}
		if (T.StartsWith(TEXT("craft:")))
		{
			auto St = E->enter_craft();
			if (St.ok()) Scene->PossessCraft();
			else Scene->SetFeedback(KozmoStr(St.error().message));
			return;
		}
	}
}

void AKozmogenisCharacter::Talk(const FString& Topic)
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !Scene || FocusedNpc < 0) return;
	auto R = E->talk(FocusedNpc, KozmoStd(Topic));
	Scene->SetFeedback(R.ok() ? KozmoStr(R.value()) + TEXT("\n[1 selam  2 nasılsın  3 iş  4 koloni  5 yardım]") : KozmoStr(R.error().message));
}

void AKozmogenisCharacter::Sample()
{
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !Scene) return;
	auto St = E->collect_sample();
	Scene->SetFeedback(St.ok() ? FString::Printf(TEXT("Numune toplandı (%d). Laboratuvarda mikroskopla analiz et."), E->player().samples) : KozmoStr(St.error().message));
}

void AKozmogenisCharacter::Tick(float Dt)
{
	Super::Tick(Dt);
	UKozmoSubsystem* K = Kozmo();
	auto* E = K ? K->GetExpedition() : nullptr;
	if (!E || !Scene) return;
	const FVector2D S = Scene->WorldToSettlement(GetActorLocation());
	// bina sınırından çıkıldıysa çekirdekte de çık
	if (E->player().mode == kozmo::world::PlayerMode::InBuilding && Scene->BuildingAt(GetActorLocation()).IsEmpty()) (void)E->leave_building();
	E->set_player_position(S.X, S.Y);
	if (!E->player().body.alive) Scene->SetFeedback(TEXT("HAYATINI KAYBETTİN: ") + KozmoStr(E->player().body.last_cause) + TEXT(" — panelden seferi yeniden başlat"));
}

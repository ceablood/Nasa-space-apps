#include "KozmogenisColony.h"

#include "Components/PointLightComponent.h"
#include "Components/TextRenderComponent.h"
#include "KozmoShapes.h"
#include "KozmoSubsystem.h"   // KozmoStr

using kozmo::life::Building;
using kozmo::life::District;
using kozmo::life::Layout;

AKozmogenisColony::AKozmogenisColony()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
}

void AKozmogenisColony::Build(const kozmo::life::Settlement& S, const FString& SiteId, float Progress)
{
	Buildings = S.buildings();
	const FLinearColor Path(0.30f, 0.30f, 0.31f);
	// meydan ve kapılara giden basınçlı koridor / yürüyüş yolları
	KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, FVector(0, 0, 0.05f), FVector(22.f, 22.f, 0.1f), Path, 0.9f);
	for (const Building& B : Buildings)
	{
		const FVector Door(B.door_x, B.door_y, 0.f);
		const float Len = Door.Size2D();
		const FRotator Rot(0.f, FMath::RadiansToDegrees(FMath::Atan2(B.door_y, B.door_x)), 0.f);
		if (!B.built && B.district != District::LandingPad)
		{
			BuildPlot(B, KozmoStr(B.id) == SiteId, Progress);   // arsa ya da inşaat sahası
			continue;
		}
		KozmoShapes::Add(this, Root, EKozmoShape::Cube, Door * 0.5f + FVector(0, 0, 0.04f), FVector(Len / 1.f, 2.4f, 0.08f), Path, 0.9f, 0.f, Rot);
		BuildBuilding(B, S.layout());
	}
}

void AKozmogenisColony::BuildBuilding(const Building& B, Layout L)
{
	const FVector C(B.x, B.y, 0.f);
	const float W = B.w, D = B.d, H = B.h;
	FLinearColor Wall(0.62f, 0.62f, 0.60f), Floor(0.26f, 0.26f, 0.27f);
	if (B.district == District::Hospital) Wall = FLinearColor(0.70f, 0.72f, 0.74f);
	if (B.district == District::Power) Wall = FLinearColor(0.45f, 0.40f, 0.20f);
	if (B.district == District::Farm) Wall = FLinearColor(0.35f, 0.50f, 0.32f);
	if (B.district == District::LandingPad)
	{
		KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, C + FVector(0, 0, 0.1f), FVector(W, D, 0.2f), FLinearColor(0.42f, 0.41f, 0.39f), 0.85f);
		KozmoShapes::Label(this, Root, C + FVector(0, 0, 0.3f), TEXT("İNİŞ ALANI"), 300.f, FColor(230, 200, 60), FRotator(90.f, 0.f, 0.f));
		return;
	}
	// zemin
	KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + FVector(0, 0, 0.05f), FVector(W, D, 0.1f), Floor, 0.8f);
	// duvarlar: kapı meydana bakan tarafta 2.4 m boşluk
	const FVector2D ToPlaza = FVector2D(-B.x, -B.y).GetSafeNormal();
	const bool DoorOnX = FMath::Abs(ToPlaza.X) > FMath::Abs(ToPlaza.Y);
	const float T = 0.25f;
	for (int32 Side = 0; Side < 4; ++Side)
	{
		const bool AlongX = Side < 2;               // 0,1: ±X duvarı (Y yönünde uzanır); 2,3: ±Y duvarı
		const float Sign = (Side % 2 == 0) ? 1.f : -1.f;
		const FVector Mid = AlongX ? FVector(Sign * W / 2, 0, H / 2) : FVector(0, Sign * D / 2, H / 2);
		const float Span = AlongX ? D : W;
		const bool HasDoor = DoorOnX ? (AlongX && FMath::Sign(ToPlaza.X) == Sign) : (!AlongX && FMath::Sign(ToPlaza.Y) == Sign);
		if (!HasDoor)
		{
			KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + Mid, AlongX ? FVector(T, Span, H) : FVector(Span, T, H), Wall, 0.6f);
			continue;
		}
		const float Seg = (Span - 2.4f) / 2.f;
		for (int32 k = -1; k <= 1; k += 2)
		{
			const FVector Off = AlongX ? FVector(0, k * (1.2f + Seg / 2), 0) : FVector(k * (1.2f + Seg / 2), 0, 0);
			KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + Mid + Off, AlongX ? FVector(T, Seg, H) : FVector(Seg, T, H), Wall, 0.6f);
		}
		// kapı üstü ve kapı işareti (etkileşim: E ile gir/çık)
		KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + Mid + FVector(0, 0, H / 2 - 0.4f), AlongX ? FVector(T, 2.4f, 0.8f) : FVector(2.4f, T, 0.8f), Wall, 0.6f);
		UStaticMeshComponent* Mark = KozmoShapes::Add(this, Root, EKozmoShape::Cube, FVector(B.door_x, B.door_y, 1.0f), FVector(0.3f, 0.3f, 0.3f),
			FLinearColor(0.1f, 0.6f, 0.8f), 0.3f, 0.f, FRotator::ZeroRotator, false);
		Mark->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		Mark->SetCollisionResponseToAllChannels(ECR_Ignore);
		Mark->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
		Mark->ComponentTags.Add(FName(*(TEXT("door:") + KozmoStr(B.id))));
		KozmoShapes::Label(this, Root, FVector(B.door_x, B.door_y, H + 0.6f), KozmoStr(B.name), 60.f, FColor(220, 235, 245),
			FRotator(0.f, FMath::RadiansToDegrees(FMath::Atan2(-B.y, -B.x)) + 180.f, 0.f));
	}
	// çatı: yüzey kubbesi / yer altında regolit örtüsü (radyasyon kalkanı) / diğerlerinde düz çatı
	if (L == Layout::SurfaceDomes || L == Layout::Polar)
		KozmoShapes::Add(this, Root, EKozmoShape::Sphere, C + FVector(0, 0, H), FVector(W * 1.05f, D * 1.05f, 2.f * H * 0.6f), FLinearColor(0.75f, 0.76f, 0.78f), 0.3f, 0.2f);
	else if (L == Layout::Underground && B.pressurized)
		KozmoShapes::Add(this, Root, EKozmoShape::Sphere, C + FVector(0, 0, H * 0.6f), FVector(W * 1.4f, D * 1.4f, H * 2.4f), FLinearColor(0.36f, 0.35f, 0.33f), 0.95f);
	else
		KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + FVector(0, 0, H), FVector(W, D, 0.2f), Wall, 0.6f);
	// iç mekân: oda konsolları (etiketli; E ile kullanılır)
	int32 n = 0;
	for (const auto& Room : B.rooms)
		for (const auto& It : Room.items)
		{
			const float A = 2.f * PI * n++ / 6.f;
			const FVector P = C + FVector(FMath::Cos(A) * W * 0.3f, FMath::Sin(A) * D * 0.3f, 0.6f);
			UStaticMeshComponent* K = KozmoShapes::Add(this, Root, EKozmoShape::Cube, P, FVector(0.8f, 0.5f, 1.1f), FLinearColor(0.10f, 0.12f, 0.15f), 0.4f, 0.4f);
			K->ComponentTags.Add(FName(*(TEXT("use:") + KozmoStr(It.id))));
			KozmoShapes::Label(this, Root, P + FVector(0, 0, 0.8f), KozmoStr(It.name), 18.f, FColor(140, 220, 235));
		}
	UPointLightComponent* Lamp = NewObject<UPointLightComponent>(this);
	Lamp->SetupAttachment(Root);
	Lamp->SetRelativeLocation((C + FVector(0, 0, H - 0.4f)) * 100.f);
	Lamp->SetIntensity(3000.f);
	Lamp->SetAttenuationRadius(FMath::Max(W, D) * 90.f);
	Lamp->SetLightColor(FLinearColor(1.f, 0.92f, 0.82f));
	Lamp->SetCastShadows(false);
	Lamp->RegisterComponent();
}

void AKozmogenisColony::BuildPlot(const Building& B, bool bSite, float Progress)
{
	const FVector C(B.x, B.y, 0.f);
	// arsa: köşe kazıkları; inşaat sahası: temel + ilerlemeyle yükselen iskele ve duvarlar
	for (int32 k = 0; k < 4; ++k)
	{
		const FVector Corner = C + FVector((k & 1 ? 1.f : -1.f) * B.w / 2, (k & 2 ? 1.f : -1.f) * B.d / 2, 0.5f);
		KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, Corner, FVector(0.1f, 0.1f, 1.f), FLinearColor(0.8f, 0.5f, 0.1f), 0.6f, 0.f, FRotator::ZeroRotator, false);
	}
	if (!bSite)
	{
		KozmoShapes::Label(this, Root, C + FVector(0, 0, 1.4f), KozmoStr(B.name) + TEXT(" (arsa)"), 50.f, FColor(200, 170, 120));
		return;
	}
	const float H = FMath::Max(0.2f, B.h * Progress);
	KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + FVector(0, 0, 0.1f), FVector(B.w, B.d, 0.2f), FLinearColor(0.4f, 0.4f, 0.4f), 0.9f);
	if (Progress > 0.3f) KozmoShapes::Add(this, Root, EKozmoShape::Cube, C + FVector(0, 0, H / 2), FVector(B.w * 0.9f, B.d * 0.9f, H), FLinearColor(0.55f, 0.55f, 0.53f), 0.7f);
	for (int32 i = 0; i < 6; ++i)   // iskele direkleri
	{
		const float A = 2.f * PI * i / 6.f;
		KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, C + FVector(FMath::Cos(A) * B.w * 0.55f, FMath::Sin(A) * B.d * 0.55f, B.h / 2), FVector(0.08f, 0.08f, B.h),
			FLinearColor(0.75f, 0.6f, 0.1f), 0.5f, 0.8f, FRotator::ZeroRotator, false);
	}
	KozmoShapes::Label(this, Root, C + FVector(0, 0, B.h + 1.f), FString::Printf(TEXT("%s — İNŞAAT %%%.0f"), *KozmoStr(B.name), Progress * 100.f), 60.f, FColor(255, 200, 90));
}

FString AKozmogenisColony::BuildingAt(const FVector& World) const
{
	const FVector L = GetActorTransform().InverseTransformPosition(World) / 100.f;
	for (const Building& B : Buildings)
		if (B.district != District::LandingPad && B.built && FMath::Abs(L.X - B.x) <= B.w / 2 && FMath::Abs(L.Y - B.y) <= B.d / 2) return KozmoStr(B.id);
	return FString();
}

// ------------------------------------------------------------------------------------------------
AKozmogenisNPC::AKozmogenisNPC()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
}

void AKozmogenisNPC::Setup(int32 InId, const FString& Name, int32 Job)
{
	Id = InId;
	NpcName = Name;
	static const FLinearColor JobColors[] = {FLinearColor(0.3f, 0.6f, 0.2f), FLinearColor(0.85f, 0.5f, 0.1f), FLinearColor(0.5f, 0.4f, 0.3f),
		FLinearColor(0.2f, 0.4f, 0.8f), FLinearColor(0.85f, 0.85f, 0.9f), FLinearColor(0.2f, 0.2f, 0.3f), FLinearColor(0.7f, 0.1f, 0.1f)};
	const FLinearColor Suit = JobColors[FMath::Clamp(Job, 0, 6)];
	UStaticMeshComponent* Body = KozmoShapes::Add(this, Root, EKozmoShape::Cylinder, FVector(0, 0, 0.85f), FVector(0.45f, 0.35f, 1.3f), Suit, 0.7f);
	Body->ComponentTags.Add(FName(*FString::Printf(TEXT("npc:%d"), Id)));
	UStaticMeshComponent* Head = KozmoShapes::Add(this, Root, EKozmoShape::Sphere, FVector(0, 0, 1.68f), FVector(0.26f, 0.26f, 0.3f), FLinearColor(0.72f, 0.55f, 0.42f), 0.6f);
	Head->ComponentTags.Add(FName(*FString::Printf(TEXT("npc:%d"), Id)));
	Label = KozmoShapes::Label(this, Root, FVector(0, 0, 2.15f), Name, 14.f, FColor(240, 240, 240));
}

void AKozmogenisNPC::Sync(const FVector& TargetWorld, const FString& Intent, bool bNear)
{
	Target = TargetWorld;
	if (Label) Label->SetText(FText::FromString(bNear ? NpcName + TEXT("\n") + Intent : NpcName));
	if (!bNear) SetActorLocation(TargetWorld);   // uzak NPC: soyut simülasyon, animasyon yok
}

void AKozmogenisNPC::Tick(float Dt)
{
	Super::Tick(Dt);
	const FVector P = GetActorLocation();
	const FVector To = Target - P;
	if (To.Size2D() > 5.f)
	{
		SetActorRotation(FRotator(0.f, To.Rotation().Yaw, 0.f));
		SetActorLocation(FMath::VInterpConstantTo(P, Target, Dt, 250.f));
		Bob += Dt * 8.f;   // basit yürüyüş salınımı (iskelet animasyonu planlandı)
		if (Root->GetNumChildrenComponents() > 0) Root->GetChildComponent(0)->SetRelativeRotation(FRotator(0.f, 0.f, FMath::Sin(Bob) * 4.f));
	}
}

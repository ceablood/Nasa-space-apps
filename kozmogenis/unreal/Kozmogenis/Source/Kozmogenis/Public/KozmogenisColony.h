// KOZMOGENİS — gezilebilir 3B koloni (V41 §4) ve yaşayan NPC'ler (§5). Yerleşim planı ve NPC kararları
// çekirdektedir (life::Settlement, life::Society); bu aktörler onları 3B'de kurar ve canlandırır.
// Binalar: zemin, kapı boşluklu duvarlar, çatı/kubbe (yer altı düzeninde regolit örtüsü), iç konsollar.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ. Davranış ağaçları / State Tree / Mass entegrasyonu PLANLANDI;
// bu dilimde karar mantığı test edilmiş C++ çekirdektedir.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

THIRD_PARTY_INCLUDES_START
#include "kozmo/life.hpp"
THIRD_PARTY_INCLUDES_END

#include "KozmogenisColony.generated.h"

class UTextRenderComponent;
class UPointLightComponent;

UCLASS()
class KOZMOGENIS_API AKozmogenisColony : public AActor
{
	GENERATED_BODY()

public:
	AKozmogenisColony();
	/** SiteId/Progress: etkin inşaat sahası (iskele + ilerleme etiketi) */
	void Build(const kozmo::life::Settlement& S, const FString& SiteId = FString(), float Progress = 0.f);
	/** Dünya konumu (cm) -> hangi binanın içinde (yoksa boş) */
	FString BuildingAt(const FVector& World) const;

private:
	void BuildBuilding(const kozmo::life::Building& B, kozmo::life::Layout L);
	void BuildPlot(const kozmo::life::Building& B, bool bSite, float Progress);
	UPROPERTY() TObjectPtr<USceneComponent> Root;
	TArray<kozmo::life::Building> Buildings;
};

UCLASS()
class KOZMOGENIS_API AKozmogenisNPC : public AActor
{
	GENERATED_BODY()

public:
	AKozmogenisNPC();
	virtual void Tick(float DeltaSeconds) override;
	void Setup(int32 InId, const FString& Name, int32 Job);
	/** Çekirdek NPC durumundan hedef konum ve etiket */
	void Sync(const FVector& TargetWorld, const FString& Intent, bool bNear);
	int32 GetNpcId() const { return Id; }

private:
	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UTextRenderComponent> Label;
	int32 Id = 0;
	FString NpcName;
	FVector Target = FVector::ZeroVector;
	float Bob = 0.f;
};

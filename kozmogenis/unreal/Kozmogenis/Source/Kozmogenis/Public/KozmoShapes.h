// KOZMOGENİS — motorun temel şekilleriyle (/Engine/BasicShapes) çalışma zamanı mesh kurma yardımcıları.
// Harici varlık gerekmez; gerçek modeller geldiğinde bu çağrılar Nanite mesh'leriyle değiştirilecek.
// DURUM: yazıldı, UE5 yokken DERLENMEDİ.
#pragma once

#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "CoreMinimal.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"

enum class EKozmoShape : uint8 { Cube, Cylinder, Sphere, Cone, Plane };

namespace KozmoShapes
{
	inline UStaticMesh* Mesh(EKozmoShape S)
	{
		static const TCHAR* Paths[] = {TEXT("/Engine/BasicShapes/Cube.Cube"), TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
			TEXT("/Engine/BasicShapes/Sphere.Sphere"), TEXT("/Engine/BasicShapes/Cone.Cone"), TEXT("/Engine/BasicShapes/Plane.Plane")};
		return LoadObject<UStaticMesh>(nullptr, Paths[static_cast<int32>(S)]);
	}

	inline UMaterialInterface* BaseMaterial()
	{
		return LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	}

	/** Şekil ekler. Ölçek metre cinsindendir (temel şekiller 1 m = 100 birimlik birim gövdeler). */
	inline UStaticMeshComponent* Add(AActor* Owner, USceneComponent* Parent, EKozmoShape S, const FVector& LocM, const FVector& SizeM,
		const FLinearColor& Color, float Roughness = 0.6f, float Metallic = 0.f, const FRotator& Rot = FRotator::ZeroRotator, bool bCollide = true)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Owner);
		C->SetStaticMesh(Mesh(S));
		C->SetupAttachment(Parent);
		C->SetRelativeLocationAndRotation(LocM * 100.f, Rot);
		C->SetRelativeScale3D(SizeM);
		C->SetCollisionEnabled(bCollide ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		C->SetCollisionResponseToAllChannels(bCollide ? ECR_Block : ECR_Ignore);
		if (UMaterialInterface* Base = BaseMaterial())
		{
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Base, Owner);
			M->SetVectorParameterValue(TEXT("Color"), Color);
			M->SetScalarParameterValue(TEXT("Roughness"), Roughness);
			M->SetScalarParameterValue(TEXT("Metallic"), Metallic);
			C->SetMaterial(0, M);
		}
		C->RegisterComponent();
		return C;
	}

	inline UTextRenderComponent* Label(AActor* Owner, USceneComponent* Parent, const FVector& LocM, const FString& Text, float SizeCm,
		const FColor& Color, const FRotator& Rot = FRotator::ZeroRotator)
	{
		UTextRenderComponent* T = NewObject<UTextRenderComponent>(Owner);
		T->SetupAttachment(Parent);
		T->SetRelativeLocationAndRotation(LocM * 100.f, Rot);
		T->SetText(FText::FromString(Text));
		T->SetWorldSize(SizeCm);
		T->SetTextRenderColor(Color);
		T->SetHorizontalAlignment(EHTA_Center);
		T->RegisterComponent();
		return T;
	}
}

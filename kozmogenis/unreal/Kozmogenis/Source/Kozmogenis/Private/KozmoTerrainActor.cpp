#include "KozmoTerrainActor.h"

#include "KozmoShapes.h"
#include "KozmoSubsystem.h"   // KozmoStr / KozmoStd
#include "ProceduralMeshComponent.h"

AKozmoTerrainActor::AKozmoTerrainActor()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->bUseAsyncCooking = true;
}

FString AKozmoTerrainActor::Generate(const FString& Body, int64 Seed, float SizeM, float CellM)
{
	auto Env = kozmo::challenge::body_environment(KozmoStd(Body));
	if (!Env.ok()) return KozmoStr(Env.error().message);
	Heightmap = kozmo::terrain::Heightmap::generate(Env.value(), static_cast<std::uint64_t>(Seed), SizeM, CellM);
	const kozmo::terrain::Mesh M = Heightmap.mesh(FMath::Max(1, MeshStep));
	TArray<FVector> V;
	TArray<FVector> N;
	TArray<int32> T;
	TArray<FVector2D> UV;
	TArray<FLinearColor> Col;
	TArray<FProcMeshTangent> Tan;
	const int32 Count = static_cast<int32>(M.vertices.size() / 3);
	V.Reserve(Count);
	N.Reserve(Count);
	UV.Reserve(Count);
	Col.Reserve(Count);
	const FLinearColor Base = Body == TEXT("mars") ? FLinearColor(0.45f, 0.24f, 0.13f)
		: (Body == TEXT("titan") ? FLinearColor(0.32f, 0.23f, 0.12f) : FLinearColor(0.36f, 0.36f, 0.35f));
	for (int32 i = 0; i < Count; ++i)
	{
		const float X = M.vertices[i * 3], Y = M.vertices[i * 3 + 1], Z = M.vertices[i * 3 + 2];
		V.Add(FVector(X, Y, Z) * 100.f);
		N.Add(FVector(M.normals[i * 3], M.normals[i * 3 + 1], M.normals[i * 3 + 2]));
		UV.Add(FVector2D(X / 50.f, Y / 50.f));
		// eğime göre ton (dik yamaçlar açık, düzlükler toz koyu) — vertex rengi destekleyen malzeme için
		const float Slope = static_cast<float>(Heightmap.slope_deg(X, Y));
		Col.Add(FMath::Lerp(Base, Base * 1.4f, FMath::Clamp(Slope / 30.f, 0.f, 1.f)));
	}
	T.Reserve(static_cast<int32>(M.triangles.size()));
	for (std::size_t i = 0; i + 2 < M.triangles.size(); i += 3)
	{
		T.Add(M.triangles[i]);
		T.Add(bFlipWinding ? M.triangles[i + 1] : M.triangles[i + 2]);
		T.Add(bFlipWinding ? M.triangles[i + 2] : M.triangles[i + 1]);
	}
	Mesh->CreateMeshSection_LinearColor(0, V, T, N, UV, Col, Tan, true);
	if (UMaterialInterface* Mat = KozmoShapes::BaseMaterial())
	{
		UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(Mat, this);
		D->SetVectorParameterValue(TEXT("Color"), Base);
		D->SetScalarParameterValue(TEXT("Roughness"), 0.95f);
		Mesh->SetMaterial(0, D);
	}
	// işaretler: lav tüpü girişleri (kırmızı direk) ve en iyi 3 iniş yeri (yeşil halka)
	for (const auto& P : Heightmap.pits())
	{
		KozmoShapes::Add(this, Mesh, EKozmoShape::Cylinder, FVector(P.x, P.y, Heightmap.height(P.x, P.y) + 10.f), FVector(0.4f, 0.4f, 20.f), FLinearColor(0.8f, 0.2f, 0.1f), 0.5f, 0.f,
			FRotator::ZeroRotator, false);
		KozmoShapes::Label(this, Mesh, FVector(P.x, P.y, Heightmap.height(P.x, P.y) + 25.f),
			FString::Printf(TEXT("Lav tüpü girişi Ø%.0f m, ~%.0f m tünel"), P.diameter_m, P.cave_length_m), 400.f, FColor(255, 140, 120));
	}
	int32 k = 0;
	for (const auto& S : Heightmap.find_landing_sites(20.0, 12.0, 1.5, 3))
	{
		KozmoShapes::Add(this, Mesh, EKozmoShape::Cylinder, FVector(S.x, S.y, S.height_m + 0.1f), FVector(20.f, 20.f, 0.05f), FLinearColor(0.1f, 0.7f, 0.3f), 0.5f, 0.f,
			FRotator::ZeroRotator, false);
		KozmoShapes::Label(this, Mesh, FVector(S.x, S.y, S.height_m + 4.f), FString::Printf(TEXT("İniş adayı %d — %s"), ++k, *KozmoStr(S.reason)), 300.f, FColor(150, 255, 170));
	}
	bReady = true;
	return FString::Printf(TEXT("%s yüzeyi: %d krater, %d lav tüpü girişi, %d köşe"), *Body, static_cast<int32>(Heightmap.craters().size()),
		static_cast<int32>(Heightmap.pits().size()), Count);
}

float AKozmoTerrainActor::GetHeightAt(const FVector& W) const
{
	if (!bReady) return GetActorLocation().Z;
	const FVector L = (W - GetActorLocation()) / 100.f;
	return GetActorLocation().Z + static_cast<float>(Heightmap.height(L.X, L.Y)) * 100.f;
}

float AKozmoTerrainActor::GetSlopeAt(const FVector& W) const
{
	if (!bReady) return 0.f;
	const FVector L = (W - GetActorLocation()) / 100.f;
	return static_cast<float>(Heightmap.slope_deg(L.X, L.Y));
}

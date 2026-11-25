#include "YellBattle.h"

#include "Components/BoxComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextRenderActor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NavigationSystem.h"
#include "NavMesh/RecastNavMesh.h"

namespace
{
	constexpr double BaseX = 6650.0;
	constexpr double LaneSpacing = 2250.0;
	const FVector2D Extent(7700, 3900);
	const FLinearColor Turf(0.10f, 0.15f, 0.13f);
	const FLinearColor Road(0.25f, 0.26f, 0.25f);
	const FLinearColor Wall(0.34f, 0.40f, 0.41f);
	const FLinearColor Friendly(0.05f, 0.48f, 0.60f);
	const FLinearColor Rival(0.67f, 0.13f, 0.055f);
	const FLinearColor Gold(0.76f, 0.47f, 0.10f);

	template <class T>
	T* Art(const TCHAR* Folder, const TCHAR* Name)
	{
		return LoadObject<T>(nullptr, *FString::Printf(TEXT("/Game/Yell/Art/%s/%s.%s"), Folder, Name, Name));
	}

	AStaticMeshActor* Scenery(UWorld* World, const TCHAR* Name, const FVector& Ground, const FVector& Size,
		float Yaw, const TCHAR* Surface)
	{
		UStaticMesh* Mesh = Art<UStaticMesh>(TEXT("Models/Static"), Name);
		if (!Mesh) return nullptr;
		auto* Actor = World->SpawnActor<AStaticMeshActor>(Ground, FRotator(0, Yaw, 0));
		auto* Component = Actor->GetStaticMeshComponent();
		Component->SetMobility(EComponentMobility::Movable);
		Component->SetStaticMesh(Mesh);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetCanEverAffectNavigation(false);
		const FBoxSphereBounds Bounds = Mesh->GetBounds();
		const FVector Scale = Size / (Bounds.BoxExtent * 2.).ComponentMax(FVector(1.));
		Actor->SetActorScale3D(Scale);
		const FVector LocalBase(Bounds.Origin.X, Bounds.Origin.Y, Bounds.Origin.Z - Bounds.BoxExtent.Z);
		Actor->SetActorLocation(Ground - Actor->GetActorRotation().RotateVector(LocalBase * Scale));
		if (auto* Material = Art<UMaterialInterface>(TEXT("Materials/Instances/Tileable"), Surface))
			for (int32 Slot = 0; Slot < Component->GetNumMaterials(); ++Slot) Component->SetMaterial(Slot, Material);
		return Actor;
	}
}

AYellNavigationBounds::AYellNavigationBounds(const FObjectInitializer& Initializer) : Super(Initializer)
{
	UBoxComponent* Bounds = CreateDefaultSubobject<UBoxComponent>(TEXT("ArenaNavigationBox"));
	Bounds->SetupAttachment(GetRootComponent());
	Bounds->SetBoxExtent(FVector(Extent.X, Extent.Y, 385));
	Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Bounds->SetCanEverAffectNavigation(false);
}

FVector AYellBattle::Position(const EYellZone Zone, const uint8 Team) const
{
	switch (Zone)
	{
	case EYellZone::Left: return FVector(0, -LaneSpacing, 12);
	case EYellZone::Right: return FVector(0, LaneSpacing, 12);
	case EYellZone::Home: return FVector(Team == 0 ? -5800 : 5800, 0, 12);
	case EYellZone::Rival: return FVector(Team == 0 ? 6150 : -6150, 0, 12);
	default: return FVector(0, 0, 12);
	}
}

FVector AYellBattle::SpawnPosition(const uint8 Team) const
{
	return FVector(Team == 0 ? -6230 : 6230, -510, 104);
}

FVector AYellBattle::CorePosition(const uint8 Team) const
{
	return FVector(Team == 0 ? -BaseX : BaseX, 0, 150);
}

EYellZone AYellBattle::LaneOf(const FVector& Location) const
{
	return Location.Y < -LaneSpacing * 0.5 ? EYellZone::Left
		: Location.Y > LaneSpacing * 0.5 ? EYellZone::Right : EYellZone::Center;
}

bool AYellBattle::IsTerminalNearby(const uint8 Team, const FVector& Location) const
{
	return FVector::Dist2D(Location, TerminalPosition(Team)) <= 440;
}

FVector AYellBattle::TerminalPosition(const uint8 Team) const
{
	return FVector(Team == 0 ? -6250 : 6250, -810, 60);
}

FVector2D AYellBattle::ArenaExtent()
{
	return Extent;
}

void AYellBattle::CacheWalkableTerrain(ANavigationData* Data)
{
	const auto* Mesh = Cast<ARecastNavMesh>(Data);
	if (!Mesh) return;
	NavTriangles.Reset();
	TArray<FNavTileRef> Tiles;
	Mesh->GetAllNavMeshTiles(Tiles);
	TArray<FNavPoly> Polys;
	TArray<FVector> Vertices;
	for (const FNavTileRef Tile : Tiles)
	{
		Polys.Reset();
		if (!Mesh->GetPolysInTile(Tile, Polys)) continue;
		for (const FNavPoly& Poly : Polys)
		{
			Vertices.Reset();
			if (!Mesh->GetPolyVerts(Poly.Ref, Vertices)) continue;
			for (int32 Index = 2; Index < Vertices.Num(); ++Index)
			{
				NavTriangles.Add(Vertices[0]);
				NavTriangles.Add(Vertices[Index-1]);
				NavTriangles.Add(Vertices[Index]);
			}
		}
	}
}

void AYellBattle::UpdateCoreAppearance(const uint8 Team)
{
	const int32 State = BaseHealth[Team] <= 0 ? 2 : BaseHealth[Team] <= 250 ? 1 : 0;
	for (int32 Index = 0; Index < 3; ++Index)
		if (auto* Model = Bunkers[Team][Index].Get()) Model->SetActorHiddenInGame(Index != State);
}

AStaticMeshActor* AYellBattle::Block(const FVector& Location, const FVector& Size,
	const FLinearColor& Tint, const bool bCollision, const bool bRound)
{
	static const TCHAR* CubePath = TEXT("/Engine/BasicShapes/Cube.Cube");
	static const TCHAR* CylinderPath = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
	AStaticMeshActor* Actor = GetWorld()->SpawnActor<AStaticMeshActor>(Location, FRotator::ZeroRotator);
	UStaticMeshComponent* Mesh = Actor->GetStaticMeshComponent();
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, bRound ? CylinderPath : CubePath));
	Actor->SetActorScale3D(Size / 100.0);
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/LevelPrototyping/Materials/M_FlatCol.M_FlatCol")))
	{
		UMaterialInstanceDynamic* Material = Mesh->CreateDynamicMaterialInstance(0, Base);
		Material->SetVectorParameterValue(TEXT("Color"), Tint);
		Material->SetVectorParameterValue(TEXT("BaseColor"), Tint);
		Material->SetVectorParameterValue(TEXT("Base Color"), Tint);
	}
	if (!bCollision)
	{
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetCanEverAffectNavigation(false);
	}
	return Actor;
}

void AYellBattle::Sign(const FVector& Location, const FString& Text, const FColor& Color, const float Size, const float Yaw)
{
	ATextRenderActor* Actor = GetWorld()->SpawnActor<ATextRenderActor>(Location, FRotator(0, Yaw, 0));
	UTextRenderComponent* Label = Actor->GetTextRender();
	Label->SetText(FText::FromString(Text));
	Label->SetTextRenderColor(Color);
	Label->SetHorizontalAlignment(EHTA_Center);
	Label->SetWorldSize(Size);
}

void AYellBattle::BuildArena()
{
	ADirectionalLight* Sun = GetWorld()->SpawnActor<ADirectionalLight>(FVector(0, 0, 900),
		FRotator(-57, -34, 0));
	Sun->GetLightComponent()->SetMobility(EComponentMobility::Movable);
	Sun->GetLightComponent()->SetIntensity(5.0f);
	Sun->GetComponent()->SetAtmosphereSunLight(true);
	GetWorld()->SpawnActor<ASkyAtmosphere>();
	ASkyLight* Sky = GetWorld()->SpawnActor<ASkyLight>();
	Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
	Sky->GetLightComponent()->SetIntensity(0.9f);
	Sky->GetLightComponent()->SetRealTimeCaptureEnabled(true);

	auto Surface = [](AStaticMeshActor* Actor, const TCHAR* Name)
	{
		if (auto* Material = Art<UMaterialInterface>(TEXT("Materials/Instances/Tileable"), Name))
			Actor->GetStaticMeshComponent()->SetMaterial(0, Material);
	};
	Surface(Block(FVector(0, 0, -90), FVector(Extent.X*2, Extent.Y*2, 180), Turf), TEXT("MI_Suelo_Arena"));
	if (auto* Terrain = Art<UStaticMesh>(TEXT("Models/Terrain"), TEXT("SM_Terreno_ValleAlfa")))
	{
		auto* Hills = GetWorld()->SpawnActor<AStaticMeshActor>();
		auto* Mesh = Hills->GetStaticMeshComponent();
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetStaticMesh(Terrain);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetCanEverAffectNavigation(false);
		const FVector Half = Terrain->GetBounds().BoxExtent;
		Hills->SetActorScale3D(FVector(23000 / FMath::Max(1., Half.X), 19800 / FMath::Max(1., Half.Y), 1.5));
		Hills->SetActorLocation(FVector(0,0,-40));
		if (auto* Material = Art<UMaterialInterface>(TEXT("Materials/Instances/Terrain"), TEXT("MI_Terreno_ValleAlfa")))
			Mesh->SetMaterial(0, Material);
	}
	for (const double Side : {-1.0, 1.0})
	{
		Surface(Block(FVector(0, Side * 3820, 140), FVector(15300, 140, 280), Wall), TEXT("MI_Roca"));
		Surface(Block(FVector(Side * 7610, 0, 140), FVector(140, 7600, 280), Wall), TEXT("MI_Roca"));
		Surface(Block(FVector(Side * 5890, 0, 2), FVector(1450, 6600, 4), Road, false), TEXT("MI_Camino_Arena"));
		for (int32 Index = -4; Index <= 4; ++Index)
			Scenery(GetWorld(), TEXT("SM_Rocas_PuertaNorte_Muro"), FVector(Index * 1770, Side * 3930, -70),
				FVector(1850, 470, 560 + (Index + 4) % 3 * 110), 0, TEXT("MI_Roca"));
	}
	for (int32 Lane = -1; Lane <= 1; ++Lane)
	{
		const double Y = Lane * LaneSpacing;
		Surface(Block(FVector(0, Y, 1), FVector(14300, 850, 2), Road, false), TEXT("MI_Camino_Arena"));
		for (const double Side : {-1.0, 1.0})
		{
			const FVector Trench(Side*3220, Y + Side*580, 0);
			if (Scenery(GetWorld(), TEXT("SM_Trinchera_Recta_4m"), Trench, FVector(510, 510, 146), 0, TEXT("MI_Tierra")))
			{
				for (const double Edge : {-1., 1.})
					Block(Trench + FVector(0, Edge*195, 47), FVector(470,55,94), Wall)->SetActorHiddenInGame(true);
			}
		}
		const FString Name = Lane < 0 ? TEXT("IZQUIERDA") : Lane > 0 ? TEXT("DERECHA") : TEXT("CENTRO");
		Sign(FVector(-3750, Y + 620, 225), Name, Gold.ToFColorSRGB(), 54);
		for (int32 Index = -3; Index <= 3; ++Index)
		{
			const FVector Center(Index * 1220., Y + (Index % 2 == 0 ? -340 : 355), 0);
			const bool bRidge = FMath::Abs(Index) <= 1;
			const FVector Size = bRidge ? FVector(640, 1030, 430) : FVector(205, 290, 92);
			auto* Collider = Block(Center + FVector(0,0,Size.Z*.5), Size*.88, Wall);
			if (Scenery(GetWorld(), bRidge ? TEXT("SM_Rocas_PuertaNorte_02") : TEXT("SM_Sacos_Muro_2m_Alto"),
				Center, Size, 0, bRidge ? TEXT("MI_Roca") : TEXT("MI_Saco")))
				Collider->SetActorHiddenInGame(true);
			CoverPositions.Add(Center + FVector(-Size.X*.5 - 95, 0, 10));
			CoverPositions.Add(Center + FVector(Size.X*.5 + 95, 0, 10));
		}
	}
	for (const double Y : {-1125.0, 1125.0})
	{
		auto* Ridge = Block(FVector(-2230, Y, 190), FVector(1870, 330, 380), Wall);
		if (Scenery(GetWorld(), TEXT("SM_Rocas_PuertaNorte_Muro"), FVector(-2230,Y,0),
			FVector(1950,390,440), 0, TEXT("MI_Roca"))) Ridge->SetActorHiddenInGame(true);
	}
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		const FLinearColor Tint = Team == 0 ? Friendly : Rival;
		const double SignX = Team == 0 ? -1.0 : 1.0;
		const FVector Core = CorePosition(Team);
		Surface(Block(Core - FVector(0, 0, 117), FVector(600, 700, 66), Wall), TEXT("MI_Concreto"));
		Cores[Team] = Block(Core, FVector(360, 470, 220), Tint);
		const FVector BunkerBase = Core + FVector(SignX * 455, 0, -150);
		const TCHAR* States[] = {TEXT("SM_Bunker_Enemigo_Intacto"), TEXT("SM_Bunker_Enemigo_Danado"), TEXT("SM_Bunker_Enemigo_Destruido")};
		for (int32 Index = 0; Index < 3; ++Index)
			Bunkers[Team][Index] = Scenery(GetWorld(), States[Index], BunkerBase,
				FVector(840, 1000, Index == 2 ? 276 : 515), Team == 0 ? -90 : 90, TEXT("MI_Concreto"));
		if (Bunkers[Team][0].IsValid())
			Block(BunkerBase + FVector(SignX*175,0,180), FVector(510,710,360), Wall)->SetActorHiddenInGame(true);
		UpdateCoreAppearance(Team);
		Sign(Core + FVector(-SignX * 250, 0, 205), Team == 0 ? TEXT("BASE ALIADA") : TEXT("BASE RIVAL"),
			Tint.ToFColorSRGB(), 55, Team == 0 ? 0 : 180);
		const FVector Terminal = TerminalPosition(Team);
		Block(Terminal, FVector(95, 135, 120), Tint);
		Block(Terminal + FVector(0,0,68), FVector(110,145,18), Gold, false);
		Sign(Terminal + FVector(60,0,137), TEXT("REFUERZOS"), Gold.ToFColorSRGB(), 33, 0);
	}
	AYellNavigationBounds* Bounds = GetWorld()->SpawnActor<AYellNavigationBounds>(FVector(0, 0, 100),
		FRotator::ZeroRotator);
	if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		Nav->OnNavigationBoundsUpdated(Bounds);
		Nav->Build();
	}
}

#include "YellBattle.h"

#include "Components/BoxComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PointLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextRenderActor.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "NavigationSystem.h"
#include "NavMesh/RecastNavMesh.h"

namespace
{
	constexpr double BaseX = 13300.;
	constexpr double LaneSpacing = 4500.;
	constexpr double RoadHalfWidth = 570.;
	constexpr double CampJunction = 11100.;
	constexpr double InteriorJunction = 5600.;
	constexpr double CenterRoadEnd = BaseX - 440.;
	const FVector2D Extent(15400, 7800);
	const FLinearColor Turf(0.10f, 0.15f, 0.13f);
	const FLinearColor Road(0.25f, 0.26f, 0.25f);
	const FLinearColor Wall(0.34f, 0.40f, 0.41f);
	const FLinearColor Friendly(0.05f, 0.48f, 0.60f);
	const FLinearColor Rival(0.67f, 0.13f, 0.055f);

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

	UStaticMeshComponent* CampProp(UWorld* World, const TCHAR* Name, const FVector& Ground, float Yaw, bool bCollision = true)
	{
		auto* Mesh = Art<UStaticMesh>(TEXT("Models/Props"), Name);
		if (!Mesh) return nullptr;
		auto* Actor = World->SpawnActor<AStaticMeshActor>(Ground, FRotator(0, Yaw, 0));
		Actor->Tags.Add(FName(Name));
		auto* Component = Actor->GetStaticMeshComponent();
		Component->SetMobility(EComponentMobility::Movable);
		Component->SetCollisionProfileName(bCollision ? TEXT("BlockAll") : TEXT("NoCollision"));
		Component->SetCanEverAffectNavigation(bCollision);
		Component->SetStaticMesh(Mesh);
		return Component;
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
	case EYellZone::Home: return FVector((Team == 0 ? -1. : 1.) * (BaseX - 850.), 0, 12);
	case EYellZone::Rival: return FVector((Team == 0 ? 1. : -1.) * (BaseX - 500.), 0, 12);
	default: return FVector(0, 0, 12);
	}
}

FVector AYellBattle::SpawnPosition(const uint8 Team) const
{
	return FVector((Team == 0 ? -1. : 1.) * (BaseX - 420.), -510, 104);
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
	return FVector((Team == 0 ? -1. : 1.) * (BaseX - 830.), -970, 0);
}

FVector AYellBattle::RivalApproach(const EYellZone Lane) const
{
	return FVector(-CampJunction, Position(Lane, 1).Y, 12);
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

void AYellBattle::UpdateTerminalAppearance(const uint8 Team)
{
	auto* Display = TerminalDisplays[Team].Get();
	if (!Display) return;
	const uint8 State = WinningTeam != INDEX_NONE ? 2 : NextReinforcement(Team) > 0.f ? 1 : 0;
	if (State == TerminalState[Team]) return;
	const TCHAR* Screens[] = {TEXT("T_Terminal_Pantalla_Activa"), TEXT("T_Terminal_Pantalla_Alerta"), TEXT("T_Terminal_Pantalla_Apagada")};
	if (auto* Texture = Art<UTexture2D>(TEXT("Textures/Props"), Screens[State]))
	{
		Display->SetTextureParameterValue(TEXT("Pantalla"), Texture);
		TerminalState[Team] = State;
	}
}

void AYellBattle::BuildCampProps(const uint8 Team)
{
	const double Side = Team == 0 ? -1. : 1.;
	const double Front = Team == 0 ? 0. : 180.;
	auto Place = [this, Side, Front](const TCHAR* Name, double Depth, double Y, double Yaw = 0.)
	{
		return CampProp(GetWorld(), Name, FVector(Side * (BaseX + Depth), Y, 0), Front + Yaw);
	};
	if (auto* Terminal = CampProp(GetWorld(), TEXT("SM_Terminal_Refuerzos"), TerminalPosition(Team), Team == 0 ? 45.f : -45.f))
	{
		for (int32 Slot = 0; Slot < Terminal->GetNumMaterials(); ++Slot)
		{
			const auto* Material = Terminal->GetMaterial(Slot);
			if (Material && Material->GetFName() == TEXT("M_Valle_Terminal"))
			{
				TerminalDisplays[Team] = Terminal->CreateDynamicMaterialInstance(Slot);
				UpdateTerminalAppearance(Team);
				break;
			}
		}
	}
	Place(TEXT("SM_Tienda_Militar"), 270, 1470, 10.);
	Place(TEXT("SM_Tienda_Militar"), -340, 2220, -15.);
	Place(TEXT("SM_Mastil_Radio"), 720, -1240);
	Place(TEXT("SM_Cajas_Municion_Pila"), -700, 1670, 22.);
	Place(TEXT("SM_Cajas_Municion_Pila"), 370, -1650, -34.);
	Place(TEXT("SM_Barril_Combustible"), -505, 1870);
	Place(TEXT("SM_Barril_Combustible"), -575, 1933);
	Place(TEXT("SM_Barril_Combustible"), 290, -1645);
	for (double Y : {-1850., -1440., -1030., 1050., 1460., 1870., 2280., 2690.})
		Place(TEXT("SM_Alambrada_4m"), 1350, Y, 90.);
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
		bMenuScene ? FRotator(-16, 32, 0) : FRotator(-57, -34, 0));
	Sun->GetLightComponent()->SetMobility(EComponentMobility::Movable);
	Sun->GetLightComponent()->SetIntensity(bMenuScene ? 3.2f : 5.f);
	if (bMenuScene) Sun->GetLightComponent()->SetLightColor(FLinearColor(1.0f, .76f, .53f));
	Sun->GetComponent()->SetAtmosphereSunLight(true);
	GetWorld()->SpawnActor<ASkyAtmosphere>();
	ASkyLight* Sky = GetWorld()->SpawnActor<ASkyLight>();
	Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
	Sky->GetLightComponent()->SetIntensity(bMenuScene ? .6f : .9f);
	Sky->GetLightComponent()->SetRealTimeCaptureEnabled(true);
	if (!bMenuScene)
	{
		auto* Haze = GetWorld()->SpawnActor<AExponentialHeightFog>(FVector(0, 0, 80), FRotator::ZeroRotator);
		auto* Fog = Haze->GetComponent();
		Fog->SetFogDensity(.022f);
		Fog->SetFogHeightFalloff(.55f);
		Fog->SetStartDistance(3400.f);
		Fog->SetFogMaxOpacity(.86f);
		Fog->SetFogInscatteringColor(FLinearColor(.22f, .27f, .28f));
	}

	auto Surface = [](AStaticMeshActor* Actor, const TCHAR* Name)
	{
		if (auto* Material = Art<UMaterialInterface>(TEXT("Materials/Instances/Tileable"), Name))
			Actor->GetStaticMeshComponent()->SetMaterial(0, Material);
	};
	auto* Dirt = Art<UMaterialInterface>(TEXT("Materials/Props"), TEXT("M_Valle_Suelo"));
	auto* Floor = Block(FVector(0, 0, -90), FVector(Extent.X * 2, Extent.Y * 2, 180), Turf);
	auto* FloorMaterial = Dirt ? Floor->GetStaticMeshComponent()->CreateDynamicMaterialInstance(0, Dirt) : nullptr;
	if (FloorMaterial)
	{
		FloorMaterial->SetVectorParameterValue(TEXT("Vias"), FLinearColor(
			static_cast<float>(LaneSpacing), static_cast<float>(RoadHalfWidth),
			static_cast<float>(CampJunction), static_cast<float>(CenterRoadEnd)));
		FloorMaterial->SetScalarParameterValue(TEXT("CruceInterior"), static_cast<float>(InteriorJunction));
	}
	else Surface(Floor, TEXT("MI_Suelo_Arena"));
	if (auto* Terrain = Art<UStaticMesh>(TEXT("Models/Terrain"), TEXT("SM_Terreno_ValleAlfa")))
	{
		auto* Hills = GetWorld()->SpawnActor<AStaticMeshActor>();
		auto* Mesh = Hills->GetStaticMeshComponent();
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetStaticMesh(Terrain);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Mesh->SetCanEverAffectNavigation(false);
		const FVector Half = Terrain->GetBounds().BoxExtent;
		Hills->SetActorScale3D(FVector(Extent.X * 3. / FMath::Max(1., Half.X),
			Extent.Y * 5.1 / FMath::Max(1., Half.Y), 1.85));
		Hills->SetActorLocation(FVector(0,0,-40));
		if (auto* Material = Art<UMaterialInterface>(TEXT("Materials/Instances/Terrain"), TEXT("MI_Terreno_ValleAlfa")))
			Mesh->SetMaterial(0, Material);
	}
	auto AddRoad = [this, &Surface, FloorMaterial](const FVector2D& Min, const FVector2D& Max)
	{
		Roads.Emplace(Min, Max);
		if (!FloorMaterial)
		{
			auto* Actor = Block(FVector((Min + Max) * .5, 1.5), FVector(Max - Min, 3), Road, false);
			Actor->GetStaticMeshComponent()->SetCastShadow(false);
			Surface(Actor, TEXT("MI_Camino_Arena"));
		}
	};
	for (const double Y : {-LaneSpacing, 0., LaneSpacing})
	{
		const double HalfLength = Y == 0. ? CenterRoadEnd : CampJunction + RoadHalfWidth;
		AddRoad(FVector2D(-HalfLength, Y - RoadHalfWidth), FVector2D(HalfLength, Y + RoadHalfWidth));
	}
	for (const double X : {-CampJunction, -InteriorJunction, 0., InteriorJunction, CampJunction})
	{
		AddRoad(FVector2D(X - RoadHalfWidth, -LaneSpacing + RoadHalfWidth),
			FVector2D(X + RoadHalfWidth, -RoadHalfWidth));
		AddRoad(FVector2D(X - RoadHalfWidth, RoadHalfWidth),
			FVector2D(X + RoadHalfWidth, LaneSpacing - RoadHalfWidth));
	}
	auto AddCover = [this](const TCHAR* Asset, const TCHAR* SurfaceName, const FVector& Center, const FVector& Size, float Yaw = 0.f)
	{
		const FRotator Rotation(0, Yaw, 0);
		auto* Collider = Block(Center + FVector(0, 0, Size.Z * .42), Size * .82, Wall);
		Collider->SetActorRotation(Rotation);
		if (Scenery(GetWorld(), Asset, Center, Size, Yaw, SurfaceName)) Collider->SetActorHiddenInGame(true);
		const FVector Offset = Rotation.RotateVector(FVector(0, Size.Y * .5 + 115., 10.));
		CoverPositions.Add(Center + Offset);
		CoverPositions.Add(Center - FVector(Offset.X, Offset.Y, -10.));
	};
	for (const double Side : {-1., 1.})
	{
		Block(FVector(0, Side * (Extent.Y - 80.), 175), FVector(Extent.X * 2, 150, 350), Wall)->SetActorHiddenInGame(true);
		Block(FVector(Side * (Extent.X - 80.), 0, 175), FVector(150, Extent.Y * 2, 350), Wall)->SetActorHiddenInGame(true);
		for (int32 Index = -8; Index <= 8; ++Index)
		{
			Scenery(GetWorld(), Index % 3 ? TEXT("SM_Rocas_PuertaNorte_Muro") : TEXT("SM_Rocas_PuertaNorte_03"),
				FVector(Index * 1850., Side * (Extent.Y + (Index % 3) * 210.), -50.),
				FVector(2140., 630., 720. + FMath::Abs(Index % 4) * 150.), Index % 2 ? 12.f : -7.f, TEXT("MI_Roca"));
		}
		for (int32 Index = -4; Index <= 4; ++Index)
			Scenery(GetWorld(), TEXT("SM_Rocas_PuertaNorte_Muro"), FVector(Side * Extent.X, Index * 1680., -60.),
				FVector(610., 2030., 625. + FMath::Abs(Index % 3) * 150.), 0, TEXT("MI_Roca"));

		for (const double X : {-8800., -3050., 2670., 8340.})
		{
			const double Y = Side * (X < 0. ? 2230. : 2610.);
			AddCover(TEXT("SM_Rocas_PuertaNorte_Muro"), TEXT("MI_Roca"),
				FVector(X, Y, 0), FVector(1640, 1020, 520), Side * 14.f);
			AddCover(TEXT("SM_Rocas_PuertaNorte_02"), TEXT("MI_Roca"),
				FVector(X + 630., Side * 6610., 0), FVector(1170, 850, 490), Side * 25.f);
			AddCover(TEXT("SM_Sacos_Muro_2m_Alto"), TEXT("MI_Saco"),
				FVector(X - 330., Side * (LaneSpacing + 1170.), 0), FVector(390, 110, 115), Side * 36.f);
		}
		for (const double X : {-7500., 7500.})
		{
			const double Y = Side * (LaneSpacing - 1280.);
			const FVector Trench(X, Y, 0);
			if (Scenery(GetWorld(), TEXT("SM_Trinchera_Recta_4m"), Trench, FVector(520, 520, 148), 0, TEXT("MI_Tierra")))
				for (const double Edge : {-1., 1.})
					Block(Trench + FVector(0, Edge * 195., 48), FVector(475, 60, 96), Wall)->SetActorHiddenInGame(true);

			CampProp(GetWorld(), TEXT("SM_Tienda_Militar"), FVector(X - 370., Side * 5900., 0), X < 0. ? 16.f : 155.f);
			CampProp(GetWorld(), TEXT("SM_Cajas_Municion_Pila"), FVector(X + 80., Side * 5920., 0), Side * 21.f);
			CampProp(GetWorld(), TEXT("SM_Barril_Combustible"), FVector(X + 160., Side * 5940., 0), 0.f);
		}
	}
	for (uint8 Team = 0; !bMenuScene && Team < 2; ++Team)
	{
		const FLinearColor Tint = Team == 0 ? Friendly : Rival;
		const double SignX = Team == 0 ? -1.0 : 1.0;
		const FVector Core = CorePosition(Team);
		Surface(Block(Core - FVector(0, 0, 117), FVector(600, 700, 66), Wall), TEXT("MI_Concreto"));
		Cores[Team] = Block(Core, FVector(360, 470, 220), Tint);
		Surface(Cores[Team].Get(), TEXT("MI_Metal"));
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
		BuildCampProps(Team);
	}
	AYellNavigationBounds* Bounds = GetWorld()->SpawnActor<AYellNavigationBounds>(FVector(0, 0, 100),
		FRotator::ZeroRotator);
	if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		Nav->OnNavigationBoundsUpdated(Bounds);
		Nav->Build();
	}
}

void AYellBattle::BuildMenuScene()
{
	const FVector CampOffset(6650. - BaseX, 0, 0);
	auto* Camera = GetWorld()->SpawnActor<ACameraActor>(CampOffset + FVector(-6990, -1650, 194), FRotator(-4, 29, 0));
	if (Camera)
	{
		auto* Lens = Camera->GetCameraComponent();
		Lens->SetFieldOfView(61.f);
		auto& Grade = Lens->PostProcessSettings;
		Grade.bOverride_ColorSaturation = true;
		Grade.ColorSaturation = FVector4(.75, .81, .88, 1.);
		Grade.bOverride_AutoExposureBias = true;
		Grade.AutoExposureBias = -.55f;
		Grade.bOverride_VignetteIntensity = true;
		Grade.VignetteIntensity = .52f;
	}
	MenuCamera = Camera;
	if (auto* Haze = GetWorld()->SpawnActor<AExponentialHeightFog>(FVector(0, 0, 90), FRotator::ZeroRotator))
	{
		auto* Fog = Haze->GetComponent();
		Fog->SetFogDensity(.036f);
		Fog->SetFogHeightFalloff(.72f);
		Fog->SetFogInscatteringColor(FLinearColor(.09f, .125f, .14f));
		Fog->SetStartDistance(450.f);
		Fog->SetFogMaxOpacity(.72f);
	}

	auto* Operator = GetWorld()->SpawnActor<AYellSoldier>(CampOffset + FVector(-6560, -1230, 88), FRotator(0, 218, 0));
	if (Operator)
	{
		Operator->Initialize(0, TEXT("Alfa"), 0, false);
		Operator->EquipMenuRadio();
		MenuOperator = Operator;
		AllUnits.Add(Operator);
	}
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FVector Start = CampOffset + FVector(-6190 - Index * 119, -930 + Index * 182, 88);
		if (auto* Soldier = GetWorld()->SpawnActor<AYellSoldier>(Start, FRotator::ZeroRotator))
		{
			Soldier->Initialize(0, TEXT("Bravo"), Index, false);
			FYellOrder Patrol;
			Patrol.Action = EYellAction::Patrol;
			Soldier->Accept(Patrol, Start + FVector(1270, 180, -75), Start - FVector(0, 0, 75));
			AllUnits.Add(Soldier);
		}
	}
	Scenery(GetWorld(), TEXT("SM_Sacos_Muro_2m_Alto"), CampOffset + FVector(-6660, -925, 0),
		FVector(280, 55, 82), -26, TEXT("MI_Saco"));
	Scenery(GetWorld(), TEXT("SM_Bunker_Enemigo_Intacto"), CampOffset + FVector(-5280, 410, 0),
		FVector(770, 760, 420), -65, TEXT("MI_Concreto"));
	Scenery(GetWorld(), TEXT("SM_Sacos_Muro_2m_Bajo"), CampOffset + FVector(-5550, -470, 0),
		FVector(420, 60, 58), -24, TEXT("MI_Saco"));
	CampProp(GetWorld(), TEXT("SM_Cajas_Municion_Pila"), CampOffset + FVector(-6565, -825, 0), -26.f, false);
	CampProp(GetWorld(), TEXT("SM_Barril_Combustible"), CampOffset + FVector(-6440, -770, 0), 22.f, false);
	CampProp(GetWorld(), TEXT("SM_Mastil_Radio"), CampOffset + FVector(-5480, 147, 0), 0.f, false);
	CampProp(GetWorld(), TEXT("SM_Tienda_Militar"), CampOffset + FVector(-4770, -430, 0), 20.f, false);
	if (auto* Lamp = GetWorld()->SpawnActor<APointLight>(CampOffset + FVector(-5710, -250, 290), FRotator::ZeroRotator))
	{
		auto* Light = Lamp->PointLightComponent.Get();
		Light->SetMobility(EComponentMobility::Movable);
		Light->SetLightColor(FLinearColor(1.f, .54f, .24f));
		Light->SetIntensity(1750.f);
		Light->SetAttenuationRadius(530.f);
		Light->SetCastShadows(false);
	}
}

void AYellBattle::UpdateMenuScene()
{
	const double Now = GetWorld()->GetTimeSeconds();
	for (const auto& Soldier : AllUnits)
		if (Soldier.IsValid() && Soldier != MenuOperator) Soldier->Step(*this, Now);
	if (Now < NextMenuRadio || !GetWorld()->GetAudioDeviceRaw() || !MenuOperator.IsValid()) return;
	NextMenuRadio = Now + 18.;
	const FVector Source = MenuOperator->GetActorLocation();
	PlayEffect(TEXT("RadioEnvio"), Source, .45f);
	if (auto* Voice = LoadObject<USoundBase>(nullptr, TEXT("/Game/Yell/Audio/RadioPatrulla.RadioPatrulla")))
		UGameplayStatics::PlaySoundAtLocation(this, Voice, Source, .28f);
}

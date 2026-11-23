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
#include "Engine/TextRenderActor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NavigationSystem.h"

namespace
{
	constexpr double BaseX = 3450.0;
	constexpr double LaneSpacing = 1440.0;
	const FLinearColor Turf(0.10f, 0.15f, 0.13f);
	const FLinearColor Road(0.25f, 0.26f, 0.25f);
	const FLinearColor Wall(0.34f, 0.40f, 0.41f);
	const FLinearColor Friendly(0.05f, 0.48f, 0.60f);
	const FLinearColor Rival(0.67f, 0.13f, 0.055f);
	const FLinearColor Gold(0.76f, 0.47f, 0.10f);
}

AYellNavigationBounds::AYellNavigationBounds(const FObjectInitializer& Initializer) : Super(Initializer)
{
	UBoxComponent* Bounds = CreateDefaultSubobject<UBoxComponent>(TEXT("ArenaNavigationBox"));
	Bounds->SetupAttachment(GetRootComponent());
	Bounds->SetBoxExtent(FVector(4100, 2460, 300));
	Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Bounds->SetCanEverAffectNavigation(false);
}

FVector AYellBattle::Position(const EYellZone Zone, const uint8 Team) const
{
	switch (Zone)
	{
	case EYellZone::Left: return FVector(0, -LaneSpacing, 12);
	case EYellZone::Right: return FVector(0, LaneSpacing, 12);
	case EYellZone::Home: return FVector(Team == 0 ? -2800 : 2800, 0, 12);
	case EYellZone::Rival: return FVector(Team == 0 ? 2980 : -2980, 0, 12);
	default: return FVector(0, 0, 12);
	}
}

FVector AYellBattle::SpawnPosition(const uint8 Team) const
{
	return FVector(Team == 0 ? -3100 : 3100, -510, 104);
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
	return FVector::Dist2D(Location, FVector(Team == 0 ? -3040 : 3040, -700, 0)) <= 440;
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

	Block(FVector(0, 0, -90), FVector(8500, 4950, 180), Turf);
	for (const double Side : {-1.0, 1.0})
	{
		Block(FVector(0, Side * 2420, 140), FVector(8420, 100, 280), Wall);
		Block(FVector(Side * 4150, 0, 140), FVector(100, 4810, 280), Wall);
		Block(FVector(Side * 2900, 0, 2), FVector(1220, 4770, 4), Road, false);
		Block(FVector(Side * 980, 0, 2), FVector(250, 4600, 4), Road, false);
	}
	for (int32 Lane = -1; Lane <= 1; ++Lane)
	{
		const double Y = Lane * LaneSpacing;
		Block(FVector(0, Y, 2), FVector(7900, 765, 4), Road, false);
		for (const double Side : {-1.0, 1.0})
		{
			Block(FVector(0, Y + Side * 400, 4), FVector(7900, 22, 5), Gold, false);
			Block(FVector(-1420, Y + Side * 430, 60), FVector(105, 152, 120), Wall);
			Block(FVector(1420, Y + Side * 430, 60), FVector(105, 152, 120), Wall);
		}
		const FString Name = Lane < 0 ? TEXT("IZQUIERDA") : Lane > 0 ? TEXT("DERECHA") : TEXT("CENTRO");
		Sign(FVector(-1490, Y, 235), Name, Gold.ToFColorSRGB(), 65);
		for (int32 Index = 0; Index < 5; ++Index)
		{
			const FVector Center((Index - 2) * 520.0, Y + (Index % 2 == 0 ? -280 : 280), 79);
			Block(Center, FVector(175, 235, 158), Wall);
			CoverPositions.Add(FVector(Center.X - 155, Center.Y, 10));
			CoverPositions.Add(FVector(Center.X + 155, Center.Y, 10));
		}
	}
	for (const double Y : {-720.0, 720.0})
	{
		Block(FVector(0, Y, 160), FVector(1360, 206, 320), Wall);
		Block(FVector(0, Y, 320), FVector(1450, 250, 35), Gold, false);
	}
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		const FLinearColor Tint = Team == 0 ? Friendly : Rival;
		const double SignX = Team == 0 ? -1.0 : 1.0;
		const FVector Core = CorePosition(Team);
		Block(Core - FVector(0, 0, 117), FVector(600, 700, 66), Wall);
		Cores[Team] = Block(Core, FVector(360, 470, 220), Tint);
		Block(Core + FVector(0, 0, 130), FVector(330, 440, 38), Gold, false);
		Block(Core + FVector(0, 0, 220), FVector(42, 42, 170), Tint, false, true);
		Sign(Core + FVector(-SignX * 250, 0, 205), Team == 0 ? TEXT("BASE ALIADA") : TEXT("BASE RIVAL"),
			Tint.ToFColorSRGB(), 55, Team == 0 ? 0 : 180);
		Block(FVector(SignX * 3040, -700, 60), FVector(95, 135, 120), Tint);
		Block(FVector(SignX * 3040, -700, 128), FVector(110, 145, 18), Gold, false);
		Sign(FVector(SignX * 3040 + 60, -700, 197), TEXT("REFUERZOS"), Gold.ToFColorSRGB(), 33, 0);
	}
	AYellNavigationBounds* Bounds = GetWorld()->SpawnActor<AYellNavigationBounds>(FVector(0, 0, 100),
		FRotator::ZeroRotator);
	if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		Nav->OnNavigationBoundsUpdated(Bounds);
		Nav->Build();
	}
}

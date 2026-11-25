#include "YellRoundVisual.h"

#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

AYellRoundVisual::AYellRoundVisual()
{
	PrimaryActorTick.bCanEverTick = true;
	RoundMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Round"));
	SetRootComponent(RoundMesh);
	RoundMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RoundMesh->SetCanEverAffectNavigation(false);
	RoundMesh->SetCastShadow(false);
	const ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (Shape.Succeeded()) RoundMesh->SetStaticMesh(Shape.Object);
	RoundMesh->SetRelativeScale3D(FVector(.12, .035, .035));
}

void AYellRoundVisual::TravelTo(const FVector& Impact)
{
	Destination = Impact;
	SetActorRotation((Impact - GetActorLocation()).Rotation());
	if (auto* Material = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/LevelPrototyping/Materials/M_FlatCol.M_FlatCol")))
		if (auto* Instance = RoundMesh->CreateDynamicMaterialInstance(0, Material))
			Instance->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f,.66f,.17f));
	SetLifeSpan(.4f);
}

void AYellRoundVisual::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const FVector Delta = Destination - GetActorLocation();
	const double Step = 12500. * DeltaSeconds;
	if (Delta.SizeSquared() <= FMath::Square(Step))
	{
		Destroy();
		return;
	}
	AddActorWorldOffset(Delta.GetSafeNormal() * Step);
}

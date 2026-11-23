#include "YellBattle.h"

#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"

namespace
{
	const FLinearColor Ally(0.04f, 0.55f, 0.75f);
	const FLinearColor Opponent(0.85f, 0.15f, 0.055f);
	const FLinearColor Healer(0.25f, 0.80f, 0.33f);
	const FLinearColor Dark(0.03f, 0.067f, 0.08f);
}

AYellSoldier::AYellSoldier()
{
	GetCapsuleComponent()->InitCapsuleSize(35, 85);
	AIControllerClass = AAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->MaxWalkSpeed = 360.0f;
	Movement->RotationRate.Yaw = 520;
	Movement->bUseRVOAvoidance = true;
	Movement->AvoidanceConsiderationRadius = 280.0f;

	auto MakePart = [this](FName Name, const FVector& Offset, const FVector& Scale, const TCHAR* MeshPath)
	{
		UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Part->SetupAttachment(GetCapsuleComponent());
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetCanEverAffectNavigation(false);
		Part->SetRelativeLocation(Offset);
		Part->SetRelativeScale3D(Scale);
		Part->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, MeshPath));
		return Part;
	};
	Torso = MakePart(TEXT("FieldJacket"), FVector(0, 0, -22), FVector(.45, .57, 1.03),
		TEXT("/Engine/BasicShapes/Cube.Cube"));
	Helmet = MakePart(TEXT("Helmet"), FVector(0, 0, 43), FVector(.66, .66, .52),
		TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	Visor = MakePart(TEXT("Visor"), FVector(23, 0, 40), FVector(.18, .51, .15),
		TEXT("/Engine/BasicShapes/Cube.Cube"));
}

void AYellSoldier::Initialize(const uint8 InTeam, const FName InSquad, const int32 Index, const bool bInMedic)
{
	Team = InTeam;
	Squad = InSquad;
	CallSign = FName(*FString::Printf(TEXT("%s-%d"), *Squad.ToString(), Index + 1));
	static const TMap<FName,TArray<FString>> Names = {
		{TEXT("Alfa"), {TEXT("Alex"), TEXT("Juan"), TEXT("Carlos"), TEXT("Jorge"), TEXT("Mario")}},
		{TEXT("Bravo"), {TEXT("Diego"), TEXT("Miguel"), TEXT("Luis"), TEXT("Sergio"), TEXT("Pablo")}},
		{TEXT("Médico"), {TEXT("Lucas"), TEXT("Mateo"), TEXT("Iván"), TEXT("Joel"), TEXT("Tomás")}},
		{TEXT("Delta"), {TEXT("Raúl"), TEXT("Andrés"), TEXT("Manuel"), TEXT("David"), TEXT("Pedro")}},
		{TEXT("Eco"), {TEXT("Hugo"), TEXT("René"), TEXT("Julián"), TEXT("Leo"), TEXT("Martín")}},
		{TEXT("Óxido"), {TEXT("Ramiro"), TEXT("Javier"), TEXT("Ricardo")}},
		{TEXT("Chispa"), {TEXT("Rubén"), TEXT("Óscar"), TEXT("Fabio")}},
		{TEXT("Resorte"), {TEXT("Marco"), TEXT("César"), TEXT("Emilio")}},
		{TEXT("Tuerca"), {TEXT("Raimer"), TEXT("Nicolás"), TEXT("Simón")}},
		{TEXT("Fósforo"), {TEXT("Joaquín"), TEXT("Emanuel"), TEXT("Bruno")}},
		{TEXT("Parche"), {TEXT("Víctor"), TEXT("Samuel"), TEXT("Felipe")}}
	};
	const TArray<FString>* Group = Names.Find(Squad);
	GivenName = Group && Group->IsValidIndex(Index) ? (*Group)[Index] : CallSign.ToString();
	bMedic = bInMedic;
	NextAction = GetWorld()->GetTimeSeconds() + Index * 0.19;
	CurrentOrder.Squad = Squad;
	Destination = GetActorLocation();
	UpdateVisuals();
}

bool AYellSoldier::CanAct() const
{
	return State != EYellSoldierState::Dead && State != EYellSoldierState::Downed;
}

FVector AYellSoldier::Eye() const
{
	return GetActorLocation() + FVector(0, 0, State == EYellSoldierState::TakingCover ? 4.0 : 48.0);
}

void AYellSoldier::UpdateVisuals()
{
	const FLinearColor Tint = !CanAct() ? FLinearColor(.3f, .25f, .12f) : bMedic ? Healer : Team == 0 ? Ally : Opponent;
	UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/LevelPrototyping/Materials/M_FlatCol.M_FlatCol"));
	if (!Base)
	{
		return;
	}
	for (UStaticMeshComponent* Part : {Torso.Get(), Helmet.Get(), Visor.Get()})
	{
		UMaterialInstanceDynamic* Material = Part->CreateDynamicMaterialInstance(0, Base);
		const FLinearColor Color = Part == Visor ? Dark : Tint;
		Material->SetVectorParameterValue(TEXT("Color"), Color);
		Material->SetVectorParameterValue(TEXT("BaseColor"), Color);
		Material->SetVectorParameterValue(TEXT("Base Color"), Color);
	}
}

void AYellSoldier::Accept(const FYellOrder& Order, const FVector& Goal, const FVector& Alternate)
{
	CurrentOrder = Order;
	Destination = Goal;
	Secondary = Alternate;
	bAlternate = false;
	CoverUntil = 0.0;
	NextMove = 0.0;
	Stop();
	State = EYellSoldierState::FollowingOrder;
}

void AYellSoldier::Move(const FVector& Goal, const double Time, const float Acceptance)
{
	if (Time < NextMove && FVector::DistSquared2D(Goal, LastMoveGoal) < FMath::Square(110.0))
	{
		return;
	}
	NextMove = Time + 0.85;
	LastMoveGoal = Goal;
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		if (AI->MoveToLocation(Goal, Acceptance, false, true, true, false) == EPathFollowingRequestResult::Failed)
		{
			FNavLocation Alternative;
			const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
			if (Nav && Nav->GetRandomReachablePointInRadius(Goal, 230, Alternative))
			{
				AI->MoveToLocation(Alternative.Location, Acceptance, false, true, true, false);
			}
		}
	}
}

void AYellSoldier::Stop()
{
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
	}
	NextMove = 0;
}

void AYellSoldier::Hurt(const float Damage, const double Time)
{
	if (!CanAct() || Damage <= 0)
	{
		return;
	}
	Health = FMath::Max(Health - Damage * (Time < BoostUntil ? 0.86f : 1.0f), 0.0f);
	if (Health <= 0)
	{
		Stop();
		State = EYellSoldierState::Downed;
		VisibleOpponent.Reset();
		DownUntil = Time + 22.0;
		GetCharacterMovement()->MaxWalkSpeed = 0;
		GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
		Torso->SetRelativeRotation(FRotator(75, 0, 0));
		Torso->SetRelativeLocation(FVector(0, 0, -65));
		Helmet->SetRelativeLocation(FVector(49, 0, -62));
		Visor->SetVisibility(false);
		UpdateVisuals();
	}
}

void AYellSoldier::Treat(const double Time)
{
	if (State == EYellSoldierState::Downed && Time < DownUntil)
	{
		State = EYellSoldierState::FollowingOrder;
		Health = 44;
		GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
		Torso->SetRelativeRotation(FRotator::ZeroRotator);
		Torso->SetRelativeLocation(FVector(0, 0, -22));
		Helmet->SetRelativeLocation(FVector(0, 0, 43));
		Visor->SetVisibility(true);
		UpdateVisuals();
	}
	else if (CanAct())
	{
		Health = FMath::Min(100.0f, Health + 18.0f);
	}
}

void AYellSoldier::Step(AYellBattle& Battle, const double Time)
{
	if (State == EYellSoldierState::Downed && Time >= DownUntil)
	{
		State = EYellSoldierState::Dead;
		SetActorEnableCollision(false);
		SetActorHiddenInGame(true);
		SetLifeSpan(1.5f);
	}
	if (!CanAct())
	{
		return;
	}
	GetCharacterMovement()->MaxWalkSpeed = Time < BoostUntil ? 444.0f : 370.0f;
	const EYellAction Action = CurrentOrder.Action;
	AYellSoldier* Enemy = Battle.FindOpponent(*this);
	VisibleOpponent = Enemy;
	if (bMedic && (Action == EYellAction::Heal || Action == EYellAction::Revive || Action == EYellAction::None))
	{
		if (AYellSoldier* Patient = Battle.FindPatient(*this))
		{
			State = EYellSoldierState::Healing;
			if (FVector::Dist2D(Patient->GetActorLocation(), GetActorLocation()) > 135)
			{
				Move(Patient->GetActorLocation(), Time, 102);
			}
			else if (Time >= NextAction)
			{
				Stop();
				Patient->Treat(Time);
				NextAction = Time + 1.35;
				DrawDebugLine(GetWorld(), Eye(), Patient->GetActorLocation(), FColor::Green, false, .35f, 0, 3);
			}
			return;
		}
	}
	if (Enemy && Health < 48 && Time >= CoverUntil + 2.0
		&& Action != EYellAction::Hold && Action != EYellAction::Cancel
		&& Battle.FindCover(*this, *Enemy, CoverGoal))
	{
		CoverUntil = Time + 2.4;
	}
	if (Time < CoverUntil)
	{
		State = EYellSoldierState::TakingCover;
		Move(CoverGoal, Time);
		return;
	}
	if (!bMedic && Action != EYellAction::Retreat && Action != EYellAction::Scout && Time >= NextAction)
	{
		AActor* Target = Enemy;
		FVector Impact = Enemy ? Enemy->Eye() : FVector::ZeroVector;
		if (!Target && Team == 1 && Battle.GetWorld()->GetFirstPlayerController())
		{
			APawn* Commander = Battle.GetWorld()->GetFirstPlayerController()->GetPawn();
			if (Commander && Battle.Visible(*this, *Commander, Commander->GetActorLocation()))
			{
				Target = Commander;
				Impact = Commander->GetActorLocation();
			}
		}
		if (Target || (Action == EYellAction::Attack && CurrentOrder.Zone == EYellZone::Rival))
		{
			State = EYellSoldierState::Attacking;
			Battle.SimulatePulse(*this, Target, Impact);
			NextAction = Time + 0.8;
		}
	}
	if (Action == EYellAction::None || Action == EYellAction::Cancel || Action == EYellAction::Hold)
	{
		State = Enemy ? EYellSoldierState::Defending : EYellSoldierState::Idle;
		return;
	}
	FVector Goal = bAlternate ? Secondary : Destination;
	if (FVector::DistSquared2D(Goal, GetActorLocation()) <= FMath::Square(105.0))
	{
		if (Action != EYellAction::Patrol)
		{
			State = Action == EYellAction::Attack ? EYellSoldierState::Attacking : EYellSoldierState::Defending;
			return;
		}
		bAlternate = !bAlternate;
		Goal = bAlternate ? Secondary : Destination;
	}
	State = Action == EYellAction::Retreat ? EYellSoldierState::Retreating : EYellSoldierState::Moving;
	Move(Goal, Time);
}

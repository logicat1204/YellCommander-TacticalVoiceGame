#include "YellBattle.h"

#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
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
	PrimaryActorTick.bCanEverTick = true;
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
	Rifle = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Rifle"));
	Rifle->SetupAttachment(GetCapsuleComponent());
	Rifle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Rifle->SetCanEverAffectNavigation(false);
	Rifle->SetVisibility(false);
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
	if (Team == 0 && FParse::Param(FCommandLine::Get(), TEXT("YellSujetoLugar")))
	{
		static const TCHAR* Stories[] = { TEXT("Antes reparaba radios con mi padre."), TEXT("Crecí junto a un río."),
			TEXT("Toco la guitarra en mis días libres."), TEXT("Mi hermano y yo teníamos una panadería.") };
		Background = Stories[FMath::RandHelper(UE_ARRAY_COUNT(Stories))];
	}
	bMedic = bInMedic;
	LoadUniform();
	NextAction = GetWorld()->GetTimeSeconds() + Index * 0.19;
	CurrentOrder.Squad = Squad;
	Destination = GetActorLocation();
	UpdateVisuals();
	if (AimClip)
	{
		ActiveClip = AimClip;
		GetMesh()->PlayAnimation(AimClip, true);
	}
}

void AYellSoldier::LoadUniform()
{
	const FString UniformName = bMedic ? TEXT("Medico") : Team == 0 ? TEXT("Aliado") : TEXT("Enemigo");
	const FString Folder = TEXT("/Game/Yell/Gameplay/Characters/") + UniformName + TEXT("/");
	auto Asset = [&Folder](const FString& Name) { return Folder + Name + TEXT(".") + Name; };
	const FString MeshPath = Asset(TEXT("SK_") + UniformName);
	USkeletalMesh* Uniform = LoadObject<USkeletalMesh>(nullptr, *MeshPath);
	if (!Uniform)
		return;
	GetMesh()->SetSkeletalMeshAsset(Uniform);
	const FBoxSphereBounds Bounds = Uniform->GetBounds();
	const double Scale = 173.0 / FMath::Max(1.0, Bounds.BoxExtent.Z * 2.);
	GetMesh()->SetRelativeScale3D(FVector(Scale));
	GetMesh()->SetRelativeLocation(FVector(0, 0, -85. - (Bounds.Origin.Z - Bounds.BoxExtent.Z)*Scale));
	StandingMeshOffset = GetMesh()->GetRelativeLocation();
	GetMesh()->SetRelativeRotation(FRotator(0, -90, 0));
	const FString Palette = bMedic ? TEXT("Medico") : Team == 1 ? TEXT("Enemigo")
		: Squad == TEXT("Bravo") ? TEXT("Bravo") : TEXT("Alpha");
	const FString Material = TEXT("MI_Soldado_") + Palette;
	const FString MaterialPath = TEXT("/Game/Yell/Art/Materials/Instances/Teams/") + Material + TEXT(".") + Material;
	if (UMaterialInterface* Skin = LoadObject<UMaterialInterface>(nullptr, *MaterialPath))
	{
		for (int32 Slot = 0; Slot < GetMesh()->GetNumMaterials(); ++Slot)
			GetMesh()->SetMaterial(Slot, Skin);
		if (bMedic && Team == 1)
			GetMesh()->CreateDynamicMaterialInstance(0, Skin)->SetVectorParameterValue(TEXT("Tint"), FLinearColor(1.f,.59f,.51f));
	}
	WalkClip = LoadObject<UAnimSequence>(nullptr, *Asset(TEXT("A_Caminar")));
	AimClip = LoadObject<UAnimSequence>(nullptr, *Asset(bMedic ? TEXT("A_Alerta") : TEXT("A_Postura")));
	CareClip = bMedic ? LoadObject<UAnimSequence>(nullptr, *Asset(TEXT("A_Postura"))) : nullptr;
	FallClip = LoadObject<UAnimSequence>(nullptr, *Asset(TEXT("A_Caer")));
	if (FallClip) FallClip->bForceRootLock = false;
	TArray<FName> Bones;
	GetMesh()->GetBoneNames(Bones);
	for (const FName Bone : Bones)
	{
		const FString Label = Bone.ToString();
		if (Label.EndsWith(TEXT("RightHand"))) RightHand = Bone;
		if (Label.EndsWith(TEXT("LeftHand"))) LeftHand = Bone;
		if (Label.EndsWith(TEXT("Hips")) || Label.Equals(TEXT("pelvis"), ESearchCase::IgnoreCase)) Hips = Bone;
	}
	if (!bMedic && !RightHand.IsNone())
	{
		auto* Weapon = LoadObject<UStaticMesh>(nullptr,
			TEXT("/Game/Yell/Art/Models/Static/SM_Rifle_Asalto.SM_Rifle_Asalto"));
		if (Weapon)
		{
			Rifle->SetStaticMesh(Weapon);
			const FBoxSphereBounds WeaponBounds = Weapon->GetBounds();
			const bool bLongY = WeaponBounds.BoxExtent.Y > WeaponBounds.BoxExtent.X;
			const double Offset = bLongY ? WeaponBounds.Origin.Y : WeaponBounds.Origin.X;
			BarrelAxis = (bLongY ? FVector::RightVector : FVector::ForwardVector) * (Offset < 0. ? -1. : 1.);
			const double HalfLength = bLongY ? WeaponBounds.BoxExtent.Y : WeaponBounds.BoxExtent.X;
			BarrelTip = BarrelAxis * (HalfLength + FMath::Abs(Offset)) + FVector(0,0,6);
			Rifle->SetRelativeScale3D(FVector(88. / FMath::Max(1., 2. * HalfLength)));
			if (auto* Metal = LoadObject<UMaterialInterface>(nullptr,
				TEXT("/Game/Yell/Art/Materials/Instances/Teams/MI_Armas.MI_Armas")))
				Rifle->SetMaterial(0, Metal);
		}
	}
	Torso->SetVisibility(false);
	Helmet->SetVisibility(false);
	Visor->SetVisibility(false);
}

void AYellSoldier::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!GetMesh()->GetSkeletalMeshAsset())
		return;
	const bool bWalking = GetVelocity().SizeSquared2D() > FMath::Square(30.0);
	UAnimSequence* Clip = !CanAct() ? FallClip.Get() : bWalking ? WalkClip.Get()
		: State == EYellSoldierState::Healing && CareClip ? CareClip.Get() : AimClip.Get();
	if (Clip && Clip != ActiveClip)
	{
		ActiveClip = Clip;
		GetMesh()->PlayAnimation(Clip, CanAct());
	}
	PoseRifle(bWalking);
	const double Now = GetWorld()->GetTimeSeconds();
	if (!CanAct() && (!FallClip || Now - FallStartedAt >= FallClip->GetPlayLength()) &&
		(Hips.IsNone() || GetMesh()->GetSocketLocation(Hips).Z > GetActorLocation().Z - 27.))
	{
		GetMesh()->SetRelativeRotation(FRotator(0,-90,90));
		GetMesh()->SetRelativeLocation(FVector(0,0,-72));
	}
	if (CanAct() && bWalking && Now >= NextFootstep && GetCharacterMovement()->IsMovingOnGround())
	{
		NextFootstep = Now + .34;
		const FName Step = FName(*FString::Printf(TEXT("Paso%d"), FMath::RandRange(1,3)));
		if (auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>())
			Battle->PlayEffect(Step, GetActorLocation(), .34f);
	}
	if (CanAct() && !bWalking && !bMedic && VisibleOpponent.IsValid())
	{
		const FRotator Look(0, (VisibleOpponent->GetActorLocation() - GetActorLocation()).Rotation().Yaw, 0);
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), Look, DeltaSeconds, 8.f));
	}
}

void AYellSoldier::PoseRifle(const bool bWalking)
{
	if (!Rifle->GetStaticMesh()) return;
	Rifle->SetVisibility(CanAct());
	if (!CanAct()) return;
	const FVector Grip = GetMesh()->GetSocketLocation(RightHand);
	FVector Aim = GetActorForwardVector();
	if (bWalking)
		Aim = (Aim - FVector(0,0,.7)).GetSafeNormal();
	else if (!LeftHand.IsNone())
	{
		const FVector ToSupport = (GetMesh()->GetSocketLocation(LeftHand) - Grip).GetSafeNormal();
		if (!ToSupport.IsNearlyZero()) Aim = ToSupport;
	}
	const FQuat Orientation = FRotationMatrix::MakeFromXZ(Aim, FVector::UpVector).ToQuat()
		* FQuat::FindBetweenNormals(BarrelAxis, FVector::ForwardVector);
	Rifle->SetWorldLocationAndRotation(Grip + Orientation.RotateVector(FVector(0,0,5)), Orientation);
}

FVector AYellSoldier::Muzzle() const
{
	return Rifle->IsVisible() ? Rifle->GetComponentTransform().TransformPosition(BarrelTip) : Eye();
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
	if (GetMesh()->GetSkeletalMeshAsset())
		return;
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
	LastHit = Time;
	Health = FMath::Max(Health - Damage * (Time < BoostUntil ? 0.86f : 1.0f), 0.0f);
	if (Health <= 0)
	{
		Stop();
		State = EYellSoldierState::Downed;
		FallStartedAt = Time;
		GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		if (auto* Battle = GetWorld()->GetAuthGameMode<AYellBattle>())
			Battle->PlayEffect(TEXT("Caida"), GetActorLocation(), .7f);
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
		DownedBy.Reset();
		State = EYellSoldierState::FollowingOrder;
		GetMesh()->SetRelativeRotation(FRotator(0,-90,0));
		GetMesh()->SetRelativeLocation(StandingMeshOffset);
		GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPose;
		Health = 44;
		GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
		Torso->SetRelativeRotation(FRotator::ZeroRotator);
		Torso->SetRelativeLocation(FVector(0, 0, -22));
		Helmet->SetRelativeLocation(FVector(0, 0, 43));
		Visor->SetVisibility(!GetMesh()->GetSkeletalMeshAsset());
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
		if (DownedBy.IsValid()) ++DownedBy->Eliminations;
		DownedBy.Reset();
		State = EYellSoldierState::Dead;
		SetActorEnableCollision(false);
		SetLifeSpan(4.f);
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

#include "YellBattle.h"
#include "YellRoundVisual.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "NavigationSystem.h"

#include "Algo/Count.h"
#include "Engine/StaticMeshActor.h"
#include "TimerManager.h"
#include "YellPlayer.h"

DEFINE_LOG_CATEGORY_STATIC(LogYellBattle, Log, All);

namespace
{
	constexpr double RequestLifetime = 48.0;
	constexpr double IntelLifetime = 26.0;
	constexpr float PulseReach = 1720.0f;
	constexpr float HearingReach = 1080.0f;

	FVector FormationOffset(const int32 Index, const uint8 Team)
	{
		return FVector((Team == 0 ? -1.0 : 1.0) * (Index % 2) * 125, (Index - 2) * 123, 0);
	}
}

int32 FYellSquad::Alive() const
{
	return Algo::CountIf(Members, [](const auto& Unit) { return Unit.IsValid() && Unit->IsAlive(); });
}

int32 FYellSquad::Ready() const
{
	return Algo::CountIf(Members, [](const auto& Unit) { return Unit.IsValid() && Unit->CanAct(); });
}

AYellBattle::AYellBattle()
{
	PlayerControllerClass = AYellPlayer::StaticClass();
	DefaultPawnClass = AYellCommander::StaticClass();
	HUDClass = AYellHUD::StaticClass();
	EffectAttenuation = CreateDefaultSubobject<USoundAttenuation>(TEXT("BattlefieldAudio"));
	EffectAttenuation->Attenuation.AttenuationShapeExtents = FVector(250.f, 0.f, 0.f);
	EffectAttenuation->Attenuation.FalloffDistance = 2450.f;
}

void AYellBattle::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);
	bMenuScene = UGameplayStatics::HasOption(Options, TEXT("YellMenu"));
	Difficulty = FYellRivalPolicy::Parse(UGameplayStatics::ParseOption(Options, TEXT("YellDifficulty")));
	RivalPolicy = FYellRivalPolicy::For(Difficulty);
}

void AYellBattle::BeginPlay()
{
	Super::BeginPlay();
	if (auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
		Nav->OnNavigationGenerationFinishedDelegate.AddUniqueDynamic(this, &AYellBattle::CacheWalkableTerrain);
	BuildArena();
	if (bMenuScene)
	{
		BuildMenuScene();
		GetWorldTimerManager().SetTimer(BattleTimer, this, &AYellBattle::UpdateMenuScene, .24f, true);
		return;
	}
	SpawnSquad(0, TEXT("Alfa"), false, 4);
	SpawnSquad(0, TEXT("Bravo"), false, 4);
	SpawnSquad(0, TEXT("Médico"), true, 2);
	SpawnSquad(1, TEXT("Óxido"), false, 3);
	SpawnSquad(1, TEXT("Chispa"), false, 3);
	SpawnSquad(1, TEXT("Resorte"), false, 3);
	Personality = FMath::RandRange(0, 2);
	SpawnSquad(1, TEXT("Parche"), true, 2);
	NextRivalDecision = GetWorld()->GetTimeSeconds() + 6.0;
	MedicalClockStart = GetWorld()->GetTimeSeconds();
	NextIntelReport = GetWorld()->GetTimeSeconds() + RivalPolicy.IntelInterval;
	OrderListener = OnOrder.AddUObject(this, &AYellBattle::ApplyOrder);
	bArenaReady = true;
	GetWorldTimerManager().SetTimer(BattleTimer, this, &AYellBattle::UpdateBattle, 0.24f, true);
	UE_LOG(LogYellBattle, Display, TEXT("Valle Alfa listo. Dificultad %s, informe rival cada %.2fs."),
		FYellRivalPolicy::Name(Difficulty), RivalPolicy.IntelInterval);
}

void AYellBattle::EndPlay(const EEndPlayReason::Type Reason)
{
	GetWorldTimerManager().ClearTimer(BattleTimer);
	if (auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
		Nav->OnNavigationGenerationFinishedDelegate.RemoveDynamic(this, &AYellBattle::CacheWalkableTerrain);
	OnOrder.Remove(OrderListener);
	Super::EndPlay(Reason);
}

void AYellBattle::PlayEffect(const FName Name, const FVector& Location, const float Volume)
{
	if (!GetWorld()->GetAudioDeviceRaw()) return;
	auto* Cached = Effects.Find(Name);
	if (!Cached)
	{
		const FString Asset = Name.ToString();
		const FString Path = FString::Printf(TEXT("/Game/Yell/Gameplay/Sounds/%s.%s"), *Asset, *Asset);
		Cached = &Effects.Add(Name, LoadObject<USoundBase>(nullptr, *Path));
	}
	if (auto* Cue = Cached->Get())
		UGameplayStatics::PlaySoundAtLocation(this, Cue, Location, FRotator::ZeroRotator, Volume, 1.f, 0.f,
			EffectAttenuation);
}

void AYellBattle::RestartPlayer(AController* NewPlayer)
{
	if (!bMenuScene && NewPlayer && !NewPlayer->GetPawn())
	{
		RestartPlayerAtTransform(NewPlayer, FTransform(FRotator::ZeroRotator, SpawnPosition(0)));
	}
}

bool AYellBattle::SpawnSquad(const uint8 Team, const FName Name, const bool bMedic, const int32 Count)
{
	if (Count < 1 || Count > FYellReinforcements::MaxMembers || Name.IsNone()
		|| Algo::CountIf(Squads, [Team](const FYellSquad& S) { return S.Team == Team && S.Alive() > 0; }) >= FYellReinforcements::MaxSquads
		|| Squads.ContainsByPredicate([Team, Name, bMedic](const FYellSquad& S)
			{ return S.Team == Team && S.Alive() > 0 && (S.Id == Name || (bMedic && S.bMedic)); }))
	{
		return false;
	}
	const double Sign = Team == 0 ? -1.0 : 1.0;
	const int32 TeamCount = Algo::CountIf(Squads, [Team](const FYellSquad& S) { return S.Team == Team && S.Alive() > 0; });
	const FVector Rally = Position(EYellZone::Home, Team)
		+ FVector(-Sign * (TeamCount < 3 ? 470 : 890), (TeamCount % 3 - 1) * 1150, 82);
	FYellSquad Squad;
	Squad.Id = Name;
	Squad.Team = Team;
	Squad.bMedic = bMedic;
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		AYellSoldier* Unit = GetWorld()->SpawnActor<AYellSoldier>(Rally + FormationOffset(Index, Team),
			FRotator(0, Team == 0 ? 0 : 180, 0), Params);
		if (Unit)
		{
			Unit->Initialize(Team, Name, Index, bMedic);
			Squad.Members.Add(Unit);
			AllUnits.Add(Unit);
		}
	}
	if (Squad.Members.IsEmpty())
	{
		return false;
	}
	Squads.Add(MoveTemp(Squad));
	return true;
}

TArray<FString> AYellBattle::AlliedNames() const
{
	TArray<FString> Names;
	for (const FYellSquad& Squad : Squads)
	{
		if (Squad.Team == 0 && Squad.Alive() > 0)
		{
			Names.Add(Squad.Id.ToString());
		}
	}
	return Names;
}

TArray<FString> AYellBattle::AlliedSoldierNames() const
{
	TArray<FString> Names;
	for (const auto& Unit : AllUnits)
	{
		if (Unit.IsValid() && Unit->Team == 0 && Unit->IsAlive())
		{
			Names.Add(Unit->CallSign.ToString());
		}
	}
	return Names;
}

FString AYellBattle::Dispatch(FYellOrder Order, const FYellRequestContext& Context, bool& bAccepted)
{
	bAccepted = false;
	const double Now = GetWorld()->GetTimeSeconds();
	if (!bArenaReady || WinningTeam != INDEX_NONE)
	{
		return TEXT("La partida no admite nuevas órdenes.");
	}
	if (!Context.Id.IsValid() || Context.Started > Now + 0.1 || Now - Context.Started > RequestLifetime
		|| SeenRequests.Contains(Context.Id))
	{
		return TEXT("La transmisión ya fue procesada o venció.");
	}
	SeenRequests.Add(Context.Id, Now);
	if (Order.Intent == EYellIntent::Chat)
	{
		return TEXT("Canal de charla. Los pelotones siguen en lo suyo.");
	}
	if (Order.Intent == EYellIntent::Unknown)
	{
		return TEXT("No se entendió la instrucción. Repítala, mi General.");
	}
	const uint8 Team = Context.Channel == EYellChannel::Rival ? 1 : 0;
	const bool bMorale = Order.Intent == EYellIntent::Morale;
	if (!bMorale && (Order.Action == EYellAction::None
		|| (Order.Squad.IsNone() && Order.Soldier.IsNone() && Context.Channel != EYellChannel::Nearby)))
	{
		return TEXT("Indique una acción y un pelotón, mi General.");
	}
	if (!bMorale && (YellOrder::NeedsZone(Order.Action) && Order.Zone == EYellZone::None))
	{
		return TEXT("¿A qué zona nos dirigimos, mi General?");
	}
	if ((Order.Action == EYellAction::Hold || Order.Action == EYellAction::Cancel) && Order.Zone != EYellZone::None)
	{
		return TEXT("Mantener o cancelar se aplica al sitio actual del pelotón.");
	}
	TArray<AYellSoldier*> Recipients;
	TSet<FName> SquadIds;
	bool bRecipientExists = Order.Squad.IsNone() && Order.Soldier.IsNone();
	for (const FYellSquad& Squad : Squads)
	{
		if (Squad.Team != Team || (!Order.Squad.IsNone() && Squad.Id != Order.Squad) || !Squad.Alive())
		{
			continue;
		}
		bRecipientExists |= Order.Soldier.IsNone();
		for (const auto& Member : Squad.Members)
		{
			if (!Member.IsValid() || !Member->IsAlive() || (!Order.Soldier.IsNone() && Member->CallSign != Order.Soldier))
			{
				continue;
			}
			bRecipientExists = true;
			if (Member->CanAct() && (Context.Channel != EYellChannel::Nearby
				|| FVector::DistSquared(Context.Origin, Member->GetActorLocation()) <= FMath::Square(NearbyRadius)))
			{
				Recipients.Add(Member.Get());
				SquadIds.Add(Squad.Id);
			}
		}
	}
	if (Recipients.IsEmpty())
	{
		return bRecipientExists ? TEXT("Ningún soldado disponible recibió la transmisión.")
			: TEXT("El destinatario indicado no está activo.");
	}
	if (!bMorale && SquadIds.Num() != 1)
	{
		return TEXT("Hay varios pelotones al alcance. Indique uno.");
	}
	if (bMorale)
	{
		if (Now < MoraleReady)
		{
			return TEXT("La tropa todavía está recuperando el aliento.");
		}
		MoraleReady = Now + MoraleCooldown;
		bAccepted = true;
		OnOrder.Broadcast(Order, Recipients);
		return FString::Printf(TEXT("¡Por usted y por el almuerzo! Moral para %d soldados."), Recipients.Num());
	}
	Order.Squad = Recipients[0]->Squad;
	if (YellOrder::IsMedical(Order.Action) && !Recipients[0]->bMedic)
	{
		return TEXT("Se requiere un pelotón médico para esa orden.");
	}
	if (Recipients[0]->bMedic && Order.Action == EYellAction::Attack)
	{
		return TEXT("El pelotón médico se dedica a atender a los heridos.");
	}
	if (!Order.Target.IsNone() && !Squads.ContainsByPredicate([&](const FYellSquad& Squad)
		{ return Squad.Team == Team && Squad.Id == Order.Target && Squad.Id != Order.Squad && Squad.Alive() > 0; }))
	{
		return TEXT("El pelotón a atender no está disponible.");
	}
	if (!Order.TargetSoldier.IsNone() && !AllUnits.ContainsByPredicate([&](const auto& Unit)
		{ return Unit.IsValid() && Unit->Team == Team && Unit->CallSign == Order.TargetSoldier
			&& Unit->IsAlive() && !Recipients.Contains(Unit.Get()); }))
	{
		return TEXT("El soldado a atender no está disponible.");
	}
	if (Order.Action == EYellAction::Retreat && Order.Zone == EYellZone::None)
	{
		Order.Zone = EYellZone::Home;
	}
	if (Order.Zone != EYellZone::None)
	{
		FNavLocation Projected;
		const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
		if (!Nav || !Nav->ProjectPointToNavigation(Position(Order.Zone, Team), Projected, FVector(240, 240, 230)))
		{
			return TEXT("El destino no está disponible en la malla de navegación.");
		}
	}
	bAccepted = true;
	OnOrder.Broadcast(Order, Recipients);
	UE_LOG(LogYellBattle, Display, TEXT("Orden %s equipo=%u peloton=%s accion=%s lugar=%s receptores=%d"),
		*Context.Id.ToString(), Team, *Order.Squad.ToString(), *YellOrder::ActionText(Order.Action),
		*YellOrder::ZoneText(Order.Zone), Recipients.Num());
	const FString Addressee = Order.Soldier.IsNone() ? Order.Squad.ToString() : Recipients[0]->GivenName;
	return FString::Printf(TEXT("¡Copiado, %s! %s %s."), *Addressee, *YellOrder::ActionText(Order.Action),
		*YellOrder::ZoneText(Order.Zone)).Replace(TEXT(" ."), TEXT("."));
}

void AYellBattle::ApplyOrder(const FYellOrder& Order, const TArray<AYellSoldier*>& Recipients)
{
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < Recipients.Num(); ++Index)
	{
		AYellSoldier* Soldier = Recipients[Index];
		if (Order.Intent == EYellIntent::Morale)
		{
			Soldier->BoostUntil = Now + MoraleDuration;
			continue;
		}
		const FVector Goal = Order.Zone == EYellZone::None ? Soldier->GetActorLocation()
			: Position(Order.Zone, Soldier->Team) + FormationOffset(Index, Soldier->Team);
		Soldier->Accept(Order, Goal, Goal + FVector(Soldier->Team == 0 ? 470 : -470, 180, 0));
		if (Soldier->Team == 1 && Order.Action == EYellAction::Attack && Order.Zone == EYellZone::Rival)
		{
			if (const auto* Lane = AttackLanes.Find(Order.Squad); Lane && *Lane != EYellZone::Center)
			{
				const FVector Approach = RivalApproach(*Lane);
				if (Soldier->GetActorLocation().X > Approach.X + 140.)
					Soldier->SetMarchWaypoint(Approach + FVector(0, FormationOffset(Index, 1).Y, 0));
			}
		}
	}
}

float AYellBattle::NextReinforcement(const uint8 Team) const
{
	return Reinforcements[Team].Remaining(GetWorld()->GetTimeSeconds());
}

float AYellBattle::NextMorale() const
{
	return FMath::Max(0.0, MoraleReady - GetWorld()->GetTimeSeconds());
}

FString AYellBattle::TryReinforce(const uint8 Team, const bool bMedical, const FVector* Requester)
{
	if (WinningTeam != INDEX_NONE || (Team == 0 && (!Requester || !IsTerminalNearby(Team, *Requester))))
	{
		return TEXT("Acérquese a la terminal aliada para solicitar refuerzos.");
	}
	const int32 Active = Algo::CountIf(Squads, [Team](const FYellSquad& S) { return S.Team == Team && S.Alive() > 0; });
	const bool bActiveMedic = Squads.ContainsByPredicate([Team](const FYellSquad& S)
		{ return S.Team == Team && S.bMedic && S.Alive() > 0; });
	switch (Reinforcements[Team].Request(GetWorld()->GetTimeSeconds(), ReinforcementCooldown, Active, bActiveMedic, bMedical))
	{
	case FYellReinforcements::EResult::Full: return TEXT("Ya hay cinco pelotones activos.");
	case FYellReinforcements::EResult::MedicAlreadyActive: return TEXT("Ya existe un pelotón médico activo.");
	case FYellReinforcements::EResult::Busy: return TEXT("La terminal ya tiene una solicitud en curso o en espera.");
	default:
		UpdateTerminalAppearance(Team);
		return TEXT("Refuerzos en camino. Ojalá traigan café.");
	}
}

void AYellBattle::DamageCore(const uint8 Team, const float Damage)
{
	if (WinningTeam != INDEX_NONE)
	{
		return;
	}
	BaseHealth[Team] = FMath::Max(0.0f, BaseHealth[Team] - Damage);
	UpdateCoreAppearance(Team);
	if (Team == 1 && Damage > 0)
	{
		const double Now = GetWorld()->GetTimeSeconds();
		if (Now - LastRivalCoreHit > 4.0)
			NextRivalDecision = FMath::Min(NextRivalDecision, Now + 0.6);
		LastRivalCoreHit = Now;
	}
	if (BaseHealth[Team] == 0)
	{
		WinningTeam = 1 - Team;
		UpdateTerminalAppearance(0);
		UpdateTerminalAppearance(1);
		if (Cores[Team].IsValid())
		{
			Cores[Team]->SetActorHiddenInGame(true);
			Cores[Team]->SetActorEnableCollision(false);
		}
		for (const auto& Unit : AllUnits)
		{
			if (Unit.IsValid() && Unit->CanAct())
			{
				Unit->Accept(FYellOrder(), Unit->GetActorLocation(), Unit->GetActorLocation());
			}
		}
		UE_LOG(LogYellBattle, Display, TEXT("Partida finalizada. Equipo vencedor: %d"), WinningTeam);
	}
}

bool AYellBattle::Visible(const AYellSoldier& Observer, const AActor& Target, const FVector& Point, const bool bCone) const
{
	const FVector Delta = Point - Observer.Eye();
	if (Delta.SizeSquared() > FMath::Square(PulseReach)
		|| (bCone && FVector::DotProduct(Delta.GetSafeNormal2D(), Observer.GetActorForwardVector()) < 0.15
			&& Delta.SizeSquared2D() > FMath::Square(300.0)))
	{
		return false;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(YellVision), false, &Observer);
	FHitResult Hit;
	return !GetWorld()->LineTraceSingleByChannel(Hit, Observer.Eye(), Point, ECC_Visibility, Params)
		|| Hit.GetActor() == &Target;
}

AYellSoldier* AYellBattle::FindOpponent(AYellSoldier& Soldier) const
{
	AYellSoldier* Result = nullptr;
	double Best = FMath::Square(PulseReach);
	for (const auto& Other : AllUnits)
	{
		if (!Other.IsValid() || Other->Team == Soldier.Team || !Other->CanAct())
		{
			continue;
		}
		const double Distance = FVector::DistSquared(Other->Eye(), Soldier.Eye());
		if (Distance < Best && Visible(Soldier, *Other, Other->Eye(), Soldier.CurrentOrder.Action != EYellAction::Defend))
		{
			Best = Distance;
			Result = Other.Get();
		}
	}
	return Result;
}

FYellMedicalStatus AYellBattle::MedicalStatus(uint8 Team) const
{
	return MedicalSupplies[Team].Status(GetWorld()->GetTimeSeconds() - MedicalClockStart);
}

AYellSoldier* AYellBattle::FindPatient(const AYellSoldier& Medic) const
{
	AYellSoldier* Best = nullptr;
	double BestScore = -1e9;
	const double Now = GetWorld()->GetTimeSeconds();
	const auto Supplies = MedicalSupplies[Medic.Team].Status(Now - MedicalClockStart);
	for (const auto& Unit : AllUnits)
	{
		if (!Unit.IsValid() || Unit.Get() == &Medic || Unit->Team != Medic.Team || !Unit->IsAlive()
			|| (!Medic.CurrentOrder.Target.IsNone() && Medic.CurrentOrder.Target != Unit->Squad)
			|| (!Medic.CurrentOrder.TargetSoldier.IsNone() && Medic.CurrentOrder.TargetSoldier != Unit->CallSign)
			|| (Unit->CanAct() ? (Unit->Health >= 97 || Supplies.Healing <= 0.f || Medic.CurrentOrder.Action == EYellAction::Revive)
				: (!Unit->CanBeRevived(Now) || Supplies.Revives == 0)))
		{
			continue;
		}
		const double Distance = FVector::Dist2D(Medic.GetActorLocation(), Unit->GetActorLocation());
		const double ToZone = FVector::Dist2D(Medic.Destination, Unit->GetActorLocation());
		const bool bRouted = Medic.CurrentOrder.Zone != EYellZone::None;
		if ((bRouted && ToZone > 900)
			|| (!bRouted && Medic.CurrentOrder.Target.IsNone() && Medic.CurrentOrder.TargetSoldier.IsNone() && Distance > 950))
		{
			continue;
		}
		const double Score = (!Unit->CanAct() ? 1500 : 100 - Unit->Health) - Distance * 0.18;
		if (Score > BestScore)
		{
			Best = Unit.Get();
			BestScore = Score;
		}
	}
	return Best;
}

void AYellBattle::TreatPatient(const AYellSoldier& Medic, AYellSoldier& Patient, double Now)
{
	if (!Medic.bMedic || !Medic.CanAct() || Medic.Team != Patient.Team || &Medic == &Patient
		|| WinningTeam != INDEX_NONE) return;
	auto& Supplies = MedicalSupplies[Medic.Team];
	const double Elapsed = Now - MedicalClockStart;
	if (Patient.CanBeRevived(Now))
	{
		if (Supplies.SpendRevive(Elapsed)) Patient.Revive();
	}
	else if (Patient.CanAct() && Medic.CurrentOrder.Action != EYellAction::Revive)
	{
		Patient.Health += Supplies.SpendHealing(Elapsed, FMath::Min(18.f, 100.f - Patient.Health));
	}
}

bool AYellBattle::FindCover(const AYellSoldier& Soldier, const AActor& Threat, FVector& Goal) const
{
	double Best = FMath::Square(480.0);
	bool bFound = false;
	for (const FVector& Candidate : CoverPositions)
	{
		const double Distance = FVector::DistSquared2D(Soldier.GetActorLocation(), Candidate);
		if (Distance < Best && GetWorld()->LineTraceTestByChannel(Threat.GetActorLocation() + FVector(0, 0, 20),
			Candidate + FVector(0, 0, 90), ECC_Visibility, FCollisionQueryParams(SCENE_QUERY_STAT(YellCover), false, &Threat)))
		{
			Goal = Candidate;
			Best = Distance;
			bFound = true;
		}
	}
	return bFound;
}

void AYellBattle::SimulatePulse(AYellSoldier& Soldier, AActor* Target, const FVector& Point)
{
	const uint8 Team = Soldier.Team;
	const double Now = GetWorld()->GetTimeSeconds();
	FVector Impact = Point;
	AActor* RivalCore = Cores[1 - Team].Get();
	if (Soldier.CurrentOrder.Action == EYellAction::Attack && Soldier.CurrentOrder.Zone == EYellZone::Rival
		&& RivalCore && Visible(Soldier, *RivalCore, CorePosition(1 - Team), false))
	{
		Impact = CorePosition(1 - Team);
		DamageCore(1 - Team, 14);
	}
	else if (AYellSoldier* Other = Cast<AYellSoldier>(Target))
	{
		const bool bWasActive = Other->CanAct();
		Other->Hurt(16, Now);
		if (bWasActive && !Other->CanAct()) Other->DownedBy = &Soldier;
	}
	else if (AYellCommander* Commander = Cast<AYellCommander>(Target))
	{
		Commander->Hurt(13);
	}
	else
	{
		return;
	}
	if (FApp::CanEverRender())
	{
		if (auto* Visual = GetWorld()->SpawnActor<AYellRoundVisual>(Soldier.Muzzle(), FRotator::ZeroRotator))
			Visual->TravelTo(Impact);
	}
	PlayEffect(TEXT("Disparo"), Soldier.Muzzle(), .62f);
	if (Team == 0)
	{
		for (const auto& Observer : AllUnits)
		{
			if (Observer.IsValid() && Observer->Team == 1 && Observer->CanAct()
				&& Observer->CurrentOrder.Action != EYellAction::Scout
				&& FVector::DistSquared2D(Soldier.GetActorLocation(), Observer->GetActorLocation()) < FMath::Square(HearingReach))
			{
				ReportContact({ NAME_None, LaneOf(Soldier.GetActorLocation()), Now, 0.38f });
				break;
			}
		}
	}
}

bool AYellBattle::DetectedByPlayer(const AYellSoldier& Soldier) const
{
	const double* Detected = PlayerIntel.Find(const_cast<AYellSoldier*>(&Soldier));
	return Detected && GetWorld()->GetTimeSeconds() - *Detected < 1.0;
}

FString AYellBattle::RivalPersonality() const
{
	const TCHAR* Names[] = { TEXT("Impulsivo"), TEXT("Calculador"), TEXT("Engañoso") };
	return Names[Personality];
}

void AYellBattle::ReportContact(const FContact& Contact)
{
	const FName Key = Contact.Squad.IsNone() ? FName(*YellOrder::ZoneText(Contact.Lane)) : Contact.Squad;
	Observations.Add(Key, Contact);
}

void AYellBattle::UpdateBattle()
{
	if (WinningTeam != INDEX_NONE)
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	// The initial mesh may already be registered before the generation callback runs.
	if (NavTriangles.IsEmpty())
		if (auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
			CacheWalkableTerrain(Nav->GetDefaultNavDataInstance(FNavigationSystem::DontCreate));
	for (auto It = SeenRequests.CreateIterator(); It; ++It)
	{
		if (Now - It.Value() > RequestLifetime)
		{
			It.RemoveCurrent();
		}
	}
	AllUnits.RemoveAll([](const auto& Unit) { return !Unit.IsValid(); });
	Squads.RemoveAll([](const FYellSquad& Squad) { return !Squad.Alive(); });
	for (auto It = PlayerIntel.CreateIterator(); It; ++It)
	{
		if (!It.Key().IsValid() || Now - It.Value() > 1.0)
		{
			It.RemoveCurrent();
		}
	}
	for (uint8 Team = 0; Team < 2; ++Team)
	{
		bool bMedical = false;
		if (Reinforcements[Team].Collect(Now, bMedical))
		{
			const TArray<FName> Names = Team == 0 ? TArray<FName>{TEXT("Delta"), TEXT("Eco"), TEXT("Alfa"), TEXT("Bravo")}
				: TArray<FName>{TEXT("Tuerca"), TEXT("Fósforo"), TEXT("Óxido"), TEXT("Chispa"), TEXT("Resorte")};
			for (const FName Name : Names)
			{
				if (SpawnSquad(Team, bMedical ? FName(Team == 0 ? TEXT("Médico") : TEXT("Parche")) : Name, bMedical, 3))
				{
					break;
				}
			}
		}
	}
	RequestRivalReinforcements(Now);
	UpdateTerminalAppearance(0);
	UpdateTerminalAppearance(1);
	for (const auto& WeakUnit : AllUnits)
	{
		if (WinningTeam != INDEX_NONE)
		{
			break;
		}
		AYellSoldier* Unit = WeakUnit.Get();
		if (!Unit)
		{
			continue;
		}
		Unit->Step(*this, Now);
		AYellSoldier* Opponent = Unit->LastSeenOpponent();
		if (Unit->CanAct() && Opponent && Opponent->CanAct())
		{
			if (Unit->Team == 0)
			{
				PlayerIntel.Add(Opponent, Now);
			}
			else
			{
				const FContact Contact = { Opponent->CallSign, LaneOf(Opponent->GetActorLocation()), Now, 0.95f, Opponent->bMedic ? 0.f : Opponent->Health * 20.f, static_cast<float>(FMath::Clamp(1. - FVector::Dist2D(Opponent->GetActorLocation(), CorePosition(1)) / FVector::Dist2D(CorePosition(0), CorePosition(1)), 0., 1.)) };
				ReportContact(Contact);
			}
		}
	}
	if (Now >= NextIntelReport)
	{
		for (const auto& Entry : Observations) Intelligence.Add(Entry.Key, Entry.Value);
		Observations.Reset();
		NextIntelReport = Now + RivalPolicy.IntelInterval;
	}
	if (Now >= NextRivalDecision && WinningTeam == INDEX_NONE)
	{
		RunRival(Now);
		NextRivalDecision = Now + FMath::FRandRange(3.f, 4.f);
	}
}

void AYellBattle::RequestRivalReinforcements(const double Now)
{
	if (Reinforcements[1].Remaining(Now) > 0.f) return;
	int32 SquadsAlive = 0;
	int32 CombatReady = 0;
	bool bHasMedic = false;
	for (const auto& Squad : Squads)
	{
		if (Squad.Team != 1 || !Squad.Alive()) continue;
		++SquadsAlive;
		bHasMedic |= Squad.bMedic;
		if (!Squad.bMedic) CombatReady += Squad.Ready();
	}
	if (SquadsAlive < FYellReinforcements::MaxSquads)
		TryReinforce(1, !bHasMedic && CombatReady >= 4);
}

void AYellBattle::RunRival(const double Now)
{
	struct FLane
	{
		float Own = 0, Seen = 0, Proximity = 0, Support = 0;
		int32 Assigned = 0, Hits = 0, OwnCount = 0, SeenCount = 0;
	};
	FLane Lanes[3];
	auto Index = [](EYellZone Z) { return int32(Z) - int32(EYellZone::Left); };
	for (auto It = Intelligence.CreateIterator(); It; ++It)
	{
		const auto& C = It.Value();
		const float Age = (Now - C.Reported) / IntelLifetime;
		if (Age >= 1) { It.RemoveCurrent(); continue; }
		auto& L = Lanes[Index(C.Lane)];
		L.Seen += C.Power * C.Confidence * (1 - Age);
		if (C.Power > 0.f && Now - C.Reported < 10.) ++L.SeenCount;
		L.Proximity = FMath::Max(L.Proximity, C.Proximity);
	}

	int32 Fighters = 0;
	const FYellSquad* Interceptor = nullptr;
	double NearestToBase = TNumericLimits<double>::Max();
	for (const auto& S : Squads)
	{
		if (S.Team != 1 || S.bMedic || !S.Ready()) continue;
		++Fighters;
		for (const auto& M : S.Members)
		{
			if (!M.IsValid() || !M->CanAct()) continue;
			auto& L = Lanes[Index(LaneOf(M->GetActorLocation()))];
			L.Own += M->Health * 20.f;
			++L.OwnCount;
			if (Now - M->LastHit <= 3.) ++L.Hits;
			const double ToBase = FVector::DistSquared2D(M->GetActorLocation(), CorePosition(1));
			if (ToBase < NearestToBase)
			{
				NearestToBase = ToBase;
				Interceptor = &S;
			}
		}
	}
	float Threat = 0;
	for (int32 I=0; I<3; ++I)
	{
		const auto& L = Lanes[I];
		const float Risk = L.Proximity * L.Seen / FMath::Max(2000.f,L.Own);
		Threat = FMath::Max(Threat, Risk);
	}
	const bool bCoreUnderFire = Now - LastRivalCoreHit <= 6.0;
	if (bCoreUnderFire || Threat >= 1.1f)
		RetreatUntil = Now + 9.;
	const bool Retreat = Now < RetreatUntil;
	auto Send = [&](const FYellSquad& S, EYellAction Action, EYellZone Zone)
	{
		for (const auto& M : S.Members)
		{
			if (!M.IsValid() || !M->CanAct()) continue;
			if (M->CurrentOrder.Action == Action && M->CurrentOrder.Zone == Zone) continue;
			FYellOrder O;
			O.Squad = S.Id; O.Action = Action; O.Zone = Zone;
			bool Accepted = false;
			Dispatch(O, {FGuid::NewGuid(), EYellChannel::Rival, FVector::ZeroVector, Now}, Accepted);
			break;
		}
	};
	int32 AttackingSquads = 0;
	for (const auto& S : Squads)
	{
		if (S.Team != 1 || S.bMedic || !S.Ready()) continue;
		if (Retreat)
		{
			const bool bAtPerimeter = S.Members.ContainsByPredicate([&](const auto& M)
			{
				return M.IsValid() && M->CanAct() &&
					FVector::DistSquared2D(M->GetActorLocation(), Position(EYellZone::Home, 1)) < FMath::Square(560.);
			});
			AttackLanes.Remove(S.Id);
			const auto Move = RivalPolicy.Decide(true, bAtPerimeter || &S == Interceptor,
				false, false, false, false, 0.f, false, false);
			Send(S, Move == EYellRivalMove::Guard ? EYellAction::Defend : EYellAction::Retreat, EYellZone::Home);
			continue;
		}
		if (Threat >= .6f && &S == Interceptor)
		{
			AttackLanes.Remove(S.Id);
			Send(S, EYellAction::Defend, EYellZone::Home);
			continue;
		}
		int32 Best = 0;
		float Top = -1e9f;
		for (int32 I=0; I<3; ++I)
		{
			const auto& L = Lanes[I];
			const float Ratio = (L.Own+10)/(L.Seen+10);
			// A contested lane with a plausible advantage can justify a second squad.
			float Score = L.Seen < 1 ? 65 : Ratio < .65 ? 25 : Ratio <= 1.6 ? 100 : 75;
			Score -= L.Assigned * (L.SeenCount > L.OwnCount ? 24.f : 42.f);
			for (const auto& M : S.Members)
				if (M.IsValid() && M->CanAct()) { if (Index(M->CurrentOrder.Zone)==I) Score += 24; break; }
			if (Score > Top) { Top = Score; Best = I; }
		}
		const auto* CommittedLane = AttackLanes.Find(S.Id);
		if (CommittedLane) Best = Index(*CommittedLane);
		auto& L = Lanes[Best];
		++L.Assigned;
		const auto Zone = EYellZone(int32(EYellZone::Left)+Best);
		int32 Formation = 0;
		int32 Healthy = 0;
		bool bTakingFire = false;
		FVector PositionSum = FVector::ZeroVector;
		for (const auto& M : S.Members)
		{
			if (!M.IsValid() || !M->CanAct()) continue;
			PositionSum += M->GetActorLocation();
			if (M->Health >= 62.f) ++Healthy;
			bTakingFire |= Now - M->LastHit < 5.;
			if (LaneOf(M->GetActorLocation()) == Zone && M->GetActorLocation().X < 670.) ++Formation;
		}
		const FVector SquadPosition = PositionSum / S.Ready();
		const auto& Nearby = Lanes[Index(LaneOf(SquadPosition))];
		const bool bOvermatched = Nearby.SeenCount >= 2 && Nearby.SeenCount > Nearby.OwnCount &&
			Nearby.Seen > Nearby.Own * 1.1f && bTakingFire;
		const auto& Center = Lanes[1];
		const bool bRouteContested = Best != 1 && Center.SeenCount >= S.Ready() &&
			Center.Seen > Center.Own * 1.15f;
		const bool bHasCover = Threat < .55f && AttackingSquads < FMath::Min(2, Fighters - 1);
		const bool bStaged = Healthy >= 2 && (Formation >= 2 || (CommittedLane && SquadPosition.X < -950.));
		const int32 OwnCount = CommittedLane ? Nearby.OwnCount : L.OwnCount;
		const int32 SeenCount = CommittedLane ? FMath::Max(L.SeenCount, Nearby.SeenCount) : L.SeenCount;
		const float Strength = CommittedLane ? Nearby.Own : L.Own;
		const float Opposition = CommittedLane ? FMath::Max(L.Seen, Nearby.Seen) : L.Seen;
		const int32 ClearFormation = RivalPolicy.Aggression >= .8f ? 2 : 3;
		const bool bNumbers = OwnCount > SeenCount && SeenCount > 0;
		const bool bClearOpportunity = SeenCount == 0 && Opposition < Strength * .6f && !bTakingFire
			&& Healthy >= ClearFormation && OwnCount >= ClearFormation;
		const float StrengthRatio = (Strength + 1.f) / FMath::Max(1.f, Opposition);
		const auto Move = RivalPolicy.Decide(false, false, bOvermatched || (bTakingFire && Healthy < 2),
			bStaged, bHasCover, bRouteContested, StrengthRatio, bNumbers, bClearOpportunity);
		if (Move == EYellRivalMove::Assault)
		{
			++AttackingSquads;
			AttackLanes.Add(S.Id, Zone);
			Send(S, EYellAction::Attack, EYellZone::Rival);
		}
		else
		{
			AttackLanes.Remove(S.Id);
			if (Move == EYellRivalMove::Withdraw) Send(S, EYellAction::Retreat, EYellZone::Home);
			else
			{
				Send(S, EYellAction::Defend, Zone);
				L.Support += S.Ready();
			}
		}
	}
	for (const auto& S : Squads)
	{
		if (S.Team != 1 || !S.bMedic || !S.Ready()) continue;
		float Top = 0;
		EYellZone Zone = EYellZone::Home;
		for (int32 I=0; !Retreat && I<3; ++I)
		{
			const auto& L = Lanes[I];
			const float Score = L.Own >= .35f*L.Seen ? L.Support * L.Hits * L.Own : 0;
			if (Score > Top) { Top = Score; Zone = EYellZone(int32(EYellZone::Left)+I); }
		}
		Send(S,EYellAction::Heal,Zone);
	}
}
